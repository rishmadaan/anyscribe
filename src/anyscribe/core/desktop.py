"""Desktop mode: app launcher + login item + tray, installed and run as one.

``install`` writes the icons, the launcher and the login item and records them
in ``~/.anyscribe/desktop.json``; ``open`` (what the app icon runs) makes sure
the tray and its server are up, then opens the dashboard.
"""

from __future__ import annotations

import json
import os
import plistlib
import shutil
import signal
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
from anyscribe.core.tray import health_is_anyscribe


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


class PortMismatch(DesktopError):
    def __init__(self, installed: int, requested: int) -> None:
        self.installed, self.requested = installed, requested
        super().__init__(
            f"anyscribe is installed on port {installed}. Run `anyscribe desktop open` "
            f"(no --port) to open it, or `anyscribe desktop install --port {requested}` "
            "to move it."
        )


class StartFailed(DesktopError):
    def __init__(self, port: int) -> None:
        self.port = port
        super().__init__(f"anyscribe did not start on port {port}. See the log: {tray.TRAY_LOG}")


NO_TRAY_REASON = (
    "Running without its tray icon (no graphical session or tray support). "
    "The dashboard works; the tray will start at your next graphical login."
)


def running_without_tray(port: int) -> bool:
    """The dashboard answers but no tray is alive: the bare-dashboard fallback."""
    return tray.read_pidfile() is None and health_is_anyscribe(port)


def read_manifest() -> Manifest | None:
    try:
        return json.loads(paths.DESKTOP_MANIFEST.read_text())
    except (OSError, ValueError):
        return None


def write_manifest(m: Manifest) -> None:
    atomic_write(paths.DESKTOP_MANIFEST, json.dumps(m, indent=2) + "\n")


def tray_available() -> bool:
    return find_spec("pystray") is not None and find_spec("PIL") is not None


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
ORPHAN_GRACE = 3.0  # seconds a live tray gets to bring its server's port up


def _wait_until(done: Callable[[], bool], timeout: float, interval: float = 0.25) -> bool:
    deadline = time.monotonic() + timeout
    while not done():
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval)
    return True


def _login_item_port() -> int | None:
    """The port the macOS login item starts the tray on (its last argument), or None."""
    try:
        return int(plistlib.loads(service.plist_path().read_bytes())["ProgramArguments"][-1])
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None


def installed_port() -> int | None:
    """The port desktop mode is installed on: the manifest's, else the login item's."""
    m = read_manifest()
    return m["port"] if m else _login_item_port()


def _kickstart(port: int) -> bool:
    """Start the tray under launchd, so KeepAlive restarts it after a crash.

    Only reached with no tray alive, so no ``-k``: killing a job launchd is
    already respawning waits out its ThrottleInterval and then kills it again.
    False if there is no login item for this port or launchctl refused.
    """
    if _login_item_port() != port:
        return False  # no login item, or it serves another port
    target = f"gui/{os.getuid()}/{service.LABEL}"
    try:
        r = subprocess.run(
            ["launchctl", "kickstart", target], check=False, capture_output=True, timeout=15
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def _start_tray(port: int) -> subprocess.Popen | None:
    """Start the tray: through launchd on macOS when the login item is there, else spawn.

    Returns the spawned process, or None when launchd started it.
    """
    if sys.platform == "darwin" and _kickstart(port):
        return None
    python = launcher.pythonw(sys.executable)
    return spawn_detached([python, "-m", "anyscribe", "tray", "--port", str(port)], tray.TRAY_LOG)


def _signal_restart(pid: int) -> bool:
    """Ask a live tray to restart its server (SIGUSR1). False on Windows or if it is gone."""
    if os.name == "nt":
        return False
    try:
        os.kill(pid, signal.SIGUSR1)
    except OSError:
        return False
    return True


def _await_health(proc: subprocess.Popen | None, port: int, timeout: float) -> str:
    """Wait for health on ``port`` (``proc``: what was started, None if someone else).

    Returns "up", "exited-ok" (the process exited 0 first: a duplicate tray that
    found another holding the lock), "exited" (it failed) or "timeout".
    """
    result = "timeout"

    def done() -> bool:
        nonlocal result
        if health_is_anyscribe(port):
            result = "up"
        elif proc is not None and (code := proc.poll()) is not None:
            result = "exited-ok" if code == 0 else "exited"
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
    installed = installed_port()
    if installed is not None and installed != port:
        # Its tray serves another port: signalling or stopping it would take that one
        # down, and a tray spawned here would be killed by the next app click.
        raise PortMismatch(installed, port)
    url = f"http://127.0.0.1:{port}"
    if expect_external:
        _wait_until(
            lambda: tray.read_pidfile() is not None or health_is_anyscribe(port), EXTERNAL_WAIT
        )
    if not health_is_anyscribe(port):
        if tray.port_responding(port):
            raise PortInUseError(port)
        proc = None  # a tray already running (e.g. launchd's) brings its server up
        pid = tray.read_pidfile()
        if pid is None:
            proc = _start_tray(port)
        elif not _wait_until(lambda: tray.port_responding(port), ORPHAN_GRACE):
            # A tray whose server is gone (dashboard Shutdown, a crash): ask it for a new
            # server rather than kill it. Replace it only if that fails (or on Windows).
            if not (_signal_restart(pid) and _await_health(None, port, timeout) == "up"):
                tray.stop_tray(port)
                proc = _start_tray(port)
        state = _await_health(proc, port, timeout)
        if state == "exited-ok":
            # Another tray won the lock (two clicks at once): it brings the server up.
            state = _await_health(None, port, timeout)
        elif state == "exited":
            # The tray exits at once with no tray backend (headless Linux, no display).
            python = launcher.pythonw(sys.executable)
            ui_args = [python, "-m", "anyscribe", "ui", "--port", str(port), "--no-open"]
            state = _await_health(spawn_detached(ui_args, tray.TRAY_LOG), port, timeout)
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
    # A tray with no manifest is the pre-desktop-mode upgrade: it must go too, or it keeps
    # serving the old code and launchd's load of the new login item fails.
    if old or tray.read_pidfile() is not None:
        # Clean reinstall: a running tray keeps launchd's old job and the old port alive.
        old_port = old["port"] if old else port
        tray.stop_tray(old_port)
        service.uninstall_service()
        # The old install is gone: its port must not refuse this install's own open.
        paths.DESKTOP_MANIFEST.unlink(missing_ok=True)
        _wait_until(lambda: not tray.port_responding(old_port), 10)
    if tray.port_responding(port) and not health_is_anyscribe(port):
        raise PortInUseError(port)

    icons = launcher.render_icons(paths.DESKTOP_DIR)
    launcher_p = launcher.install_launcher(sys.executable, port, icons)
    if sys.platform == "darwin":
        # Login item first: launchd's RunAtLoad starts the tray it supervises, so
        # KeepAlive restarts it after a crash. A tray we spawned would be outside launchd.
        if service.is_installed():
            # A job still loaded (e.g. no manifest) makes load a no-op and RunAtLoad never fires.
            service.uninstall_service()
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
    port = installed_port() or tray.DEFAULT_PORT  # same rule as `desktop open`
    stopped = False
    # Nothing recorded and no tray: a server on the port was started by hand; leave it.
    if m or tray.read_pidfile():
        was_serving = health_is_anyscribe(port)
        stopped = tray.stop_tray(port) or was_serving
    login_item = service.uninstall_service()  # after the stop, so macOS unloads the job
    launcher_removed = launcher.uninstall_launcher()
    shutil.rmtree(paths.DESKTOP_DIR, ignore_errors=True)
    paths.DESKTOP_MANIFEST.unlink(missing_ok=True)
    lock = tray.acquire_instance_lock()
    if lock is not None:  # no tray holds it (a live tray's lock must stay)
        lock.close()
        tray.LOCKFILE.unlink(missing_ok=True)
    return {"stopped": stopped, "launcher": launcher_removed, "login_item": login_item}


def status() -> dict:
    m = read_manifest()
    port = installed_port() or tray.DEFAULT_PORT  # same rule as `desktop open`
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
    server_running = health_is_anyscribe(port)
    tray_running = tray.read_pidfile() is not None
    if reason is None and not server_running:
        reason = "Installed but not running. Click the anyscribe app or run: anyscribe desktop open"
    healthy = reason is None
    if healthy and not tray_running:
        reason = NO_TRAY_REASON  # the dashboard answers, so still healthy
    return {
        "platform": sys.platform,
        "supported": service.supported(),
        "installed": m is not None,
        "launcher": str(launcher_p),
        "login_item": str(login_item),
        "python": m["python"] if m else None,
        "port": port,
        "tray_running": tray_running,
        "server_running": server_running,
        "healthy": healthy,
        "reason": reason,
    }
