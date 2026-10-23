"""`anyscribe install-service` / `uninstall-service` — autostart at login.

macOS LaunchAgent, Windows Startup-folder shortcut, Linux XDG autostart entry.
Other platforms get a friendly "not supported" error.
"""

from __future__ import annotations

import json
import platform
import sys
from importlib.util import find_spec

import typer
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def _fail(msg: str, output_json: bool) -> None:
    if output_json:
        json.dump({"success": False, "data": None, "error": msg}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        err_console.print(f"[red]Error:[/red] {msg}")
    raise typer.Exit(code=1)


def _require_supported(output_json: bool) -> None:
    from anyscribe.core import service

    if not service.supported():
        _fail(f"Autostart is not supported on {platform.system()}.", output_json)


def install_service(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output result as JSON."),
) -> None:
    """[bold]Register[/bold] the tray companion to start automatically at login."""
    _require_supported(output_json)
    # With KeepAlive, a login item that can't import pystray relaunches every 10 s.
    if find_spec("pystray") is None:
        _fail(
            'The tray isn\'t installed. Run: pip install "anyscribe[tray]" first.',
            output_json,
        )
    from anyscribe.core.service import install_service as do_install, login_item_path

    if not yes and not output_json:
        typer.confirm(f"Install login item at {login_item_path()}?", abort=True)

    try:
        path = do_install()
    except RuntimeError as e:
        _fail(str(e), output_json)
    if output_json:
        # "plist" kept for agents written against the macOS-only release.
        data = {"path": str(path), "plist": str(path)}
        json.dump({"success": True, "data": data, "error": None}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        console.print(f"[green]Installed:[/green] {path}")
        console.print("[dim]The tray will start at your next login.[/dim]")


def uninstall_service(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output result as JSON."),
) -> None:
    """[bold red]Remove[/bold red] the tray companion's login autostart."""
    _require_supported(output_json)
    from anyscribe.core.service import login_item_path, uninstall_service as do_uninstall

    if not yes and not output_json:
        typer.confirm(f"Remove login item at {login_item_path()}?", abort=True)

    existed = do_uninstall()
    if output_json:
        json.dump(
            {"success": True, "data": {"removed": existed}, "error": None}, sys.stdout, indent=2
        )
        sys.stdout.write("\n")
    elif existed:
        console.print("[green]Removed[/green] the tray login item.")
    else:
        console.print("[dim]No tray login item was installed.[/dim]")
