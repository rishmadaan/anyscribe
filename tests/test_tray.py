"""Unit tests for the tray companion — no GUI, no real launchctl."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import types
from pathlib import Path

import pytest
from typer.testing import CliRunner

from anyscribe.cli import tray_cmd
from anyscribe.cli.main import app
from anyscribe.core import launcher, service, tray

runner = CliRunner()


# ---- pidfile -------------------------------------------------------------


def test_pidfile_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    assert tray.read_pidfile() is None
    tray.write_pidfile()
    assert tray.read_pidfile() == os.getpid()
    tray.remove_pidfile()
    assert tray.read_pidfile() is None


def test_pidfile_stale_pid_treated_as_absent(monkeypatch, tmp_path):
    pidfile = tmp_path / "tray.pid"
    pidfile.write_text("999999999")  # implausible / dead pid
    monkeypatch.setattr(tray, "PIDFILE", pidfile)
    assert tray.read_pidfile() is None


def test_pidfile_garbage_is_absent(monkeypatch, tmp_path):
    pidfile = tmp_path / "tray.pid"
    pidfile.write_text("not-a-pid")
    monkeypatch.setattr(tray, "PIDFILE", pidfile)
    assert tray.read_pidfile() is None


def test_pid_alive_never_calls_os_kill_on_windows(monkeypatch):
    monkeypatch.setattr(tray.os, "name", "nt")
    monkeypatch.setattr(tray.os, "kill", lambda *a: pytest.fail("os.kill used as a probe on nt"))
    monkeypatch.setattr(tray, "_windows_pid_alive", lambda pid: True)
    assert tray._pid_alive(123) is True


@pytest.mark.skipif(sys.platform != "win32", reason="real Windows process probe")
def test_pid_alive_real_windows():
    assert tray._pid_alive(os.getpid()) is True
    # Popen, not run: run() does not expose the child's pid.
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait()
    assert tray._pid_alive(child.pid) is False


# ---- port probe ----------------------------------------------------------


def test_port_probe_free_port():
    # An almost-certainly-unbound port responds False.
    assert tray.port_responding(1, timeout=0.2) is False


def test_port_probe_bound_port():
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen()
    port = s.getsockname()[1]
    try:
        assert tray.port_responding(port, timeout=0.5) is True
    finally:
        s.close()


# ---- plist generation ----------------------------------------------------


def test_render_plist_contents():
    xml = service.render_plist(python="/usr/bin/python3")
    assert f"<string>{service.LABEL}</string>" in xml
    assert "<string>/usr/bin/python3</string>" in xml
    assert "<string>-m</string>" in xml
    assert "<string>anyscribe</string>" in xml
    assert "<string>tray</string>" in xml
    assert "<key>RunAtLoad</key>" in xml


def test_service_path_appends_known_dirs_once(tmp_path):
    env = {"PATH": f"/opt/homebrew/bin{os.pathsep}/usr/bin"}
    parts = service.service_path(env, home=tmp_path).split(os.pathsep)
    assert parts[:2] == ["/opt/homebrew/bin", "/usr/bin"]
    assert parts.count("/opt/homebrew/bin") == 1
    assert str(tmp_path / ".deno" / "bin") in parts
    assert str(Path(sys.executable).parent) in parts


def test_render_plist_carries_path_log_keepalive_and_port():
    xml = service.render_plist(
        python="/usr/bin/python3", port=9000, path_env="/a:/b", log=Path("/tmp/t.log")
    )
    assert "<key>PATH</key>" in xml and "<string>/a:/b</string>" in xml
    assert "<string>--port</string>" in xml and "<string>9000</string>" in xml
    assert "<key>SuccessfulExit</key>" in xml and "<false/>" in xml
    assert "<string>/tmp/t.log</string>" in xml


def test_plist_has_throttle_interval():
    xml = service.render_plist(python="/usr/bin/python3")
    assert "<key>ThrottleInterval</key>" in xml and "<integer>60</integer>" in xml


# ---- install / uninstall (no real launchctl) -----------------------------


@pytest.fixture
def fake_agents(monkeypatch, tmp_path):
    agents = tmp_path / "LaunchAgents"
    monkeypatch.setattr(service.sys, "platform", "darwin")
    monkeypatch.setattr(service, "launch_agents_dir", lambda: agents)
    calls = []
    monkeypatch.setattr(service, "_launchctl", lambda *a: calls.append(a))
    monkeypatch.setattr(tray, "TRAY_LOG", tmp_path / "logs" / "tray.log")
    monkeypatch.setattr(service.tray, "read_pidfile", lambda: None)
    return agents, calls


def test_install_writes_plist_and_loads(fake_agents):
    agents, calls = fake_agents
    path = service.install_service()
    assert path.exists()
    assert path.read_text().startswith("<?xml")
    assert ("load", str(path)) in calls
    assert tray.TRAY_LOG.parent.exists()


def test_uninstall_removes_and_unloads(fake_agents):
    agents, calls = fake_agents
    path = service.install_service()
    assert service.uninstall_service() is True
    assert not path.exists()
    assert ("unload", str(path)) in calls


def test_uninstall_leaves_running_tray_alone(fake_agents, monkeypatch):
    """Unload would kill the tray serving the Settings page the toggle lives on."""
    agents, calls = fake_agents
    path = service.install_service()
    monkeypatch.setattr(service.tray, "read_pidfile", lambda: 4242)
    assert service.uninstall_service() is True
    assert not path.exists()
    assert not any(c[0] == "unload" for c in calls)


def test_uninstall_when_absent(fake_agents):
    assert service.uninstall_service() is False


def test_linux_autostart_exec_quotes_path(tmp_path):
    py = str(tmp_path / "Rish O'Brien" / "py env" / "python3")
    txt = service.render_autostart_entry(py, 8457, "/a:/b c")
    exec_line = (
        f"Exec=env {launcher.desktop_quote('PATH=/a:/b c')} {launcher.desktop_quote(py)}"
        " -m anyscribe tray --port 8457"
    )
    assert exec_line in txt
    assert f'"{py}"' in txt and "\\'" not in txt
    for line in ("Type=Application", "Name=anyscribe tray", "Terminal=false", "NoDisplay=true"):
        assert line in txt
    assert "X-GNOME-Autostart-enabled=true" in txt


def test_install_service_linux_writes_autostart(monkeypatch, tmp_path):
    monkeypatch.setattr(service.sys, "platform", "linux")
    monkeypatch.setattr(service, "autostart_dir", lambda: tmp_path / "autostart")
    path = service.install_service(port=9000)
    assert path == tmp_path / "autostart" / "anyscribe-tray.desktop"
    assert "--port 9000" in path.read_text() and service.is_installed()
    assert service.uninstall_service() is True and not path.exists()
    assert service.uninstall_service() is False


def test_install_service_windows_creates_startup_shortcut(monkeypatch, tmp_path):
    monkeypatch.setattr(service.sys, "platform", "win32")
    monkeypatch.setattr(service, "startup_dir", lambda: tmp_path / "Startup")
    calls = []
    monkeypatch.setattr(service.launcher, "create_shortcut", lambda *a, **k: calls.append((a, k)))
    path = service.install_service()
    assert path == tmp_path / "Startup" / "anyscribe tray.lnk"
    assert calls == [
        ((path, launcher.pythonw(), "-m anyscribe tray --port 8457", None, "anyscribe tray"), {})
    ]
    path.parent.mkdir()
    path.write_text("")  # stand-in for the .lnk PowerShell would have written
    assert service.uninstall_service() is True and not path.exists()


def test_install_service_unsupported_platform(monkeypatch):
    monkeypatch.setattr(service.sys, "platform", "freebsd")
    assert service.supported() is False
    with pytest.raises(NotImplementedError):
        service.install_service()


# ---- teardown (signal / quit / exception path) ----------------------------


class FakeProc:
    """Fake Popen: ignores /shutdown, exits only after terminate()."""

    def __init__(self):
        self.terminated = False
        self.killed = False

    def wait(self, timeout=None):
        if not self.terminated:
            raise subprocess.TimeoutExpired("scribe ui", timeout)
        return 0

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


def test_teardown_stops_owned_server_and_removes_pidfile(monkeypatch, tmp_path):
    from anyscribe.cli import tray_cmd

    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    tray.write_pidfile()
    proc = FakeProc()
    state = {"proc": proc}

    tray_cmd._teardown(state, port=1)  # port 1: /shutdown POST fails fast, ignored

    assert proc.terminated is True  # stop was requested (SIGTERM after POST failed)
    assert proc.killed is False  # exited after terminate, no SIGKILL needed
    assert "proc" not in state  # idempotent — second call won't re-stop
    assert not (tmp_path / "tray.pid").exists()


def test_teardown_leaves_attached_server_alone(monkeypatch, tmp_path):
    from anyscribe.cli import tray_cmd

    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    tray.write_pidfile()

    tray_cmd._teardown({"proc": None}, port=1)  # attached: we own nothing

    assert not (tmp_path / "tray.pid").exists()  # pidfile still cleaned up


# ---- missing-extra error path --------------------------------------------


def test_tray_missing_extra(monkeypatch):
    import builtins

    from anyscribe.cli.main import app

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pystray" or name.startswith("PIL"):
            raise ImportError("no tray extra")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = runner.invoke(app, ["tray"])
    assert result.exit_code == 1
    assert "anyscribe[tray]" in result.output


def test_install_service_unsupported_platform_cli(monkeypatch):
    monkeypatch.setattr(service.sys, "platform", "freebsd")
    monkeypatch.setattr("platform.system", lambda: "FreeBSD")
    result = runner.invoke(app, ["install-service", "--yes"])
    assert result.exit_code == 1
    assert "not supported on FreeBSD" in result.output


def test_install_service_refused_without_tray(monkeypatch, fake_agents):
    from anyscribe.cli import service_cmd

    agents, calls = fake_agents
    monkeypatch.setattr(service_cmd, "find_spec", lambda name: None)
    result = runner.invoke(app, ["install-service", "--yes", "--json"])
    assert result.exit_code == 1
    assert 'pip install \\"anyscribe[tray]\\" first.' in result.output  # JSON-escaped
    assert not agents.exists() and calls == []


def test_setup_callback_makes_icon_visible():
    # pystray replaces its default setup (whose whole job is `icon.visible =
    # True`) with ours — if ours doesn't set visible, the tray NEVER appears.
    # Regression test for the invisible-tray bug in 0.13.1.
    from anyscribe.cli.tray_cmd import _mark_template

    class FakeIcon:
        def __init__(self):
            self.visible = False
            self._icon_image = None  # not yet created, like pystray pre-show

    icon = FakeIcon()
    _mark_template(icon)
    assert icon.visible is True


# ---- desktop mode: second tray, Windows, stop_tray ------------------------


def test_tray_exits_zero_when_already_running(monkeypatch):
    # A login item relaunches any non-zero exit, so a duplicate must exit 0.
    monkeypatch.setattr(tray_cmd.core, "read_pidfile", lambda: 4242)
    monkeypatch.setitem(sys.modules, "pystray", types.ModuleType("pystray"))
    monkeypatch.setitem(sys.modules, "PIL", types.ModuleType("PIL"))
    sys.modules["PIL"].Image = object
    result = CliRunner().invoke(app, ["tray"])
    assert result.exit_code == 0
    assert "already running" in result.output


def test_signal_watch_is_skipped_on_windows(monkeypatch):
    monkeypatch.setattr(tray_cmd.os, "name", "nt")
    monkeypatch.setattr(
        tray_cmd.signal,
        "pthread_sigmask",
        lambda *a: pytest.fail("pthread_sigmask called on nt"),
        raising=False,
    )
    tray_cmd._watch_signals_in_thread({"proc": None}, 8457)


def test_child_kwargs_per_platform(monkeypatch):
    assert set(tray_cmd._child_kwargs()) == {"preexec_fn"}
    monkeypatch.setattr(tray_cmd.os, "name", "nt")
    monkeypatch.setattr(tray_cmd.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    assert tray_cmd._child_kwargs() == {"creationflags": 0x08000000}


def test_stop_tray_shuts_down_and_kills(monkeypatch, tmp_path):
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    tray.PIDFILE.write_text("777")
    monkeypatch.setattr(tray, "_pid_alive", lambda pid: True)
    killed, posted = [], []
    monkeypatch.setattr(tray.os, "kill", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(tray, "_post_shutdown", lambda port: posted.append(port))
    assert tray.stop_tray(8457) is True
    assert killed == [(777, signal.SIGTERM)] and posted == [8457]
    assert not tray.PIDFILE.exists()


def test_stop_tray_without_tray_signals_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    monkeypatch.setattr(tray.os, "kill", lambda pid, sig: pytest.fail("kill without a pid"))
    monkeypatch.setattr(tray, "_post_shutdown", lambda port: None)
    assert tray.stop_tray(8457) is False
