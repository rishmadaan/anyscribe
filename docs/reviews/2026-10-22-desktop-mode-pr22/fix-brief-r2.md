# Fix wave after review round 2 (correctness NOT YET; fit report pending at writing time)

Repo <repo>, branch feat/desktop-mode, from 273be39.
All round-1 mechanism fixes were confirmed real by the round-2 correctness reviewer; what
remains are edges of the new identity and race logic, plus a one-line Windows test
portability failure from CI. Apply all of the following.

## W. Windows CI (tests only, one line)
CI run 39808100206 windows-latest: 115 passed, 1 failed:
`tests/test_desktop.py::test_open_falls_back_to_stop_and_start_when_restart_fails[posix]`
raised `AttributeError: module 'signal' has no attribute 'SIGUSR1'` at the assertion
`kills == ([] if os_name == "nt" else [(4242, signal.SIGUSR1)])` because the expression
evaluates `signal.SIGUSR1` on Windows even in the posix-parametrised case. Fix: compute the
expected signal via `getattr(signal, "SIGUSR1", None)` (or build the expected list inside
`if os_name != "nt"`), and check that no other test or production path references
`signal.SIGUSR1` unguarded on Windows (grep; production code must reference it only inside
`os.name != "nt"` branches or via `getattr`).

## C1. Process identity is role-aware and alias-aware (blocker)
`core/tray.py::pid_is_anyscribe(pid)` currently accepts any command line containing
"anyscribe" (so `/Users/x/labs/projects/anyscribe/.venv/bin/python -c ...` passes, and a
transcription `anyscribe https://...` passes as a tray) and rejects the aliases
`scribe tray` / `ascli tray`. Replace with `pid_is_anyscribe(pid, role: str) -> bool`
where `role` is `"tray"` or `"ui"`, matching the command line against ONE regex:
`(?:-m\s+anyscribe|[\\/](?:anyscribe|scribe|ascli)(?:\.exe)?)\s+<role>\b` (role interpolated,
case-insensitive on Windows). `read_pidfile()` uses role "tray"; the server pid uses role
"ui"; `service.uninstall_service`'s "is a tray running" check uses `read_pidfile()` (so the
alias case now keeps the tray). Non-positive pids → False (keep). Tests (real children, assert
identity of survivors, not counts): an unrelated `sys.executable -c "import time; time.sleep(30)"`
child whose interpreter path contains "anyscribe" (run it from a tmp dir named
`anyscribe-x`, or pass a path with that substring) must NOT be recognised as a tray and
must survive `stop_tray`; a child whose argv is `[sys.executable, "-c", "import time; time.sleep(30)", "-m", "anyscribe", "https://x"]`
(wrong role) must not be recognised; a fake command line `.../bin/scribe tray --port 8457`
must be recognised (unit test of the regex with fixed strings for the alias, the module
form, and Windows `anyscribe.exe tray`). Mutation: drop the role token from the regex → the
wrong-role test fails; restore.

## C2. `desktop open --port N` must not stop the installed instance on another port (should-fix)
`core/desktop.py::open_dashboard`: before any signal or stop, if a tray is alive
(`read_pidfile()`), compare the requested port with the installed port (manifest
`port`, else the plist's `--port` argument via the existing `_kickstart` parsing, factored
into `installed_port() -> int | None`). If they differ → raise `PortMismatch(installed,
requested)` with the exact message: `Desktop mode is installed on port {installed}. To
change it, run: anyscribe desktop install --port {requested}`; the CLI maps it to exit 1.
Test `test_open_other_port_refuses_without_touching_running_instance` (manifest port 8457,
pidfile alive, `--port 9000` → the error, and neither `os.kill` nor `stop_tray` nor spawn
was called). Mutation: remove the check → test fails.

## C3. A losing duplicate tray is not a backend failure (should-fix)
`_await_health`: when the started process exits, return `"exited-ok"` if its returncode is 0
and `"exited"` otherwise. In `open_dashboard`, `"exited-ok"` means another tray won the lock:
wait for health again (`_await_health(None, port, timeout)`) and never spawn bare `ui`;
only a non-zero exit takes the `ui --no-open` fallback. Test
`test_open_waits_for_winning_tray_when_duplicate_exits_zero` (two opens simulated: the
spawned proc polls 0; health turns True later; assert no `ui` spawn and the URL is
returned) and keep the headless-Linux test (non-zero exit → `ui` fallback). Mutation: treat
exit 0 as failure → the new test fails.

## C4. Explicit foreign `app` always wins; legacy shape is typed (should-fix)
`core/tray.py::health_is_anyscribe`: if `"app" in body` → identity iff `body["app"] ==
"anyscribe"` (any other value → foreign, regardless of other keys); only when `app` is
absent apply the legacy rule: `isinstance(body.get("version"), str)` and
`isinstance(body.get("dependencies"), dict)`. Tests with the real local HTTP server:
`{"app":"another-program","version":"1","dependencies":{}}` → foreign;
`{"version":null,"dependencies":null}` → foreign; `{"ok":true,"version":"0.17.1","dependencies":{"ffmpeg":true}}`
→ anyscribe (keep). Docstring: legacy matching is a compatibility heuristic for pre-0.18
servers. Mutation: drop the explicit-app precedence → the first new test fails.

## C5. One lifecycle lock for start, restart and teardown; no spawn after Quit begins (should-fix)
`cli/tray_cmd.py`: `state["closing"] = False`; `_start_server`, the SIGUSR1/menu restart and
`_teardown` all run under the same `restart_lock`; `_teardown` sets `closing = True` first;
`_start_server` and the restart return immediately when `closing` is set. Test with
threads and a barrier: start a restart that has popped the old process and is paused (use
a `threading.Event` the fake Popen waits on), run `_teardown` concurrently, release; assert
no server process exists after teardown (identity: the fake Popen list is empty / the one
created was terminated). Mutation: remove the `closing` check → the test fails.

## C6. Wording (nits, exact text)
- Uninstall copy everywhere (CLI `desktop_cmd.py`, docs/user/commands.md, getting-started,
  skill reference): `Stopped anyscribe. If a transcription was running, run it again. Saved
  chunks may be reused; unfinished work may run again.`
- docs/user/commands.md (~944) example comment: `# Set up desktop mode without opening the
  dashboard now`.
- docs/building/architecture.md (~239): `The launcher is generated locally and needs no
  separately signed app download. It avoided Gatekeeper prompts in our Mac test; Windows
  click-through remains unverified.` Also its supervision paragraph (~62): the tray attaches
  only to a listener that identifies itself as anyscribe on /api/health; single instance by a
  lifetime OS lock on ~/.anyscribe/tray.lock (not the pidfile); and its install-order summary
  (~155): macOS writes the login item first and launchd starts the tray; Windows/Linux spawn
  first.
- Skill reference (`src/anyscribe/skill/references/commands.md`, the tray section): `Menu
  Quit performs teardown. On macOS and Linux, SIGTERM/SIGINT do too; on Windows, desktop
  uninstall separately terminates the recorded server.`
- Regenerate `landing/docs` where user docs changed.

## Gates and process
`.venv/bin/python -m pytest -q && ruff check src tests scripts`; `scripts/build-docs.py &&
scripts/check-docs.py` after docs. One commit per section (W, C1, C2, C3, C4, C5, C6),
trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Every new guard is
mutation-tested; paste each failing tail. Do not run `anyscribe tray`, `desktop
install/uninstall/open`, `launchctl` or send signals against the real `~/.anyscribe` (live
install running; the lead verifies afterwards). Report to
`.superpowers/sdd/2026-10-22-desktop-mode/review-fix-r2-report.md`. If any item is wrong
for a reason you can show, say so instead of building it.

## Additions from the round-2 fit reviewer (same wave)
- F10 (same defect as C2): also acceptable to implement as the CLI refusal in `open_cmd`
  with this exact message: `anyscribe is installed on port {installed}. Run \`anyscribe
  desktop open\` (no --port) to open it, or \`anyscribe desktop install --port {port}\` to
  move it.` Put the check in `core/desktop.py::open_dashboard` (so the launcher path is
  covered too) and use this wording for `PortMismatch`.
- F11 (should-fix, skill + user docs): the "already running" explanation must describe the
  OS lock, not the pidfile. Skill `references/troubleshooting.md` (~357): "A tray is already
  active: it holds the one-tray lock (`~/.anyscribe/tray.lock`) for as long as it runs, so a
  second `anyscribe tray` exits quietly with code 0. The OS releases the lock when that tray
  exits, however it exits, so there is no stale lock to clean up." Skill
  `references/commands.md` (~363): "If a tray is already running (it holds the lock on
  `~/.anyscribe/tray.lock`), a second `anyscribe tray` prints *already running* and exits 0
  rather than colliding." `docs/user/troubleshooting.md` (~523-525): "A tray is already
  active: it holds a lock file (`~/.anyscribe/tray.lock`) while it runs, so a second copy
  steps aside instead of colliding with the first."
- F13 (nit): `docs/user/configuration.md` inventory (~28 and the tree ~412-424) gains rows:
  "Tray lock | `~/.anyscribe/tray.lock` | Empty file the running tray holds a lock on, so
  only one tray runs; safe to leave in place"; "Server PID | `~/.anyscribe/server.pid` |
  Process ID of the dashboard server the tray started"; "Desktop app |
  `~/.anyscribe/desktop.json`, `~/.anyscribe/desktop/` | What `anyscribe desktop install`
  set up, and the rendered icons".
- F14 (test gap): add a sibling of `test_tray_restart_lock_is_idempotent` where
  `Proc.poll()` returns None and health is always False: `restart()` must neither shut
  down nor spawn (the `starting` guard); mutation: remove `starting or` → it fails.
- F15 (prose): CHANGELOG 0.18.0: drop the sentence "Nothing is downloaded or signed: the app
  is built on your own machine from the anyscribe you installed." and keep the C10
  sentences. `docs/user/troubleshooting.md` (~597-601) replace the paragraph with: "That's
  expected. Windows' SmartScreen warning (and macOS's Gatekeeper prompt) is for apps
  downloaded through a web browser. Desktop mode doesn't download an app: it builds the
  small launcher on your own machine from the anyscribe you just installed, with nothing to
  sign. On a Mac this showed no Gatekeeper prompt in our test; we have not yet confirmed the
  whole Windows path, so if Windows does warn you when you click the app, tell us."
- C1 regex must also cover the `scribe` and `ascli` aliases (already in C1 above); F12 is
  the same item.
