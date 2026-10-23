# Fix wave after review round 1 (both reviewers NOT YET)

Repo <repo>, branch feat/desktop-mode, from 24a5322.
Two reviewers (fit: F1–F7; correctness: C1–C10). The lead reproduced F1/C6 and F2 live
on this Mac and verified C4 with Sol's command (see "Lead evidence" below). Five findings
sit in one mechanism (process ownership by pidfile + port probe): F1/C6, C1, C2, C3, C5.
Fix the mechanism once, as designed below, instead of patching each symptom.

## A. Ownership redesign (fixes C1, C2, C3, C5, F1/C6, F4)

A1. **Single instance by OS lock, not pidfile.** The tray (`cli/tray_cmd.py::_run_tray`)
acquires a non-blocking exclusive lock on `APP_HOME / "tray.lock"` at startup and holds
the file handle for its whole lifetime: POSIX `fcntl.flock(fd, LOCK_EX | LOCK_NB)`,
Windows `msvcrt.locking(fd, LK_NBLCK, 1)`. Put it in `core/tray.py` as
`acquire_instance_lock() -> IO | None` (None = another tray holds it). The pidfile check
in `tray()` is replaced by the lock: if the lock is not acquired → print "An anyscribe
tray is already running." and exit 0 (same as today). `write_pidfile()` happens after the
lock. The lock covers the whole critical region (check + publish + lifetime), so two
simultaneous `desktop open` clicks can both spawn trays and exactly one survives.
Real test (not a fake): `test_instance_lock_excludes_second_process` spawns two
`sys.executable -c` children that each call `acquire_instance_lock()` against a tmp
`APP_HOME`, hold it 2 s, and print "got"/"busy"; assert exactly one "got" and one
"busy" (identity of the survivor: the first one's output line). Mutation: make the lock
non-exclusive (LOCK_SH) → both print "got" → the test fails; restore.
Per the house rule on mutual exclusion: test the actual launch command: one test runs
`[sys.executable, "-m", "anyscribe", "tray", "--port", <free port>]` twice with the
tray extra present? Not possible headless; instead test `anyscribe tray` with the lock
already held by the test process: it must exit 0 and print the already-running line
(no pystray import needed if you check the lock before importing pystray; do that).

A2. **Identity on the wire.** `web/routes/health.py` adds `"app": "anyscribe"` to the
health JSON. `core/desktop.py::health_is_anyscribe(port)` = HTTP 200 and
`body.get("app") == "anyscribe"` (keep `version` for display). Every path that attaches,
opens or stops must use it: `cli/tray_cmd.py::_start_server` attaches only when
`health_is_anyscribe(port)`; if the port is bound by something else, the tray does NOT
start a server, sets its status text to `Status: port {port} is used by another program`,
and logs one line; "Open UI" opens the browser only when health identifies anyscribe
(otherwise no-op + log). `tray._post_shutdown(port)` posts only when
`health_is_anyscribe(port)` (move `health_is_anyscribe` into `core/tray.py` so both
modules share it; keep a re-export in `desktop.py`). Tests: a fake server returning
`{"version": "1"}` without `app` must be treated as foreign (`test_health_identity_requires_app_field`,
using a real local HTTP server thread on a free port, not a stub); the existing
foreign-port test must exercise the real parser against that server.

A3. **Only signal what is ours.** `core/tray.py`: a new `pid_is_anyscribe(pid) -> bool`
(POSIX: `ps -o command= -p <pid>` contains "anyscribe"; Windows: PowerShell
`(Get-CimInstance Win32_Process -Filter "ProcessId=<pid>").CommandLine` contains
"anyscribe"; non-positive pid → False). `read_pidfile()` returns the pid only if alive
AND `pid_is_anyscribe`; `stop_tray` never signals a pid that fails it (it removes the
stale pidfile instead). Test `test_stale_pidfile_with_reused_pid_is_not_signalled`:
pidfile holds `os.getpid()` of a `sleep` child the test started (command line has no
"anyscribe") → `stop_tray` sends no signal and the child is still alive afterwards
(assert identity: the child's pid is alive, `proc.poll() is None`). Mutation: drop the
identity check → the child is killed → test fails.

A4. **Server pid is recorded and stopped.** The tray writes `APP_HOME / "server.pid"`
when it spawns the server (and removes it on teardown). `stop_tray` after the tray:
if `server.pid` names a live anyscribe pid, terminate it (SIGTERM, then SIGKILL after the
same timeout; on Windows `os.kill` = TerminateProcess), wait for the port. Test: fake
server pid file + `pid_is_anyscribe` True → kill sequence includes the server pid.
The uninstall copy becomes honest (C7, exact): `Stopped anyscribe. If a transcription was
running, it was interrupted: run it again (long jobs reuse the chunks they already
finished).` Apply the same meaning to `docs/user/getting-started.md` (~272),
`docs/user/commands.md`, and `src/anyscribe/skill/references/commands.md`.

A5. **Orphaned tray and restarts go through one helper** (F1/C6, F4).
`core/desktop.py`: `_start_tray(port)`: on darwin when `service.is_installed()`, run
`launchctl kickstart -k gui/<uid>/com.anyscribe.tray` (`subprocess.run`, `check=False`,
`capture_output=True`, timeout 15); if non-zero or not darwin/no login item,
`spawn_detached` the tray. `open_dashboard`: when a tray is alive (lock held / pidfile)
but `port_responding(port)` is False after `ORPHAN_GRACE = 3.0` s (module constant), the
tray is orphaned: `tray.stop_tray(port)` then `_start_tray(port)`, then wait for health.
Lead evidence: `curl -X POST /api/shutdown; anyscribe desktop open` → exit 1 after 15 s.
Tests: `test_open_replaces_orphaned_tray` (order stop_tray → start, exactly one start,
browser opened); `test_open_uses_launchctl_kickstart_on_macos_with_login_item`;
`test_open_spawns_when_kickstart_fails`. Mutation: remove the orphan branch → StartFailed.

## B. Install path (F2, reproduced)
`install()`: `if old or tray.read_pidfile() is not None:` → `tray.stop_tray(old["port"] if
old else port)`, `service.uninstall_service()`, existing port wait. `service._launchctl`
uses `capture_output=True, text=True` and on non-zero exit prints to stderr exactly one
plain line: `launchctl {verb} did not succeed: {first line of stderr}` (never the raw
"Try running launchctl bootstrap as root" text). Lead evidence: with `desktop.json`
removed and the launchd tray running, install printed `Load failed: 5: Input/output
error`, kept the same tray pid, reported success. Tests:
`test_install_stops_running_tray_without_manifest` (order stop_tray → uninstall_service →
install_service); `test_launchctl_failure_prints_one_plain_line`. Mutation: drop the
pidfile clause → first test fails.

## C. Windows streams (C4, lead-verified)
Under `pythonw.exe`, `sys.stdout`/`sys.stderr` are `None`; uvicorn's logging setup calls
`sys.stdout.isatty()` and raises before the server starts, so a Windows desktop-mode
tray would never get a server. Fix in two places: (1) `web/app.py::run()` begins with
`_ensure_streams()`: if `sys.stdout is None or sys.stderr is None`, open
`tray.TRAY_LOG` (append, line-buffered, utf-8) and assign it to both; (2)
`cli/tray_cmd.py::_start_server` spawns the server with `stdin=DEVNULL`,
`stdout=stderr=` the tray log (append), and the tray itself does the same `_ensure_streams()`
at the top of `tray()`. Tests: `test_ensure_streams_replaces_none` (monkeypatch
`sys.stdout = None`, call, assert `sys.stdout is not None and sys.stdout.name ==
str(TRAY_LOG)`); `test_uvicorn_config_with_no_stdout` runs Sol's probe as a subprocess:
`python -c "import sys; sys.stdout=None; from anyscribe.web.app import _ensure_streams;
_ensure_streams(); import uvicorn; uvicorn.Config('anyscribe.web.app:create_app', factory=True)"`
with `ANYSCRIBE_HOME`/tmp log so nothing real is written → exit 0.

## D. Status semantics (C8)
`status()["healthy"]` = installation intact (files + recorded Python present) AND
`server_running` (health identifies anyscribe on the port). New `reason` when intact but
not running: `Installed but not running. Click the anyscribe app or run: anyscribe desktop
open`. Keep `installed` as is. Update tests (`test_status_*`), `docs/user/commands.md`
(~906) and the skill reference: "`healthy` is true only when the app is installed and
its dashboard answers".

## E. Docs and copy (F3, F6, C9, C10)
- F3 `docs/user/getting-started.md` Step 2 Option A: insert at top: "**Used the one-line
  installer?** The dashboard is already open in your browser with the setup wizard; skip
  the command below and go straight to step 1. Run `anyscribe ui` only in CLI mode
  (installer with `--no-desktop`, or plain pip)." Closing line (~110): "Close the tab when
  you're finished. In CLI mode, stop the server with Ctrl+C in the terminal or
  **Shutdown** in the sidebar; in desktop mode leave it running (Quit from the tray icon
  stops it)." The "way back in" paragraph (~282-284) becomes true after A5: after
  Shutdown or a reboot, clicking the app brings it back.
- F6: human-mode install output prints `Starts at login: yes` (path stays in `--json`);
  `desktop` group help: "app icon, start at login, tray icon"; Settings caption →
  "Starts anyscribe in the background when you log in." then `cd ui && npm ci && npm run
  lint && npm run build`, commit `web/static`.
- C9 exact `--no-launch` help/docs/skill text: "Do not open the dashboard now. On macOS,
  registering the login item still starts the tray; on Windows and Linux this also skips
  starting it now." (desktop_cmd.py help, SKILL.md row, docs/user/commands.md, skill
  references/commands.md).
- C10 exact wording for CHANGELOG (~24), troubleshooting (~597), journal (~4): "The
  launcher is generated locally and needs no separately signed app download. It avoided
  Gatekeeper prompts in our Mac test; Windows click-through remains unverified."
- F7 `install.sh`: on Linux with both `DISPLAY` and `WAYLAND_DISPLAY` empty, skip desktop
  mode with `Desktop mode skipped: no graphical session detected. On a desktop, run:
  anyscribe desktop install`; test via `run_installer_dry` or a static check.
- F5 declined: the plist keeps a copy of the installing shell's PATH (documented).

## Gates and process
`.venv/bin/python -m pytest -q`, `ruff check src tests scripts`, `scripts/build-docs.py`,
`scripts/check-docs.py`, `bash -n install.sh`. Commit per section (A, B, C, D, E) with
trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Every new guard is
mutation-tested; the report pastes each failing tail. Do not run `desktop
install/uninstall/open` or `anyscribe tray` against the real `~/.anyscribe` (a live install
is running; the lead re-runs the live reproductions afterwards); tests use tmp homes.
Report to `.superpowers/sdd/2026-10-22-desktop-mode/review-fix-r1-report.md`.
If any item here is wrong for a reason you can show, say so instead of building it.
