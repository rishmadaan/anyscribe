# Review fix wave r2: PR #22 (feat/desktop-mode)

Base 273be39. Seven commits, one per section. Gates before each commit:
`.venv/bin/python -m pytest -q && .venv/bin/ruff check src tests scripts`.
Final run: **647 passed, 3 skipped; ruff: All checks passed**; `scripts/build-docs.py && scripts/check-docs.py` clean.

Note on ruff: the `ruff` on PATH (/Library/Frameworks/.../3.13/bin/ruff) is a different version and reports
hundreds of findings across untouched files. The project's `.venv/bin/ruff` (what CI pins) is clean, so that one is the gate.
`ruff format --check` flags 4 files (cli/main.py, cli/migrate_cmd.py, tests/test_migrate_cmd.py, tests/test_ui_port.py).
That drift predates this wave; none of those files was touched here.

## W: Windows CI, f5c1e16
- tests/test_desktop.py: the expected signal is `getattr(signal, "SIGUSR1", None)`.
- Grep for every `signal.SIGUSR1` in src and tests: desktop.py:152 sits after `if os.name == "nt": return False`.
  tray_cmd.py:30 is inside `if os.name != "nt"`. tray_cmd.py:115 runs inside `_watch`, which `_watch_signals_in_thread` never starts on nt.
  test_tray.py:777 and test_desktop.py:315 are skipif Windows. Nothing is evaluated unguarded on Windows.
- Not run on Windows here. The CI rerun confirms it.

## C1: role-aware, alias-aware identity, c63872d
- core/tray.py: a new `command_line_is(cmdline, role)` uses the brief's regex. `pid_is_anyscribe(pid, role)` and `_read_pid(path, role)` call it.
  `read_pidfile()` passes "tray"; the server pidfile in `stop_tray` passes "ui". `service.uninstall_service` already uses `read_pidfile()`.
- **Deviation (one character): the regex has an optional `"` after the script name**: `(?:\.exe)?"?`.
  On Windows, Win32_Process.CommandLine quotes the path: `"C:\...\Scripts\anyscribe.exe" tray`. That puts a quote between `.exe` and the space.
  The brief's regex without the quote would not match a real Windows console-script tray. A unit case covers it.
- Tests (tests/test_tray.py):
  - `test_command_line_identity`: 11 fixed strings. They cover the module form, `ui` vs `tray`, `scribe` and `ascli`, quoted and unquoted Windows `anyscribe.exe tray`,
    a path containing "anyscribe", a transcription (`-m anyscribe https://x`), `transcribe tray` and `traybox`.
  - `test_command_line_identity_ignores_case_only_on_windows`.
  - `test_path_containing_anyscribe_is_not_a_tray_and_survives_stop_tray`: a real child. It is not recognised, `stop_tray` returns False and that exact child is still alive.
  - `test_transcription_is_not_a_tray`: a real child whose argv is `... -m anyscribe https://x`. It is rejected for both roles.
  - `test_alias_tray_is_recognised_and_keeps_its_login_item_job`: a real child whose argv ends `/x/bin/scribe tray --port 8457`.
    It is recognised as a tray and not as a ui. With the real `read_pidfile`, `uninstall_service` removes the plist without an unload, and the child is still alive.
  - The existing stubs moved to `lambda pid, role: True`.
- **Test-harness finding:** a real-child identity check taken right after `Popen` is racy on macOS. ps can show the command line mid-exec, because a framework Python re-execs to Python.app.
  One mutation run passed falsely before I fixed this. `_child()` now waits for the child to print "ready" before any check. After that, 5 of 5 mutation runs failed correctly and 3 of 3 real runs passed.
- Mutation: drop the role token (`)\s+'` instead of `)\s+{role}\b'`):
  ```
  FAILED tests/test_tray.py::test_command_line_identity[/usr/bin/python3 -m anyscribe ui --port 8457 --no-open-tray-False]
  FAILED tests/test_tray.py::test_command_line_identity[/usr/bin/python3 -m anyscribe https://x-tray-False]
  FAILED tests/test_tray.py::test_command_line_identity[/usr/bin/python3 -m anyscribe traybox-tray-False]
  FAILED tests/test_tray.py::test_transcription_is_not_a_tray - AssertionError:...
  FAILED tests/test_tray.py::test_alias_tray_is_recognised_and_keeps_its_login_item_job
  >           assert tray.pid_is_anyscribe(child.pid, "tray") is False
  E           AssertionError: assert True is False
  ```
- Mutation: the old substring check (`return "anyscribe" in out`):
  ```
  FAILED tests/test_tray.py::test_path_containing_anyscribe_is_not_a_tray_and_survives_stop_tray
  FAILED tests/test_tray.py::test_transcription_is_not_a_tray
  FAILED tests/test_tray.py::test_alias_tray_is_recognised_and_keeps_its_login_item_job
  3 failed, 64 deselected
  ```
- I checked that `ps -o command=` does not truncate when piped: a 461-character command line came back whole.

## C2/F10: open --port N never stops the install on another port, 41b4322
- core/desktop.py: new `PortMismatch(installed, requested)`, a DesktopError, so the CLI already maps it to exit 1. It uses the F10 wording:
  ``anyscribe is installed on port {installed}. Run `anyscribe desktop open` (no --port) to open it, or `anyscribe desktop install --port {requested}` to move it.``
- `_login_item_port()` is the plist parsing factored out of `_kickstart`. `_kickstart` now calls it, with the same behaviour.
  `installed_port()` returns the manifest's port, else the login item's.
- The check lives in `open_dashboard`, right after `read_pidfile()` and before any signal, stop or spawn. That also covers the launcher path.
- **Additional fix the check made necessary:** on macOS, reinstalling on a new port (8500 to 9000) failed with PortMismatch.
  The cause: launchd's new tray is alive inside install's own `open_dashboard`, while the old manifest still says 8500, because the manifest is written last.
  `install()` now deletes the old manifest right after it stops the old tray and removes the old login item.
  If install then fails, `desktop status` says "Partly installed ... Run: anyscribe desktop install". That is accurate, because the old install has already been torn down.
- Test isolation: the autouse fixture now stubs `service.plist_path` to a tmp path. Before this, `installed_port()` would have read the real `~/Library/LaunchAgents` plist of the live install.
- Tests (tests/test_desktop.py):
  - `test_open_other_port_refuses_without_touching_running_instance`: manifest 8457, live pid, `--port 9000`. The exact message is raised.
    `os.kill`, `stop_tray`, `spawn_detached` and `_start_tray` are never called, and no browser opens. The CLI exits 1.
  - `test_installed_port_falls_back_to_login_item`.
  - `test_reinstall_on_new_port_opens_without_port_mismatch`.
- Mutation: remove the check:
  ```
  E   Failed: stopped the tray
  tests/test_desktop.py:354: Failed
  ```
- Mutation: remove the manifest unlink in install:
  ```
  E   anyscribe.core.desktop.PortMismatch: anyscribe is installed on port 8500. Run `anyscribe desktop open` (no --port) to open it, or `anyscribe desktop install --port 9000` to move it.
  ```

## C3: a duplicate tray that exits 0, c3c3429
- `_await_health` returns "exited-ok" for code 0 and "exited" otherwise. In `open_dashboard`, "exited-ok" waits for health again with `_await_health(None, ...)` and never spawns `ui`. Only "exited" takes the `ui --no-open` fallback.
- Test: `test_open_waits_for_winning_tray_when_duplicate_exits_zero`. The spawned process polls 0 and health turns True on later probes.
  Exactly one spawn happens, and it is the tray; there is no `ui` spawn; the URL is returned and opened.
  The headless test `test_open_falls_back_to_ui_when_tray_dies` (code 1, so `ui`) still passes.
- Mutation: treat exit 0 as failure:
  ```
  E   anyscribe.core.desktop.StartFailed: anyscribe did not start on port 8457. ...
  FAILED tests/test_desktop.py::test_open_waits_for_winning_tray_when_duplicate_exits_zero
  1 failed, 1 passed (the headless ui-fallback test stays green)
  ```

## C4: an explicit foreign app field wins; the legacy shape is typed, 9cdabaa
- `health_is_anyscribe`: if `"app"` is in the body, it is anyscribe only when the value is `"anyscribe"`. Only when `app` is absent does the legacy rule apply: `version` must be a str and `dependencies` a dict. The docstring calls the legacy rule a compatibility heuristic for pre-0.18 servers.
- Tests use the real local HTTP server:
  - `test_health_identity_explicit_foreign_app_wins`: `{"app":"another-program","version":"1","dependencies":{}}` is foreign.
  - `test_health_identity_legacy_shape_is_typed`: `{"version":null,"dependencies":null}` is foreign.
  - The existing 0.17.1 test still passes.
- Mutation: drop the explicit-app precedence:
  ```
  FAILED tests/test_tray.py::test_health_identity_explicit_foreign_app_wins
  E       AssertionError: assert True is False
  ```
- Mutation: an untyped legacy check (`"version" in body and "dependencies" in body`):
  ```
  FAILED tests/test_tray.py::test_health_identity_legacy_shape_is_typed
  ```

## C5 + F14: one lifecycle lock, 8b048bb
- cli/tray_cmd.py: state is `{"proc": None, "closing": False, "lock": threading.RLock()}`.
  It is an RLock because the restart calls `_start_server` while holding the lock.
  `_start_server` and `restart_server` both run under `state["lock"]` and return at once when `closing` is set.
  `_teardown` sets `closing = True` before it waits for the lock, then pops and stops the server under the lock.
- Harness: `_run_fake_tray(..., during=)` runs the test body inside the fake icon loop. Before this, the loop returned at once, and the tray's own finally-teardown (which now sets `closing`) ran before the test's restart calls.
  `test_tray_restart_lock_is_idempotent` was rewritten onto `during` with the same assertion: one new server (4001), and only the dead one is shut down.
  The two direct `_teardown` tests now pass a lock in their state.
- **Brief correction:** the brief's single scenario (restart paused inside Popen, teardown concurrent) tests the *lock*, not the `closing` check.
  With the lock in place, teardown waits, then stops the restart's new server, whether or not `closing` exists. Removing `closing` would not fail that test.
  So there are two tests, each with its own mutation:
  - `test_teardown_stops_a_server_a_concurrent_restart_is_starting` (the brief's scenario): the restart pops the dead server and blocks in a gated Popen; teardown starts; then the gate is released.
    Survivor identity: the servers are exactly [4000, 4001], and none is alive after teardown.
  - `test_restart_waiting_on_the_lock_spawns_nothing_after_quit`: teardown is paused while it holds the lock, and a restart is queued behind it. After release, the only server ever started is [4000].
  - F14 `test_tray_restart_leaves_a_starting_server_alone`: `poll()` returns None and health is always False. The restart neither shuts down nor spawns; alive is [4000] and the shutdown list is empty.
- Mutation: remove both `closing` checks:
  ```
  E       assert [4000, 4001] == [4000]
  FAILED tests/test_tray.py::test_restart_waiting_on_the_lock_spawns_nothing_after_quit
  ```
  Either check alone is enough to pass this test, because the restart calls `_start_server`, which checks too. The restart's own check only skips a pointless shutdown and its 0.5 s sleep.
- Mutation: teardown without the lock:
  ```
  E       assert [4001] == []
  FAILED tests/test_tray.py::test_teardown_stops_a_server_a_concurrent_restart_is_starting
  ```
- Mutation: F14, remove `starting or`:
  ```
  E       AssertionError: assert [[4001], ['shutdown']] == [[4000], []]
  FAILED tests/test_tray.py::test_tray_restart_leaves_a_starting_server_alone
  ```
- The tray tests passed in 3 of 3 repeated runs, so the threaded tests showed no flakiness here.

## C6 / F11 / F13 / F15: docs, 240766b
- Uninstall copy, with the exact text: cli/desktop_cmd.py `STOPPED_COPY`, docs/user/commands.md, docs/user/getting-started.md (which now quotes the message), the skill references/commands.md uninstall row, and the test assertion.
- docs/user/commands.md: the example comment now reads `# Set up desktop mode without opening the dashboard now`.
- docs/building/architecture.md:
  - The Gatekeeper sentence is replaced with the exact text.
  - The supervision paragraph now says the tray attaches only to a listener that identifies itself on `/api/health`, and that one tray runs at a time through a lifetime OS lock on `~/.anyscribe/tray.lock`, not the pidfile.
  - The install-order summary: on macOS the login item comes first and launchd starts the tray; on Windows and Linux the tray is spawned first.
- Skill references/commands.md tray section: the Quit/SIGTERM sentence is exact, and the F11 "already running" sentence is exact.
- F11: skill references/troubleshooting.md and docs/user/troubleshooting.md use the exact text.
- F13: docs/user/configuration.md gains three inventory rows and four tree lines.
- F15: CHANGELOG 0.18.0 drops the "Nothing is downloaded or signed..." sentence and keeps the C10 sentences.
  docs/user/troubleshooting.md: the security-warning paragraph is replaced with the exact text. It had also contained a stray pasted architecture sentence, which is now gone.
- Added because the CLAUDE.md skill-sync rule requires it: the new `open --port` refusal is documented in the skill references/commands.md exit-codes paragraph and in the docs/user/commands.md `--port` row.
- `landing/docs` regenerated; check-docs is clean.

## Concerns
- Windows is unverified locally: the quoted-path regex, case-insensitivity, and the W fix all depend on CI.
- C2 changed `install()`: the old manifest is deleted mid-reinstall. See C2 for why, and for what `status` shows if a reinstall then fails.
- C5: a teardown now waits for any in-flight restart. That restart's `_shutdown_server` can take up to about 8 s when a server ignores /shutdown, so Quit can take that long in the worst case. This is by design, so nothing is orphaned.
- None of the live install, `~/.anyscribe`, LaunchAgents or launchctl was touched. Every test uses tmp pidfiles, locks and plists, free ports and port-0 HTTP servers. The lead's live verification is still owed.
