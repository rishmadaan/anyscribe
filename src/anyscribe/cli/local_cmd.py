"""``anyscribe local`` — provisioning lifecycle for offline transcription.

Three commands, all agentic-first (flag-driven, ``--json``-capable, idempotent,
no interactive prompts outside the setup confirmation which is guarded by
``--yes`` in non-TTY contexts):

* ``anyscribe local setup --model ID`` — install the engines + download a model.
* ``anyscribe local status`` — report readiness (safe before setup).
* ``anyscribe local teardown`` — reverse setup: uninstall + delete cached models.

Interactive model picking happens in ``anyscribe onboard``. This command group
never picks a model for the user — ``--model`` is required.
"""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from anyscribe.core.local_setup import (
    RESTART_MESSAGE,
    use_local_tip,
    check_status,
    run_setup,
    run_teardown,
)
from anyscribe.providers.local_models import (
    LANGUAGE_CHECK_MODEL,
    MODEL_SIZES,
    MODEL_SPECS,
    RECOMMENDED_MODEL,
    engine_of,
)

console = Console()
err_console = Console(stderr=True)

local_app = typer.Typer(
    name="local",
    help="Set up and manage offline transcription (Parakeet, Whisper).",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def _emit_event(event: dict) -> None:
    """NDJSON event writer used when --json is passed to setup/teardown."""
    json.dump(event, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _human_phase(event: dict) -> None:
    """Human-readable progress lines mirroring the NDJSON events."""
    name = event.get("event", "")
    if name == "detecting_install_method":
        console.print("[dim]• Detecting install method…[/dim]")
    elif name == "installing_package":
        console.print(
            "[dim]• Installing the local engines (faster-whisper, onnx-asr) "
            f"via {event.get('method', '?')}…[/dim]"
        )
    elif name == "pipx_not_on_path_fallback":
        console.print("[yellow]  pipx not on PATH — falling back to pip.[/yellow]")
    elif name == "package_installed":
        console.print("[green]• Engines installed.[/green]")
    elif name == "downloading_model":
        console.print(f"[dim]• Downloading {event.get('size', '?')} model…[/dim]")
    elif name == "model_downloaded":
        mb = int(event.get("bytes", 0)) // (1024 * 1024)
        console.print(f"[green]• Model downloaded ({mb} MB).[/green]")
    elif name == "deleting_models":
        console.print("[dim]• Deleting cached models…[/dim]")
    elif name == "uninstalling_package":
        console.print("[dim]• Uninstalling the local engines…[/dim]")
    elif name == "done":
        pass


@local_app.command("setup")
def local_setup(
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help=f"Model to install. Required. Recommended: [bold]{RECOMMENDED_MODEL}[/bold]. "
        f"Choices: {', '.join(MODEL_SIZES)}.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt. Required in non-TTY (agent) contexts.",
    ),
    output_json: bool = typer.Option(
        False, "--json", "-j", help="Stream NDJSON progress events to stdout."
    ),
) -> None:
    """[bold]Install[/bold] the local engines and download a model.

    Idempotent — re-running with the same model is a no-op (updates the
    default-model setting). A Parakeet model also downloads Whisper Tiny
    (~75 MB), the language-check helper.

    [dim]The CLI never picks a model silently; --model is required every
    time. Recommended: parakeet-v3 (English and 24 European languages);
    large-v3-turbo for Hindi and other languages.[/dim]
    """
    if model is None:
        err = {
            "error": "--model is required",
            "recommended": RECOMMENDED_MODEL,
            "choices": list(MODEL_SIZES),
        }
        if output_json:
            json.dump(err, sys.stderr)
            sys.stderr.write("\n")
        else:
            err_console.print(
                f"[red]Must specify --model.[/red] Recommended: [bold]{RECOMMENDED_MODEL}[/bold]. "
                f"Choices: {', '.join(MODEL_SIZES)}."
            )
        raise typer.Exit(code=2)

    if model not in MODEL_SIZES:
        err = {"error": f"unknown model '{model}'", "choices": list(MODEL_SIZES)}
        if output_json:
            json.dump(err, sys.stderr)
            sys.stderr.write("\n")
        else:
            err_console.print(
                f"[red]Unknown model '{model}'.[/red] Choices: {', '.join(MODEL_SIZES)}."
            )
        raise typer.Exit(code=2)

    is_tty = sys.stdin.isatty() and sys.stdout.isatty()
    if not is_tty and not yes:
        err = {"error": "refusing to setup without --yes in non-TTY"}
        if output_json:
            json.dump(err, sys.stderr)
            sys.stderr.write("\n")
        else:
            err_console.print("[red]Non-interactive run — pass --yes to confirm the install.[/red]")
        raise typer.Exit(code=2)

    if is_tty and not yes:
        spec = MODEL_SPECS[model]
        mb = spec["download_mb"]
        if engine_of(model) == "parakeet":
            mb += MODEL_SPECS[LANGUAGE_CHECK_MODEL]["download_mb"]
        if not typer.confirm(
            f"Install the local engines and download {spec['display_name']} (~{mb} MB)?",
            default=True,
        ):
            if output_json:
                _emit_event({"status": "cancelled"})
            else:
                console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=0)

    status = check_status()
    if status["runtime_ready"] and any(
        m["size"] == model and m["runnable"] for m in status["models"]
    ):
        # Already fully set up for this size — just persist default and exit.
        from anyscribe.config.settings import CONFIG_LOCK, load_config, save_config

        with CONFIG_LOCK:
            settings = load_config()
            if settings.local_model != model:
                settings.local_model = model
                save_config(settings)
        tip = use_local_tip()
        payload = {
            "status": "already_set_up",
            "default_model": model,
            "size": model,
            "use_local_tip": tip,
        }
        if output_json:
            _emit_event(payload)
        else:
            console.print(
                f"[green]Already set up.[/green] Default model is now [bold]{model}[/bold]."
            )
            if tip:
                console.print(tip)
        return

    progress_fn = _emit_event if output_json else _human_phase
    result = run_setup(model, on_progress=progress_fn)

    if result["status"] == "failed":
        if output_json:
            _emit_event({"status": "failed", **result})
        else:
            phase = result.get("phase", "?")
            err_console.print(f"[red]Setup failed during {phase}.[/red]")
            if phase == "install":
                cmd = result["install"].get("command") or []
                err_console.print(f"  Command: [dim]{' '.join(cmd)}[/dim]")
                stderr_msg = result["install"].get("stderr") or ""
                if stderr_msg:
                    err_console.print(f"  stderr: [dim]{stderr_msg[:500]}[/dim]")
            else:
                err_console.print(f"  Error: [dim]{result.get('error', '')}[/dim]")
        raise typer.Exit(code=1)

    tip = use_local_tip()
    if output_json:
        _emit_event({"status": "set_up", **result, "use_local_tip": tip})
    else:
        console.print(
            "\n[bold green]Local transcription ready.[/bold green] Default model: "
            f"[bold]{MODEL_SPECS[model]['display_name']}[/bold]."
        )
        if result.get("restart_needed"):
            console.print(
                f"[yellow]{RESTART_MESSAGE}[/yellow] (Stop any running anyscribe ui first.)"
            )
        if tip:
            console.print(tip)


@local_app.command("status")
def local_status(
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]Report[/bold] the state of local transcription.

    Always exits 0; ``set_up: false`` when the engines aren't installed yet.
    """
    status = check_status()
    if output_json:
        # "Help me choose" for agents: the pick for every answer to the one question
        from anyscribe.core.local_recommend import LANGUAGE_ANSWERS, detect_hardware, recommend

        hw = detect_hardware()
        cached = {m["size"] for m in status["models"] if m["cached"]}
        status["question"] = "What language is most of your audio?"
        status["recommendations"] = {
            a: {k: v for k, v in recommend(a, hw, cached).items() if k != "hardware"}
            for a in LANGUAGE_ANSWERS
        }
        status["hardware"] = hw
        json.dump(status, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return

    table = Table(title="Local transcription")
    table.add_column("Check", style="bold")
    table.add_column("Value")

    table.add_row("Set up", "[green]yes[/green]" if status["set_up"] else "[yellow]no[/yellow]")
    table.add_row(
        "faster-whisper",
        f"[green]{status['faster_whisper_version']}[/green]"
        if status["faster_whisper_installed"]
        else "[red]not installed[/red]",
    )
    table.add_row(
        "ffmpeg",
        f"[green]{status['ffmpeg_message']}[/green]"
        if status["ffmpeg_ok"]
        else f"[red]{status['ffmpeg_message']}[/red]",
    )
    table.add_row(
        "onnx-asr (Parakeet)",
        "[green]installed[/green]" if status["onnx_asr_installed"] else "[red]not installed[/red]",
    )
    table.add_row("Default model", status["default_model"])
    table.add_row("Install method", status["install_method"])
    total_mb = status["total_disk_bytes"] // (1024 * 1024)
    table.add_row("Cache on disk", f"{total_mb} MB")
    console.print(table)

    from anyscribe.cli.models_cmd import models_table

    console.print(models_table(status["models"], status["default_model"]))
    if status.get("suggestion"):
        console.print(f"[dim]{status['suggestion']}[/dim]")


@local_app.command("teardown")
def local_teardown(
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the confirmation prompt (required when there is no terminal).",
    ),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]Remove[/bold] local transcription — uninstalls the engines and deletes all cached models."""
    is_tty = sys.stdin.isatty() and sys.stdout.isatty()
    if not yes:
        if not is_tty:
            err = {"error": "refusing to teardown without --yes"}
            if output_json:
                json.dump(err, sys.stderr)
                sys.stderr.write("\n")
            else:
                err_console.print("[red]Non-interactive run — pass --yes to confirm.[/red]")
            raise typer.Exit(code=2)
        if not typer.confirm(
            "Uninstall the local engines and delete all cached models?", default=False
        ):
            if output_json:
                _emit_event({"status": "cancelled"})
            else:
                console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=0)

    progress_fn = _emit_event if output_json else _human_phase
    result = run_teardown(on_progress=progress_fn)

    if output_json:
        _emit_event(result)
    else:
        mb = result["bytes_freed"] // (1024 * 1024)
        console.print(
            f"\n[bold green]Removed.[/bold green] Freed {mb} MB. "
            f"Deleted: {', '.join(result['models_deleted']) or 'no cached models'}."
        )
        if result["provider_reset"]:
            console.print("[dim]Default provider reset to openai.[/dim]")
