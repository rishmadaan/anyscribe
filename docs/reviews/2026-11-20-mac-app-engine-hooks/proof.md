# Proof: phase 2a, engine hooks for the Mac app

Implementer, round 0. Worktree `~/labs/projects/anyscribe-wt/mac-engine`,
branch `feat/mac-app-engine`, base `7ab1539` (confirmed before editing). Python
environment: `.venv` inside the worktree (`uv venv`, `uv pip install -e ".[dev,mcp]"`),
importing `src/anyscribe` from this worktree. Baseline before any change:
`912 passed, 6 skipped`.

## Commits (one per item, packet first)

```
00cb756 docs: add review packet for mac app engine hooks
bbd1cad feat(engine): app mode (ANYSCRIBE_APP=1) for the Mac app's engine
6fa77b9 feat(engine): hidden 'ui --watch-stdin' so the engine follows the Mac app
1a540b6 feat(web): GET /api/jobs lists this run's jobs for the Mac app
572fec3 fix(web): refuse requests other websites send to the local engine
4cde4c1 docs(building): Mac app hooks in architecture, journal entry, index row
```
(plus the commit adding this file)

## Whole suite, as CI runs it

```
$ pytest
=========== 943 passed, 6 skipped, 160 warnings in 83.78s (0:01:23) ============
$ ruff check src tests scripts
All checks passed!
$ python scripts/check-docs.py      # CI's docs job
(no output) rc=0
```

`ruff format --check` reports drift in `src/anyscribe/cli/main.py` and
`tests/test_tailnet.py`; both files already drifted at `7ab1539` (checked on the
base copies). CI does not run the format check, and I left those lines alone. My
new lines are formatted.

## One test per item, asserting what the user would see

| Item | Test | What it asserts |
|---|---|---|
| 1 app mode | `tests/test_app_mode.py::test_update_says_the_app_updates_itself_and_runs_nothing[update]` and `[update --check]` | output is exactly "This anyscribe came with the Mac app, which updates itself.", exit code 0; `updater.subprocess.run` is replaced by a function that fails the test, so no pip or git ran |
| 1 app mode | `test_starting_in_app_mode_leaves_the_skill_folder_untouched` | a stale skill (`.version` 0.0.1) and a superseded `scribe` dir are byte-identical after a CLI start in app mode |
| 1 app mode (control) | `test_outside_app_mode_the_same_start_does_update_the_skill` | without the variable the same start rewrites `.version` to the current version and removes `scribe`, so the snapshot check can see a write |
| 1 app mode | `test_local_engines_install_with_the_apps_own_pip_and_say_app` | with pip "missing" and uv on PATH, install runs `[sys.executable, "-m", "pip", "install", faster-whisper>=1.0, av<19, onnx-asr>=0.12.0]`, uninstall runs `... pip uninstall -y faster-whisper onnx-asr`, method `app`, and the progress event says `"method": "app"` |
| 1 app mode | `test_only_the_exact_value_1_is_app_mode[0, "", true]` | other values are not app mode |
| 2 stdin | `tests/test_engine_process.py::test_closing_stdin_stops_the_engine` | the real `python -m anyscribe ui --watch-stdin --no-open --port <free>` subprocess (throwaway HOME, stopped by its own pid in the fixture's finally) exits with code 0 within 20 s of its stdin closing, and its port no longer accepts connections |
| 2 stdin | `test_stdin_end_runs_the_shutdown_path_then_exits_hard` | in-process, order is exactly: tailnet rule closed, `should_exit=True`, then `os._exit(1)` after the grace period |
| 3 jobs | `tests/test_orchestrator.py::test_job_list_shows_the_title_while_running_and_the_file_when_done` | the real `process()` (fake downloader and provider) run through the job manager; a GET `/api/jobs` made from inside the provider's transcribe call shows `title "Test Video"`, `status running`, `stage transcribe`, `file_path null`; after it ends, the exact key set, `status completed`, `stage index`, `error null`, `file_path` = the written `.md`, `completed_at >= created_at` |
| 3 jobs | `test_a_failed_job_keeps_its_title_and_shows_the_error` | failed job: `stage transcribe`, title kept, `error "provider down"`, `file_path null` |
| 3 jobs | `test_job_title_is_never_parsed_from_the_message_text` | an event "Downloaded: Looks Like A Title" with no data leaves `title null` |
| 3 jobs | `test_job_list_is_newest_first_and_at_most_50` | 60 jobs: ids j59..j10, in that order |
| 4 Origin | `tests/test_engine_process.py::test_another_website_cannot_stop_it_or_read_jobs[https://evil.example]` and `[null]` | real subprocess engine: POST `/api/shutdown` and GET `/api/jobs` with that Origin get 403; half a second later the process is alive and `/api/health` answers 200 |
| 4 Origin | `test_no_origin_and_local_origins_are_answered[None, http://localhost:5173, http://127.0.0.1:8457]` | 200 on `/api/health` and `/api/jobs` |
| 4 Origin | `tests/test_tailnet.py::test_another_websites_origin_gets_403_and_the_server_keeps_running` (6 Origins: evil.example, null, localhost.evil.example, localhost@evil.example, `http://[bad`, the tailnet name while not held) | 403 with body "anyscribe does not answer requests sent by other websites.", `server.should_exit` still False |
| 4 Origin | `test_no_origin_or_a_local_origin_on_any_port_is_answered` | no Origin, localhost:5173, 127.0.0.1:8467, [::1]:5173: 200 |
| 4 Origin | `test_another_websites_origin_cannot_open_the_progress_websocket` | WebSocket with Origin evil.example closed 1008; with localhost:5173 accepted |
| 4 Origin | `test_the_tailnet_origin_is_answered_only_while_the_share_is_held` | `{"held": 200, "evil": 403, "released": 403}` |

## Mutation tests (guard removed, seen failing, restored, seen passing)

**App-mode skill skip** (`cli/main.py`: `if not is_app():` removed, `_auto_update_skill()` called unconditionally):
```
        assert runner.invoke(app, ["update", "--check"]).exit_code == 0
>       assert _snapshot(stale_skill) == before
E       AssertionError: assert {'anyscribe':....md`.\n', ...} == {'anyscribe':...scribe': None}
tests/test_app_mode.py:69: AssertionError
1 failed, 7 deselected in 42.75s
```
Restored: `1 passed, 7 deselected in 0.32s`; `git diff | grep -c MUTANT` = 0.

**Stdin watch** (`web/app.py`: the `threading.Thread(target=_stop_when_stdin_closes, ...).start()` line replaced by `pass`):
```
E   subprocess.TimeoutExpired: Command '[.../.venv/bin/python', '-m', 'anyscribe', 'ui', '--watch-stdin', '--no-open', '--port', '34943']' timed out after 20 seconds
E   Failed: engine still running 20 s after its stdin closed:
E   anyscribe ui → http://127.0.0.1:34943
tests/test_engine_process.py:77: Failed
1 failed, 1 passed in 24.40s
```
The fixture killed that engine by its own pid; `ps` afterwards showed no `anyscribe ui --watch-stdin` left. Restored: `2 passed in 1.80s`.

**Origin check** (`web/app.py`: the `elif origin is not None and not self.allowed(_origin_host(origin))` branch removed):
```
E       assert 200 == 403
E        +  where 200 = <Response [200 OK]>.status_code          (x6, one per refused Origin)
E       Failed: DID NOT RAISE WebSocketDisconnect
E       AssertionError: assert {'held': 200,...eleased': 200} == {'held': 200,...eleased': 403}
E         {'released': 200} != {'released': 403}
E         {'evil': 200} != {'evil': 403}
E       AssertionError: assert 200 == 403
E        +  where 200 = _request(35227, '/api/shutdown', 'POST', 'https://evil.example')
E       AssertionError: assert 200 == 403
E        +  where 200 = _request(35227, '/api/shutdown', 'POST', 'null')
E       urllib.error.URLError: <urlopen error [Errno 111] Connection refused>   (x3)
```
Without the guard, the POST carrying `Origin: https://evil.example` actually shut the
subprocess engine down, so the three later "local origin" checks then found nothing
listening. That is the hole, shown live. Restored: `17 passed, 92 deselected`.

Extra (not required): removing `data={"title": download.title}` from the orchestrator
fails `test_job_list_shows_the_title...` with `assert None == 'Test Video'`.

## Live check, the way the app will run it

A stand-in app (`fake_app.py` in the session scratchpad) started the engine with
`ANYSCRIBE_APP=1`, a throwaway HOME, a free port and `stdin=PIPE`, then waited:

```
1169389 1169381 .../.venv/bin/python -m anyscribe ui --watch-stdin --no-open --port 58063
GET /api/jobs: [] 200
POST shutdown Origin evil: anyscribe does not answer requests sent by other websites. 403
POST upload Origin null: 403
health after: 200
```
Then `kill -9` of the stand-in app (pid 1169381, read with `ps` first):
```
14:11:03.707833479
14:11:04.026884530
engine 1169389 gone after fake app SIGKILL
port 58063 refused
```
The engine followed a force-killed parent in about 0.3 s.

CLI in app mode, throwaway HOME:
```
$ ANYSCRIBE_APP=1 python -m anyscribe update        -> This anyscribe came with the Mac app, which updates itself.  rc=0
$ ANYSCRIBE_APP=1 python -m anyscribe update --check -> same line, rc=0
$ ANYSCRIBE_APP=1 python -m anyscribe doctor | grep "Install type" -> Install type: Mac app
$ python -m anyscribe ui --help | grep -c watch-stdin -> 0   (hidden)
```

## Choices left to the builder

- Helper: `core/appmode.py` (`is_app()`, plus the update message constant).
- The stdin thread lives in `web/app.py` (`_stop_when_stdin_closes`), started in
  `run()` only when `watch_stdin=True`. Hard exit: `os._exit(1)` after
  `STDIN_EXIT_GRACE_SECONDS = 10`. It repeats the shutdown route's few lines
  (close the share, then `should_exit`) instead of calling the route, because
  `web/routes/system.py` was not in this slice's files.
- `GET /api/jobs` returns a plain JSON array. `stage` is the step of the last
  *pipeline* event (download, transcribe, write, index, cached), not the
  terminal done/error/cancelled markers, so a failed job shows the step it failed
  at; `status` already says completed/failed/cancelled. Times are Unix seconds
  (float), as `completed_at` already was.
- Origin refusals get their own one-line 403 body, distinct from the Host one.
- `doctor` prints "Install type: Mac app" in app mode (it would otherwise say
  "pip package").
- `CLAUDE.md`'s file tree gains `appmode.py` (one word; the repo's commit
  checklist requires new files there). Not on the scope list, not on the
  must-not-change list.
- `tests/test_ui_port.py`'s stub of `web.app.run` now accepts the new keyword.

## Where the spec is incomplete

- **Onboarding still installs the skill in the app.** (Since built: see
  "Amendment: skill install from onboarding" below.) The web wizard calls
  `run_headless_onboard()` without `install_skill`, which defaults to True, so
  finishing onboarding inside the app copies the skill when `~/.claude` exists.
  That breaks the mockup rule "only the app's Terminal switch installs the skill".
  The fix belongs in `core/onboard_headless.py` or `web/routes/onboarding.py`,
  neither in this slice, and onboarding is another session's active area. Not
  built; recorded in the journal's open items.
- **The app's window must load `http://127.0.0.1:<port>`.** A `file://` or
  custom-scheme renderer would send `Origin: null` or a non-local Origin and be
  refused. Worth stating in the desktop build's brief.

## Not checked

- macOS and Windows: everything ran on Linux only (the stdin thread is meant to
  be Windows-safe; not run there).
- The 10 s hard exit end to end (a real engine stuck in a long job after stdin
  closes); covered only by the in-process order test.
- pip with `PIP_USER=1` / `PYTHONUSERBASE` inside the packed app: taken from
  phase 0, not re-run here.
- A real Tailscale share: the tailnet-Origin test uses the suite's faked
  Tailscale CLI.

## Amendment: skill install from onboarding

The coordinator amended the spec (round 0 continued): build the gap above.
`core/onboard_headless.py` and `web/routes/onboarding.py` were put in scope for
this one change.

Change (commit `974f13d`): in `run_headless_onboard()`, where the install happens,
the condition is now `install_skill and CLAUDE_HOME.exists() and not is_app()`.
It covers the web wizard and `anyscribe onboard --yes`. (Corrected in round 1,
C3: this first said every caller, including the interactive wizard, was covered.
The interactive `anyscribe onboard` does not go through this function; it had its
own install in `cli/onboard.py` step 12, which round 1 guards too.) The response keeps its `skill_installed` field (the
one `ui/src/api/types.ts` reads), which reads `false`; no UI change, and
`web/routes/onboarding.py` needed no edit.

Tests in `tests/test_app_mode.py`:

| Test | What it asserts |
|---|---|
| `test_onboarding_in_the_app_leaves_the_skill_uninstalled` | with `ANYSCRIBE_APP=1`, POST `/api/onboarding/save` (provider openai, key sk-test) against a throwaway home holding a fake `~/.claude`: 200, and `(skill_installed, skills/anyscribe exists) == (False, False)` |
| `test_onboarding_outside_the_app_still_installs_the_skill` | same request without the variable: `skill_installed` true and `skills/anyscribe/.version` equals the current version (behaviour unchanged) |
| `test_agent_onboarding_in_the_app_leaves_the_skill_uninstalled` | a real `python -m anyscribe onboard --yes --provider openai --api-key sk-test --json` process with `HOME` set to a throwaway folder holding `~/.claude` and `ANYSCRIBE_APP=1`: exit 0, `(skill_installed, ~/.claude/skills/anyscribe exists) == (False, False)` |

Mutation (`and not is_app()` removed from that line):
```
>       assert (r.json()["skill_installed"], target.exists()) == (False, False)
E       assert (True, True) == (False, False)
>       assert (json.loads(done.stdout)["skill_installed"], skill_dir.exists()) == (False, False)
E       assert (True, True) == (False, False)
FAILED tests/test_app_mode.py::test_onboarding_in_the_app_leaves_the_skill_uninstalled
FAILED tests/test_app_mode.py::test_agent_onboarding_in_the_app_leaves_the_skill_uninstalled
2 failed, 1 passed, 8 deselected in 1.02s
```
In the subprocess case the CLI callback's own skill update is already skipped in
app mode, so the skill that appeared came from onboarding. Restored:
`3 passed, 8 deselected`; `git diff | grep -c MUTANT` = 0.

Docs: the journal's "Open for the app build" line now records this as built,
and its "What was built" item 1 lists onboarding. The architecture "Mac app
hooks" section and the `_index.md` row mention onboarding too.

Whole suite and lint after the amendment:
```
$ pytest
=========== 946 passed, 6 skipped, 160 warnings in 100.71s (0:01:40) ===========
$ ruff check src tests scripts
All checks passed!
$ python scripts/check-docs.py
rc=0
```

## Round 1 fixes (one entry per finding)

Format: change | ran | saw. Every mutant was restored and its file re-run green.

- **C1** | `vault/writer.py` writes the transcript with `core/fileutil.atomic_write` (temp file in the same folder, then `os.replace`), commit `4e2ed3e`. Encoding follow-up per the fix plan's addendum, commit `1db9f36`: `atomic_write` gains `encoding` (default `"utf-8"`, its other callers unchanged) and the writer passes `encoding=None`, the platform default that `write_text` used and every reader still uses. Other vault writes: `vault/index.py` already rewrites through `atomic_write`; its two fallback appends (`open(..., "a")`, index.py:50 and :98) are left (one short line each, and the master index can be rebuilt); `vault/scaffold.py` writes only when the vault is created, left. | `test_a_write_cut_off_part_way_leaves_no_partial_transcript` (half the bytes written, then the write raises, on both write paths); `test_transcript_keeps_the_platform_encoding` (title "Café Crème à la mode") | After the cut the folder is empty (no partial `.md`, no temp file), duplicate detection returns None, and a retry writes the exact text of a clean write. Mutant (direct write put back): fails on `assert left == {}` with a cut-off `my-test-video.md` holding frontmatter only. Encoding: the bytes equal `write_text`'s under the current locale, and with a cp1252 platform encoding they are cp1252 (`Caf\xe9 Cr\xe8me`). Mutant (writer without `encoding=None`): `At index 80 diff: b'\xc3' != b'\xe9'`. Line endings: `write_text` wrote `\r\n` on Windows and `atomic_write` writes `\n`; every reader opens in text mode, which reads both the same.
- **C2** | `GET /api/jobs` lists every pending and running job (even past 50), then the newest finished jobs up to 50 rows, newest first; `_cleanup_stale` and the 500-job cap never remove an active job, and the cap evicts the oldest finished first. Commit `54f0d0b`; architecture.md states the rule. The old "newest 50" test was replaced, since its 60 pending jobs are now all listed by design. | a running job behind 50 finished ones; 55 running jobs; the cap test | listed: 2 active plus 48 finished; all 55 listed; the cap leaves `["oldest-running", "j3", "pending"]`. Mutant (active-always-listed guard removed): `assert ('long' in ['queued', 'j49', ...])` fails, and the 55-running test fails. Mutant (cap may evict any job): `['j2', 'j3', 'pending'] == ['oldest-running', 'j3', 'pending']` fails.
- **C3** | The interactive wizard's skill install (step 12) moves into `cli/onboard.py::_install_skill_step()`, placed above `def onboard(` and away from the other session's area near line 663. In app mode it returns "not installed (the Mac app's Terminal switch installs it)"; outside app mode it behaves as before. The amendment's claim above that every onboarding caller was covered is corrected in place. Commit `95e87f9`. | `test_interactive_onboarding_in_the_app_leaves_the_skill_uninstalled`, `test_interactive_onboarding_outside_the_app_still_installs_the_skill` (throwaway `~/.claude`) | In app mode `(status, skill folder exists) == ("not installed (...)", False)`; outside, "installed" and `.version` equals the current version. Mutant (app-mode return removed): `assert ('installed', True) == ('not install...s it)', False)`.
- **C4** | `_stop_when_stdin_closes` starts a daemon `threading.Timer(STDIN_EXIT_GRACE_SECONDS, _exit_hard)` the moment stdin ends, before the tailnet cleanup and its print; `try/finally` still sets `should_exit`. Commit `16fbfd6`. | `test_slow_tailnet_cleanup_cannot_delay_the_hard_exit` (close sleeps 1.5 s, grace 0.2 s), `test_a_failing_print_cannot_skip_the_hard_exit` (print raises), `test_stdin_end_runs_the_shutdown_path_then_exits_hard` | The hard exit fires before 1.0 s while the cleanup is still running; with a raising print the order is `tailnet closed, should_exit=True, raised OSError, exit`. Mutant (timer started after the cleanup, the old order): the slow case fires at 1.70 s, and the print case never exits (`Right contains one more item: 'exit'`).
- **C5** | `_origin_host` accepts only a serialized origin (`https?://host[:port]` as a regex full match: no userinfo, path, query, fragment, spaces or newline) and returns its lowercased host; `HostCheck` refuses two or more Origin headers. Commit `836ea1f`. | Refused, in `test_another_websites_origin_gets_403_and_the_server_keeps_running`: `https://evil.example`, `null`, `""`, `http://localhost.evil.example`, `http://127.0.0.1.evil.example`, `http://localhost@evil.example`, `http://evil.example@127.0.0.1`, `http://[bad`, `file://`, `chrome-extension://abc`, the tailnet name while not held, `http://localhost:5173/`, `http://localhost:5173\n`, and Sol's `http://127.0.0.1:80@evil.example` and `http://localhost:80 https://evil.example`. Accepted: no Origin, `http://localhost:5173`, `http://127.0.0.1:8467`, `http://[::1]:5173`, `HTTP://LOCALHOST`. `https://<held name>.evil.example` refused while the share is held. `test_two_origin_headers_are_refused_in_either_order` on HTTP and on a raw WebSocket upgrade scope (TestClient joins repeated headers into one for WebSockets, so that scope is built by hand). | All as listed: 403 or close 1008, and the shutdown never ran. Mutant (netloc-then-split parsing back): 5 fail, including `http://127.0.0.1:80@evil.example` accepted. Mutant (first Origin header only): local-then-evil gives `(200, True, 'reached the route')` against `(403, False, 1008)`, so the shutdown ran and the WebSocket reached the route.
- **C6** | With `--watch-stdin` on POSIX, `run()` calls `_lead_own_process_group()` (`os.setpgrp()`, OSError ignored). `_exit_hard()` SIGKILLs its own group only when `os.getpgid(0) == os.getpid()`, then calls `os._exit(1)`; without `killpg` (Windows) only `os._exit(1)`. Commit `16fbfd6`. | `test_the_hard_exit_takes_the_engines_children_with_it` (a real process held from stopping, leading its group as `run()` does, with a `sleep 300` child); `test_the_hard_exit_never_signals_a_group_the_engine_does_not_lead` (a stand-in app, in a new session, runs an engine that is not a group leader and calls `_exit_hard`) | The child is gone after the deadline; the stand-in app prints `app survived 1`. Mutant (group kill removed): `the engine's child outlived its hard exit` (the test's cleanup stopped that child by its own pid; no `sleep 300` was left afterwards). Mutant (leadership check removed, signal its own group): the stand-in app dies with -9 and prints nothing.
- **F1** | In app mode finished jobs no longer expire after an hour; outside app mode the hour stays. Commit `54f0d0b`, with C2. | a job finished over an hour ago, with and without app mode | Kept in app mode, dropped without it. Mutant (app-mode no-expiry guard removed): `assert [] == ['j0']`.
- **F2** | Journal "Open for the app build": the last bullet is now a requirement (the app's Terminal command `~/.local/bin/anyscribe` exports `ANYSCRIBE_APP=1`, `PIP_USER=1` and `PYTHONUSERBASE=~/.anyscribe/runtime`), plus a bullet that the app re-copies the skill after each update while the Terminal switch is on. Commit `b9f9783`. | docs only; `scripts/check-docs.py` | rc=0.
- **F3** | In app mode `anyscribe ui --port N` checks only N: if it is taken, it prints "Port N is already in use." and exits 1, with no roll-forward hint. Outside app mode unchanged. architecture.md notes it. Commit `2d933c8`. | `test_in_the_mac_app_a_busy_port_is_an_error_not_a_move`, `test_in_the_mac_app_a_free_port_is_used_as_asked`, the existing roll-forward tests | In app mode on a busy port, `(exit code, ports started) == (1, [])`; the existing tests pass unchanged. Mutant (span not zeroed in app mode): `assert (0, [59036]) == (1, [])`, so it moved ports.
- **F4** | The engine fixture in `tests/test_engine_process.py` sets `ANYSCRIBE_APP=1`, so its docstring is true; the Windows lines in architecture.md and the journal now say "meant to work on Windows; not yet run there". Commit `8758435`. | `pytest tests/test_engine_process.py` | 11 passed with the app environment.
- **S-C2** (the shell's review; fix plan Addendum 2) | `GET /api/health` adds `"pid": os.getpid()`; nothing else in the response changes. architecture.md "Mac app hooks" notes it. Commit `f4fb787`. | `test_health_reports_the_engines_own_pid` against the real subprocess engine; the existing health test in `tests/test_web.py` | `(app, pid) == ("anyscribe", <the Popen's pid>)`. Mutant (`os.getppid()`): `('anyscribe', 205743) == ('anyscribe', 205789)` fails.

Also in round 1: commit `e4845eb` brings the journal and architecture.md in line with C2 to C6.

Whole suite and lint after round 1:
```
$ pytest
974 passed, 6 skipped, 184 warnings in 71.08s (0:01:11)
$ ruff check src tests scripts
All checks passed!
$ python scripts/check-docs.py
rc=0
```

## Round 3 fixes (one entry per finding)

Format: change | ran | saw. Every mutant was restored and its file re-run green. The tests check the two invariants in spec.md's "Round 3 design", not the patch.

- **A1** (a short write published as a whole transcript) | Design A, commit `61de6ac`: `core/fileutil.atomic_write` opens a hidden temp file in the same folder with `open(".<name>.<16 hex>.tmp", "xb")`, writes through that buffered file object (which writes every byte or raises), `flush()`, `os.fsync()`, closes, then `os.replace`. On any exception it unlinks the temp and re-raises; `open` sits outside the `try`, so a name it did not create is never unlinked. The `encoding` parameter is unchanged. The raise-midway test is replaced. | `test_a_short_write_never_reaches_the_final_path`: a subprocess sets `RLIMIT_FSIZE` to 64 KB, then (1) `atomic_write`s 1 MB over a file holding "old", (2) `write_transcript`s a 1.25 MB transcript into an empty vault | (1) `("EFBIG", "old", ["t.md"])`: it raised, the file still reads exactly "old", and no temp file remains. (2) `("EFBIG", [])`: nothing in the folder, and `dedup.find_existing_transcript` returns None, so a retry runs. Mutant (the old `mkstemp` + raw `os.write` back): `assert ('no error', ...xx', ['t.md']) == ('EFBIG', 'old', ['t.md'])`: the kernel's short write was ignored and 64 KB of the new content was published over "old".
- **A2** (graceful shutdown leaving children running) | Design B, commit `339bc3c`: see the invariant 2 entry below. | the real `run(watch_stdin=True)` test below | see below.
- **A3** (the encoding test decodes cp1252 output as UTF-8) | Commit `0f12967`: the test keeps the first transcript's text (`out.read_text()`) before switching the platform encoding, then compares the second transcript with `text.encode("cp1252")`. | `test_transcript_keeps_the_platform_encoding` | Passes. Mutant (writer without `encoding=None`) still fails it: `At index 80 diff: b'\xc3' != b'\xe9'`. Not run on a real cp1252 Windows interpreter.
- **A4** (Origin ports above 65535) | Commit `f0d6575`: the regex captures the port's digits and `_origin_host` refuses a value above 65535 (0 is accepted). | `test_an_origin_port_must_be_a_real_port`, HTTP `GET /api/tailnet` and a WebSocket upgrade for ports 0, 65535, 65536 and 99999 | 0 and 65535 give `(200, "answered")`; 65536 and 99999 give `(403, 1008)`. Mutant (range check removed): 65536 and 99999 give `assert (200, 'answered') == (403, 1008)`.
- **Invariant 1** (a transcript's final path only ever holds the whole content, or what it held before) | Design A as in A1. Hidden name, so Obsidian and the vault's `*.md` scans never see a temp file. | the short-write test above; `test_a_transcript_gets_the_same_permissions_as_write_text`, under umask 022 and 002 | Short write: as in A1. Permissions: a transcript gets the same bits as a plain `write_text` under the same umask (`0o644`, `0o664`). Mutant (old `mkstemp` write): `assert '0o600' == '0o644'` and `assert '0o600' == '0o664'`. fsync is not testable here (it needs a power cut); a mutant without it would survive.
- **Invariant 2** (when the app's engine ends, by any route, nothing it started is still running) | Design B, commit `339bc3c`, `--watch-stdin` only. SIGTERM and SIGINT handlers call `_exit_hard()`; they are installed before `server.run()`, and uvicorn 0.54 captures the signal while serving, stops gracefully (tailnet rule removed), restores these handlers and re-raises the signal into them. `server.run()` sits in `try/finally: _exit_hard()`. The stdin timer stays. `_lead_own_process_group()` calls `setpgrp()` only when `os.getpgid(0) != os.getpid()`. The stop test `test_closing_stdin_stops_the_engine` now expects `-SIGKILL` (1 where there are no groups), not 0. The stand-in held-engine test (`_HELD_ENGINE`) is replaced. architecture.md records the invariant and "in app mode a stop is final". | `test_the_engine_never_outlives_its_watch_by_any_route`: the real `run(watch_stdin=True)` in a subprocess (app environment, throwaway HOME, free port) with a `sleep 300` child held by a worker thread, for five stops: stdin closes; SIGTERM; stdin closes and SIGTERM (the app's quit); a server held past a 1 s deadline by a shutdown hook; started detached as a session leader (as design C will), then SIGTERM. Each reaps the engine and asserts `os.killpg(pgid, 0)` raises ProcessLookupError. | All five pass. Mutant (signal handlers dropped): `the engine's group outlived it (SIGTERM)` and `(stdin closes and SIGTERM)`: uvicorn re-raised SIGTERM into the default handler, and the engine died without its child. Mutant (`finally` dropped): `the engine's group outlived it (stdin closes)`, and the stop test `assert 0 == -9`. Mutant (group kill dropped): all four non-detached routes fail, `the engine's group outlived it (stdin closes)`, `(SIGTERM)`, `(stdin closes and SIGTERM)`, `(held)`. Mutant (the `getpgid != getpid` check before `setpgrp` dropped): all five pass. It is an equivalent mutant: as a session leader `setpgrp()` raises EPERM (probed: `PermissionError 1`, still its own group leader), which the `except OSError` already caught, and for a plain group leader `setpgrp()` is a no-op. It was kept at first because the spec asked for it, then removed in the follow-up below. Each test stopped what it started by pid (the child only while it was still in the engine's group); afterwards no `sleep 300` and no test engine was running.
- **Follow-up 1, permissions** (the fixer's risk 1: design A would have widened every existing `atomic_write` file from mkstemp's 0600 to the umask default) | Commit `43de6e0`: before the rename, `atomic_write` gives the temp file the existing target's bits (`os.chmod(tmp, stat.S_IMODE(os.stat(path).st_mode))`); a new file (FileNotFoundError) keeps the umask default. So config.yaml, the index files, batch state, the desktop manifest and the tailnet ports file keep whatever bits they have today, and new transcripts get `write_text`'s bits. | `TestAtomicWrite::test_an_existing_files_permissions_are_kept` (a 0600 file, umask 022), `TestAtomicWrite::test_a_new_file_gets_the_umask_default` (umask 022), and the transcript permission test above | `("new", "0o600")`; a new file `0o644`; transcripts still match `write_text` under umask 022 and 002. Mutant (chmod dropped): `assert ('new', '0o644') == ('new', '0o600')`.
- **Follow-up 2, the setpgrp check** | Commit `60a50b1`: the "only if not already a group leader" check (`os.getpgid(0) != os.getpid()`) is removed; `os.setpgrp()` stays inside its `try/except OSError`. It was an equivalent mutant (see invariant 2: removing it changed no outcome across all five stop routes, because a session leader's `setpgrp()` raises EPERM, which was already caught, and a plain group leader's is a no-op), so under the rule it was removed rather than kept. architecture.md says so. | `pytest tests/test_engine_process.py` after the removal | 16 passed, the detached session-leader route included.

Whole suite and lint after round 3 (before the follow-ups):
```
$ pytest
984 passed, 6 skipped, 192 warnings in 82.42s (0:01:22)
$ ruff check src tests scripts
All checks passed!
$ python scripts/check-docs.py
rc=0
```

Whole suite and lint after the round 3 follow-ups:
```
$ pytest
986 passed, 6 skipped, 192 warnings in 65.36s (0:01:05)
$ ruff check src tests scripts
All checks passed!
$ python scripts/check-docs.py
rc=0
```

## Round 4 fixes

Format: change | ran | saw. Each mutant was run with the bytecode cache for the mutated module removed and `python -B` (see the last line), then restored; the restored files passed 32 of 32.

- **R1** (a private file's temp copy was more readable than the file while it was written) | Commit `56448de`, spec.md "Round 4 design" built as one contract. `atomic_write(path, content, encoding="utf-8", new_mode=0o600)`: `mode` = the existing file's exact bits, else `new_mode`; `fd = os.open(tmp, O_WRONLY | O_CREAT | O_EXCL | O_BINARY-if-present, mode)` outside the `try`; for an existing file `os.chmod(tmp, mode)` straight after creation, before any byte (it undoes the umask's narrowing and is never wider than the target); then `os.fdopen(fd, "wb")`, write, flush, fsync, close, `os.replace`; on any failure the fd (if fdopen never took it) is closed and the temp unlinked. Hidden `.<name>.<16 hex>.tmp` name and `encoding` kept; `os.umask` is never called. `vault/writer.py` passes `new_mode=0o666`. The round 3 follow-up's chmod-before-replace is gone, replaced by the creation mode. | `TestAtomicWritePermissions` in tests/test_fileutil.py: the temp file's mode recorded right after `os.open`, at `os.fdopen` and at `os.fsync` for an existing 0600 target under umask 022; an existing 0600 file; an existing 0664 file under umask 022; a new file through the default under umask 022 and 002; `new_mode=0o666` under 022 and 002; a failed fsync leaves no temp file. In tests/test_vault_writer.py: a new transcript against `write_text` under 022 and 002, now with the expected bits named; the RLIMIT short-write test. | Temp file `{"created": "0o600", "fdopen": "0o600", "fsync": "0o600"}` and the target `("new", "0o600")`; existing 0664 stays `("new", "0o664")`; new default file `0o600` under both umasks; `new_mode=0o666` gives `0o644` and `0o664`; transcripts `("0o644", "0o644")` and `("0o664", "0o664")` against `write_text`; a failed write leaves the folder empty; the short write still raises EFBIG and leaves "old".
  - Mutant "open `xb` at the umask default" (round 3's write, chmod after fsync): `assert {'fsync': '0o644'} == {'created': '...ync': '0o600'}`, plus new default files `'0o644' == '0o600'` and `'0o664' == '0o600'`.
  - Mutant "create wide, then chmod straight after creation" (`os.open(..., 0o666)` then `os.chmod(tmp, mode)`): `{'created': '0o644'} != {'created': '0o600'}`. The record taken right after `os.open` is what catches it; at fdopen and fsync the mode was already 0600. Also `'0o666' == '0o644'` for `new_mode=0o666` and `('0o666', '0o644') == ('0o644', '0o644')` for a transcript.
  - Mutant "chmod for an existing file dropped": `assert ('new', '0o644') == ('new', '0o664')`.
  - Mutant "`new_mode` defaults to 0o666": `assert '0o644' == '0o600'` and `assert '0o664' == '0o600'`.
  - Mutant "the transcript writer without `new_mode=0o666`": `assert ('0o600', '0o644') == ('0o644', '0o644')` and `('0o600', '0o664') == ('0o664', '0o664')`.
  - A testing pitfall found on the way: a mutant that keeps a file's size (`0o600` to `0o666`) and is written in the same second as its restore leaves a cached `.pyc` that Python accepts as current, because its check is the source's mtime in whole seconds plus its size. The first pass ran the restored code from the mutant's cache, and the following run's result was invalid. Every result above comes from the second pass, with the cache file removed before each run. The earlier rounds' mutants whose edits are on record here (C1, C3 to C6, F3, S-C2, A1 to A4, design B) each changed the file's size, so the same false reading could not happen to them; the round 1 C2 and F1 mutants are not recorded closely enough to check, and their restored runs were followed by full-suite runs.

Whole suite and lint after round 4:
```
$ pytest
992 passed, 6 skipped, 192 warnings in 85.11s (0:01:25)
$ ruff check src tests scripts
All checks passed!
$ python scripts/check-docs.py
rc=0
```
