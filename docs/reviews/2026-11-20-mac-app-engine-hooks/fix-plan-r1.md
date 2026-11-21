# Fix plan, round 1 (the lead's choices; binding where it decides)

Scope grows by two files for these fixes only: src/anyscribe/vault/writer.py and src/anyscribe/cli/onboard.py (one guard near line 939; the other session's onboarding change in that file is near line 663, leave that area alone). Everything else in target.md still holds.

**C1 (partial transcript after a hard exit).** Make the transcript write atomic: vault/writer.py uses the existing `core/fileutil.atomic_write` for the final .md (temp file in the same folder, then os.replace). Check every other place the vault writes a transcript or index the same way and say in proof.md which you changed and which you left (with the reason). Test: an interrupted write leaves either no file or the complete file, never a partial one (simulate the interruption by making the temp write raise after part of the content; assert the final path's exact contents). Mutation: revert to the direct write, see the test fail.

**C2 + F1 (the job list must never hide an active job, and keep finished ones in app mode).**
- GET /api/jobs returns every pending and running job, always, plus the newest finished jobs up to 50 in total (active jobs first count against nothing; list them all even past 50).
- `_cleanup_stale` and the MAX_JOBS cap never remove a pending or running job.
- In app mode, finished jobs do not expire by age (the MAX_JOBS cap still bounds memory, evicting the oldest finished first). Outside app mode the one-hour expiry stays.
- Tests: a running job behind 50 finished ones is listed (reproduce Sol's case); in app mode a job finished more than an hour ago is still listed; the cap evicts finished jobs only. Mutation-test the "active always listed" guard and the app-mode no-expiry guard.
- Docs: state the rule in architecture.md "Mac app hooks".

**C3 (interactive onboarding).** Guard the automatic skill install in cli/onboard.py (around line 939) with `not is_app()`, matching the headless guard; the onboarding summary says "not installed" in app mode as the headless path does. Test the interactive path's install decision (drive the function with the prompts stubbed, as existing onboarding tests do, or test the decision helper you extract). Correct the proof's coverage claim.

**C4 + C6 (shutdown after stdin closes).**
- Start the hard-exit clock the moment stdin reaches end of file, independent of cleanup and printing: for example a timer thread started first, then the share cleanup and `should_exit` in a try/except that cannot skip the timer.
- With `--watch-stdin` on POSIX, the engine makes itself a process group leader at startup (`os.setpgrp()` or `os.setsid()`), so its children (pip, yt-dlp, ffmpeg) share its group. The hard exit then sends SIGKILL to its own group, but only when `os.getpgid(0) == os.getpid()` (never signal a group the engine does not lead; that could be the app's). Elsewhere (Windows, or not a group leader), keep `os._exit`.
- Tests: slow cleanup (a share.close that sleeps longer than the grace) still ends the process at the deadline; a print that raises still ends it; a real harmless child (for example `sleep 300` started by the engine process in the test) is gone after the deadline. Mutation-test the clock-starts-first ordering and the group kill.
- Use a short grace in tests through the existing constant, not 10 s of waiting each.

**C5 (Origin parsing).** Parse the Origin strictly: exactly one Origin header (two or more: refuse); the value must be `null` (refused) or a serialized origin, meaning scheme http or https, a host, an optional port, and nothing else (no userinfo, path, query, fragment or spaces). Compare `urlsplit(...).hostname` (lowercased) against the allowed names, any port. Tests for every input in lens.md's list plus Sol's two values. Mutation: revert to the netloc-then-split parsing and see `http://127.0.0.1:80@evil.example` accepted.

**F2 (the Terminal command's environment).** Reword the journal's last "Open for the app build" bullet into a requirement: the app's Terminal command (`~/.local/bin/anyscribe`) must export ANYSCRIBE_APP=1, PIP_USER=1 and PYTHONUSERBASE=~/.anyscribe/runtime, the same as the engine's environment, or `update` and local setup would write into the signed app. Add a second bullet: in app mode nothing in the engine refreshes the Claude Code skill after an app update, so the app re-copies it after each update while the Terminal switch is on.

**F3 (no port roll-forward in app mode).** In app mode, `anyscribe ui --port N` does not move to another port: if N is taken it prints the existing "already in use" message and exits 1. Outside app mode, unchanged. Test both. Mutation: remove the guard, see it move ports.

**F4 (wording).** Set ANYSCRIBE_APP=1 in tests/test_engine_process.py's engine environment (so the docstring is true) and re-run it. Change the Windows lines in architecture.md and the journal to "meant to work on Windows; not yet run there".

## proof.md
Append "## Round 1 fixes (one entry per finding)": one line per id in review-log.md (C1 to C6, F1 to F4): change | ran | saw, with the mutation result for every new guard. Then run the whole suite, ruff and scripts/check-docs.py, and report the new head sha. Commit after each finding.

## Addendum (2026-11-20, after the fixer's C1 note on encoding)
C1 must not change the encoding transcripts are written in. Before this round the writer used `write_text` with the platform default encoding, and every reader (web/routes/history.py, mcp/server.py, core/dedup.py) reads with the same default; on Windows a UTF-8 file would read back garbled. Keep the write atomic with the old encoding: give `core/fileutil.atomic_write` an optional `encoding` parameter (default "utf-8", so its existing callers are unchanged) and have vault/writer.py pass `encoding=None` (the platform default, exactly as `write_text` did). Test: the writer's output bytes equal what `write_text` produced before for a title with accented characters, under the current locale. No reader changes.

## Addendum 2 (2026-11-20, from the shell's review, C2 there)
GET /api/health adds `"pid": os.getpid()` (the engine process's own pid), so the Mac app can prove the server answering on its port is the engine it started before it loads it or sends it /api/shutdown. Additive field; nothing else in the response changes. Test: the field equals the serving process's pid (subprocess engine test) and the existing health tests still pass. Note it in architecture.md "Mac app hooks". proof.md id: S-C2.
