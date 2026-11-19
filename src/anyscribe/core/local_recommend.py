""" "Help me choose": one question plus detected hardware -> a local model pick.

Shared by every surface (CLI onboarding, Web UI wizard + Settings, MCP doctor)
so the advice is identical wherever it's asked. The rules are deliberately
small; the figures they cite come from the measured registry in
``providers/local_models.py``.
"""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import Any

from anyscribe.providers.local_models import (
    LANGUAGE_CHECK_MODEL,
    MODEL_SPECS,
    display_name,
    engine_of,
)

# The one question: "What language is most of your audio?"
LANGUAGE_ANSWERS: dict[str, str] = {
    "english": "English",
    "indian": "Hindi or another Indian language",
    "european": "Another European language",
    "mix": "A mix (e.g. English and Hindi)",
    "other": "Something else",
}

# What the person said, as the start of the first sentence.
_SAID = {
    "english": "You said mostly English.",
    "indian": "You said mostly Hindi or another Indian language.",
    "european": "You said mostly a European language.",
    "mix": "You said a mix of languages.",
    "other": "You said a language outside English and Europe.",
}

# Picks to try in order for each answer, first that fits on disk wins:
# (primary, also). A mix never drops to Parakeet alone, which would leave
# Hindi with no model to switch to.
_CANDIDATES: dict[str, list[tuple[str, list[str]]]] = {
    "english": [("parakeet-v3", []), ("small", []), ("base", [])],
    "european": [("parakeet-v3", []), ("small", []), ("base", [])],
    "mix": [
        ("parakeet-v3", ["large-v3-turbo"]),
        ("large-v3-turbo", []),
        ("small", []),
        ("base", []),
    ],
    "indian": [("large-v3-turbo", []), ("small", []), ("base", [])],
    "other": [("large-v3-turbo", []), ("small", []), ("base", [])],
}

# Measured on Hindi (FLEURS): Turbo's character error rate with the language
# set to Hindi vs left on auto-detect (9.9 vs 28.5, journal 2026-11-19).
HINDI_SET_VS_AUTO = "about 3 times"


def _total_ram_gb() -> float | None:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3
    except (AttributeError, ValueError, OSError):
        pass
    if os.name == "nt":
        try:
            import ctypes

            class _MemStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
                    (n, ctypes.c_ulonglong)
                    for n in (
                        "ullTotalPhys",
                        "ullAvailPhys",
                        "ullTotalPageFile",
                        "ullAvailPageFile",
                        "ullTotalVirtual",
                        "ullAvailVirtual",
                        "ullAvailExtendedVirtual",
                    )
                ]

            st = _MemStatus()
            st.dwLength = ctypes.sizeof(_MemStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))  # type: ignore[attr-defined]
            return st.ullTotalPhys / 1024**3
        except Exception:
            return None
    return None


def _model_cache_dir() -> Path:
    try:
        from huggingface_hub.constants import HF_HUB_CACHE

        return Path(HF_HUB_CACHE)
    except ImportError:
        home = os.environ.get("HF_HOME") or str(Path.home() / ".cache" / "huggingface")
        return Path(home) / "hub"


def _free_disk_mb(path: Path) -> int | None:
    while not path.exists() and path != path.parent:
        path = path.parent
    try:
        return int(shutil.disk_usage(path).free / 1024**2)
    except OSError:
        return None


def _nvidia_gpu() -> bool:
    try:
        import ctranslate2  # type: ignore[import-not-found]

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def detect_hardware() -> dict[str, Any]:
    """Cheap, read-only facts about this computer. Never asks the user."""
    ram = _total_ram_gb()
    return {
        "ram_gb": round(ram, 1) if ram else None,
        "cpu_cores": os.cpu_count(),
        "apple_silicon": platform.system() == "Darwin" and platform.machine() == "arm64",
        "nvidia_gpu": _nvidia_gpu(),
        "free_disk_mb": _free_disk_mb(_model_cache_dir()),
    }


def _need_mb(ids: list[str], cached: set[str]) -> int:
    need = {m for m in ids if m not in cached}
    if any(engine_of(m) == "parakeet" for m in ids) and LANGUAGE_CHECK_MODEL not in cached:
        need.add(LANGUAGE_CHECK_MODEL)
    return sum(MODEL_SPECS[m]["download_mb"] for m in need)


def _gb(mb: int) -> str:
    return f"{mb / 1024:.1f} GB" if mb >= 1024 else f"{mb} MB"


def _describe(pick: str, also: list[str], answer: str, times: int) -> list[str]:
    """Why ``pick`` (+ ``also``) suits ``answer``: one or two sentences."""
    pk, turbo = display_name("parakeet-v3"), display_name("large-v3-turbo")
    faster = f"about {times} times faster on our test desktop"
    if pick == "parakeet-v3" and also:
        return [
            f"anyscribe uses two models: {pk} for English and European audio, and "
            f"{turbo} for anything else, Hindi for example. It checks the language at "
            "the start, middle and end of each recording and says on the transcript "
            f"when it switched. {pk} is the main one because it is about {times} times "
            "faster on English.",
            f"If one recording switches language mid-sentence (Hinglish), make {turbo} "
            "your default instead.",
        ]
    if pick == "parakeet-v3" and answer == "european":
        return [
            f"{pk} covers 25 European languages including English; on English it is as "
            f"accurate as {turbo} and {faster}.",
            "Anything else is caught by the language check and sent to Whisper.",
        ]
    if pick == "parakeet-v3":
        return [
            f"{pk} is as accurate as {turbo} on English, and {faster}.",
            "It also covers 24 European languages; the language check sends anything "
            "else to Whisper.",
        ]
    if pick == "large-v3-turbo" and answer == "indian":
        return [
            f"{turbo} was the most accurate local model on Hindi in our test.",
            f"If your audio is Hindi, set your language to Hindi: Turbo is {HINDI_SET_VS_AUTO} "
            "more accurate on Hindi when it is told the language. Every recording is then "
            "treated as Hindi.",
        ]
    if pick == "large-v3-turbo" and answer == "mix":
        return [f"{turbo} handles English and Hindi on its own, more slowly than {pk}."]
    if pick == "large-v3-turbo":
        return [
            f"{turbo} covers 95+ languages and was the most accurate Whisper model in our test."
        ]
    if pick == "small":
        return [
            f"{display_name('small')} covers 95+ languages with a small download, a little less accurately."
        ]
    return [
        f"{display_name('base')} handles any language; expect a rough draft rather than a polished transcript."
    ]


def _sizes(ids: list[str], cached: set[str]) -> str:
    """'Downloads 670 MB + 1.6 GB, plus the 75 MB language check.' for what isn't on disk."""
    parts = [_gb(MODEL_SPECS[m]["download_mb"]) for m in ids if m not in cached]
    check = any(engine_of(m) == "parakeet" for m in ids) and LANGUAGE_CHECK_MODEL not in cached
    if not parts and not check:
        return "Already downloaded."
    tiny = f"the {_gb(MODEL_SPECS[LANGUAGE_CHECK_MODEL]['download_mb'])} language check"
    if not parts:
        return f"Downloads {tiny}."
    return "Downloads " + " + ".join(parts) + (f", plus {tiny}." if check else ".")


def recommend(
    language_answer: str,
    hardware: dict[str, Any] | None = None,
    cached: set[str] | None = None,
) -> dict[str, Any]:
    """Pick a local model for ``language_answer`` (a key of LANGUAGE_ANSWERS).

    Returns ``{answer, primary, also, reasons, download_mb, set_language,
    hardware}``: ``primary`` is the model to make the default (None when
    nothing fits on disk), ``also`` lists extra downloads (Turbo for a mix),
    ``reasons`` are plain sentences about the final pick (memory or disk are
    cited only when they changed it), ``download_mb`` is what still has to
    download, and ``set_language`` is a language worth setting (Hindi), or None.
    """
    if language_answer not in LANGUAGE_ANSWERS:
        raise ValueError(
            f"unknown answer '{language_answer}'. Choices: {', '.join(LANGUAGE_ANSWERS)}"
        )
    hw = hardware if hardware is not None else detect_hardware()
    cached = cached or set()
    ram = hw.get("ram_gb")
    free = hw.get("free_disk_mb")
    turbo = MODEL_SPECS["large-v3-turbo"]
    times = round(MODEL_SPECS["parakeet-v3"]["x_realtime"] / turbo["x_realtime"])

    candidates = _CANDIDATES[language_answer]
    memory: str | None = None
    if ram is not None and ram < 4:
        candidates = [("base", [])]
        memory = (
            f"This computer has {ram:g} GB of memory, so Whisper Base fits: the larger "
            "models need 1.3 GB or more while they run and would slow everything else down."
        )
    elif candidates[0][0] == "large-v3-turbo" and ram is not None and ram < 6:
        candidates = [c for c in candidates if c[0] != "large-v3-turbo"]
        memory = (
            f"{display_name('large-v3-turbo')} would want about {_gb(turbo['ram_mb'])} of "
            f"memory and this computer has {ram:g} GB, so Whisper Small fits better."
        )

    fits = [c for c in candidates if free is None or _need_mb([c[0], *c[1]], cached) * 1.1 <= free]
    if not fits:
        need = _need_mb([candidates[-1][0]], cached)
        return {
            "answer": language_answer,
            "primary": None,
            "also": [],
            "reasons": [
                f"Not enough free disk space: only {_gb(free or 0)} is free, and even the "
                f"smallest suitable model ({display_name(candidates[-1][0])}) needs about "
                f"{_gb(round(need * 1.1))}. Free up space, then ask again."
            ],
            "download_mb": need,
            "set_language": None,
            "hardware": hw,
        }
    primary, also = fits[0]

    reasons = [_SAID[language_answer]]
    if memory and primary == candidates[0][0]:
        reasons.append(memory)
    if primary != candidates[0][0]:
        first = " + ".join(display_name(m) for m in [candidates[0][0], *candidates[0][1]])
        reasons.append(
            f"Only {_gb(free or 0)} of disk space is free, not enough for {first}, "
            f"so this suggests {display_name(primary)}."
        )
    reasons += _describe(primary, also, language_answer, times)
    reasons.append(_sizes([primary, *also], cached))

    return {
        "answer": language_answer,
        "primary": primary,
        "also": also,
        "reasons": reasons,
        "download_mb": _need_mb([primary, *also], cached),
        "set_language": "hi" if language_answer == "indian" else None,
        "hardware": hw,
    }


def parakeet_suggestion(default_model: str, language: str, web: bool = False) -> str | None:
    """One line suggesting Parakeet v3 to an existing Whisper user whose audio
    is English (or auto). A suggestion only; nothing switches. ``web`` points
    at the card under it instead of the command."""
    if default_model not in MODEL_SPECS or engine_of(default_model) != "whisper":
        return None
    if language.lower().split("-")[0] not in ("en", "auto"):
        return None
    pk, cur = MODEL_SPECS["parakeet-v3"], MODEL_SPECS[default_model]
    return (
        f"Tip: Parakeet v3 is rated {pk['accuracy']}/5 for accuracy and "
        f"{pk['speed']}/5 for speed (your {display_name(default_model)}: "
        f"{cur['accuracy']}/5, {cur['speed']}/5) on English. "
        + (
            "Try it: click the Parakeet v3 card below."
            if web
            else "Try it: anyscribe local setup --model parakeet-v3"
        )
    )
