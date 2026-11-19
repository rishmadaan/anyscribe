"""Local model transcription provider.

Two engines behind the one ``local`` provider: faster-whisper (CTranslate2
Whisper) and onnx-asr (NVIDIA Parakeet, int8 ONNX, Silero voice-activity
segments). No API key needed, no internet required. Runs on CPU or GPU.

Parakeet only knows 25 languages, and on anything else it writes confident
gibberish, so a language guard sits in front of it: an explicit language
outside its set, or an ``auto`` run where Whisper Tiny hears another language
at the start, middle or end of the speech, goes to a Whisper model instead,
with a note saying so.

Set up via ``anyscribe local setup --model <id>`` (CLI), the "Set up local
transcription" button in the Web UI, or the opt-in step in ``anyscribe onboard``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from anyscribe.providers.base import (
    TranscriptionProvider,
    TranscriptResult,
    TranscriptSegment,
)
from anyscribe.providers.local_models import (
    LANGUAGE_CHECK_MODEL,
    MODEL_REPOS,
    MODEL_SIZES,
    MODEL_SPECS,
    ONNX_ASR_NAMES,
    RECOMMENDED_MODEL,
    display_name,
    engine_of,
    is_cached,
)

SAMPLE_RATE = 16_000
DETECT_SECONDS = 30
DETECT_WINDOWS = 3  # start, middle and end of the speech
UNSURE_BELOW = 0.5  # every window's top-language probability under this = unsure
# Restores sentence case and punctuation when Whisper starts mid-sentence and
# would otherwise write the whole file lowercase (3 of 6 English test clips).
ENGLISH_PROMPT = "Hello, and welcome. Here's what we'll cover today."
FALLBACK_PREFERENCE = "large-v3-turbo"


def _resolve_model_size() -> str:
    """Pick the model for this transcription.

    Precedence: ASCLI_LOCAL_MODEL env var (power-user override) → settings.local_model
    (user-chosen default) → RECOMMENDED_MODEL (safety net if config is empty).
    """
    import os

    env_override = os.environ.get("ASCLI_LOCAL_MODEL")
    if env_override:
        return env_override

    try:
        from anyscribe.config.settings import load_config

        size = load_config().local_model
        if size:
            return size
    except Exception:
        pass

    return RECOMMENDED_MODEL


def _device() -> tuple[str, str]:
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda", "float16"
    except ImportError:
        pass
    return "cpu", "int8"


def _new_whisper(model_id: str, device: str, compute_type: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "faster-whisper is not installed. Run "
            f"`anyscribe local setup --model {model_id}` to install it and pull a model."
        )
    # Load by HF repo id, not size alias — newer sizes (large-v3-turbo,
    # distil-large-v3.5) aren't in every faster-whisper alias table, and the
    # repo id hits the exact cache entry `anyscribe model pull` downloaded.
    return WhisperModel(MODEL_REPOS[model_id], device=device, compute_type=compute_type)


# Loaded models stay in memory between files so a batch doesn't pay the
# 6-17 s load per file. At most one big model plus the Tiny language checker,
# because the Web UI server is long-lived and these weigh gigabytes.
@lru_cache(maxsize=1)
def _load_whisper(model_id: str, device: str, compute_type: str):
    _load_parakeet.cache_clear()
    return _new_whisper(model_id, device, compute_type)


@lru_cache(maxsize=1)
def _load_checker(device: str, compute_type: str):
    return _new_whisper(LANGUAGE_CHECK_MODEL, device, compute_type)


@lru_cache(maxsize=1)
def _load_parakeet(model_id: str):
    _load_whisper.cache_clear()
    try:
        import onnx_asr  # type: ignore[import-not-found]
    except ImportError:
        raise RuntimeError(
            "onnx-asr (the Parakeet engine) is not installed. Run "
            f"`anyscribe local setup --model {model_id}` to install it."
        )
    # shortcut: CoreML partial support made load 110 s and runs 7x slower on
    # Apple silicon (measured 2026-11-19); revisit if onnx-asr ships a full CoreML path
    cpu = ["CPUExecutionProvider"]
    model = onnx_asr.load_model(ONNX_ASR_NAMES[model_id], quantization="int8", providers=cpu)
    return model.with_vad(onnx_asr.load_vad("silero", providers=cpu))


def _decode(audio_path: Path):
    from faster_whisper.audio import decode_audio

    return decode_audio(str(audio_path), sampling_rate=SAMPLE_RATE)


def _speech_windows(audio) -> list:
    """Up to three 30 s windows of speech only (silence cut out by
    faster-whisper's Silero VAD): the start, middle and end of the speech.
    Fewer for short recordings; none when no speech is found."""
    import numpy as np
    from faster_whisper.vad import VadOptions, collect_chunks, get_speech_timestamps

    chunks = get_speech_timestamps(audio, VadOptions())
    if not chunks:
        return []
    speech = np.concatenate(collect_chunks(audio, chunks)[0])
    win = SAMPLE_RATE * DETECT_SECONDS
    n = min(DETECT_WINDOWS, -(-len(speech) // win))
    last = max(len(speech) - win, 0)
    starts = sorted({round(i * last / (n - 1)) if n > 1 else 0 for i in range(n)})
    return [speech[s : s + win] for s in starts]


def _base_lang(language: str) -> str:
    return language.lower().split("-")[0]


def _language_name(code: str) -> str:
    from anyscribe.providers.languages import WHISPER_LANGUAGES

    return next((e["name"] for e in WHISPER_LANGUAGES if e["code"] == code), code)


def pick_fallback() -> str | None:
    """Whisper model to use when Parakeet can't: Turbo if cached, else the most
    accurate other cached multilingual Whisper (never Distil, which is
    English-weak, nor Tiny, which is only the language checker)."""
    if is_cached(FALLBACK_PREFERENCE):
        return FALLBACK_PREFERENCE
    candidates = [
        m
        for m in MODEL_SIZES
        if engine_of(m) == "whisper"
        and m not in ("distil-large-v3.5", LANGUAGE_CHECK_MODEL)
        and is_cached(m)
    ]
    candidates.sort(key=lambda m: (-MODEL_SPECS[m]["accuracy"], -MODEL_SPECS[m]["speed"]))
    return candidates[0] if candidates else None


class LocalProvider(TranscriptionProvider):
    """Transcribe locally with Parakeet (onnx-asr) or Whisper (faster-whisper).

    No API key, no internet. Weights live in the HuggingFace cache
    (``~/.cache/huggingface/hub/``) after ``anyscribe local setup``.
    """

    @property
    def name(self) -> str:
        return "local"

    def _model_id(self) -> str:
        model_id = _resolve_model_size()
        if model_id not in MODEL_SIZES:
            raise ValueError(f"Unknown model '{model_id}'. Available: {', '.join(MODEL_SIZES)}")
        return model_id

    def _get_model(self):
        """Load the configured Whisper model (kept for callers that warm it)."""
        return _load_whisper(self._model_id(), *_device())

    def detect_languages(self, audio) -> list[tuple[str, float]]:
        """Whisper Tiny's ``(language, probability)`` for each speech window
        (start, middle, end); empty when the audio has no speech."""
        if not is_cached(LANGUAGE_CHECK_MODEL):
            raise RuntimeError(
                "Parakeet needs its language check (Whisper Tiny, ~75 MB), which isn't "
                f"downloaded. Run `anyscribe model pull {LANGUAGE_CHECK_MODEL}`, or set "
                "your language explicitly (e.g. `--language en`)."
            )
        checker = _load_checker(*_device())
        return [tuple(checker.detect_language(w)[:2]) for w in _speech_windows(audio)]

    def plan(self, model_id: str, language: str, audio) -> tuple[str, str, list[str]]:
        """The language guard. Decides which model runs and in what language:
        returns ``(model_id, language, notes)`` and raises when nothing suitable
        is cached. Parakeet never sees a language outside its set."""
        if engine_of(model_id) != "parakeet":
            return model_id, language, []

        covered = MODEL_SPECS[model_id]["language_codes"]
        if language.lower() != "auto":
            lang = _base_lang(language)
            if lang in covered:
                return model_id, lang, []
            return self._switch(model_id, lang, "Language is set to", "")

        # Disjoint rules, so their order can't matter: a sure uncovered window
        # switches; any doubt (all windows unsure, or an unsure uncovered one)
        # takes the unsure path; otherwise every window is covered.
        checks = self.detect_languages(audio)
        outside = [c for c in checks if c[0] not in covered]
        sure_outside = [c for c in outside if c[1] >= UNSURE_BELOW]
        if sure_outside:
            lang = max(sure_outside, key=lambda c: c[1])[0]
            name = _language_name(lang)
            if any(c[0] in covered for c in checks):  # some windows were a covered language
                return self._switch(
                    model_id,
                    lang,
                    "Detected",
                    " If your recordings switch language, make Whisper Large v3 Turbo "
                    "your default in Settings.",
                    where=" in part of this recording",
                )
            return self._switch(
                model_id,
                lang,
                "Detected",
                f" To skip the check, set your language to {name} in Settings.",
            )

        pk = display_name(model_id)
        inside = [c for c in checks if c[0] in covered]
        if outside or all(p < UNSURE_BELOW for _, p in checks):  # also when no speech was found
            fallback = pick_fallback()
            if fallback is not None:
                return fallback, "auto", [
                    "The language check couldn't tell what language this is, so this "
                    f"used {display_name(fallback)} instead of {pk}."
                ]
            guess = max(inside, key=lambda c: c[1])[0] if inside else "unknown"
            return model_id, guess, [
                f"The language check couldn't tell what language this is, so {pk} ran "
                "anyway. If the text looks wrong, set your language in Settings."
            ]
        return model_id, max(inside, key=lambda c: c[1])[0], []

    def _switch(
        self, model_id: str, lang: str, how: str, tail: str, where: str = ""
    ) -> tuple[str, str, list[str]]:
        """Route to the best ready Whisper model, with the note that says so."""
        name = _language_name(lang)
        fallback = pick_fallback()
        if fallback is None:
            raise RuntimeError(
                f"{how} {name}{where}, which {display_name(model_id)} doesn't cover, and no "
                "Whisper model to use instead is downloaded. Download Whisper Large v3 "
                "Turbo: `anyscribe model pull large-v3-turbo`, or Settings → Local "
                "transcription. Nothing was written."
            )
        note = (
            f"{how} {name}{where} — {display_name(model_id)} doesn't cover {name}, "
            f"so this used {display_name(fallback)}.{tail}"
        )
        return fallback, lang, [note]

    def transcribe(
        self, audio_path: Path, language: str = "auto", diarize: bool = False
    ) -> TranscriptResult:
        model_id = self._model_id()
        audio = _decode(audio_path)
        model_id, language, notes = self.plan(model_id, language, audio)
        if engine_of(model_id) == "parakeet":
            result = self._parakeet(model_id, audio, language)
        else:
            result = self._whisper(model_id, audio, language)
        result.model = model_id
        result.notes = notes
        return result

    def _parakeet(self, model_id: str, audio, language: str) -> TranscriptResult:
        model = _load_parakeet(model_id)
        segments: list[TranscriptSegment] = []
        for seg in model.recognize(audio, sample_rate=SAMPLE_RATE):
            text = seg.text.strip()
            if text:
                segments.append(
                    TranscriptSegment(id=len(segments), start=seg.start, end=seg.end, text=text)
                )
        return TranscriptResult(
            text=" ".join(s.text for s in segments),
            language=language,
            duration=len(audio) / SAMPLE_RATE,
            segments=segments,
        )

    def _whisper(self, model_id: str, audio, language: str) -> TranscriptResult:
        model = _load_whisper(model_id, *_device())
        auto = language.lower() == "auto"
        kwargs: dict[str, Any] = {"language": None if auto else language}
        if auto:
            # Whisper still picks the language itself; this speech-only guess
            # on the loaded model only decides whether English gets the prompt.
            try:
                language = model.detect_language(audio, vad_filter=True)[0]
            except Exception:  # no speech at all: no prompt
                language = "unknown"
        if _base_lang(language) == "en":
            kwargs["initial_prompt"] = ENGLISH_PROMPT

        segments_iter, info = model.transcribe(
            audio,
            beam_size=5,
            vad_filter=True,  # Skip silence for speed
            **kwargs,
        )

        segments: list[TranscriptSegment] = []
        for i, seg in enumerate(segments_iter):
            segments.append(
                TranscriptSegment(id=i, start=seg.start, end=seg.end, text=seg.text.strip())
            )
        return TranscriptResult(
            text=" ".join(s.text for s in segments),
            language=info.language or "unknown",
            duration=info.duration,
            segments=segments,
        )
