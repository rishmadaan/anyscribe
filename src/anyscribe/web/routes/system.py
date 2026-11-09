"""System endpoints — shutdown, autostart, tailnet sharing."""

from __future__ import annotations

import sys
from importlib.util import find_spec

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from anyscribe.core import service, tailnet, tray
from anyscribe.web.models import TailnetRequest

router = APIRouter(prefix="/api", tags=["system"])


class AutostartRequest(BaseModel):
    enabled: bool


def _autostart_state() -> dict:
    supported = sys.platform in service.SUPPORTED
    return {"supported": supported, "enabled": supported and service.is_installed()}


@router.get("/autostart")
async def autostart_status() -> dict:
    """Report whether open-at-login is available and currently on."""
    return _autostart_state()


@router.put("/autostart")
async def set_autostart(req: AutostartRequest, request: Request) -> dict:
    """Install or remove the tray login item (macOS, Windows, Linux)."""
    if sys.platform not in service.SUPPORTED:
        raise HTTPException(status_code=400, detail=f"Autostart is not supported on {sys.platform}")
    if req.enabled:
        # A login item without pystray installs fine and then fails at login,
        # silently. Refuse up front instead.
        if find_spec("pystray") is None:
            raise HTTPException(
                status_code=400,
                detail='The tray isn\'t installed. Run: pip install "anyscribe[tray]" first.',
            )
        try:
            # The login item must reopen this dashboard's port, not always 8457.
            service.install_service(port=request.url.port or tray.DEFAULT_PORT)
        except RuntimeError as e:  # Windows: the shortcut could not be created
            raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        service.uninstall_service()
    return _autostart_state()


def tailnet_state(request: Request) -> dict:
    """Live sharing state of this server, plus the saved setting (they differ after a one-off flag).

    A config.yaml that can't be read gives saved None, never a 500: the live state still shows.
    """
    try:
        saved = tailnet.saved_setting()
    except Exception:
        saved = None
    return {**request.app.state.tailnet.status.to_dict(), "saved": saved}


@router.get("/tailnet")
def tailnet_status(request: Request) -> dict:
    """Sync (threadpool): while live it re-reads Tailscale, so a removed share is not shown live."""
    request.app.state.tailnet.refresh()
    return tailnet_state(request)


@router.put("/tailnet")
def set_tailnet(req: TailnetRequest, request: Request) -> dict:
    """Save the setting and apply it to this running server now (sync: runs in the threadpool)."""
    outcome = request.app.state.tailnet.save_and_apply(req.enabled)
    if not outcome.ok:
        raise HTTPException(status_code=500, detail=outcome.error)
    return tailnet_state(request)


@router.post("/shutdown")
async def shutdown(request: Request) -> dict:
    """Gracefully shut down the server, removing anyscribe's tailnet rule first."""
    # Before shutdown starts: uvicorn waits for in-flight work before its shutdown hook,
    # and the tray force-stops the server a few seconds after this request.
    await run_in_threadpool(request.app.state.tailnet.close)
    server = getattr(request.app.state, "server", None)
    if server:
        server.should_exit = True
    return {"ok": True, "message": "shutting down"}
