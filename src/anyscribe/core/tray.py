"""Tray companion core — process supervision, port probe, pidfile, instance lock.

GUI-free helpers so they stay unit-testable. The pystray loop lives in
``cli/tray_cmd.py`` and imports these. All pystray/Pillow imports are lazy
inside the command, never here or at module import — base install stays
tray-free.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import IO

from anyscribe.config.paths import APP_HOME, LOGS_DIR

PIDFILE = APP_HOME / "tray.pid"
SERVER_PIDFILE = APP_HOME / "server.pid"
LOCKFILE = APP_HOME / "tray.lock"
TRAY_LOG = LOGS_DIR / "tray.log"
GITHUB_RELEASES_URL = "https://github.com/rishmadaan/anyscribe/releases"
DEFAULT_PORT = 8457


def acquire_instance_lock(path: Path | None = None) -> IO | None:
    """Take the one-tray-per-user lock; None if another tray holds it.

    Keep the returned file open for the tray's whole life: the OS drops the
    lock when the process exits, however it exits, so a crash never locks out
    the next start.
    """
    path = path or LOCKFILE
    path.parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "a+")
    try:
        if os.name == "nt":
            import msvcrt

            f.seek(0)  # msvcrt locks bytes from the current position
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def port_responding(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """True if something is listening on host:port (a server is up)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


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
    return r.status_code == 200 and isinstance(body, dict) and body.get("app") == "anyscribe"


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


def pid_is_anyscribe(pid: int) -> bool:
    """True if this pid's command line names anyscribe.

    A pidfile can outlive a crash or reboot, and its number can be reused by
    an unrelated program: never signal a pid on its number alone.
    """
    if pid <= 0:
        return False
    if os.name == "nt":
        query = f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine'
        args = ["powershell", "-NoProfile", "-NonInteractive", "-Command", query]
    else:
        args = ["ps", "-o", "command=", "-p", str(pid)]
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return "anyscribe" in out


def _read_pid(path: Path) -> int | None:
    try:
        pid = int(path.read_text().strip())
    except (FileNotFoundError, ValueError, OSError):
        return None
    return pid if pid > 0 and _pid_alive(pid) and pid_is_anyscribe(pid) else None


def read_pidfile() -> int | None:
    """Return the live anyscribe tray pid recorded in the pidfile, or None.

    A stale pidfile (process gone, or its pid reused by another program) is
    treated as absent.
    """
    return _read_pid(PIDFILE)


def write_pidfile(pid: int | None = None, path: Path | None = None) -> None:
    path = path or PIDFILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid or os.getpid()))


def remove_pidfile(force: bool = False, pid: int | None = None, path: Path | None = None) -> None:
    """Remove the pidfile if it still names ``pid`` (default: this process), or ``force``.

    A tray tearing down after a newer tray started must not delete the newer one's file.
    """
    path = path or PIDFILE
    try:
        if force or path.read_text().strip() == str(pid or os.getpid()):
            path.unlink()
    except OSError:  # includes FileNotFoundError
        pass


def _post_shutdown(port: int) -> None:
    """Ask anyscribe's web server on this port to stop; ignore any failure.

    Only anyscribe gets the request: another program on the port is left alone.
    """
    if not health_is_anyscribe(port):
        return
    try:
        import httpx

        httpx.post(f"http://127.0.0.1:{port}/api/shutdown", timeout=2.0)
    except Exception:
        pass


def _wait_until(done, timeout: float) -> bool:
    """Poll ``done()`` every 0.2 s until it is True or ``timeout`` elapses."""
    deadline = time.monotonic() + timeout
    while not done():
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.2)
    return True


def _terminate(pid: int | None, port: int, timeout: float) -> bool:
    """SIGTERM ``pid``, wait for it and the port, SIGKILL if it outlives ``timeout``.

    True if the pid was signalled. Waits for the port too, so a tray started
    right after cannot mistake the dying server for an external one.
    """
    signalled = False
    if pid is not None:
        try:
            os.kill(pid, signal.SIGTERM)
            signalled = True
        except OSError:
            pass  # exited since the pidfile read, or not ours to signal

    def gone() -> bool:
        return not (signalled and _pid_alive(pid)) and not port_responding(port)

    if not _wait_until(gone, timeout) and signalled and _pid_alive(pid):
        try:
            # Windows has no SIGKILL; os.kill there terminates outright.
            os.kill(pid, getattr(signal, "SIGKILL", signal.SIGTERM))
        except OSError:
            pass
        _wait_until(lambda: not port_responding(port), 2.0)
    return signalled


def stop_tray(port: int, timeout: float = 10.0) -> bool:
    """Stop a running tray and its server from outside. True if either was signalled.

    The server is stopped by its own pid as well: on Windows the tray is
    terminated outright, skipping its teardown, and a server whose HTTP side
    has stopped can still be finishing a transcription.
    """
    _post_shutdown(port)
    tray_signalled = _terminate(read_pidfile(), port, timeout)
    server_pid = _read_pid(SERVER_PIDFILE)
    server_signalled = server_pid is not None and _terminate(server_pid, port, timeout)
    remove_pidfile(force=True)
    remove_pidfile(force=True, path=SERVER_PIDFILE)
    return tray_signalled or server_signalled
