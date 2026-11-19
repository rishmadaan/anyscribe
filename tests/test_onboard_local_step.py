"""The interactive onboarding's local step (beaupy prompts faked): what it says
about the suggestion, the second download and the result."""

from __future__ import annotations

import io

from rich.console import Console

from anyscribe.cli import onboard
from anyscribe.config.settings import Settings
from anyscribe.core import local_recommend


def _run(monkeypatch, answer, disk=100_000, confirm=True):
    out = io.StringIO()
    pulls: list[str] = []
    setups: list[str] = []
    monkeypatch.setattr(onboard, "console", Console(file=out, width=300))
    monkeypatch.setattr(onboard, "list_cached_models", lambda: [])
    monkeypatch.setattr(
        local_recommend,
        "detect_hardware",
        lambda: {
            "ram_gb": 16.0,
            "cpu_cores": 12,
            "apple_silicon": False,
            "nvidia_gpu": False,
            "free_disk_mb": disk,
        },
    )
    labels = iter([local_recommend.LANGUAGE_ANSWERS[answer], None])  # answer, then keep the default
    monkeypatch.setattr(onboard, "bselect", lambda *a, **k: next(labels))
    monkeypatch.setattr(onboard, "bconfirm", lambda *a, **k: confirm)

    def setup(model, on_progress=None):
        setups.append(model)
        return {"status": "set_up", "restart_needed": True}

    def pull(model, progress_cb=None):
        pulls.append(model)
        if progress_cb:
            progress_cb(800, 1600)
        return {"status": "downloaded"}

    monkeypatch.setattr(onboard, "run_local_setup", setup)
    monkeypatch.setattr("anyscribe.providers.local_models.pull_model", pull)
    settings = Settings()
    onboard._offer_local_setup(settings, make_primary=True)
    return " ".join(out.getvalue().split()), setups, pulls, settings


def test_mix_names_both_models_with_sizes_and_downloads_the_second(monkeypatch):
    text, setups, pulls, settings = _run(monkeypatch, "mix")
    assert "Suggested: Parakeet v3 + Whisper Large v3 Turbo" in text
    assert "Downloads 670 MB + 1.6 GB, plus the 75 MB language check." in text
    assert setups == ["parakeet-v3"] and pulls == ["large-v3-turbo"]
    assert "Downloading Whisper Large v3 Turbo (1600 MB)" in text
    assert "Default model: Parakeet v3. Also ready: Whisper Large v3 Turbo." in text
    assert "Restart anyscribe to finish setting up local transcription." in text
    assert "measured on English audio on a 6-core desktop processor" in text


def test_hindi_answer_offers_to_set_the_language(monkeypatch):
    _, setups, _, settings = _run(monkeypatch, "indian")
    assert setups == ["large-v3-turbo"] and settings.language == "hi"
    _, _, _, settings = _run(monkeypatch, "indian", confirm=False)
    assert settings.language == "auto"


def test_no_disk_space_stops_before_any_setup(monkeypatch):
    text, setups, pulls, _ = _run(monkeypatch, "english", disk=10)
    assert setups == [] and pulls == []
    assert "Not enough free disk space" in text
