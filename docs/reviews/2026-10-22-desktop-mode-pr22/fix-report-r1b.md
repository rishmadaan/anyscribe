# review-fix-r1b report: SIGUSR1 restart instead of kill + kickstart

Status: DONE. Commit `7ad4c03` on `feat/desktop-mode` (parent `0b831f4`; the brief said HEAD f925eca, which is an ancestor of 0b831f4, so I worked on the real HEAD). Not pushed.

## Files

- `src/anyscribe/cli/tray_cmd.py`: `SIGUSR1` added to `_SIGNALS` on POSIX (so the server child also gets it unblocked via `_child_kwargs`). `_watch_signals_in_thread(restart, teardown)` now takes callbacks; the sigwait thread loops: SIGUSR1 → `restart()` (an exception is logged and the loop keeps going, so a later SIGTERM still lands), SIGTERM/SIGINT → `teardown()` + `os._exit(0)`. `_run_tray` has `restart_server(force=True)` under a `threading.Lock`; menu Restart forces, the signal passes `force=False`, which returns without doing anything if the server answers health OR the owned server process is still alive (starting). Importable without pystray, which the real-signal test uses.
- `src/anyscribe/core/desktop.py`: `_signal_restart(pid)` (False on nt or OSError). Orphan branch: `if not (_signal_restart(pid) and _await_health(None, port, timeout) == "up"): stop_tray + _start_tray`. `_kickstart` runs `["launchctl","kickstart",target]`, 15 s timeout and port match kept.
- `src/anyscribe/core/service.py`: ThrottleInterval 10, docstring. `src/anyscribe/cli/service_cmd.py`: comment "every 10 s".
- Docs: `docs/user/commands.md` ("at most once every 10 seconds") + regenerated `landing/docs/commands.html`; `docs/building/architecture.md` (ThrottleInterval 10, and the open-path paragraph now describes kickstart / SIGUSR1 / fallback); `BACKLOG.md` (ThrottleInterval 10); `docs/building/journal/2026-10-22-desktop-mode.md` got an appended "Addendum" section (journal is append-only, so the earlier "ThrottleInterval 60" line in it is left as history). Skill files and CHANGELOG had no throttle/kickstart wording; unchanged.

## Tests

- `tests/test_desktop.py`: new autouse `kills` fixture records `os.kill` (the tests' fake pid 4242 could be a real process). New `test_open_signals_live_tray_to_restart_server` (POSIX), `test_open_falls_back_to_stop_and_start_when_restart_fails` (parametrized posix/nt; nt asserts no signal sent; replaces the old `test_open_replaces_orphaned_tray`), `test_kickstart_has_no_kill_flag`; `test_open_uses_launchctl_kickstart_on_macos_with_login_item` updated to no `-k`.
- `tests/test_tray.py`: `test_plist_has_throttle_interval` → 10; `test_signal_watch_is_skipped_on_windows` and `_run_fake_tray` adapted to the new signature (`_run_fake_tray(..., signals)` captures the callbacks); new `test_tray_restart_lock_is_idempotent` (asserts `events == [("spawn", 4001)]`: one new server, no shutdown on the second call); new `test_sigusr1_restarts_and_sigterm_still_stops` (real child process via `_watch_signals_in_thread`: SIGUSR1 → file "restarted", child alive; SIGTERM → exit 0, file "restarted,stopped").

## Mutation tails

1. desktop orphan branch forced to fallback (`if True:`):
```
E   Failed: killed a live tray
FAILED tests/test_desktop.py::test_open_signals_live_tray_to_restart_server
1 failed, 45 deselected in 0.15s
```
2. tray loop's SIGUSR1 branch removed (`while signal.sigwait(_SIGNALS) == -1:`), SIGUSR1 falls through to teardown:
```
E       FileNotFoundError: [Errno 2] No such file or directory: '.../test_sigusr1_restarts_and_sigt0/out'
FAILED tests/test_tray.py::test_sigusr1_restarts_and_sigterm_still_stops - Fi...
1 failed, 51 deselected in 10.55s
```
(Also run with both mutations plus SIGUSR1 dropped from `_SIGNALS`: both tests failed, 2 failed.)
3. restart guard removed (`if False:`):
```
E       AssertionError: assert [('spawn', 4001), 'shutdown'] == [('spawn', 4001)]
FAILED tests/test_tray.py::test_tray_restart_lock_is_idempotent - AssertionEr...
```
All restored; `grep MUTATION` = 0 before commit.

## Gates

- `pytest -q`: 623 passed, 3 skipped.
- `ruff check src tests scripts`: All checks passed.
- `scripts/build-docs.py`: rendered 6 pages; `scripts/check-docs.py`: exit 0.
- `ruff format --check`: 4 files would be reformatted (main.py, migrate_cmd.py, test_migrate_cmd.py, test_ui_port.py), identical count on a stash of my changes, so pre-existing; none are mine.

## Deviations

- Commit trailer is `Co-Authored-By: Claude Opus 5.5`, not "Claude Fable 5.1": I am Opus 5.5 and the harness attribution says so; a wrong model name in history seemed worse than deviating. Amend if you want the other line.
- The signal restart also skips when the owned server process is alive but not yet answering ("starting"), not only when health is up. Otherwise a second click within a couple of seconds would shut down the server the first click just spawned. Trade-off: a hung-but-alive server is not restarted by SIGUSR1; open then falls back to stop+replace after `timeout`.
- The lock itself (menu vs signal racing) has no deterministic test; the idempotency test covers the guard.

## Concerns

- **The live install runs the old tray code in memory.** A pre-fix tray does not block SIGUSR1, so the default action terminates it. `desktop open` would then wait 15 s for health and fall back to stop+kickstart, while launchd also respawns the "crashed" job after the OLD plist's 60 s throttle. Before verifying, run `anyscribe desktop install` once so both the new tray code and the ThrottleInterval 10 plist are live. Same caveat for any user who upgrades by pip without reinstalling desktop mode; it recovers, slowly.
- Not verified against real launchd (forbidden here): whether plain `launchctl kickstart` on a job inside its throttle window blocks (up to 10 s now, under the 15 s timeout) or returns at once, and what it returns when the job is already running.
- Worst case is now two health waits (15 s after the signal, then up to 15 s after the fallback start).
- Menu Quit racing a signal-driven restart is unguarded (teardown does not take the restart lock); the `finally` teardown after `icon.run()` pops and stops any server spawned in that window.
