"""Tailnet sharing (core/tailnet.py) with the tailscale CLI faked.

The fake keeps a real serve config dict and records every argv, so tests can
assert exactly which rule survived and which command was never issued.
"""

from __future__ import annotations

import copy
import json
import socket
import subprocess

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from anyscribe.cli.main import app as cli_app
from anyscribe.config.paths import CONFIG_FILE
from anyscribe.core import tailnet

HOST = "box.tail1234.ts.net"
OTHER = {
    "TCP": {"443": {"HTTPS": True}, "8443": {"HTTPS": True}},
    "Web": {
        f"{HOST}:443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:18789"}}},
        f"{HOST}:8443": {"Handlers": {"/hook": {"Proxy": "http://127.0.0.1:4200/hook"}}},
    },
    "AllowFunnel": {f"{HOST}:8443": True},
}


def ours(port: int) -> tuple[dict, dict]:
    return {"HTTPS": True}, {"Handlers": {"/": {"Proxy": f"http://127.0.0.1:{port}"}}}


class FakeTailscale:
    def __init__(self, config: dict | None = None) -> None:
        self.config = copy.deepcopy(OTHER if config is None else config)
        self.calls: list[list[str]] = []
        self.backend = "Running"
        self.status_rc = 0
        self.serve_result: tuple[int, str, str] | None = None  # force a `serve --bg` outcome
        self.serve_timeout_output: bytes | None = None

    def __call__(self, args, capture_output=True, text=True, timeout=None):
        argv = list(args[1:])
        self.calls.append(argv)
        done = lambda rc=0, out="", err="": subprocess.CompletedProcess(args, rc, out, err)  # noqa: E731
        if argv == ["status", "--json"]:
            body = {"BackendState": self.backend, "Self": {"DNSName": HOST + "."}}
            return done(self.status_rc, json.dumps(body))
        if argv == ["serve", "status", "--json"]:
            return done(0, json.dumps(self.config))
        if argv[:2] == ["serve", "--bg"]:
            if self.serve_timeout_output is not None:
                raise subprocess.TimeoutExpired(args, timeout, output=self.serve_timeout_output)
            if self.serve_result:
                return done(*self.serve_result)
            port = argv[2].split("=")[1]
            tcp, web = ours(int(port))
            assert argv[3] == f"http://127.0.0.1:{port}"
            self.config.setdefault("TCP", {})[port] = tcp
            self.config.setdefault("Web", {})[f"{HOST}:{port}"] = web
            return done()
        if argv[0] == "serve" and argv[-1] == "off":
            port = argv[1].split("=")[1]
            self.config["TCP"].pop(port, None)
            self.config["Web"].pop(f"{HOST}:{port}", None)
            return done()
        raise AssertionError(f"unexpected tailscale call: {argv}")


@pytest.fixture
def fake(monkeypatch, tmp_path):
    ts = FakeTailscale()
    monkeypatch.setattr(tailnet, "OWNED_FILE", tmp_path / "tailnet-owned.json")
    monkeypatch.setattr(tailnet, "find_cli", lambda: "/usr/bin/tailscale")
    monkeypatch.setattr(tailnet.subprocess, "run", ts)
    monkeypatch.setattr(tailnet, "run_override", None)
    return ts


@pytest.fixture
def config_restored():
    before = CONFIG_FILE.read_bytes() if CONFIG_FILE.exists() else None
    yield
    if before is None:
        CONFIG_FILE.unlink(missing_ok=True)
    else:
        CONFIG_FILE.write_bytes(before)


def bg_calls(ts: FakeTailscale) -> list[list[str]]:
    return [c for c in ts.calls if c[:2] == ["serve", "--bg"]]


def off_calls(ts: FakeTailscale) -> list[list[str]]:
    return [c for c in ts.calls if c[-1:] == ["off"]]


# ── start: success and each failure case ─────────────────────


def test_start_shares_the_port_and_reports_the_live_link(fake):
    status = tailnet.start(8467)
    assert status.active and status.url == f"https://{HOST}:8467/"
    assert bg_calls(fake) == [["serve", "--bg", "--https=8467", "http://127.0.0.1:8467"]]
    assert tailnet.port_state(fake.config, 8467) == "ours"
    assert tailnet.describe(status) == f"Shared on your tailnet → https://{HOST}:8467/"


def test_not_installed_says_so_and_calls_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(tailnet, "find_cli", lambda: None)
    monkeypatch.setattr(tailnet.subprocess, "run", lambda *a, **k: calls.append(a))
    status = tailnet.start(8467)
    assert not status.active and status.url is None
    assert "isn't installed" in status.reason and "tailscale.com/download" in status.fix
    assert calls == []


def test_mac_app_bundle_cli_is_found(monkeypatch, tmp_path):
    exe = tmp_path / "Tailscale"
    exe.write_text("")
    monkeypatch.setattr(tailnet.shutil, "which", lambda name: None)
    monkeypatch.setattr(tailnet.sys, "platform", "darwin")
    monkeypatch.setattr(tailnet, "MAC_APP_CLI", str(exe))
    assert tailnet.find_cli() == str(exe)
    monkeypatch.setattr(tailnet.sys, "platform", "linux")
    assert tailnet.find_cli() is None


@pytest.mark.parametrize("backend,rc", [("Stopped", 0), ("NeedsLogin", 0), ("Running", 1)])
def test_not_running_or_signed_out(fake, backend, rc):
    fake.backend, fake.status_rc = backend, rc
    status = tailnet.start(8467)
    assert not status.active and status.url is None
    assert "not running or not signed in" in status.reason
    assert bg_calls(fake) == []


def test_permission_refused_names_the_operator_fix(fake, monkeypatch):
    monkeypatch.setattr(tailnet.sys, "platform", "linux")
    fake.serve_result = (
        1,
        "",
        "sending serve config: Access denied: serve config denied\n\n"
        "To not require root, use 'sudo tailscale set --operator=$USER' once.\n",
    )
    status = tailnet.start(8467)
    assert not status.active and status.url is None
    assert "won't let your user" in status.reason
    assert status.fix == "Run once: sudo tailscale set --operator=$USER"
    assert tailnet._owned_ports() == set()


def test_https_not_enabled_passes_the_enable_url_through(fake):
    url = "https://login.tailscale.com/f/serve?node=abc123"
    fake.serve_timeout_output = (
        f"Serve is not enabled on your tailnet.\nTo enable, visit:\n\n    {url}\n".encode()
    )
    status = tailnet.start(8467)
    assert not status.active and status.url is None
    assert "isn't enabled on your tailnet" in status.reason
    assert url in status.fix
    assert tailnet.port_state(fake.config, 8467) == "free"
    assert tailnet._owned_ports() == set()  # a failed serve is never recorded as ours


def test_port_served_to_a_different_target_is_never_overwritten(fake):
    fake.config["TCP"]["8467"] = {"HTTPS": True}
    fake.config["Web"][f"{HOST}:8467"] = {"Handlers": {"/": {"Proxy": "http://127.0.0.1:9999"}}}
    status = tailnet.start(8467)
    assert bg_calls(fake) == []
    assert fake.config["Web"][f"{HOST}:8467"] == {
        "Handlers": {"/": {"Proxy": "http://127.0.0.1:9999"}}
    }
    assert not status.active and status.url is None
    assert "Port 8467 is already shared" in status.reason and "--port" in status.fix


def test_a_funnel_port_is_never_treated_as_ours(fake):
    tcp, web = ours(8443)
    cfg = {
        "TCP": {"8443": tcp},
        "Web": {f"{HOST}:8443": web},
        "AllowFunnel": {f"{HOST}:8443": True},
    }
    assert tailnet.port_state(cfg, 8443) == "taken"


def test_a_hand_made_matching_rule_is_used_but_never_removed(fake):
    """C1: the exact rule from ask.md, made by hand, survives anyscribe's stop."""
    tcp, web = ours(8467)
    fake.config["TCP"]["8467"], fake.config["Web"][f"{HOST}:8467"] = tcp, web
    share = tailnet.Share(8467)
    status = share.apply(True)
    assert status.active and status.url == f"https://{HOST}:8467/"
    assert status.note == tailnet.HANDMADE and status.owned is False
    assert bg_calls(fake) == []
    share.close()
    assert off_calls(fake) == []
    assert fake.config["TCP"]["8467"] == {"HTTPS": True}
    assert fake.config["Web"][f"{HOST}:8467"] == {
        "Handlers": {"/": {"Proxy": "http://127.0.0.1:8467"}}
    }
    assert tailnet._owned_ports() == set()


def test_a_recorded_leftover_from_a_hard_kill_is_reused_then_removed(fake):
    first = tailnet.Share(8467)
    first.apply(True)  # creates and records the rule, then the process "dies" (no close)
    assert tailnet._owned_ports() == {8467}
    second = tailnet.Share(8467)
    status = second.apply(True)
    assert status.active and status.note is None
    assert bg_calls(fake) == [["serve", "--bg", "--https=8467", "http://127.0.0.1:8467"]]
    second.close()
    assert off_calls(fake) == [["serve", "--https=8467", "off"]]
    assert fake.config == OTHER and tailnet._owned_ports() == set()


def test_a_failed_repeat_on_does_not_orphan_our_rule(fake):
    """C6: a temporary failure on a second "on" must not make shutdown forget the rule."""
    share = tailnet.Share(8467)
    share.apply(True)
    fake.backend = "Stopped"  # the repeat start fails before reaching serve
    assert share.apply(True).active is False
    fake.backend = "Running"
    share.close()
    assert off_calls(fake) == [["serve", "--https=8467", "off"]]
    assert fake.config == OTHER


def test_failure_line_is_one_line_with_reason_and_fix(fake):
    fake.backend = "Stopped"
    line = tailnet.describe(tailnet.start(8467))
    assert "\n" not in line
    assert line.startswith("Tailnet sharing is on but not working: Tailscale is installed")
    assert "Fix: Open Tailscale" in line


# ── stop: only our own rule ──────────────────────────────────


def test_stop_removes_our_rule_and_leaves_every_other_rule_identical(fake):
    tailnet.start(8467)
    tailnet.stop(8467)
    assert off_calls(fake) == [["serve", "--https=8467", "off"]]
    assert fake.config == OTHER
    assert tailnet._owned_ports() == set()


def test_stop_never_removes_an_unrecorded_rule(fake):
    tcp, web = ours(8467)
    fake.config["TCP"]["8467"], fake.config["Web"][f"{HOST}:8467"] = tcp, web
    tailnet.stop(8467)
    assert off_calls(fake) == [] and fake.config["Web"][f"{HOST}:8467"] == web


def test_stop_leaves_a_rule_that_now_points_elsewhere(fake):
    tailnet.start(8467)
    fake.config["Web"][f"{HOST}:8467"] = {"Handlers": {"/": {"Proxy": "http://127.0.0.1:9999"}}}
    tailnet.stop(8467)
    assert off_calls(fake) == []
    assert fake.config["Web"][f"{HOST}:8467"] == {
        "Handlers": {"/": {"Proxy": "http://127.0.0.1:9999"}}
    }


def test_share_off_touches_tailscale_only_when_it_was_live(fake):
    share = tailnet.Share(8467)
    share.apply(False)
    assert fake.calls == []
    share.apply(True)
    share.apply(False)
    assert off_calls(fake) == [["serve", "--https=8467", "off"]]
    assert fake.config == OTHER


# ── the server lifecycle: setting off = zero calls ───────────


@pytest.fixture
def lifecycle(monkeypatch):
    """Make web.app.run run startup + shutdown events once instead of serving."""
    import uvicorn

    seen = {}

    def fake_serve(self, sockets=None):
        app = self.config.app
        with TestClient(app):
            seen["status"] = app.state.tailnet.status
        seen["port"] = app.state.tailnet.port

    monkeypatch.setattr(uvicorn.Server, "run", fake_serve)
    return seen


def test_setting_off_never_calls_tailscale(fake, lifecycle, config_restored):
    from anyscribe.core.config_set import set_value
    from anyscribe.web.app import run

    assert set_value("tailnet", "off").ok
    run(port=8467, open_browser=False)
    assert fake.calls == []
    assert lifecycle["status"].enabled is False


def test_setting_on_shares_at_startup_and_unshares_at_shutdown(
    fake, lifecycle, config_restored, capsys
):
    from anyscribe.core.config_set import set_value
    from anyscribe.web.app import run

    assert set_value("tailnet", "on").ok
    run(port=8467, open_browser=False)
    assert lifecycle["status"].active
    assert bg_calls(fake) == [["serve", "--bg", "--https=8467", "http://127.0.0.1:8467"]]
    assert off_calls(fake) == [["serve", "--https=8467", "off"]]
    assert fake.config == OTHER
    assert f"Shared on your tailnet → https://{HOST}:8467/" in capsys.readouterr().out


# ── CLI flags ────────────────────────────────────────────────

runner = CliRunner()


@pytest.fixture
def busy_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    yield s.getsockname()[1]
    s.close()


def test_rolled_forward_port_is_the_one_shared(fake, lifecycle, config_restored, busy_port):
    from anyscribe.core.config_set import set_value

    assert set_value("tailnet", "on").ok
    result = runner.invoke(cli_app, ["ui", "--port", str(busy_port), "--no-open"])
    assert result.exit_code == 0, result.output
    chosen = lifecycle["port"]
    assert chosen > busy_port
    assert bg_calls(fake) == [["serve", "--bg", f"--https={chosen}", f"http://127.0.0.1:{chosen}"]]


def test_tailnet_flag_shares_this_run_without_saving(fake, lifecycle, config_restored):
    from anyscribe.config.settings import load_config
    from anyscribe.core.config_set import set_value

    assert set_value("tailnet", "off").ok
    result = runner.invoke(cli_app, ["ui", "--port", "8467", "--no-open", "--tailnet"])
    assert result.exit_code == 0, result.output
    assert bg_calls(fake) == [["serve", "--bg", "--https=8467", "http://127.0.0.1:8467"]]
    assert load_config().tailnet is False


def test_local_only_flag_beats_the_setting_and_calls_nothing(fake, lifecycle, config_restored):
    from anyscribe.config.settings import load_config
    from anyscribe.core.config_set import set_value

    assert set_value("tailnet", "on").ok
    result = runner.invoke(cli_app, ["ui", "--port", "8467", "--no-open", "--local-only"])
    assert result.exit_code == 0, result.output
    assert fake.calls == []
    assert load_config().tailnet is True


def test_both_flags_is_an_error_and_starts_nothing(fake, lifecycle):
    result = runner.invoke(cli_app, ["ui", "--no-open", "--tailnet", "--local-only"])
    assert result.exit_code == 2
    assert "not both" in result.output
    assert "port" not in lifecycle and fake.calls == []


@pytest.mark.parametrize(
    "raw,expected", [("on", True), ("yes", True), ("true", True), ("off", False), ("false", False)]
)
def test_config_set_accepts_boolean_spellings(raw, expected, config_restored):
    result = runner.invoke(cli_app, ["config", "set", "tailnet", raw])
    assert result.exit_code == 0, result.output
    from anyscribe.config.settings import load_config

    assert load_config().tailnet is expected


# ── web API ──────────────────────────────────────────────────


@pytest.fixture
def client(fake, config_restored):
    from anyscribe.web.app import create_app

    app = create_app()
    app.state.tailnet.port = 8467
    return TestClient(app)


def test_api_toggle_saves_and_applies_live(client, fake):
    assert client.get("/api/tailnet").json() == {
        "enabled": False,
        "active": False,
        "url": None,
        "reason": None,
        "fix": None,
        "note": None,
        "saved": False,
    }
    on = client.put("/api/tailnet", json={"enabled": True}).json()
    assert on["active"] and on["url"] == f"https://{HOST}:8467/" and on["saved"] is True
    assert tailnet.port_state(fake.config, 8467) == "ours"
    off = client.put("/api/tailnet", json={"enabled": False}).json()
    assert off["enabled"] is False and off["saved"] is False
    assert fake.config == OTHER


def test_api_reports_the_failure_reason(client, fake):
    fake.backend = "Stopped"
    data = client.put("/api/tailnet", json={"enabled": True}).json()
    assert data["enabled"] and not data["active"] and data["url"] is None
    assert "not running" in data["reason"] and data["fix"]


def test_put_config_applies_tailnet_live_too(client, fake):
    assert client.put("/api/config", json={"tailnet": True}).json()["tailnet"] is True
    assert tailnet.port_state(fake.config, 8467) == "ours"
    client.put("/api/config", json={"tailnet": False})
    assert fake.config == OTHER
