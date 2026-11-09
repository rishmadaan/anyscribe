"""Local Whisper model vocabulary and on-disk cache management.

Single source of truth for the sizes the user can pick and the HuggingFace
repos they map to. Wraps ``huggingface_hub`` for list/download/delete so the
rest of the codebase never has to touch the HF cache layout directly.

These helpers are safe to import before ``faster-whisper`` is installed:
``list_cached_models()`` returns ``[]`` and ``is_cached()`` returns ``False``
when the hub library isn't available, so status UIs can render a "not set up"
state without crashing.
"""

from __future__ import annotations

import threading
from typing import Any, Callable

MODEL_SIZES: list[str] = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3",
    "large-v3-turbo",
    "distil-large-v3.5",
]

RECOMMENDED_MODEL: str = "base"

# faster-whisper loads these HF repos directly. Keep the keys in lockstep with
# MODEL_SIZES; the size string is also what we accept on the CLI and store
# in settings.local_model.
MODEL_REPOS: dict[str, str] = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large-v3-turbo": "dropbox-dash/faster-whisper-large-v3-turbo",
    "distil-large-v3.5": "distil-whisper/distil-large-v3.5-ct2",
}

# Approximate figures used by the UI (CLI + Web) to help the user pick a size.
# ``use_for`` completes the sentence "Use it for ..." shown under each size.
# Download sizes are what HF reports for the int8 CTranslate2 weights; RAM
# numbers are typical peak usage during transcription on CPU.
MODEL_SPECS: dict[str, dict[str, Any]] = {
    "tiny": {
        "download_mb": 75,
        "ram_mb": 400,
        "relative_speed": "~10x realtime (CPU)",
        "quality": "lowest",
        "use_for": "quick rough drafts on an old or slow computer",
    },
    "base": {
        "download_mb": 145,
        "ram_mb": 600,
        "relative_speed": "~7x realtime (CPU)",
        "quality": "good for most use cases",
        "use_for": "everyday podcasts, interviews and talks with clear audio. Start here",
    },
    "small": {
        "download_mb": 480,
        "ram_mb": 1200,
        "relative_speed": "~4x realtime (CPU)",
        "quality": "noticeably better than base",
        "use_for": "accents, background noise or jargon that base gets wrong",
    },
    "medium": {
        "download_mb": 1500,
        "ram_mb": 2500,
        "relative_speed": "~2x realtime (CPU)",
        "quality": "near-large for many languages",
        "use_for": "non-English audio, if you can wait longer",
    },
    "large-v3": {
        "download_mb": 3000,
        "ram_mb": 5000,
        "relative_speed": "~1x realtime (CPU); fast on GPU",
        "quality": "highest",
        "use_for": "the most accurate transcript, on a computer with a graphics card (GPU)",
    },
    "large-v3-turbo": {
        "download_mb": 1600,
        "ram_mb": 3000,
        "relative_speed": "~6x realtime (CPU)",
        "quality": "near large-v3, much faster",
        "use_for": "near-best accuracy at good speed, if you have 4 GB of memory to spare",
    },
    "distil-large-v3.5": {
        "download_mb": 1500,
        "ram_mb": 2800,
        "relative_speed": "~6x realtime (CPU)",
        "quality": "near large-v3 for English; weaker multilingual",
        "use_for": "English-only audio where you want near-best accuracy, fast",
    },
}


def validate_size(size: str) -> None:
    """Raise ValueError if ``size`` isn't one of MODEL_SIZES."""
    if size not in MODEL_SIZES:
        raise ValueError(f"unknown model size '{size}'. Choices: {', '.join(MODEL_SIZES)}")


def _safe_import_hub():
    """Return the huggingface_hub module or None if unavailable."""
    try:
        import huggingface_hub  # type: ignore[import-not-found]

        return huggingface_hub
    except ImportError:
        return None


def faster_whisper_importable() -> bool:
    """Return True if ``faster_whisper`` can be imported right now."""
    try:
        import faster_whisper  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


def faster_whisper_version() -> str | None:
    """Return faster-whisper's installed version, or None if not importable."""
    try:
        import faster_whisper  # type: ignore[import-not-found]

        return getattr(faster_whisper, "__version__", None)
    except ImportError:
        return None


def list_cached_models() -> list[dict[str, Any]]:
    """Return one entry per MODEL_SIZES with cache status + disk bytes.

    Safe before setup: if huggingface_hub isn't importable, every entry is
    ``cached=False, bytes=0``.
    """
    cached_bytes: dict[str, int] = {}
    hub = _safe_import_hub()
    if hub is not None:
        try:
            info = hub.scan_cache_dir()
            repo_to_size = {repo: size for size, repo in MODEL_REPOS.items()}
            for repo in info.repos:
                size = repo_to_size.get(repo.repo_id)
                if size:
                    cached_bytes[size] = cached_bytes.get(size, 0) + int(repo.size_on_disk)
        except Exception:
            # scan_cache_dir can fail on a half-written cache; treat as empty.
            pass

    result = []
    for size in MODEL_SIZES:
        bytes_on_disk = cached_bytes.get(size, 0)
        result.append(
            {
                "size": size,
                "repo": MODEL_REPOS[size],
                "cached": bytes_on_disk > 0,
                "bytes": bytes_on_disk,
                "spec": MODEL_SPECS[size],
            }
        )
    return result


def is_cached(size: str) -> bool:
    """Return True if any revision of the repo for ``size`` is in the HF cache."""
    validate_size(size)
    for entry in list_cached_models():
        if entry["size"] == size:
            return bool(entry["cached"])
    return False


def any_model_cached() -> bool:
    """Return True if at least one size is cached."""
    return any(e["cached"] for e in list_cached_models())


def _progress_tqdm_class(progress_cb: Callable[[int, int], None]):
    """Build a tqdm subclass that reports byte progress to ``progress_cb``.

    huggingface_hub >= 1.x hands ``tqdm_class`` two whole-snapshot byte bars
    (``unit == "B"``): network bytes and bytes written to disk, each totalling
    the full download, plus a files-count bar we ignore. Summing would double
    the size, so we report the furthest bar as ``(downloaded, total)``. Older
    versions give us only the files bar, so the UI falls back to the spinner.

    Returns ``None`` if the tqdm base can't be imported — caller then downloads
    without a progress hook (UI falls back to the spinner).
    """
    try:
        from huggingface_hub.utils import tqdm as hf_tqdm  # type: ignore[import-not-found]
        from tqdm import tqdm as base_tqdm
    except ImportError:
        return None

    bars: dict[int, tuple[int, int]] = {}  # id(bar) -> (n, total)
    lock = threading.Lock()

    def _report() -> None:
        with lock:
            downloaded = max((n for n, _ in bars.values()), default=0)
            total = max((t for _, t in bars.values()), default=0)
            if total:  # 1.x bars can disagree on the total
                total = max(total, downloaded)
        try:
            progress_cb(downloaded, total)
        except Exception:
            pass

    class _NullFile:
        def write(self, _s):
            pass

        def flush(self):
            pass

    class _ProgressTqdm(hf_tqdm):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            # huggingface_hub >= 1.x passes disable=None (off with no TTY, e.g. the
            # Web UI) and its base class forces disable=True under
            # HF_HUB_DISABLE_PROGRESS_BARS; a disabled bar never sets .unit or
            # counts .n. Skip the HF base init, keep the bar on, draw to nowhere.
            kwargs.pop("name", None)
            kwargs["disable"] = False
            kwargs["file"] = _NullFile()
            base_tqdm.__init__(self, *args, **kwargs)
            if self.unit == "B":
                with lock:
                    bars[id(self)] = (self.n, self.total or 0)
                _report()

        def update(self, n=1):
            ret = super().update(n)
            if self.unit == "B":
                with lock:
                    bars[id(self)] = (self.n, self.total or 0)
                _report()
            return ret

        def close(self):
            super().close()
            if self.unit == "B":
                with lock:
                    bars[id(self)] = (self.total or self.n, self.total or self.n)
                _report()

    return _ProgressTqdm


def pull_model(
    size: str,
    progress_cb: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Download the weights for ``size`` via huggingface_hub. Idempotent.

    Returns a dict with keys ``{status, size, repo, bytes}``. ``status`` is
    ``"already_present"`` if already fully cached, otherwise ``"downloaded"``.
    Raises if huggingface_hub or faster-whisper aren't installed.

    ``progress_cb(downloaded_bytes, total_bytes)`` is called during download if
    provided — used by the Web UI to show a byte-level progress bar.
    """
    validate_size(size)

    if not faster_whisper_importable():
        raise RuntimeError(
            "faster-whisper is not installed. Run `anyscribe local setup --model <size>` "
            "to install it and pull a model."
        )

    hub = _safe_import_hub()
    if hub is None:
        raise RuntimeError("huggingface_hub is not available. Reinstall anyscribe to restore it.")

    repo = MODEL_REPOS[size]

    if is_cached(size):
        bytes_on_disk = 0
        for entry in list_cached_models():
            if entry["size"] == size:
                bytes_on_disk = int(entry["bytes"])
                break
        return {
            "status": "already_present",
            "size": size,
            "repo": repo,
            "bytes": bytes_on_disk,
        }

    download_kwargs: dict[str, Any] = {"repo_id": repo}
    if progress_cb is not None:
        tqdm_class = _progress_tqdm_class(progress_cb)
        if tqdm_class is not None:
            download_kwargs["tqdm_class"] = tqdm_class
    hub.snapshot_download(**download_kwargs)

    bytes_on_disk = 0
    for entry in list_cached_models():
        if entry["size"] == size:
            bytes_on_disk = int(entry["bytes"])
            break

    return {
        "status": "downloaded",
        "size": size,
        "repo": repo,
        "bytes": bytes_on_disk,
    }


def delete_model(size: str) -> dict[str, Any]:
    """Remove all cached revisions of ``size`` from the HF cache.

    Returns ``{status, size, bytes_freed}``. ``status`` is ``"not_present"``
    if nothing was cached, otherwise ``"removed"``.
    """
    validate_size(size)

    hub = _safe_import_hub()
    if hub is None:
        return {"status": "not_present", "size": size, "bytes_freed": 0}

    try:
        info = hub.scan_cache_dir()
    except Exception:
        return {"status": "not_present", "size": size, "bytes_freed": 0}

    repo_id = MODEL_REPOS[size]
    commit_hashes: list[str] = []
    total_bytes = 0
    for repo in info.repos:
        if repo.repo_id != repo_id:
            continue
        for rev in repo.revisions:
            commit_hashes.append(rev.commit_hash)
            total_bytes += int(rev.size_on_disk)

    if not commit_hashes:
        return {"status": "not_present", "size": size, "bytes_freed": 0}

    strategy = info.delete_revisions(*commit_hashes)
    strategy.execute()
    return {"status": "removed", "size": size, "bytes_freed": total_bytes}


def delete_all_models() -> dict[str, Any]:
    """Remove every cached size. Used by teardown.

    Returns ``{models_deleted: [...], bytes_freed: int}``.
    """
    deleted: list[str] = []
    total = 0
    for size in MODEL_SIZES:
        res = delete_model(size)
        if res["status"] == "removed":
            deleted.append(size)
            total += int(res["bytes_freed"])
    return {"models_deleted": deleted, "bytes_freed": total}
