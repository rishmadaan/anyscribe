"""Start-at-login for the tray companion, per OS.

macOS: a launchd LaunchAgent plist. Windows: a shortcut in the Startup folder.
Linux: an XDG autostart ``.desktop`` entry.

Uses ``{python} -m anyscribe tray`` rather than the ``scribe`` binary path:
the module path is stable within a given Python install, so it survives PATH
changes that would leave a hardcoded binary path dangling (per the plan).
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from xml.sax.saxutils import escape

from anyscribe.core import launcher, tray

LABEL = "com.anyscribe.tray"
SUPPORTED = frozenset({"darwin", "win32", "linux"})


def supported() -> bool:
    return sys.platform in SUPPORTED


def launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def plist_path() -> Path:
    return launch_agents_dir() / f"{LABEL}.plist"


def startup_dir() -> Path:
    return launcher.start_menu_dir() / "Startup"


def autostart_dir() -> Path:
    config = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config) / "autostart"


def login_item_path() -> Path:
    if sys.platform == "win32":
        return startup_dir() / "anyscribe tray.lnk"
    if sys.platform == "linux":
        return autostart_dir() / "anyscribe-tray.desktop"
    return plist_path()


def is_installed() -> bool:
    return login_item_path().exists()


def service_path(environ: Mapping[str, str] | None = None, home: Path | None = None) -> str:
    """PATH for the login item: launchd's default lacks ffmpeg, Deno and our venv.

    The installing shell's PATH first, then the usual install dirs, de-duplicated.
    """
    environ = os.environ if environ is None else environ
    home = home or Path.home()
    dirs = environ.get("PATH", "").split(os.pathsep) + [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        str(home / ".deno" / "bin"),
        str(home / ".local" / "bin"),
        str(Path(sys.executable).parent),
    ]
    return os.pathsep.join(dict.fromkeys(d for d in dirs if d))


def render_plist(
    python: str | None = None,
    label: str = LABEL,
    port: int = tray.DEFAULT_PORT,
    path_env: str | None = None,
    log: Path | None = None,
) -> str:
    """Return the launchd plist XML for the tray LaunchAgent.

    KeepAlive restarts the tray after a crash (non-zero exit) but not after Quit;
    ThrottleInterval (launchd's default, 10 s) spaces out a crash loop. ProcessType Interactive:
    the default lets launchd throttle the server's children (ffmpeg, yt-dlp), measured
    at 5-13 s for /api/health against 0.3 s.
    """
    python = python or sys.executable
    path_env = service_path() if path_env is None else path_env
    log = log or tray.TRAY_LOG
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{escape(label)}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{escape(python)}</string>
        <string>-m</string>
        <string>anyscribe</string>
        <string>tray</string>
        <string>--port</string>
        <string>{port}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{escape(path_env)}</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>ProcessType</key>
    <string>Interactive</string>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>{escape(str(log))}</string>
    <key>StandardErrorPath</key>
    <string>{escape(str(log))}</string>
</dict>
</plist>
"""


def _launchctl(*args: str) -> None:
    """Run launchctl; on failure print one plain line. Wrapped so tests can monkeypatch it.

    ``load``/``unload`` report failure on stderr with exit status 0 (seen on macOS 26.6), so
    any stderr counts as failure too; success prints nothing.
    """
    r = subprocess.run(["launchctl", *args], check=False, capture_output=True, text=True)
    detail = (r.stderr or "").strip()
    if r.returncode != 0 or detail:
        first = detail.splitlines()[0] if detail else f"exit status {r.returncode}"
        print(f"launchctl {args[0]} did not succeed: {first}", file=sys.stderr)


def render_autostart_entry(python: str, port: int, path_env: str) -> str:
    """XDG autostart entry; ``env`` carries the PATH (a login session lacks ffmpeg etc.)."""
    q = launcher.desktop_quote
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=anyscribe tray\n"
        f"Exec=env {q('PATH=' + path_env)} {q(python)} -m anyscribe tray --port {port}\n"
        "Terminal=false\n"
        "NoDisplay=true\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def install_service(port: int = tray.DEFAULT_PORT) -> Path:
    """Register the tray to start at login. Returns the login item's path."""
    if not supported():
        raise NotImplementedError(f"Autostart is not supported on {sys.platform}")
    path = login_item_path()
    if sys.platform == "win32":
        # No restart-on-crash on Windows: the Startup folder just runs it once.
        launcher.create_shortcut(
            path, launcher.pythonw(), f"-m anyscribe tray --port {port}", None, "anyscribe tray"
        )
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "linux":
        path.write_text(render_autostart_entry(sys.executable, port, service_path()))
        return path
    # launchd won't create the log's folder; a missing one stops the agent starting.
    tray.TRAY_LOG.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_plist(port=port, path_env=service_path(), log=tray.TRAY_LOG))
    _launchctl("load", str(path))
    return path


def uninstall_service() -> bool:
    """Remove the login item; a running tray keeps running. True if it existed."""
    if not supported():
        raise NotImplementedError(f"Autostart is not supported on {sys.platform}")
    path = login_item_path()
    existed = path.exists()
    if existed:
        # Unload kills the tray, and with it the dashboard the Startup toggle sits
        # in; only unload a registration that has no live tray behind it.
        if sys.platform == "darwin" and tray.read_pidfile() is None:
            _launchctl("unload", str(path))
        path.unlink()
    return existed
