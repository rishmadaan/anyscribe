Note: home-folder paths rewritten to `~`.

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
