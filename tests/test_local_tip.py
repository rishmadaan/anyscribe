"""R3F2: Settings' Parakeet tip points at the card on the web (the CLI and
MCP keep the command), and is hidden while a chosen model is still on its way
or its switch just failed."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from anyscribe.config import paths, settings
from anyscribe.core import local_setup
from anyscribe.providers import local_models as lm
from anyscribe.web.app import create_app
from anyscribe.web.routes import local as local_routes
from anyscribe.web.routes import models as routes

WEB_END = "Try it: click the Parakeet v3 card below."
CLI_END = "Try it: anyscribe local setup --model parakeet-v3"


@pytest.fixture
def client(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    monkeypatch.setattr(paths, "CONFIG_FILE", cfg)
    monkeypatch.setattr(settings, "CONFIG_FILE", cfg)
    settings.save_config(settings.Settings(local_model="large-v3-turbo"))
    ready = {"large-v3-turbo", "tiny"}
    for mod in (lm, routes, local_routes):
        monkeypatch.setattr(mod, "runnable", lambda m: m in ready)
    monkeypatch.setattr(routes, "_kick_worker", lambda app: None)  # Parakeet stays downloading
    monkeypatch.setattr(local_routes, "faster_whisper_importable", lambda: True)
    return TestClient(create_app())


def tip(client):
    return client.get("/api/local/status").json()["suggestion"]


def test_web_tip_points_at_the_card_and_the_cli_keeps_the_command(client):
    assert tip(client).endswith(WEB_END)
    assert local_setup.check_status()["suggestion"].endswith(CLI_END)


def test_no_tip_while_the_chosen_model_downloads_or_after_its_switch_failed(client):
    assert (
        client.post("/api/local/choose", json={"model": "parakeet-v3"}).json()["status"]
        == "pending"
    )
    assert tip(client) is None
    state = routes._download_state(client.app)
    state["pending"].update(state="failed", error="connection reset")
    status = client.get("/api/local/status").json()
    assert (status["suggestion"], status["pending_default"]["state"]) == (None, "failed")
