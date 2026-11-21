# Fix plan, round 1 (the lead's choices; binding where it decides)

The shell merges after slice 2a (engine hooks), so from now on it targets 2a's engine: always pass `--watch-stdin`, and run the e2e against 2a with `PYTHONPATH=~/labs/projects/anyscribe-wt/mac-engine/src` (read-only; that worktree is being fixed in parallel, so record the 2a commit you ran against). 2a is also adding `"pid"` to GET /api/health (the engine process's own pid) for C2.

**C1 + F2 + F1 (job list unknown vs empty; quitting and logout).**
- `jobs()` returns `null` when the list is unknown (timeout, error status, bad JSON, wrong shape) and validates shape: an array of objects with string `job_id` and `status`; anything else is unknown. Never throw on a bad body.
- The poll keeps the last known list when a read is unknown, and the state it holds says whether it is known.
- Quit decision, made synchronously in before-quit from the last poll: known and no pending or running job: do not prevent the quit; stop the engine in will-quit (close stdin, SIGTERM to its own pid; 2a's watcher and signal handling do the rest). Known with active jobs: prevent and ask (the approved question). Unknown while the engine runs: prevent and ask a plain variant: title "anyscribe couldn't check for running transcriptions", message "Quitting now stops any transcription that is still running.", buttons Quit Anyway, Cancel (Cancel default). Engine not running: quit.
- Quit When Done waits while the list is unknown; it quits only on a known empty list.
- Restart engine is refused while the list is unknown (reason "anyscribe couldn't check for running transcriptions; try again in a moment").
- Tests: each unknown cause (timeout, 500, bad JSON, `{"jobs":{}}`, `[null]`) gives unknown, not empty; quit with a known-empty list is not prevented; unknown asks the plain variant; Quit When Done does not quit on unknown. Mutation-test the unknown-is-not-empty guard and the no-prevent path.

**C4 + F3 (lifecycle races).** Serialize start, stop and restart through one queue (a promise chain); each operation claims itself before its first await. Give each launch a generation number; every continuation (`_launch` after each await, `_exitedEarly`, `_crashed`, readiness) returns without acting when its generation is stale or a stop has begun. `stop()` only clears the child it stopped. Tests with the fake engine: two concurrent restarts leave exactly one engine and the shell owns it (assert its pid); stop during "restarting" leaves no new pid; stop during the port check spawns nothing. Mutation-test the generation check.

**C2 (ownership).** Readiness requires `/api/health` to report `pid` equal to the spawned child's pid; a mismatch is "Another program is using port N" (the taken-port failure state) and the shell sends that server nothing (no /api/shutdown). Only send POST /api/shutdown to a server whose pid matched. Test with a fake second server answering on the port with another pid. Mutation-test the pid check.

**C3 (frames and redirects).** Apply the same origin rule to `will-frame-navigate` and `will-redirect` (block and, for top-level, open outside), and deny subframes from any other origin. Tests for an iframe to another origin, a redirect out of 127.0.0.1, and a popup.

**C6.** Resolve ANYSCRIBE_DEV_PYTHON to an absolute path at startup (relative to the process's cwd before any spawn); README examples use `$(pwd)/..` or an absolute path. Test.

**C7 (finished-while-hidden).** The shell remembers finished jobs it has seen go from active to finished while the window was hidden, by job id, until the window is next shown, so the engine's 50-row cap cannot drop them from the menu. Test: one failure then 50 completions while hidden keeps the failure row and the red dot.

**C8.** The force-kill check fails the e2e when the engine supports `--watch-stdin` and survives the app. Keep cleanup in finally.

**C9.** Wrap log setup and every log write so a failure never throws out of a callback or before a window exists; if app.log cannot be written, keep a small in-memory tail for Copy details and show the failure state with the reason ("Can't write the log file: <error>"). Test with an unwritable log folder.

**F4 (Start at login).** Drop `openAsHidden`. The system is the source of truth: read `app.getLoginItemSettings()` (`openAtLogin`, and `status` where present) for the menu tick and the bridge; drop startAtLogin from settings.json. Keep using `wasOpenedAtLogin` to start without a window, and record in proof.md that it is unverified on macOS 13 and later (the lead will check it on the Mac). Fix the README and proof wording.

**F5.** The dashboard window uses the default title bar until 2c adds a drag area; the start window keeps hiddenInset.

**F6.** A separator before "Open anyscribe" only when job rows are shown; use `type: 'header'` for the first line where Electron supports it, with the disabled-item look as the fallback.

**F7.** Reword the e2e step and proof to "a --hidden launch"; list the real login path under could not check.

**F8, F12.** No code change: add both to the journal's "left for phase 3" list (version stamped from pyproject.toml at packaging; a small application menu).

**F9.** Remove the no-flag fallback and its shortcut comment; always pass `--watch-stdin`.

**F10.** Create the add-ons folder only in packaged mode.

**F11.** Bring the app forward (`app.focus({ steal: true })`) before the quit question; give it the main window as parent when it is visible.

## proof.md
Append "## Round 1 fixes (one entry per finding)": one line per UPHELD id (C1 to C4, C6 to C9, F1 to F12): change | ran | saw, with mutation results for every new guard. Re-run `npm test` and the e2e against 2a (name the 2a commit). Commit after each finding.
