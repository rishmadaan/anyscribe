"""Install-command selection for the local engines: the pins (av<19, onnx-asr),
the uv fallback for venvs without pip, and the "older install lacks onnx-asr"
upgrade path. Subprocesses are never run; ``_run`` is captured."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from unittest.mock import patch

from anyscribe.core import local_setup

ROOT = Path(__file__).resolve().parents[1]


def _captured_install(monkeypatch, *, method="venv", pip=True, uv="/usr/bin/uv", ready=False):
    monkeypatch.setattr(local_setup, "local_runtime_ready", lambda: ready)
    monkeypatch.setattr(local_setup, "detect_install_method", lambda: method)
    monkeypatch.setattr(local_setup, "_pip_available", lambda: pip)
    monkeypatch.setattr(local_setup.shutil, "which", lambda name: uv if name == "uv" else name)
    monkeypatch.setattr(local_setup, "_pipx_venv_name", lambda: "anyscribe")
    with patch.object(local_setup, "_run", return_value=(0, "", "")) as run:
        result = local_setup.install_faster_whisper()
    return result, (run.call_args.args[0] if run.called else None)


def test_pip_install_command_carries_the_av_pin_and_onnx_asr(monkeypatch):
    _, cmd = _captured_install(monkeypatch)
    assert cmd == [
        sys.executable,
        "-m",
        "pip",
        "install",
        "faster-whisper>=1.0",
        "av<19",
        "onnx-asr>=0.12.0",
    ]


def test_pipx_inject_command_carries_the_av_pin(monkeypatch):
    _, cmd = _captured_install(monkeypatch, method="pipx")
    assert cmd == [
        "pipx",
        "inject",
        "anyscribe",
        "faster-whisper>=1.0",
        "av<19",
        "onnx-asr>=0.12.0",
    ]


def test_uv_fallback_when_venv_has_no_pip(monkeypatch):
    result, cmd = _captured_install(monkeypatch, pip=False)
    assert cmd == [
        "uv",
        "pip",
        "install",
        "--python",
        sys.executable,
        "faster-whisper>=1.0",
        "av<19",
        "onnx-asr>=0.12.0",
    ]
    assert result["method"] == "uv" and result["status"] == "installed"


def test_pip_preferred_over_uv_when_pip_exists(monkeypatch):
    _, cmd = _captured_install(monkeypatch, pip=True)
    assert cmd[:3] == [sys.executable, "-m", "pip"]


def test_no_pip_and_no_uv_keeps_the_pip_command(monkeypatch):
    # nothing better to try; the failure output then names the missing pip
    _, cmd = _captured_install(monkeypatch, pip=False, uv=None)
    assert cmd[:3] == [sys.executable, "-m", "pip"]


def test_uv_uninstall_removes_both_engines(monkeypatch):
    monkeypatch.setattr(local_setup, "faster_whisper_importable", lambda: True)
    monkeypatch.setattr(local_setup, "detect_install_method", lambda: "venv")
    monkeypatch.setattr(local_setup, "_pip_available", lambda: False)
    monkeypatch.setattr(local_setup.shutil, "which", lambda name: "/usr/bin/uv")
    with patch.object(local_setup, "_run", return_value=(0, "", "")) as run:
        local_setup.uninstall_faster_whisper()
    assert run.call_args.args[0] == [
        "uv",
        "pip",
        "uninstall",
        "--python",
        sys.executable,
        "faster-whisper",
        "onnx-asr",
    ]


def test_existing_whisper_install_without_onnx_asr_gets_installed(monkeypatch):
    """An install from before Parakeet has faster-whisper but not onnx-asr: the
    runtime is not ready, so picking a model runs the install step."""
    monkeypatch.setattr(local_setup, "faster_whisper_importable", lambda: True)
    monkeypatch.setattr(local_setup, "onnx_asr_importable", lambda: False)
    monkeypatch.setattr(local_setup, "_av_too_new", lambda: False)
    assert local_setup.local_runtime_ready() is False
    monkeypatch.setattr(local_setup, "detect_install_method", lambda: "venv")
    monkeypatch.setattr(local_setup, "_pip_available", lambda: True)
    with patch.object(local_setup, "_run", return_value=(0, "", "")) as run:
        assert local_setup.ensure_runtime() is None
    assert "onnx-asr>=0.12.0" in run.call_args.args[0]


def test_pyav_19_counts_as_not_ready(monkeypatch):
    monkeypatch.setattr(local_setup, "faster_whisper_importable", lambda: True)
    monkeypatch.setattr(local_setup, "onnx_asr_importable", lambda: True)
    monkeypatch.setattr(local_setup.importlib.metadata, "version", lambda name: "19.0.0")
    assert local_setup.local_runtime_ready() is False
    monkeypatch.setattr(local_setup.importlib.metadata, "version", lambda name: "18.1.0")
    assert local_setup.local_runtime_ready() is True


def test_ensure_runtime_returns_the_failed_result(monkeypatch):
    monkeypatch.setattr(local_setup, "local_runtime_ready", lambda: False)
    monkeypatch.setattr(local_setup, "detect_install_method", lambda: "venv")
    monkeypatch.setattr(local_setup, "_pip_available", lambda: True)
    with patch.object(local_setup, "_run", return_value=(1, "", "boom")):
        failed = local_setup.ensure_runtime()
    assert failed["status"] == "failed" and failed["stderr"] == "boom"


def test_pyproject_local_extra_matches_runtime_install():
    extra = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
        "optional-dependencies"
    ]["local"]
    assert extra == local_setup.LOCAL_RUNTIME_SPECS


# ── a replaced, already-loaded engine needs a restart (C10) ──────


def _install_replacing(monkeypatch, before, after, loaded):
    """Run the install with engine versions going ``before`` -> ``after`` and
    ``loaded`` modules already imported in this process."""
    versions = iter([before, after])
    monkeypatch.setattr(local_setup, "_restart_needed", False)
    monkeypatch.setattr(local_setup, "local_runtime_ready", lambda: False)
    monkeypatch.setattr(local_setup, "detect_install_method", lambda: "venv")
    monkeypatch.setattr(local_setup, "_engine_versions", lambda: next(versions))
    for mod in local_setup.ENGINE_MODULES:
        if mod in loaded:
            monkeypatch.setitem(sys.modules, mod, object())
        else:
            monkeypatch.delitem(sys.modules, mod, raising=False)
    with patch.object(local_setup, "_run", return_value=(0, "", "")):
        return local_setup.install_faster_whisper()


def test_downgrading_a_loaded_pyav_says_restart(monkeypatch):
    res = _install_replacing(
        monkeypatch,
        before={"av": "19.0.0", "faster-whisper": "1.2.1", "onnx-asr": None},
        after={"av": "18.1.0", "faster-whisper": "1.2.1", "onnx-asr": "0.12.0"},
        loaded={"av", "faster_whisper"},
    )
    assert res["status"] == "installed" and res["restart_needed"] is True
    assert local_setup.restart_needed() is True


def test_adding_a_package_not_yet_loaded_needs_no_restart(monkeypatch):
    res = _install_replacing(
        monkeypatch,
        before={"av": "18.1.0", "faster-whisper": "1.2.1", "onnx-asr": None},
        after={"av": "18.1.0", "faster-whisper": "1.2.1", "onnx-asr": "0.12.0"},
        loaded={"av", "faster_whisper"},
    )
    assert res["restart_needed"] is False and local_setup.restart_needed() is False


def test_fresh_install_in_a_clean_process_needs_no_restart(monkeypatch):
    res = _install_replacing(
        monkeypatch,
        before={"av": None, "faster-whisper": None, "onnx-asr": None},
        after={"av": "18.1.0", "faster-whisper": "1.2.1", "onnx-asr": "0.12.0"},
        loaded=set(),
    )
    assert res["restart_needed"] is False


def test_web_status_and_cli_say_restart(monkeypatch):
    from fastapi.testclient import TestClient
    from typer.testing import CliRunner

    from anyscribe.cli import local_cmd
    from anyscribe.web.app import create_app

    monkeypatch.setattr(local_setup, "_restart_needed", True)
    status = TestClient(create_app()).get("/api/local/status").json()
    assert status["restart_needed"] is True

    monkeypatch.setattr(local_cmd, "check_status", lambda: {"runtime_ready": False, "models": []})
    monkeypatch.setattr(
        local_cmd,
        "run_setup",
        lambda m, on_progress=None: {"status": "set_up", "restart_needed": True},
    )
    out = CliRunner().invoke(local_cmd.local_app, ["setup", "--model", "small", "--yes"])
    assert local_setup.RESTART_MESSAGE in " ".join(out.output.split())
