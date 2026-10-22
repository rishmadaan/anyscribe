"""`anyscribe desktop` — install, remove, inspect and open the desktop app.

Exit codes: 0 ok; 1 refused or failed; 2 unsupported platform.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.markup import escape

from anyscribe.core import desktop, launcher, service, tray

desktop_app = typer.Typer(
    name="desktop",
    help="The [bold]desktop app[/bold]: app icon, start at login, menu-bar tray.",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)

STOPPED_COPY = (
    "Stopped anyscribe. If a transcription was running, it was interrupted: "
    "run it again (long jobs reuse the chunks they already finished)."
)


# Expected failures: shown as a message or JSON envelope with exit 1, never a traceback.
_FAILURES = (desktop.DesktopError, RuntimeError, OSError, subprocess.CalledProcessError)


def _emit(data: object) -> None:
    json.dump({"success": True, "data": data, "error": None}, sys.stdout, indent=2)
    sys.stdout.write("\n")


def _fail(msg: str, output_json: bool, code: int = 1) -> None:
    if output_json:
        json.dump({"success": False, "data": None, "error": msg}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        err_console.print(f"[red]Error:[/red] {escape(msg)}", soft_wrap=True)
    raise typer.Exit(code=code)


def _require_supported(output_json: bool) -> None:
    if not service.supported():
        _fail(f"Desktop mode is not supported on {platform.system()}.", output_json, code=2)


@desktop_app.command()
def install(
    port: int = typer.Option(
        tray.DEFAULT_PORT, "--port", "-p", min=1, max=65535, help="Port for the dashboard."
    ),
    no_launch: bool = typer.Option(False, "--no-launch", help="Don't start it or open it now."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output result as JSON."),
) -> None:
    """[bold]Install[/bold] the app icon, start it at login, and open the dashboard."""
    _require_supported(output_json)
    if not yes and not output_json:
        typer.confirm(
            f"Install the anyscribe app at {launcher.launcher_path()} and start it at login?",
            abort=True,
        )
    try:
        m = desktop.install(port=port, launch=not no_launch)
    except _FAILURES as e:
        _fail(str(e), output_json)
    if output_json:
        _emit(m)
        return
    console.print(f"[green]Installed:[/green] {escape(m['launcher'])}", soft_wrap=True)
    console.print(f"[green]Starts at login:[/green] {escape(m['login_item'])}", soft_wrap=True)
    if no_launch:
        console.print("[dim]Click the anyscribe app to open the dashboard.[/dim]")
    else:
        console.print(f"[green]Dashboard:[/green] http://127.0.0.1:{port}")


@desktop_app.command()
def uninstall(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output result as JSON."),
) -> None:
    """[bold red]Remove[/bold red] the app, its login item and icons; stop it if running.

    Never touches your transcripts, config or API keys.
    """
    _require_supported(output_json)
    if not yes and not output_json:
        typer.confirm("Stop anyscribe and remove the desktop app?", abort=True)
    try:
        r = desktop.uninstall()
    except _FAILURES as e:
        _fail(str(e), output_json)
    if output_json:
        _emit(r)
        return
    if r["stopped"]:
        console.print(STOPPED_COPY, soft_wrap=True, markup=False)
    if r["launcher"] or r["login_item"]:
        console.print("[green]Removed[/green] the anyscribe app and its login item.")
    else:
        console.print("[dim]The desktop app was not installed.[/dim]")


@desktop_app.command()
def status(
    output_json: bool = typer.Option(False, "--json", "-j", help="Output result as JSON."),
) -> None:
    """[bold]Show[/bold] whether the desktop app is installed, running and healthy."""
    s = desktop.status()
    if output_json:
        _emit(s)
        return
    if not s["supported"]:
        console.print(f"Desktop mode is not supported on {platform.system()}.")
        return
    yes_no = {True: "[green]yes[/green]", False: "[dim]no[/dim]"}
    console.print(f"Installed:       {yes_no[s['installed']]}")
    console.print(f"App:             {s['launcher']}", soft_wrap=True, markup=False)
    console.print(f"Login item:      {s['login_item']}", soft_wrap=True, markup=False)
    console.print(f"Tray running:    {yes_no[s['tray_running']]}")
    console.print(f"Server running:  {yes_no[s['server_running']]} (port {s['port']})")
    if s["healthy"]:
        console.print("Healthy:         [green]yes[/green]")
    else:
        console.print(
            f"Healthy:         [yellow]no[/yellow] — {escape(s['reason'])}", soft_wrap=True
        )


@desktop_app.command("open")
def open_cmd(
    port: Optional[int] = typer.Option(
        None, "--port", "-p", min=1, max=65535, help="Port (default: the installed one)."
    ),
) -> None:
    """[bold]Open[/bold] the dashboard, starting anyscribe first if needed (what the app icon runs)."""
    try:
        if port is None:
            m = desktop.read_manifest()
            port = m["port"] if m else tray.DEFAULT_PORT
        desktop.open_dashboard(port)
    except _FAILURES as e:
        # Started from the app icon there is no terminal; the log is where it shows.
        tray.TRAY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(tray.TRAY_LOG, "a") as log:
            log.write(f"desktop open: {e}\n")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
