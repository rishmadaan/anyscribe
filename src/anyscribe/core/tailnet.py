"""Optional sharing of the web UI on the user's tailnet, through ``tailscale serve``.

The server always binds 127.0.0.1. When sharing is on, Tailscale proxies
``https://<machine>.<tailnet>.ts.net:<port>/`` to it: reachable from the user's
own Tailscale devices only, never the public internet (no Funnel). The CLI,
the tray/desktop server and the web toggle all go through ``Share`` so they
cannot disagree. With sharing off, nothing here calls Tailscale.
"""

from __future__ import annotations

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
MAC_APP_CLI = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"

# One-run override set by `anyscribe ui --tailnet / --local-only`; None follows the setting.
run_override: bool | None = None

HANDMADE = "A share you set up yourself; anyscribe will leave it in place."
NO_LOGIN = "no login: anyone on your tailnet can use it"


@dataclass
class Status:
    enabled: bool = False  # sharing is wanted for this server
    active: bool = False  # the serve rule is live and the link works
    url: str | None = None
    reason: str | None = None
    fix: str | None = None
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


def _run(cli: str, *args: str) -> tuple[int, str, str]:
    """(exit code, stdout, stderr). A timeout or launch failure is code -1 with what was printed."""
    try:
        r = subprocess.run([cli, *args], capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired as e:  # partial output arrives as bytes on POSIX
        return -1, _text(e.stdout), _text(e.stderr)
    except OSError as e:
        return -1, "", str(e)
    return r.returncode, r.stdout or "", r.stderr or ""


def _target(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def _serve_config(cli: str) -> dict | None:
    """The current serve config, or None when it cannot be read (then touch nothing)."""
    code, out, _ = _run(cli, "serve", "status", "--json")
    if code != 0:
        return None
    if not out.strip():
        return {}
    try:
        data = json.loads(out)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


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
    return Status(enabled=True, reason=reason, fix=fix)


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
    code, out, _ = _run(cli, "status", "--json")
    try:
        status = json.loads(out) if code == 0 else {}
    except ValueError:
        status = {}
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
        _record(port, True)  # only now: our own serve succeeded and reads back as ours
        recorded = True
    # A matching rule nobody recorded was made by hand: use it for the link, never remove it.
    return Status(
        enabled=True,
        active=True,
        url=f"https://{dns}:{port}/",
        note=None if recorded else HANDMADE,
        owned=recorded,
    )


def stop(port: int) -> None:
    """Remove the serve rule for ``port`` only if anyscribe recorded it AND it is still ours."""
    cli = find_cli()
    if not cli or port not in _owned_ports():
        return
    config = _serve_config(cli)
    if config is None:
        return  # can't see it: keep the record, a later clean stop retries
    if port_state(config, port) == "ours":
        code, _, _ = _run(cli, "serve", f"--https={port}", "off")
        if code != 0:
            return
    _record(port, False)


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
            else:
                self._release()
                self.status = Status()
            return self.status

    def _release(self) -> None:
        if self.owned:
            stop(self.port)
            self.owned = False

    def close(self) -> None:
        """The server is stopping: remove our own rule and refuse any later share."""
        with self._lock:
            self._release()
            self.closed = True
            self.status = Status()
