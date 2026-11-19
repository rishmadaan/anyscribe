"""Pulling a Parakeet model fetches only its int8 files, plus the helpers a
run needs (Silero VAD, Whisper Tiny for the language check), so a run never
downloads anything silently. The hub is faked; calls are recorded."""

from __future__ import annotations

from unittest.mock import patch

from anyscribe.providers import local_models as lm


class FakeHub:
    def __init__(self):
        self.calls: list[tuple[str, tuple | None]] = []

    def snapshot_download(self, repo_id, allow_patterns=None, **kw):
        self.calls.append((repo_id, tuple(allow_patterns) if allow_patterns else None))


def _pull(model_id, cached):
    hub = FakeHub()
    with (
        patch.object(lm, "engine_importable", return_value=True),
        patch.object(lm, "_safe_import_hub", return_value=hub),
        patch.object(lm, "is_cached", side_effect=lambda m: m in cached),
        patch.object(lm, "list_cached_models", return_value=[]),
    ):
        result = lm.pull_model(model_id)
    return hub.calls, result


def test_parakeet_pull_fetches_int8_files_vad_and_tiny():
    calls, result = _pull("parakeet-v3", cached=set())
    assert calls == [
        ("istupakov/parakeet-tdt-0.6b-v3-onnx", tuple(lm.PARAKEET_FILES)),
        ("istupakov/silero-vad-onnx", tuple(lm.VAD_FILES)),
        ("Systran/faster-whisper-tiny", None),
    ]
    assert result["helpers_downloaded"] == ["tiny"]


def test_parakeet_pull_skips_tiny_when_cached():
    calls, result = _pull("parakeet-v3", cached={"tiny"})
    assert [c[0] for c in calls] == [
        "istupakov/parakeet-tdt-0.6b-v3-onnx",
        "istupakov/silero-vad-onnx",
    ]
    assert "helpers_downloaded" not in result


def test_whisper_pull_fetches_only_its_repo():
    calls, _ = _pull("small", cached=set())
    assert calls == [("Systran/faster-whisper-small", None)]


def test_delete_all_also_removes_the_vad_helper():
    with (
        patch.object(lm, "delete_model", return_value={"status": "not_present", "bytes_freed": 0}),
        patch.object(lm, "_delete_repo", return_value=2_000_000) as rm,
    ):
        out = lm.delete_all_models()
    rm.assert_called_once_with(lm.VAD_REPO)
    assert out["bytes_freed"] == 2_000_000
