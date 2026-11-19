"""The server owns "choose a local model": the default switches only once the
chosen model can run, a later choice replaces an earlier one, a failure keeps
the old default, and setup downloads the extras itself. Downloads are faked;
each assertion names WHICH model is the default and WHICH models were queued."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from anyscribe.config import paths, settings
from anyscribe.providers import local_models as lm
from anyscribe.web.app import create_app
from anyscribe.web.routes import local as local_routes
from anyscribe.web.routes import models as routes


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Config on tmp_path with Turbo as the default; ``ready`` is the set of
    models that can run; ``pull`` makes a model ready unless ``fail`` names it.
    The worker is run by hand (``drain``) so the test controls the order."""
    cfg = tmp_path / "config.yaml"
    monkeypatch.setattr(paths, "CONFIG_FILE", cfg)
    monkeypatch.setattr(settings, "CONFIG_FILE", cfg)
    settings.save_config(settings.Settings(local_model="large-v3-turbo"))

    class W:
        ready = {"large-v3-turbo", "tiny"}
        fail: dict[str, str] = {}
        pulled: list[str] = []
        weights_only: set[str] = set()  # pull lands the weights but not the helpers

    def runnable(m):
        return m in W.ready

    def pull(size, progress_cb=None):
        W.pulled.append(size)
        if size in W.fail:
            raise RuntimeError(W.fail[size])
        if size not in W.weights_only:
            W.ready.add(size)
        return {"status": "downloaded", "size": size}

    monkeypatch.setattr(lm, "runnable", runnable)  # config_set's guard reads it here
    monkeypatch.setattr(routes, "runnable", runnable)
    monkeypatch.setattr(local_routes, "runnable", runnable)
    monkeypatch.setattr(routes, "pull_model", pull)
    monkeypatch.setattr(routes, "engine_importable", lambda m: True)
    monkeypatch.setattr(routes, "_kick_worker", lambda app: None)
    monkeypatch.setattr(local_routes, "faster_whisper_importable", lambda: True)
    W.client = TestClient(create_app())
    W.app = W.client.app

    def drain():
        routes._download_state(W.app)["worker_running"] = True
        routes._worker_loop(W.app)

    W.drain = drain
    W.queue = lambda: list(routes._download_state(W.app)["queue"])
    W.default = lambda: settings.load_config().local_model
    return W


def test_choosing_a_not_ready_model_keeps_the_default_until_it_can_run(world):
    r = world.client.post("/api/local/choose", json={"model": "parakeet-v3"}).json()
    assert r["status"] == "pending" and world.queue() == ["parakeet-v3"]
    assert world.default() == "large-v3-turbo"
    pending = world.client.get("/api/local/status").json()["pending_default"]
    assert pending == {"model": "parakeet-v3", "also": [], "state": "downloading", "error": None}
    world.drain()
    assert world.default() == "parakeet-v3"
    assert world.client.get("/api/local/status").json()["pending_default"] is None


def test_weights_done_but_helper_failed_keeps_the_old_default(world):
    """The R2C3 gap: Parakeet's weights land, its language check fails."""
    world.weights_only = {"parakeet-v3"}
    world.fail = {"parakeet-v3": "Whisper Tiny: connection reset"}
    world.client.post("/api/local/choose", json={"model": "parakeet-v3"})
    world.drain()
    assert world.default() == "large-v3-turbo"
    pending = world.client.get("/api/local/status").json()["pending_default"]
    assert pending["model"] == "parakeet-v3" and pending["state"] == "failed"
    assert pending["error"] == "Whisper Tiny: connection reset"


def test_a_pull_that_returns_without_making_it_runnable_does_not_switch(world):
    world.weights_only = {"parakeet-v3"}
    world.client.post("/api/local/choose", json={"model": "parakeet-v3"})
    world.drain()
    assert world.default() == "large-v3-turbo"
    pending = world.client.get("/api/local/status").json()["pending_default"]
    assert pending["state"] == "failed" and "isn't ready to use yet" in pending["error"]


def test_a_later_choice_replaces_the_earlier_one(world):
    world.client.post("/api/local/choose", json={"model": "large-v3"})
    world.client.post("/api/local/choose", json={"model": "small"})
    assert world.queue() == ["large-v3", "small"]
    world.drain()  # large-v3 finishes first, then small
    assert world.pulled == ["large-v3", "small"]
    assert world.default() == "small"


def test_a_later_ready_choice_cancels_the_pending_one(world):
    world.client.post("/api/local/choose", json={"model": "large-v3"})
    r = world.client.post("/api/local/choose", json={"model": "tiny"}).json()
    assert r["status"] == "switched" and world.default() == "tiny"
    world.drain()  # large-v3 still downloads, but is no longer the choice
    assert world.default() == "tiny"


def test_a_ready_model_switches_at_once_and_queues_only_extras_that_cannot_run(world):
    world.ready.add("parakeet-v3")
    r = world.client.post(
        "/api/local/choose", json={"model": "parakeet-v3", "also": ["large-v3-turbo", "medium"]}
    ).json()
    assert r["status"] == "switched" and world.default() == "parakeet-v3"
    assert world.queue() == ["medium"]


def test_choose_queues_the_model_then_its_extras_and_switches_on_the_model(world):
    world.fail = {"large-v3": "disk full"}
    world.client.post("/api/local/choose", json={"model": "parakeet-v3", "also": ["large-v3"]})
    assert world.queue() == ["parakeet-v3", "large-v3"]
    world.drain()
    assert world.default() == "parakeet-v3"  # an extra failing doesn't undo the switch
    models = {m["size"]: m for m in world.client.get("/api/local/status").json()["models"]}
    assert models["large-v3"]["last_error"] == "disk full"


def test_setup_queues_the_extras_itself(world, monkeypatch):
    """R2C4 / extras lost on closing the wizard: the server queues them after
    setup, whatever the page does."""
    world.ready.add("parakeet-v3")
    calls: list[str] = []

    def fake_setup(model, on_progress=None, activate=None):
        calls.append(model)
        return {"status": "set_up", "default_model": model}

    monkeypatch.setattr(local_routes, "run_setup", fake_setup)
    r = world.client.post(
        "/api/local/setup", json={"model": "parakeet-v3", "also": ["large-v3-turbo", "medium"]}
    )
    assert r.json()["also"] == ["large-v3-turbo", "medium"]
    deadline = time.time() + 5
    while world.client.get("/api/local/status").json()["setup_running"] and time.time() < deadline:
        time.sleep(0.02)
    assert calls == ["parakeet-v3"]
    assert world.queue() == ["medium"]  # Turbo can already run
    assert world.client.get("/api/local/status").json()["setup_also"] == [
        "large-v3-turbo",
        "medium",
    ]


def test_failed_setup_queues_no_extras(world, monkeypatch):
    monkeypatch.setattr(
        local_routes, "run_setup", lambda model, on_progress=None: {"status": "failed", "error": "x"}
    )
    world.client.post("/api/local/setup", json={"model": "parakeet-v3", "also": ["medium"]})
    deadline = time.time() + 5
    while world.client.get("/api/local/status").json()["setup_running"] and time.time() < deadline:
        time.sleep(0.02)
    assert world.queue() == []


def test_choose_rejects_an_unknown_model(world):
    r = world.client.post("/api/local/choose", json={"model": "parakeet-v3", "also": ["huge"]})
    assert r.status_code == 400 and world.queue() == []


def test_set_value_refuses_a_model_that_cannot_run_and_names_the_command(world):
    from anyscribe.core.config_set import set_value

    out = set_value("local_model", "parakeet-v3")
    assert not out.ok and "`anyscribe model pull parakeet-v3`" in out.error
    assert world.default() == "large-v3-turbo"
    assert set_value("local_model", "tiny").ok and world.default() == "tiny"


def test_set_value_keeps_an_unchanged_default_that_cannot_run(world):
    """Only a change is guarded: a fresh config's never-downloaded "base" can
    be re-saved alongside other fields."""
    from anyscribe.core.config_set import set_value

    settings.save_config(settings.Settings(local_model="base"))
    assert set_value("local_model", "base").ok


def test_headless_local_onboarding_switches_only_after_setup(world, monkeypatch):
    from anyscribe.core import local_setup, onboard_headless

    seen: list[str] = []

    def fake_setup(model, on_progress=None):
        seen.append(settings.load_config().local_model)  # the default while it downloads
        return {"status": "failed", "phase": "download", "error": "offline"}

    monkeypatch.setattr(local_setup, "run_setup", fake_setup)
    result = onboard_headless.run_headless_onboard(
        "local", local_model="parakeet-v3", install_skill=False
    )
    assert result["status"] == "partial"
    assert seen == ["large-v3-turbo"] and world.default() == "large-v3-turbo"


def test_headless_onboarding_refuses_a_local_model_that_cannot_run(world, monkeypatch):
    from anyscribe.core import onboard_headless

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(onboard_headless.OnboardValidationError) as exc:
        onboard_headless.run_headless_onboard(
            "openai", local_model="parakeet-v3", install_skill=False
        )
    assert "anyscribe local setup --model parakeet-v3" in exc.value.payload["hint"]
    assert world.default() == "large-v3-turbo"
