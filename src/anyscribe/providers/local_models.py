"""Local model vocabulary and on-disk cache management.

Single source of truth for the local models the user can pick (Whisper via
faster-whisper, Parakeet via onnx-asr), the HuggingFace repos they map to and
the measured figures every surface shows. Wraps ``huggingface_hub`` for
list/download/delete so the rest of the codebase never has to touch the HF
cache layout directly.

These helpers are safe to import before the engines are installed:
``list_cached_models()`` returns all-uncached and ``is_cached()`` returns
``False`` when the hub library isn't available, so status UIs can render a
"not set up" state without crashing.

"Cached" means the model's own files are complete: every file the engine
loads is on disk and nothing is half-downloaded (used for sizes and disk
maths). Some bytes without that is ``partial`` (an interrupted or running
download), which pull resumes. "Runnable" (``runnable()``) is the one
readiness test everything else uses: the engine imports, the weights are
complete and, for Parakeet, its helpers (Tiny, VAD) are too.
"""

from __future__ import annotations

import fnmatch
import threading
from pathlib import Path
from typing import Any, Callable

# Model ids: the strings stored in settings.local_model and accepted on the CLI
# and API. Order is display order: the four featured cards, then the rest.
MODEL_SIZES: list[str] = [
    "parakeet-v3",
    "large-v3-turbo",
    "small",
    "base",
    "parakeet-v2",
    "medium",
    "large-v3",
    "distil-large-v3.5",
    "tiny",
]

RECOMMENDED_MODEL: str = "parakeet-v3"

# The Whisper model used for the pre-run language check in front of Parakeet.
LANGUAGE_CHECK_MODEL: str = "tiny"

# faster-whisper / onnx-asr load these HF repos. Keys stay in lockstep with
# MODEL_SIZES.
MODEL_REPOS: dict[str, str] = {
    "parakeet-v3": "istupakov/parakeet-tdt-0.6b-v3-onnx",
    "parakeet-v2": "istupakov/parakeet-tdt-0.6b-v2-onnx",
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large-v3-turbo": "dropbox-dash/faster-whisper-large-v3-turbo",
    "distil-large-v3.5": "distil-whisper/distil-large-v3.5-ct2",
}

# onnx-asr's own name for each Parakeet model (selects the decoder class).
ONNX_ASR_NAMES: dict[str, str] = {
    "parakeet-v3": "nemo-parakeet-tdt-0.6b-v3",
    "parakeet-v2": "nemo-parakeet-tdt-0.6b-v2",
}
# Only the int8 weights onnx-asr loads with quantization="int8" (the repos
# also hold fp32 weights several times larger).
PARAKEET_FILES: list[str] = [
    "config.json",
    "config.yaml",
    "vocab.txt",
    "*.int8.onnx",
    "*.int8.onnx?data",
]
# Silero voice-activity model: splits audio into speech segments for Parakeet.
VAD_REPO: str = "istupakov/silero-vad-onnx"
VAD_FILES: list[str] = ["config.json", "silero_vad.onnx"]

# The files each engine can't load without (globs). A model is ready when a
# snapshot holds all of them and no blob is still ``.incomplete``.
WHISPER_REQUIRED: list[str] = ["config.json", "model.bin", "tokenizer.json", "vocabulary.*"]
PARAKEET_REQUIRED: list[str] = [
    "config.json",
    "vocab.txt",
    "encoder-model.int8.onnx",
    "decoder_joint-model.int8.onnx",
]
VAD_REQUIRED: list[str] = ["silero_vad.onnx"]

# Parakeet v3's 25 languages (ISO 639-1), from NVIDIA's model card.
PARAKEET_V3_LANGUAGES: frozenset[str] = frozenset(
    "bg hr cs da nl en et fi fr de el hu it lv lt mt pl pt ro sk sl es sv ru uk".split()
)

WHISPER_LANGS = "Hindi and 95+ other languages"

# Shown under the model cards on every surface that shows the measured figures.
BENCHMARK_CAPTION = (
    "Speed and accuracy measured on English audio on a 6-core desktop processor without "
    "a graphics card. Your computer may be faster or slower."
)


def accuracy_rating(en_wer: float) -> int:
    """1-5 accuracy from English word error rate (%). Rule kept in docs/building/providers.md."""
    return 5 if en_wer <= 6.7 else 4 if en_wer <= 7.6 else 3 if en_wer <= 10.5 else 2


def speed_rating(x_realtime: float) -> int:
    """1-5 speed from audio-seconds per wall-second on the reference machine."""
    if x_realtime >= 12:
        return 5
    if x_realtime >= 6:
        return 4
    if x_realtime >= 2.5:
        return 3
    return 2 if x_realtime >= 1.2 else 1


# Measured 2026-11-19 on the reference machine: Intel i5-10600K (6 cores /
# 12 threads), 15 GB RAM, no graphics card, CPU int8, model already loaded.
# en_wer: word error rate (%) on 15.2 min of English speech (pitch videos and
# voice messages) against a commercial cloud transcript, after lowercasing and
# stripping punctuation and fillers. x_realtime: audio seconds per wall second.
# ram_mb: peak memory while transcribing. Ratings and "minutes per hour of
# audio" are derived from these by _derive() below, never typed by hand.
# ``use_for`` is the one-line "for" shown on each card; ``tucked`` says why a
# non-featured model sits under "More models".
MODEL_SPECS: dict[str, dict[str, Any]] = {
    "parakeet-v3": {
        "display_name": "Parakeet v3",
        "engine": "parakeet",
        "en_wer": 6.54,
        "x_realtime": 6.3,
        "download_mb": 670,
        "ram_mb": 2200,
        "languages": "English and 24 European languages",
        "language_codes": sorted(PARAKEET_V3_LANGUAGES),
        "use_for": "English and 24 European languages. Fastest accurate option.",
        "featured": 1,
        "badge": "recommended",
        "tucked": None,
    },
    "large-v3-turbo": {
        "display_name": "Whisper Large v3 Turbo",
        "engine": "whisper",
        "en_wer": 6.63,
        "x_realtime": 1.5,
        "download_mb": 1600,
        "ram_mb": 3100,
        "languages": WHISPER_LANGS,
        "language_codes": None,
        "use_for": "Hindi and 95+ other languages. As accurate as Parakeet on English, but slower.",
        "featured": 2,
        "badge": "for Hindi",
        "tucked": None,
    },
    "small": {
        "display_name": "Whisper Small",
        "engine": "whisper",
        "en_wer": 7.06,
        "x_realtime": 2.7,
        "download_mb": 460,
        "ram_mb": 1300,
        "languages": WHISPER_LANGS,
        "language_codes": None,
        "use_for": "Older or low-memory computers. Any language, small download.",
        "featured": 3,
        "badge": None,
        "tucked": None,
    },
    "base": {
        "display_name": "Whisper Base",
        "engine": "whisper",
        "en_wer": 10.16,
        "x_realtime": 7.8,
        "download_mb": 140,
        "ram_mb": 1000,
        "languages": WHISPER_LANGS,
        "language_codes": None,
        "use_for": "Quick rough drafts. Smallest useful model.",
        "featured": 4,
        "badge": None,
        "tucked": None,
    },
    "parakeet-v2": {
        "display_name": "Parakeet v2",
        "engine": "parakeet",
        "en_wer": 7.50,
        "x_realtime": 6.5,
        "download_mb": 670,
        "ram_mb": 2500,
        "languages": "English only",
        "language_codes": ["en"],
        "use_for": "English-only audio, if you already have it downloaded.",
        "featured": None,
        "badge": None,
        "tucked": "English only; v3 is as fast and more accurate",
    },
    "medium": {
        "display_name": "Whisper Medium",
        "engine": "whisper",
        "en_wer": 7.28,
        "x_realtime": 0.9,
        "download_mb": 1500,
        "ram_mb": 3200,
        "languages": WHISPER_LANGS,
        "language_codes": None,
        "use_for": "Non-English audio when you can wait.",
        "featured": None,
        "badge": None,
        "tucked": "Slower than real time, no more accurate than Small",
    },
    "large-v3": {
        "display_name": "Whisper Large v3",
        "engine": "whisper",
        "en_wer": 7.19,
        "x_realtime": 0.4,
        "download_mb": 2900,
        "ram_mb": 6400,
        "languages": WHISPER_LANGS,
        "language_codes": None,
        "use_for": "Computers with a graphics card (GPU).",
        "featured": None,
        "badge": None,
        "tucked": "Needs a graphics card to be practical",
    },
    "distil-large-v3.5": {
        "display_name": "Distil-Whisper Large v3.5",
        "engine": "whisper",
        "en_wer": 10.01,
        "x_realtime": 1.9,
        "download_mb": 1400,
        "ram_mb": 2700,
        "languages": "English (weak on other languages)",
        "language_codes": None,
        "use_for": "English audio; scored below Small in our test.",
        "featured": None,
        "badge": None,
        "tucked": "Scored below Small in our test",
    },
    "tiny": {
        "display_name": "Whisper Tiny",
        "engine": "whisper",
        "en_wer": 11.90,
        "x_realtime": 14.4,
        "download_mb": 75,
        "ram_mb": 900,
        "languages": WHISPER_LANGS,
        "language_codes": None,
        "use_for": "The language check in front of Parakeet; very rough drafts.",
        "featured": None,
        "badge": None,
        "tucked": "Very rough; used for the language check",
    },
}


def _derive() -> None:
    for spec in MODEL_SPECS.values():
        spec["accuracy"] = accuracy_rating(spec["en_wer"])
        spec["speed"] = speed_rating(spec["x_realtime"])
        spec["min_per_hour"] = round(60 / spec["x_realtime"])


_derive()


def engine_of(model_id: str) -> str:
    """``"whisper"`` or ``"parakeet"`` for a model id."""
    return MODEL_SPECS[model_id]["engine"]


def display_name(model_id: str) -> str:
    return MODEL_SPECS.get(model_id, {}).get("display_name", model_id)


def featured_models() -> list[str]:
    """Ids shown as cards, in card order."""
    ids = [m for m in MODEL_SIZES if MODEL_SPECS[m]["featured"]]
    return sorted(ids, key=lambda m: MODEL_SPECS[m]["featured"])


def validate_size(size: str) -> None:
    """Raise ValueError if ``size`` isn't one of MODEL_SIZES."""
    if size not in MODEL_SIZES:
        raise ValueError(f"unknown model '{size}'. Choices: {', '.join(MODEL_SIZES)}")


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


def onnx_asr_importable() -> bool:
    """Return True if ``onnx_asr`` (the Parakeet engine) can be imported right now."""
    try:
        import onnx_asr  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


def engine_importable(model_id: str) -> bool:
    """True when the engine ``model_id`` runs on is installed (Parakeet also
    decodes audio through faster-whisper's PyAV reader, so it needs both)."""
    if engine_of(model_id) == "parakeet":
        return onnx_asr_importable() and faster_whisper_importable()
    return faster_whisper_importable()


def _hub_cache_dir() -> Path | None:
    try:
        from huggingface_hub.constants import HF_HUB_CACHE  # type: ignore[import-not-found]
    except ImportError:
        return None
    return Path(HF_HUB_CACHE)


def repo_ready(repo_id: str, required: list[str]) -> bool:
    """True when ``repo_id`` is fully downloaded: a snapshot holds every
    ``required`` file (each glob matches a file whose blob exists) and no blob
    is still ``.incomplete``. A ``<hash>.<tag>.incomplete`` left by a killed
    download whose ``<hash>`` blob has since completed is stale and ignored."""
    cache = _hub_cache_dir()
    if cache is None:
        return False
    repo_dir = cache / ("models--" + repo_id.replace("/", "--"))
    for part in repo_dir.glob("blobs/*.incomplete"):
        if not (part.parent / part.name.split(".")[0]).exists():
            return False
    for snap in repo_dir.glob("snapshots/*"):
        names = [f.name for f in snap.iterdir() if f.exists()]  # exists() follows the link
        if all(fnmatch.filter(names, pattern) for pattern in required):
            return True
    return False


def model_ready(size: str) -> bool:
    """True when every file ``size``'s engine loads is on disk."""
    required = PARAKEET_REQUIRED if engine_of(size) == "parakeet" else WHISPER_REQUIRED
    return repo_ready(MODEL_REPOS[size], required)


def helpers_ready() -> bool:
    """True when Parakeet's helpers are ready: Silero VAD and Whisper Tiny."""
    return repo_ready(VAD_REPO, VAD_REQUIRED) and model_ready(LANGUAGE_CHECK_MODEL)


def runnable(size: str) -> bool:
    """True when ``size`` can transcribe right now: its engine imports, its
    weights are complete and, for Parakeet, Tiny and the VAD are too. The one
    readiness test for "set up", "ready", the Test button and switching the
    default."""
    if _safe_import_hub() is None or not engine_importable(size) or not model_ready(size):
        return False
    return engine_of(size) != "parakeet" or helpers_ready()


def list_cached_models() -> list[dict[str, Any]]:
    """Return one entry per MODEL_SIZES with readiness + disk bytes.

    ``cached`` is True when the model's own files are complete (see
    ``model_ready``); ``partial`` is True when some bytes are on disk but they
    aren't; ``runnable`` is ``runnable()``. Safe before setup: if
    huggingface_hub isn't importable, every entry is all False with 0 bytes.
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

    engines = {"whisper": faster_whisper_importable()}
    engines["parakeet"] = engines["whisper"] and onnx_asr_importable()
    helpers = hub is not None and helpers_ready()
    result = []
    for size in MODEL_SIZES:
        bytes_on_disk = cached_bytes.get(size, 0)
        ready = hub is not None and model_ready(size)
        engine = engine_of(size)
        result.append(
            {
                "size": size,
                "repo": MODEL_REPOS[size],
                "cached": ready,
                "partial": bytes_on_disk > 0 and not ready,
                "runnable": ready and engines[engine] and (engine != "parakeet" or helpers),
                "bytes": bytes_on_disk,
                "spec": MODEL_SPECS[size],
            }
        )
    return result


def is_cached(size: str) -> bool:
    """Return True if ``size`` is fully downloaded and ready to load."""
    validate_size(size)
    return _safe_import_hub() is not None and model_ready(size)


def any_model_runnable() -> bool:
    """Return True if at least one model can transcribe right now."""
    return any(e["runnable"] for e in list_cached_models())


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


def bytes_on_disk(size: str) -> int:
    """Bytes of ``size`` in the HF cache, ready or not (0 when absent)."""
    for entry in list_cached_models():
        if entry["size"] == size:
            return int(entry["bytes"])
    return 0


def pull_model(
    size: str,
    progress_cb: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Download the weights for ``size`` via huggingface_hub. Idempotent.

    Always calls the downloader, which resumes a partial download and is a
    no-op (also offline) when the snapshot is complete. Returns a dict with
    keys ``{status, size, repo, bytes}``. ``status`` is ``"already_present"``
    if the model was ready before the call, otherwise ``"downloaded"``.
    Raises if huggingface_hub or the model's engine isn't installed.

    A Parakeet model also pulls its helpers: the Silero voice-activity model
    and Whisper ``tiny`` for the language check (so a run never has to fetch
    them silently).

    ``progress_cb(downloaded_bytes, total_bytes)`` is called during download if
    provided — used by the Web UI to show a byte-level progress bar.
    """
    validate_size(size)

    if not engine_importable(size):
        engine = "onnx-asr" if engine_of(size) == "parakeet" else "faster-whisper"
        raise RuntimeError(
            f"{engine} is not installed. Run "
            f"`anyscribe local setup --model {size}` to install it and pull a model."
        )

    hub = _safe_import_hub()
    if hub is None:
        raise RuntimeError("huggingface_hub is not available. Reinstall anyscribe to restore it.")

    repo = MODEL_REPOS[size]
    parakeet = engine_of(size) == "parakeet"

    def _snapshot(repo_id: str, allow: list[str] | None, cb) -> None:
        kwargs: dict[str, Any] = {"repo_id": repo_id}
        if allow:
            kwargs["allow_patterns"] = allow
        if cb is not None:
            tqdm_class = _progress_tqdm_class(cb)
            if tqdm_class is not None:
                kwargs["tqdm_class"] = tqdm_class
        hub.snapshot_download(**kwargs)

    status = "already_present" if is_cached(size) else "downloaded"
    _snapshot(repo, PARAKEET_FILES if parakeet else None, progress_cb)

    helpers: list[str] = []
    if parakeet:
        _snapshot(VAD_REPO, VAD_FILES, None)  # ~2 MB; a no-op once complete
        if not is_cached(LANGUAGE_CHECK_MODEL):
            _snapshot(MODEL_REPOS[LANGUAGE_CHECK_MODEL], None, progress_cb)
            helpers.append(LANGUAGE_CHECK_MODEL)

    result = {"status": status, "size": size, "repo": repo, "bytes": bytes_on_disk(size)}
    if helpers:
        result["helpers_downloaded"] = helpers
    return result


def _delete_repo(repo_id: str) -> int:
    """Delete every cached revision of ``repo_id``; return bytes freed (0 if absent)."""
    hub = _safe_import_hub()
    if hub is None:
        return 0
    try:
        info = hub.scan_cache_dir()
    except Exception:
        return 0

    commit_hashes: list[str] = []
    total_bytes = 0
    for repo in info.repos:
        if repo.repo_id != repo_id:
            continue
        for rev in repo.revisions:
            commit_hashes.append(rev.commit_hash)
            total_bytes += int(rev.size_on_disk)

    if not commit_hashes:
        return 0
    info.delete_revisions(*commit_hashes).execute()
    return total_bytes


def delete_model(size: str) -> dict[str, Any]:
    """Remove all cached revisions of ``size`` from the HF cache.

    Returns ``{status, size, bytes_freed}``. ``status`` is ``"not_present"``
    if nothing was cached, otherwise ``"removed"``.
    """
    validate_size(size)
    freed = _delete_repo(MODEL_REPOS[size])
    if not freed:
        return {"status": "not_present", "size": size, "bytes_freed": 0}
    return {"status": "removed", "size": size, "bytes_freed": freed}


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
    total += _delete_repo(VAD_REPO)
    return {"models_deleted": deleted, "bytes_freed": total}
