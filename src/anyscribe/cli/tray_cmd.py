"""`anyscribe tray` — menu-bar/tray companion that supervises the web server.

All pystray/Pillow imports are lazy (inside functions) so the base install
stays tray-free and `anyscribe tray --help` works without the `[tray]` extra.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from typing import NoReturn

import typer
from rich.console import Console

from anyscribe.core import tray as core

console = Console()
err_console = Console(stderr=True)

_MISSING_EXTRA = "The tray companion needs extra packages.\nRun: pip install -U 'anyscribe[tray]'"

_SIGNALS = {signal.SIGTERM, signal.SIGINT}
if os.name != "nt":
    _SIGNALS.add(signal.SIGUSR1)  # from `anyscribe desktop open`: restart the server, keep the tray


def _make_image():
    """Load the bundled waveform glyph (black + alpha, template-ready).

    Falls back to a drawn circle if the asset is missing (e.g. odd
    packaging), so the tray never fails to start over an icon.
    """
    import io
    from importlib.resources import files

    from PIL import Image, ImageDraw

    try:
        data = files("anyscribe").joinpath("assets/tray-icon.png").read_bytes()
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((10, 10, size - 10, size - 10), fill=(0, 0, 0, 255))
        return img


def _mark_template(icon) -> None:
    """pystray setup callback: show the icon, then mark it as a macOS
    template image so it adapts to light/dark menu bars.

    Passing a custom setup to ``icon.run()`` REPLACES pystray's default,
    whose whole job is ``icon.visible = True`` — so we must set it here or
    the tray never appears. Visibility also creates the native image, which
    is why setTemplate_ comes second. The template call reaches into
    pystray's darwin backend; harmless no-op elsewhere."""
    icon.visible = True
    try:
        icon._icon_image.setTemplate_(True)
    except Exception:
        pass


def _shutdown_server(proc, port: int) -> None:
    """Stop a server WE spawned: POST /shutdown → wait 5s → SIGTERM → wait 3s → SIGKILL.

    ``proc is None`` means we attached to a pre-existing server we don't own —
    leave it alone.
    """
    if proc is None:
        return
    core._post_shutdown(port)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    core.remove_pidfile(pid=proc.pid, path=core.SERVER_PIDFILE)


def _child_kwargs() -> dict:
    """Popen kwargs for the server child, per platform."""
    if os.name == "nt":
        # No console window flashing up for a tray started without one.
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    # The tray blocks SIGTERM/SIGINT/SIGUSR1 (see _watch_signals_in_thread) and the
    # mask is inherited across exec — unblock in the child so uvicorn still
    # responds to signals.
    return {"preexec_fn": lambda: signal.pthread_sigmask(signal.SIG_UNBLOCK, _SIGNALS)}


def _watch_signals_in_thread(restart: Callable[[], None], teardown: Callable[[], None]) -> None:
    """SIGUSR1 runs ``restart``; SIGTERM/SIGINT run ``teardown`` (menu Quit's) and exit. POSIX only.

    A plain signal.signal handler never fires here: the Cocoa event loop
    blocks in ObjC, so Python bytecode (where handlers run) may never
    execute. Block the signals and catch them in a sigwait thread. Windows
    has neither call; there the finally around icon.run() does the teardown.
    """
    if os.name == "nt":
        return
    signal.pthread_sigmask(signal.SIG_BLOCK, _SIGNALS)

    def _watch() -> None:
        while signal.sigwait(_SIGNALS) == signal.SIGUSR1:
            try:
                restart()
            except Exception as e:  # the loop must survive, or SIGTERM is never caught again
                print(f"tray: restart failed: {e}", file=sys.stderr, flush=True)
        teardown()
        os._exit(0)  # Cocoa loop can't be trusted to unwind from a signal

    threading.Thread(target=_watch, daemon=True).start()


def _teardown(state: dict, port: int) -> None:
    """Single teardown for menu Quit, signals, and exceptions. Idempotent.

    ``closing`` is set before waiting for the lock: a restart already holding it
    finishes and its server is stopped here; one still waiting starts nothing.
    """
    state["closing"] = True
    with state["lock"]:
        _shutdown_server(state.pop("proc", None), port)
    core.remove_pidfile()


def tray(
    port: int = typer.Option(core.DEFAULT_PORT, "--port", "-p", help="Port to listen on."),
) -> None:
    r"""Run the [bold]menu-bar tray[/bold] companion (supervises the web server).

    Requires the optional extra: [bold]pip install 'anyscribe\[tray]'[/bold]
    """
    core.ensure_streams()
    # Held for the tray's whole life; checked before the extra so a duplicate exits quietly.
    lock = core.acquire_instance_lock()
    if lock is None:
        # Exit 0: the login item relaunches any non-zero exit, forever.
        err_console.print("[yellow]An anyscribe tray is already running.[/yellow]")
        raise typer.Exit(code=0)

    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        err_console.print(_MISSING_EXTRA, style="red", markup=False)
        raise typer.Exit(code=1)
    except Exception as e:  # e.g. Xlib's "Bad display name" on a box with no desktop
        _cannot_start(e)

    try:
        _run_tray(port)
    except Exception as e:
        _cannot_start(e)
    lock.close()


def _is_tray_log(stream) -> bool:  # noqa: ANN001
    try:
        return os.path.samestat(os.fstat(stream.fileno()), os.stat(core.TRAY_LOG))
    except (OSError, ValueError, AttributeError):
        return False


def _cannot_start(e: Exception) -> NoReturn:
    """One line, not a traceback; exit 1 so `desktop open` starts the bare dashboard."""
    first = (str(e).splitlines() or [""])[0]
    msg = (
        f"The tray could not start ({type(e).__name__}: {first}). The dashboard runs "
        "without it; the tray will try again at your next graphical login."
    )
    print(msg, file=sys.stderr, flush=True)
    if not _is_tray_log(sys.stderr):  # the Linux login entry's stderr is not tray.log
        core.TRAY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(core.TRAY_LOG, "a", encoding="utf-8") as log:
            log.write(msg + "\n")
    raise typer.Exit(code=1)


def _run_tray(port: int) -> None:
    import pystray

    core.write_pidfile()
    # One lock for start, restart and teardown; RLock because restart calls start.
    state: dict = {"proc": None, "closing": False, "lock": threading.RLock()}

    def _log(msg: str) -> None:
        print(f"tray: {msg}", file=sys.stderr, flush=True)  # the tray's stderr is tray.log

    def _start_server() -> None:
        """Spawn the uvicorn server as a subprocess unless anyscribe is already up."""
        with state["lock"]:
            if state["closing"]:
                return  # Quit has begun: a server started now would outlive the tray
            state["foreign"] = False
            if core.health_is_anyscribe(port):
                return  # attach to an externally-started anyscribe server (we don't own it)
            if core.port_responding(port):
                state["foreign"] = True
                _log(f"port {port} is used by another program; not starting the server")
                return
            core.TRAY_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(core.TRAY_LOG, "ab") as log:
                # Explicit streams: under pythonw.exe the tray has none to hand down.
                state["proc"] = subprocess.Popen(
                    [sys.executable, "-m", "anyscribe", "ui", "--port", str(port), "--no-open"],
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    **_child_kwargs(),
                )
            core.write_pidfile(state["proc"].pid, core.SERVER_PIDFILE)

    def on_open(icon, item) -> None:  # noqa: ANN001
        if core.health_is_anyscribe(port):
            webbrowser.open(f"http://127.0.0.1:{port}")
        else:
            _log(f"Open UI: anyscribe is not answering on port {port}")

    def restart_server(force: bool = True) -> None:
        """Menu Restart (force), or SIGUSR1 from `desktop open`: only when the server is down."""
        with state["lock"]:  # the menu and a signal must not spawn two servers
            if state["closing"]:
                return
            proc = state.get("proc")
            starting = proc is not None and proc.poll() is None
            if not force and (starting or core.health_is_anyscribe(port)):
                return
            _shutdown_server(state.pop("proc", None), port)
            time.sleep(0.5)
            _start_server()

    def on_restart(icon, item) -> None:  # noqa: ANN001
        restart_server()

    def on_updates(icon, item) -> None:  # noqa: ANN001
        webbrowser.open(core.GITHUB_RELEASES_URL)

    def status_text(item) -> str:  # noqa: ANN001
        if state.get("foreign"):
            return f"Status: port {port} is used by another program"
        return f"Status: {'running' if core.port_responding(port) else 'stopped'}"

    def on_quit(icon, item) -> None:  # noqa: ANN001
        _teardown(state, port)
        icon.stop()

    _watch_signals_in_thread(lambda: restart_server(force=False), lambda: _teardown(state, port))

    menu = pystray.Menu(
        pystray.MenuItem("Open UI", on_open, default=True),
        pystray.MenuItem(status_text, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Restart server", on_restart),
        pystray.MenuItem("Check for updates…", on_updates),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )

    icon = pystray.Icon("anyscribe", _make_image(), "anyscribe", menu)
    _start_server()
    try:
        # setup runs once the backend has built the native image.
        icon.run(setup=_mark_template)  # blocks until on_quit -> icon.stop()
    finally:
        _teardown(state, port)  # any exit path stops the server we own
