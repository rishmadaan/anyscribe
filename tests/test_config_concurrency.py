"""Round-3 concurrency findings, each forced into its bad interleaving.

R3C1: a background save of the local model must not erase a foreground save
(PUT /api/config) that lands while it runs. R3C2: ``choose`` answers from what
it decided, even when the worker or a second choose finishes first. R3C3: an
older setup finishing must not replace a choice made after it started.
Downloads are faked; every assertion names which provider, quality and model
survived, never a count.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from anyscribe.config import paths, settings
from anyscribe.core import config_set, local_setup
from anyscribe.providers import local_models as lm
from anyscribe.web.app import create_app
from anyscribe.web.routes import local as local_routes
from anyscribe.web.routes import models as routes


@pytest.fixture
def world(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    monkeypatch.setattr(paths, "CONFIG_FILE", cfg)
    monkeypatch.setattr(settings, "CONFIG_FILE", cfg)
    settings.save_config(
        settings.Settings(provider="openai", quality="balanced", local_model="large-v3-turbo")
    )

    class W:
        ready = {"large-v3-turbo", "tiny", "small"}
        guard = None  # optional hook run inside config_set's runnable check

    def runnable(m):
        if W.guard:
            W.guard(m)
        return m in W.ready

    def pull(size, progress_cb=None):
        W.ready.add(size)
        return {"status": "downloaded", "size": size}

    monkeypatch.setattr(lm, "runnable", runnable)
    monkeypatch.setattr(routes, "pull_model", pull)
    monkeypatch.setattr(routes, "_kick_worker", lambda app: None)  # run by hand: drain()
    monkeypatch.setattr(routes, "runnable", runnable)
    monkeypatch.setattr(local_routes, "runnable", runnable)
    monkeypatch.setattr(routes, "engine_importable", lambda m: True)
    monkeypatch.setattr(local_routes, "faster_whisper_importable", lambda: True)
    W.client = TestClient(create_app())
    W.app = W.client.app
    W.cfg = lambda: settings.load_config()

    def drain():
        routes._download_state(W.app)["worker_running"] = True
        routes._worker_loop(W.app)

    W.drain = drain
    return W


# R3C1 ----------------------------------------------------------------------


def test_background_model_save_keeps_a_foreground_provider_save(world):
    """The worker's set_value("local_model") pauses between its read and its
    save; a PUT of the provider arrives in that gap. Both must survive."""
    inside, release = threading.Event(), threading.Event()

    def pause_once(m):
        if m == "small" and not inside.is_set():
            inside.set()
            release.wait(5)

    world.guard = pause_once
    bg = threading.Thread(target=config_set.set_value, args=("local_model", "small"))
    bg.start()
    assert inside.wait(5)
    put = {}
    fg = threading.Thread(
        target=lambda: put.update(r=world.client.put("/api/config", json={"provider": "local"}))
    )
    fg.start()
    fg.join(0.5)  # without the lock the PUT finishes here, inside the gap
    release.set()
    bg.join(5)
    fg.join(5)
    assert put["r"].status_code == 200
    c = world.cfg()
    assert (c.provider, c.quality, c.local_model) == ("local", "custom", "small")


def test_tailnet_failure_undo_keeps_a_background_model_save(world):
    """PUT keep_media + tailnet; the tailnet part fails after the worker saved
    a new model. The undo puts keep_media back and keeps the worker's model."""

    def save_and_apply(wanted):
        config_set.set_value("local_model", "small")  # the worker, meanwhile
        return config_set.SetOutcome(False, error="disk full")

    world.app.state.tailnet = SimpleNamespace(save_and_apply=save_and_apply)
    r = world.client.put("/api/config", json={"keep_media": True, "tailnet": True})
    assert r.status_code == 422 and r.json()["error"] == "disk full"
    c = world.cfg()
    assert (c.keep_media, c.tailnet, c.local_model) == (False, False, "small")
    assert (c.provider, c.quality) == ("openai", "balanced")


def test_put_rollback_keeps_a_background_save_made_mid_request(world, monkeypatch):
    """PUT language (valid) + output_format (invalid): after the first field
    saves, the worker saves a model. The 422 rollback undoes the language and
    keeps the worker's model (it waits for the PUT instead of landing in it)."""
    from anyscribe.web.routes import config as config_routes

    real = config_routes.set_value
    bg = []

    def set_value(key, value):
        out = real(key, value)
        if key == "language":
            t = threading.Thread(target=config_set.set_value, args=("local_model", "small"))
            t.start()
            t.join(0.5)  # without the PUT's lock it saves now, before the rollback
            bg.append(t)
        return out

    monkeypatch.setattr(config_routes, "set_value", set_value)
    r = world.client.put("/api/config", json={"language": "hi", "output_format": "nope"})
    bg[0].join(5)
    assert r.status_code == 422
    c = world.cfg()
    assert (c.language, c.output_format, c.local_model) == ("auto", "clean", "small")


def test_tailnet_failure_with_no_config_leaves_no_config(world):
    """With nothing else writing, the undo is the exact old state: no file."""
    paths.CONFIG_FILE.unlink()
    world.app.state.tailnet = SimpleNamespace(
        save_and_apply=lambda wanted: config_set.SetOutcome(False, error="disk full")
    )
    r = world.client.put("/api/config", json={"keep_media": True, "tailnet": True})
    assert r.status_code == 422 and not paths.CONFIG_FILE.exists()


# R3C2 ----------------------------------------------------------------------


def test_choose_answers_after_the_worker_already_finished(world, monkeypatch):
    """The worker switches the default before choose builds its reply."""
    monkeypatch.setattr(routes, "_kick_worker", lambda app: world.drain())
    r = world.client.post("/api/local/choose", json={"model": "parakeet-v3"})
    assert r.status_code == 200
    assert r.json() == {
        "status": "pending",
        "pending": {"model": "parakeet-v3", "also": [], "state": "downloading", "error": None},
        "queued": ["parakeet-v3"],
    }
    assert world.cfg().local_model == "parakeet-v3"


def test_choose_answers_when_a_second_choose_finished_first(world, monkeypatch):
    """While the first choose queues Parakeet, a second picks the ready Tiny."""
    real = routes.enqueue_pull

    def enqueue(app, size):
        if size == "parakeet-v3":
            assert routes.choose(app, "tiny", [])["status"] == "switched"
        return real(app, size)

    monkeypatch.setattr(routes, "enqueue_pull", enqueue)
    r = world.client.post("/api/local/choose", json={"model": "parakeet-v3"})
    assert r.status_code == 200
    assert r.json()["pending"]["model"] == "parakeet-v3"
    assert r.json()["queued"] == ["parakeet-v3"]
    world.drain()  # Parakeet lands; the later choice (Tiny) stays the default
    assert world.cfg().local_model == "tiny"


# R3C3 ----------------------------------------------------------------------


def _setup_world(world, monkeypatch, hold: str | None = None):
    """Fake setup: install succeeds; pulling ``hold`` waits for ``release``."""
    started, release = threading.Event(), threading.Event()

    def pull(size, progress_cb=None):
        if size == hold:
            started.set()
            release.wait(5)
        world.ready.add(size)
        return {"status": "downloaded", "size": size, "bytes": 0}

    monkeypatch.setattr(
        local_setup, "install_faster_whisper", lambda on_progress=None: {"status": "installed"}
    )
    monkeypatch.setattr(local_setup, "pull_model", pull)
    return started, release


def _wait_setup(world) -> dict:
    state = local_routes._setup_state(world.app)
    for _ in range(250):
        if not state["running"]:
            break
        time.sleep(0.02)
    assert not state["running"]
    return world.client.get("/api/local/status").json()


def test_a_choose_made_during_setup_wins_over_the_setup(world, monkeypatch):
    started, release = _setup_world(world, monkeypatch, hold="parakeet-v3")
    # TestClient's POST returns only once the setup thread ends, so send it from a thread
    post = {}
    t = threading.Thread(
        target=lambda: post.update(
            r=world.client.post("/api/local/setup", json={"model": "parakeet-v3"})
        )
    )
    t.start()
    assert started.wait(5)
    r = world.client.post("/api/local/choose", json={"model": "small"}).json()
    assert r == {"status": "switched", "default": "small", "queued": []}
    release.set()
    t.join(5)
    assert post["r"].json() == {"status": "started", "model": "parakeet-v3", "also": []}
    status = _wait_setup(world)
    assert world.cfg().local_model == "small"
    assert (status["setup_outcome"], status["setup_error"], status["default_model"]) == (
        "superseded",
        None,
        "small",
    )


def test_a_choice_pending_before_setup_never_switches_after_it(world, monkeypatch):
    """Choose Parakeet (still downloading), then run setup of Base. Parakeet's
    download finishing later must not replace the newer setup's Base."""
    _setup_world(world, monkeypatch)
    assert (
        world.client.post("/api/local/choose", json={"model": "parakeet-v3"}).json()["status"]
        == "pending"
    )
    assert world.client.post("/api/local/setup", json={"model": "base"}).status_code == 200
    _wait_setup(world)
    assert world.cfg().local_model == "base"
    world.drain()  # the older choice's download lands now
    assert world.cfg().local_model == "base"
    status = world.client.get("/api/local/status").json()
    assert (status["setup_outcome"], status["pending_default"]) == ("set_up", None)


def test_a_pending_choose_made_during_setup_also_wins(world, monkeypatch):
    """During a held setup of Parakeet, choose Base (not downloaded): its
    download lands and switches first; the older setup must not switch after."""
    world.ready.discard("base")
    started, release = _setup_world(world, monkeypatch, hold="parakeet-v3")
    post = {}
    t = threading.Thread(
        target=lambda: post.update(
            r=world.client.post("/api/local/setup", json={"model": "parakeet-v3"})
        )
    )
    t.start()
    assert started.wait(5)
    assert world.client.post("/api/local/choose", json={"model": "base"}).json()["status"] == (
        "pending"
    )
    world.drain()  # Base lands while setup still downloads
    assert world.cfg().local_model == "base"
    release.set()
    t.join(5)
    status = _wait_setup(world)
    assert world.cfg().local_model == "base"
    assert status["setup_outcome"] == "superseded"
