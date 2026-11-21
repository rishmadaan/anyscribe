"""App mode (ANYSCRIBE_APP=1): the engine the Mac app starts never updates itself or
touches the Claude Code skill, and installs the local engines with the app's own pip."""

from __future__ import annotations

import sys

import pytest
from typer.testing import CliRunner

from anyscribe import __version__
from anyscribe.cli import skill_cmd
from anyscribe.cli.main import app
from anyscribe.config import paths
from anyscribe.core import local_setup, updater
from anyscribe.core.appmode import APP_UPDATE_MESSAGE

runner = CliRunner()


@pytest.fixture
def app_mode(monkeypatch):
    monkeypatch.setenv("ANYSCRIBE_APP", "1")


@pytest.fixture
def no_subprocess(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError(f"ran a command in app mode: {a}")

    monkeypatch.setattr(updater.subprocess, "run", refuse)


@pytest.mark.parametrize("args", [["update"], ["update", "--check"]])
def test_update_says_the_app_updates_itself_and_runs_nothing(app_mode, no_subprocess, args):
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert result.output.strip() == APP_UPDATE_MESSAGE


@pytest.fixture
def stale_skill(tmp_path, monkeypatch):
    """Claude Code present with an old anyscribe skill and a superseded 'scribe' skill dir."""
    claude = tmp_path / ".claude"
    target = claude / "skills" / "anyscribe"
    monkeypatch.setattr(paths, "CLAUDE_HOME", claude)
    monkeypatch.setattr(paths, "CLAUDE_SKILLS_DIR", claude / "skills")
    monkeypatch.setattr(paths, "ASCLI_SKILL_TARGET", target)
    monkeypatch.setattr(skill_cmd, "ASCLI_SKILL_TARGET", target)
    target.mkdir(parents=True)
    (target / ".version").write_text("0.0.1")
    (target / "SKILL.md").write_text("old skill")
    (claude / "skills" / "scribe").mkdir()
    return claude / "skills"


def _snapshot(folder):
    return {
        str(p.relative_to(folder)): p.read_bytes() if p.is_file() else None
        for p in sorted(folder.rglob("*"))
    }


def test_starting_in_app_mode_leaves_the_skill_folder_untouched(
    app_mode, no_subprocess, stale_skill
):
    before = _snapshot(stale_skill)
    assert runner.invoke(app, ["update", "--check"]).exit_code == 0
    assert _snapshot(stale_skill) == before


def test_outside_app_mode_the_same_start_does_update_the_skill(
    monkeypatch, no_subprocess, stale_skill
):
    """The control: proves the folder check above can see a skill write."""
    monkeypatch.delenv("ANYSCRIBE_APP", raising=False)
    monkeypatch.setattr(updater, "get_install_type", lambda: "app")  # still no network
    runner.invoke(app, ["update", "--check"])
    assert (stale_skill / "anyscribe" / ".version").read_text() == __version__
    assert not (stale_skill / "scribe").exists()


@pytest.mark.parametrize("other", ["0", "", "true"])
def test_only_the_exact_value_1_is_app_mode(monkeypatch, other):
    monkeypatch.setenv("ANYSCRIBE_APP", other)
    assert updater.get_install_type() != "app"
    assert local_setup.detect_install_method() != "app"


def test_local_engines_install_with_the_apps_own_pip_and_say_app(app_mode, monkeypatch):
    # Even with no pip importable and uv on PATH, the app uses its own pip.
    monkeypatch.setattr(local_setup, "local_runtime_ready", lambda: False)
    monkeypatch.setattr(local_setup, "_pip_available", lambda: False)
    monkeypatch.setattr(local_setup.shutil, "which", lambda name: f"/usr/bin/{name}")
    ran, events = [], []
    monkeypatch.setattr(
        local_setup, "_run", lambda cmd, timeout=600: ran.append(cmd) or (0, "", "")
    )
    result = local_setup.install_faster_whisper(on_progress=events.append)
    pip = [sys.executable, "-m", "pip", "install", *local_setup.LOCAL_RUNTIME_SPECS]
    assert ran == [pip] and result["method"] == "app"
    assert events[0] == {"event": "installing_package", "method": "app", "command": pip}

    monkeypatch.setattr(local_setup, "faster_whisper_importable", lambda: True)
    ran.clear()
    result = local_setup.uninstall_faster_whisper()
    remove = [sys.executable, "-m", "pip", "uninstall", "-y", *local_setup.LOCAL_RUNTIME_PACKAGES]
    assert ran == [remove] and result["method"] == "app"


# ── Onboarding never installs the skill in app mode ──────────


@pytest.fixture
def wizard(tmp_path, monkeypatch):
    """The web wizard's save route against a throwaway home holding a fake ~/.claude."""
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from anyscribe.config import settings
    from anyscribe.core import onboard_headless
    from anyscribe.web.app import create_app

    claude = tmp_path / ".claude"
    claude.mkdir()
    target = claude / "skills" / "anyscribe"
    monkeypatch.setattr(onboard_headless, "CLAUDE_HOME", claude)
    monkeypatch.setattr(skill_cmd, "ASCLI_SKILL_TARGET", target)
    monkeypatch.setattr(settings, "CONFIG_FILE", tmp_path / ".anyscribe" / "config.yaml")
    monkeypatch.setattr(settings, "ENV_FILE", tmp_path / ".anyscribe" / ".env")
    monkeypatch.setattr(onboard_headless, "ensure_app_dirs", lambda: None)
    with patch("anyscribe.vault.scaffold.create_vault", return_value=tmp_path / "vault"):
        yield TestClient(create_app()), target


def test_onboarding_in_the_app_leaves_the_skill_uninstalled(app_mode, wizard):
    client, target = wizard
    r = client.post("/api/onboarding/save", json={"provider": "openai", "api_key": "sk-test"})
    assert r.status_code == 200, r.text
    # (what the response says, whether ~/.claude/skills/anyscribe exists)
    assert (r.json()["skill_installed"], target.exists()) == (False, False)


def test_onboarding_outside_the_app_still_installs_the_skill(monkeypatch, wizard):
    monkeypatch.delenv("ANYSCRIBE_APP", raising=False)
    client, target = wizard
    r = client.post("/api/onboarding/save", json={"provider": "openai", "api_key": "sk-test"})
    assert r.status_code == 200, r.text
    assert r.json()["skill_installed"] is True
    assert (target / ".version").read_text() == __version__


def test_agent_onboarding_in_the_app_leaves_the_skill_uninstalled(tmp_path):
    """The agent path, as a real process with a throwaway HOME holding a fake ~/.claude."""
    import json
    import os
    import subprocess

    (tmp_path / ".claude").mkdir()
    env = {**os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}
    env["ANYSCRIBE_APP"] = "1"
    args = ["onboard", "--yes", "--provider", "openai", "--api-key", "sk-test", "--json"]
    done = subprocess.run(
        [sys.executable, "-m", "anyscribe", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    skill_dir = tmp_path / ".claude" / "skills" / "anyscribe"
    assert (json.loads(done.stdout)["skill_installed"], skill_dir.exists()) == (False, False)


@pytest.fixture
def tui_skill(tmp_path, monkeypatch):
    """The interactive onboarding's skill step against a throwaway home holding ~/.claude."""
    from anyscribe.cli import onboard

    claude = tmp_path / ".claude"
    claude.mkdir()
    target = claude / "skills" / "anyscribe"
    monkeypatch.setattr(onboard, "CLAUDE_HOME", claude)
    monkeypatch.setattr(skill_cmd, "ASCLI_SKILL_TARGET", target)
    return onboard._install_skill_step, target


def test_interactive_onboarding_in_the_app_leaves_the_skill_uninstalled(app_mode, tui_skill):
    step, target = tui_skill
    # (what the summary says, whether ~/.claude/skills/anyscribe exists)
    assert (step(), target.exists()) == (
        "not installed (the Mac app's Terminal switch installs it)",
        False,
    )


def test_interactive_onboarding_outside_the_app_still_installs_the_skill(monkeypatch, tui_skill):
    monkeypatch.delenv("ANYSCRIBE_APP", raising=False)
    step, target = tui_skill
    assert step() == "installed"
    assert (target / ".version").read_text() == __version__
