"""Desktop mode: app launcher + login item + tray, installed and run as one.

``install`` writes the icons, the launcher and the login item and records them
in ``~/.anyscribe/desktop.json``; ``open`` (what the app icon runs) makes sure
the tray and its server are up, then opens the dashboard.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from collections.abc import Callable
from datetime import datetime, timezone
from importlib.util import find_spec
from pathlib import Path
from typing import TypedDict

from anyscribe import __version__
from anyscribe.config import paths
from anyscribe.core import launcher, service, tray
from anyscribe.core.fileutil import atomic_write


class Manifest(TypedDict):
    version: str
    python: str
    port: int
    launcher: str
    login_item: str
    installed_at: str


class DesktopError(Exception):
    pass


class TrayMissing(DesktopError):
    def __init__(self) -> None:
        super().__init__('The tray isn\'t installed. Run: pip install "anyscribe[tray]" first.')


class PortInUseError(DesktopError):
    def __init__(self, port: int) -> None:
        self.port = port
        super().__init__(
            f"Port {port} is in use by another program. "
            "Run: anyscribe desktop install --port <free port>"
        )


class StartFailed(DesktopError):
    def __init__(self, port: int) -> None:
        self.port = port
        super().__init__(f"anyscribe did not start on port {port}. See the log: {tray.TRAY_LOG}")


def read_manifest() -> Manifest | None:
    try:
        return json.loads(paths.DESKTOP_MANIFEST.read_text())
    except (OSError, ValueError):
        return None


def write_manifest(m: Manifest) -> None:
    atomic_write(paths.DESKTOP_MANIFEST, json.dumps(m, indent=2) + "\n")


def tray_available() -> bool:
    return find_spec("pystray") is not None and find_spec("PIL") is not None


def health_is_anyscribe(port: int) -> bool:
    """True if anyscribe's own web server answers on this port."""
    try:
        import httpx

        # A login-started server runs throttled: health took 3.5-8 s there on macOS
        # (0.4 s from a terminal). Too short a timeout reads our own server as foreign.
        r = httpx.get(f"http://127.0.0.1:{port}/api/health", timeout=10.0)
        body = r.json()
    except Exception:
        return False
    return r.status_code == 200 and isinstance(body, dict) and "version" in body


def spawn_detached(args: list[str], log: Path) -> subprocess.Popen:
    """Start a process that outlives this one, output appended to ``log``."""
    log.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        kwargs: dict = {"creationflags": flags}
    else:
        kwargs = {"start_new_session": True}
    with open(log, "ab") as out:
        return subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            # Started from Finder / the Start menu, our own PATH lacks ffmpeg and Deno.
            env={**os.environ, "PATH": service.service_path()},
            **kwargs,
        )


EXTERNAL_WAIT = 10.0  # seconds open_dashboard waits for launchd's tray before spawning one


def _wait_until(done: Callable[[], bool], timeout: float, interval: float = 0.25) -> bool:
    deadline = time.monotonic() + timeout
    while not done():
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval)
    return True


def _start(args: list[str] | None, port: int, timeout: float) -> str:
    """Spawn ``args`` (None: a tray is already starting) and wait for health.

    Returns "up", "exited" (the process died first) or "timeout".
    """
    proc = spawn_detached(args, tray.TRAY_LOG) if args else None
    result = "timeout"

    def done() -> bool:
        nonlocal result
        if health_is_anyscribe(port):
            result = "up"
        elif proc is not None and proc.poll() is not None:
            result = "exited"
        else:
            return False
        return True

    _wait_until(done, timeout)
    return result


def open_dashboard(port: int, timeout: float = 15.0, expect_external: bool = False) -> str:
    """Make sure anyscribe is serving on ``port``, then open the dashboard.

    ``expect_external``: a tray is being started by someone else (launchd's
    RunAtLoad); give it ``EXTERNAL_WAIT`` seconds to show up before spawning one.
    """
    url = f"http://127.0.0.1:{port}"
    if expect_external:
        _wait_until(
            lambda: tray.read_pidfile() is not None or health_is_anyscribe(port), EXTERNAL_WAIT
        )
    if not health_is_anyscribe(port):
        if tray.port_responding(port):
            raise PortInUseError(port)
        python = launcher.pythonw(sys.executable)
        # A tray already running (e.g. launchd's) brings its server up; a second would race it.
        tray_args = [python, "-m", "anyscribe", "tray", "--port", str(port)]
        state = _start(None if tray.read_pidfile() else tray_args, port, timeout)
        if state == "exited":
            # The tray exits at once with no tray backend (headless Linux, no display).
            ui_args = [python, "-m", "anyscribe", "ui", "--port", str(port), "--no-open"]
            state = _start(ui_args, port, timeout)
        if state != "up":
            raise StartFailed(port)
    if not webbrowser.open(url):
        print(url, file=sys.stderr)  # stdout may carry a --json envelope
    return url


def install(port: int = tray.DEFAULT_PORT, launch: bool = True) -> Manifest:
    if not service.supported():
        raise NotImplementedError(f"Desktop mode is not supported on {sys.platform}")
    if not tray_available():
        raise TrayMissing()

    old = read_manifest()
    if old:
        # Clean reinstall: a running tray keeps launchd's old job and the old port alive.
        tray.stop_tray(old["port"])
        service.uninstall_service()
        _wait_until(lambda: not tray.port_responding(old["port"]), 10)
    if tray.port_responding(port) and not health_is_anyscribe(port):
        raise PortInUseError(port)

    icons = launcher.render_icons(paths.DESKTOP_DIR)
    launcher_p = launcher.install_launcher(sys.executable, port, icons)
    if sys.platform == "darwin":
        # Login item first: launchd's RunAtLoad starts the tray it supervises, so
        # KeepAlive restarts it after a crash. A tray we spawned would be outside launchd.
        login_item = service.install_service(port)
        if launch:
            open_dashboard(port, expect_external=True)
    else:
        # These login items do nothing until the next login: start the tray ourselves.
        if launch:
            open_dashboard(port)
        login_item = service.install_service(port)
    m: Manifest = {
        "version": __version__,
        "python": sys.executable,
        "port": port,
        "launcher": str(launcher_p),
        "login_item": str(login_item),
        "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    write_manifest(m)
    return m


def uninstall() -> dict:
    """Stop the tray and server, remove launcher, login item, icons and manifest."""
    m = read_manifest()
    port = m["port"] if m else tray.DEFAULT_PORT
    stopped = False
    # Nothing recorded and no tray: a server on the port was started by hand; leave it.
    if m or tray.read_pidfile():
        was_serving = health_is_anyscribe(port)
        stopped = tray.stop_tray(port) or was_serving
    login_item = service.uninstall_service()  # after the stop, so macOS unloads the job
    launcher_removed = launcher.uninstall_launcher()
    shutil.rmtree(paths.DESKTOP_DIR, ignore_errors=True)
    paths.DESKTOP_MANIFEST.unlink(missing_ok=True)
    return {"stopped": stopped, "launcher": launcher_removed, "login_item": login_item}


def status() -> dict:
    m = read_manifest()
    port = m["port"] if m else tray.DEFAULT_PORT
    launcher_p = Path(m["launcher"]) if m else launcher.launcher_path()
    login_item = Path(m["login_item"]) if m else service.login_item_path()
    reinstall = "Run: anyscribe desktop install"
    if not m and (launcher_p.exists() or service.is_installed()):
        reason = f"Partly installed (launcher or login item present, no manifest). {reinstall}"
    elif not m:
        reason = f"Not installed. {reinstall}"
    elif not Path(m["python"]).exists():
        reason = f"The recorded Python ({m['python']}) no longer exists. {reinstall}"
    elif not launcher_p.exists():
        reason = f"The app launcher is missing ({launcher_p}). {reinstall}"
    elif not login_item.exists():
        reason = f"The login item is missing ({login_item}). {reinstall}"
    else:
        reason = None
    return {
        "platform": sys.platform,
        "supported": service.supported(),
        "installed": m is not None,
        "launcher": str(launcher_p),
        "login_item": str(login_item),
        "python": m["python"] if m else None,
        "port": port,
        "tray_running": tray.read_pidfile() is not None,
        "server_running": health_is_anyscribe(port),
        "healthy": reason is None,
        "reason": reason,
    }
