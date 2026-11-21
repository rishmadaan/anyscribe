Note: home-folder paths rewritten to `~`.

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
