# Proof: phase 2b, the Mac app shell (round 0)

Branch `feat/mac-app-shell` in `~/labs/projects/anyscribe-wt/mac-shell`,
built on 7ab1539 (checked before editing). Commits, oldest first:

| Commit | Step |
|--------|------|
| bb72bcd | the review packet |
| 3cae208 | engine supervisor and menu/quit logic, unit tests, fake engine |
| c47e78c | Electron shell (windows, menu bar, quit, bridge), start window, icons, e2e; fix for a quit that hung |
| 24774f9 | tests stop their engines; a stop during start aborts the start |
| e342030 | docs (architecture, journal, index, desktop/README) |
| 6115212 | a destroyed dashboard window still counts as closed for the menu |
| (this file) | proof |

Nothing outside `desktop/`, `docs/building/`, `.gitignore` and this packet
changed. `src/`, `ui/`, the installers, `pyproject.toml`, CHANGELOG and BACKLOG
are untouched. npm packages were installed only in `desktop/` (Electron
44.9.3, exact).

## Spec sections

| Section | Built | Where |
|---------|-------|-------|
| Stack | Yes. Electron 44.9.3 exact, no other dependencies, plain JS + preload, `start` and `test` scripts (plus `e2e` and `make-icons`). contextIsolation, nodeIntegration off, sandbox on for both windows. Links leaving 127.0.0.1 open in the browser (`setWindowOpenHandler` + `will-navigate`, on every webContents; http/https only) | `desktop/package.json`, `src/main.js` |
| Starting the engine | Yes. One `resolvePython`; command with `--watch-stdin` and a held stdin pipe; explicit environment; port 8470/8471 with the desktop.json clash; taken port refused; health poll 100 ms / 60 s; `app.log` with `[app]` lines and the 5 MB / 1 MB trim. Without 2a, the engine rejects the flag (exit 2) and the app restarts it without the flag and logs it | `src/logic.js`, `src/engine.js` |
| Windows | Yes. Local start window with the three states of mockup section 2 and its three buttons; dashboard window with `hiddenInset` on macOS; close hides; single-instance lock focuses; reopening shows; login launch opens no window | `src/start.html`, `start.js`, `start-preload.js`, `src/main.js` |
| Menu bar (A) and Dock | Yes. `/api/jobs` every 2 s (404 = no jobs); Ready, Transcribing with rows, Finished while closed, Engine stopped with Restart engine; Open (Cmd O), Start at login, Quit (Cmd Q); icon with amber/red dot variants; dock modes menubar/both/dock stored in userData, applied immediately; login item off by default (round 1, F4: `openAsHidden` does not exist in Electron 44 and was dropped; a login launch relies on `wasOpenedAtLogin`, unchecked on macOS 13+) | `src/logic.js` `menuModel`, `src/main.js`, `assets/` |
| Quitting | Yes. Every quit path goes through `before-quit`; fresh `/api/jobs`; the native question with the exact wording and counts; Quit When Done (hides, menu "Quitting when these finish" with rows, Don't quit, Stop and quit now, quits when none left); Stop and Quit cancels each then stops; stop = close stdin, POST /api/shutdown, 10 s, kill own pid | `src/logic.js` `quitQuestion`/`decideQuit`, `src/main.js`, `src/engine.js` `stop` |
| Engine crashes | Yes. Auto-restart, three exits in 60 s stop retrying, menu "Engine stopped · couldn't restart", reported through the bridge, Restart engine refused during jobs, dashboard reloads after a restart | `src/engine.js`, `src/main.js` |
| The bridge | Yes, every member, in `desktop/README.md`. One addition: `engineStatus()` also carries `stoppedRestarting` (see "spec issues") | `src/preload.js`, `src/main.js` |
| Tests and done bar | Yes: unit tests, e2e, mutation tests, docs | below |

Icons: `npm run make-icons` (`desktop/scripts/make-icons.js`) runs Electron
headless, loads `src/anyscribe/assets/tray-icon.png`, resizes it to 22 and 44 px,
and writes `trayTemplate.png` (+@2x, the plain glyph, a macOS template image)
and `tray-<working|alert>-<light|dark>.png` (+@2x): the glyph with a ring
cleared at the bottom right and an amber (#F0A050) or red (#F06060) dot,
anti-aliased by 4x4 supersampling. Coloured dots cannot be template images
(macOS makes those monochrome), so each dot variant has a black glyph (light
menu bar) and a white one (dark), picked by `nativeTheme.shouldUseDarkColors`.
Also `app-icon.png` at 256 px for the start window. I looked at the 44 px
amber and red variants: glyph plus dot, as intended.

## Unit tests

`cd desktop && npm test`: 27 tests, 27 pass, 0 fail (about 6 s). Covered: port
choice (no manifest, manifest 8470 to 8471, manifest elsewhere, a taken port
via a real listener), python resolution, the environment builder (packaged PATH
equals `<resources>/bin:/usr/bin:/bin:/usr/sbin:/sbin` with a caller PATH set
that never appears; the full packaged env object; dev PATH), engine args, the
menu for Ready / Transcribing (titles, shortened links, every stage word) /
Finished while closed (seconds and ISO timestamps, cancelled and earlier jobs
excluded, back to Ready once shown, no red dot when all saved) / Engine stopped /
Quitting when these finish, the quit question's wording and counts (2 running
1 waiting, 1 running, 2 waiting, none), `decideQuit`, the restart refusal, the
crash window (third exit inside 60 s, and outside), the start-window sentences,
the log trim. Supervisor tests against `test/fake-engine.js`: start/stop by
pid, taken port, rolled-forward engine, early exit with stderr and log lines,
60 s timeout (shortened) with the child killed, the `--watch-stdin` fallback,
stdin close alone stops a `--watch-stdin` engine, three crashes, restart
refused during a running job, restart with no jobs (and a 404 jobs list),
kill-by-pid when shutdown is ignored.

## Mutation tests (each guard removed, its test run, restored, re-run)

Script: a Python file that swaps one exact line, runs `node --test
--test-name-pattern <test>`, then `git checkout -- <file>` and re-runs.

| Guard | Mutation | Failing assertion with the guard removed | Restored |
|-------|----------|------------------------------------------|----------|
| Taken port refused (pre-check) | delete `if (taken) return this._fail('port', ...)` in `engine.js` | `AssertionError: Expected values to be strictly equal: actual: 'exited', expected: 'port'` (the fake was spawned onto the taken port) | pass |
| Engine that rolled forward is not attached to | `if (announced && Number(announced[1]) !== port)` to `if (false)` | `AssertionError: Expected values to be strictly equal: actual: true, expected: false` (`start()` returned running, attached to the other server) | pass |
| Restart engine refused during jobs | delete `if (refusal) return { ok: false, reason: refusal };` | `Expected values to be strictly deep-equal: + actual - expected / + ok: true, + reason: null / - ok: false, - reason: 'Wait for transcriptions to finish before restarting the engine.'` | pass |
| Three crashes stop the retries (supervisor) | `if (this.crashes.record(...))` to always false | `Error: timed out after 10000 ms` (waiting for `stoppedRestarting`; it kept restarting) | pass |
| Three crashes stop the retries (window) | `CrashWindow.record` returns false | `AssertionError: Expected values to be strictly equal: actual: false, expected: true` | pass |
| Quit question when jobs exist | `decideQuit`: `if (!question) return 'quit';` to `return 'quit';` | `AssertionError: Expected values to be strictly equal: actual: 'quit', expected: 'whenDone'` | pass |
| Quit with no engine running exits (the bug fix below) | `setImmediate(() => app.quit())` to `app.quit()` in `main.js`, run the e2e | `FAIL AssertionError: the app quits with its engine never started` (actual: null exit code after 10 s) | e2e all pass |

Each restored run passed. The first mutation run hung on the rolled-forward
mutant because a failing test left its fake engine running; I stopped that
fake by its pid, added an `afterEach` that stops every engine a test made, and
re-ran all mutants (results above).

## End-to-end run (this Linux machine, real engine, nothing on screen)

`env -i HOME=$HOME PATH=/usr/bin:/bin ANYSCRIBE_DEV_PYTHON=<python> node test/e2e.js`.
Electron runs with no display (`--ozone-platform=headless`) and no session
bus, a throwaway HOME under `desktop/test/.tmp/`, and "dock" mode (no tray: see
below). It observes pages through the renderer DevTools port, and presses the
window's close button and the Quit item through the main process inspector
(`BrowserWindow.close()`, `app.quit()`), the same calls those controls make.

Against main's engine (`~/labs/projects/anyscribe/.venv/bin/python`, 0.19.0, no `--watch-stdin`):

```
PASS engine starts and the dashboard loads (engine pid 1737026, page http://127.0.0.1:8470/, 399 ms after ready)
PASS the bridge answers in the dashboard, no Node in the page (version 0.19.0, status {"state":"running","port":8470,"lastExit":null,"stoppedRestarting":false})
PASS closing the window hides it; app and engine keep running
PASS opening the app again shows the hidden window (single instance) (second launch exit code 0)
PASS a crashed engine is restarted and the dashboard reloads (pid 1737026 killed, new pid 1737745)
PASS quitting the app stops the engine (pid 1737745 gone, app exit 0)
PASS a login launch starts the engine with no window (engine pid 1738152)   [round 1, F7: this was a --hidden launch, not a macOS login launch]
GAP force-killed app left engine pid 1738152 running (--watch-stdin in use: false); stopped it by that pid
PASS a taken port shows "couldn't start" and leaves the holder alone (Its engine couldn't start: another program is using port 8470. Your transcripts and settings are safe.)
PASS quitting from "couldn't start" exits the app (exit 0)
```

The GAP is the expected one until 2a merges. Slice 2a's branch
(`feat/mac-app-engine` at 54f0d0b) already has the flag, so I also ran the e2e
against it, read-only: a wrapper script sets
`PYTHONPATH=~/labs/projects/anyscribe-wt/mac-engine/src` and execs the
same venv python (confirmed `anyscribe.__file__` resolves to that worktree).
All ten steps pass, including:

```
PASS a force-killed app takes its engine with it (--watch-stdin in use: true)
```

Its `[app]` log lines (timestamps cut):

```
[app] engine started (pid 1750902, port 8470)
[app] engine ready (pid 1750902, port 8470)
[app] engine stopped unexpectedly (code null, signal SIGKILL)
[app] restarting the engine
[app] engine started (pid 1751709, port 8470)
[app] engine ready (pid 1751709, port 8470)
[app] stopping the engine (pid 1751709)
[app] engine stopped (pid 1751709)
[app] engine started (pid 1751835, port 8470)
[app] engine ready (pid 1751835, port 8470)
[app] engine not started: port (another program is using port 8470)
```

After every run I checked that no app, engine or fake engine was left
running. The 2a `/api/jobs` returns a bare list of
`{job_id, url, status, stage, title, error, file_path, created_at, completed_at}`
with float-second timestamps; the shell reads a bare list or `{jobs: [...]}`,
seconds or ISO.

## Bug found and fixed

Quitting while no engine was running (for example from "couldn't start")
closed every window and left the app running invisibly. The quit decision
finished inside the microtasks of Electron's own `before-quit` emit, so
`app.quit()` re-entered it; when the outer, prevented handler returned,
Electron reset its quitting state, and with no windows left the app stayed up.
Fixed with `setImmediate(() => app.quit())`; the e2e step above fails without it.

## What I think the spec got wrong or left open

1. **The bridge cannot say "stopped after three crashes".** `engineStatus()`
   per the spec is `{state, port, lastExit}`, but the 2c banner ("It stopped 3
   times in a minute...") needs to tell that apart from any other stop. I added
   `stoppedRestarting: boolean`. Please confirm or rename.
2. **`anyscribe ui` rolls forward past a busy port.** Checking the port first
   leaves a race; the shell also refuses an engine whose start line names a
   different port. A cleaner fix is an engine flag that fails instead of
   rolling forward (would belong to 2a).
3. **`hiddenInset` with today's dashboard.** The dashboard has no drag region,
   so on a Mac the window cannot be dragged by its top edge, and the traffic
   lights sit over the sidebar's top-left. 2c needs a drag strip and top
   padding (or the shell injects CSS). Not built here.
4. **The dashboard's own Shutdown button.** In the app it stops the engine,
   which the shell treats as a crash and restarts, and its `window.close()`
   destroys the window (handled: the next Open makes a new one). 2c should
   hide that button when running in the app.
5. **PYTHONUSERBASE/PIP_USER in dev.** Set in both modes as written. In a dev
   venv user site-packages are off, so they do nothing there; the
   `python3.13` folder matches only the packaged Python.
6. **Menu row layout.** Electron menus cannot right-align the stage the way the
   mockup draws it; rows read "Founder interview, part 2 · Transcribing".
   States the mockup does not draw got my wording: "anyscribe · Starting",
   "anyscribe · Restarting the engine", "anyscribe · Couldn't start".
7. **"Couldn't start" reason.** The mockup paraphrases the error ("it can't
   write to ~/.anyscribe/config.yaml"). The shell cannot paraphrase arbitrary
   errors, so the sentence is "Its engine stopped before it was ready." and the
   raw last lines are in the log box under it.
8. **An unreachable engine reads as "no jobs"** for the quit question and
   Restart engine (it cannot be running jobs the user could keep).

## What I could not check

- Everything Mac-only: `hiddenInset`, template-image rendering in a real menu
  bar, Dock show/hide per mode, the Dock menu, `setLoginItemSettings` and
  `wasOpenedAtLogin`, whether `activate` fires at a login launch (which would
  show the window), and logout. On logout Electron emits `before-quit`; the
  shell always prevents it first and decides asynchronously, so whether a
  logout with no jobs still completes (rather than being cancelled) must be
  checked on a Mac.
- The tray menu end to end on any desktop. A Linux tray needs the desktop
  session's bus (it shows in the panel) or a display, so the e2e uses dock
  mode; the menu's content is unit-tested, the Electron menu building is not.
- The quit question, Quit When Done and Stop and Quit with real jobs: starting
  a job needs a configured provider. The decision is unit-tested and
  mutation-tested; the dialog and job cancelling were not run.
- How the start window looks: a headless window screenshot comes back blank,
  so only its text and icon load were checked, not its layout against the mockup.
- Owner's screen exposure: before I moved to a clean environment, an early
  probe (under a second) and one manual run (about 20 s) were started with the
  session bus reachable and no display. No window could appear, but an
  anyscribe tray glyph may have shown briefly in the Zorin panel. Every later
  run had no display and no session bus.

## Round 1 fixes (one entry per finding)

Branch head before: c3327f7. Every entry: change | ran | saw. Commits are on
`feat/mac-app-shell`, one per finding or per group the fix plan grouped.
Mutation runs: a script swaps one exact line, runs the named test in its own
process session (killed as a group on timeout), restores the file with
`git checkout`, and re-runs. All mutants below ran on committed code.

Slice 2a used for every e2e: `feat/mac-app-engine` at **61de6ac**, exported
read-only with `git archive 61de6ac src` into a scratch folder and put on
`PYTHONPATH` in front of the main checkout's venv Python (that worktree had an
uncommitted `web/app.py` edit in progress, so I ran the exact commit, not its
working tree). `/api/health` there returns `"pid"`, so the C2 check ran against
the real contract, not only the fake.

| Id | Change | Ran | Saw |
|----|--------|-----|-----|
| C1 | `engine.jobs()` validates the body (`logic.validJobs`: an array of objects with string `job_id` and `status`) and returns **null** when the list cannot be known (timeout, error status, bad JSON, wrong shape); `[]` only when no engine runs. The poll keeps the last list and a `jobsKnown` flag. Quit When Done quits only on a known list with nothing active (`quitWhenDoneReady`); Restart engine is refused on unknown ("anyscribe couldn't check for running transcriptions; try again in a moment"). Commit cda7898 | `npm test`: engine test feeds the fake a 3 s delay, HTTP 500, 404, `not json`, `{"jobs":{}}`, `[null]`; logic tests for validJobs, quitDecision, quitWhenDoneReady, restartRefusal(null) | Each unknown cause gives null, a real `[]` stays `[]`. Mutants: jobs() returning `[]` on failure: `AssertionError: timeout / actual: [], expected: null`; unknown guard removed from quitDecision: `TypeError: Cannot read properties of null (reading 'box')`; `known &&` removed from Quit When Done: `actual: true, expected: false`; restart unknown guard removed: `+ ok: true, + reason: null / - ok: false`. All restored: pass |
| F2 | Same change as C1 (the slow-engine case is the 3 s timeout case) | as C1 | as C1 |
| F1 | `before-quit` decides at once from the last poll (`logic.quitDecision`): engine not running, or a known list with nothing active, returns null and the quit is **not prevented**; `will-quit` then calls `engine.stopForQuit()` (close stdin, SIGTERM the engine's group). Known active jobs: the approved question. Unknown: "anyscribe couldn't check for running transcriptions" / "Quitting now stops any transcription that is still running." / Quit Anyway, Cancel (Cancel default). Commit cda7898 | logic test "quit: decided at once from the last poll"; engine test "stopForQuit"; e2e steps "quitting the app stops the engine" and "quitting from couldn't start exits the app" | Known-idle returns null; mutant that always prevents: `AssertionError: known and idle: the quit is not prevented`. e2e: quit with no jobs, engine pid gone, app exit 0. Logout itself not checkable on Linux (below) |
| C4 | Start, stop and restart run through one promise queue (`_enqueue`); restart is enqueued at call time, so two restarts run one after the other; `_stopNow` clears `this.child` only if it is the child it stopped. Commit 2718dda | engine test: two `restart()` calls at once, then every pid ever logged as started is checked | 3 engines started (first + two restarts), only the last is alive and it is `engine.child`. Queue mutant (operations run at once): the test fails (`two restarts at once` ✖; the run then hangs on the extra engines and is stopped by its group). "Only its own child" mutant: **survives** (equivalent under the queue; see "plan" below) |
| F3 | A generation number: `stop()` bumps it the moment it is called; `_launch` checks it on entry and after the port check, `_waitReady` after every await, crash restarts are enqueued with the generation they saw. Commit 2718dda | engine tests: stop when the state turns "restarting" in a crash loop; stop when the state turns "starting" (during the port check), asserting the port was free | No pid alive afterwards, one engine ever started, nothing spawned during the port check. Mutants: stale check after the port check removed: `+ [ 1154535 ]` (an engine spawned after the stop); stale check on `_launch` entry removed: `actual: 'restarting', expected: 'stopped'`. Restored: pass |
| C2 | Readiness needs `/api/health` to answer `app: "anyscribe"` **and** `pid` equal to the spawned child's pid; any other answer is "another program is using port N" (our child is killed by its group, the other server gets nothing). `POST /api/shutdown` goes only to the child whose pid was verified. The stdout port-announcement check is removed (2a no longer rolls forward in the app). Commit 2718dda | engine tests: a fake answering with another pid; a stop during start while a separate test server holds 8470 and records requests; e2e against 2a 61de6ac (real pid) | Impostor: failure `port`, no "engine ready", its process gone. The recording server got no `POST /api/shutdown`. e2e passes with 2a's real pid. Mutants: pid check returns 'ours': `actual: true, expected: false` (start() returned running); shutdown sent to anyone: `AssertionError: GET /api/health, GET /api/health, POST /api/shutdown`. Restored: pass |
| C3 | One rule (`logic.navigation`) for `setWindowOpenHandler`, `will-frame-navigate` (main frame and subframes) and `will-redirect`: the engine's origin and the start page load; `about:blank`/`about:srcdoc` only in subframes; an outside top-level http(s) page opens in the browser; anything else (outside frames, other schemes) is blocked. Commit 0dc1bef | logic test of the rule; e2e phase 9 against the fake engine (which serves a page and `/redirect-out` to `http://example.invalid/away`), with a stand-in `xdg-open` first on PATH that records URLs | Outside iframe stays `about:blank`; a frame sent to `/redirect-out` stays `about:blank`; neither is opened; top-level `/redirect-out` stays in the app and records `http://example.invalid/away`; an outside popup opens no window and records `http://example.invalid/popup`; a same-origin popup opens a window. Mutants: rule without `isMainFrame`: `an outside iframe is blocked, not opened / actual: 'outside', expected: 'block'`; `will-frame-navigate` listener removed (e2e): `FAIL AssertionError: an outside iframe never loads`; `will-redirect` listener removed (e2e): `FAIL AssertionError: a frame redirected out never loads` |
| C6 | `resolvePython` resolves a dev path containing a `/` against `process.cwd()` at startup (a bare name stays a PATH lookup); README examples use `$(pwd)/../.venv/bin/python`. Commit fa07379 | logic test: `../.venv/bin/python` from `/repo/desktop` | Gives `/repo/.venv/bin/python`. Mutant (returned unchanged): `+ '../.venv/bin/python' - '/repo/.venv/bin/python'`. Restored: pass |
| C7 | `logic.rememberFinished` keeps jobs that finished (saved or failed) after the window was hidden, by `job_id`, until the window is shown; `menuModel` takes that list (`finished`) instead of filtering the current poll. Commit 0e07fa2 | logic test: poll 1 has one failure; poll 2 has 50 later completions and no longer the failure | Menu still red, "anyscribe · 50 saved, 1 failed", a Failed row. Mutant (memory reset each poll): `actual: 'plain', expected: 'alert'`. Restored: pass. I used the finish time (`completed_at` after the window closed) rather than "seen go from active to finished", so a job that started and finished between two polls is kept too |
| C8 | e2e step 7 asserts the engine follows the force-killed app (always, since the flag is always passed); the GAP branch is gone; cleanup stays in `finally`. Commit 5bc9e80 | e2e against 2a 61de6ac; mutant run with `--watch-stdin` removed from the engine args | Passes: "a force-killed app takes its engine with it (pid 1297312 gone)". Mutant: `FAIL Error: timed out waiting for engine pid 1340451 to follow the force-killed app` |
| C9 | `AppLog` never throws: setup and each write are caught, `error` holds the reason, the in-memory tail (Copy details) always works. `_launch` shows "Can't write the log file: <error>. Your transcripts and settings are safe." and starts no engine; folder creation and `spawn` are caught into the failure state; settings writes are caught and logged. Commit e7e46df | engine test: `.anyscribe/logs` is a regular file | `log.error` matches EEXIST/ENOTDIR, the tail still has the line, start() fails with kind `log`, no child. Mutants: setup try removed: `Error: EEXIST: file already exists, mkdir '…/.anyscribe/logs'` thrown out of the constructor; log check removed: `actual: 'port', expected: 'log'` (it went on to start). Restored: pass |
| F4 | `openAsHidden` dropped; `startAtLogin` is no longer stored: the menu tick and `getSettings().startAtLogin` read `app.getLoginItemSettings()` (`status === 'enabled'` where `status` exists, else `openAtLogin`); `setStartAtLogin` only calls `setLoginItemSettings({openAtLogin})`. `wasOpenedAtLogin` still decides a windowless launch. README wording fixed; round 0 proof line annotated. Commit 7eb0b1f | e2e bridge check (`getSettings()` gives `{dockMode: 'dock', startAtLogin: false}` from the system on Linux) | Passes. **Unverified on a Mac:** whether `wasOpenedAtLogin` is true for a login launch on macOS 13 and later, and the `requires-approval` reading; no mutation (Electron-only, no test can see it here) |
| F5 | The dashboard window has the default title bar (comment: hiddenInset returns with 2c's drag area); the start window keeps hiddenInset. Commit 0d451af | e2e (window loads); read the diff | Not visible on Linux; check on the Mac |
| F6 | `logic.menuLayout`: separator before "Open anyscribe" only after job rows, none before "Restart engine" or "Stop and quit now"; header is `type: 'header'` on macOS 14+ (Darwin 23+), a greyed item otherwise; separators left first or last (the Dock menu drops Open and Quit) are removed. Commit 86d47cd | logic test of the four layouts | Ready: `header open separator startAtLogin separator quit`; Transcribing: `header row row separator open …`; Engine stopped: `header restartEngine open …`; Quitting: `header row separator dontQuit stopAndQuit`. Mutant (separator always): `+ 'header separator open …'`. Restored: pass. Native look unchecked |
| F7 | e2e step renamed "a --hidden launch starts the engine with no window"; the round 0 proof line is annotated; the real login path is listed below. Commit 5bc9e80 | e2e | "PASS a --hidden launch starts the engine with no window" |
| F8 | No code: journal "Left for later" now says phase 3 stamps the app version from `pyproject.toml`. Commit bb4008a | read the journal | Listed |
| F9 | The no-flag retry and its shortcut comment are removed; `engineArgs(port)` always ends with `--watch-stdin`; README says an engine without it does not start. Commit 8b35457 | `npm test`, e2e against 2a | Pass; the C8 mutant above is this flag removed |
| F10 | The add-ons folder is created only when `packaged`. Commit 8b35457 | engine test: dev start leaves no `…/runtime/lib/python3.13/site-packages`; packaged start creates it | Pass. Mutant (`if (true)`): `actual: true, expected: false`. Restored: pass |
| F11 | `app.focus({ steal: true })` before the quit question; it is attached to the dashboard window when that is visible. Commit c4b2d01 | read the diff | Unverified: needs a Mac, and real jobs to make the question appear |
| F12 | No code: journal "Left for later" lists a small application menu for phase 3. Commit bb4008a | read the journal | Listed |
| S-design-C | The engine is spawned `detached: true` (its own process group from birth, not unref'd, stdin pipe kept); every kill (`_kill` SIGKILL, `stopForQuit` SIGTERM) signals the group, `process.kill(-pid, sig)`, falling back to the pid. Commit 27530f6 | engine test: fake engine that ignores stdin and SIGTERM and starts a helper that ignores SIGTERM; `stop()`; helper pid checked, killed by pid in `finally` if alive | Engine and helper both gone. Mutant (kill the pid only): `AssertionError: its helper (pid 1285278) is gone too / actual: true, expected: false`. Restored: pass. One lost-work note: my first mutation run restored `engine.js` with `git checkout` while this change was still uncommitted, which wiped it; I re-applied it, committed, and re-ran the mutant (result above) |
| S-open-1 | Removed the "stop clears only its own child" check: `_stopNow` now sets `this.child = null` unconditionally. Under the queue nothing else can set `this.child` while a stop runs, so its mutant survived (exit 0, round 1 table above): an equivalent mutant, removed as the rule says. Commit 045558c | `npm test` | 41 of 41 pass with it gone (same as with it) |
| S-open-3 | `_crashed` now signals the dead engine's process group once, `process.kill(-pid, 'SIGKILL')`, ignoring ESRCH ("no such process") and logging any other error, so a helper the engine left behind goes with it before the restart. Commit b3d2c88 | engine test: fake engine in crash mode holding a helper that ignores SIGTERM; three crashes; every helper pid checked, killed by pid in `finally` if alive | 3 helpers, none alive after the crashes. Mutant (group kill removed): `AssertionError: no helper outlives its crashed engine / + [ 1422477, 1422584, …` (the helpers outlived their engines). Restored: pass |
| S-open-4 | Finished-while-closed rows show the 5 newest (by finish time), then one disabled line "and N more"; the header still counts all of them. Rows are now newest first. Commit 4272f26 | logic test: 7 jobs finished while hidden (1 failed, 6 saved) | Header "anyscribe · 6 saved, 1 failed", red dot, rows Job 6 to Job 2 then "and 2 more". Mutant (cap at Infinity): `+ label: 'Job 1', stage: 'Saved' / - label: 'and 2 more'`. Restored: pass |

### Results

- `npm test`: 41 tests, 41 pass, 0 fail (about 10 s).
- e2e against 2a **61de6ac** (exact commit): all 11 steps pass: dashboard loads (440 ms after ready), bridge, close hides, reopen shows, crash restart and reload, quit stops the engine, a --hidden launch, force-kill takes the engine, taken port, quit from couldn't start, frames/redirects/popups. An earlier run against 07b6e40 (after C3, before F4 and the group kill) also passed all 11. No process was left after any run.
- Leftovers during the work: one mutation run (queue mutant) timed out and left a test runner and one fake engine on port 8470, which made the next mutants' "restored" checks fail. I stopped the fake by its pid (the runner exited with it), made the mutation script run each test in its own session and kill that group on a timeout, added a "the port was free" assertion to the port-check test (that mutant had passed vacuously while 8470 was taken), and re-ran every affected mutant.

### Where I think the plan is wrong or open

1. (Resolved by S-open-1: removed.) **"stop() only clears the child it stopped" cannot be told apart by any test.** With the queue, nothing else can set `this.child` while `_stopNow` runs, so the mutant that clears it unconditionally survives (exit 0). Kept because the plan asks for it; by the house rule on equivalent mutants it could be removed. Lead's call.
2. **Quit with a job under 2 s old.** The synchronous decision uses a poll up to 2 s old, so a job submitted in that window is not asked about (the plan accepts this with C5 declined; README says so).
3. (Resolved by S-open-3.) **Crash leftovers.** The group kill runs on stop and quit. After an unexpected engine exit the shell does not signal the dead engine's group, so a helper the engine left behind would keep running beside the restarted engine (2a's own exit door is meant to cover that).
4. (Resolved by S-open-4.) **C7 menu length.** Nothing caps the rows: 50 jobs finishing while hidden makes a 51-row menu.

### Could not check

- On a Mac: an idle logout and shutdown going through (F1), the login launch opening no window (`wasOpenedAtLogin`, macOS 13+) and the System Settings approval state (F4), the default title bar (F5), the native header style (F6), the quit question coming to the front (F11), tray rendering, Dock modes.
- The quit question with real jobs (needs a configured provider); its decision logic is unit- and mutation-tested.

### Follow-ups S-open-1, S-open-3, S-open-4: results

- `npm test`: 43 tests, 43 pass, 0 fail.
- e2e against `feat/mac-app-engine` at **4d9bb42** (its latest commit; exported read-only with `git archive 4d9bb42 src`, `/api/health` carries `pid`): all 11 steps pass. No process left afterwards.
- Open point 2 (a job submitted under 2 s before quitting) stays as documented, accepted by the lead.

## Round 3 fixes (one entry per finding)

Branch head before: 3658785. The supervisor in `desktop/src/engine.js` was rebuilt to spec.md "Round 3 design" in one commit (b8f8822). The rebuild has:
- one current run record (`this.run`), set when a start or restart is accepted and cleared only by that child's exit or a failure before spawn;
- one gate for every late continuation (`run === this.run && !run.cancelled`);
- one exit handler;
- one stop: stdin, then SIGTERM to the group, then SIGKILL to the group on a timer, with no HTTP request;
- a probe of the log before every launch;
- seams in the constructor: `spawn`, `health`, `jobs`, `killGroup`.

Deleted: the queue, `gen`, `verified`, `_enqueue`, `_kill`, `waitExit`, the shutdown fetch, and the fake engine's `/api/shutdown` route.

Every supervisor test now ends with an invariant check in `afterEach`, done before the engine is stopped:
- at most one live child;
- no "running" status emitted while the run's child is missing or has exited (a `status` listener).

The seam tests use fake children with pids above 90,000,000; the fake `killGroup` never reaches `process.kill`.

Mutation runs work as in round 1: swap one exact line, run the named test in its own session, restore with `git checkout`, run it again. Every mutant ran on committed code, and every restored run passed. The e2e ran against `feat/mac-app-engine` **62cba9c**, its latest commit, exported read-only with `git archive 62cba9c src`.

| Id | Change | Ran | Saw |
|----|--------|-----|-----|
| A1 | The exit handler clears `this.run` first. `_waitReady` passes the gate after the health answer, so an "ours" that arrives after the exit is dropped. Commit b8f8822 | Seam test: health reply held open, child exits, then the reply "ours" is released | `start()` resolves false; failure kind `exited`; no `running` status. Mutant without the gate after health: `AssertionError: states: starting, stopped, running`. Mutant where the exit handler does not clear the run: same failure |
| A2 | Stop is: mark the run cancelled, `stdin.end()`, SIGTERM to the group, then a timer that SIGKILLs the group after `stopWaitMs` (10 s). The exit event clears the timer. No HTTP anywhere; the fake engine's shutdown route is removed. Commit b8f8822 | Seam test: `globalThis.fetch` spied, children ignore signals. A real-process test: a server holds 8470 while a stop happens during start and records every request | No fetch; stdin ended; `[[pid,'SIGTERM']]` at once, then `[[pid,'SIGTERM'],[pid,'SIGKILL']]` after the wait; the recording server got no POST. Mutants: SIGTERM removed: `SIGTERM to the group at once / + []`. SIGKILL timer removed: `SIGKILL to the group after the wait / - [ 90000000, 'SIGKILL' ]`. `stdin.end` removed: `stdin closed / actual: false` |
| A3 | `AppLog.probe()` does an empty append before every launch. A failure is "Can't write the log file: <error>" and nothing is spawned. `write()` always tries and clears its error on success; a failed write mid-run keeps the engine running and the in-memory tail. Commit b8f8822 | Seam test: an existing `app.log` at 0444 (the folder and size checks pass); start; chmod 0644; Try again | First start: false, no spawn, reason `Can't write the log file: EACCES…`. Try again: true, one spawn, and the file holds `engine started (pid N, port 8470)`. Mutant using the remembered error instead of probing: `actual: true, expected: false` (it spawned) |
| A4 | `restart()` passes the gate after reading jobs: a run that was stopped meanwhile, or a quit, refuses with "The engine was stopped while the restart was being checked." It sets "restarting" at once, and a second restart while one is pending is refused ("A restart is already under way."), not queued. Commit b8f8822 | Seam tests: jobs held, `restart()`, then `stop()` (and a `stopForQuit()` variant), then `[]` released. Real-process test: two restarts at once | Restart refused, 1 spawn, state stopped (both variants). Two restarts: `[{ok:true},{ok:false,'A restart is already under way.'}]`, two engines ever started, only the last alive and held. Mutants: gate after jobs removed: `+ ok: true, reason: null / - ok: false`. Pending-restart refusal removed: the second restart got the gate's reason instead (`+ 'The engine was stopped…' - 'A restart is already under way.'`) |
| R2 (engine round 3) | The one exit handler kills the dead run's process group once, before or after ready, ignoring ESRCH. **Broader than the design:** it does this on every exit, a stop included, not only an unexpected one. A helper that ignores the SIGTERM a stop sends would otherwise outlive the engine, because the engine's exit clears the SIGKILL timer. Commit b8f8822 | Real-process test: a fake engine starts a helper that ignores SIGTERM, then exits before ready (`die-before-ready`). The round 1 crash-with-helper test and the stop-with-helper test also stay | Helper gone, checked by pid. Mutant without the exit handler's group kill: the R2 and S-open-3 tests both fail (`no helper outlives its crashed engine / + [ 1636783, 1636817, …`) |
| G1 | Finished-while-closed rows sort failed first, then newest. Commit 00fe447 | Logic test: 7 jobs, the oldest one failed | Rows: Job 0 · Failed, Job 6 to Job 3 · Saved, "and 2 more"; header "6 saved, 1 failed". Mutant sorting newest only: `- label: 'Job 0', stage: 'Failed'` |
| G2 | README "Quit" bullet and the journal now say that during a logout any question cancels the logout, and that after Stop and Quit you log out again. Commits c84ba08 (README), 3cc4d91 (journal) | Read both | Present. Not checkable on Linux |
| G3 | Waiting rows (and so the quitting rows) are capped at 5 plus "and N more"; running rows always show. Commit 8d448c8 | Logic test: 2 running and 10 waiting, in both the Transcribing and the quitting state | A, B, W0 to W4, "and 5 more"; header "Transcribing · 2 running, 10 waiting". Mutant without the cap: `+ label: 'W5'` |
| G4 | The unknown-list question has the approved three buttons: Quit When Done (default), Stop and Quit, Cancel. Its text is the lead's, split like the approved box: message "anyscribe couldn't check which transcriptions are running"; detail "Quit when they finish, or stop them now? To finish a stopped one later, transcribe it again." After three failed job reads in a row the menu header ends " · not answering" (`main.js` counts failed reads). README and architecture are updated. Commits c84ba08, 198989a | Logic tests: the unknown box and its choices; header at 2 and 3 failed reads, and on Engine stopped | The box matches; the header changes at the third read, never on Engine stopped. Mutants: unknown choices without whenDone: `G4: the approved three buttons / + 'quit' - 'whenDone'`. Threshold at Infinity: `+ 'Transcribing · 1 running' - '… · not answering'` |
| G5 | The journal now names `quitDecision`, not `decideQuit`. "Roll forward" is replaced with the fake's real modes. Round 1's queue, generation and `/api/shutdown` lines say round 3 replaced them, and a "Round 3: the supervisor rebuilt" section is added. Commit 3cc4d91 | `grep decideQuit\|roll forward` on the journal | No match |
| G6 | Same change as A3. The probe runs before every launch, so Try again re-checks a repaired log, and a good write clears the error. Commit b8f8822 | The A3 test's Try again step | Passes. Mutant where `probe()` returns a latched error without retrying: `Try again / actual: false, expected: true` |

Docs also updated for the new stop (commit 355b496):
- the README "Stop" and "Crash" bullets;
- spec.md's "Stopping the engine" sentence (it now says no POST /api/shutdown, round 3);
- the architecture section.

### Results

- `npm test`: 49 tests, 49 pass, 0 fail (about 11 s). It also passed twice in a row straight after the rebuild.
- e2e against **62cba9c**: all 11 steps pass (dashboard 368 ms after ready). An earlier run against 56448de, just after the rebuild, also passed all 11.
  - The e2e's log lines are unchanged ("engine ready", "quitting: stopping the engine", "stopped unexpectedly"); its regexes matched them.
  - No process was left after any run.

### Risks the rebuild adds

1. **The group kill on every exit** (R2, broadened above) signals a process group id after its leader has exited. If the group is empty this is ESRCH. A different process could only receive it if the same id were reused as a new group leader before the handler runs, which happens synchronously in the exit event. I judge this negligible; it is the same assumption as round 1's crash kill.
2. **At quit nothing waits.** `stopForQuit` sends SIGTERM and closes stdin, then the app exits, so its 10 s SIGKILL timer never fires. A stubborn engine is then left to slice 2a's own hard exit and its stdin watcher (the e2e force-kill step shows the engine follows).
3. **Restart refuses where round 1 queued.** A second Restart engine click while one is pending now gets "A restart is already under way." The menu only offers Restart engine when the engine is stopped, and the bridge returns the reason, so 2c should show it.
4. **Dashboard Shutdown.** The dashboard's own Shutdown button is now the only `/api/shutdown` caller. The shell treats the resulting exit as a crash and restarts (unchanged; 2c hides the button).

## Round 4 fixes

Branch head before: 5ab847e. Built to spec.md "Round 4 design". Every mutant ran on committed code, and every restored run passed. The e2e ran against `feat/mac-app-engine` **b22df16** (origin/main + 43 commits, after its rebase), exported read-only with `git archive b22df16 src`.

| Id | Change | Ran | Saw |
|----|--------|-----|-----|
| S3-A1 | `stop()` now runs `if (this.run) this.run.restartRequested = false;` before `_cancel`. An explicit stop revokes a restart's pending relaunch. The line is not in `_cancel`, because restart() sets the flag and then cancels through `_cancel`. Commit af4245d | Seam test: start; restart() with signals ignored; wait for its SIGTERM; stop(); emit the old child's exit | restart() returns ok false; one child only; `run` null; state stopped. Mutant (line removed): `AssertionError: the overtaken restart reports it did not restart / actual: true, expected: false`. The relaunch went ahead. |
| G7 | "Stop and Quit" quits straight away through the normal quit path. That covers both the quit question's button and the menu's "Stop and quit now". There is no job read and no per-job cancel. The engine's stop (stdin plus SIGTERM to its group, in `will-quit`) ends every job. `stopAndQuit()` and `engine.cancelJob` are deleted. Commit f959a5b | New e2e step 10. A fake engine answers /api/jobs once with one running and one pending job, then never again. The main process's `dialog.showMessageBox` is replaced with one that prints "ASKED <button 1>" and answers "Stop and Quit". Then `app.quit()`. Any POST to the fake is written to the log | The app exits 39 ms after quit. The question was asked ("ASKED Stop and Quit"). The fake engine's pid is gone. The fake received no POST. Mutant (the job read and cancel loop put back): `FAIL AssertionError: Stop and Quit took 2484 ms`. |
| G10 | The dead `choice === 'quit'` branch in `askQuit` is removed. No question offers a 'quit' choice since G4. Commit f959a5b | `npm test`, e2e | Pass. Only dead code was removed, so there is no mutant. |
| G8 | The cap lines now read "and N more waiting" and "and N more finished". README updated. Commit 9e41dc4 (with G9: one commit, same two files) | Logic tests: G3 (10 waiting) and G1 (7 finished) | "and 5 more waiting", "and 2 more finished". Mutants (word dropped): `+ label: 'and 5 more' - label: 'and 5 more waiting'`; `+ label: 'and 2 more' - label: 'and 2 more finished'`. |
| G9 | When idle and not answering, the header reads "anyscribe · Not answering" in place of "Ready". The " · not answering" suffix stays for Transcribing and Quitting. The finished-while-closed header keeps the suffix too; the design does not name it. README updated. Commit 9e41dc4 | Logic test: idle at 5 failed reads; Quitting at 3 | "anyscribe · Not answering"; "Quitting when these finish · not answering". Mutant (suffix always appended): `+ 'anyscribe · Ready · not answering' - 'anyscribe · Not answering'`. |

Also updated:
- The journal has a "Round 4" section (commit f9e83af).
- spec.md's Stop and Quit sentence no longer says POST /api/jobs/<id>/cancel (commit e1db88d).

### Results

- `npm test`: 50 tests, 50 pass, 0 fail.
- e2e against b22df16: all 12 steps pass. That is the 11 from before plus step 10, "Stop and Quit quits at once" (39 ms).
- No process was left after any run.
