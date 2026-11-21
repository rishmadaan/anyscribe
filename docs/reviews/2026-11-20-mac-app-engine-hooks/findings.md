# Findings (verbatim reports)

Note: absolute home-folder paths in these copies were rewritten to `~` paths; the byte-exact originals stay in ~/.review-runs/2026-11-20-mac-app-engine-hooks/.


# Round 1


## report-sol-r1.md

~~~~
**NOT YET.** The hooks are relevant to the approved Mac app, but shutdown safety, complete job accounting, and app-mode onboarding have gaps. The reported passing tests do not cover these paths.

Reviewed `7ab1539..2dd8e64`. The checked-out source matches that target; `8ab28d0` adds only review records. No files or processes were changed.

1. **C1: blocker, CONFIRMED by trace. Forced shutdown can leave a partial transcript that later counts as complete.**

   Where: web/app.py:154 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/web/app.py:154`), vault/writer.py:138 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/vault/writer.py:138`), core/dedup.py:32 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/core/dedup.py:32`).

   After stdin closes, `os._exit(1)` can interrupt any worker, including one saving a transcript. The writer writes directly to the final `.md` path. If the deadline lands after the frontmatter reaches disk but before the body finishes, a partial transcript remains visible. Duplicate detection accepts the file as soon as its `source:` line matches, so retrying can return that partial file as “already transcribed.”

   **Fix:** publish transcripts atomically and coordinate shutdown with persistence. If completed transcription output must survive interrupted publication, preserve recoverable output before exposing the final file. Add a subprocess check that interrupts a deliberately paused write and checks the surviving file’s exact contents and retry behavior. I traced this failure path; I did not induce disk corruption.

2. **C2: blocker, CONFIRMED by reproduction. The job list can report no running jobs while a transcription is running.**

   Where: web/jobs.py:78 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/web/jobs.py:78`).

   `summaries()` returns only the newest 50 jobs, regardless of status. With one long-running job followed by 50 completed jobs, the running job disappears. This is feasible with two workers: one remains busy while the other finishes shorter jobs.

   Calling the actual summary method against that in-memory state produced:

   ```text
   {'listed': 50, 'running_listed': [], 'old_running_listed': False}
   ```

   The planned quit question, restart control, and update restart therefore cannot safely infer “nothing is running” from this list. The existing test verifies the truncation but misses its consequence. At higher volume, the existing 500-job cleanup also evicts entries without preserving active jobs.

   **Fix:** amend the spec. A capped recent-history array needs authoritative active counts or complete active-job accounting alongside it. Shutdown decisions must include every pending and running job.

3. **C3: blocker, CONFIRMED by trace. Interactive onboarding still installs the skill in app mode.**

   Where: cli/onboard.py:939 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/cli/onboard.py:939`), core/onboard_headless.py:270 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/core/onboard_headless.py:270`).

   The new guard covers the web wizard and `onboard --yes`. Interactive `onboard` follows a separate branch and calls `copy_skill_files(quiet=True)` whenever `~/.claude` exists, without checking app mode.

   Someone completing interactive onboarding using the app’s Python with `ANYSCRIBE_APP=1` still installs or overwrites the skill. The proof’s statement that the interactive TUI is covered is incorrect. All three new onboarding tests exercise the web or headless paths.

   **Fix:** guard this automatic install too, preserving normal CLI behavior outside app mode. Add an interactive-path regression test and correct the coverage claim.

4. **C4: should-fix, CONFIRMED by trace. The ten-second deadline starts after potentially slow cleanup.**

   Where: web/app.py:148 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/web/app.py:148`), core/tailnet.py:449 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/core/tailnet.py:449`).

   The watcher calls `share.close()` before setting `should_exit` and before starting its ten-second sleep. Closing waits for the share lock and can run two Tailscale commands, each with a ten-second timeout. The engine can therefore remain serving well beyond ten seconds after EOF. Waiting for an ongoing share operation adds further delay.

   Also, an exception while printing the cleanup error escapes after the `finally` sets `should_exit`, skipping the hard-exit timer entirely.

   **Fix:** establish the shutdown deadline at EOF, independently of cleanup and logging. Coordinate that deadline with the persistence protection in C1. Test slow cleanup, lock contention, and logging failure. The current order test replaces cleanup with an immediate return.

5. **C5: should-fix, CONFIRMED by reproduction and trace. Origin validation accepts malformed values and ignores additional headers.**

   Where: web/app.py:41 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/web/app.py:41`), web/app.py:72 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/web/app.py:72`).

   The parser extracts `netloc`, then applies the Host parser, which stops at the first colon. Direct calls to the actual functions accepted:

   ```text
   http://127.0.0.1:80@evil.example
   http://localhost:80 https://evil.example
   ```

   The first names `evil.example`; the second is malformed. Two Origin headers are reduced to the first, so local-then-evil passes and the reverse fails. HTTP and WebSocket requests share this logic.

   **Fix:** reject repeated Origin headers and malformed or multi-value Origins. Validate the complete Origin before comparing its parsed hostname, retaining the approved local-host and any-port policy.

   This confirms validation defects. I did **not** establish that an ordinary browser page can generate these headers, so this is not a demonstrated browser exploit.

6. **C6: should-fix, CONFIRMED by trace. Hard exit abandons subprocesses doing engine work.**

   Where: web/app.py:155 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/web/app.py:155`), core/local_setup.py:188 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/core/local_setup.py:188`), downloaders/youtube.py:75 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/downloaders/youtube.py:75`).

   Killing the Python process with `os._exit` does not terminate its subprocess tree. A pip installation, yt-dlp download, or ffmpeg conversion can survive the engine on POSIX. An app restart can then overlap an installation still changing the add-ons directory.

   **Fix:** track and shut down subprocesses owned by this watched engine, with an explicit policy for installation work. Verify a real harmless child process is gone after EOF. The current lifecycle test checks only the engine PID and listening port.

**Answers and advice**

This is the right general instrument: small engine hooks supporting the approved Electron shell. The job-list contract needs correction before the shell relies on it.

The approved fixed-port behavior also remains an integration obligation. `ui --port N` still rolls forward when N is occupied. The desktop build must reliably enforce “couldn’t start” without connecting to or stopping the occupant.

By inspection, the update guards return before pip/git execution, title data travels through the callback without message parsing, and the real `run()` path wraps routes and static files in `HostCheck`. MCP remains stdio. The ordinary foreign-Origin checks are consistent with the implementation.

**Pending owner checks**

None needed to settle these code findings. Final visual acceptance of the installed Mac app belongs to the later desktop build. Mac lifecycle, packaging, and add-on installation checks are technical verification work, not owner-only tasks.

**Verification limits and inspected material**

I read the complete review packet, settled declined finding, changed code and tests, repository instructions, commit checklist, building documentation, and the mockup’s “For the build” promises. I traced surrounding onboarding, shutdown, tailnet, subprocess, transcript-writing, deduplication, CLI, and MCP paths.

I reproduced the Origin parsing results and hidden-running-job case using import-and-print Python commands. I did not run tests, mutations, servers, builds, or installations, as prohibited. The claimed `946 passed, 6 skipped` remains builder-supplied evidence. The private plan and phase-0 artifacts were not available in the supplied packet.

The lead should rerun these commands from `~/labs/projects/anyscribe-wt/mac-engine` after fixing the findings and adding the missing regression cases:

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests scripts
.venv/bin/python scripts/check-docs.py
```

Real macOS/Windows behavior, packed-app pip installation, live Tailscale cleanup, and the busy-engine hard-exit path remain unverified here.
~~~~


## report-opus-r1.md

~~~~
FIT REVIEW, round 1: mac app engine hooks, diff 7ab1539..2dd8e64 on feat/mac-app-engine

1. VERDICT

CONDITIONAL on F1, the job list forgetting finished jobs after one hour, which breaks a menu bar promise in the approved mockup. F1 can be fixed in this slice with one line, or in the shell slice. Also wanted: the F2 wording fix in the journal.

This is the job he asked for. It covers the engine side of the approved Mac app and adds nothing beyond it, apart from two small, justified extras: `doctor` showing "Mac app", and the onboarding skill fix the coordinator added by amendment. Each hook matches a promise in the mockup's "For the build" list:
- "No surprise skill": app mode plus the onboarding guard.
- "One job list": GET /api/jobs.
- "Stop with the app": `--watch-stdin`.
- The Origin fix closes a real hole, and the spec approved it.

The code is small and follows the repo's existing patterns: one place reads the variable, the new route reuses `job_manager`, and the Origin check reuses `HostCheck.allowed`. I found no over-engineering.

2. FINDINGS

F1 (should-fix, CONFIRMED by reading both sides): finished jobs drop out of /api/jobs one hour after they finish, so the menu's "Finished while the window was closed" rows disappear unseen.
- Where: src/anyscribe/web/jobs.py:17 (`JOB_TTL_SECONDS = 3600`). `_cleanup_stale()` runs inside `summaries()` at jobs.py:78, and also in `get()` and `submit()`.
- Mockup section 6, direction A: "Jobs that finish while the window is closed stay in the menu as Saved or Failed until the window is opened". The spec says the menu bar, the quit question, Settings and the update restart "will all read this one list". The shell branch (feat/mac-app-shell, desktop/src/logic.js:136-143 `menuModel`) builds those rows only from the current /api/jobs, filtered by `completed_at >= hiddenSince`, and keeps no memory of its own.
- Scenario: he closes the window at 9:00. A job fails at 9:05 and the menu shows "Failed" with a red dot. At 10:10 the engine has dropped the job, so the menu reads "Ready" with no dot. He never learns it failed.
- The docs overclaim in the same way. architecture.md's "Mac app hooks" section and the journal say "every job this engine run knows" and "this run's jobs", but never mention the one-hour expiry.
- Fix, simplest first:
  (a) Engine: skip the time-based expiry in app mode, `if is_app(): skip the TTL part` in `_cleanup_stale`. The MAX_JOBS 500 cap and the 50-row listing still bound memory, and the shell needs no change.
  (b) Shell: it polls every 2 s, so it can remember finished-while-hidden jobs itself.
  Whichever is chosen, state the expiry, or its absence in app mode, in architecture.md's "Mac app hooks" section.

F2 (should-fix, the code path is CONFIRMED; the signing consequence is PLAUSIBLE): the journal understates what happens if the Terminal command does not set ANYSCRIBE_APP=1.
- Where: docs/building/journal/2026-11-20-mac-app-engine-hooks.md, last "Open for the app build" bullet. It says the shim's choice "decides whether `update` there says 'the app updates itself'; that is the shim's choice, not the engine's."
- What actually happens without the variable, traced:
  - `anyscribe update` from Terminal reaches `updater._pip_update()`, which runs `[sys.executable, "-m", "pip", "install", "--upgrade", "anyscribe"]`. `sys.executable` is the Python packed inside the app (the shell spec puts it at `<resources>/python/bin/python3`). A shell started from Terminal has no PIP_USER, so pip writes into the app bundle itself.
  - `anyscribe local install` from Terminal does the same, via `detect_install_method()`, which would no longer return "app".
  - Every Terminal command also runs `_auto_update_skill()`.
- Writing into a signed bundle very likely breaks its signature: PLAUSIBLE. A packaged run in phase 3 would settle it.
- Fix: reword the bullet to a requirement. The `~/.local/bin/anyscribe` shim must export ANYSCRIBE_APP=1, PIP_USER=1 and PYTHONUSERBASE=~/.anyscribe/runtime, the same as the engine environment in the shell spec. Add a companion bullet: in app mode nothing in the engine refreshes the Claude Code skill after an app update, so the app must re-copy it (for example `anyscribe skill install`) after it updates itself whenever the Terminal switch is on. Otherwise the skill stays at the version installed when he turned it on.

F3 (nit, PLAUSIBLE): "Its own port" depends on the shell reading the engine's printed output, not on the engine.
- Where: src/anyscribe/cli/main.py, the `ui` port scan (`PORT_SCAN_SPAN = 10`).
- In app mode the engine still moves to the next port when its port is busy. The shell guards against this by checking the port first, then matching `http://127.0.0.1:(\d+)` in the engine's output and killing the engine if the port moved (desktop/src/engine.js:192-196).
- That holds only while the printed line stays the same. In the race window, an engine that moved could also begin a tailnet share on the wrong port before it is stopped.
- Fix (optional): in app mode, do not move ports; exit non-zero with the existing "already in use" message. That makes the promise the engine's own, and the output matching can go later.

F4 (nit, CONFIRMED): two claims are worded stronger than their evidence.
- tests/test_engine_process.py's docstring says "The real engine as the Mac app starts it", but the fixture's environment does not set ANYSCRIBE_APP=1. Fix: set it in the fixture's env, or reword the docstring.
- The journal and architecture.md say the stdin thread "behaves the same on Windows" and "also works on Windows". Nothing ran on Windows (proof.md says so). Fix: say "meant to work on Windows; not yet run there".

3. ANSWERS (advice, not findings)
- Simplest thing: yes. `_stop_when_stdin_closes` repeats the shutdown route's few lines (close the share, then `should_exit`) rather than calling the route. Since system.py was out of scope, that is acceptable.
- A release note is worth having. The Origin fix changes behaviour: any page or bookmarklet on another site that calls the local API is now refused. When the release writes its CHANGELOG entry, name this as a security fix. The spec's "nothing user-facing" is true for screens, not for this behaviour.
- The hard exit uses code 1. The shell may report code 1 as a crash ("engine exited with code 1") if it ever observes this exit. It normally won't, because the shell kills the engine itself on stop. A distinct exit code would make the log clearer. Optional.

4. PENDING OWNER CHECKS
- None of the decisions here need him. A real Mac run, force-quitting the packaged app and watching the engine stop, belongs to phase 3, not to him.

5. NOT CHECKED, AND WHAT I INSPECTED
- I ran nothing: no tests, as the brief requires. If F1 is fixed engine-side, the lead can run `.venv/bin/python -m pytest -q tests/test_orchestrator.py -k job_list` plus a new test that sets `completed_at` more than 3600 s back under ANYSCRIBE_APP=1 and asserts the job is still listed. Mutation-check it by removing the `is_app()` skip.
- Not traced: the 10-second hard exit landing during a vault write. vault/writer.py:138 uses a plain `write_text`, not `core/fileutil.atomic_write`, so a hard exit at that exact moment could leave a cut-off transcript that a later run finds and reports as "Already transcribed". The window is microseconds. writer.py is out of this slice; a correctness reviewer should take it.
- Inspected: the whole packet (ask, spec, target, proof-bar, proof, lens, declined.md, nothing reopened); the full source diff plus surrounding code (jobs.py, web/app.py HostCheck and run, cli/main.py _auto_update_skill, ui, update, doctor, updater.py _pip_update, local_setup.py install and uninstall paths, onboard_headless.py, the /api/shutdown route, every on_progress caller, the other skill-copy sites); the docs diff (architecture.md, journal, _index.md, CLAUDE.md) and tests/test_engine_process.py; the mockup's job map and sections 2, 6, 7, 8, 9, 10 and "For the build"; the sibling branch feat/mac-app-shell (spec.md, desktop/src/engine.js port and readiness, logic.js menuModel); the onboarding branches (none touch onboard_headless.py, web/app.py or jobs.py).

Skipped: deep attacks on the Origin check and the race and abort cases, which belong to the correctness reviewer. Risk: F1 is invisible in testing unless someone waits an hour with the window closed.
~~~~

# Round 2

## report-astra-r2.md

~~~~
**NOT YET.** The job accounting, onboarding guard, deadline ordering and fixed-port changes work as intended. Transcript publication still has a data-loss path, and child-process cleanup misses graceful shutdown.

Reviewed code at **2b1c2bc**. Checkout HEAD is `07b6e40`, which adds only the round-2 patch and review-log note; source and tests match the requested target. No files were changed, and no tests, servers, builds or installations were run.

**Round-1 findings**

Paths below are relative to `~/labs/projects/anyscribe-wt/mac-engine`.

| ID | Status | Evidence |
|---|---|---|
| C1 | **PARTLY** | `vault/writer.py:142` now publishes through a temporary file, protecting against interrupted publication. The helper ignores short writes and can publish incomplete contents. See A1. |
| C2 | **FIXED** | `web/jobs.py:66–96` preserves and lists every active job. In-memory cases with 0, 1, 50, 51 and 600 mixed-state jobs lost no active IDs and retained newest-first ordering. |
| C3 | **FIXED** | `cli/onboard.py:443` returns before skill installation in app mode; the actual interactive wizard calls this helper at line 958. |
| C4 | **FIXED** | `web/app.py:173–181` arms the timer before cleanup and printing, with `should_exit` in `finally`. In-memory tracing confirmed that ordering. |
| C5 | **PARTLY** | Userinfo, trailing paths, whitespace and repeated headers are rejected. HTTP and WebSocket checks still accept out-of-range ports. See A4. |
| C6 | **PARTLY** | `_exit_hard()` signals only a group the engine leads. In-memory tracing confirmed the nonleader branch signals no group. Graceful exit can bypass child cleanup entirely. See A2. |
| F1 | **FIXED** | A two-hour-old failed job remained in app mode and expired outside it. This fixes age-based expiry; the explicitly approved listing and memory limits still apply. |
| F2 | **FIXED** | The journal now requires all three Terminal environment variables and skill refresh after app updates. Shell implementation remains a separate integration obligation. |
| F3 | **FIXED** | App mode probes only the requested port. Simulating busy on the first probe and free on a subsequent probe produced exit 1, one probe and no engine start. |
| F4 | **FIXED** | The subprocess fixture sets `ANYSCRIBE_APP=1`; both Windows claims now explicitly say untested. |
| S-C2 | **FIXED** | `web/routes/health.py:26` returns `os.getpid()`. Calling the handler with dependency checks stubbed returned the current process’s PID. The supplied subprocess test compares it with the spawned engine PID. |

**New findings and remaining defects**

1. **A1: blocker, CONFIRMED. A short write is published as a complete transcript.**

   Where: core/fileutil.py:45 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/core/fileutil.py:45`), newly used by vault/writer.py:142 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/vault/writer.py:142`).

   `os.write()` returns the number of bytes written. The helper ignores that result, closes the file and renames it to the final `.md` path. A short successful write, for example when storage fills during writing, therefore publishes truncated contents.

   I reproduced this entirely in memory using the actual helper and duplicate detector, replacing filesystem operations with doubles:

   ```text
   expected_bytes: 404
   published_bytes: 49
   publish_calls: ['published']
   dedup_returns: 'final.md'
   truncated_tail: b'video\n---\n\nTrans'
   ```

   The saved prefix includes the source URL, so duplicate detection accepts it and a retry skips transcription. The existing interruption test always raises after writing a prefix; it does not cover a short return without an exception.

   **Fix:** write until every byte is accounted for, or use a buffered file writer that handles short writes. Publish only after successful completion. Add regressions for a short return followed by completion, and a short return followed by failure. Assert exact surviving contents and duplicate-detection behavior, then mutation-test the completion guard.

2. **A2: should-fix, CONFIRMED by trace. Graceful shutdown can leave pip running after the engine exits.**

   Where: web/app.py:174 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/web/app.py:174`), web/app.py:250 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/web/app.py:250`), routes/models.py:177 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/web/routes/models.py:177`).

   The model-download worker is a daemon thread. When an engine package is missing, its path is:

   ```text
   _worker_loop → ensure_runtime → install_faster_whisper → subprocess.run(pip)
   ```

   If stdin closes during that installation, the server can finish shutting down before the ten-second deadline. The timer is also a daemon, so Python exits without waiting for it. Nothing after `server.run()` terminates the owned children. Pip can continue modifying the add-ons directory while a replacement engine starts.

   The supplied child-process test explicitly keeps its stand-in engine alive with `time.sleep(300)`, forcing the timer to fire. It therefore proves the hard-exit branch but misses this branch.

   **Fix:** clean up owned subprocesses on graceful termination as well as at the deadline, preserving the process-group ownership check. Add a regression through the model-worker path with a harmless child and a server allowed to stop normally.

   This exact command lets the lead demonstrate the missing lifecycle case using the existing test harness. I did **not** execute it:

   ```sh
   .venv/bin/python -B - <<'PY'
   import os, runpy, signal, subprocess, sys, time

   t = runpy.run_path("tests/test_engine_process.py")
   code = t["_HELD_ENGINE"].replace("time.sleep(300)", "time.sleep(0.1)")
   proc = subprocess.Popen(
       [sys.executable, "-B", "-c", code],
       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
       text=True, start_new_session=True,
   )
   child = int(proc.stdout.readline())
   try:
       proc.stdin.close()
       print("engine exit:", proc.wait(timeout=5))
       time.sleep(1)
       print("child survived deadline:", t["_alive"](child))
   finally:
       if proc.poll() is None:
           proc.kill()
           proc.wait()
       if t["_alive"](child):
           os.kill(child, signal.SIGKILL)
   PY
   ```

3. **A3: nit, CONFIRMED. The platform-encoding test fails on the Windows encoding it intends to support.**

   Where: tests/test_vault_writer.py:237 (`~/labs/projects/anyscribe-wt/mac-engine/tests/test_vault_writer.py:237`).

   On a CP1252 Windows interpreter, the first transcript correctly contains CP1252 bytes. The assertion then decodes those bytes as UTF-8, raising `UnicodeDecodeError` on “Café”. I reproduced that byte-conversion failure in memory.

   **Fix:** retain the original Unicode text before changing the encoding mock, then compare the second output with that text encoded as CP1252.

   Lead verification on a CP1252 Windows interpreter:

   ```sh
   python -X utf8=0 -m pytest -q tests/test_vault_writer.py::test_transcript_keeps_the_platform_encoding
   ```

4. **A4: nit, CONFIRMED. Strict Origin parsing still accepts impossible ports.**

   Where: web/app.py:45 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/web/app.py:45`).

   The expression restricts the port to five digits but does not validate its numeric range. Both `http://localhost:65536` and `http://localhost:99999` pass. I confirmed that `99999` reaches the wrapped application through both HTTP and WebSocket middleware.

   This contradicts the claimed serialized-origin validation. It is **not** a demonstrated browser-origin bypass: the allowed hostname remains local.

   **Fix:** validate the optional port numerically, accepting the approved valid-port range, including port 0, and rejecting values above 65535. Add both HTTP and WebSocket regressions.

**Pending owner checks**

None needed to settle these findings. Packaged Mac lifecycle checks, real Tailscale cleanup and platform verification are technical work for the implementation team. Final visual acceptance belongs to the desktop-app phase.

**Verification scope and limits**

I read the complete packet, both round-1 reports, verdict ledger, binding fix plan and addenda, supplied delta, settled declined list and approved mockup. I inspected the changed implementation and regression cases, then traced transcript writing and deduplication, job cleanup, interactive/headless onboarding, subprocess creation, model-worker lifetime, shutdown and tailnet cleanup. The declined findings were not reopened.

Read-only reproductions covered the requested job counts; malformed Origins, repeated headers, held/released tailnet names, bracketed/unbracketed IPv6, mixed-case schemes and ports; timer-before-cleanup ordering; group-leadership branching; strict-port behavior; age-based job retention; and PID reporting.

The reported **974 passed, 6 skipped**, lint and documentation checks remain lead-supplied evidence. I could not independently run process-lifetime checks, real interrupted disk writes, mutations, macOS/Windows execution, packaged pip installation or live Tailscale operations under this brief. A hard deadline also does not prove Tailscale rule removal completed: it can interrupt cleanup.

After adding the missing regressions, the lead should run:

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests scripts
.venv/bin/python scripts/check-docs.py
```
~~~~

# Round 3

## report-sol-r3.md

~~~~
**NOT YET.** The original short-write and graceful-shutdown defects are repaired by inspection. The permissions follow-up leaves a temporary disclosure window, and the sibling shell still misses child cleanup on an early startup death.

Reviewed engine source at **4d9bb42**. Checkout HEAD `586bfb9` adds only review records; source and tests match the target. No files were changed, tests run, or processes signalled.

| Item | Status | Evidence |
|---|---|---|
| A1 | **FIXED** | Buffered write, flush and fsync must finish before replacement. Exceptions remove the temporary file. The supplied RLIMIT regression checks exact surviving contents and duplicate detection. |
| A2 | **FIXED for the original graceful-exit defect** | Watched `server.run()` now has a `finally` cleanup path; restored signal handlers cover uvicorn’s signal re-raise. The broader lifecycle invariant still has the shell gap in R2. |
| A3 | **FIXED** | The test retains Unicode text before changing the encoding mock and compares against `text.encode("cp1252")`. Real Windows execution remains unverified. |
| A4 | **FIXED** | Import-and-print probes rejected ports 65536 and 99999. In-memory ASGI probes returned HTTP 403 and WebSocket 1008, while 65535 passed. |
| Follow-up 1: permissions | **PARTLY** | The final replacement keeps existing permission bits, but those bits are applied after the temporary copy has been written. See R1. |
| Follow-up 2: `setpgrp` check | **FIXED** | The redundant pre-check is removed. `setpgrp()` remains guarded, and `_exit_hard()` independently checks group ownership before signalling. |

New findings, most severe first:

1. **R1: should-fix, CONFIRMED by trace. Private files acquire a more readable temporary copy.**

   Where: core/fileutil.py:48 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/core/fileutil.py:48`), especially the write at line 51 and chmod at line 55.

   With umask 022, `open(tmp, "xb")` creates a 0644 temporary file even when the existing target is 0600. The helper writes and syncs its contents before applying 0600. In a directory accessible to other users, they can read that copy during this interval. A SIGKILL before chmod can leave it readable indefinitely.

   An in-memory probe of the actual helper recorded:

   ```text
   open(xb) → write → flush → fsync → chmod(0600) → replace
   ```

   This affects existing private batch-state files, configuration and indexes. API keys use the separate `.env` writer, so this is not a demonstrated API-key leak. The existing permissions test checks only the final pathname and misses the interval.

   **Fix:** for an existing target, establish its permissions on the temporary file before writing any content. Retain the approved umask behavior for new files. Add a regression inspecting temporary permissions during flush/fsync, then verify it fails when the early permission protection is removed.

   This exact disposable-directory probe would settle the real filesystem behavior. I did not run it:

   ```sh
   .venv/bin/python -B - <<'PY'
   import os, stat, tempfile
   from pathlib import Path
   from unittest.mock import patch
   from anyscribe.core import fileutil

   with tempfile.TemporaryDirectory() as directory:
       folder = Path(directory)
       target = folder / "state.json"
       target.write_text("old")
       target.chmod(0o600)
       previous = os.umask(0o022)
       real_fsync = os.fsync

       def inspect(fd):
           real_fsync(fd)
           temporary = next(folder.glob(".*.tmp"))
           assert stat.S_IMODE(temporary.stat().st_mode) == 0o600

       try:
           with patch.object(fileutil.os, "fsync", inspect):
               fileutil.atomic_write(target, "new")
       finally:
           os.umask(previous)
   PY
   ```

2. **R2: should-fix, CONFIRMED by trace. The shell abandons helpers when the engine dies before initial readiness.**

   This is an integration finding in **`feat/mac-app-shell` at `3051264`**, separate from the frozen engine source.

   Where: `desktop/src/engine.js:270–277`, `_exitedEarly()`.

   After readiness, `_crashed()` kills the dead engine’s remaining process group. Before initial readiness, `_exitedEarly(auto=false)` goes directly to `_fail()`, which clears the child reference without group cleanup.

   A real engine can already have children before readiness: `/api/health` launches dependency-version subprocesses, and tailnet startup can launch Tailscale commands. If the engine receives SIGKILL or crashes natively during that interval, its Python exit handlers cannot run, and the shell takes this unchecked branch.

   **Fix:** clean the owned group on early unexpected exit too, before discarding its identity. Add an early-death-with-helper regression. The current fake engine’s `exit-early` mode exits before creating its helper, so the existing early-exit test cannot detect this.

   After adding that case, run from the shell worktree:

   ```sh
   node --test desktop/test/engine.test.js
   ```

Migration and integration judgments:

- **All `atomic_write` callers:** config, master/daily indexes, batch state, desktop manifest, tailnet ownership file and transcripts share the repaired write mechanism. Existing final permission bits are retained; new files follow umask. Temporary confidentiality remains R1.
- **Fsync cost:** every call now waits for storage, including CLI and MCP writes. No timing evidence establishes the cost. File fsync also does not prove directory-entry durability across power loss.
- **Hidden vault temporary files:** the `.tmp` suffix excludes them from the inspected history, deduplication and index `*.md` scans. Obsidian behavior was not exercised. SIGKILL can leave a partial hidden temporary file; no scavenger removes it.
- **Tailnet cleanup:** EOF explicitly closes the share; ordinary graceful signal and API shutdown routes invoke cleanup. The deadline, failed cleanup, or abrupt death can leave a Tailscale rule. Removal is best effort, not guaranteed on every route.
- **Exit codes and bind failure:** the shell accepts signal exits and suppresses expected-stop crash handling. A bind failure after the CLI’s port check becomes SIGKILL in watched mode through `finally`; its stderr remains available. The sharing thread waits for successful binding, so that failure creates no new share.
- **Uvicorn compatibility:** 0.27 returns after handling signals; 0.29 introduced capture and re-raise, also present in 0.54. The outer `finally` covers the return path, and restored handlers cover re-raise. These paths were traced, not exercised as a version matrix. [0.27 source](https://raw.githubusercontent.com/encode/uvicorn/0.27.0/uvicorn/server.py), [0.29 source](https://raw.githubusercontent.com/encode/uvicorn/0.29.0/uvicorn/server.py), [0.54 source](https://raw.githubusercontent.com/Kludex/uvicorn/0.54.0/uvicorn/server.py).
- **“A stop is final”:** immediate job termination is implemented intentionally. A killed pip install can leave partially installed add-ons; the packet supplies no interrupted-install recovery proof. This needs disposable-runtime verification before packaging release.
- **CLI, MCP and Claude Code without app/watch flags:** the new signal and process-group behavior is gated off. They inherit the shared write changes, including R1. Transcript newline normalization and safer active-job retention are additional previously documented differences from the original baseline.
- **Windows:** engine termination is implemented, but child-tree termination is not: the fallback is `os._exit(1)`. The unconditional “nothing it started is still running” claim therefore needs a POSIX qualification until Windows lifecycle work exists.

I read every file directly named by the brief, the approved mockup, the changed implementation and relevant regressions, and traced all atomic-write callers, transcript readers, subprocess creation, shutdown and tailnet ownership. I also inspected the sibling shell’s supervisor, fake engine and lifecycle tests. The settled declined findings were not reopened.

Read-only reproductions confirmed Origin rejection and preservation of all 70 active job IDs in a 600-job in-memory case. The reported **986 passed, 6 skipped**, lint, documentation checks and mutation results remain lead-supplied evidence. This brief prohibited independently running them, kernel interruption probes, servers or installations. Packaged macOS behavior, Windows, live Tailscale removal and interrupted pip recovery remain unchecked. No owner-only action is needed to resolve these findings.
~~~~

# Round 4

## report-sol-r4.md

~~~~
**GOOD TO GO for the reviewed engine changes at `4470a4d`.** The round-4 permission fix addresses the previous disclosure window, and I found no new blocker or should-fix defect in the delta. This verdict covers the engine slice, not packaged-app release verification.

Checkout HEAD was `62cba9c`; its changes after the target are review records only. Source and tests match `4470a4d`. I changed nothing and ran no tests, servers, installations or process-lifetime experiments.

| Item | Status | Evidence |
|---|---|---|
| A1: short writes | **FIXED** | Buffered writing, flushing, fsync and closing precede replacement. The RLIMIT regression checks the exact surviving `"old"` contents, absence of temporary files and duplicate-detection behavior. |
| A2: graceful exit leaves children | **FIXED for the original POSIX defect** | Watched `server.run()` ends through `_exit_hard()` in `finally`; installed handlers also cover uvicorn’s signal re-raise. The supplied lifecycle regression exercises the real `run()` with a child. |
| A3: encoding regression test | **FIXED** | The test retains Unicode text before changing the encoding mock, then compares CP1252 bytes. Actual Windows execution remains unverified. |
| A4: impossible Origin ports | **FIXED** | Import-and-print reproduction accepted 0 and 65535 and rejected 65536 and 99999. |
| Follow-up 1: permissions | **FIXED for the specified mode-bit cases** | Existing permissions determine creation mode; new ordinary files default to 0600; transcripts explicitly request 0666 narrowed by umask. |
| Follow-up 2: redundant `setpgrp` check | **FIXED** | The redundant check is removed; guarded `setpgrp()` and the independent ownership check before group signalling remain. |
| Previous R1: readable temporary copy | **FIXED** | `os.open(..., mode)` establishes permissions at creation, before writing. The new regression observes creation itself, as well as fdopen and fsync, catching create-wide-then-chmod. |
| Previous R2: shell early-exit cleanup | **FIXED by source trace in the current sibling shell** | At shell `8d448c8`, `_onExit()` kills the owned group before taking any exit branch. An early-death-with-helper regression exists. I did not execute it or independently approve the whole shell. |

The implementation matches the five-point round-4 design: publication follows a complete buffered write; temporary permissions are supplied at creation; existing mode bits are restored after umask narrowing; default and transcript creation modes are distinct; and ordinary exception paths attempt temporary-file cleanup. Exclusive creation remains outside the cleanup `try`, so a failed name collision cannot delete somebody else’s file.

**New findings:** none confirmed or sufficiently supported to raise. The limitations below remain material boundaries on the claims.

**Migration and integration judgments**

| Risk | Judgment |
|---|---|
| Config | `save_config()` uses the default mode. New files are private; existing mode bits are retained. |
| Master and daily indexes | Atomic-write calls use the same default. Existing bits are retained. The pre-existing fallback append paths remain non-atomic. |
| Batch state | Uses the default mode; existing bits are retained and new files are private. |
| Desktop manifest | Same permission behavior through `write_manifest()`. |
| Tailnet ownership file | Same permission behavior through `_record()`. Its existing cross-process update race is unchanged. |
| Transcripts | The writer alone passes `new_mode=0o666`, preserving normal umask-based creation permissions. Encoding remains platform-default. |
| Fsync cost | Every atomic write now waits for file synchronization. No timing evidence establishes the cost. File fsync without directory fsync does not establish rename durability through power loss. |
| Hidden vault temporary names | Their `.tmp` suffix excludes them from the inspected history, deduplication and index `*.md` scans. Obsidian behavior was not exercised. |
| Hard-kill leftovers | SIGKILL can leave a partial hidden temporary file. It cannot publish that partial file as the final transcript. No scavenger was demonstrated. |
| Tailnet removal | EOF explicitly calls `share.close()`; normal server shutdown also calls it. Cleanup failure, deadline expiry and abrupt death can leave a Tailscale rule. Removal on every exit is not guaranteed. |
| Exit codes and shell handling | A watched POSIX engine normally ends with SIGKILL. The shell distinguishes requested cancellation from unexpected exit using its run state, rather than requiring exit code zero. |
| Bind failure | A bind failure inside watched `server.run()` reaches the hard-exit `finally`, replacing the ordinary numeric exit with a signal exit. Error output remains available. Sharing waits for `server.started`, so this failure creates no new share. |
| Uvicorn 0.27 to 0.54 | The traced designs are covered: 0.27 returns after signal handling; 0.29 and 0.54 restore handlers and re-raise. The outer `finally` covers return, and installed handlers cover re-raise. This was source inspection, not a release-by-release runtime matrix. [0.27 source](https://raw.githubusercontent.com/encode/uvicorn/0.27.0/uvicorn/server.py), [0.29 source](https://raw.githubusercontent.com/encode/uvicorn/0.29.0/uvicorn/server.py), [0.54 source](https://raw.githubusercontent.com/Kludex/uvicorn/0.54.0/uvicorn/server.py). |
| “A stop is final” | Implemented for children remaining in the owned POSIX group. Running jobs and pip installations can end mid-step. The Windows fallback exits only the engine, so the child-cleanup invariant cannot be claimed there. |
| Add-ons after interrupted pip | No rollback or recovery proof was supplied. Importability checks do not establish that an interrupted installation is intact. Disposable-runtime verification remains necessary before packaging release. |
| CLI, MCP and Claude Code | App/watch-specific lifecycle behavior remains gated off. Round 4 changes their shared permission behavior only. Across the whole branch, “unchanged except fsync and permissions” is too broad: previously reviewed active-job retention and Windows transcript newline changes also exist. |

**Verification scope and limits**

I read every file directly named by the brief, including both diagnoses, all verbatim findings, the verdict ledger, fix proofs and settled declined list. I inspected the delta, actual write implementation and regressions, every atomic-write caller, transcript readers, shutdown and tailnet paths, app-mode guards, job accounting, and the sibling shell’s exit handling.

Read-only reproduction confirmed the imported helper’s new signature and Origin-port behavior. Source/test whitespace checks passed; the worktree was clean. The broader whitespace check reported whitespace in archived review logs.

The reported **992 passed, 6 skipped**, lint, documentation checks and mutation results remain lead-supplied evidence. The brief prohibited independently reproducing filesystem interruption, permission mutations, process termination, live Tailscale cleanup or interrupted pip installation. Packaged macOS behavior, Windows behavior and installed-runtime recovery remain technical verification work; none requires an owner-only action.
~~~~
