"""FastAPI application factory for the anyscribe web UI."""

from __future__ import annotations

import os
import re
import signal
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from anyscribe import __version__
from anyscribe.core import tailnet
from anyscribe.core.tray import ensure_streams as _ensure_streams

STATIC_DIR = Path(__file__).parent / "static"

LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
WRONG_HOST = (
    "anyscribe only answers on this computer's own address (127.0.0.1 or localhost), "
    "or on its own tailnet link while it is shared. "
    "Open it on the computer running anyscribe to see why."
)
WRONG_ORIGIN = "anyscribe does not answer requests sent by other websites."


def _host_name(host: str) -> str:
    """The Host header without its port: "[::1]:8457" -> "[::1]", "box.ts.net:8457" -> "box.ts.net"."""
    host = host.strip().lower()
    if host.startswith("["):
        return host[: host.find("]") + 1]
    return host.partition(":")[0]


# A serialized origin and nothing else: scheme, host, optional port. No userinfo, path,
# query, fragment or spaces; "null" does not match. The port is range-checked below.
SERIALIZED_ORIGIN = re.compile(r"https?://(\[[0-9a-f:.]+\]|[a-z0-9.-]+)(?::([0-9]{1,5}))?", re.I)


def _origin_host(origin: bytes) -> str:
    """The host an Origin header names; "" for "null" or anything but a serialized origin
    (a port above 65535 included)."""
    match = SERIALIZED_ORIGIN.fullmatch(origin.decode("latin-1"))
    if not match or int(match.group(2) or 0) > 65535:
        return ""
    return match.group(1).lower()


class HostCheck:
    """Pure ASGI (HTTP and WebSocket): answer only on local names and, while this server holds
    a share, the exact tailnet name Tailscale gave it. Blocks DNS rebinding, where a
    web page reaches 127.0.0.1 under its own name; with sharing off no other name is answered,
    so a leftover or hand-made Tailscale rule cannot expose the page.

    An Origin header, when present, must be one serialized origin naming one of those same
    hosts (any port: the Vite dev
    server proxies with the browser's Origin). Blocks other websites' no-preflight requests
    (a form POST to /api/shutdown); "null" is refused, and no Origin (curl, the CLI) passes."""

    def __init__(self, app, share: tailnet.Share) -> None:
        self.app = app
        self.share = share

    def allowed(self, host: str) -> bool:
        name = _host_name(host)
        if name in LOCAL_HOSTS:
            return True
        held = self.share.held  # the share being held, not the display (it may read failed)
        return bool(held and name == urlsplit(held).hostname)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = dict(reversed(scope["headers"]))  # a repeated header: the first counts
            host = headers.get(b"host", b"").decode("latin-1")
            origins = [v for k, v in scope["headers"] if k == b"origin"]
            refusal = None
            if not self.allowed(host):
                refusal = WRONG_HOST
            elif len(origins) > 1 or (origins and not self.allowed(_origin_host(origins[0]))):
                refusal = WRONG_ORIGIN
            if refusal:
                if scope["type"] == "websocket":
                    await receive()  # websocket.connect
                    await send({"type": "websocket.close", "code": 1008})  # sent as HTTP 403
                else:
                    await PlainTextResponse(refusal, status_code=403)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(
        title="anyscribe",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # Import and include route modules
    from anyscribe.web.routes.config import router as config_router
    from anyscribe.web.routes.health import router as health_router
    from anyscribe.web.routes.history import router as history_router
    from anyscribe.web.routes.local import router as local_router
    from anyscribe.web.routes.models import router as models_router
    from anyscribe.web.routes.onboarding import router as onboarding_router
    from anyscribe.web.routes.system import router as system_router
    from anyscribe.web.routes.transcribe import router as transcribe_router

    app.include_router(health_router)
    app.include_router(config_router)
    app.include_router(history_router)
    app.include_router(transcribe_router)
    app.include_router(system_router)
    app.include_router(local_router)
    app.include_router(models_router)
    app.include_router(onboarding_router)

    # Tailnet sharing state for this server; run() sets the port.
    app.state.tailnet = tailnet.Share()

    # Serve built React SPA from static/
    if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
        # Mount static assets (JS, CSS, images)
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        # SPA catch-all: any non-API path serves index.html for client-side routing
        @app.get("/{full_path:path}")
        async def spa_fallback(request: Request, full_path: str) -> FileResponse:
            # Serve actual files if they exist (favicon.svg, etc.)
            file_path = STATIC_DIR / full_path
            if full_path and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(STATIC_DIR / "index.html")

    return app


# After stdin closes, how long a graceful shutdown may take before the process exits hard.
STDIN_EXIT_GRACE_SECONDS = 10.0


def _lead_own_process_group() -> None:
    """Make this engine its own process group's leader, so its children (pip, yt-dlp, ffmpeg)
    share its group and the hard exit can take them along. POSIX only. A session leader (the
    app starts it detached) already leads its group; setpgrp raises there, which is fine."""
    if hasattr(os, "setpgrp"):
        try:
            os.setpgrp()
        except OSError:  # _exit_hard checks leadership, so failing here only loses the group
            pass


def _exit_hard() -> None:
    """Exit now, killing the process group too when this engine leads it. Never signal a
    group it does not lead: that could be the app's."""
    if hasattr(os, "killpg") and os.getpgid(0) == os.getpid():
        os.killpg(os.getpid(), signal.SIGKILL)
    os._exit(1)


def _stop_when_stdin_closes(server, share: tailnet.Share) -> None:
    """Read stdin until end of file, then stop as POST /api/shutdown does; exit hard if that
    has not finished within the grace period (a running job or open socket can hold it)."""
    while sys.stdin.buffer.read(4096):
        pass
    # The clock starts first, so a slow Tailscale call or a failing print cannot delay or skip it.
    timer = threading.Timer(STDIN_EXIT_GRACE_SECONDS, _exit_hard)
    timer.daemon = True
    timer.start()
    try:
        error = share.close()
        if error:
            print(tailnet.CLEANUP_FAILED.format(error=error, port=share.port), flush=True)
    finally:
        server.should_exit = True


def run(
    host: str = "127.0.0.1", port: int = 8457, open_browser: bool = True, watch_stdin: bool = False
) -> None:
    """Start the uvicorn server."""
    _ensure_streams()
    import uvicorn

    app = create_app()
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    # Stash server on app.state so /shutdown route can access it
    app.state.server = server

    share = app.state.tailnet
    share.port = port
    # Only the real server checks Host (TestClient tests of create_app() send "testserver").
    app.add_middleware(HostCheck, share=share)
    wanted = tailnet.run_override
    if wanted is None:
        try:
            wanted = tailnet.saved_setting()
        except Exception:  # a broken config.yaml must not stop the dashboard starting
            print(
                "Couldn't read your anyscribe config, so tailnet sharing is off for this run.",
                flush=True,
            )
            wanted = False

    if wanted:

        def _share_when_listening() -> None:
            # uvicorn runs startup events BEFORE it binds the port, so wait for the bind:
            # a failed bind must never touch Tailscale or print a link.
            while not server.started:
                if server.should_exit or share.closed:
                    return
                time.sleep(0.05)
            print("Asking Tailscale to share it...", flush=True)
            line = tailnet.describe(share.apply(True))
            if line:
                print(line, flush=True)

        @app.on_event("startup")
        async def _share_on_tailnet() -> None:
            app.state.tailnet_thread = threading.Thread(target=_share_when_listening, daemon=True)
            app.state.tailnet_thread.start()

    # Shutdown runs on /api/shutdown, Ctrl+C and SIGTERM alike (uvicorn re-raises
    # the signal only after it). A no-op unless this process owns a live rule.
    @app.on_event("shutdown")
    async def _unshare() -> None:
        error = await run_in_threadpool(share.close)
        if error:
            print(tailnet.CLEANUP_FAILED.format(error=error, port=port), flush=True)

    if watch_stdin:
        # One exit door: stdin end, SIGTERM, SIGINT, the server stopping by itself or the
        # deadline all end in _exit_hard, which takes the engine's children with it.
        # uvicorn captures SIGTERM/SIGINT while serving (graceful stop, tailnet rule removed),
        # then restores these handlers and re-raises the signal into them.
        _lead_own_process_group()
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: _exit_hard())
        threading.Thread(target=_stop_when_stdin_closes, args=(server, share), daemon=True).start()

    if open_browser:

        @app.on_event("startup")
        async def _open_browser() -> None:
            webbrowser.open(f"http://{host}:{port}")

    if not watch_stdin:
        server.run()
        return
    try:
        server.run()
    finally:
        _exit_hard()
