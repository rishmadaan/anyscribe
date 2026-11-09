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
        self.serve_status_rc = 0  # nonzero: `serve status` fails (tailscaled stopped)
        self.off_rc = 0  # nonzero: `serve ... off` fails and changes nothing
        self.serve_result: tuple[int, str, str] | None = None  # force a `serve --bg` outcome
        self.serve_timeout_output: bytes | None = None
        self.status_hangs = False  # `status --json` runs past its timeout
        self.timeouts: list = []  # the timeout each call was given

    def __call__(self, args, capture_output=True, text=True, timeout=None):
        argv = list(args[1:])
        self.calls.append(argv)
        self.timeouts.append(timeout)
        done = lambda rc=0, out="", err="": subprocess.CompletedProcess(args, rc, out, err)  # noqa: E731
        if argv == ["status", "--json"] and self.status_hangs:
            raise subprocess.TimeoutExpired(args, timeout)
        if argv == ["status", "--json"]:
            body = {"BackendState": self.backend, "Self": {"DNSName": HOST + "."}}
            return done(self.status_rc, json.dumps(body))
        if argv == ["serve", "status", "--json"]:
            return done(self.serve_status_rc, json.dumps(self.config))
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
            if self.off_rc:
                return done(self.off_rc, "", "failed")
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
    assert tailnet.describe(status) == (
        f"Shared on your tailnet → https://{HOST}:8467/ "
        "(no login: anyone on your tailnet can use it)"
    )


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


def test_switching_off_a_hand_made_share_says_anyscribe_left_it_in_place(fake):
    """R2-C2: anyscribe leaves the user's rule, and the off state says so instead of "Off"."""
    tcp, web = ours(8467)
    fake.config["TCP"]["8467"], fake.config["Web"][f"{HOST}:8467"] = tcp, web
    share = tailnet.Share(8467)
    assert share.apply(True).note == tailnet.HANDMADE
    off = share.apply(False)
    assert not off.enabled and not off.active and off.url is None
    # R3-cF1/fF3: a past event (anyscribe no longer looks), and no literal backticks on the card.
    assert off.note == (
        "anyscribe left your own Tailscale rule on port 8467 in place, but no longer answers "
        "through it. "
        "To remove it: tailscale serve --https=8467 off"
    )
    assert off_calls(fake) == [] and tailnet.port_state(fake.config, 8467) == "ours"
    owned = tailnet.Share(8468)
    owned.apply(True)
    assert owned.apply(False).note is None  # our own rule is removed: nothing left to mention


def test_the_left_in_place_note_shows_even_when_tailscale_was_down_at_switch_off(fake):
    """R3-cF1: the note follows the adopted share being held, not the display, which a
    Tailscale outage turns to failed."""
    tcp, web = ours(8467)
    fake.config["TCP"]["8467"], fake.config["Web"][f"{HOST}:8467"] = tcp, web
    share = tailnet.Share(8467)
    share.apply(True)
    fake.backend = "Stopped"
    assert share.refresh().active is False and share.held == f"https://{HOST}:8467/"
    assert share.apply(False).note == tailnet.LEFT_IN_PLACE.format(port=8467)
    assert off_calls(fake) == [] and tailnet.port_state(fake.config, 8467) == "ours"


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


@pytest.mark.parametrize("undo_works", [True, False])
def test_a_share_that_cannot_be_recorded_is_undone_not_left_unowned(fake, monkeypatch, undo_works):
    """R2-C6: serve --bg worked but the ownership note can't be written: remove the rule."""

    def unwritable(path, content):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(tailnet, "atomic_write", unwritable)
    fake.off_rc = 0 if undo_works else 1
    status = tailnet.start(8467)
    assert not status.active and status.url is None and status.enabled
    assert off_calls(fake) == [["serve", "--https=8467", "off"]]
    assert tailnet._owned_ports() == set()
    if undo_works:
        assert fake.config == OTHER  # no unowned live rule left behind
        assert status.reason.endswith("so it removed it again.")
    else:
        assert tailnet.port_state(fake.config, 8467) == "ours"
        assert status.reason.endswith("and couldn't remove it.")
        assert status.fix.startswith("Remove it: tailscale serve --https=8467 off")


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
        seen["app"] = app
        with TestClient(app):
            self.started = seen.get("bind_ok", True)  # what uvicorn sets once it is listening
            thread = getattr(app.state, "tailnet_thread", None)
            if thread:
                thread.join(seen.get("join", 5))
            seen["status"] = app.state.tailnet.status
            if "during" in seen:  # a test's requests against the live server
                seen["during"](app)
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


def test_a_broken_config_starts_local_only_with_one_line(fake, lifecycle, config_restored, capsys):
    """C5: a malformed config.yaml must not stop `anyscribe ui`; sharing is off, said once."""
    from anyscribe.web.app import run

    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text("tailnet: [\n")
    run(port=8467, open_browser=False)
    assert fake.calls == [] and lifecycle["status"].enabled is False
    out = capsys.readouterr().out
    assert out.count("Couldn't read your anyscribe config") == 1
    assert "tailnet sharing is off for this run" in out


def test_a_quoted_false_in_config_is_off(fake, lifecycle, config_restored):
    from anyscribe.web.app import run

    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text('tailnet: "false"\n')
    run(port=8467, open_browser=False)
    assert fake.calls == [] and lifecycle["status"].enabled is False


def test_a_failed_bind_never_touches_tailscale(fake, lifecycle, config_restored, capsys):
    """C3: startup events run before the bind; sharing must wait until the server listens."""
    from anyscribe.core.config_set import set_value
    from anyscribe.web.app import run

    assert set_value("tailnet", "on").ok
    lifecycle["bind_ok"], lifecycle["join"] = False, 0.5
    run(port=8467, open_browser=False)
    assert fake.calls == []
    assert "Shared on your tailnet" not in capsys.readouterr().out


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
    out = capsys.readouterr().out
    assert (
        f"Shared on your tailnet → https://{HOST}:8467/ "
        "(no login: anyone on your tailnet can use it)" in out
    )
    assert out.index("Asking Tailscale to share it...") < out.index("Shared on your tailnet")


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


def test_tailnet_flag_help_says_there_is_no_login():
    result = runner.invoke(cli_app, ["ui", "--help"], env={"COLUMNS": "200"})
    assert "No login: anyone on your tailnet can use it." in result.output


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
    # C2: turning it on says, once, that the page has no login; turning it off does not.
    assert ("no login: anyone on your tailnet can use it" in result.output) is expected
    # R2-fF5: both ways say when it takes effect.
    assert (
        "Takes effect the next time you start anyscribe ui (or flip it in Settings)."
        in result.output
    )
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
        "card_fix": None,
        "note": None,
        "held": False,
        "saved": False,
    }
    on = client.put("/api/tailnet", json={"enabled": True}).json()
    assert on["active"] and on["url"] == f"https://{HOST}:8467/" and on["saved"] is True
    assert on["held"] is True
    assert tailnet.port_state(fake.config, 8467) == "ours"
    off = client.put("/api/tailnet", json={"enabled": False}).json()
    assert off["enabled"] is False and off["saved"] is False and off["held"] is False
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


def test_put_config_saves_nothing_when_the_tailnet_part_fails(client, fake, monkeypatch):
    """R2-C6: a 422 from PUT /api/config means nothing was saved, tailnet failure included."""
    from anyscribe.config.settings import load_config
    from anyscribe.core import config_set

    real = config_set.set_value
    client.put("/api/config", json={"keep_media": False})
    before = CONFIG_FILE.read_bytes()

    def tailnet_save_fails(key, value):
        if key == "tailnet":
            return config_set.SetOutcome(False, error="disk full")
        return real(key, value)

    monkeypatch.setattr(config_set, "set_value", tailnet_save_fails)
    r = client.put("/api/config", json={"keep_media": True, "tailnet": True})
    assert r.status_code == 422 and r.json()["error"] == "disk full"
    assert CONFIG_FILE.read_bytes() == before and load_config().keep_media is False
    assert fake.calls == []


def test_save_and_apply_hold_one_lock(fake, monkeypatch, config_restored):
    """C7: an "off" sent while an "on" is still applying waits, so saved and live agree."""
    import threading
    import time

    from anyscribe.config.settings import load_config

    share = tailnet.Share(8467)
    inside, release = threading.Event(), threading.Event()
    real_start = tailnet.start

    def slow_start(port):
        inside.set()
        release.wait(5)
        return real_start(port)

    monkeypatch.setattr(tailnet, "start", slow_start)
    on = threading.Thread(target=share.save_and_apply, args=(True,))
    on.start()
    assert inside.wait(5)
    off = threading.Thread(target=share.save_and_apply, args=(False,))
    off.start()
    time.sleep(0.3)
    assert load_config().tailnet is True  # the "off" has not saved yet: it waits for the lock
    release.set()
    on.join(5)
    off.join(5)
    assert load_config().tailnet is False and share.status.active is False
    assert fake.config == OTHER


def test_a_failed_save_applies_nothing(client, fake, monkeypatch):
    from anyscribe.core import config_set

    monkeypatch.setattr(
        config_set, "set_value", lambda k, v: config_set.SetOutcome(False, error="disk full")
    )
    r = client.put("/api/tailnet", json={"enabled": True})
    assert r.status_code == 500 and r.json()["detail"] == "disk full"
    assert fake.calls == []


def test_a_share_removed_outside_anyscribe_reads_as_failed(client, fake):
    """C4: GET re-checks a live share; a rule removed by hand is not shown as live."""
    assert client.put("/api/tailnet", json={"enabled": True}).json()["active"] is True
    fake.config["TCP"].pop("8467")
    fake.config["Web"].pop(f"{HOST}:8467")
    data = client.get("/api/tailnet").json()
    assert data["active"] is False and data["url"] is None
    assert data["reason"] == (
        "Tailscale no longer has the share (removed outside anyscribe, or cleared when "
        "Tailscale signed out)."
    )
    assert tailnet._owned_ports() == set()


@pytest.mark.parametrize("cause", ["Stopped", "NeedsLogin", "status fails", "config unreadable"])
def test_a_live_share_whose_tailscale_is_down_reads_as_failed(client, fake, cause):
    """R2-C5: Tailscale stopped or signed out while shared: no dead link, the rule kept owned."""
    assert client.put("/api/tailnet", json={"enabled": True}).json()["active"] is True
    if cause == "status fails":
        fake.status_rc = 1
    elif cause == "config unreadable":
        fake.serve_status_rc = 1
    else:
        fake.backend = cause
    data = client.get("/api/tailnet").json()
    assert data["active"] is False and data["url"] is None and data["enabled"] is True
    assert data["held"] is True  # R4-F1: still held, so the card never says "only on this computer"
    if cause in ("Stopped", "NeedsLogin"):  # a definite answer: nothing can reach it
        assert data["reason"] == (
            "Tailscale says it is stopped or signed out on this computer, so other devices "
            "can't reach the link right now."
        )
        # R3-C1: it heals by itself once Tailscale is back, so no switch flip is asked for.
        assert data["fix"] == (
            "Open Tailscale and sign in (or run: tailscale up); the link comes back by itself."
        )
    else:  # no answer: it may well still work
        assert data["reason"] == (
            "anyscribe couldn't get an answer from Tailscale, so it can't confirm the link "
            "works. Other devices may still be able to open it."
        )
        assert data["fix"] == "It checks again when you come back to this page."
    assert data["card_fix"] is None
    assert client.app.state.tailnet.owned and tailnet._owned_ports() == {8467}
    # Tailscale is back: switching off removes our rule.
    fake.backend, fake.status_rc, fake.serve_status_rc = "Running", 0, 0
    client.put("/api/tailnet", json={"enabled": False})
    assert fake.config == OTHER


@pytest.mark.parametrize("meanwhile", ["switched off", "off and on again", "closed"])
def test_a_refresh_result_read_before_a_change_is_dropped(fake, monkeypatch, meanwhile):
    """R3-C1: refresh reads Tailscale outside the lock; a toggle or close() that lands during
    the read wins, so a stale answer never revives a released link or drops a new share."""
    share = tailnet.Share(8467)
    share.apply(True)
    url = share.held
    real = tailnet._serve_config

    def change_during_the_read(cli, timeout=tailnet.TIMEOUT):
        monkeypatch.setattr(tailnet, "_serve_config", real)  # only the refresh's own read
        if meanwhile == "switched off":
            stale = real(cli)  # still shows our rule
            share.apply(False)
        elif meanwhile == "closed":
            stale = real(cli)
            share.close()
        else:
            share.apply(False)
            stale = real(cli)  # shows the rule gone
            share.apply(True)
        return stale

    monkeypatch.setattr(tailnet, "_serve_config", change_during_the_read)
    share.refresh()
    if meanwhile == "off and on again":
        assert share.held == url and share.owned and share.status.active
        assert tailnet._owned_ports() == {8467}  # the new rule is still recorded, so removable
        share.close()
        assert fake.config == OTHER
    else:
        assert share.held is None and share.status == tailnet.Status()
        assert fake.config == OTHER


def test_no_tailscale_command_starts_after_switch_off(fake, monkeypatch):
    """R4-C2: switched off while refresh's first read runs: that read finishes and is dropped,
    and no further Tailscale command starts once the switch-off has returned."""
    share = tailnet.Share(8467)
    share.apply(True)
    real = tailnet._status_json
    after_off = {}

    def switch_off_during_the_read(cli, timeout=tailnet.TIMEOUT):
        out = real(cli, timeout)  # a read already running finishes...
        share.apply(False)  # ...while the switch-off lands
        after_off["mark"] = len(fake.calls)
        return out

    monkeypatch.setattr(tailnet, "_status_json", switch_off_during_the_read)
    share.refresh()
    assert fake.calls[after_off["mark"] :] == []
    assert share.held is None and share.status == tailnet.Status()
    assert fake.config == OTHER


def test_get_with_an_unreadable_config_shows_the_live_state(client, fake):
    """C5 leftover: a broken config.yaml gives saved None, not a 500; the live share still shows."""
    assert client.put("/api/tailnet", json={"enabled": True}).json()["active"] is True
    CONFIG_FILE.write_text("tailnet: [\n")
    r = client.get("/api/tailnet")
    assert r.status_code == 200
    data = r.json()
    assert data["saved"] is None and data["active"] is True
    assert data["url"] == f"https://{HOST}:8467/"


def test_get_with_sharing_off_never_calls_tailscale(client, fake):
    client.get("/api/tailnet")
    assert fake.calls == []


def test_shutdown_removes_our_rule_before_the_server_stops(client, fake):
    """C10: /api/shutdown unshares first, then asks uvicorn to exit."""
    seen = []

    class Server:
        def __setattr__(self, name, value):
            seen.append((name, copy.deepcopy(fake.config)))
            object.__setattr__(self, name, value)

    client.app.state.server = Server()
    client.put("/api/tailnet", json={"enabled": True})
    assert client.post("/api/shutdown").json()["ok"] is True
    assert seen == [("should_exit", OTHER)]  # the rule was already gone when exit was asked
    assert off_calls(fake) == [["serve", "--https=8467", "off"]]


def test_shutdown_exits_even_if_close_raises(client, fake, monkeypatch):
    """R4-C1: should_exit is set in a finally, so nothing in close() can keep the server up."""

    class Server:
        should_exit = False

    def broken_close():
        raise RuntimeError("boom")

    client.app.state.server = Server()
    monkeypatch.setattr(client.app.state.tailnet, "close", broken_close)
    with pytest.raises(RuntimeError):
        client.post("/api/shutdown")
    assert client.app.state.server.should_exit is True


# ── Host check (C8): DNS rebinding cannot reach the API ──────


@pytest.fixture
def served_app(fake, lifecycle, config_restored):
    """The app exactly as run() serves it (with its middleware), sharing off."""
    from anyscribe.core.config_set import set_value
    from anyscribe.web.app import run

    assert set_value("tailnet", "off").ok
    run(port=8467, open_browser=False)
    return lifecycle["app"]


@pytest.mark.parametrize("host", ["127.0.0.1:8467", "localhost:8467", "[::1]:8467", "localhost"])
def test_local_hosts_are_answered(served_app, host):
    r = TestClient(served_app, base_url=f"http://{host}").get("/api/tailnet")
    assert r.status_code == 200 and r.json()["enabled"] is False


def test_a_foreign_host_gets_403_on_every_route(served_app, fake):
    c = TestClient(served_app, base_url="http://evil.example")
    for method, path in [("get", "/api/tailnet"), ("get", "/"), ("put", "/api/tailnet")]:
        r = c.request(method.upper(), path, json={"enabled": True} if method == "put" else None)
        assert r.status_code == 403 and "only answers" in r.text, (method, path)
    assert fake.calls == []  # the rebinding PUT never reached the toggle


def test_a_foreign_host_cannot_open_the_progress_websocket(served_app):
    from starlette.websockets import WebSocketDisconnect

    # TestClient's websocket ignores base_url for Host, so set it explicitly.
    client = TestClient(served_app)
    with pytest.raises(WebSocketDisconnect) as refused:
        with client.websocket_connect("/api/ws/jobs/x", headers={"host": "evil.example"}):
            pass
    assert refused.value.code == 1008
    good = {"host": "127.0.0.1:8467"}
    with client.websocket_connect("/api/ws/jobs/x", headers=good) as ws:  # accepted: route answers
        assert ws.receive_json()["message"] == "Job not found"
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
        assert closed.value.code == 4004  # the route's own close, not the Host check's 1008


GATE_HOSTS = [
    "127.0.0.1:8467",
    "localhost:8467",
    "[::1]:8467",
    f"{HOST}:8467",
    HOST,
    "other.tail9.ts.net:8467",
    f"{HOST}.evil.example",
    "evil.example",
]


def _gate_rows(app) -> dict[str, int]:
    return {h: TestClient(app, base_url=f"http://{h}").get("/").status_code for h in GATE_HOSTS}


def _assert_gate_matches_the_hold(app) -> tuple[bool, bool]:
    """The invariant (R3-C1): a non-local Host gets 200 if and only if a URL is held and its
    host is exactly that name. The display may read failed while held, but never shows a link
    that is not held. Returns (display active, tailnet name answered)."""
    claim = TestClient(app, base_url="http://127.0.0.1:8467").get("/api/tailnet").json()
    held = app.state.tailnet.held  # read after the GET: its refresh may release the hold
    held_name = held.split("/")[2].rpartition(":")[0] if held else None
    rows = _gate_rows(app)
    for host, code in rows.items():
        name = host.partition("]")[0] + "]" if host.startswith("[") else host.partition(":")[0]
        local = name in ("127.0.0.1", "localhost", "[::1]")
        assert code == (200 if local or name == held_name else 403), (host, code, claim, held)
    if claim["active"]:
        assert claim["url"] == held
    assert claim["held"] == (held is not None)  # R4-F1: the card's privacy line reads this
    return claim["active"], rows[f"{HOST}:8467"] == 200


@pytest.mark.parametrize(
    "setting,rule,tailnet_name_answered,event,after_event",
    [
        ("off", "none", False, None, None),
        ("off", "leftover", False, None, None),  # R2-C1: a hard-killed run's rule, still recorded
        ("off", "hand-made", False, None, None),  # R2-C1: the user's own `tailscale serve`
        ("off", "owned-live", True, None, None),  # `anyscribe ui --tailnet` with the setting off
        ("on", "none", True, None, None),
        ("on", "leftover", True, None, None),  # reused
        ("on", "hand-made", True, None, None),  # adopted, left in place
        ("on", "owned-live", True, None, None),
        # R3-C1: Tailscale down while held: the display reads failed, the name is still answered
        ("on", "none", True, "down", (False, True)),
        ("on", "hand-made", True, "down", (False, True)),
        # removed outside anyscribe while Tailscale is Running: the hold is released
        ("on", "none", True, "removed", (False, False)),
        ("on", "hand-made", True, "removed", (False, False)),
    ],
)
def test_the_gate_answers_a_non_local_name_only_while_a_share_is_held(
    fake,
    lifecycle,
    config_restored,
    setting,
    rule,
    tailnet_name_answered,
    event,
    after_event,
    monkeypatch,
):
    """R2-C1/C2/C3, R3-C1: setting x rule state x Host. Then switch off live: every non-local
    name is refused again, a hand-made rule included (it stays in Tailscale, anyscribe refuses
    it)."""
    from anyscribe.core.config_set import set_value
    from anyscribe.web.app import run

    assert set_value("tailnet", setting).ok
    if rule in ("leftover", "hand-made"):
        tcp, web = ours(8467)
        fake.config["TCP"]["8467"], fake.config["Web"][f"{HOST}:8467"] = tcp, web
    if rule == "leftover":
        tailnet.OWNED_FILE.write_text("[8467]")
    if rule == "owned-live":
        monkeypatch.setattr(tailnet, "run_override", True)
    seen = {}

    def during(app):
        seen["before"] = _assert_gate_matches_the_hold(app)
        if event == "down":
            fake.backend = "Starting"
        if event == "removed":
            fake.config["TCP"].pop("8467")
            fake.config["Web"].pop(f"{HOST}:8467")
        if event:
            seen["event"] = _assert_gate_matches_the_hold(app)
        local = TestClient(app, base_url="http://127.0.0.1:8467")
        assert local.put("/api/tailnet", json={"enabled": False}).status_code == 200
        seen["after"] = _assert_gate_matches_the_hold(app)

    lifecycle["during"] = during
    run(port=8467, open_browser=False)
    expected = {"before": (tailnet_name_answered,) * 2, "after": (False, False)}
    if event:
        expected["event"] = after_event
    assert seen == expected
    if setting == "off" and rule != "owned-live":
        assert fake.calls == []  # setting off: the gate needed no Tailscale call
    if rule == "hand-made" and event != "removed":
        assert tailnet.port_state(fake.config, 8467) == "ours"  # never removed


@pytest.mark.parametrize("rule", ["owned", "hand-made"])
@pytest.mark.parametrize("fault", ["timeout", "status exit 1", "serve status exit 1", "Starting"])
def test_one_bad_tailscale_read_never_costs_the_remote_device_its_share(
    fake, lifecycle, config_restored, rule, fault
):
    """R3-C1: one bad read during a GET from the tailnet name shows failed but keeps the share
    held; once the read is good again, the remote device's next GET (no local request in
    between) is answered and shows the same link live."""
    from anyscribe.core.config_set import set_value
    from anyscribe.web.app import run

    assert set_value("tailnet", "on").ok
    if rule == "hand-made":
        tcp, web = ours(8467)
        fake.config["TCP"]["8467"], fake.config["Web"][f"{HOST}:8467"] = tcp, web
    url = f"https://{HOST}:8467/"
    seen = {}

    def inject(on: bool) -> None:
        if fault == "timeout":
            fake.status_hangs = on
        elif fault == "status exit 1":
            fake.status_rc = 1 if on else 0
        elif fault == "serve status exit 1":
            fake.serve_status_rc = 1 if on else 0
        else:
            fake.backend = fault if on else "Running"

    def during(app):
        remote = TestClient(app, base_url=f"http://{HOST}:8467")
        assert remote.get("/api/tailnet").json()["url"] == url
        inject(True)
        fake.calls.clear()
        fake.timeouts.clear()
        bad = remote.get("/api/tailnet")
        assert bad.status_code == 200, bad.text
        assert bad.json()["active"] is False and bad.json()["enabled"] is True
        assert bad.json()["url"] is None  # no link shown while it may not work
        assert bad.json()["held"] is True  # R4-F1: so the card says it works for this device
        assert set(fake.timeouts) == {tailnet.REFRESH_TIMEOUT}  # a focus never waits 10 s
        inject(False)
        good = remote.get("/api/tailnet")
        assert good.status_code == 200, good.text
        data = good.json()
        assert data["active"] is True and data["url"] == url
        assert data["note"] == (None if rule == "owned" else tailnet.HANDMADE)
        seen["ok"] = True

    lifecycle["during"] = during
    run(port=8467, open_browser=False)
    assert seen == {"ok": True}
    if rule == "owned":
        assert fake.config == OTHER  # still ours, so the clean stop removed it
    else:
        assert off_calls(fake) == [] and tailnet.port_state(fake.config, 8467) == "ours"


def _unwritable(path, content):
    raise PermissionError(13, "Permission denied", str(path))


@pytest.mark.parametrize(
    "where,fault",
    [
        ("switch off", "record write fails"),
        ("switch off", "serve off exits 1"),
        ("removed outside", "record write fails"),  # refresh never runs `serve off`
        ("shutdown", "record write fails"),
        ("shutdown", "serve off exits 1"),
    ],
)
def test_access_is_revoked_first_even_when_cleanup_fails(
    fake, lifecycle, config_restored, monkeypatch, capsys, where, fault
):
    """R4-C1: every release path refuses the tailnet name before any disk write or Tailscale
    call. A failed record write or `serve off` is reported in plain words, never a 500, never
    leaves the name answered, /api/shutdown still exits, and the next close() retries."""
    from anyscribe.core.config_set import set_value
    from anyscribe.web.app import run

    assert set_value("tailnet", "on").ok
    real_write, real_stop = tailnet.atomic_write, tailnet.stop
    held_at_cleanup = []  # the hold, seen at the moment each cleanup step starts
    seen = {}

    def during(app):
        share = app.state.tailnet
        local = TestClient(app, base_url="http://127.0.0.1:8467")
        remote = TestClient(app, base_url=f"http://{HOST}:8467")
        assert remote.get("/").status_code == 200 and share.owned

        def write(path, content):
            held_at_cleanup.append(share.held)
            if fault == "record write fails":
                _unwritable(path, content)
            real_write(path, content)

        def stop(port):
            held_at_cleanup.append(share.held)
            return real_stop(port)

        monkeypatch.setattr(tailnet, "atomic_write", write)
        monkeypatch.setattr(tailnet, "stop", stop)
        fake.off_rc = 1 if fault == "serve off exits 1" else 0
        if where == "switch off":
            r = local.put("/api/tailnet", json={"enabled": False})
            assert r.status_code == 200, r.text
            error = (
                str(PermissionError(13, "Permission denied", str(tailnet.OWNED_FILE)))
                if fault == "record write fails"
                else "failed"  # the fake's stderr
            )
            assert r.json()["note"] == tailnet.CLEANUP_FAILED.format(error=error, port=8467)
        elif where == "removed outside":
            fake.config["TCP"].pop("8467")
            fake.config["Web"].pop(f"{HOST}:8467")
            r = local.get("/api/tailnet")
            assert r.status_code == 200, r.text
            assert r.json()["active"] is False and r.json()["url"] is None
        else:
            r = local.post("/api/shutdown")
            assert r.status_code == 200, r.text
            assert app.state.server.should_exit is True and share.closed
            assert "Other devices are refused now." in capsys.readouterr().out
        assert share.held is None
        assert remote.get("/").status_code == 403
        assert held_at_cleanup and set(held_at_cleanup) == {None}
        # The fault clears; the shutdown hook's close() retries the removal.
        monkeypatch.setattr(tailnet, "atomic_write", real_write)
        fake.off_rc = 0
        seen["ok"] = True

    lifecycle["during"] = during
    run(port=8467, open_browser=False)
    assert seen == {"ok": True}
    assert fake.config == OTHER
    # Refresh forgets ownership first, so a record it could not clear stays (start re-checks it).
    stale = where == "removed outside"
    assert tailnet._owned_ports() == ({8467} if stale else set())


def test_a_stale_record_that_cannot_be_cleared_never_breaks_a_start(fake, monkeypatch):
    """R4-C1: start() forgets a recorded rule that is gone; a failed write must not raise."""
    tailnet.OWNED_FILE.write_text("[8467]")
    fake.config["TCP"]["8467"] = {"HTTPS": True}  # someone else's rule on the port now
    fake.config["Web"][f"{HOST}:8467"] = {"Handlers": {"/": {"Proxy": "http://127.0.0.1:9"}}}
    monkeypatch.setattr(tailnet, "atomic_write", _unwritable)
    status = tailnet.start(8467)
    assert not status.active and "already shared on your tailnet by something else" in status.reason
    assert bg_calls(fake) == [] and off_calls(fake) == []


def _failure_cases(fake, monkeypatch):
    """Every failure whose CLI fix names a terminal step, with the switch beside it on the card."""
    monkeypatch.setattr(tailnet, "find_cli", lambda: None)
    yield tailnet.start(8467)  # not installed
    monkeypatch.setattr(tailnet, "find_cli", lambda: "/usr/bin/tailscale")
    fake.backend = "Stopped"
    yield tailnet.start(8467)  # not running
    fake.backend = "Running"
    yield tailnet._classify("Serve is not enabled. https://login.tailscale.com/f/serve?x=1", 8467)
    yield tailnet._classify("serve is not enabled on your tailnet", 8467)
    monkeypatch.setattr(tailnet, "_serve_config", lambda cli: None)
    yield tailnet.start(8467)  # serve status unreadable


def test_card_fix_says_flip_the_switch_where_the_cli_says_a_command(fake, monkeypatch):
    """F6: the card never tells the user to type a command its own switch does."""
    cases = list(_failure_cases(fake, monkeypatch))
    assert len(cases) == 5
    for status in cases:
        assert "anyscribe config set" in status.fix or "restart anyscribe ui" in status.fix
        assert "anyscribe config set" not in status.card_fix
        assert "restart anyscribe ui" not in status.card_fix
        assert "flip this switch" in status.card_fix
        assert status.to_dict()["card_fix"] == status.card_fix
