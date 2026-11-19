"""``anyscribe model`` — day-to-day local model cache management.

These commands operate on the HuggingFace cache directly. They never
uninstall the engines — that's ``anyscribe local teardown``'s job. ``pull``
installs the missing engine first when needed (an install from before
Parakeet has faster-whisper but not onnx-asr). If local transcription isn't
set up, rm/reinstall error cleanly and point at the right command; list
still works (showing everything as not-cached).

All commands support ``--json`` for agent consumption.
"""

from __future__ import annotations

import json
import sys

import typer
from rich.console import Console
from rich.table import Table

from anyscribe.config.settings import load_config
from anyscribe.providers.local_models import (
    MODEL_REPOS,
    MODEL_SIZES,
    BENCHMARK_CAPTION,
    MODEL_SPECS,
    RECOMMENDED_MODEL,
    bytes_on_disk,
    delete_model,
    display_name,
    engine_importable,
    engine_of,
    faster_whisper_importable,
    is_cached,
    list_cached_models,
    pull_model,
    validate_size,
)

console = Console()
err_console = Console(stderr=True)

models_app = typer.Typer(
    name="model",
    help="List, download, and delete local transcription models (Parakeet, Whisper).",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def _write_json(data) -> None:
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


def _write_json_err(data) -> None:
    json.dump(data, sys.stderr)
    sys.stderr.write("\n")


@models_app.command("list")
def model_list(
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]List[/bold] all local models with ratings, cache status and disk usage."""
    settings = load_config()
    models = list_cached_models()

    if output_json:
        payload = [
            {
                "size": m["size"],
                "cached": m["cached"],
                "partial": m.get("partial", False),
                "bytes": m["bytes"],
                "repo": m["repo"],
                "default": m["size"] == settings.local_model,
                "recommended": m["size"] == RECOMMENDED_MODEL,
                "spec": m["spec"],
            }
            for m in models
        ]
        _write_json(payload)
        if not faster_whisper_importable():
            err_console.print("hint: faster-whisper not installed — run `anyscribe local setup`")
        return

    console.print(models_table(models, settings.local_model))
    if not faster_whisper_importable():
        console.print(
            "\n[yellow]Local transcription is not set up.[/yellow] "
            f"Run [bold]anyscribe local setup --model {RECOMMENDED_MODEL}[/bold] to install."
        )


def models_table(models: list[dict], default: str, title: str = "Local models") -> Table:
    """The shared model table for ``model list`` and ``local status``."""
    table = Table(title=title)
    table.add_column("Model", style="bold")
    table.add_column("Id", style="dim")
    table.add_column("Accuracy", justify="right")
    table.add_column("Speed", justify="right")
    table.add_column("1 h audio", justify="right")
    table.add_column("Download", justify="right")
    table.add_column("Status")
    for m in models:
        spec = m["spec"]
        marks = []
        if m["size"] == default:
            marks.append("[green]default[/green]")
        if m["size"] == RECOMMENDED_MODEL:
            marks.append("[yellow]recommended[/yellow]")
        cached_mb = int(m["bytes"]) // (1024 * 1024)
        if m["cached"]:
            status = f"downloaded ({cached_mb} MB)"
        elif m.get("partial"):
            status = (
                f"[yellow]incomplete ({cached_mb} MB): anyscribe model pull {m['size']}[/yellow]"
            )
        else:
            status = "[dim]not downloaded[/dim]"
        table.add_row(
            display_name(m["size"]) + (" · " + ", ".join(marks) if marks else ""),
            m["size"],
            f"{spec['accuracy']}/5",
            f"{spec['speed']}/5",
            f"~{spec['min_per_hour']} min",
            f"~{spec['download_mb']} MB",
            status,
        )
    table.caption = f"{BENCHMARK_CAPTION} `anyscribe model info <id>` explains each one."
    return table


@models_app.command("pull")
def model_pull(
    size: str = typer.Argument(..., help="Model size to download."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]Download[/bold] a local model to the cache. Idempotent.

    A Parakeet model also fetches Whisper Tiny (~75 MB), the language-check helper.
    """
    if size not in MODEL_SIZES:
        err = {"error": f"unknown size '{size}'", "choices": list(MODEL_SIZES)}
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(
                f"[red]Unknown size '{size}'.[/red] Choices: {', '.join(MODEL_SIZES)}."
            )
        raise typer.Exit(code=2)

    if not faster_whisper_importable():
        err = {
            "error": "local transcription not set up",
            "hint": f"run `anyscribe local setup --model {size}`",
        }
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(
                "[red]faster-whisper not installed.[/red] "
                f"Run [bold]anyscribe local setup --model {size}[/bold] first."
            )
        raise typer.Exit(code=2)

    if engine_of(size) == "parakeet" and not engine_importable(size):
        # set up before Parakeet existed: add onnx-asr now, on first pick
        from anyscribe.core.local_setup import ensure_runtime

        if not output_json:
            console.print("[dim]• Installing the Parakeet engine (onnx-asr)…[/dim]")
        failed = ensure_runtime()
        if failed:
            err = {"error": "engine install failed", "install": failed}
            if output_json:
                _write_json_err(err)
            else:
                err_console.print(
                    f"[red]Engine install failed.[/red] Command: {' '.join(failed['command'])}"
                )
            raise typer.Exit(code=1)

    try:
        result = pull_model(size)
    except Exception as e:
        err = {"error": str(e)}
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(f"[red]Download failed:[/red] {e}")
        raise typer.Exit(code=1)

    if output_json:
        _write_json(result)
    else:
        mb = int(result.get("bytes", 0)) // (1024 * 1024)
        if result["status"] == "already_present":
            console.print(f"[green]{size} already cached[/green] ({mb} MB).")
        else:
            console.print(f"[green]Downloaded {size}[/green] ({mb} MB).")
        if result.get("helpers_downloaded"):
            console.print(
                "[dim]Also downloaded Whisper Tiny (~75 MB): the language check that "
                "keeps Parakeet away from languages it can't transcribe.[/dim]"
            )


@models_app.command("rm")
def model_rm(
    size: str = typer.Argument(..., help="Model size to delete from the cache."),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the confirmation prompt (required when there is no terminal).",
    ),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]Remove[/bold] a cached local model from disk."""
    if size not in MODEL_SIZES:
        err = {"error": f"unknown size '{size}'", "choices": list(MODEL_SIZES)}
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(
                f"[red]Unknown size '{size}'.[/red] Choices: {', '.join(MODEL_SIZES)}."
            )
        raise typer.Exit(code=2)

    if not bytes_on_disk(size):  # a partial download can be removed too
        payload = {"status": "not_present", "size": size, "bytes_freed": 0}
        if output_json:
            _write_json(payload)
        else:
            console.print(f"[dim]{size} is not cached — nothing to remove.[/dim]")
        return

    is_tty = sys.stdin.isatty() and sys.stdout.isatty()
    if not yes:
        if not is_tty:
            err = {"error": "refusing to remove without --yes"}
            if output_json:
                _write_json_err(err)
            else:
                err_console.print("[red]Non-interactive run — pass --yes to confirm.[/red]")
            raise typer.Exit(code=2)
        if not typer.confirm(f"Delete cached {size} model?", default=False):
            if output_json:
                _write_json({"status": "cancelled", "size": size})
            else:
                console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=0)

    result = delete_model(size)
    if output_json:
        _write_json(result)
    else:
        mb = int(result["bytes_freed"]) // (1024 * 1024)
        console.print(f"[green]Removed {size}[/green] — freed {mb} MB.")


@models_app.command("reinstall")
def model_reinstall(
    size: str = typer.Argument(..., help="Model size to reinstall."),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the confirmation prompt (required when there is no terminal).",
    ),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]Reinstall[/bold] a local model — delete + re-download in one step.

    Useful if cached weights look corrupted. If the model wasn't cached, this
    is equivalent to ``anyscribe model pull`` (no delete needed).
    """
    if size not in MODEL_SIZES:
        err = {"error": f"unknown size '{size}'", "choices": list(MODEL_SIZES)}
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(
                f"[red]Unknown size '{size}'.[/red] Choices: {', '.join(MODEL_SIZES)}."
            )
        raise typer.Exit(code=2)

    if not faster_whisper_importable():
        err = {
            "error": "local transcription not set up",
            "hint": f"run `anyscribe local setup --model {size}`",
        }
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(
                "[red]faster-whisper not installed.[/red] "
                f"Run [bold]anyscribe local setup --model {size}[/bold] first."
            )
        raise typer.Exit(code=2)

    is_tty = sys.stdin.isatty() and sys.stdout.isatty()
    if not yes:
        if not is_tty:
            err = {"error": "refusing to reinstall without --yes"}
            if output_json:
                _write_json_err(err)
            else:
                err_console.print("[red]Non-interactive run — pass --yes to confirm.[/red]")
            raise typer.Exit(code=2)
        if not typer.confirm(f"Delete and re-download {size} model?", default=False):
            if output_json:
                _write_json({"status": "cancelled", "size": size})
            else:
                console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=0)

    bytes_freed = 0
    if bytes_on_disk(size):
        delete_result = delete_model(size)
        bytes_freed = int(delete_result.get("bytes_freed", 0))

    try:
        pull_result = pull_model(size)
    except Exception as e:
        err = {"error": str(e), "bytes_freed": bytes_freed}
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(f"[red]Reinstall failed:[/red] {e}")
        raise typer.Exit(code=1)

    bytes_downloaded = int(pull_result.get("bytes", 0))
    if bytes_freed > 0:
        status = "reinstalled"
    else:
        status = "downloaded_only"

    payload = {
        "status": status,
        "size": size,
        "bytes_freed": bytes_freed,
        "bytes_downloaded": bytes_downloaded,
    }

    if output_json:
        _write_json(payload)
    else:
        freed_mb = bytes_freed // (1024 * 1024)
        dl_mb = bytes_downloaded // (1024 * 1024)
        if status == "reinstalled":
            console.print(
                f"[green]Reinstalled {size}[/green] — freed {freed_mb} MB, downloaded {dl_mb} MB."
            )
        else:
            console.print(
                f"[green]Installed {size}[/green] — downloaded {dl_mb} MB. "
                "(Wasn't previously cached; no delete needed.)"
            )


@models_app.command("info")
def model_info(
    size: str = typer.Argument(..., help="Model size to inspect."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]Inspect[/bold] a single local model."""
    try:
        validate_size(size)
    except ValueError as e:
        err = {"error": str(e), "choices": list(MODEL_SIZES)}
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2)

    cached = is_cached(size)
    on_disk = bytes_on_disk(size)

    settings = load_config()
    payload = {
        "size": size,
        "cached": cached,
        "partial": bool(on_disk) and not cached,
        "bytes": on_disk,
        "repo": MODEL_REPOS[size],
        "default": size == settings.local_model,
        "spec": MODEL_SPECS[size],
    }
    if output_json:
        _write_json(payload)
    else:
        spec = payload["spec"]
        console.print(f"[bold]{spec['display_name']}[/bold] [dim]({size})[/dim]")
        console.print(f"  For:       {spec['use_for']}")
        console.print(f"  Languages: {spec['languages']}")
        console.print(f"  Accuracy:  {spec['accuracy']}/5  (English word error {spec['en_wer']}%)")
        console.print(
            f"  Speed:     {spec['speed']}/5  (1 hour of audio ≈ {spec['min_per_hour']} min)"
        )
        console.print(f"  Download:  ~{spec['download_mb']} MB")
        console.print(f"  Memory:    ~{spec['ram_mb']} MB while transcribing")
        if spec["tucked"]:
            console.print(f"  Note:      {spec['tucked']}")
        console.print(f"  Repo:      [cyan]{payload['repo']}[/cyan]")
        state = "downloaded" if cached else "incomplete" if payload["partial"] else "not downloaded"
        console.print(f"  Status:    {state}")
        if on_disk:
            console.print(f"  Disk:      {on_disk // (1024 * 1024)} MB")
        if payload["partial"]:
            console.print(f"  [yellow]Resume the download: anyscribe model pull {size}[/yellow]")
        if payload["default"]:
            console.print("  [green]This is the default model.[/green]")
