---
type: feature
tags: [web-ui, tailscale, networking, settings, security]
tldr: "Optional tailnet sharing for the web UI: a `tailnet` setting (default off) plus one-run `ui --tailnet` / `--local-only`. The server still binds 127.0.0.1; core/tailnet.py asks `tailscale serve --bg --https=<port>` to proxy it, never overwrites another serve rule, removes only its own rule on stop, never uses Funnel, and with sharing off never calls Tailscale. Settings gets a live switch; the sidebar shows the link with a copy button while shared."
---

# Tailnet sharing for the web UI

## The ask

The owner ran `scribe ui` on a Linux box and wanted it on his Mac. It had to
be exposed by hand with `tailscale serve`, because anyscribe binds 127.0.0.1
with no option. He asked for a toggle: on, `anyscribe ui` is reachable on his
tailnet; off, local only. anyscribe is a public tool and most users have no
Tailscale, so the setting is off by default and switched on once per machine.

## Decision: proxy through `tailscale serve`, never widen the bind

Options considered:

| Option | Why not / why |
|---|---|
| Bind `0.0.0.0` | Exposes a no-auth dashboard to every network the laptop joins (cafe Wi-Fi). Rejected. |
| Bind the Tailscale IP | Plain HTTP, the IP changes per machine, and the server has to know about Tailscale's interface. Rejected. |
| Tailscale Funnel | Public internet. Rejected outright. |
| **`tailscale serve --https=<port> http://127.0.0.1:<port>`** | Server keeps its 127.0.0.1 bind; Tailscale terminates HTTPS with a real cert and only tailnet devices reach it. Chosen. |

The HTTPS port equals the local port, so the link is predictable
(`https://<machine>.<tailnet>.ts.net:<port>/`) and the port roll-forward in
`anyscribe ui` carries over: the chosen port is the shared one.

## How it fits

- `core/tailnet.py` holds everything: `find_cli()` (PATH, plus the macOS app
  bundle path), `start(port)`, `stop(port)`, `port_state(config, port)` and a
  small `Share` object with a lock that holds the live state for one server.
- `web.app.run()` sets `Share.port` and, only if sharing is wanted, registers a
  startup handler that applies it and prints one line. A shutdown handler
  always runs `Share.apply(False)`, which is a no-op unless the rule is live.
  Uvicorn runs shutdown handlers for `/api/shutdown`, SIGINT and SIGTERM before
  it re-raises the signal, so all three clean up.
- The tray and desktop mode start the server as `python -m anyscribe ui`, so
  they get the behaviour with no code of their own.
- `GET/PUT /api/tailnet` mirror `/api/autostart` (a dedicated endpoint
  returning the live state in one round trip). `PUT /api/config` also accepts
  `tailnet` and applies it through the same `Share`, so the two writes cannot
  disagree. CLI `config set` and MCP `set_config` get the key for free through
  `core/config_set.py`.
- The one-run flags are a module-level `run_override` that `ui` sets before
  calling `run()`; it is never written to config. (Passing it as a `run()`
  argument would have broken an existing test fixture that stubs `run` with a
  fixed signature.)

## Ownership rules (the parts that protect other people's setups)

- **Never overwrite.** Before adding the rule, anyscribe reads
  `tailscale serve status --json`. The port is "ours" only when its single
  handler is `/ → http://127.0.0.1:<port>` over HTTPS with no Funnel; "free"
  when nothing is on it; anything else is "taken" and anyscribe stops with a
  message suggesting `--port`. An unreadable serve config also stops it.
- **Remove only ours.** On stop it re-reads the config and runs
  `tailscale serve --https=<port> off` only if the port is still exactly ours.
- **Off means off.** With sharing off nothing calls Tailscale, including stale
  rule cleanup.
- **Never show a dead link.** After `serve --bg` succeeds, anyscribe re-reads
  the serve config and reports the link only if the rule is there.

## Failure messages

Each prints one line (`Tailnet sharing is on but not working: <reason> Fix:
<fix>`) and the server still starts locally: not installed; not running or
signed out (`status --json` fails or `BackendState` is not `Running`);
permission refused (Linux non-operator, fix `sudo tailscale set
--operator=$USER`); HTTPS/Serve not enabled (the CLI prints a
`login.tailscale.com` link and waits; anyscribe's 10 s timeout collects the
partial output and passes the link through); port taken by another rule.

## Known limits

- A hard kill (SIGKILL, power loss) skips the shutdown handler and leaves the
  rule, which answers "bad gateway". The next start with sharing on reuses it;
  with sharing off anyscribe never cleans it up. Documented in the user docs.
- (Fixed in review round 1: a failed repeat "on" no longer orphans the rule.)
- The dashboard has no login, so sharing hands every tailnet device full
  control. The Settings card, docs and the skill (Safety Rule 6) say so;
  auth is out of scope.

## Verification

`tests/test_tailnet.py` fakes the tailscale CLI with a real serve-config dict
and asserts on the exact argv issued and the exact rules left. The guards
(never overwrite, remove only ours, off means zero calls) were each
mutation-tested. Live on a Linux box with six other serve rules (one a Funnel):
link answered 200 from the box and from a Mac on the tailnet, the transcription
WebSocket upgraded (101) through the link, the rule was removed on SIGTERM,
SIGINT and `/api/shutdown`, the Settings switch toggled the rule live, and the
other rules were byte-identical before and after.

## Review round 1 fixes (same day)

An independent review (correctness and fit) upheld 15 findings. What changed:

- **Ownership is recorded, not inferred.** The first cut called any
  `https=N -> http://127.0.0.1:N` rule "ours" and removed it on stop, which
  would have deleted a rule the user made by hand (the exact command this
  feature grew out of) or another app's same-shape rule. Now anyscribe writes
  the port to `~/.anyscribe/tailnet-owned.json` only after its own
  `serve --bg` succeeded and reads back, and removes a rule only if it is
  recorded and still matches. A matching unrecorded rule is used for the link
  and left in place. `Share` tracks "this process owns a live rule" apart from
  the displayed status, so a failed repeat "on" cannot orphan the rule.
- **Share after the bind.** uvicorn runs startup handlers before it binds and
  shutdown handlers on a bind failure, so the old startup hook could share,
  then unshare a port a second server was serving. A thread now waits for
  `server.started` first; a failed bind never touches Tailscale.
- **No stale link.** `GET /api/tailnet` re-reads the serve config while live
  and reports "The share was removed outside anyscribe." if the rule is gone;
  the UI re-reads on window focus.
- **The gate follows the held share, not the display** (review round 3). Round
  2 made a live share drop to failed when Tailscale was down, and the Host gate
  keyed on that display, so one slow or failed Tailscale read refused the
  remote device until someone flipped the switch at the host. `Share.held` now
  holds the link from a successful `start()` until switch-off, "removed outside
  anyscribe" or close, and the gate answers its exact name. The re-check runs
  while held, outside the lock with a 3 s timeout: not Running or a failed read
  shows failed and keeps holding; Running with our rule shows it live again;
  only Running with the rule gone releases the hold. Answering the name during
  an outage costs nothing, because no tailnet request can arrive then.
- **Host check.** A pure ASGI middleware (HTTP and WebSocket) answers the
  local names always, and the exact tailnet name of this server's share only
  while that share is live; anything else gets 403, so a DNS-rebinding page
  cannot switch sharing on. An interim version allowed any `*.ts.net` name at
  all times, so a share made by hand kept working with the setting off. Round 2
  of review reverted it: with the setting off, a rule left behind by a hard
  kill (or made by hand) then exposed the no-login page while the card said
  "only this computer", and "Tailscale issues those names" does not stop a
  hostile DNS resolver from rebinding a `.ts.net` name. A hand-made share now
  works once the setting is on (anyscribe adopts it and leaves it in place).
  Deliberate change for every install, setting on or off: a dashboard reached
  through another proxy, tunnel or hostname (Caddy, ngrok, a hosts-file alias)
  is now refused; open it at 127.0.0.1 or use the tailnet setting.
- **No login, said everywhere:** the CLI's shared line, `config set tailnet
  on`, the `--tailnet` help and the card ("or stop it").
- Smaller: a broken `config.yaml` starts local-only with one line; a quoted
  `"false"` is off; save and apply share one lock and the card's note is worded
  from the data; `/api/shutdown` unshares before shutting down; the card says
  "flip this switch" where the CLI names a command; switching off from another
  device asks first; the card moved below the daily settings; the CLI prints
  "Asking Tailscale to share it..." before the wait.
