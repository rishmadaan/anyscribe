"""R2F3: a person with no cloud key who meets a missing-key message is told
about the free local option, once; with any cloud key set, nothing extra."""

from __future__ import annotations

import pytest

from anyscribe.config.settings import Settings
from anyscribe.core.resolve import resolve_run
from anyscribe.providers import PROVIDER_KEY_ENV, get_provider
from anyscribe.providers.base import LOCAL_HINT

KEYED = sorted(name for name, env in PROVIDER_KEY_ENV.items() if env)


@pytest.fixture(autouse=True)
def _no_keys(monkeypatch):
    for env in PROVIDER_KEY_ENV.values():
        if env:
            monkeypatch.delenv(env, raising=False)


@pytest.mark.parametrize("name", KEYED)
def test_every_missing_key_error_offers_local_when_no_key_is_set(name):
    with pytest.raises(RuntimeError) as exc:
        get_provider(name)._get_api_key()
    assert str(exc.value).endswith("\n" + LOCAL_HINT)
    assert PROVIDER_KEY_ENV[name] in str(exc.value)


def test_no_local_hint_once_any_cloud_key_is_set(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "x")
    with pytest.raises(RuntimeError) as exc:
        get_provider("openai")._get_api_key()
    assert LOCAL_HINT not in str(exc.value)


def test_keyless_tier_warning_offers_local(monkeypatch):
    plan = resolve_run(Settings(quality="balanced", provider="openai"))
    assert plan.notes[0].startswith("WARNING: quality 'balanced' wants deepgram")
    assert plan.notes[0].endswith("\n" + LOCAL_HINT)
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    plan = resolve_run(Settings(quality="balanced", provider="openai"))
    assert LOCAL_HINT not in plan.notes[0]


# R3F1: the hint names a step that actually switches to local, said once a run.

WANTED_HINT = (
    "Or transcribe free on this computer, no key needed: run `anyscribe onboard --force` and "
    "choose On this computer (in the dashboard: Settings, then Run setup wizard)."
)


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    from anyscribe.config import paths, settings

    path = tmp_path / "config.yaml"
    for mod in (paths, settings):
        monkeypatch.setattr(mod, "CONFIG_FILE", path)
    monkeypatch.setattr("anyscribe.cli.onboard.CONFIG_FILE", path)
    return path


def test_following_the_hint_makes_the_next_run_local(cfg, monkeypatch):
    import typer
    from typer.testing import CliRunner

    from anyscribe.cli.onboard import onboard
    from anyscribe.config.settings import load_config
    from anyscribe.core import local_setup

    before = resolve_run(load_config())
    assert before.provider == "openai" and before.notes[0].endswith("\n" + WANTED_HINT)

    monkeypatch.setattr(
        local_setup,
        "run_setup",
        lambda model, on_progress=None: {"status": "set_up", "default_model": model},
    )
    app = typer.Typer()
    app.command()(onboard)
    # the hint's step, headless: `anyscribe onboard`, On this computer
    r = CliRunner().invoke(
        app, ["--yes", "--provider", "local", "--local-model", "parakeet-v3", "--json"]
    )
    assert r.exit_code == 0, r.output
    after = resolve_run(load_config())
    assert (after.provider, load_config().quality) == ("local", "custom")


@pytest.fixture
def preflight_only(monkeypatch):
    """A run stops at the real pre-flight key check (ffmpeg taken as present)."""
    from anyscribe.core import orchestrator, preflight

    monkeypatch.setattr("anyscribe.core.preflight.shutil.which", lambda name: "/bin/" + name)
    monkeypatch.setattr(
        orchestrator, "process", lambda url, settings, **k: preflight.preflight_check(settings, url)
    )


def test_the_preflight_key_error_offers_local_when_no_key_is_set(monkeypatch):
    """Every run meets this check before any provider, so it carries the hint."""
    from anyscribe.core.preflight import preflight_check

    monkeypatch.setattr("anyscribe.core.preflight.shutil.which", lambda name: "/bin/" + name)
    with pytest.raises(RuntimeError) as exc:
        preflight_check(Settings(provider="groq"), "https://example.com/v")
    assert str(exc.value).startswith("GROQ_API_KEY not set")
    assert str(exc.value).endswith("\n" + WANTED_HINT)


def test_cli_transcribe_says_the_hint_once(cfg, preflight_only):
    """Keyless default config: the plan's WARNING and the missing-key error
    both carry the hint; the person reads it once."""
    from typer.testing import CliRunner

    from anyscribe.cli.main import app

    r = CliRunner().invoke(app, ["transcribe", "https://example.com/v"])
    out = " ".join(r.output.split())  # undo rich's line wrapping
    assert r.exit_code == 1
    assert "OPENAI_API_KEY not set" in out and "wants deepgram" in out
    assert out.count("Or transcribe free on this computer") == 1


@pytest.mark.parametrize(
    ("provider", "tip"),
    [("openai", True), ("local", False)],
)
def test_local_setup_ends_with_how_to_use_it_when_not_local(cfg, provider, tip):
    from unittest.mock import patch

    from typer.testing import CliRunner

    from anyscribe.cli.local_cmd import local_app
    from anyscribe.config.settings import save_config
    from anyscribe.core.local_setup import USE_LOCAL_TIP, check_status

    save_config(Settings(provider=provider, quality="custom", local_model="base"))
    ready = {
        "runtime_ready": True,
        "models": [{"size": "base", "runnable": True}],
    }
    with patch("anyscribe.cli.local_cmd.check_status", return_value=ready):
        r = CliRunner().invoke(local_app, ["setup", "--model", "base", "--yes"])
    out = " ".join(r.output.split())
    assert r.exit_code == 0 and "Already set up" in out
    assert (" ".join(USE_LOCAL_TIP.split()) in out) is tip
    assert check_status()["use_local_tip"] == (USE_LOCAL_TIP if tip else None)


@pytest.mark.parametrize("quality", ["balanced", "custom"])  # with and without the WARNING
def test_cli_batch_says_the_hint_once(cfg, preflight_only, monkeypatch, tmp_path, quality):
    from typer.testing import CliRunner

    from anyscribe.cli.main import app
    from anyscribe.config.settings import save_config

    save_config(Settings(provider="groq", quality=quality))
    urls = tmp_path / "urls.txt"
    urls.write_text("https://example.com/a\nhttps://example.com/b\n")
    monkeypatch.chdir(tmp_path)  # batch keeps its resume file beside the run
    r = CliRunner().invoke(app, ["batch", str(urls)])
    out = " ".join(r.output.split())
    assert r.exit_code == 1 and "0 succeeded, 2 failed" in out
    assert out.count("Or transcribe free") == 1


# R4F1 / R4C2 (lead-made, after the round-4 re-check).


def test_web_setup_tip_names_the_cloud_and_has_no_terminal_command(cfg):
    from anyscribe.config.settings import save_config
    from anyscribe.core.local_setup import USE_LOCAL_TIP, check_status

    save_config(Settings(provider="openai", quality="custom", local_model="base"))
    web_tip = check_status(web=True)["use_local_tip"]
    assert web_tip.startswith("New transcripts still go to openai.")
    assert "anyscribe config set" not in web_tip and "`" not in web_tip
    assert check_status()["use_local_tip"] == USE_LOCAL_TIP  # CLI keeps the command


def test_no_local_hint_when_the_fallback_is_already_local():
    plan = resolve_run(Settings(quality="balanced", provider="local"))
    assert plan.notes[0].startswith("WARNING: quality 'balanced' wants deepgram")
    assert LOCAL_HINT not in plan.notes[0]
