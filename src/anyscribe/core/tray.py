"""Tray companion core — process supervision, port probe, pidfile.

GUI-free helpers so they stay unit-testable. The pystray loop lives in
``cli/tray_cmd.py`` and imports these. All pystray/Pillow imports are lazy
inside the command, never here or at module import — base install stays
tray-free.
"""

from __future__ import annotations

import os
import signal
import socket

from anyscribe.config.paths import APP_HOME, LOGS_DIR

PIDFILE = APP_HOME / "tray.pid"
TRAY_LOG = LOGS_DIR / "tray.log"
GITHUB_RELEASES_URL = "https://github.com/rishmadaan/anyscribe/releases"
DEFAULT_PORT = 8457


def port_responding(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """True if something is listening on host:port (a server is up)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def _windows_pid_alive(pid: int) -> bool:
    """Windows existence probe: open the process and check it has not exited."""
    import ctypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == 259  # STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _pid_alive(pid: int) -> bool:
    """True if a process with this pid exists (POSIX: signal 0 probe; Windows: OpenProcess)."""
    if os.name == "nt":
        # os.kill(pid, 0) on Windows sends CTRL_C_EVENT, not a probe.
        return _windows_pid_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    return True


def read_pidfile() -> int | None:
    """Return the live pid recorded in the pidfile, or None.

    Stale pidfiles (process gone) are treated as absent — so a crash doesn't
    lock out the next launch.
    """
    try:
        pid = int(PIDFILE.read_text().strip())
    except (FileNotFoundError, ValueError, OSError):
        return None
    return pid if _pid_alive(pid) else None


def write_pidfile() -> None:
    PIDFILE.parent.mkdir(parents=True, exist_ok=True)
    PIDFILE.write_text(str(os.getpid()))


def remove_pidfile() -> None:
    try:
        PIDFILE.unlink()
    except FileNotFoundError:
        pass


def _post_shutdown(port: int) -> None:
    """Ask the web server on this port to stop; ignore any failure."""
    try:
        import httpx

        httpx.post(f"http://127.0.0.1:{port}/api/shutdown", timeout=2.0)
    except Exception:
        pass


def stop_tray(port: int) -> bool:
    """Stop a running tray and its server from outside. True if a tray pid was signalled."""
    _post_shutdown(port)
    pid = read_pidfile()
    signalled = False
    if pid is not None:
        try:
            os.kill(pid, signal.SIGTERM)
            signalled = True
        except OSError:
            pass  # exited since the pidfile read, or not ours to signal; drop the pidfile anyway
    remove_pidfile()
    return signalled
