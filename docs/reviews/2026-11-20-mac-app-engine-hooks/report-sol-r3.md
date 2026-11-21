Note: home-folder paths rewritten to `~`.

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
