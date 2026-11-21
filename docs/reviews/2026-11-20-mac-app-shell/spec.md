# Spec: phase 2b, the Mac app shell (dev-runnable; packaging is phase 3)

A new top-level folder `desktop/`: an Electron app that starts the anyscribe engine, shows the existing dashboard in its window, and lives in the menu bar. It follows T3 Code's pattern (a local server plus a window) without its complexity. The design is the approved mockup (path in ask.md), sections 2, 6, 7 and 9, menu bar direction A. Screens inside the dashboard (Settings "This Mac", the engine banner, first-launch cards, the Terminal switch, the old-launcher removal) are slice 2c, built later; this slice gives them the bridge they will call.

## Stack (decided)
- Electron 44.9.3, pinned exactly (phase 0 proved it on the owner's Mac; T3 Code uses it). No other runtime dependencies. No TypeScript, bundler or framework: plain JavaScript with a preload script. electron-builder and electron-updater come in phase 3, not now.
- `desktop/package.json` scripts: `start` (dev run), `test` (node's built-in test runner, `node --test`).
- Security: contextIsolation on, nodeIntegration off, sandbox on; the page gets only the bridge below. Links that leave 127.0.0.1 open in the default browser (setWindowOpenHandler and will-navigate).

## Starting the engine
- Python: in dev, the path in env ANYSCRIBE_DEV_PYTHON (for example the repo's .venv/bin/python); packaged (phase 3), `<resources>/python/bin/python3`. One function resolves it.
- Command: `<python> -m anyscribe ui --port <N> --no-open --watch-stdin`, with stdin a pipe the shell keeps open (slice 2a adds `--watch-stdin`; until it merges, run without it and say so in proof.md).
- Environment, built explicitly (never inherited wholesale; an app opened from Finder does not get the Terminal's PATH): HOME; PATH = `<resources>/bin` (packaged only) plus /usr/bin:/bin:/usr/sbin:/sbin (in dev also /usr/local/bin and /opt/homebrew/bin so a system ffmpeg is found); ANYSCRIBE_APP=1; PYTHONUSERBASE=~/.anyscribe/runtime and PIP_USER=1 (add-ons folder; create `~/.anyscribe/runtime/lib/python3.13/site-packages` before spawning or Python ignores it); ANYSCRIBE_ELECTRON=process.execPath (yt-dlp's Node, packaged only); LANG=en_US.UTF-8; PYTHONUNBUFFERED=1; TMPDIR.
- Port: fixed 8470. If `~/.anyscribe/desktop.json` (today's desktop mode) records that same port, use 8471. If the chosen port is already taken, do not connect to it and do not stop whatever holds it: show "Couldn't start" with that reason.
- Readiness: poll GET /api/health every 100 ms for up to 60 s.
- Logs: the engine's stdout and stderr, plus one shell line per start, stop, crash and restart, append to `~/.anyscribe/logs/app.log`; if it is over 5 MB at launch, keep the last 1 MB.

## Windows
- Start window: a local HTML page in desktop/ (never served by the engine): icon, name, a thin "Starting" bar. Failure states as in mockup section 2: a known reason (the engine exited early: show the last stderr lines; or the port is taken) and "no reason reported" (no answer in 60 s). Buttons: Try again, Copy details (copies the last 40 log lines), Troubleshooting guide (opens https://github.com/rishmadaan/anyscribe/blob/main/docs/user/troubleshooting.md in the browser).
- Main window: loads http://127.0.0.1:<N>/ once healthy. On macOS, `titleBarStyle: "hiddenInset"`. Closing hides it (the app keeps running). A second launch of the app focuses the window (single-instance lock). Opening the app when the window is hidden shows it.
- Launched at login: no window, menu bar only.

## Menu bar (direction A) and the Dock
- Poll GET /api/jobs every 2 s (2a adds it; until then treat 404 as "no jobs"). Menu states exactly as mockup section 6, direction A: Ready; "Transcribing · N running, M waiting" with one row per job (title, or the URL until the title is known; stage word: Downloading, Transcribing, Saving, Waiting); "Finished while the window was closed" (jobs that finished while the window was hidden, with Saved or Failed, kept until the window is next shown); "Engine stopped · couldn't restart" with Restart engine. Items: Open anyscribe (Cmd O), Start at login (checkbox), Quit anyscribe (Cmd Q).
- Icon: today's tray glyph (`src/anyscribe/assets/tray-icon.png`, a template image) plus variants with a small dot: amber while working, red after a failed job or a stopped engine. Generate the variants once, check them in under desktop/assets/, and say how in proof.md. The menu always says the state in words.
- Dock mode setting, stored in Electron's userData as JSON: "menubar" (default: Dock icon only while the window is shown), "both" (Dock and menu bar always), "dock" (no menu bar icon; the Dock icon's menu carries the status line and Start at login). Applies immediately.
- Start at login: `app.setLoginItemSettings`, off by default, launched hidden.

## Quitting (mockup section 7)
On every quit path (Cmd Q, the menu, logout or shutdown): read /api/jobs. If any job is pending or running, show the native question: title "Transcriptions are still running"; message "2 are running and 1 is waiting. Quit when they finish, or stop them now? To finish a stopped one later, transcribe it again." (counts from the list); buttons Quit When Done (default), Stop and Quit, Cancel. Quit When Done hides the window, and the menu's first line reads "Quitting when these finish", with the job rows, then Don't quit and Stop and quit now; when no job is left, quit. During logout, Quit When Done cancels the logout. Stop and Quit: quit straight away; the engine's stop ends every job (round 4: no per-job POST /api/jobs/<id>/cancel; see "Round 4 design").
Stopping the engine: close its stdin and send SIGTERM to its process group, then SIGKILL the group if it has not exited within 10 s (never by matching names). Round 3: no POST /api/shutdown; see "Round 3 design" below.

## Engine crashes
An unexpected exit restarts the engine automatically. Three exits within 60 s: stop retrying, set the menu to "Engine stopped · couldn't restart", and report it through the bridge. Restart engine is refused while any job is pending or running (the bridge returns a reason). After a restart the window reloads the dashboard. The banner itself (mockup section 10) is slice 2c.

## The bridge (preload, `window.anyscribeDesktop`), the contract slice 2c builds on
- `version`, `platform`
- `getSettings()` gives `{dockMode, startAtLogin}`; `setDockMode(mode)`; `setStartAtLogin(on)`
- `engineStatus()` gives `{state: "starting"|"running"|"restarting"|"stopped", port, lastExit: {code, signal, reason}|null}`; `onEngineStatus(callback)` returns an unsubscribe function; `restartEngine()` gives `{ok, reason}`
- `openLogFolder()`; `revealInFinder(path)`; `pathForFile(file)` (webUtils.getPathForFile, so a dropped or picked file is read in place instead of uploaded)
Write this contract into desktop/README.md.

## Tests and the done bar
- Unit tests (`node --test`) for the pure logic: port choice (including the desktop.json clash and a taken port), the environment builder (PATH never includes the caller's PATH in packaged mode), the job-list-to-menu mapping for every state above, quit-question wording and counts, the crash-retry window (third exit in 60 s stops).
- One end-to-end run on this Linux machine against the real engine (ANYSCRIBE_DEV_PYTHON, a throwaway HOME, windows created with show: false so nothing appears on the owner's screen): the engine starts, the dashboard loads, closing the window keeps the engine up, quit stops the engine (its pid gone), and a force-killed shell does not leave the engine running once 2a's flag is in (until then, record that gap).
- Mutation tests for the guards: the taken-port refusal, the Restart-engine refusal during jobs, the three-crashes stop, the quit question when jobs exist. Each seen failing with the guard removed, quoting the assertion.
- Docs: desktop/README.md (how to run it in dev, the bridge contract), docs/building/architecture.md "Mac app shell" section, a journal entry docs/building/journal/2026-11-20-mac-app-shell.md and its _index.md row.

## Left to the builder
File layout inside desktop/, module boundaries, how the start window gets its state, how icon variants are generated.

## Round 3 design (the lead's choice after the diagnosis; binding)

The supervisor decides from the child process, not from remembered facts.

1. One current run. `this.run` is set synchronously when start or restart is accepted: `{child, cancelled, restartRequested, ready, failure}`. Only the child's exit or error event (or a failure before spawn) clears it. No queue, no generation counter, no `verified`, no `_enqueue`, no `_kill`.
2. One gate. Every late continuation (port check, health reply, readiness timeout, jobs reply inside restart) begins `if (run !== this.run || run.cancelled) return`. The exit handler clears `this.run` first, so a late "ours" is dropped (A1).
3. One exit handler decides what happens next, and on every unexpected exit (before or after ready) first kills the dead run's process group once, ignoring "no such process" (Sol's engine round 3 R2): failure set (port taken, timeout): stopped with that reason; cancelled: stopped, or relaunch if a restart asked; not ready: exited early; ready: crash count, then relaunch or stop after three in 60 s.
4. One stop. Mark the run cancelled, `stdin.end()`, SIGTERM to the group, arm a timer that SIGKILLs the group if no exit arrives in 10 s; the exit event clears the timer. `stopForQuit` is the same plus a permanent "never spawn again" flag. No HTTP /api/shutdown anywhere (A2). Readiness still requires /api/health's pid to equal the child's pid.
5. Restart: refuse unless the list is known and idle (as now); read jobs, then pass the gate; set "restarting" at once; a second restart while one is pending is refused with a reason, not queued (A4).
6. Log: before each launch, probe with an empty append; `write()` always tries and clears its error on success; a write failure mid-run keeps the engine running and keeps the in-memory tail; a failed probe is "Can't write the log file: <error>", and Try again re-probes (A3, G6).
7. Seams: the supervisor's constructor takes `spawn`, `health`, `jobs` and `killGroup`, defaulting to the real ones; tests use fakes and fake pids never reach the real `process.kill`.

Tests (each mutation-tested), plus an invariant check after every supervisor test (at most one live child; "running" means the child has not exited):
- A1: hold the health reply, emit exit, release "ours": no "running" status is ever emitted; failure kind is exited.
- A4: hold jobs(), call restart(), then stop() (and a stopForQuit() variant), release []: spawn count 1, restart refused, state stopped.
- A2: spy on fetch during stop: zero requests; stdin ended; SIGTERM to the group; SIGKILL to the group after the wait when no exit comes. Remove the shutdown route from the fake engine.
- A3: an existing app.log at 0444: no spawn, the failure reason shown; after chmod back, Try again starts the engine and the line is in the file.
- R2 (engine round 3): an engine that dies before readiness while holding a helper leaves no helper (by pid).
- Keep the e2e's log lines verbatim ("engine ready", "quitting: stopping the engine", "stopped unexpectedly").

Fit items in the same round: G1 sort failed jobs first, then newest, in the finished rows; G2 document in README and journal that any question during a logout cancels it (after Stop and Quit, log out again); G3 cap waiting and quitting rows at 5 plus "and N more" (running rows always shown); G4 the unknown-list question uses the approved three buttons (Quit When Done default, Stop and Quit, Cancel) with the message "anyscribe couldn't check which transcriptions are running. Quit when they finish, or stop them now? To finish a stopped one later, transcribe it again.", and the menu header gains " · not answering" after three failed reads in a row; G5 fix the journal's stale names. Update the README and spec sentences that name /api/shutdown.

## Round 4 design (the lead's choice after the third diagnosis; binding)

- S3-A1: in engine.js `stop()`, revoke a pending relaunch before cancelling (`if (this.run) this.run.restartRequested = false;`). Test with the seams: start; restart() with signals ignored; wait for SIGTERM; stop(); emit the old child's exit; assert restart returned ok false, one child only, run null, state stopped. Mutation: remove the line (two children, state running).
- G7 and G10: "Stop and Quit" (both the quit question's button and the menu's "Stop and quit now") quits straight away through the normal quit path; no job list read, no per-job cancel requests. Delete engine.cancelJob, the read before it, and main.js's dead `choice === 'quit'` branch. The engine's stop (stdin end plus SIGTERM to its group) ends every job. Test: an e2e step (or a seam test if the e2e cannot hold replies) with a fake engine that never answers /api/jobs and has active jobs in the last list: Stop and Quit exits within 1 s, the engine's pid is gone, and the fake engine received no POST. Mutation: put the cancel loop back.
- G8: label the cap lines "and N more waiting" and "and N more finished".
- G9: when the engine is idle and not answering, the header reads "anyscribe · Not answering" (replacing "Ready"); keep the " · not answering" suffix for Transcribing and Quitting.
