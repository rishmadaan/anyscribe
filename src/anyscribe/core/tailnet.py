"""Optional sharing of the web UI on the user's tailnet, through ``tailscale serve``.

The server always binds 127.0.0.1. When sharing is on, Tailscale proxies
``https://<machine>.<tailnet>.ts.net:<port>/`` to it: reachable from the user's
own Tailscale devices only, never the public internet (no Funnel). The CLI,
the tray/desktop server and the web toggle all go through ``Share`` so they
cannot disagree. With sharing off, nothing here starts a Tailscale command (a read already
running at switch-off finishes, at most 3 s, and is discarded).
"""

from __future__ import annotations

import contextlib
import json
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from anyscribe.config.paths import TAILNET_OWNED as OWNED_FILE
from anyscribe.core.fileutil import atomic_write

# Tailscale's CLI answers in well under a second; a wedged daemon, or `serve`
# waiting for the admin to enable HTTPS, would otherwise block the server start.
TIMEOUT = 10
# A page focus re-reads Tailscale; it must never keep the page (or close()) waiting long.
REFRESH_TIMEOUT = 3
MAC_APP_CLI = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"

# One-run override set by `anyscribe ui --tailnet / --local-only`; None follows the setting.
run_override: bool | None = None

HANDMADE = "A share you set up yourself; anyscribe will leave it in place."
# Past tense, no backticks: with sharing off anyscribe no longer looks, and the card shows plain text.
LEFT_IN_PLACE = (
    "anyscribe left your own Tailscale rule on port {port} in place and now refuses it. "
    "To remove it: tailscale serve --https={port} off"
)
NO_LOGIN = "no login: anyone on your tailnet can use it"
# BackendStates that definitely mean no tailnet traffic reaches this computer.
STOPPED = ("Stopped", "NeedsLogin", "NeedsMachineAuth")
CLEANUP_FAILED = (
    "Other devices are refused now. anyscribe couldn't remove its Tailscale rule ({error}); "
    "it retries on stop, or run: tailscale serve --https={port} off"
)


@dataclass
class Status:
    enabled: bool = False  # sharing is wanted for this server
    active: bool = False  # the serve rule is live and the link works
    url: str | None = None
    reason: str | None = None
    fix: str | None = None  # terminal wording, printed by the CLI
    card_fix: str | None = None  # the Settings card's wording, when it differs (it has a switch)
    note: str | None = None  # e.g. the link is a share the user made by hand
    owned: bool = False  # anyscribe created this rule (recorded), so it may remove it

    def to_dict(self) -> dict:
        data = asdict(self)
        del data["owned"]
        return data


def find_cli() -> str | None:
    """Path to the tailscale CLI, or None when Tailscale is not installed."""
    # which() also finds tailscale.exe on Windows (PATHEXT).
    found = shutil.which("tailscale")
    if found:
        return found
    if sys.platform == "darwin" and Path(MAC_APP_CLI).is_file():
        return MAC_APP_CLI
    return None


def _text(data) -> str:
    if isinstance(data, bytes):
        return data.decode(errors="replace")
    return data or ""


def _run(cli: str, *args: str, timeout: float = TIMEOUT) -> tuple[int, str, str]:
    """(exit code, stdout, stderr). A timeout or launch failure is code -1 with what was printed."""
    try:
        r = subprocess.run([cli, *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:  # partial output arrives as bytes on POSIX
        return -1, _text(e.stdout), _text(e.stderr)
    except OSError as e:
        return -1, "", str(e)
    return r.returncode, r.stdout or "", r.stderr or ""


def _target(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def _serve_config(cli: str, timeout: float = TIMEOUT) -> dict | None:
    """The current serve config, or None when it cannot be read (then touch nothing)."""
    code, out, _ = _run(cli, "serve", "status", "--json", timeout=timeout)
    if code != 0:
        return None
    if not out.strip():
        return {}
    try:
        data = json.loads(out)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _status_json(cli: str, timeout: float = TIMEOUT) -> dict:
    """`tailscale status --json`, or {} when it fails or is unreadable."""
    code, out, _ = _run(cli, "status", "--json", timeout=timeout)
    try:
        data = json.loads(out) if code == 0 else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _owned_ports() -> set[int]:
    """Ports whose serve rule anyscribe created. Unreadable = none (then nothing is ever removed)."""
    try:
        return {int(p) for p in json.loads(OWNED_FILE.read_text())}
    except (OSError, ValueError, TypeError):
        return set()


def _record(port: int, owned: bool) -> None:
    # shortcut: read-modify-write without a cross-process lock; two servers toggling at the
    # same instant can drop an entry, which only leaves a rule in place (never removes one).
    ports = _owned_ports()
    if (port in ports) == owned:
        return
    ports = ports | {port} if owned else ports - {port}
    atomic_write(OWNED_FILE, json.dumps(sorted(ports)))


def _on_port(mapping: dict | None, port: int) -> list:
    """Values of a serve-config map keyed "host:port" that are on ``port``."""
    return [v for k, v in (mapping or {}).items() if k.rpartition(":")[2] == str(port)]


def port_state(config: dict, port: int) -> str:
    """ "free", "ours" (exactly anyscribe's proxy, HTTPS, no Funnel) or "taken"."""
    tcp = (config.get("TCP") or {}).get(str(port))
    handlers: dict = {}
    for web in _on_port(config.get("Web"), port):
        handlers.update((web or {}).get("Handlers") or {})
    funnel = any(_on_port(config.get("AllowFunnel"), port))
    if not tcp and not handlers and not funnel:
        return "free"
    ours = handlers == {"/": {"Proxy": _target(port)}} and tcp == {"HTTPS": True}
    return "ours" if ours and not funnel else "taken"


def _failed(reason: str, fix: str) -> Status:
    # The card sits beside the switch: flipping it replaces the terminal steps.
    card = fix.replace(
        ", or turn sharing off: anyscribe config set tailnet off", ", or flip this switch off."
    ).replace("restart anyscribe ui", "flip this switch off and on")
    return Status(enabled=True, reason=reason, fix=fix, card_fix=card if card != fix else None)


def _classify(output: str, port: int) -> Status:
    """Turn a failed `tailscale serve` into a plain reason and fix."""
    low = output.lower()
    if "access denied" in low or "permission denied" in low or "--operator" in low:
        fix = (
            "Run once: sudo tailscale set --operator=$USER"
            if sys.platform.startswith("linux")
            else "Run anyscribe as the user who is signed in to Tailscale."
        )
        return _failed("Tailscale won't let your user change its sharing settings.", fix)
    url = re.search(r"https://login\.tailscale\.com/\S+", output)
    if url or "not enabled" in low:
        fix = (
            f"Enable it once at {url.group(0)} then restart anyscribe ui."
            if url
            else "Turn on HTTPS certificates in the Tailscale admin console (DNS page), "
            "then restart anyscribe ui."
        )
        return _failed("HTTPS sharing (Serve) isn't enabled on your tailnet yet.", fix)
    first = next((ln.strip() for ln in output.splitlines() if ln.strip()), "no reason given")
    return _failed(
        f"Tailscale couldn't share the page: {first}",
        f"Try it by hand to see why: tailscale serve --bg --https={port} {_target(port)}",
    )


def start(port: int) -> Status:
    """Share 127.0.0.1:<port> on the tailnet at the same port. Never overwrites another rule."""
    cli = find_cli()
    if not cli:
        return _failed(
            "Tailscale isn't installed on this computer.",
            "Install it from https://tailscale.com/download, or turn sharing off: "
            "anyscribe config set tailnet off",
        )
    status = _status_json(cli)
    dns = ((status.get("Self") or {}).get("DNSName") or "").rstrip(".")
    if status.get("BackendState") != "Running" or not dns:
        return _failed(
            "Tailscale is installed but not running or not signed in.",
            "Open Tailscale and sign in (or run: tailscale up), then restart anyscribe ui.",
        )
    config = _serve_config(cli)
    if config is None:
        return _failed(
            "Couldn't read Tailscale's sharing settings, so anyscribe changed nothing.",
            "Check that `tailscale serve status` works, then restart anyscribe ui.",
        )
    state = port_state(config, port)
    recorded = port in _owned_ports()
    if recorded and state != "ours":
        with contextlib.suppress(OSError):  # best effort: a stale record is re-checked here
            _record(port, False)  # our old rule is gone (or replaced): forget it
        recorded = False
    if state == "taken":
        return _failed(
            f"Port {port} is already shared on your tailnet by something else; "
            "anyscribe left it alone.",
            "Start on another port: anyscribe ui --port <number>",
        )
    if state == "free":
        code, out, err = _run(cli, "serve", "--bg", f"--https={port}", _target(port))
        if code != 0:
            return _classify(out + "\n" + err, port)
        config = _serve_config(cli)
        if config is None or port_state(config, port) != "ours":
            return _failed(
                "Tailscale accepted the request but the share isn't showing up.",
                f"Check with: tailscale serve status (port {port}).",
            )
        try:
            _record(port, True)  # only now: our own serve succeeded and reads back as ours
        except OSError as e:
            # Unrecorded, the rule would never be removed: undo it rather than leave it live.
            folder = OWNED_FILE.parent
            if _run(cli, "serve", f"--https={port}", "off")[0] != 0:
                return _failed(
                    f"anyscribe couldn't note the share it made ({e}) and couldn't remove it.",
                    f"Remove it: tailscale serve --https={port} off, then check that "
                    f"{folder} is writable.",
                )
            return _failed(
                f"anyscribe couldn't note the share it made ({e}), so it removed it again.",
                f"Check that {folder} is writable, then restart anyscribe ui.",
            )
        recorded = True
    # A matching rule nobody recorded was made by hand: use it for the link, never remove it.
    return Status(
        enabled=True,
        active=True,
        url=f"https://{dns}:{port}/",
        note=None if recorded else HANDMADE,
        owned=recorded,
    )


def stop(port: int) -> str | None:
    """Remove the serve rule for ``port`` only if anyscribe recorded it AND it is still ours.

    None when done (or nothing to do); otherwise what went wrong, with the record kept so a
    later stop retries. Writing the record may raise OSError.
    """
    cli = find_cli()
    if not cli or port not in _owned_ports():
        return None
    config = _serve_config(cli)
    if config is None:
        return "couldn't read its sharing settings"
    if port_state(config, port) == "ours":
        code, out, err = _run(cli, "serve", f"--https={port}", "off")
        if code != 0:
            return next(iter((err or out).strip().splitlines()), f"exit code {code}")
    _record(port, False)
    return None


def saved_setting() -> bool:
    """The saved `tailnet` setting as a real bool (a hand-written "false" is off). May raise."""
    from anyscribe.config.settings import load_config
    from anyscribe.core.config_set import as_bool

    return as_bool(load_config().tailnet)


def describe(status: Status) -> str | None:
    """The one line the CLI prints; None when sharing is off."""
    if status.active:
        line = f"Shared on your tailnet → {status.url} ({NO_LOGIN})"
        return f"{line}. {status.note}" if status.note else line
    if status.enabled:
        return f"Tailnet sharing is on but not working: {status.reason} Fix: {status.fix}"
    return None


class Share:
    """The live sharing state of one running web server."""

    def __init__(self, port: int | None = None) -> None:
        self.port = port
        self.status = Status()  # what the CLI and the UI show
        # The link this server holds: set when start() succeeds (our rule or an adopted
        # hand-made one), cleared on switch-off, "removed outside anyscribe" and close. The
        # Host gate answers its exact name; `status` may show failed meanwhile (Tailscale down).
        self.held: str | None = None
        self._hold = 0  # bumped whenever `held` changes, so a stale refresh result is dropped
        self.owned = False  # this process holds a live rule anyscribe created; kept apart
        # from `status` so a failed repeat "on" cannot make shutdown forget the rule
        self.closed = False  # the server is stopping: never share again
        self._lock = threading.RLock()

    def apply(self, wanted: bool) -> Status:
        """Start or stop sharing now. Turning off touches Tailscale only if we own a rule."""
        with self._lock:
            if self.closed:
                return self.status
            if wanted and self.port is None:
                self.status = _failed(
                    "This server's port is unknown.", "Start it with: anyscribe ui"
                )
            elif wanted:
                self.status = start(self.port)
                self.owned = self.owned or self.status.owned
                if self.status.active:  # a failed repeat "on" keeps the hold; refresh settles it
                    self._set_held(self.status.url)
            else:
                # An adopted hand-made share stays in Tailscale: say so.
                left = self.held is not None and not self.owned
                error = self._release()
                if error:
                    note = CLEANUP_FAILED.format(error=error, port=self.port)
                else:
                    note = LEFT_IN_PLACE.format(port=self.port) if left else None
                self.status = Status(note=note)
            return self.status

    def refresh(self) -> Status:
        """While a link is held, re-read Tailscale so the display tells the truth.

        Not Running, or a read that fails or times out: show failed and keep holding (a passing
        hiccup must not cost a working share). Running and the rule is ours: show it live again.
        Running and the rule is gone: "removed outside anyscribe", and the hold is released.
        Nothing held (including sharing off) = no Tailscale call. Switched off during a read:
        that read finishes (at most 3 s) and is discarded, and none starts after it.
        """
        with self._lock:
            held, hold, port = self.held, self._hold, self.port
        if held is None:
            return self.status
        # Read outside the lock, so a page focus never makes a toggle or close() wait.
        cli = find_cli()
        backend = _status_json(cli, REFRESH_TIMEOUT).get("BackendState") if cli else None
        with self._lock:
            if self._hold != hold:
                return self.status  # released during the first read: start no second command
        config = _serve_config(cli, REFRESH_TIMEOUT) if backend == "Running" else None
        with self._lock:
            if self._hold != hold:
                return self.status  # switched off, re-shared or closed while we read
            # Either way keep the hold and self.owned: our rule may still be there.
            if config is None and backend in STOPPED:
                self.status = _failed(
                    "Tailscale says it is stopped or signed out on this computer, so other "
                    "devices can't reach the link right now.",
                    "Open Tailscale and sign in (or run: tailscale up); "
                    "the link comes back by itself.",
                )
            elif config is None:  # a failed or slow read, or Starting: no answer either way
                self.status = _failed(
                    "anyscribe couldn't get an answer from Tailscale, so it can't confirm the "
                    "link works. Other devices may still be able to open it.",
                    "It checks again when you come back to this page.",
                )
            elif port_state(config, port) == "ours":
                if not self.status.active:
                    self.status = Status(
                        enabled=True,
                        active=True,
                        url=held,
                        note=None if self.owned else HANDMADE,
                        owned=self.owned,
                    )
            else:
                owned, self.owned = self.owned, False
                self._set_held(None)  # revoke first: the record write below may fail
                self.status = _failed(
                    "Tailscale no longer has the share (removed outside anyscribe, or cleared "
                    "when Tailscale signed out).",
                    "Turn sharing off and on again to share it again.",
                )
                if owned:
                    with contextlib.suppress(OSError):  # a stale record: start() re-checks it
                        _record(port, False)
            return self.status

    def _set_held(self, url: str | None) -> None:
        self.held = url
        self._hold += 1

    def save_and_apply(self, wanted: bool):
        """Save the setting and apply it under one lock, so saved and live cannot drift apart.

        Returns config_set's SetOutcome; nothing is applied when the save failed.
        """
        from anyscribe.core.config_set import set_value

        with self._lock:
            outcome = set_value("tailnet", wanted)
            if outcome.ok:
                self.apply(wanted)
            return outcome

    def _release(self) -> str | None:
        """Revoke first (the gate refuses the tailnet name at once), then remove our rule.

        Cleanup is best effort and never raises: the error is returned, and `owned` stays
        True so close() retries. `stop` stays under the lock: outside it, a start/stop on the
        same port could race.
        """
        self._set_held(None)
        if not self.owned:
            return None
        try:
            error = stop(self.port)
        except Exception as e:  # e.g. the record file can't be written
            error = str(e) or type(e).__name__
        if error is None:
            self.owned = False
        return error

    def close(self) -> str | None:
        """The server is stopping: refuse any later share, then remove our own rule.

        Never raises; returns the cleanup error, if any (a later close() retries).
        """
        with self._lock:
            self.closed = True
            error = self._release()
            self.status = Status()
            return error
