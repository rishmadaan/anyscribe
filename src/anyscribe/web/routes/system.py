"""System endpoints — shutdown, autostart."""

from __future__ import annotations

import sys
from importlib.util import find_spec

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from anyscribe.core import service

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
async def set_autostart(req: AutostartRequest) -> dict:
    """Install or remove the tray login item (macOS, Windows, Linux)."""
    if sys.platform not in service.SUPPORTED:
        raise HTTPException(status_code=400, detail=f"Autostart is not supported on {sys.platform}")
    if req.enabled:
        # A login item without pystray installs fine and then fails at login,
        # silently. Refuse up front instead.
        if find_spec("pystray") is None:
            raise HTTPException(
                status_code=400,
                detail='The menu-bar tray isn\'t installed. Run: pip install "anyscribe[tray]" first.',
            )
        try:
            service.install_service()
        except RuntimeError as e:  # Windows: the shortcut could not be created
            raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        service.uninstall_service()
    return _autostart_state()


@router.post("/shutdown")
async def shutdown(request: Request) -> dict:
    """Gracefully shut down the server."""
    server = getattr(request.app.state, "server", None)
    if server:
        server.should_exit = True
    return {"ok": True, "message": "shutting down"}
