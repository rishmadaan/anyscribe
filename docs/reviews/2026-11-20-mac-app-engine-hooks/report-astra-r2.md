Note: home-folder paths rewritten to `~`.

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
