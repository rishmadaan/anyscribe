"""Unit tests for the tray companion — no GUI, no real launchctl."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
import types
from pathlib import Path

import pytest
from typer.testing import CliRunner

from anyscribe.cli import tray_cmd
from anyscribe.cli.main import app
from anyscribe.core import launcher, service, tray

runner = CliRunner()
REAL_READ_PIDFILE = tray.read_pidfile  # before fake_agents stubs it


@pytest.fixture(autouse=True)
def tmp_tray_files(monkeypatch, tmp_path):
    """Every pidfile and lock in a tmp dir, never one a real tray holds."""
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    monkeypatch.setattr(tray, "SERVER_PIDFILE", tmp_path / "server.pid")
    monkeypatch.setattr(tray, "LOCKFILE", tmp_path / "tray.lock")


def _free_port() -> int:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---- pidfile -------------------------------------------------------------


def test_pidfile_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    monkeypatch.setattr(tray, "pid_is_anyscribe", lambda pid, role: True)
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
    log = Path("/tmp/t.log")
    xml = service.render_plist(python="/usr/bin/python3", port=9000, path_env="/a:/b", log=log)
    assert "<key>PATH</key>" in xml and "<string>/a:/b</string>" in xml
    assert "<string>--port</string>" in xml and "<string>9000</string>" in xml
    assert "<key>SuccessfulExit</key>" in xml and "<false/>" in xml
    assert f"<string>{log}</string>" in xml


def test_plist_has_throttle_interval():
    xml = service.render_plist(python="/usr/bin/python3")
    assert "<key>ThrottleInterval</key>" in xml and "<integer>10</integer>" in xml


def test_plist_process_type_interactive():
    """Without it launchd throttles the server's children (ffmpeg, yt-dlp): 5-13 s vs 0.3 s."""
    import plistlib

    xml = service.render_plist(python="/usr/bin/python3")
    assert plistlib.loads(xml.encode())["ProcessType"] == "Interactive"


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


@pytest.mark.parametrize("code", [0, 5])  # legacy load/unload exit 0 even when they fail
def test_launchctl_failure_prints_one_plain_line(monkeypatch, capsys, code):
    err = "Load failed: 5: Input/output error\nTry running `launchctl bootstrap` as root for richer errors.\n"
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda args, **k: subprocess.CompletedProcess(args, code, "", err),
    )
    service._launchctl("load", "/x.plist")
    out = capsys.readouterr()
    assert out.err == "launchctl load did not succeed: Load failed: 5: Input/output error\n"
    assert out.out == ""


def test_launchctl_success_prints_nothing(monkeypatch, capsys):
    seen = {}

    def run(args, **k):
        seen.update(k)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(service.subprocess, "run", run)
    service._launchctl("load", "/x.plist")
    assert capsys.readouterr() == ("", "")
    assert seen["capture_output"] is True  # launchctl's own text never reaches the terminal


def test_linux_autostart_exec_quotes_path(tmp_path):
    py = "/home/Rish O'Brien/py env/python3"  # POSIX literal: a .desktop path has no backslashes
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

    pid = 999

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
    state = {"proc": proc, "lock": threading.Lock()}

    tray_cmd._teardown(state, port=1)  # port 1: /shutdown POST fails fast, ignored

    assert proc.terminated is True  # stop was requested (SIGTERM after POST failed)
    assert proc.killed is False  # exited after terminate, no SIGKILL needed
    assert "proc" not in state  # idempotent — second call won't re-stop
    assert not (tmp_path / "tray.pid").exists()


def test_teardown_leaves_attached_server_alone(monkeypatch, tmp_path):
    from anyscribe.cli import tray_cmd

    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    tray.write_pidfile()

    tray_cmd._teardown({"proc": None, "lock": threading.Lock()}, port=1)  # attached: own nothing

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
    assert (
        'The tray isn\'t installed. Run: pip install \\"anyscribe[tray]\\" first.' in result.output
    )
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
    monkeypatch.setattr(tray_cmd.core, "acquire_instance_lock", lambda: None)
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
    tray_cmd._watch_signals_in_thread(lambda: None, lambda: None)


def test_child_kwargs_per_platform(monkeypatch):
    assert set(tray_cmd._child_kwargs()) == (
        {"creationflags"} if os.name == "nt" else {"preexec_fn"}
    )
    monkeypatch.setattr(tray_cmd.os, "name", "nt")
    monkeypatch.setattr(tray_cmd.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    assert tray_cmd._child_kwargs() == {"creationflags": 0x08000000}


def test_stop_tray_shuts_down_and_kills(monkeypatch, tmp_path):
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    monkeypatch.setattr(tray, "pid_is_anyscribe", lambda pid, role: True)
    tray.PIDFILE.write_text("777")
    killed, posted = [], []
    monkeypatch.setattr(tray, "_pid_alive", lambda pid: not killed)  # exits on SIGTERM
    monkeypatch.setattr(tray, "port_responding", lambda port: False)
    monkeypatch.setattr(tray.os, "kill", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(tray, "_post_shutdown", lambda port: posted.append(port))
    assert tray.stop_tray(8457) is True
    assert killed == [(777, signal.SIGTERM)] and posted == [8457]
    assert not tray.PIDFILE.exists()


def test_stop_tray_without_tray_signals_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    monkeypatch.setattr(tray.os, "kill", lambda pid, sig: pytest.fail("kill without a pid"))
    monkeypatch.setattr(tray, "_post_shutdown", lambda port: None)
    monkeypatch.setattr(tray, "port_responding", lambda port: False)
    assert tray.stop_tray(8457) is False


def test_stop_tray_removes_pidfile_when_kill_raises_oserror(monkeypatch, tmp_path):
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    monkeypatch.setattr(tray, "pid_is_anyscribe", lambda pid, role: True)
    tray.PIDFILE.write_text("777")
    monkeypatch.setattr(tray, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(tray, "_post_shutdown", lambda port: None)
    monkeypatch.setattr(tray, "port_responding", lambda port: False)

    def kill(pid, sig):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(tray.os, "kill", kill)
    assert tray.stop_tray(8457) is False
    assert not tray.PIDFILE.exists()


def test_stop_tray_waits_for_port_to_free(monkeypatch, tmp_path):
    # The old server must be gone before stop_tray returns, or a new tray attaches to it.
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    monkeypatch.setattr(tray, "pid_is_anyscribe", lambda pid, role: True)
    tray.PIDFILE.write_text("777")
    alive = iter([True, True, False])  # read_pidfile, first poll, then exited
    monkeypatch.setattr(tray, "_pid_alive", lambda pid: next(alive, False))
    answers, probes = iter([True, True, False]), []

    def port_responding(port):
        probes.append(port)
        return next(answers, False)

    monkeypatch.setattr(tray, "port_responding", port_responding)
    monkeypatch.setattr(tray.time, "sleep", lambda s: None)
    monkeypatch.setattr(tray.os, "kill", lambda pid, sig: None)
    monkeypatch.setattr(tray, "_post_shutdown", lambda port: None)
    assert tray.stop_tray(8457) is True
    assert len(probes) >= 3
    assert not tray.PIDFILE.exists()


def test_stop_tray_kills_when_pid_outlives_timeout(monkeypatch, tmp_path):
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    monkeypatch.setattr(tray, "pid_is_anyscribe", lambda pid, role: True)
    tray.PIDFILE.write_text("777")
    monkeypatch.setattr(tray, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(tray, "port_responding", lambda port: False)
    monkeypatch.setattr(tray.time, "sleep", lambda s: None)
    monkeypatch.setattr(tray, "_post_shutdown", lambda port: None)
    killed = []
    monkeypatch.setattr(tray.os, "kill", lambda pid, sig: killed.append((pid, sig)))
    assert tray.stop_tray(8457, timeout=0.01) is True
    kill_sig = getattr(signal, "SIGKILL", signal.SIGTERM)
    assert killed == [(777, signal.SIGTERM), (777, kill_sig)]


def test_remove_pidfile_leaves_another_trays_file(monkeypatch, tmp_path):
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    tray.PIDFILE.write_text(str(os.getpid() + 1))
    tray.remove_pidfile()
    assert tray.PIDFILE.read_text() == str(os.getpid() + 1)
    tray.remove_pidfile(force=True)
    assert not tray.PIDFILE.exists()
    tray.PIDFILE.write_text(str(os.getpid()))
    tray.remove_pidfile()
    assert not tray.PIDFILE.exists()


# ---- ownership: instance lock, identity on the wire, only signal what is ours ----

_LOCK_CHILD = """
import sys, time
from pathlib import Path
from anyscribe.core import tray
lock = tray.acquire_instance_lock(Path(sys.argv[1]))
print("got" if lock else "busy", flush=True)
time.sleep(float(sys.argv[2]))
"""


def test_instance_lock_excludes_second_process(tmp_path):
    lockfile = tmp_path / "tray.lock"

    def child(hold: float) -> subprocess.Popen:
        return subprocess.Popen(
            [sys.executable, "-c", _LOCK_CHILD, str(lockfile), str(hold)],
            stdout=subprocess.PIPE,
            text=True,
        )

    first = child(2)
    first_line = first.stdout.readline().strip()  # it holds the lock from here on
    second = child(0)
    second_line = second.stdout.readline().strip()
    second.wait(timeout=10)
    first.wait(timeout=10)
    assert (first_line, second_line) == ("got", "busy")
    # Released at exit, however the holder exits: the next tray is not locked out.
    assert tray.acquire_instance_lock(lockfile) is not None


def test_tray_command_exits_zero_while_lock_held(tmp_path):
    """The real launch command, not a fake: a second `anyscribe tray` exits 0, starting nothing."""
    home = tmp_path / "home"
    held = tray.acquire_instance_lock(home / ".anyscribe" / "tray.lock")
    assert held is not None
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    r = subprocess.run(
        [sys.executable, "-m", "anyscribe", "tray", "--port", str(_free_port())],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    held.close()
    assert r.returncode == 0, r.stderr
    assert "An anyscribe tray is already running." in r.stderr
    assert not (home / ".anyscribe" / "tray.pid").exists()


def test_health_identity_requires_app_field(health_server):
    assert tray.health_is_anyscribe(health_server.port) is False  # {"version": "1"}: foreign
    health_server.body = {"app": "anyscribe", "version": "1"}
    assert tray.health_is_anyscribe(health_server.port) is True


def test_health_identity_accepts_pre_0_18_shape(health_server):
    """A 0.17 server (pip upgrade, desktop install not yet re-run) is still anyscribe."""
    health_server.body = {"ok": True, "version": "0.17.1", "dependencies": {"ffmpeg": True}}
    assert tray.health_is_anyscribe(health_server.port) is True


def test_health_identity_explicit_foreign_app_wins(health_server):
    """Another program's own "app" name is foreign even with anyscribe's legacy keys."""
    health_server.body = {"app": "another-program", "version": "1", "dependencies": {}}
    assert tray.health_is_anyscribe(health_server.port) is False


def test_health_identity_legacy_shape_is_typed(health_server):
    health_server.body = {"version": None, "dependencies": None}
    assert tray.health_is_anyscribe(health_server.port) is False


def test_post_shutdown_leaves_foreign_server_alone(health_server):
    tray._post_shutdown(health_server.port)
    assert health_server.posts == []
    health_server.body = {"app": "anyscribe", "version": "1"}
    tray._post_shutdown(health_server.port)
    assert health_server.posts == ["/api/shutdown"]


def test_pid_is_anyscribe_rejects_non_positive_and_other_programs():
    assert tray.pid_is_anyscribe(0, "tray") is False and tray.pid_is_anyscribe(-1, "tray") is False
    child = subprocess.Popen(_sleeper())
    try:
        assert tray.pid_is_anyscribe(child.pid, "tray") is False
    finally:
        child.kill()
        child.wait()


@pytest.mark.parametrize(
    "cmdline, role, expected",
    [
        ("/usr/bin/python3 -m anyscribe tray --port 8457", "tray", True),
        ("/usr/bin/python3 -m anyscribe ui --port 8457 --no-open", "ui", True),
        ("/usr/bin/python3 -m anyscribe ui --port 8457 --no-open", "tray", False),
        ("/home/x/.venv/bin/python3 /home/x/.venv/bin/scribe tray --port 8457", "tray", True),
        ("/home/x/.venv/bin/python3 /home/x/.venv/bin/ascli tray", "tray", True),
        ('"C:\\Py\\python.exe" "C:\\Py\\Scripts\\anyscribe.exe" tray --port 8457', "tray", True),
        ("C:\\Py\\Scripts\\anyscribe.exe tray", "tray", True),
        ("/x/anyscribe/.venv/bin/python -c import time", "tray", False),  # path, not command
        ("/usr/bin/python3 -m anyscribe https://x", "tray", False),  # a transcription
        ("/usr/bin/transcribe tray", "tray", False),
        ("/usr/bin/python3 -m anyscribe traybox", "tray", False),
    ],
)
def test_command_line_identity(cmdline, role, expected):
    assert tray.command_line_is(cmdline, role) is expected


def test_command_line_identity_ignores_case_only_on_windows(monkeypatch):
    cmd = "C:\\PY\\SCRIPTS\\ANYSCRIBE.EXE TRAY"
    monkeypatch.setattr(tray.os, "name", "posix")
    assert tray.command_line_is(cmd, "tray") is False
    monkeypatch.setattr(tray.os, "name", "nt")
    assert tray.command_line_is(cmd, "tray") is True


def _child(*extra: str) -> subprocess.Popen:
    """A sleeping Python whose command line carries ``extra`` after the script.

    Returns once it runs its script: mid-exec (macOS re-execs a framework
    Python) ps can show another command line, or none.
    """
    script = "import time; print('ready', flush=True); time.sleep(30)"
    child = subprocess.Popen([sys.executable, "-c", script, *extra], stdout=subprocess.PIPE)
    assert child.stdout.readline().strip() == b"ready"
    return child


def test_path_containing_anyscribe_is_not_a_tray_and_survives_stop_tray(tmp_path):
    """A repo checkout's own python (".../anyscribe/.venv/bin/python -c ...") is not the tray."""
    child = _child(str(tmp_path / "anyscribe-x" / "python"))
    try:
        assert tray.pid_is_anyscribe(child.pid, "tray") is False
        tray.PIDFILE.write_text(str(child.pid))
        assert tray.stop_tray(_free_port(), timeout=1) is False
        time.sleep(0.3)  # a signal, had one been sent, has landed
        assert child.poll() is None  # this exact process is still running
    finally:
        child.kill()
        child.wait()


def test_transcription_is_not_a_tray():
    child = _child("-m", "anyscribe", "https://x")
    try:
        assert tray.pid_is_anyscribe(child.pid, "tray") is False
        assert tray.pid_is_anyscribe(child.pid, "ui") is False
    finally:
        child.kill()
        child.wait()


def test_alias_tray_is_recognised_and_keeps_its_login_item_job(fake_agents, monkeypatch):
    """A tray started as `scribe tray`: recognised, so the Settings toggle does not unload it."""
    agents, calls = fake_agents
    child = _child(str(Path("/x/bin/scribe")), "tray", "--port", "8457")
    try:
        assert tray.pid_is_anyscribe(child.pid, "tray") is True
        assert tray.pid_is_anyscribe(child.pid, "ui") is False
        tray.PIDFILE.write_text(str(child.pid))
        monkeypatch.setattr(service.tray, "read_pidfile", REAL_READ_PIDFILE)
        path = service.install_service()
        assert service.uninstall_service() is True and not path.exists()
        assert not any(c[0] == "unload" for c in calls)
        assert child.poll() is None
    finally:
        child.kill()
        child.wait()


def _sleeper() -> list[str]:
    """A long-running process whose command line does not mention anyscribe."""
    return ["ping", "-n", "30", "127.0.0.1"] if os.name == "nt" else ["sleep", "30"]


def test_stale_pidfile_with_reused_pid_is_not_signalled():
    """After a reboot the pidfile's number can belong to an unrelated program."""
    child = subprocess.Popen(_sleeper(), stdout=subprocess.DEVNULL)
    try:
        tray.PIDFILE.write_text(str(child.pid))
        signalled = tray.stop_tray(_free_port(), timeout=1)
        time.sleep(0.3)  # a signal, had one been sent, has landed
        assert child.poll() is None  # the unrelated program is still running
        assert signalled is False
        assert not tray.PIDFILE.exists()  # the stale file is gone
    finally:
        child.kill()
        child.wait()


def test_stop_tray_stops_recorded_server(monkeypatch):
    """The tray's teardown is skipped on Windows; the server is stopped by its own pid."""
    tray.PIDFILE.write_text("777")
    tray.SERVER_PIDFILE.write_text("888")
    killed = []
    monkeypatch.setattr(tray, "pid_is_anyscribe", lambda pid, role: True)
    monkeypatch.setattr(tray, "_pid_alive", lambda pid: pid not in [k[0] for k in killed])
    monkeypatch.setattr(tray, "port_responding", lambda port: False)
    monkeypatch.setattr(tray.os, "kill", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(tray, "_post_shutdown", lambda port: None)
    assert tray.stop_tray(8457) is True
    assert killed == [(777, signal.SIGTERM), (888, signal.SIGTERM)]
    assert not tray.PIDFILE.exists() and not tray.SERVER_PIDFILE.exists()


class _FakeMenu:
    SEPARATOR = None

    def __init__(self, *items):
        self.items = items


class _FakeMenuItem:
    def __init__(self, text, action, **kw):
        self.text, self.action = text, action


def _run_fake_tray(monkeypatch, port: int, signals: list | None = None, during=None) -> dict:
    """Run _run_tray with a fake pystray whose loop returns at once; return its menu.

    ``signals`` receives the (restart, teardown) callbacks the tray would watch;
    ``during()`` runs inside the icon loop, before the tray's own teardown.
    """
    menu = {}
    signals = [] if signals is None else signals

    class FakeIcon:
        def __init__(self, name, image, title, m):
            menu.update({str(i.text): i for i in m.items if i})

        def run(self, setup=None):
            if during:
                during()

    fake = types.ModuleType("pystray")
    fake.Menu, fake.MenuItem, fake.Icon = _FakeMenu, _FakeMenuItem, FakeIcon
    monkeypatch.setitem(sys.modules, "pystray", fake)
    monkeypatch.setattr(tray_cmd, "_make_image", lambda: None)
    monkeypatch.setattr(
        tray_cmd, "_watch_signals_in_thread", lambda *callbacks: signals.extend(callbacks)
    )
    tray_cmd._run_tray(port)
    return menu


def test_tray_does_not_attach_to_foreign_server(monkeypatch, health_server, capsys):
    monkeypatch.setattr(
        tray_cmd.subprocess, "Popen", lambda *a, **k: pytest.fail("started a server")
    )
    opened = []
    monkeypatch.setattr(tray_cmd.webbrowser, "open", opened.append)
    menu = _run_fake_tray(monkeypatch, health_server.port)
    status = next(i for i in menu.values() if callable(i.text))
    assert status.text(None) == f"Status: port {health_server.port} is used by another program"
    menu["Open UI"].action(None, None)
    assert opened == []  # Open UI does not open another program's page
    assert "used by another program" in capsys.readouterr().err


def test_tray_records_server_pid(monkeypatch, tmp_path):
    class Proc:
        pid = 4321

        def wait(self, timeout=None):
            return 0

    seen, real_write, popen_kwargs = [], tray.write_pidfile, {}
    monkeypatch.setattr(tray, "TRAY_LOG", tmp_path / "logs" / "tray.log")
    monkeypatch.setattr(
        tray_cmd.subprocess, "Popen", lambda *a, **k: popen_kwargs.update(k) or Proc()
    )
    monkeypatch.setattr(tray_cmd.core, "_post_shutdown", lambda port: None)
    monkeypatch.setattr(
        tray_cmd.core,
        "write_pidfile",
        lambda pid=None, path=None: seen.append((pid, path)) or real_write(pid, path),
    )
    _run_fake_tray(monkeypatch, _free_port())
    assert (4321, tray.SERVER_PIDFILE) in seen
    assert not tray.SERVER_PIDFILE.exists()  # removed again by the teardown
    # Under pythonw.exe the tray has no streams of its own to hand the server.
    assert popen_kwargs["stdin"] is subprocess.DEVNULL
    assert popen_kwargs["stdout"].name == popen_kwargs["stderr"].name == str(tray.TRAY_LOG)


def test_ensure_streams_replaces_none(monkeypatch, tmp_path):
    from anyscribe.web.app import _ensure_streams

    monkeypatch.setattr(tray, "TRAY_LOG", tmp_path / "logs" / "tray.log")
    monkeypatch.setattr(sys, "stdout", None)
    real_stderr = sys.stderr
    _ensure_streams()
    try:
        assert sys.stdout is not None and sys.stdout.name == str(tray.TRAY_LOG)
        assert sys.stderr is real_stderr  # a working stream is left alone
    finally:
        sys.stdout.close()


def test_uvicorn_config_with_no_stdout(tmp_path):
    """The reviewer's probe: uvicorn's log setup calls sys.stdout.isatty() (None under pythonw)."""
    probe = (
        "import sys; sys.stdout = None; "
        "from anyscribe.web.app import _ensure_streams; _ensure_streams(); "
        "import uvicorn; uvicorn.Config('anyscribe.web.app:create_app', factory=True)"
    )
    env = {**os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}
    r = subprocess.run(
        [sys.executable, "-c", probe], env=env, capture_output=True, text=True, timeout=60
    )
    assert r.returncode == 0, r.stderr
    assert (tmp_path / ".anyscribe" / "logs" / "tray.log").exists()


class _Server:
    """Fake server Popen: alive until stopped (``wait`` after /shutdown), or ``exited``."""

    def __init__(self, pid, alive=True):
        self.pid, self.alive = pid, alive

    def poll(self):
        return None if self.alive else 0

    def wait(self, timeout=None):
        self.alive = False
        return 0


def _fake_servers(monkeypatch, tmp_path, health=lambda port: False, gate=None):
    """Stub the tray's server spawn; return the list of every server it started.

    ``gate``: (entered, release) events; every spawn after the first signals
    ``entered`` and waits for ``release``, like a slow Popen.
    """
    servers: list[_Server] = []

    def popen(args, **kwargs):
        if gate and servers:
            gate[0].set()
            assert gate[1].wait(10)
        server = _Server(4000 + len(servers))
        servers.append(server)
        return server

    monkeypatch.setattr(tray, "TRAY_LOG", tmp_path / "logs" / "tray.log")
    monkeypatch.setattr(tray_cmd.time, "sleep", lambda s: None)
    monkeypatch.setattr(tray_cmd.subprocess, "Popen", popen)
    monkeypatch.setattr(tray_cmd.core, "health_is_anyscribe", health)
    monkeypatch.setattr(tray_cmd.core, "port_responding", lambda port, **k: False)
    return servers


def test_tray_restart_lock_is_idempotent(monkeypatch, tmp_path):
    """Two `desktop open` clicks send two SIGUSR1s: the second must not kill the new server."""
    events, seen = [], []
    servers = _fake_servers(monkeypatch, tmp_path)
    # Up once the restart has spawned its server (the startup spawn is the first).
    monkeypatch.setattr(tray_cmd.core, "health_is_anyscribe", lambda port: len(servers) > 1)
    monkeypatch.setattr(tray_cmd.core, "_post_shutdown", lambda port: events.append("shutdown"))
    signals = []

    def during():
        servers[0].alive = False  # stopped by the dashboard's Shutdown
        signals[0]()
        signals[0]()
        seen.extend([s.pid for s in servers if s.alive])
        seen.append(events.count("shutdown"))

    _run_fake_tray(monkeypatch, _free_port(), signals, during)
    assert seen == [4001, 1]  # one new server; only the dead one was shut down


def test_tray_restart_leaves_a_starting_server_alone(monkeypatch, tmp_path):
    """A server still starting (alive, health not yet up) is not shut down or doubled."""
    events, seen = [], []
    servers = _fake_servers(monkeypatch, tmp_path)  # health never answers
    monkeypatch.setattr(tray_cmd.core, "_post_shutdown", lambda port: events.append("shutdown"))
    signals = []

    def during():
        signals[0]()
        seen.extend([[s.pid for s in servers if s.alive], list(events)])

    _run_fake_tray(monkeypatch, _free_port(), signals, during)
    assert seen == [[4000], []]


def test_teardown_stops_a_server_a_concurrent_restart_is_starting(monkeypatch, tmp_path):
    """Quit while a restart is mid-spawn: the restart's server is stopped, not orphaned."""
    entered, release = threading.Event(), threading.Event()
    servers = _fake_servers(monkeypatch, tmp_path, gate=(entered, release))
    monkeypatch.setattr(tray_cmd.core, "_post_shutdown", lambda port: None)
    signals, alive_after = [], []

    def during():
        restart, teardown = signals
        servers[0].alive = False  # stopped by the dashboard's Shutdown
        r = threading.Thread(target=restart)
        r.start()
        assert entered.wait(10)  # the restart popped the old server and is spawning
        t = threading.Thread(target=teardown)
        t.start()
        threading.Event().wait(0.2)  # teardown is waiting for the lock
        release.set()
        r.join(10)
        t.join(10)
        alive_after.extend([s.pid for s in servers if s.alive])

    _run_fake_tray(monkeypatch, _free_port(), signals, during)
    assert [s.pid for s in servers] == [4000, 4001]
    assert alive_after == []  # the restart's server 4001 was stopped by the teardown


def test_restart_waiting_on_the_lock_spawns_nothing_after_quit(monkeypatch, tmp_path):
    """A restart queued behind a teardown must not start a server the exiting tray orphans."""
    in_teardown, release = threading.Event(), threading.Event()
    servers = _fake_servers(monkeypatch, tmp_path)

    def post_shutdown(port):  # the teardown pauses while holding the lock
        in_teardown.set()
        assert release.wait(10)

    monkeypatch.setattr(tray_cmd.core, "_post_shutdown", post_shutdown)
    signals, spawned_after = [], []

    def during():
        restart, teardown = signals
        servers[0].alive = False
        t = threading.Thread(target=teardown)
        t.start()
        assert in_teardown.wait(10)
        r = threading.Thread(target=restart)
        r.start()
        threading.Event().wait(0.2)  # the restart is waiting for the lock
        release.set()
        t.join(10)
        r.join(10)
        spawned_after.extend([s.pid for s in servers])

    _run_fake_tray(monkeypatch, _free_port(), signals, during)
    assert spawned_after == [4000]  # only the startup server; nothing after Quit began


_SIGNAL_CHILD = """
import sys, time
from pathlib import Path
from anyscribe.cli import tray_cmd
out = Path(sys.argv[1])
tray_cmd._watch_signals_in_thread(
    lambda: out.write_text("restarted"),
    lambda: out.write_text(out.read_text() + ",stopped"),
)
print("ready", flush=True)
time.sleep(30)
"""


@pytest.mark.skipif(os.name == "nt", reason="SIGUSR1 and sigwait are POSIX only")
def test_sigusr1_restarts_and_sigterm_still_stops(tmp_path):
    """The real signal path: SIGUSR1 restarts and keeps the tray alive; SIGTERM still exits 0."""
    out = tmp_path / "out"
    child = subprocess.Popen(
        [sys.executable, "-c", _SIGNAL_CHILD, str(out)], stdout=subprocess.PIPE, text=True
    )
    try:
        assert child.stdout.readline().strip() == "ready"
        child.send_signal(signal.SIGUSR1)
        deadline = time.monotonic() + 10
        while not out.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        time.sleep(0.3)  # a kill, had SIGUSR1 been fatal, has landed
        assert out.read_text() == "restarted"
        assert child.poll() is None
        child.send_signal(signal.SIGTERM)
        assert child.wait(timeout=10) == 0
        assert out.read_text() == "restarted,stopped"
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
