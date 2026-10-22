# Review fix wave r1, PR #22 (feat/desktop-mode, from 24a5322)

Status: DONE_WITH_CONCERNS (concerns at the end; none blocks).

| Section | Commit | Subject |
|---|---|---|
| A ownership | 478b3f0 | own the tray by OS lock, identify anyscribe on the wire, signal only our pids |
| C Windows streams | 6893690 | give a windowless pythonw tray and its server real output streams |
| B install path | 8b8209d | install stops a running tray even without a manifest; quiet launchctl |
| D status | 4450c4f | status is healthy only when installed and the dashboard answers |
| E docs/copy/UI | 513a6a7 | first-run, --no-launch, security-prompt and status copy; skip headless Linux |
| Addendum (lead) | a440865 | treat a pre-0.18 server's health answer as anyscribe |

Not pushed. Nothing was run against the real `~/.anyscribe`, launchd or port 8457. The tests use the conftest tmp HOME, tmp pidfile/lock/server.pid, and ports 0/free. `desktop._kickstart` is stubbed to False in an autouse fixture because launchctl acts on the real user's job whatever HOME says.

## A. Ownership redesign (C1, C2, C3, C5, F1/C6, F4)

Files: `src/anyscribe/core/tray.py`, `src/anyscribe/core/desktop.py`, `src/anyscribe/cli/tray_cmd.py`, `src/anyscribe/web/routes/health.py`, `src/anyscribe/cli/desktop_cmd.py` (STOPPED_COPY), `docs/user/commands.md`, `docs/user/getting-started.md`, `src/anyscribe/skill/references/commands.md`, `landing/docs/*.html`, `tests/conftest.py` (new `health_server` fixture: a real ThreadingHTTPServer on port 0), `tests/test_tray.py`, `tests/test_desktop.py`, `tests/test_web.py`.

- A1: `tray.acquire_instance_lock(path=None) -> IO | None` uses `fcntl.flock(LOCK_EX|LOCK_NB)`, or `msvcrt.locking(LK_NBLCK, 1)` after `seek(0)` on Windows, on `APP_HOME/tray.lock` (opened `a+`, never truncated). `tray()` takes the lock before the pystray import. When the lock is busy it prints "An anyscribe tray is already running." and exits 0. A missing extra still exits 1. The lock stays held in `tray()`'s frame for the whole of `_run_tray`, and `write_pidfile()` comes after it. Python file handles are non-inheritable, so the server child does not get the lock.
- A2: `/api/health` adds `"app": "anyscribe"`. `health_is_anyscribe` moved to `core/tray.py` and `desktop.py` re-imports it. The tray's `_start_server` attaches only when the identity matches. A foreign listener sets `state["foreign"]`, which shows `Status: port N is used by another program`, writes one `tray: ...` line to stderr (tray.log), and starts no server. Open UI opens the browser only when the identity matches; otherwise it logs a line. `_post_shutdown` posts only to anyscribe.
- A3: `pid_is_anyscribe(pid)` uses `ps -o command= -p` on POSIX and PowerShell `Get-CimInstance Win32_Process` CommandLine on Windows. A non-positive pid or any error returns False. `read_pidfile()` (via `_read_pid`) requires the pid to be alive and pass this check. A pid that fails is never signalled, and the stale file is removed.
- A4: the tray writes `APP_HOME/server.pid` after spawning the server and removes it when the server stops (`_shutdown_server`). `stop_tray` stops the tray, then the recorded live anyscribe server (SIGTERM, then SIGKILL after the same timeout, then waits for the port), and removes both pidfiles. It returns True if either was signalled. The uninstall copy is the exact brief text. The same meaning is in getting-started (~272), commands.md (912) and the skill reference.
- A5: `desktop._start_tray(port)`: on darwin, `_kickstart(port)` runs `launchctl kickstart -k gui/<uid>/com.anyscribe.tray` (check=False, capture_output, timeout 15). If that fails, or on any other OS, it uses `spawn_detached`. `open_dashboard` checks whether a live tray's port comes up within `ORPHAN_GRACE = 3.0`. If not, it calls `tray.stop_tray(port)` then `_start_tray(port)` and waits for health. `_start` became `_await_health(proc, port, timeout)`.

Tests added or changed:
- `test_instance_lock_excludes_second_process`: real `sys.executable -c` children. The first holds the lock 2 s and prints its line before the second starts. The test asserts `(first, second) == ("got", "busy")`, then that the lock is free after the holder exits.
- `test_tray_command_exits_zero_while_lock_held`: the real `python -m anyscribe tray --port <free>` with a tmp HOME, the lock held by the test process. Exit 0, the already-running line on stderr, no tray.pid written.
- `test_health_identity_requires_app_field`: a real server returning `{"version":"1"}` is foreign; with `app` it is ours.
- `test_open_refuses_foreign_listener`: now uses the real `port_responding` and the real health parser against that server. Asserts PortInUseError and no browser opened.
- `test_post_shutdown_leaves_foreign_server_alone`: the real server records POSTs. None arrive for the foreign shape; one `/api/shutdown` arrives for ours.
- `test_pid_is_anyscribe_rejects_non_positive_and_other_programs`.
- `test_stale_pidfile_with_reused_pid_is_not_signalled`: a real `sleep 30` child (`ping -n 30` on Windows). Its pid goes in tray.pid, then `stop_tray(free_port, timeout=1)` runs. Asserts `child.poll() is None` first, then the return is False and the pidfile is gone.
- `test_stop_tray_stops_recorded_server`: the kill sequence is `[(777, SIGTERM), (888, SIGTERM)]` and both pidfiles are gone.
- `test_tray_does_not_attach_to_foreign_server`: `_run_tray` with a fake pystray against the real foreign server. No Popen, the status text names the foreign port, Open UI opens nothing, and the log line is present.
- `test_tray_records_server_pid`.
- `test_open_replaces_orphaned_tray`: order `["stop", "start"]`, exactly one spawn, browser opened.
- `test_open_uses_launchctl_kickstart_on_macos_with_login_item`: exact argv, no spawn.
- `test_open_spawns_when_kickstart_fails`.
- `test_kickstart_skips_login_item_for_another_port`.
- Updated: `test_open_does_not_spawn_second_tray` (the port binds within the grace; stop_tray fails if called); the health parametrize (version-only is now False); the uninstall copy assertion; the stop_tray unit tests (they stub `pid_is_anyscribe`); `test_web` checks `app`.

Mutation tails (each applied alone, the named tests run, the file restored):
```
== M1 LOCK_SH
E       AssertionError: assert ('got', 'got') == ('got', 'busy')
FAILED tests/test_tray.py::test_instance_lock_excludes_second_process - Asser...
1 failed in 2.21s
== M2 no identity check in _read_pid (the sleep child gets killed)
E           AssertionError: assert -15 is None
E            +  where -15 = poll()
E            +    where poll = <Popen: returncode: -15 args: ['sleep', '30']>.poll
FAILED tests/test_tray.py::test_stale_pidfile_with_reused_pid_is_not_signalled
1 failed in 1.58s
== M3 orphan branch removed
E               anyscribe.core.desktop.StartFailed: anyscribe did not start on port 8457. See the log: .../test_open_replaces_orphaned_tr0/logs/tray.log
FAILED tests/test_desktop.py::test_open_replaces_orphaned_tray - anyscribe.co...
1 failed in 1.12s
== M4 health accepts any {"version"}
E       AssertionError: assert True is False
E        +  where True = <function health_is_anyscribe ...>(62565)
E       Failed: DID NOT RAISE <class 'anyscribe.core.desktop.PortInUseError'>
FAILED tests/test_tray.py::test_health_identity_requires_app_field - Assertio...
FAILED tests/test_desktop.py::test_open_refuses_foreign_listener - Failed: DI...
2 failed in 1.18s
== M5 tray attaches to any listener (port_responding instead of identity)
E       AssertionError: assert 'Status: running' == 'Status: port...other program'
E         - Status: port 62628 is used by another program
E         + Status: running
FAILED tests/test_tray.py::test_tray_does_not_attach_to_foreign_server - Asse...
1 failed in 0.60s
== M5b Open UI without identity
E       AssertionError: assert ['http://127.0.0.1:62631'] == []
FAILED tests/test_tray.py::test_tray_does_not_attach_to_foreign_server - Asse...
1 failed in 0.65s
== M6 _post_shutdown without identity
E       AssertionError: assert ['/api/shutdown'] == []
FAILED tests/test_tray.py::test_post_shutdown_leaves_foreign_server_alone - A...
1 failed in 0.68s
== M7 server pid not stopped
E       assert [(777, <Signals.SIGTERM: 15>)] == [(777, <Signa...SIGTERM: 15>)]
E         Right contains one more item: (888, <Signals.SIGTERM: 15>)
FAILED tests/test_tray.py::test_stop_tray_stops_recorded_server - assert [(77...
1 failed in 0.12s
== M8 kickstart never used
E               anyscribe.core.desktop.StartFailed: anyscribe did not start on port 8457. ...
FAILED tests/test_desktop.py::test_open_uses_launchctl_kickstart_on_macos_with_login_item
1 failed in 1.12s
```
Gates before the A commit: 609 passed, 3 skipped. Project ruff (`.venv/bin/python -m ruff check src tests scripts`): All checks passed. build-docs rendered 6 pages; check-docs rc=0.

## C. Windows streams (C4)

Files: `core/tray.py` (`ensure_streams()`: if stdout or stderr is None, it opens `tray.TRAY_LOG` with append, line-buffered utf-8, and assigns it only to the stream that is None), `web/app.py` (`from anyscribe.core.tray import ensure_streams as _ensure_streams`, called first in `run()`), `cli/tray_cmd.py` (`ensure_streams()` at the top of `tray()`; the server is spawned with `stdin=DEVNULL` and stdout/stderr on tray.log, opened `ab`).

Tests:
- `test_ensure_streams_replaces_none`: `sys.stdout.name == str(TRAY_LOG)`, and the working stderr is left alone.
- `test_uvicorn_config_with_no_stdout`: the reviewer's probe as a subprocess with a tmp HOME/USERPROFILE. Exit 0, and tray.log was created in the tmp home.
- `test_tray_records_server_pid` also asserts the Popen streams.

Mutation tails:
```
== MC1 ensure_streams a no-op
E         ValueError: Unable to configure formatter 'default'
E       assert 1 == 0
E           assert (None is not None)
FAILED tests/test_tray.py::test_uvicorn_config_with_no_stdout - AssertionErro...
FAILED tests/test_tray.py::test_ensure_streams_replaces_none - AttributeError...
2 failed in 0.96s
== MC2 server spawned without explicit streams
E       KeyError: 'stdin'
FAILED tests/test_tray.py::test_tray_records_server_pid - KeyError: 'stdin'
1 failed in 0.33s
```
Gates: 611 passed, 3 skipped; project ruff clean.

## B. Install path (F2)

Files: `core/desktop.py` (`if old or tray.read_pidfile() is not None:`, then `stop_tray(old port or requested)`, then `uninstall_service()`, then the port wait), `core/service.py` (`_launchctl` uses capture_output and text, and prints one line to stderr: `launchctl {verb} did not succeed: {first stderr line}`).

Deviation, with evidence: the brief says to print the line "on non-zero exit", but on this Mac (macOS 26.6.2) legacy `load`/`unload` exit 0 when they fail:
```
$ launchctl load /nonexistent/x.plist      -> stderr "Load failed: 5: Input/output error\nTry running `launchctl bootstrap` as root...", rc=0
$ launchctl unload /nonexistent/x.plist    -> stderr "Unload failed: 5: ...", rc=0
$ launchctl kickstart -k gui/501/com.anyscribe.nonexistent -> rc=113
```
So a non-zero exit **or any stderr text** counts as failure. Success prints nothing.

Tests:
- `test_install_stops_running_tray_without_manifest`: no manifest, live pidfile; order is stop_tray, then uninstall_service, then install_service; stop called with 9000.
- `test_launchctl_failure_prints_one_plain_line[0|5]`: the exact one-line stderr, nothing on stdout.
- `test_launchctl_success_prints_nothing`: asserts capture_output=True.

Mutation tails:
```
== MB1 drop the pidfile clause
E       assert [] == [9000]
FAILED tests/test_desktop.py::test_install_stops_running_tray_without_manifest
1 failed in 0.12s
== MB2 non-zero exit only
E       AssertionError: assert '' == 'launchctl lo...utput error\n'
FAILED tests/test_tray.py::test_launchctl_failure_prints_one_plain_line[0] - ...
1 failed, 1 passed in 0.14s
== MB3 output not captured
E       KeyError: 'capture_output'
FAILED tests/test_tray.py::test_launchctl_success_prints_nothing - KeyError: ...
1 failed in 0.12s
```
Gates: 615 passed, 3 skipped; project ruff clean.

## D. Status semantics (C8)

`status()`: `healthy` requires an intact install **and** `server_running`. An intact install with no server gets the reason `Installed but not running. Click the anyscribe app or run: anyscribe desktop open`. `installed` is unchanged. Docs: commands.md table row ("`healthy` is true only when the app is installed and its dashboard answers"), the skill reference row, and the JSON note.

Tests: `test_status_healthy` (health stubbed True) and `test_status_installed_but_not_running_is_not_healthy` (exact reason).
```
== MD1 healthy ignores the server
E       assert (True is True and False is False and True is False)
FAILED tests/test_desktop.py::test_status_installed_but_not_running_is_not_healthy
1 failed in 0.12s
```
Gates: 616 passed, 3 skipped; project ruff clean; check-docs rc=0.

## E. Docs and copy (F3, F6, C9, C10, F7)

- F3, `docs/user/getting-started.md`: the "Used the one-line installer?" paragraph is at the top of Option A, and the closing line is the exact brief text. The "way back in" paragraph is unchanged: it is now true through A5.
- F6: human-mode install prints `Starts at login: yes` (the path stays in `--json`). The group help reads "app icon, start at login, tray icon". The Settings caption reads "Starts anyscribe in the background when you log in." I ran `npm ci && npm run lint && npm run build` (lint clean). The bundle is committed: `index-CzIwZuKn.js` replaces `index-B3cD0Um3.js`, and `index.html` changed.
- C9: the exact text is in `desktop_cmd.py` help, the SKILL.md row, the docs/user/commands.md flag row and the skill references/commands.md flag row. I also added to the commands.md macOS note that after Quit, clicking the app starts the tray again under the crash guard (A5 makes that true).
- C10: the exact sentences are in CHANGELOG (0.18.0 entry), troubleshooting ("Windows didn't show a security warning") and the journal tldr.
- F7, `install.sh`: on Linux with neither DISPLAY nor WAYLAND_DISPLAY set, it warns `Desktop mode skipped: no graphical session detected. On a desktop, run: anyscribe desktop install` and skips desktop mode. `run_installer_dry` now passes `DISPLAY` (inherited or `:0`), so a headless Linux CI runner still takes the desktop path in the existing tests. New test `test_headless_linux_skips_desktop_and_says_why`: the skip path, plus Wayland alone still installing.
```
== ME1 headless check removed
E       assert ('[dry-run]' in '...' and 'desktop install --yes' not in '...')
E         'desktop install --yes' is contained here:
E           anyscribe desktop install --yes
FAILED tests/test_install_sh.py::test_headless_linux_skips_desktop_and_says_why
1 failed in 0.15s
```

## Addendum: pre-0.18 health shape (lead request)

`health_is_anyscribe` = HTTP 200, a dict body, and (`app == "anyscribe"` or both `version` and `dependencies` present). `{"version": "1"}` alone stays foreign. New `test_health_identity_accepts_pre_0_18_shape`, which uses the real local server with `{"ok", "version": "0.17.1", "dependencies"}`.
```
== MA1 drop the fallback clause
E       AssertionError: assert False is True
E        +  where False = <function health_is_anyscribe ...>(65005)
FAILED tests/test_tray.py::test_health_identity_accepts_pre_0_18_shape - Asse...
1 failed in 0.99s
== M4 re-run against the new rule (fallback = "version" alone)
E       AssertionError: assert True is False
E       Failed: DID NOT RAISE <class 'anyscribe.core.desktop.PortInUseError'>
FAILED tests/test_tray.py::test_health_identity_requires_app_field - Assertio...
FAILED tests/test_desktop.py::test_open_refuses_foreign_listener - Failed: DI...
2 failed in 1.53s
```

## Final gates (HEAD a440865)

```
.venv/bin/python scripts/build-docs.py   -> rendered 6 pages + index
.venv/bin/python scripts/check-docs.py   -> rc=0
bash -n install.sh                        -> ok
.venv/bin/python -m pytest -q             -> 618 passed, 3 skipped in 52.39s
.venv/bin/python -m ruff check src tests scripts -> All checks passed!
ruff format --check (touched files)       -> 27 files already formatted
```
Bare `ruff` on PATH is a global 0.16.2 with a user-level rule set. It reports 281 findings at 24a5322 and 294 at HEAD. The 13 new ones are BLE001 (the `except Exception` in `health_is_anyscribe`, moved from desktop.py), SIM115 ×2 (the lock and the stream file must stay open), PLW1510, RUF012 and RUF100 in tests. The project's pinned ruff (0.15.7, what CI installs) is clean.

## Deviations

1. `_launchctl` treats stderr text as failure as well as a non-zero exit (B, evidence above).
2. `_kickstart` also checks that the login item's ProgramArguments end in the requested port. `kickstart -k` would otherwise start the tray on the installed port while `desktop open --port N` waits on N. Covered by `test_kickstart_skips_login_item_for_another_port`.
3. `ensure_streams` replaces only the stream that is None, not both (a working stream is kept). In the pythonw case both are None, so the effect is the same.
4. Commit trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, not the requested "Claude Fable 5.1". This run is Opus 5.5 and the harness attribution rule names that line. Amend if you want the other.
5. The C commit came before B, as the work order said.

## Concerns

- `pid_is_anyscribe` matches the substring "anyscribe" in the command line. A tray started as `scribe tray` / `ascli tray` from an interpreter whose path lacks "anyscribe" would not be recognised, so stop_tray would leave it. Desktop mode always runs `-m anyscribe`. Separately, any process whose path contains "anyscribe" passes (for example, on this Mac the repo's own `.venv` python), so the check proves less than full process identity: it has no creation-time check, which Sol suggested. That is acceptable for pid reuse after a reboot.
- `ORPHAN_GRACE = 3.0` s: a tray that has just started (at login) and whose server takes longer than 3 s to bind the port would be judged orphaned and replaced. That is one avoidable restart, not a failure. ProcessType Interactive should keep binding fast; it was not measured.
- The tray's lock path when it runs for real (`anyscribe tray` with the lock free and pystray present) was not executed end to end. That would start a real tray icon. It is covered by the lock-held subprocess test and the fake-pystray `_run_tray` tests. The lead's live re-run should cover: two quick app clicks, Shutdown then app click, the F2 upgrade path, and `desktop status` with the server stopped.
- Windows: `msvcrt.locking`, the PowerShell identity probe and the stream fix are written to the documented semantics but not run on Windows here. The CI desktop-platforms Windows job runs test_tray/test_desktop, including the real lock and stale-pid tests (a `ping` sleeper), so it will exercise them.
- `npm ci` reinstalled `ui/node_modules` (the documented command); nothing else outside my edits was touched. `docs/reviews/` is untouched.
