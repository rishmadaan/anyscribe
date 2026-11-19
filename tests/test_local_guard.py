"""The Parakeet language guard, the Whisper English prompt, and the note that
must reach every surface. Engines are faked; each fake records that it ran, so
the assertions name WHICH model transcribed, never just how many things ran."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from anyscribe.providers import local as local_mod
from anyscribe.providers.local import ENGLISH_PROMPT, LocalProvider

AUDIO = np.zeros(16_000 * 5, dtype=np.float32)


class FakeWhisper:
    """``detected`` is one language, or a list of ``(language, probability)``
    handed out one per call (one call per speech window)."""

    def __init__(self, model_id, detected="en"):
        self.model_id = model_id
        self.detected = detected if isinstance(detected, list) else None
        self.single = detected
        self.calls: list[dict] = []
        self.detect_kwargs: list[dict] = []

    def detect_language(self, audio, **kwargs):
        self.detect_kwargs.append(kwargs)
        if self.detected is not None:
            lang, prob = self.detected.pop(0)
            return lang, prob, []
        return self.single, 0.9, []

    def transcribe(self, audio, **kwargs):
        self.calls.append(kwargs)
        seg = SimpleNamespace(start=0.0, end=2.0, text=f" whisper {self.model_id} text")
        return iter([seg]), SimpleNamespace(language=kwargs.get("language"), duration=5.0)


class FakeParakeet:
    def __init__(self, model_id):
        self.model_id = model_id
        self.calls = 0

    def recognize(self, audio, sample_rate):
        self.calls += 1
        return [
            SimpleNamespace(start=0.5, end=1.5, text="Hello there."),
            SimpleNamespace(start=2.0, end=3.25, text="Second part."),
        ]


@pytest.fixture
def rig(monkeypatch):
    """Configurable fake world: default model, cached ids, Tiny's verdict."""
    state = SimpleNamespace(
        default="parakeet-v3",
        cached={"parakeet-v3", "tiny", "large-v3-turbo"},
        tiny_says="en",  # or [(lang, prob), ...]: one per speech window
        whisper={},
        parakeet={},
        detect_calls=0,
    )

    def load_whisper(model_id, device, compute_type):
        return state.whisper.setdefault(model_id, FakeWhisper(model_id))

    def load_parakeet(model_id):
        return state.parakeet.setdefault(model_id, FakeParakeet(model_id))

    def checker(device, compute_type):
        state.detect_calls += 1
        return FakeWhisper("tiny", detected=state.tiny_says)

    def windows(audio):
        says = state.tiny_says
        return [audio] * (len(says) if isinstance(says, list) else 3)

    monkeypatch.setattr(local_mod, "_resolve_model_size", lambda: state.default)
    monkeypatch.setattr(local_mod, "is_cached", lambda m: m in state.cached)
    monkeypatch.setattr(local_mod, "_decode", lambda path: AUDIO)
    monkeypatch.setattr(local_mod, "_load_whisper", load_whisper)
    monkeypatch.setattr(local_mod, "_load_parakeet", load_parakeet)
    monkeypatch.setattr(local_mod, "_load_checker", checker)
    monkeypatch.setattr(local_mod, "_speech_windows", windows)
    return state


def run(language):
    return LocalProvider().transcribe(Path("x.wav"), language=language)


def test_explicit_parakeet_language_runs_parakeet_without_a_check(rig):
    r = run("fr")
    assert r.model == "parakeet-v3"
    assert rig.parakeet["parakeet-v3"].calls == 1 and not rig.whisper
    assert rig.detect_calls == 0 and r.notes == []
    assert r.language == "fr"


def test_explicit_other_language_never_runs_parakeet(rig):
    r = run("hi")
    assert r.model == "large-v3-turbo"
    assert list(rig.whisper) == ["large-v3-turbo"] and not rig.parakeet
    assert rig.whisper["large-v3-turbo"].calls[0]["language"] == "hi"
    assert r.notes == [
        "Language is set to Hindi — Parakeet v3 doesn't cover Hindi, "
        "so this used Whisper Large v3 Turbo."
    ]


def test_auto_english_runs_parakeet_with_real_segment_times(rig):
    r = run("auto")
    assert r.model == "parakeet-v3" and rig.detect_calls == 1
    assert [(s.start, s.end, s.text) for s in r.segments] == [
        (0.5, 1.5, "Hello there."),
        (2.0, 3.25, "Second part."),
    ]
    assert r.text == "Hello there. Second part." and r.language == "en"


def test_auto_hindi_runs_turbo_not_parakeet(rig):
    rig.tiny_says = "hi"
    r = run("auto")
    assert r.model == "large-v3-turbo"
    assert "parakeet-v3" not in rig.parakeet
    assert rig.whisper["large-v3-turbo"].calls[0]["language"] == "hi"
    assert r.notes == [
        "Detected Hindi — Parakeet v3 doesn't cover Hindi, so this used Whisper Large v3 "
        "Turbo. To skip the check, set your language to Hindi in Settings."
    ]


def test_parakeet_v2_is_english_only(rig):
    rig.default, rig.cached = "parakeet-v2", {"parakeet-v2", "tiny", "small"}
    r = run("de")
    assert r.model == "small" and not rig.parakeet


def test_no_whisper_cached_fails_with_the_download_command(rig):
    rig.tiny_says, rig.cached = "hi", {"parakeet-v3", "tiny", "distil-large-v3.5"}
    with pytest.raises(RuntimeError, match="anyscribe model pull large-v3-turbo"):
        run("auto")
    assert not rig.parakeet and not rig.whisper


def test_tiny_missing_fails_before_any_model_runs(rig):
    rig.cached = {"parakeet-v3", "large-v3-turbo"}
    with pytest.raises(RuntimeError, match="anyscribe model pull tiny"):
        run("auto")
    assert not rig.parakeet and not rig.whisper


def test_fallback_prefers_turbo_then_most_accurate_cached(rig):
    rig.cached = {"tiny", "small", "medium", "distil-large-v3.5"}
    # medium and small share accuracy 4/5; small is faster. Distil is never used.
    assert local_mod.pick_fallback() == "small"
    rig.cached |= {"large-v3-turbo"}
    assert local_mod.pick_fallback() == "large-v3-turbo"
    rig.cached = {"tiny", "distil-large-v3.5"}
    assert local_mod.pick_fallback() is None


# ── Whisper English prompt (B3) ──────────────────────────────────


def test_whisper_english_gets_the_punctuation_prompt(rig):
    rig.default = "large-v3-turbo"
    run("en")
    assert rig.whisper["large-v3-turbo"].calls[0]["initial_prompt"] == ENGLISH_PROMPT


def test_whisper_hindi_gets_no_prompt(rig):
    rig.default = "large-v3-turbo"
    r = run("hi")
    assert r.model == "large-v3-turbo"
    assert "initial_prompt" not in rig.whisper["large-v3-turbo"].calls[0]


def test_whisper_auto_detected_english_gets_the_prompt(rig):
    rig.default = "small"
    run("auto")
    call = rig.whisper["small"].calls[0]
    # Whisper keeps choosing the language itself (language=None, as before
    # Parakeet); a speech-only guess on the loaded model only adds the prompt.
    assert call["language"] is None and call["initial_prompt"] == ENGLISH_PROMPT
    assert rig.whisper["small"].detect_kwargs == [{"vad_filter": True}]
    assert rig.detect_calls == 0  # Whisper defaults never run the Tiny guard


def test_whisper_auto_detected_hindi_is_not_forced(rig):
    rig.default = "small"
    rig.whisper["small"] = FakeWhisper("small", detected="hi")
    run("auto")
    call = rig.whisper["small"].calls[0]
    assert call["language"] is None and "initial_prompt" not in call


# ── language check across the recording (C2) ─────────────────────


def test_english_start_then_hindi_routes_to_whisper(rig):
    rig.tiny_says = [("en", 0.97), ("hi", 0.6), ("hi", 0.95)]
    r = run("auto")
    assert r.model == "large-v3-turbo" and not rig.parakeet
    assert rig.whisper["large-v3-turbo"].calls[0]["language"] == "hi"
    assert r.notes == [
        "Detected Hindi in part of this recording — Parakeet v3 doesn't cover Hindi, so "
        "this used Whisper Large v3 Turbo. If your recordings switch language, make "
        "Whisper Large v3 Turbo your default in Settings."
    ]


def test_only_the_end_window_outside_still_routes_to_whisper(rig):
    rig.tiny_says = [("en", 0.97), ("en", 0.9), ("ja", 0.3)]
    r = run("auto")
    assert r.model == "large-v3-turbo" and not rig.parakeet


def test_all_windows_covered_runs_parakeet(rig):
    rig.tiny_says = [("de", 0.4), ("en", 0.9), ("en", 0.8)]
    r = run("auto")
    assert r.model == "parakeet-v3" and r.language == "en" and r.notes == []
    assert list(rig.parakeet) == ["parakeet-v3"] and not rig.whisper


def test_unsure_uses_a_ready_whisper_without_forcing_a_language(rig):
    rig.tiny_says = [("en", 0.3), ("en", 0.45)]
    r = run("auto")
    assert r.model == "large-v3-turbo" and not rig.parakeet
    assert rig.whisper["large-v3-turbo"].calls[0]["language"] is None
    assert r.notes == [
        "The language check couldn't tell what language this is, so this used "
        "Whisper Large v3 Turbo instead of Parakeet v3."
    ]


def test_unsure_without_whisper_runs_parakeet_and_says_so(rig):
    rig.tiny_says, rig.cached = [("en", 0.3)], {"parakeet-v3", "tiny"}
    r = run("auto")
    assert r.model == "parakeet-v3" and not rig.whisper
    assert r.notes == [
        "The language check couldn't tell what language this is, so Parakeet v3 ran "
        "anyway. If the text looks wrong, set your language in Settings."
    ]


def test_no_speech_counts_as_unsure(rig):
    rig.tiny_says = []
    r = run("auto")
    assert r.model == "large-v3-turbo" and r.notes[0].startswith(
        "The language check couldn't tell"
    )


def test_speech_windows_skip_leading_silence_and_spread_out(monkeypatch):
    """The windows cover speech only: start, middle and end of it."""
    import faster_whisper.vad as vad

    sr = 16_000
    audio = np.zeros(sr * 100, dtype=np.float32)
    audio[sr * 10 :] = np.arange(sr * 90, dtype=np.float32)  # marks each speech sample
    monkeypatch.setattr(
        vad, "get_speech_timestamps", lambda a, o: [{"start": sr * 10, "end": sr * 100}]
    )
    wins = local_mod._speech_windows(audio)
    assert [(int(w[0]) // sr, len(w) // sr) for w in wins] == [(0, 30), (30, 30), (60, 30)]
    monkeypatch.setattr(vad, "get_speech_timestamps", lambda a, o: [])
    assert local_mod._speech_windows(audio) == []
    monkeypatch.setattr(
        vad, "get_speech_timestamps", lambda a, o: [{"start": sr * 10, "end": sr * 50}]
    )
    wins = local_mod._speech_windows(audio)
    assert [(int(w[0]) // sr, len(w) // sr) for w in wins] == [(0, 30), (10, 30)]


# ── note propagation: provider → ProcessResult → markdown ────────


@pytest.fixture
def pipeline(tmp_path, monkeypatch, rig):
    from anyscribe.core import dedup, migrate, orchestrator, preflight
    from anyscribe.downloaders.base import DownloadResult
    from anyscribe.vault import index, writer

    ws = tmp_path / "workspace"
    for mod in (dedup, writer, index):
        monkeypatch.setattr(mod, "get_workspace_dir", lambda: ws)
    monkeypatch.setattr(orchestrator, "TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(orchestrator, "RECOVERY_DIR", tmp_path / "recovery")
    monkeypatch.setattr(migrate, "maybe_migrate_workspace", lambda: None)
    monkeypatch.setattr(migrate, "maybe_migrate_media_to_downloads", lambda: None)
    monkeypatch.setattr(migrate, "maybe_flatten_date_folders", lambda: 0)
    monkeypatch.setattr(preflight, "preflight_check", lambda settings, url: None)

    class Dl:
        def download(self, url, out):
            audio = out / "a.mp3"
            audio.write_bytes(b"x")
            return DownloadResult(
                audio_path=audio,
                title="Voice note",
                duration=5.0,
                platform="local",
                original_url=url,
            )

    monkeypatch.setattr(orchestrator, "get_downloader", lambda url: Dl())
    return ws


def _settings():
    from anyscribe.config.settings import Settings

    s = Settings()
    s.provider = "local"
    s.output_format = "timestamped"
    return s


def test_switch_note_reaches_result_and_markdown(pipeline, rig):
    from anyscribe.core.orchestrator import process

    rig.tiny_says = "hi"
    result = process("/tmp/voice-note.ogg", _settings(), quiet=True)
    assert result.model == "large-v3-turbo"
    assert result.notes and result.notes[0].startswith("Detected Hindi")
    md = result.file_path.read_text()
    assert "\nmodel: large-v3-turbo\n" in md
    assert f'  - "{result.notes[0]}"' in md  # frontmatter
    assert f"> **Note:** {result.notes[0]}" in md  # transcript details


def test_parakeet_run_records_model_and_timestamps(pipeline, rig):
    from anyscribe.core.orchestrator import process

    result = process("/tmp/voice-note.ogg", _settings(), quiet=True)
    md = result.file_path.read_text()
    assert result.model == "parakeet-v3" and result.notes == []
    assert "\nmodel: parakeet-v3\n" in md and "notes:" not in md
    assert "**[0:00]** Hello there." in md and "**[0:02]** Second part." in md


def test_guard_error_writes_nothing(pipeline, rig):
    from anyscribe.core.orchestrator import process

    rig.tiny_says, rig.cached = "hi", {"parakeet-v3", "tiny"}
    with pytest.raises(RuntimeError, match="Nothing was written"):
        process("/tmp/voice-note.ogg", _settings(), quiet=True)
    assert not (pipeline / "sources").exists() or not any((pipeline / "sources").rglob("*.md"))


def test_cli_json_carries_the_note(monkeypatch, tmp_path):
    """`anyscribe transcribe --json` merges run-time notes into `notes` and
    reports the model that actually ran."""
    import json

    from typer.testing import CliRunner

    from anyscribe.cli import transcribe as tmod
    from anyscribe.cli.main import app
    from anyscribe.core import orchestrator

    note = "Detected Hindi — Parakeet v3 doesn't cover Hindi, so this used Whisper Large v3 Turbo."
    fake = orchestrator.ProcessResult(
        file_path=tmp_path / "a.md",
        title="t",
        platform="local",
        duration="0:05",
        language="hi",
        word_count=3,
        provider="local",
        model="large-v3-turbo",
        notes=[note],
    )
    monkeypatch.setattr(orchestrator, "process", lambda *a, **k: fake)
    monkeypatch.setattr(tmod, "_validate_input", lambda u: u)
    out = CliRunner().invoke(app, ["transcribe", "x.wav", "--provider", "local", "--json"])
    data = json.loads(out.stdout)["data"]
    assert data["model"] == "large-v3-turbo" and note in data["notes"]


def _fake_result(tmp_path):
    from anyscribe.core import orchestrator

    note = "Detected Hindi — Parakeet v3 doesn't cover Hindi, so this used Whisper Large v3 Turbo."
    return note, orchestrator.ProcessResult(
        file_path=tmp_path / "a.md",
        title="t",
        platform="local",
        duration="0:05",
        language="hi",
        word_count=3,
        provider="local",
        model="large-v3-turbo",
        notes=[note],
    )


def test_mcp_transcribe_carries_the_note(monkeypatch, tmp_path):
    import json

    pytest.importorskip("mcp", reason="mcp extra not installed")
    from anyscribe.config.settings import Settings
    from anyscribe.core import orchestrator
    from anyscribe.mcp import server

    note, fake = _fake_result(tmp_path)
    monkeypatch.setattr(server, "_load_settings", lambda: Settings(provider="local"))
    monkeypatch.setattr(orchestrator, "process", lambda *a, **k: fake)
    data = json.loads(server.transcribe("x.wav"))
    assert data["model"] == "large-v3-turbo" and note in data["notes"]
    batch = json.loads(server.batch_transcribe(["x.wav"]))["results"][0]
    assert batch["model"] == "large-v3-turbo" and batch["notes"] == [note]


def test_web_job_result_carries_the_note(monkeypatch, tmp_path):
    import asyncio

    from anyscribe.config.settings import Settings
    from anyscribe.core import orchestrator
    from anyscribe.web.jobs import Job, job_manager

    note, fake = _fake_result(tmp_path)
    monkeypatch.setattr(orchestrator, "process", lambda *a, **k: fake)
    job = Job(id="guardtest", url="x.wav")
    loop = asyncio.new_event_loop()
    try:
        job_manager._run_job(job, Settings(provider="local"), loop)
    finally:
        loop.close()
    assert job.result["model"] == "large-v3-turbo" and job.result["notes"] == [note]


def test_parakeet_and_vad_load_on_the_cpu_provider(monkeypatch):
    """CoreML (onnxruntime's default on Apple silicon) made Parakeet load in
    110 s and run 7x slower; both loads must name the CPU provider."""
    import sys

    calls: dict[str, dict] = {}

    class FakeModel:
        def with_vad(self, vad):
            return ("parakeet+vad", vad)

    def load_model(name, **kwargs):
        calls["model"] = {"name": name, **kwargs}
        return FakeModel()

    def load_vad(name, **kwargs):
        calls["vad"] = {"name": name, **kwargs}
        return "vad"

    monkeypatch.setitem(
        sys.modules, "onnx_asr", SimpleNamespace(load_model=load_model, load_vad=load_vad)
    )
    local_mod._load_parakeet.cache_clear()
    try:
        local_mod._load_parakeet("parakeet-v3")
    finally:
        local_mod._load_parakeet.cache_clear()
    assert calls["model"] == {
        "name": "nemo-parakeet-tdt-0.6b-v3",
        "quantization": "int8",
        "providers": ["CPUExecutionProvider"],
    }
    assert calls["vad"] == {"name": "silero", "providers": ["CPUExecutionProvider"]}


# ── notes on cached runs and in batch output (C9) ────────────────


def test_cached_rerun_keeps_the_switch_note(pipeline, rig):
    from anyscribe.core.orchestrator import process

    rig.tiny_says = "hi"
    first = process("/tmp/voice-note.ogg", _settings(), quiet=True)
    again = process("/tmp/voice-note.ogg", _settings(), quiet=True)
    assert again.cached and again.model == "large-v3-turbo"
    assert again.notes == first.notes and again.notes[0].startswith("Detected Hindi")


def test_human_batch_prints_each_files_note(monkeypatch, tmp_path):
    from typer.testing import CliRunner

    from anyscribe.cli.main import app
    from anyscribe.core import orchestrator

    note, fake = _fake_result(tmp_path)
    urls = tmp_path / "urls.txt"
    urls.write_text("/tmp/a.wav\n")
    monkeypatch.setattr(orchestrator, "process", lambda *a, **k: fake)
    out = CliRunner().invoke(
        app, ["batch", str(urls), "--provider", "local"], env={"COLUMNS": "400"}
    )
    assert out.exit_code == 0, out.output
    assert "Note: " + note in " ".join(out.output.split())


# R2C1: a weak guess of an uncovered language is doubt, not a detection.
UNSURE_TURBO = (
    "The language check couldn't tell what language this is, so this used "
    "Whisper Large v3 Turbo instead of Parakeet v3."
)
UNSURE_PARAKEET = (
    "The language check couldn't tell what language this is, so Parakeet v3 ran "
    "anyway. If the text looks wrong, set your language in Settings."
)


def test_a_weak_uncovered_guess_takes_the_unsure_path_not_a_forced_language(rig):
    rig.tiny_says = [("hi", 0.2)]
    r = run("auto")
    assert r.model == "large-v3-turbo" and not rig.parakeet
    assert rig.whisper["large-v3-turbo"].calls[0]["language"] is None
    assert r.notes == [UNSURE_TURBO]


def test_a_weak_uncovered_guess_without_whisper_runs_parakeet_unsure(rig):
    rig.tiny_says, rig.cached = [("hi", 0.2)], {"parakeet-v3", "tiny"}
    r = run("auto")  # used to raise "download Turbo" for a guess it never established
    assert r.model == "parakeet-v3" and not rig.whisper
    assert r.language == "unknown" and r.notes == [UNSURE_PARAKEET]


def test_a_weak_uncovered_window_beside_sure_english_is_still_doubt(rig):
    rig.tiny_says = [("en", 0.9), ("ja", 0.3)]
    r = run("auto")
    assert r.model == "large-v3-turbo"
    assert rig.whisper["large-v3-turbo"].calls[0]["language"] is None
    assert r.notes == [UNSURE_TURBO]


def test_doubt_without_whisper_takes_the_language_from_covered_windows_only(rig):
    rig.tiny_says, rig.cached = [("ja", 0.3), ("en", 0.9)], {"parakeet-v3", "tiny"}
    r = run("auto")
    assert r.model == "parakeet-v3" and r.language == "en" and r.notes == [UNSURE_PARAKEET]


def test_a_sure_uncovered_window_still_switches_even_beside_a_weak_one(rig):
    rig.tiny_says = [("en", 0.9), ("ja", 0.3), ("hi", 0.7)]
    r = run("auto")
    assert r.model == "large-v3-turbo"
    assert rig.whisper["large-v3-turbo"].calls[0]["language"] == "hi"
    assert r.notes[0].startswith("Detected Hindi in part of this recording")
