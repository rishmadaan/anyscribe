"""Unified setup + teardown for local transcription.

Local transcription needs two things on disk before it can run:

1. The engines (``faster-whisper`` for Whisper, ``onnx-asr`` for Parakeet)
   installed into the same Python environment as ``anyscribe``.
2. At least one model downloaded into the HuggingFace cache.

This module detects how ``anyscribe`` itself was installed (pipx / venv pip /
system pip, or uv when the venv has no pip) and runs the appropriate
subprocess to add the engines, then pulls the requested model. The same routine powers the CLI (``anyscribe local
setup``), the onboarding wizard, and the Web UI "Set up local transcription"
button — one code path, consistent behaviour.

Never raises on subprocess failure — callers get a structured dict with the
exact command that ran and the captured stderr so they (or an agent) can
resolve it manually.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Literal

from anyscribe.config.settings import CONFIG_LOCK, load_config, save_config
from anyscribe.core.appmode import is_app
from anyscribe.core.deps import check_dependencies
from anyscribe.providers.local_models import (
    any_model_runnable,
    delete_all_models,
    faster_whisper_importable,
    faster_whisper_version,
    list_cached_models,
    onnx_asr_importable,
    pull_model,
    validate_size,
)

FASTER_WHISPER_SPEC = "faster-whisper>=1.0"
# shortcut: faster-whisper 1.2.1 breaks on PyAV 19; drop once a faster-whisper
# release includes SYSTRAN/faster-whisper#1495
AV_SPEC = "av<19"
ONNX_ASR_SPEC = "onnx-asr>=0.12.0"  # Parakeet engine; floor = the version tested
# Everything `local setup` installs. Keep in step with pyproject's `local` extra.
LOCAL_RUNTIME_SPECS = [FASTER_WHISPER_SPEC, AV_SPEC, ONNX_ASR_SPEC]
# What teardown removes (av stays: other packages may use it).
LOCAL_RUNTIME_PACKAGES = ["faster-whisper", "onnx-asr"]

InstallMethod = Literal["app", "pipx", "venv", "system", "uv", "unknown"]

# Engine modules this process may already have imported, by distribution.
# Replacing one on disk doesn't replace the loaded copy (Python keeps it), so
# the running process must restart to use the new one.
ENGINE_MODULES = {"av": "av", "faster_whisper": "faster-whisper", "onnx_asr": "onnx-asr"}
RESTART_MESSAGE = "Restart anyscribe to finish setting up local transcription."
USE_LOCAL_TIP = (
    "To use it for every transcript: `anyscribe config set quality free` "
    "(or pick 'free' under What runs by default)."
)
# The web shows no terminal command (R4F1): say plainly that setup didn't switch.
USE_LOCAL_TIP_WEB = (
    "New transcripts still go to {provider}. To transcribe on this computer "
    "instead, pick 'free' under What runs by default."
)
_restart_needed = False


def restart_needed() -> bool:
    """True once this process replaced an engine package it had already loaded."""
    return _restart_needed


def _engine_versions() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for dist in ENGINE_MODULES.values():
        try:
            out[dist] = importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            out[dist] = None
    return out


ProgressFn = Callable[[dict[str, Any]], None]


def _emit(on_progress: ProgressFn | None, event: dict[str, Any]) -> None:
    if on_progress is not None:
        try:
            on_progress(event)
        except Exception:
            pass


def detect_install_method() -> InstallMethod:
    """Figure out how anyscribe itself was installed.

    The detection drives which command we shell out to when adding or removing
    faster-whisper. Order matters: the Mac app first (its own Python, whose pip
    writes to the add-ons folder via PIP_USER/PYTHONUSERBASE); pipx lives inside
    its own venv, so we have to check the pipx markers before the generic venv heuristic.
    """
    if is_app():
        return "app"
    exe = Path(sys.executable).resolve()

    pipx_home = os.environ.get("PIPX_HOME")
    pipx_default = Path.home() / ".local" / "pipx"
    pipx_roots = [Path(p) for p in [pipx_home, str(pipx_default)] if p]
    for root in pipx_roots:
        try:
            if root.exists() and str(exe).startswith(str(root.resolve())):
                return "pipx"
        except OSError:
            continue

    # Generic venv check: prefix differs from base_prefix in venvs/virtualenvs.
    if getattr(sys, "prefix", None) and getattr(sys, "base_prefix", None):
        if sys.prefix != sys.base_prefix:
            return "venv"

    # System Python (Homebrew, OS package, etc.). pip may be blocked by PEP 668.
    return "system"


def _pipx_venv_name() -> str | None:
    """Return the pipx venv name that owns the current Python, if detectable."""
    exe = Path(sys.executable).resolve()
    for parent in exe.parents:
        if parent.parent.name == "venvs" and parent.parent.parent.name == "pipx":
            return parent.name
    return None


def _pip_available() -> bool:
    return importlib.util.find_spec("pip") is not None


def _pip_command(action: str, packages: list[str]) -> tuple[list[str], InstallMethod | None]:
    """pip argv for the running interpreter. A venv made by ``uv tool install``
    has no pip, so fall back to ``uv pip --python <this interpreter>`` when uv is
    on PATH. Returns ``(argv, "uv")`` when that fallback is used, else ``(argv, None)``."""
    extra = ["-y"] if action == "uninstall" else []
    # The Mac app keeps its own pip: PIP_USER/PYTHONUSERBASE send it to the add-ons folder.
    if not is_app() and not _pip_available() and shutil.which("uv"):
        return ["uv", "pip", action, "--python", sys.executable, *packages], "uv"
    return [sys.executable, "-m", "pip", action, *extra, *packages], None


def _install_command(method: InstallMethod) -> list[str]:
    """Build the argv list to install the local engines for the given method."""
    if method == "pipx":
        venv = _pipx_venv_name() or "anyscribe"
        return ["pipx", "inject", venv, *LOCAL_RUNTIME_SPECS]
    return _pip_command("install", LOCAL_RUNTIME_SPECS)[0]


def _uninstall_command(method: InstallMethod) -> list[str]:
    if method == "pipx":
        venv = _pipx_venv_name() or "anyscribe"
        return ["pipx", "uninject", venv, *LOCAL_RUNTIME_PACKAGES]
    return _pip_command("uninstall", LOCAL_RUNTIME_PACKAGES)[0]


def _av_too_new() -> bool:
    """True when the installed PyAV is 19+, which faster-whisper 1.2.1 can't open files with."""
    try:
        major = importlib.metadata.version("av").split(".")[0]
        return int(major) >= 19
    except (importlib.metadata.PackageNotFoundError, ValueError):
        return False


def local_runtime_ready() -> bool:
    """Both engines import and PyAV is a version faster-whisper can use."""
    return faster_whisper_importable() and onnx_asr_importable() and not _av_too_new()


def _run(cmd: list[str], timeout: int = 600) -> tuple[int, str, str]:
    """Run ``cmd`` with captured stdout/stderr. Never raises on nonzero."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except (FileNotFoundError, PermissionError) as e:
        return 127, "", str(e)
    except subprocess.TimeoutExpired as e:
        return 124, "", f"timed out after {timeout}s: {e}"


def install_faster_whisper(
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """Install the local engines (faster-whisper, onnx-asr, a compatible PyAV)
    into the running Python environment. Idempotent: a no-op when
    ``local_runtime_ready()``; an older install missing onnx-asr, or carrying
    PyAV 19, gets the missing pieces.

    Returns ``{status, method, command, version?, stderr?}``. ``status`` is
    one of ``"already_installed" | "installed" | "failed"``.
    """
    if local_runtime_ready():
        return {
            "status": "already_installed",
            "method": detect_install_method(),
            "command": None,
            "version": faster_whisper_version(),
        }

    method = detect_install_method()
    cmd = _install_command(method)

    # Guard against pipx missing on PATH in the pipx branch — fall back to pip.
    if method == "pipx" and shutil.which("pipx") is None:
        cmd = _pip_command("install", LOCAL_RUNTIME_SPECS)[0]
        method = "venv"
        _emit(on_progress, {"event": "pipx_not_on_path_fallback", "command": cmd})
    if cmd[0] == "uv":
        method = "uv"

    _emit(on_progress, {"event": "installing_package", "method": method, "command": cmd})

    before = _engine_versions()
    rc, _, stderr = _run(cmd)
    if rc != 0:
        return {
            "status": "failed",
            "method": method,
            "command": cmd,
            "stderr": stderr.strip(),
        }

    importlib.invalidate_caches()  # let this process import what the subprocess just added
    after = _engine_versions()
    replaced = [
        mod
        for mod, dist in ENGINE_MODULES.items()
        if mod in sys.modules and after[dist] != before[dist]
    ]
    if replaced:
        global _restart_needed
        _restart_needed = True
    _emit(on_progress, {"event": "package_installed", "method": method})

    return {
        "status": "installed",
        "method": method,
        "command": cmd,
        "version": faster_whisper_version(),
        "restart_needed": bool(replaced),
    }


def ensure_runtime(on_progress: ProgressFn | None = None) -> dict[str, Any] | None:
    """Install the engines if anything is missing; return the failed install
    result, or None when the runtime is ready. Used before pulling a model so
    an older install that predates Parakeet gets onnx-asr on first pick."""
    result = install_faster_whisper(on_progress=on_progress)
    return result if result["status"] == "failed" else None


def uninstall_faster_whisper(
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """Remove the local engines. Returns ``{status, method, command, stderr?}``."""
    if not faster_whisper_importable() and not onnx_asr_importable():
        return {
            "status": "already_absent",
            "method": detect_install_method(),
            "command": None,
        }

    method = detect_install_method()
    cmd = _uninstall_command(method)

    if method == "pipx" and shutil.which("pipx") is None:
        cmd = _pip_command("uninstall", LOCAL_RUNTIME_PACKAGES)[0]
        method = "venv"
    if cmd[0] == "uv":
        method = "uv"

    _emit(on_progress, {"event": "uninstalling_package", "method": method, "command": cmd})

    rc, _, stderr = _run(cmd)
    if rc != 0:
        return {
            "status": "failed",
            "method": method,
            "command": cmd,
            "stderr": stderr.strip(),
        }
    return {"status": "removed", "method": method, "command": cmd}


def _ffmpeg_status() -> dict[str, Any]:
    """Return ``{ok, message}`` for ffmpeg using the existing deps check."""
    results = check_dependencies()
    for r in results:
        if r.dep.name == "ffmpeg":
            return {
                "ok": bool(r.found),
                "message": (r.version or "ffmpeg found") if r.found else "ffmpeg not found on PATH",
            }
    return {"ok": False, "message": "ffmpeg not found on PATH"}


def check_status(web: bool = False) -> dict[str, Any]:
    """Snapshot of everything local-transcription-related on this machine.

    Safe to call before setup — faster_whisper_installed will just be False
    and models will all be uncached.
    """
    from anyscribe.core.local_recommend import parakeet_suggestion
    from anyscribe.providers.local_models import RECOMMENDED_MODEL

    settings = load_config()
    fw_ok = faster_whisper_importable()
    models = list_cached_models()
    total_bytes = sum(int(m["bytes"]) for m in models)
    ffmpeg = _ffmpeg_status()

    return {
        "set_up": fw_ok and ffmpeg["ok"] and any(m["runnable"] for m in models),
        "faster_whisper_installed": fw_ok,
        "faster_whisper_version": faster_whisper_version(),
        "onnx_asr_installed": onnx_asr_importable(),
        "runtime_ready": local_runtime_ready(),
        "restart_needed": restart_needed(),
        "recommended_model": RECOMMENDED_MODEL,
        "suggestion": parakeet_suggestion(settings.local_model, settings.language, web=web),
        "ffmpeg_ok": ffmpeg["ok"],
        "ffmpeg_message": ffmpeg["message"],
        "default_model": settings.local_model,
        "use_local_tip": use_local_tip(web=web),
        "models": [
            {
                "size": m["size"],
                "cached": m["cached"],
                "partial": m["partial"],
                "runnable": m["runnable"],
                "bytes": m["bytes"],
                "repo": m["repo"],
                "spec": m["spec"],
            }
            for m in models
        ],
        "total_disk_bytes": total_bytes,
        "install_method": detect_install_method(),
    }


def use_local_tip(web: bool = False) -> str | None:
    """USE_LOCAL_TIP when the next run would not transcribe locally (setup
    never changes the provider), else None."""
    from anyscribe.config.settings import load_env
    from anyscribe.core.resolve import resolve_run

    load_env()
    try:
        provider = resolve_run(load_config()).provider
        if provider == "local":
            return None
        return USE_LOCAL_TIP_WEB.format(provider=provider) if web else USE_LOCAL_TIP
    except ValueError:  # a hand-broken provider: the plan's own error says what to fix
        return None


def run_setup(
    model_size: str,
    on_progress: ProgressFn | None = None,
    activate: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """The unified setup routine: install + pull + persist.

    Does NOT change ``settings.provider`` — setup prepares local; swapping the
    default provider stays with the user.

    ``activate`` (the web server's) makes the switch and returns None when a
    newer choice was made meanwhile: the default is left alone and the status
    is "superseded". Without it (CLI) the switch is a plain ``set_value``.
    """
    validate_size(model_size)

    _emit(on_progress, {"event": "detecting_install_method"})

    install_result = install_faster_whisper(on_progress=on_progress)
    if install_result["status"] == "failed":
        return {
            "status": "failed",
            "phase": "install",
            "install": install_result,
        }

    _emit(on_progress, {"event": "downloading_model", "size": model_size})

    def _dl_progress(downloaded: int, total: int) -> None:
        _emit(
            on_progress,
            {
                "event": "download_progress",
                "size": model_size,
                "downloaded": downloaded,
                "total": total,
            },
        )

    try:
        pull_result = pull_model(model_size, progress_cb=_dl_progress)
    except Exception as e:
        return {
            "status": "failed",
            "phase": "download",
            "install": install_result,
            "error": str(e),
        }

    _emit(
        on_progress,
        {"event": "model_downloaded", "size": model_size, "bytes": pull_result.get("bytes", 0)},
    )

    # The one guarded switch: refuses a model that still can't run.
    from anyscribe.core.config_set import set_value

    switched = (activate or (lambda m: set_value("local_model", m)))(model_size)
    if switched is None:
        _emit(on_progress, {"event": "superseded"})
        return {
            "status": "superseded",
            "install": install_result,
            "model": pull_result,
            "default_model": load_config().local_model,
            "restart_needed": bool(install_result.get("restart_needed")),
        }
    if not switched.ok:
        return {
            "status": "failed",
            "phase": "download",
            "install": install_result,
            "error": switched.error,
        }

    _emit(on_progress, {"event": "done"})

    return {
        "status": "set_up",
        "install": install_result,
        "model": pull_result,
        "default_model": model_size,
        "restart_needed": bool(install_result.get("restart_needed")),
    }


def run_teardown(on_progress: ProgressFn | None = None) -> dict[str, Any]:
    """Uninstall faster-whisper, delete all cached models, reset provider.

    ``settings.local_model`` is preserved — it's harmless and re-used if the
    user sets up again later. ``settings.provider`` flips to ``"openai"`` only
    if it was currently ``"local"``, so the user isn't left with a broken
    default.
    """
    _emit(on_progress, {"event": "deleting_models"})
    deleted = delete_all_models()

    _emit(on_progress, {"event": "uninstalling_package"})
    uninstall = uninstall_faster_whisper(on_progress=on_progress)

    provider_changed = False
    with CONFIG_LOCK:
        settings = load_config()
        if settings.provider == "local" or settings.quality == "free":
            # quality: free resolves to local, so leaving the tier in place would
            # keep routing every run to the provider we just uninstalled. Flip both
            # halves of the knob (provider + quality=custom, same invariant as
            # config_set) so the reset actually takes effect.
            if settings.provider == "local":
                settings.provider = "openai"
            settings.quality = "custom"
            provider_changed = True
            save_config(settings)

    _emit(on_progress, {"event": "done"})

    return {
        "status": "removed",
        "models_deleted": deleted["models_deleted"],
        "bytes_freed": deleted["bytes_freed"],
        "uninstall": uninstall,
        "provider_reset": provider_changed,
    }


def local_ready() -> bool:
    """Quick predicate for the Web UI green-dot check.

    ``True`` when faster-whisper imports, ffmpeg is on PATH, and at least one
    model is runnable. Used by the providers list endpoint.
    """
    if not faster_whisper_importable():
        return False
    if not _ffmpeg_status()["ok"]:
        return False
    return any_model_runnable()
