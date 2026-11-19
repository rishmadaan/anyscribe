"""A model is ready only when every file its engine loads is on disk and no
blob is half-downloaded. Some bytes without that is "partial": never used as a
fallback, never shown as downloaded, and pull resumes it. Built on a real
on-disk HF cache layout in tmp_path (blobs + snapshot links), not mocks."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from anyscribe.providers import local as local_mod
from anyscribe.providers import local_models as lm

WHISPER_FILES = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt", "README.md"]
PARAKEET_ALL = ["config.json", "vocab.txt", "encoder-model.int8.onnx", "decoder_joint-model.int8.onnx"]


@pytest.fixture
def cache(tmp_path, monkeypatch):
    import huggingface_hub.constants as hc
    import huggingface_hub.utils._cache_manager as cm

    monkeypatch.setattr(hc, "HF_HUB_CACHE", str(tmp_path))
    monkeypatch.setattr(cm, "HF_HUB_CACHE", str(tmp_path))  # scan_cache_dir's own copy

    def add(repo_id, files, incomplete=False):
        repo = tmp_path / ("models--" + repo_id.replace("/", "--"))
        (repo / "blobs").mkdir(parents=True, exist_ok=True)
        snap = repo / "snapshots" / "abc123"
        snap.mkdir(parents=True, exist_ok=True)
        (repo / "refs").mkdir(exist_ok=True)
        (repo / "refs" / "main").write_text("abc123")
        for i, name in enumerate(files):
            blob = repo / "blobs" / f"{abs(hash((repo_id, name))):040x}"  # hub: a bare hash
            blob.write_bytes(b"x" * 1000)
            (snap / name).symlink_to(blob)
        if incomplete:
            (repo / "blobs" / "deadbeef.incomplete").write_bytes(b"x" * 500)

    return add


def test_complete_whisper_is_ready(cache):
    cache(lm.MODEL_REPOS["small"], WHISPER_FILES)
    assert lm.is_cached("small")
    entry = next(m for m in lm.list_cached_models() if m["size"] == "small")
    assert (entry["cached"], entry["partial"]) == (True, False)


def test_missing_weights_is_partial_not_ready(cache):
    cache(lm.MODEL_REPOS["large-v3-turbo"], ["config.json", "tokenizer.json"])
    assert not lm.is_cached("large-v3-turbo")
    entry = next(m for m in lm.list_cached_models() if m["size"] == "large-v3-turbo")
    assert (entry["cached"], entry["partial"]) == (False, True) and entry["bytes"] > 0


def test_incomplete_blob_is_partial_even_with_every_file_linked(cache):
    cache(lm.MODEL_REPOS["parakeet-v3"], PARAKEET_ALL, incomplete=True)
    assert not lm.is_cached("parakeet-v3")
    cache(lm.MODEL_REPOS["parakeet-v2"], PARAKEET_ALL)
    assert lm.is_cached("parakeet-v2")


def test_a_stale_incomplete_left_by_a_killed_download_is_ignored(cache, tmp_path):
    """huggingface_hub names temp blobs <hash>.<tag>.incomplete; a killed run
    leaves one behind even after a later run completes <hash>."""
    cache(lm.MODEL_REPOS["large-v3"], WHISPER_FILES)
    blobs = tmp_path / "models--Systran--faster-whisper-large-v3" / "blobs"
    snap = blobs.parent / "snapshots" / "abc123"
    done = (snap / "model.bin").resolve()
    (blobs / f"{done.name}.fe0a4310.incomplete").write_bytes(b"")
    assert lm.is_cached("large-v3")
    (blobs / "0123abcd.fe0a4310.incomplete").write_bytes(b"x")  # its blob never finished
    assert not lm.is_cached("large-v3")


def test_fallback_skips_a_half_downloaded_turbo_for_a_complete_small(cache):
    cache(lm.MODEL_REPOS["large-v3-turbo"], ["config.json"], incomplete=True)
    cache(lm.MODEL_REPOS["small"], WHISPER_FILES)
    assert local_mod.pick_fallback() == "small"


def test_helpers_ready_needs_both_tiny_and_the_vad(cache):
    cache(lm.MODEL_REPOS["tiny"], WHISPER_FILES)
    assert not lm.helpers_ready()
    cache(lm.VAD_REPO, ["config.json", "silero_vad.onnx"])
    assert lm.helpers_ready()


class FakeHub:
    def __init__(self):
        self.calls: list[str] = []

    def snapshot_download(self, repo_id, **kw):
        self.calls.append(repo_id)


def _pull(size, ready):
    hub = FakeHub()
    with (
        patch.object(lm, "engine_importable", return_value=True),
        patch.object(lm, "_safe_import_hub", return_value=hub),
        patch.object(lm, "is_cached", side_effect=lambda m: m in ready),
        patch.object(lm, "list_cached_models", return_value=[]),
    ):
        return hub.calls, lm.pull_model(size)


def test_pull_resumes_a_partial_download():
    calls, result = _pull("large-v3-turbo", ready=set())
    assert calls == [lm.MODEL_REPOS["large-v3-turbo"]] and result["status"] == "downloaded"


def test_pull_of_a_ready_model_still_calls_the_downloader():
    calls, result = _pull("small", ready={"small"})
    assert calls == [lm.MODEL_REPOS["small"]] and result["status"] == "already_present"


def test_web_pull_queues_a_model_that_cannot_run_yet(monkeypatch):
    """A partial Turbo, or a Parakeet missing its helpers, isn't runnable: queued."""
    from fastapi.testclient import TestClient

    from anyscribe.web.app import create_app
    from anyscribe.web.routes import models as routes

    monkeypatch.setattr(routes, "faster_whisper_importable", lambda: True)
    monkeypatch.setattr(routes, "_kick_worker", lambda app: None)
    client = TestClient(create_app())

    monkeypatch.setattr(routes, "runnable", lambda m: m == "small")
    r = client.post("/api/models/local/large-v3-turbo/pull").json()
    assert r["status"] == "started" and r["size"] == "large-v3-turbo"
    r = client.post("/api/models/local/parakeet-v3/pull").json()
    assert r["status"] == "queued" and r["size"] == "parakeet-v3"
    assert list(client.app.state.download_queue["queue"]) == ["large-v3-turbo", "parakeet-v3"]
    r = client.post("/api/models/local/small/pull").json()
    assert r == {"status": "already_present", "size": "small"}


def test_runnable_parakeet_needs_tiny_and_the_vad_on_disk(cache, monkeypatch):
    """Real cache layout: Parakeet's weights alone are "cached" but not runnable."""
    monkeypatch.setattr(lm, "engine_importable", lambda m: True)
    monkeypatch.setattr(lm, "faster_whisper_importable", lambda: True)
    monkeypatch.setattr(lm, "onnx_asr_importable", lambda: True)
    cache(lm.MODEL_REPOS["parakeet-v3"], PARAKEET_ALL)
    entry = next(m for m in lm.list_cached_models() if m["size"] == "parakeet-v3")
    assert (entry["cached"], entry["runnable"], lm.runnable("parakeet-v3")) == (True, False, False)
    cache(lm.MODEL_REPOS["tiny"], WHISPER_FILES)
    assert not lm.runnable("parakeet-v3")  # VAD still missing
    cache(lm.VAD_REPO, ["config.json", "silero_vad.onnx"])
    entry = next(m for m in lm.list_cached_models() if m["size"] == "parakeet-v3")
    assert (entry["runnable"], lm.runnable("parakeet-v3")) == (True, True)


def test_runnable_needs_the_engine(cache, monkeypatch):
    cache(lm.MODEL_REPOS["small"], WHISPER_FILES)
    monkeypatch.setattr(lm, "engine_importable", lambda m: False)
    monkeypatch.setattr(lm, "faster_whisper_importable", lambda: False)
    entry = next(m for m in lm.list_cached_models() if m["size"] == "small")
    assert (entry["cached"], entry["runnable"], lm.runnable("small")) == (True, False, False)


def test_making_parakeet_the_default_is_refused_until_it_can_run(monkeypatch, tmp_path):
    """Replaces "queues its helpers": PUT /api/config no longer switches first
    and downloads after. The default stays exactly what it was, nothing queued."""
    from fastapi.testclient import TestClient

    from anyscribe.config import paths, settings
    from anyscribe.web.app import create_app

    cfg = tmp_path / "config.yaml"
    monkeypatch.setattr(paths, "CONFIG_FILE", cfg)
    monkeypatch.setattr(settings, "CONFIG_FILE", cfg)
    settings.save_config(settings.Settings(local_model="large-v3-turbo"))
    monkeypatch.setattr(lm, "runnable", lambda m: m != "parakeet-v3")
    client = TestClient(create_app())
    r = client.put("/api/config", json={"local_model": "parakeet-v3"})
    assert r.status_code == 422 and "anyscribe model pull parakeet-v3" in r.json()["error"]
    assert settings.load_config().local_model == "large-v3-turbo"
    assert getattr(client.app.state, "download_queue", {"queue": []})["queue"] == []
