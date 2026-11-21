Note: home-folder paths rewritten to `~`.

~~~~
FIT REVIEW, round 1: Mac app shell (feat/mac-app-shell, 7ab1539..880ed2c)

1. VERDICT: CONDITIONAL on F1 to F4.

This is the job he asked for, and Electron is the right tool for it. It is a T3-style local server inside a window, Mac first, with the CLI untouched. It also stays inside its slice: nothing from 2c (banner, Settings "This Mac", first-launch cards) leaked in. The structure is close to the simplest one that works: pure logic, a Node-only supervisor and the Electron wiring, about 1,000 lines with no dependencies beyond Electron. The start window, the quit question wording, the menu states and the stage mapping match the mockup. I checked the stage mapping against slice 2a's actual step names (download, transcribe, write, index, cached in orchestrator.py), and they line up.

There are four should-fix problems. Two are on the quit path (invariants 1 and 4), one is in Start at login, and one is a window he cannot drag on his Mac.

2. FINDINGS

F1, should-fix, PLAUSIBLE: every log out or shutdown would be interrupted, even with no jobs running.
Where: desktop/src/main.js:285-289 (before-quit always calls preventDefault and decides later), and finalQuit at 250-260.
Scenario: the app is idle in the menu bar and he chooses Log Out. Electron answers the macOS terminate request with "cancel", because before-quit was prevented. The app then quits on its own a moment later, but the log out has already been abandoned. He would see "anyscribe interrupted log out" and have to log out again, every time. The spec only wants the log out cancelled after Quit When Done. The builder lists this as unchecked on a Mac.
Fix: decide without waiting, using the last job poll (latestJobs, at most 2 s old). If no job is active, do not prevent the quit; stop the engine in will-quit by closing its stdin and sending SIGTERM to its own pid. The engine already treats SIGTERM like /api/shutdown (see the tailnet journal). Keep the asynchronous question only when the last poll showed active jobs. The leftover risk, a job started under 2 s before quitting, should be written down, or closed by refreshing latestJobs whenever the dashboard submits a job.
What settles it: on a Mac, run the app with no jobs, choose Apple menu > Log Out, and see whether the log out completes.

F2, should-fix. The logic is CONFIRMED by tracing the code; the timing is PLAUSIBLE.
What happens: a slow or briefly unreachable engine reads as "no jobs". That can end a running transcription without asking.
Where: desktop/src/engine.js:321-331 (jobs() returns [] on any error or 2 s timeout); main.js:305-307 (poll); main.js:267-271 (requestQuit).
Scenario: he picks Quit When Done. One /api/jobs call takes longer than 2 s, for example while a heavy local transcription keeps the Mac busy. poll() then sees [], calls finalQuit and stops the engine, which kills the job he explicitly chose to let finish. The same timeout on Cmd Q skips the question entirely. This breaks invariant 4. The builder's point 8 holds for a dead engine, not for a slow one.
Fix: have jobs() return null when the list is unknown. poll() then keeps the previous latestJobs. The quit decision uses the last known list when the fresh read fails, and only treats "no jobs" as real when the engine is not running.

F3, should-fix. CONFIRMED by tracing the code, not run.
What happens: quitting while the engine is restarting after a crash starts a brand-new engine during the quit.
Where: desktop/src/engine.js:188-192 and 215-224. stop() at 277-300 clears this.child only after the old engine has exited, and _exitedEarly never checks this.stopping.
Scenario: the engine crashes and its automatic restart is under way (state "restarting"). He quits. stop() closes stdin, so the starting engine exits. The next pass of the start loop still sees this.child equal to that engine, so it calls _exitedEarly, which goes to _crashed, which launches a new engine. Then stop() sets this.child = null, which drops the only reference to the new child, and the app exits. With 2a's --watch-stdin, the orphan engine dies when the app's end of its stdin closes. Without the flag, it outlives the app (invariant 1). The same kind of race exists if stop() runs while _launch is still checking the port (before spawn): the engine is spawned after stop() has already returned. The test added in 24774f9 only covers the case where the child reference has already changed.
Fix: give each launch a generation number, or check this.stopping. Check it in _launch after every await, and in _exitedEarly and _crashed; return without launching once a stop has begun.
Test to add: put the fake engine into a crash loop, call stop() while the state is "restarting", then assert that no new pid appears.

F4, should-fix. The first part is CONFIRMED; the Mac behaviour is PLAUSIBLE.
What happens: Start at login does not do what the docs say.
Where: main.js:81 and main.js:359; desktop/README.md (setStartAtLogin "launched hidden"); proof.md ("launched hidden").
- CONFIRMED: `openAsHidden` is not an option in Electron 44. Its Settings type (node_modules/electron/electron.d.ts:24360) has only openAtLogin, type, serviceName, path, args and enabled. So the option does nothing, and "launched hidden" rests entirely on `wasOpenedAtLogin`.
- PLAUSIBLE: whether wasOpenedAtLogin is true on macOS 13 and later under SMAppService. I found no source either way. If it is false, a login launch opens the window, against mockup section 9: "starts in the menu bar when you log in, with no window".
- Separately, startAtLogin is stored in settings.json alongside the system's own setting. If he turns the login item off in System Settings > Login Items, or it sits at "requires-approval", the menu tick and the bridge still say On.
Fix: drop openAsHidden; drop startAtLogin from settings.json and read `app.getLoginItemSettings().openAtLogin` (plus `status`) as the source of truth (also the simpler design); correct the README and proof wording; check the login path on a Mac.

F5, should-fix, CONFIRMED from the code and the builder's own note (proof point 3).
What happens: on his Mac, the dashboard window cannot be dragged.
Where: main.js:148 sets `titleBarStyle: 'hiddenInset'`, but today's dashboard has no drag region.
Scenario: he runs this build on his Mac before 2c ships. He cannot move the window, and the traffic-light buttons sit over the sidebar.
Fix, simplest: use the default title bar for the dashboard window now, and let 2c switch to hiddenInset in the same change as its drag strip and top padding. The start window keeps hiddenInset, since it has its own drag strip. This changes the spec, so it needs the lead's yes.

F6, nit, CONFIRMED against the mockup HTML: menu separators and header style differ from the drawing.
Where: main.js:199-203.
- The mockup has no separator between the header and "Open anyscribe" in the Ready state, nor between "Restart engine" and "Open anyscribe" in the Engine stopped state. The code adds one in both places. The mockup puts a separator before Open only after job rows.
- The mockup draws the header as a small grey bold line. Electron 44 has `type: 'header'` (electron.d.ts:10180), which renders as a macOS section header; that is closer to the drawing than a greyed-out disabled item.
Fix: add the separator before 'open' only when there are rows, and consider `type: 'header'` (macOS 14 and later; check what it falls back to on older systems).

F7, nit, CONFIRMED: the proof claims more than the e2e shows.
Where: test/e2e.js:175-182. The step "a login launch starts the engine with no window" launches with `--hidden`. A macOS login item cannot pass arguments, so this proves the --hidden path, not the Mac login path.
Fix: reword it as "a --hidden launch", and list the real login path under "could not check".

F8, nit, CONFIRMED: two copies of the version number.
Where: desktop/package.json:4 says "0.19.0", and the bridge's `version` comes from it. The engine's version lives in pyproject.toml. The next engine release will leave the app reporting an old version unless someone remembers to bump both.
Fix: note it for phase 3 (packaging can stamp the version from pyproject), or add a test that compares the two.

F9, nit: the --watch-stdin fallback is extra code with a removal date.
Where: engine.js:217-222. The spec asked only to run without the flag and say so in proof.md; the builder built an automatic retry instead. It is correctly marked `shortcut:`.
Fix: if 2a merges before this branch, delete the fallback now and always pass the flag. Fewer moving parts, and F3's orphan case disappears with it.

F10, nit: a Python 3.13 add-ons folder is created in dev.
Where: engine.js:162 and logic.js:49-52. In dev, the app creates `~/.anyscribe/runtime/lib/python3.13/site-packages` in the real home folder, even though the dev venv ignores it (proof point 5).
Fix: create the folder in packaged mode only. Later, derive the "python3.13" part from the bundled Python rather than writing it in by hand.

F11, nit, PLAUSIBLE: the quit question may open behind other windows.
Where: main.js:270 calls showMessageBox with no parent window.
Scenario: he quits from the menu bar while the app has no Dock icon (menubar mode, window hidden), or a log out triggers the question. The question box may open behind the front app.
Fix: call `app.focus({ steal: true })` before showing it, then check on a Mac.

F12, nit, for phase 3: the app still uses Electron's default application menu. In dev the app menu is named "Electron"; Help links to electronjs.org; View includes Toggle Developer Tools; the ⌘O shown in the menu bar menu is only a label; ⌘O does nothing from the app menu.
Fix: a small application menu in phase 3 (anyscribe: About, Open ⌘O, Quit ⌘Q; Edit; Window).

I found no problem on these points. The port guards: the trailing slash in `ours()` blocks 127.0.0.1:8470.evil.example, file:// is blocked, and window.open and navigation leaving the app go only to http(s) in the browser. IPC checks which page is calling, and the preload exposes only the bridge. The crash window treats 59 s and 61 s correctly. The quit question's wording and counts match. Restart engine is refused during jobs. Logs and settings are stored in the right places.

3. ANSWERS TO THE BUILDER'S "SPEC IS WRONG OR OPEN" POINTS (proof.md lists eight; all answered)
1. stoppedRestarting: agree. The 2c banner needs it, and a boolean is simpler than a fifth state. Keep the name; the spec and README should record it as part of the contract (the README already does).
2. Roll-forward: agree. The double guard is fine for now. An engine option that refuses to roll forward belongs to 2a or a later change; it would replace the stdout check.
3. hiddenInset: agree that it is a problem; see F5. Use the default title bar until 2c.
4. Dashboard Shutdown button: agree that 2c should hide it in the app. Until then, a Shutdown press counts toward the three-crash limit. That is acceptable.
5. PYTHONUSERBASE in dev: agree; see F10.
6. Menu row layout and the extra state wordings: agree. Electron cannot right-align the stage; "Title · Stage" is a fair substitute. The three new wordings fit the mockup's "anyscribe · X" pattern. The separators still differ (F6).
7. "Couldn't start" reason: agree. The shell cannot paraphrase arbitrary errors, and the raw lines in the box under the message match the mockup's log box.
8. Unreachable engine read as "no jobs": disagree as built. True for a dead engine, false for a slow one; see F2.

4. PENDING OWNER CHECKS (only he, on his Mac, can confirm)
- The menu bar menu and dots in his real menu bar, light and dark: the glyph, the amber and red dots, the spacing.
- How the start window looks against mockup section 2 (the headless run could not take a screenshot).
- Whether a log out or shutdown with the app idle completes (F1), and whether a login launch opens with no window (F4). These are Mac tests the lead or a delegate can run; he only needs to look at the result.
- Not his to act on: the naming of stoppedRestarting (lead's call), and the F5 title bar choice (lead's call; tell him the reason).

5. NOT CHECKED, AND WHAT I INSPECTED
I did not run anything, by instruction.
- For the lead: `cd ~/labs/projects/anyscribe-wt/mac-shell/desktop && npm test`.
- The F3 test as described above, against test/fake-engine.js in crash mode.
- On a Mac: `ANYSCRIBE_DEV_PYTHON=<venv python> npm start`, then Log Out with no jobs (F1); turn on Start at login and log in again (F4); drag the dashboard window (F5); open the tray menu (F6).
- I did not open the mockup in a browser; I read its HTML for sections 2, 6, 7, 9, 10 and "For the build".
- The web search on wasOpenedAtLogin under macOS 13 and later found nothing either way.
Inspected: the packet (ask.md, spec.md, target.md, proof.md, lens.md) and declined.md; the full diff (desktop/src/main.js, engine.js, logic.js, preload.js, start-preload.js, start.js, start.html; package.json; scripts/make-icons.js; desktop/README.md; the architecture.md section; the journal entry; the _index.md row; .gitignore); the test names in test/*.test.js and the login step in test/e2e.js; electron.d.ts for the login item settings and menu item types; from 2a's branch, read-only: web/jobs.py, routes/transcribe.py, core/orchestrator.py (step names), web/app.py (stdin watch).
Sources (web search, inconclusive): Ventura's Open at Login vs Allow in the Background (mjtsai.com, 2022-10-27); Porting existing LoginItem logic to SMAppService (developer.apple.com forums thread 713830); Electron: natively implement LoginItem functions (Electron commit 6fc2a2a).
Skipped: I did not read every test body, desktop/node_modules beyond the type definitions, or the icon images.
Risk to pass on: the log out (F1) and login-launch (F4) behaviours have not been seen on a real Mac, and they are what he will hit first.
~~~~
