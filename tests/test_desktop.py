"""Unit tests for `anyscribe desktop` — no real launcher, login item, tray or browser."""

from __future__ import annotations

import json
import signal
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
REAL_OPEN = desktop.open_dashboard
REAL_PORT_RESPONDING = tray.port_responding
REAL_KICKSTART = desktop._kickstart


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """Never touch a real server on 8457, launchd, or the real manifest."""
    monkeypatch.setattr(paths, "DESKTOP_MANIFEST", tmp_path / "desktop.json")
    monkeypatch.setattr(paths, "DESKTOP_DIR", tmp_path / "desktop")
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    monkeypatch.setattr(tray, "SERVER_PIDFILE", tmp_path / "server.pid")
    monkeypatch.setattr(tray, "LOCKFILE", tmp_path / "tray.lock")
    monkeypatch.setattr(tray, "TRAY_LOG", tmp_path / "logs" / "tray.log")
    # launchctl acts on the real user's job whatever HOME says: never run it here.
    monkeypatch.setattr(desktop, "_kickstart", lambda port: False)
    # The real ~/Library/LaunchAgents plist names the live install's port.
    monkeypatch.setattr(desktop.service, "plist_path", lambda: tmp_path / "no-login-item.plist")
    monkeypatch.setattr(desktop.service, "is_installed", lambda: False)
    monkeypatch.setattr(desktop, "ORPHAN_GRACE", 0)
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: False)
    monkeypatch.setattr(desktop.tray, "stop_tray", lambda port: False)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: False)
    monkeypatch.setattr(desktop, "tray_available", lambda: True)
    monkeypatch.setattr(desktop.time, "sleep", lambda s: None)


@pytest.fixture(autouse=True)
def kills(monkeypatch):
    """Signals open_dashboard sends: the fake pids here may be real processes."""
    sent = []
    monkeypatch.setattr(desktop.os, "kill", lambda pid, sig: sent.append((pid, sig)))
    return sent


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


@pytest.mark.parametrize("platform", ["linux", "win32"])
def test_install_writes_manifest_and_launches(monkeypatch, calls, platform):
    monkeypatch.setattr(desktop.sys, "platform", platform)
    monkeypatch.setattr(desktop.sys, "executable", "python")
    m = desktop.install(port=9000, launch=True)
    assert m["port"] == 9000 and Path(m["launcher"]).name == "anyscribe.app"
    assert calls["install_launcher"] == [("python", 9000)] and calls["install_service"] == [9000]
    assert calls["open_dashboard"] == [9000]
    # These login items only act at the next login, so the tray is started directly first.
    assert calls["order"].index("open_dashboard") < calls["order"].index("install_service")
    assert desktop.read_manifest() == m


def _recording_real_open(monkeypatch, calls):
    def open_(port, **k):
        calls["order"].append("open_dashboard")
        return REAL_OPEN(port, **k)

    monkeypatch.setattr(desktop, "open_dashboard", open_)


def test_install_macos_lets_launchd_start_the_tray(
    monkeypatch, fake_platform_darwin, calls, fake_spawn, fake_browser
):
    """launchd's RunAtLoad tray is the one KeepAlive restarts; we must not spawn our own."""
    _recording_real_open(monkeypatch, calls)
    health = iter([False, False])  # launchd's tray comes up during the wait
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: next(health, True))
    m = desktop.install(port=9000, launch=True)
    assert calls["order"].index("install_service") < calls["order"].index("open_dashboard")
    assert fake_spawn.args == []
    assert fake_browser.opened == ["http://127.0.0.1:9000"] and desktop.read_manifest() == m


def test_install_macos_spawns_when_launchd_does_not_start(
    monkeypatch, fake_platform_darwin, calls, fake_spawn, fake_browser
):
    _recording_real_open(monkeypatch, calls)
    monkeypatch.setattr(desktop, "EXTERNAL_WAIT", 0)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: bool(fake_spawn.args))
    desktop.install(port=9000, launch=True)
    assert len(fake_spawn.args) == 1 and "tray" in fake_spawn.args[0]
    assert fake_browser.opened == ["http://127.0.0.1:9000"]


def test_install_macos_reloads_existing_login_item_without_manifest(
    monkeypatch, fake_platform_darwin, calls
):
    """A loaded job with no manifest: load alone is a no-op, so unload it first."""
    monkeypatch.setattr(desktop.service, "is_installed", lambda: True)
    desktop.install(port=9000, launch=True)
    order = calls["order"]
    assert order.index("uninstall_service") < order.index("install_service")


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


def test_install_stops_running_tray_without_manifest(monkeypatch, fake_platform_darwin, calls):
    """The upgrade from a pre-desktop-mode tray: no manifest, but its tray is running."""
    monkeypatch.setattr(desktop.tray, "read_pidfile", lambda: 4242)
    monkeypatch.setattr(
        desktop.tray,
        "stop_tray",
        lambda port: calls["stop"].append(port) or calls["order"].append("stop_tray"),
    )
    desktop.install(port=9000, launch=False)
    assert calls["stop"] == [9000]
    order = calls["order"]
    assert (
        order.index("stop_tray") < order.index("uninstall_service") < order.index("install_service")
    )


# ---- open ----------------------------------------------------------------


def test_open_refuses_foreign_listener(monkeypatch, health_server, fake_browser):
    """A real server answering like a program with a version, but not anyscribe."""
    monkeypatch.setattr(desktop.tray, "port_responding", REAL_PORT_RESPONDING)
    monkeypatch.setattr(desktop, "health_is_anyscribe", REAL_HEALTH)
    monkeypatch.setattr(desktop, "spawn_detached", lambda *a, **k: pytest.fail("must not spawn"))
    port = health_server.port
    with pytest.raises(desktop.PortInUseError) as e:
        desktop.open_dashboard(port)
    assert str(e.value) == (
        f"Port {port} is in use by another program. "
        "Run: anyscribe desktop install --port <free port>"
    )
    assert fake_browser.opened == []


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
    bound = iter([False, True])  # free at the foreign-port check, then its server binds
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: next(bound, True))
    monkeypatch.setattr(desktop.tray, "stop_tray", lambda port: pytest.fail("killed a live tray"))
    desktop.open_dashboard(8457, timeout=1)
    assert fake_spawn.args == []


@pytest.mark.skipif(sys.platform == "win32", reason="SIGUSR1 is POSIX only")
def test_open_signals_live_tray_to_restart_server(monkeypatch, kills, fake_spawn, fake_browser):
    """Dashboard Shutdown leaves the tray up with no server: ask it for a new one, never kill it.

    Killing it hands the restart to launchd, which holds it back by its ThrottleInterval.
    """
    monkeypatch.setattr(desktop.tray, "read_pidfile", lambda: 4242)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: bool(kills))
    monkeypatch.setattr(desktop.tray, "stop_tray", lambda port: pytest.fail("killed a live tray"))
    monkeypatch.setattr(desktop, "_start_tray", lambda port: pytest.fail("started a second tray"))
    url = desktop.open_dashboard(8457, timeout=1)
    assert kills == [(4242, signal.SIGUSR1)]
    assert fake_spawn.args == []
    assert fake_browser.opened == [url]


@pytest.mark.parametrize(
    "os_name",
    [
        pytest.param(
            "posix",
            marks=pytest.mark.skipif(sys.platform == "win32", reason="SIGUSR1 is POSIX only"),
        ),
        "nt",
    ],
)
def test_open_falls_back_to_stop_and_start_when_restart_fails(
    monkeypatch, kills, fake_spawn, fake_browser, os_name
):
    """A tray that does not bring its server back (or Windows, which has no SIGUSR1) is replaced."""
    if os_name == "nt":
        monkeypatch.setattr(desktop.os, "name", "nt")
    order = []
    monkeypatch.setattr(desktop.tray, "read_pidfile", lambda: None if "stop" in order else 4242)
    monkeypatch.setattr(desktop.tray, "stop_tray", lambda port: order.append("stop"))
    real_spawn = desktop.spawn_detached

    def spawn(args, log):
        order.append("start")
        return real_spawn(args, log)

    monkeypatch.setattr(desktop, "spawn_detached", spawn)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: "start" in order)
    url = desktop.open_dashboard(8457, timeout=0.5)
    assert kills == ([] if os_name == "nt" else [(4242, signal.SIGUSR1)])
    assert order == ["stop", "start"]
    assert len(fake_spawn.args) == 1 and "tray" in fake_spawn.args[0]
    assert fake_browser.opened == [url]


def test_open_other_port_refuses_without_touching_running_instance(
    monkeypatch, tmp_manifest, kills, fake_browser
):
    """`desktop open --port 9000` beside an install on 8457 must not take 8457 down."""
    tmp_manifest(port=8457)
    monkeypatch.setattr(desktop.tray, "read_pidfile", lambda: 4242)
    monkeypatch.setattr(desktop.tray, "stop_tray", lambda port: pytest.fail("stopped the tray"))
    monkeypatch.setattr(desktop, "spawn_detached", lambda *a, **k: pytest.fail("spawned"))
    monkeypatch.setattr(desktop, "_start_tray", lambda port: pytest.fail("started a tray"))
    with pytest.raises(desktop.PortMismatch) as e:
        desktop.open_dashboard(9000, timeout=0.5)
    assert str(e.value) == (
        "anyscribe is installed on port 8457. Run `anyscribe desktop open` (no --port) "
        "to open it, or `anyscribe desktop install --port 9000` to move it."
    )
    assert kills == [] and fake_browser.opened == []
    r = CliRunner().invoke(app, ["desktop", "open", "--port", "9000"])
    assert r.exit_code == 1 and "installed on port 8457" in r.output
    assert kills == []


def test_open_other_port_refuses_even_with_no_tray(monkeypatch, tmp_manifest, fake_browser):
    """After a Quit, `open --port 9000` must not spawn a tray outside the 8457 install."""
    tmp_manifest(port=8457)
    monkeypatch.setattr(desktop.tray, "read_pidfile", lambda: None)
    monkeypatch.setattr(desktop, "spawn_detached", lambda *a, **k: pytest.fail("spawned"))
    monkeypatch.setattr(desktop, "_start_tray", lambda port: pytest.fail("started a tray"))
    with pytest.raises(desktop.PortMismatch):
        desktop.open_dashboard(9000, timeout=0.5)
    assert fake_browser.opened == []


def test_open_other_port_refuses_even_when_that_port_is_healthy(
    monkeypatch, tmp_manifest, kills, fake_browser
):
    """A hand-started `anyscribe ui --port 9000` is not desktop mode: still refuse."""
    tmp_manifest(port=8457)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: port == 9000)
    monkeypatch.setattr(desktop.tray, "stop_tray", lambda port: pytest.fail("stopped the tray"))
    monkeypatch.setattr(desktop, "spawn_detached", lambda *a, **k: pytest.fail("spawned"))
    monkeypatch.setattr(desktop, "_start_tray", lambda port: pytest.fail("started a tray"))
    with pytest.raises(desktop.PortMismatch) as e:
        desktop.open_dashboard(9000, timeout=0.5)
    assert (e.value.installed, e.value.requested) == (8457, 9000)
    assert kills == [] and fake_browser.opened == []


def test_open_without_port_uses_the_login_item_port(monkeypatch, tmp_path):
    """No manifest, a login item on 9100: a bare `desktop open` must not refuse itself."""
    _login_item(tmp_path, monkeypatch, port=9100)
    opened = []
    monkeypatch.setattr(desktop, "open_dashboard", lambda port: opened.append(port))
    r = CliRunner().invoke(app, ["desktop", "open"])
    assert r.exit_code == 0 and opened == [9100]


def test_installed_port_falls_back_to_login_item(monkeypatch, tmp_path):
    assert desktop.installed_port() is None
    _login_item(tmp_path, monkeypatch, port=9100)
    assert desktop.installed_port() == 9100


def test_reinstall_on_new_port_opens_without_port_mismatch(
    monkeypatch, fake_platform_darwin, calls, tmp_manifest, fake_browser, tmp_path
):
    """Moving 8500 -> 9000 on macOS: launchd's new tray is alive before the manifest is rewritten."""
    tmp_manifest(port=8500)
    plist = tmp_path / "com.anyscribe.tray.plist"
    monkeypatch.setattr(desktop.service, "plist_path", lambda: plist)

    def install_service(port=8457):
        plist.write_text(desktop.service.render_plist(python="/usr/bin/python3", port=port))
        return plist

    monkeypatch.setattr(desktop.service, "install_service", install_service)
    _recording_real_open(monkeypatch, calls)
    monkeypatch.setattr(desktop.tray, "read_pidfile", lambda: 4242)  # launchd's new tray
    health = iter([False, False])
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: next(health, True))
    m = desktop.install(port=9000, launch=True)
    assert m["port"] == 9000 and fake_browser.opened == ["http://127.0.0.1:9000"]


def _login_item(tmp_path, monkeypatch, port=8457):
    plist = tmp_path / "com.anyscribe.tray.plist"
    plist.write_text(desktop.service.render_plist(python="/usr/bin/python3", port=port))
    monkeypatch.setattr(desktop.service, "plist_path", lambda: plist)
    monkeypatch.setattr(desktop, "_kickstart", REAL_KICKSTART)
    monkeypatch.setattr(desktop.sys, "platform", "darwin")


def _fake_run(monkeypatch, returncode):
    ran = []

    def run(args, **kwargs):
        ran.append(args)
        return subprocess.CompletedProcess(args, returncode, b"", b"")

    monkeypatch.setattr(desktop.subprocess, "run", run)
    return ran


@pytest.mark.skipif(sys.platform == "win32", reason="launchctl targets gui/<uid>, POSIX only")
def test_open_uses_launchctl_kickstart_on_macos_with_login_item(
    monkeypatch, tmp_path, fake_spawn, fake_browser
):
    """After Quit, the app click restarts the tray under launchd, so crash restart still holds."""
    _login_item(tmp_path, monkeypatch)
    ran = _fake_run(monkeypatch, 0)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: bool(ran))
    desktop.open_dashboard(8457, timeout=1)
    assert ran == [["launchctl", "kickstart", f"gui/{desktop.os.getuid()}/com.anyscribe.tray"]]
    assert fake_spawn.args == []
    assert fake_browser.opened == ["http://127.0.0.1:8457"]


@pytest.mark.skipif(sys.platform == "win32", reason="launchctl targets gui/<uid>, POSIX only")
def test_open_spawns_when_kickstart_fails(monkeypatch, tmp_path, fake_spawn, fake_browser):
    _login_item(tmp_path, monkeypatch)
    ran = _fake_run(monkeypatch, 113)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: bool(fake_spawn.args))
    desktop.open_dashboard(8457, timeout=1)
    assert len(ran) == 1 and len(fake_spawn.args) == 1 and "tray" in fake_spawn.args[0]


@pytest.mark.skipif(sys.platform == "win32", reason="launchctl targets gui/<uid>, POSIX only")
def test_kickstart_has_no_kill_flag(monkeypatch, tmp_path):
    """-k on a job launchd is respawning waits out its throttle, then kills it again."""
    _login_item(tmp_path, monkeypatch)
    ran = _fake_run(monkeypatch, 0)
    assert desktop._kickstart(8457) is True
    assert ran == [["launchctl", "kickstart", f"gui/{desktop.os.getuid()}/com.anyscribe.tray"]]


def test_kickstart_skips_login_item_for_another_port(monkeypatch, tmp_path):
    _login_item(tmp_path, monkeypatch, port=9000)
    ran = _fake_run(monkeypatch, 0)
    assert desktop._kickstart(8457) is False and ran == []


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


def test_open_waits_for_winning_tray_when_duplicate_exits_zero(monkeypatch, fake_browser):
    """Two clicks at once: the second tray finds the lock held and exits 0. Not a failure."""
    spawned, probes = [], []

    class Proc:
        def poll(self):
            return 0

    def spawn(args, log):
        spawned.append(args)
        return Proc()

    monkeypatch.setattr(desktop, "spawn_detached", spawn)
    # The winning tray's server answers a few probes after the loser has exited.
    monkeypatch.setattr(
        desktop, "health_is_anyscribe", lambda port: probes.append(port) or len(probes) > 4
    )
    url = desktop.open_dashboard(8457, timeout=1)
    assert len(spawned) == 1 and "tray" in spawned[0]  # no bare `ui` server beside the tray
    assert url == "http://127.0.0.1:8457" and fake_browser.opened == [url]


def test_open_raises_start_failed_when_fallback_dies(monkeypatch, fake_browser):
    monkeypatch.setattr(desktop, "spawn_detached", lambda args, log: FakeProc(code=1))
    with pytest.raises(desktop.StartFailed):
        desktop.open_dashboard(8457, timeout=1)
    assert fake_browser.opened == []


def test_open_prints_url_when_no_browser(monkeypatch, fake_browser, capsys):
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: True)
    fake_browser.result = False
    desktop.open_dashboard(8457)
    assert "http://127.0.0.1:8457" in capsys.readouterr().err


@pytest.mark.parametrize(
    "status, body, expected",
    [
        (200, {"app": "anyscribe", "ok": True, "version": "1"}, True),
        (200, {"ok": True, "version": "1"}, False),  # another program's health page
        (404, {"app": "anyscribe"}, False),
    ],
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


def test_status_healthy(monkeypatch, tmp_manifest):
    tmp_manifest()
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: True)
    monkeypatch.setattr(desktop.tray, "read_pidfile", lambda: 4242)
    s = desktop.status()
    assert s["installed"] is True and s["healthy"] is True and s["reason"] is None


def test_status_without_tray_is_healthy_and_says_why(monkeypatch, tmp_manifest):
    """Headless Linux: the bare dashboard answers, no tray icon could start."""
    tmp_manifest()
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: True)
    r = CliRunner().invoke(app, ["desktop", "status", "--json"])
    s = json.loads(r.stdout)["data"]
    assert (s["healthy"], s["server_running"], s["tray_running"]) == (True, True, False)
    assert s["reason"] == (
        "Running without its tray icon (no graphical session or tray support). "
        "The dashboard works; the tray will start at your next graphical login."
    )


@pytest.mark.parametrize("tray_pid", [None, 4242])
def test_cli_install_says_when_the_tray_is_not_running(monkeypatch, calls, tray_pid):
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: True)
    monkeypatch.setattr(desktop.tray, "read_pidfile", lambda: tray_pid)
    r = CliRunner().invoke(app, ["desktop", "install", "--yes"])
    line = (
        "Tray icon: not running (no graphical session or tray support here). The dashboard "
        "works without it; the tray will start at your next graphical login."
    )
    assert r.exit_code == 0 and "Starts at login:" in r.stdout
    assert (line in r.stdout) is (tray_pid is None)


def test_status_installed_but_not_running_is_not_healthy(tmp_manifest):
    """Intact files are not a working app: healthy needs the dashboard to answer."""
    tmp_manifest()
    s = desktop.status()
    assert s["installed"] is True and s["server_running"] is False and s["healthy"] is False
    assert s["reason"] == (
        "Installed but not running. Click the anyscribe app or run: anyscribe desktop open"
    )


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


def test_uninstall_removes_tray_lock_only_when_no_tray_holds_it(calls, tmp_manifest):
    tmp_manifest()
    held = tray.acquire_instance_lock()  # a tray still alive
    desktop.uninstall()
    assert tray.LOCKFILE.exists()
    held.close()
    desktop.uninstall()
    assert not tray.LOCKFILE.exists()


def test_uninstall_without_install_leaves_hand_started_server(monkeypatch, calls):
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: True)
    monkeypatch.setattr(desktop.tray, "stop_tray", lambda port: pytest.fail("must not stop"))
    assert desktop.uninstall()["stopped"] is False


def test_uninstall_stops_tray_and_warns_about_running_job(monkeypatch, tmp_manifest, calls):
    tmp_manifest()
    monkeypatch.setattr(desktop.tray, "stop_tray", lambda port: calls["stop"].append(port) or True)
    r = CliRunner().invoke(app, ["desktop", "uninstall", "--yes"])
    assert r.exit_code == 0 and calls["stop"] == [8457]
    assert "Stopped anyscribe. If a transcription was running, run it again. Saved chunks may be reused; unfinished work may run again." in r.output


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


def test_cli_install_json_stays_clean_without_browser(calls, monkeypatch, fake_browser):
    monkeypatch.setattr(desktop, "open_dashboard", REAL_OPEN)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: True)
    fake_browser.result = False
    r = CliRunner().invoke(app, ["desktop", "install", "--yes", "--json"])
    assert r.exit_code == 0 and json.loads(r.stdout)["success"] is True
    assert "http://127.0.0.1:8457" in r.stderr


def test_status_partly_installed_without_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop.launcher, "launcher_path", lambda: tmp_path)  # exists
    s = desktop.status()
    assert s["installed"] is False and s["reason"].startswith("Partly installed")


def test_uninstall_does_not_claim_stop_for_foreign_listener(monkeypatch, calls, tmp_manifest):
    tmp_manifest()
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: True)
    assert desktop.uninstall()["stopped"] is False


@pytest.mark.parametrize("cmd", [["uninstall", "--yes", "--json"], ["open", "--port", "8457"]])
def test_cli_os_errors_fail_cleanly(monkeypatch, cmd):
    def boom(*a, **k):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(desktop, "uninstall", boom)
    monkeypatch.setattr(desktop, "open_dashboard", boom)
    r = CliRunner().invoke(app, ["desktop", *cmd])
    assert r.exit_code == 1 and not isinstance(r.exception, PermissionError)  # no traceback
    assert "Permission denied" in r.output
    if cmd[0] == "uninstall":
        assert json.loads(r.stdout)["success"] is False
    else:
        assert "Permission denied" in tray.TRAY_LOG.read_text()


def test_cli_open_foreign_port_exit_1(monkeypatch):
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: True)
    r = CliRunner().invoke(app, ["desktop", "open", "--port", "8457"])
    assert r.exit_code == 1 and "in use by another program" in r.output
    assert "in use by another program" in tray.TRAY_LOG.read_text()
