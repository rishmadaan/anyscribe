"""System endpoints — shutdown, autostart, tailnet sharing."""

from __future__ import annotations

import sys
from importlib.util import find_spec

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from anyscribe.core import service, tailnet, tray
from anyscribe.core.config_set import set_value
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
    """Live sharing state of this server, plus the saved setting (they differ after a one-off flag)."""
    return {**request.app.state.tailnet.status.to_dict(), "saved": tailnet.saved_setting()}


@router.get("/tailnet")
async def tailnet_status(request: Request) -> dict:
    return tailnet_state(request)


@router.put("/tailnet")
def set_tailnet(req: TailnetRequest, request: Request) -> dict:
    """Save the setting and apply it to this running server now (sync: runs in the threadpool)."""
    set_value("tailnet", req.enabled)
    request.app.state.tailnet.apply(req.enabled)
    return tailnet_state(request)


@router.post("/shutdown")
async def shutdown(request: Request) -> dict:
    """Gracefully shut down the server."""
    server = getattr(request.app.state, "server", None)
    if server:
        server.should_exit = True
    return {"ok": True, "message": "shutting down"}
