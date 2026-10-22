"""Unit tests for `anyscribe desktop` — no real launcher, login item, tray or browser."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pytest
from typer.testing import CliRunner

from anyscribe.cli.main import app
from anyscribe.config import paths
from anyscribe.core import desktop, tray

REAL_HEALTH = desktop.health_is_anyscribe  # before the autouse fixture stubs it


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """Never touch a real server on 8457, launchd, or the real manifest."""
    monkeypatch.setattr(paths, "DESKTOP_MANIFEST", tmp_path / "desktop.json")
    monkeypatch.setattr(paths, "DESKTOP_DIR", tmp_path / "desktop")
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    monkeypatch.setattr(tray, "TRAY_LOG", tmp_path / "logs" / "tray.log")
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: False)
    monkeypatch.setattr(desktop.tray, "stop_tray", lambda port: False)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: False)
    monkeypatch.setattr(desktop, "tray_available", lambda: True)
    monkeypatch.setattr(desktop.time, "sleep", lambda s: None)


@pytest.fixture
def calls(monkeypatch, tmp_path):
    calls = defaultdict(list)

    def record(name, value, ret=None):
        calls[name].append(value)
        calls["order"].append(name)
        return ret

    monkeypatch.setattr(desktop.launcher, "render_icons", lambda d: {})
    monkeypatch.setattr(
        desktop.launcher,
        "install_launcher",
        lambda py, port, icons: record("install_launcher", (py, port), tmp_path / "anyscribe.app"),
    )
    monkeypatch.setattr(
        desktop.launcher, "uninstall_launcher", lambda: record("uninstall_launcher", None, True)
    )
    monkeypatch.setattr(
        desktop.service,
        "install_service",
        lambda port=8457: record("install_service", port, tmp_path / "com.anyscribe.tray.plist"),
    )
    monkeypatch.setattr(
        desktop.service, "uninstall_service", lambda: record("uninstall_service", None, True)
    )
    monkeypatch.setattr(
        desktop, "open_dashboard", lambda port, **k: record("open_dashboard", port, "url")
    )
    return calls


@pytest.fixture
def fake_platform_darwin(monkeypatch):
    monkeypatch.setattr(desktop.sys, "platform", "darwin")
    monkeypatch.setattr(desktop.sys, "executable", "python")


@pytest.fixture
def tmp_manifest(tmp_path):
    def write(**overrides):
        launcher_p = tmp_path / "anyscribe.app"
        login = tmp_path / "com.anyscribe.tray.plist"
        launcher_p.mkdir(exist_ok=True)
        login.write_text("x")
        m = {
            "version": "0",
            "python": sys.executable,
            "port": 8457,
            "launcher": str(launcher_p),
            "login_item": str(login),
            "installed_at": "2026-10-22T00:00:00+00:00",
            **overrides,
        }
        desktop.write_manifest(m)
        return m

    return write


class FakeProc:
    def __init__(self, code=None):
        self.code = code

    def poll(self):
        return self.code


@pytest.fixture
def fake_spawn(monkeypatch):
    class Spawn:
        args: list = []

    def spawn(args, log):
        Spawn.args.append(args)
        return FakeProc()

    Spawn.args = []
    monkeypatch.setattr(desktop, "spawn_detached", spawn)
    return Spawn


@pytest.fixture
def fake_browser(monkeypatch):
    class Browser:
        opened: list = []
        result = True

    def open_(url):
        Browser.opened.append(url)
        return Browser.result

    Browser.opened = []
    monkeypatch.setattr(desktop.webbrowser, "open", open_)
    return Browser


# ---- install -------------------------------------------------------------


def test_install_writes_manifest_and_launches(fake_platform_darwin, calls):
    m = desktop.install(port=9000, launch=True)
    assert m["port"] == 9000 and Path(m["launcher"]).name == "anyscribe.app"
    assert calls["install_launcher"] == [("python", 9000)] and calls["install_service"] == [9000]
    assert calls["open_dashboard"] == [9000]
    assert desktop.read_manifest() == m


def test_install_no_launch_does_not_open(calls):
    desktop.install(port=9000, launch=False)
    assert calls["open_dashboard"] == []


def test_install_refuses_without_tray(monkeypatch):
    monkeypatch.setattr(desktop, "tray_available", lambda: False)
    with pytest.raises(desktop.TrayMissing):
        desktop.install()


def test_install_refuses_foreign_port_before_writing(monkeypatch, calls):
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: True)
    with pytest.raises(desktop.PortInUseError):
        desktop.install(port=9000)
    assert calls["order"] == [] and desktop.read_manifest() is None


def test_install_over_existing_stops_old_tray_first(monkeypatch, calls, tmp_manifest):
    tmp_manifest(port=8500)
    monkeypatch.setattr(
        desktop.tray,
        "stop_tray",
        lambda port: calls["stop"].append(port) or calls["order"].append("stop_tray"),
    )
    desktop.install(port=9000)
    assert calls["stop"] == [8500]
    order = calls["order"]
    assert (
        order.index("stop_tray") < order.index("uninstall_service") < order.index("install_service")
    )


# ---- open ----------------------------------------------------------------


def test_open_refuses_foreign_listener(monkeypatch):
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: True)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: False)
    monkeypatch.setattr(desktop, "spawn_detached", lambda *a, **k: pytest.fail("must not spawn"))
    with pytest.raises(desktop.PortInUseError) as e:
        desktop.open_dashboard(8457)
    assert str(e.value) == (
        "Port 8457 is in use by another program. Run: anyscribe desktop install --port <free port>"
    )


def test_open_when_already_healthy_just_opens(monkeypatch, fake_browser):
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: True)
    monkeypatch.setattr(desktop, "spawn_detached", lambda *a, **k: pytest.fail("must not spawn"))
    assert desktop.open_dashboard(8457) == "http://127.0.0.1:8457"
    assert fake_browser.opened == ["http://127.0.0.1:8457"]


def test_open_starts_tray_then_opens(monkeypatch, fake_spawn, fake_browser):
    health = iter([False, False, True])
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: False)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: next(health))
    url = desktop.open_dashboard(8457, timeout=1)
    args = fake_spawn.args[0]
    assert "tray" in args and args[-2:] == ["--port", "8457"]
    assert url == "http://127.0.0.1:8457" and fake_browser.opened == [url]


def test_open_does_not_spawn_second_tray(monkeypatch, fake_spawn, fake_browser):
    """A tray already starting (launchd's) brings the server up; a second would race it."""
    health = iter([False, True])
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: next(health))
    monkeypatch.setattr(desktop.tray, "read_pidfile", lambda: 4242)
    desktop.open_dashboard(8457, timeout=1)
    assert fake_spawn.args == []


def test_open_falls_back_to_ui_when_tray_dies(monkeypatch, fake_browser):
    spawned = []
    procs = iter([FakeProc(code=1), FakeProc()])

    def spawn(args, log):
        spawned.append(args)
        return next(procs)

    monkeypatch.setattr(desktop, "spawn_detached", spawn)
    # unhealthy until the second (ui) process is up
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: len(spawned) == 2)
    url = desktop.open_dashboard(8457, timeout=1)
    assert "tray" in spawned[0]
    assert spawned[1][-4:] == ["ui", "--port", "8457", "--no-open"]
    assert fake_browser.opened == [url]


def test_open_raises_start_failed_when_fallback_dies(monkeypatch, fake_browser):
    monkeypatch.setattr(desktop, "spawn_detached", lambda args, log: FakeProc(code=1))
    with pytest.raises(desktop.StartFailed):
        desktop.open_dashboard(8457, timeout=1)
    assert fake_browser.opened == []


def test_open_prints_url_when_no_browser(monkeypatch, fake_browser, capsys):
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: True)
    fake_browser.result = False
    desktop.open_dashboard(8457)
    assert "http://127.0.0.1:8457" in capsys.readouterr().out


@pytest.mark.parametrize(
    "status, body, expected",
    [(200, {"ok": True, "version": "1"}, True), (200, {"ok": True}, False), (404, {}, False)],
)
def test_health_is_anyscribe(monkeypatch, status, body, expected):
    import httpx

    seen = {}

    def get(url, timeout):
        seen["timeout"] = timeout
        return httpx.Response(status, json=body)

    monkeypatch.setattr(httpx, "get", get)
    assert REAL_HEALTH(8457) is expected
    # A launchd-started server answered in 3.5-8 s; a short timeout reads it as foreign.
    assert seen["timeout"] >= 10


def test_spawn_detached_sets_full_path(monkeypatch, tmp_path):
    seen = {}

    def popen(args, **kwargs):
        seen.update(kwargs, args=args)
        return FakeProc()

    monkeypatch.setattr(desktop.subprocess, "Popen", popen)
    desktop.spawn_detached(["x"], tmp_path / "logs" / "tray.log")
    assert seen["env"]["PATH"] == desktop.service.service_path()
    assert seen["stdin"] is subprocess.DEVNULL
    if desktop.os.name != "nt":
        assert seen["start_new_session"] is True


# ---- status / uninstall --------------------------------------------------


def test_status_not_installed():
    s = desktop.status()
    assert s["installed"] is False and s["healthy"] is False and "install" in s["reason"]


def test_status_healthy(tmp_manifest):
    tmp_manifest()
    s = desktop.status()
    assert s["installed"] is True and s["healthy"] is True and s["reason"] is None


def test_status_unhealthy_when_python_missing(tmp_manifest):
    tmp_manifest(python="/nonexistent/python3")
    s = desktop.status()
    assert s["installed"] is True and s["healthy"] is False and "python" in s["reason"].lower()


def test_status_unhealthy_when_login_item_missing(tmp_manifest, tmp_path):
    tmp_manifest(login_item=str(tmp_path / "gone.plist"))
    s = desktop.status()
    assert s["healthy"] is False and "login item" in s["reason"]


def test_uninstall_removes_everything(calls, tmp_manifest):
    tmp_manifest()
    paths.DESKTOP_DIR.mkdir()
    (paths.DESKTOP_DIR / "anyscribe.png").write_text("x")
    r = desktop.uninstall()
    assert r == {"stopped": False, "launcher": True, "login_item": True}
    assert not paths.DESKTOP_DIR.exists() and desktop.read_manifest() is None


def test_uninstall_without_install_leaves_hand_started_server(monkeypatch, calls):
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: True)
    monkeypatch.setattr(desktop.tray, "stop_tray", lambda port: pytest.fail("must not stop"))
    assert desktop.uninstall()["stopped"] is False


def test_uninstall_stops_tray_and_warns_about_running_job(monkeypatch, tmp_manifest, calls):
    tmp_manifest()
    monkeypatch.setattr(desktop.tray, "stop_tray", lambda port: calls["stop"].append(port) or True)
    r = CliRunner().invoke(app, ["desktop", "uninstall", "--yes"])
    assert r.exit_code == 0 and calls["stop"] == [8457]
    assert "transcription in progress" in r.output and "resume" in r.output


# ---- CLI -----------------------------------------------------------------


def test_cli_status_json_envelope(tmp_manifest):
    tmp_manifest()
    r = CliRunner().invoke(app, ["desktop", "status", "--json"])
    data = json.loads(r.output)
    assert data["success"] is True and "healthy" in data["data"]


def test_cli_install_unsupported_platform_exit_2(monkeypatch):
    monkeypatch.setattr(desktop.service.sys, "platform", "freebsd")
    assert CliRunner().invoke(app, ["desktop", "install", "--yes"]).exit_code == 2


def test_cli_install_without_tray_exit_1(monkeypatch):
    monkeypatch.setattr(desktop, "tray_available", lambda: False)
    r = CliRunner().invoke(app, ["desktop", "install", "--yes", "--json"])
    assert r.exit_code == 1 and "anyscribe[tray]" in json.loads(r.output)["error"]


def test_cli_install_json(calls):
    r = CliRunner().invoke(app, ["desktop", "install", "--yes", "--no-launch", "--json"])
    data = json.loads(r.output)
    assert r.exit_code == 0 and data["success"] is True and data["data"]["port"] == 8457


def test_cli_open_foreign_port_exit_1(monkeypatch):
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: True)
    r = CliRunner().invoke(app, ["desktop", "open", "--port", "8457"])
    assert r.exit_code == 1 and "in use by another program" in r.output
    assert "in use by another program" in tray.TRAY_LOG.read_text()
