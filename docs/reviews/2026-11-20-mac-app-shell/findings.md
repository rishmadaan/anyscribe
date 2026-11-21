# Findings (verbatim reports)

Note: absolute home-folder paths in these copies were rewritten to `~` paths; the byte-exact originals stay in ~/.review-runs/2026-11-20-mac-app-shell/.


# Round 1


## report-sol-r1.md

~~~~
**NOT YET.** The Electron shell fits the approved job and the scope of this development slice. Its current safety checks do not establish the six invariants, particularly around quitting, engine ownership, and navigation.

Reviewed `7ab1539..880ed2c` in `~/labs/projects/anyscribe-wt/mac-shell`. The implementation still matches that target; `e97ef9d` adds only review material.

**Findings, most severe first**

**C1. blocker | CONFIRMED | Failed job reads permit silent interruption.**  
Where: engine.js:321 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:321`), main.js:271 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/main.js:271`), main.js:305 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/main.js:305`).

A two-second timeout, HTTP 500, invalid JSON, or missing endpoint becomes `[]`. Consequently:

- Quit proceeds without asking.
- Quit When Done immediately stops the engine.
- Restart engine passes its active-job guard.

An unresponsive HTTP endpoint does not establish that its worker threads stopped transcribing. The builder’s explanation to the contrary is wrong.

Malformed successful responses also escape validation. `{"jobs":{}}` reaches array operations; `[null]` reaches `job.status`. Read-only Node calls reproduced `jobs.filter is not a function` and `Cannot read properties of null`.

**Fix:** distinguish a validated job list from unknown status. Unknown status must prevent automatic quitting and restarting, preserve the last known information, and offer an explicit stop decision. Validate the array and its entries. Treat the pre-2a compatibility path as lacking this protection.

**C2. blocker | CONFIRMED | The readiness check does not prove ownership of the server.**  
Where: engine.js:188 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:188`), engine.js:257 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:257`), engine.js:287 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:287`).

Trace: the port precheck succeeds; another anyscribe instance takes the port while Python starts; its health response arrives before this child’s announcement or exit. `_healthy()` accepts only the public string `app: "anyscribe"`. `_waitReady()` can therefore mark this child ready while the responding server belongs to someone else. No announcement is required, and the announcement is checked before the awaited health request, not after it.

The window can load the other server, and `stop()` can POST `/api/shutdown` to it. Killing the child by its own pid does not make that HTTP shutdown safe.

The roll-forward fixture prints its alternative-port announcement immediately and serves the original port from the same fake process. It does not test delayed announcements or an independently owned listener.

**Fix:** establish per-launch server identity and authenticate control requests, or use an exclusively owned communication channel. Add strict-port behavior in the engine. Waiting for a startup sentence alone is insufficient because it precedes the actual bind.

**C3. blocker | CONFIRMED | Navigation confinement excludes subframes and redirects.**  
Where: main.js:315 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/main.js:315`).

Only `will-navigate` and initial `window.open` requests are filtered. Electron’s installed API declarations explicitly distinguish:

- `will-navigate`: main-frame navigation.
- `will-frame-navigate`: main-frame and subframe navigation.
- `will-redirect`: server redirects.

There is no handler for the latter two. The dashboard has no frame restriction in its HTML or server response setup. A dashboard script can therefore embed an outside-origin iframe; an allowed local navigation can also redirect outside the allowed origin.

This confirms a confinement defect. I have **not** demonstrated a bridge privilege escape: the IPC URL check would reject an outside-origin sender.

**Fix:** enforce the origin policy for frames and redirects, restrict frame content, and ensure permitted child windows receive the complete policy. Test direct navigation, redirects, iframes, and popups separately.

**C4. blocker | CONFIRMED | Concurrent restarts can lose ownership of a live child.**  
Where: engine.js:303 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:303`), engine.js:277 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:277`).

Two `restartEngine()` calls can both pass the initial state check and wait for `/api/jobs`. Neither marks the restart in progress before that wait.

Both can then stop the same old child. One stop can finish and start a replacement before the other stop finishes. The second stop unconditionally sets `this.child = null`, discarding the replacement’s ownership record. Overlapping port checks and launches can also create two children. A displaced readiness loop returns on the identity mismatch without stopping its displaced child.

**Fix:** serialize start, stop, and restart through one lifecycle operation; claim the operation before the first await. Use an operation identifier to invalidate stale continuations, and never clear or abandon another operation’s child. Add concurrent-restart and restart-versus-quit tests asserting individual child identities.

**C5. blocker | CONFIRMED | A valid empty job snapshot does not reserve an idle engine.**  
Where: main.js:271 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/main.js:271`), engine.js:307 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:307`).

Even with successful HTTP responses, checking jobs and stopping are separate operations. A transcription submission can arrive after the empty list was produced and before shutdown begins. The engine still accepts submissions during that interval. The newly accepted job receives no quit question and can be interrupted by quit or restart.

This also affects the final empty poll for Quit When Done.

**Fix:** coordinate with the engine: atomically stop accepting submissions and establish whether active jobs remain before committing to shutdown or restart. If work remains, retain it and obtain the appropriate decision. Test a submission deliberately interleaved between the idle check and shutdown.

**C6. should-fix | CONFIRMED | The documented development commands resolve Python from the wrong directory.**  
Where: README.md:14 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/README.md:14`), logic.js:23 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/logic.js:23`), engine.js:165 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:165`).

The README supplies `../.venv/bin/python`. `resolvePython()` returns it unchanged, but spawning uses `cwd: home`.

For this machine, the documented relative path therefore resolves to `/home/.venv/bin/python`, rather than the repository’s interpreter. The same problem affects the documented e2e command, whose engine uses a throwaway home. I reproduced the path calculations with Node.

**Fix:** resolve the development interpreter to an absolute path before changing directories, or require and document an absolute path.

**C7. should-fix | CONFIRMED | Finished jobs are not retained until the window opens.**  
Where: main.js:306 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/main.js:306`), logic.js:136 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/logic.js:136`).

Each poll replaces the entire menu source list. The integration engine at the proof’s `54f0d0b` returns every active job but limits the total summary to 50 when possible. Older completed jobs fall out of that response.

For example, after one hidden-window failure followed by 50 successful completions, the failure can disappear and its red indicator clear without the window being shown. Active jobs reduce the available finished-job slots further.

**Fix:** retain unseen completions by job identity in the shell, combined with an engine retrieval/acknowledgment contract that prevents missed completions between polls. Alternatively, explicitly revise the retention promise and show the limitation.

**C8. should-fix | CONFIRMED | The force-kill test can pass when its required safeguard fails.**  
Where: e2e.js:187 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/test/e2e.js:187`).

If the engine survives the killed app, the test prints `GAP`, kills the engine itself, and continues successfully. It does this even when `withFlag` is true.

Thus an actual regression in the integrated `--watch-stdin` path can still produce a successful test exit. The reported successful run is evidence for that particular run, but this test does not enforce the invariant.

**Fix:** assert that the engine follows whenever watchdog support is expected. Allow the historical compatibility gap only through an explicit test mode, and retain cleanup in `finally`.

**C9. should-fix | CONFIRMED | Shell filesystem errors bypass the startup failure screen.**  
Where: main.js:27 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/main.js:27`), engine.js:41 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:41`), engine.js:162 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:162`).

An unwritable log directory can throw before any window exists. A failed runtime-directory creation, or later synchronous log write, can reject an unawaited start operation or throw from a child-output callback. These errors do not become the advertised Couldn't start state.

**Fix:** catch shell initialization and logging failures, present a usable failure state, and retain control of any child already spawned. Error presentation must work when the normal log file itself is unavailable.

**Answers to the builder’s open points**

The proof contains **eight** points, although the brief says seven.

1. **`stoppedRestarting`: agree.** The banner needs this distinction. Keep the addition documented; a structured stop reason could replace it later.
2. **Busy-port roll-forward: agree with the diagnosis, reject the claimed completeness of the workaround.** Strict-port behavior is appropriate, but server ownership and control-request identity still need C2.
3. **`hiddenInset`: agree that dashboard adaptation belongs to 2c.** Until drag behavior and traffic-light clearance are verified on Mac, do not describe the assembled interface as ready.
4. **Dashboard Shutdown: agree that 2c must replace or hide it.** Currently a deliberate shutdown is treated as a crash and restarted. That is a disclosed integration limitation.
5. **Development user-site behavior: reasonable, with limits.** The hardcoded Python 3.13 directory is a bundled-runtime assumption. Starting successfully in a development venv does not prove packaged add-on installation.
6. **Menu layout and extra wording: reasonable adaptation.** The text rows preserve the stage information. Native rendering and keyboard behavior still need verification.
7. **Raw startup error details: acceptable.** A truthful general sentence plus actual stderr is preferable to invented paraphrasing. C9 remains uncovered.
8. **Unreachable means no jobs: reject.** HTTP availability and transcription-worker activity are separate facts. This is C1.

The old-engine fallback also needs an integration gate beyond the disclosed orphan-process gap. At base `7ab1539`, CLI startup invokes the automatic skill updater without honoring `ANYSCRIBE_APP`. Running that engine against the real home can touch Claude skill files. Slice 2a supplies the guard. A throwaway-home run cannot establish the approved “No surprise skill” promise for the old engine.

**Pending owner checks**

No code correction above requires an owner decision. After the builder verifies the native paths, the owner should confirm that the actual Mac menu, Dock modes, startup screen, and quit choices feel usable in his workflow. Packaging and Finder installation remain phase 3.

**Verification limits and inspected material**

This was strictly read-only. I ran no tests, build, Electron instance, server, or process-control command, and wrote no files.

I read the complete review packet and settled declined list; the approved mockup sections 2, 6, 7, 9 and “For the build”; all desktop JavaScript, HTML, package files, tests and icon-generation code; the changed building documentation and `.gitignore` diff. I traced the integration engine’s relevant startup, health, job-list, cancellation and shutdown paths, including the proof’s `54f0d0b`, and checked relevant behavior against the installed Electron declarations. Binary icons were not visually verified.

`git diff --check 7ab1539..880ed2c` passed. The read-only Node checks reproduced the path-resolution mismatch and malformed-job exceptions.

Existing checks for the lead to run:

```sh
cd ~/labs/projects/anyscribe-wt/mac-shell/desktop && npm test
```

```sh
cd ~/labs/projects/anyscribe-wt/mac-shell/desktop && env -i HOME="$HOME" PATH=/usr/bin:/bin ANYSCRIBE_DEV_PYTHON=~/labs/projects/anyscribe/.venv/bin/python node test/e2e.js
```

The latter reproduces the main-engine compatibility run, not the integrated 2a run. The proof does not name the wrapper file used for that integration run, so its exact invocation is not reproducible from the packet alone.

The new race, failure-response, navigation and filesystem regression cases above have no existing test commands. Mac login, logout, Dock behavior, native dialogs, tray rendering and Finder launch could not be verified on this Linux host.
~~~~


## report-opus-r1.md

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

# Round 2


## report-astra-r2.md

~~~~
**NOT YET.** The fixes substantially improve the shell, but readiness can now report a dead engine as running, and log failures are not handled as promised. Stop invalidation also misses a restart continuation. Server ownership remains conditional after startup.

Reviewed shell `04986cc` against engine `4d9bb42`. The current worktrees’ relevant code matches those targets. No files were changed, and no Electron instance, server, test runner, or process-control operation was run.

**Round 1 dispositions**

“FIXED” below means the agreed code or documentation change is present. It does not certify the pending Mac checks.

| ID | Status | Evidence |
|---|---|---|
| C1 | FIXED | Failed or malformed job reads return `null`; quit, restart and Quit When Done distinguish unknown from empty. |
| C2 | PARTLY | Readiness checks the child’s PID, but shutdown trusts cached verification. See A2. |
| C3 | FIXED | Frames, redirects and popups share the navigation policy; event properties match installed Electron declarations. |
| C4 | PARTLY | Concurrent restarts are serialized, but a pending restart can continue after stop invalidation. See A4. |
| C5 | DECLINED-OK | Left settled, including the explicitly accepted polling interval limitation. |
| C6 | FIXED | Relative interpreter paths resolve against the app’s original working directory. |
| C7 | FIXED | Observed hidden-window completions persist by job ID; displayed rows are capped without dropping counts or the failure indicator. |
| C8 | FIXED | Engine survival after force-killing the app now fails the e2e instead of printing a passing GAP. |
| C9 | PARTLY | Filesystem exceptions are caught, but first-append failures escape the startup failure state; retry retains the old error. See A3. |
| F1 | FIXED | Known-idle quit is no longer prevented; shutdown occurs in `will-quit`. Native logout remains unverified. |
| F2 | FIXED | Unknown job reads no longer trigger Quit When Done or permit restart. |
| F3 | PARTLY | Automatic-launch and port-check cancellation are guarded; pending manual restart still bypasses stop invalidation. See A4. |
| F4 | FIXED | Removed `openAsHidden` and duplicated login state; system state is authoritative. Actual login launch remains unverified. |
| F5 | FIXED | Dashboard uses the default title bar pending slice 2c. |
| F6 | FIXED | Separator placement and conditional native headers implement the agreed change. |
| F7 | FIXED | Evidence now identifies `--hidden`, rather than claiming a tested macOS login launch. |
| F8 | FIXED | Version stamping is explicitly deferred to phase 3, as agreed. |
| F9 | FIXED | Removed fallback; `--watch-stdin` is unconditional. |
| F10 | FIXED | Add-ons directory creation is restricted to packaged mode. |
| F11 | FIXED | Quit question focuses the app and uses the visible dashboard as parent. Native presentation remains unverified. |
| F12 | FIXED | The application menu is explicitly recorded for phase 3. |

A1 and A4 concern the revised lifecycle code. A2 and A3 are remaining gaps in the C2 and C9 fixes.

**A1. should-fix | CONFIRMED | Readiness can permanently miss an engine exit.**

Where: engine.js:234 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:234`), especially `_waitReady()` at lines 247–260.

Scenario: the child answers health, then exits while `_health()` is still awaiting the response or JSON. The exit listener records `attempt.exit`, but does not call `_onExit()` because `attempt.ready` is still false. `_waitReady()` subsequently accepts `'ours'`, sets `ready = true`, and reports `running`. The exit event has already happened, so no automatic restart follows.

The previous implementation checked `attempt.exit` after the awaited health response. This delta removed that check.

A read-only Node reproduction supplied that interleaving to the actual `_waitReady()` method, with no child process:

```text
started: true
state: running
childExitCode: 1
crashes.exits: []
```

The dashboard can fail to load while the shell continues reporting a running engine. Restart can then be refused because `/api/jobs` is unreachable.

Fix: recheck the attempt’s exit and ownership after health completes, before accepting readiness. Add a regression that delivers a successful health response after the child’s exit event; verify the restored check fails when removed.

**A2. should-fix | PLAUSIBLE | Startup verification does not bind the later shutdown request to that server.**

Where: engine.js:345 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:345`), `_stopNow()`.

`this.verified === child` establishes who answered an earlier health request. It does not establish who receives a later request to the same port. `_stopNow()` closes stdin first, then sends unauthenticated `POST /api/shutdown`, without even rejecting an already-exited child.

Scenario: the verified engine exits during shutdown and another server takes the port before the POST connects. That server can receive the shutdown request despite having a different PID.

An in-memory probe with an already-exited, previously verified child confirmed that `_stopNow()` still issues the POST. I did **not** reproduce a live port takeover or stop another server. The existing C2 tests cover an unverified server during startup, not replacement after verification.

Fix: use the owned stdin/process channel for shutdown, or authenticate the control request with per-launch identity checked by the receiving engine. Another separate health check would still leave a race. Test replacement of the listener after verification.

**A3. should-fix | CONFIRMED | An unwritable log file can still produce a successful startup, and its error cannot be retried.**

Where: engine.js:40 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:40`), `AppLog`, and `_launch()` at lines 203–238.

The constructor creates the directory and checks file size. For an existing small log file, neither operation establishes append permission. `_launch()` checks `log.error` before spawning; the first append happens afterward. An append failure then sets `log.error`, but nothing converts it into the advertised failure state.

A read-only simulation replaced filesystem, network and spawning operations with in-memory stand-ins. The actual startup code returned:

```text
initial log error: null
started: true
spawned: 1
state: running
logError: EACCES: app.log is not writable
failure: null
```

This contradicts the README’s promise that an unwritable log prevents engine startup and displays the reason. The existing test only makes the *directory* invalid, which fails earlier.

Separately, `error` stays latched permanently. After the underlying problem is repaired, Try again checks the same error and fails without attempting to reopen the log.

Fix: establish appendability before spawning, retain the in-memory diagnostic tail, and reopen/revalidate logging on retry. Cover an unwritable existing file, later write failure, and repair followed by Try again.

**A4. should-fix | CONFIRMED at supervisor level | A pending restart adopts the stop’s new generation.**

Where: engine.js:375 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:375`), `restart()`.

Unlike `start()`, `restart()` does not capture its generation when requested or check for invalidation after awaiting `jobs()` and `_stopNow()`. It eventually calls `_launch(..., this.gen)`, adopting whichever generation now exists.

Scenario: restart waits for the job list; a stop invalidates outstanding work; the job response arrives. Restart still stops and launches. With queued `stop()`, this can start an unnecessary replacement and delay completion of the stop through another readiness wait.

An in-memory reproduction suspended `jobs()`, called `stopForQuit()`, then released the response. It recorded:

```text
quitGen: 1
launchGen: 2
currentGen: 2
restart result: { ok: true, reason: null }
```

This proves the invalidation gap. It does **not** prove an engine survives an actual Electron quit; Electron teardown and the stdin watcher may prevent that outcome.

Fix: give the complete restart operation a cancellation identity that its own internal stop cannot overwrite. Check it after each await. Add restart-versus-stop coverage, rather than relying only on concurrent-restart and automatic-crash tests.

**Pending owner checks**

The lead or builder should perform the technical Mac checks: idle logout and shutdown, login launch without a window, Login Items approval/external changes, quit-dialog visibility and choices, Dock modes, and draggable windows. These are not code-repair tasks for Rishabh.

After those pass, Rishabh should confirm the actual menu, light/dark indicators, startup screen and quit flow are usable. Packaging and Finder installation remain phase 3.

**Verification and limits**

I read every file explicitly named by the brief, including the full delta, both prior reports, binding fix plan, proof and declined list. I inspected the affected supervisor, Electron wiring, bridges, startup page, logic, regression tests, e2e, README and building documentation; the relevant approved mockup sections; and the engine’s health, job, cancellation and shutdown integration. Installed Electron declarations support the new frame and redirect handler signatures.

The engine’s own process-group exit path supports the shell’s detached spawning and group signalling. I found no new navigation-policy defect in this pass.

Read-only Node probes reproduced A1, A3 and the supervisor behavior in A4. A2’s live timing remains untested. The production-code/documentation delta passes `git diff --check`. The claimed 43 passing tests and 11 e2e steps remain supplied evidence, not independently rerun results.

After adding the missing regressions, run:

```sh
cd ~/labs/projects/anyscribe-wt/mac-shell/desktop && npm test
```

The integrated e2e also needs repeating against exact engine `4d9bb42`. The packet describes an exported engine and interpreter wrapper but does not give that wrapper’s path or full invocation, so I cannot supply an exact equivalent command from the evidence provided. Native Mac behavior, visual rendering, real-job quitting and live race timing were not checked under this review’s read-only restrictions.
~~~~


## report-opus-r2.md

~~~~
FIT REVIEW, round 2: Mac app shell (feat/mac-app-shell at 04986cc; HEAD 3051264 adds only review files, checked with git diff --stat)

1. VERDICT: CONDITIONAL on G1 (one sort comparator, under 5 lines). Everything else is a nit or a check on a real Mac.

The round 1 fixes keep the job he asked for, and nothing from slice 2c crept in. I checked the menu layouts line by line against mockup section 6, direction A, and section 7. Ready, Transcribing, Finished while the window was closed, Engine stopped and Quitting when these finish now have separators exactly where the drawing puts them. I confirmed this with a node one-liner on logic.menuLayout. The header uses `type: 'header'` only on macOS 14 and later, and Electron's own type file (electron.d.ts:10178) agrees that this is where it exists. The approved quit question is unchanged word for word. The design grew (a queue, generation numbers, the pid check, group kills, finished-job memory). Each piece answers an upheld finding, and I found nothing to delete.

2. ROUND 1 IDS
- C1: FIXED. jobs() validates the list and returns null when it cannot know. Quit, Quit When Done and Restart all treat unknown as not idle.
- C2: FIXED. Ready only when /api/health reports the child's pid; /api/shutdown goes only to the verified child.
- C3: FIXED. One navigation rule covers will-frame-navigate (main frame and subframes), will-redirect and window.open.
- C4: FIXED. Start, stop and restart run through one queue, and a stop claims itself at call time.
- C5: DECLINED-OK. Settled in declined.md.
- C6: FIXED. A relative dev Python path is resolved against cwd; the README uses $(pwd).
- C7: FIXED. Finished jobs are remembered by id until the window is shown. See G1 for a new problem in how they are shown.
- C8: FIXED. The GAP branch is gone; e2e.js:193 fails if the engine outlives a force-killed app.
- C9: FIXED. AppLog never throws, and a log failure becomes a "Couldn't start" reason. See G6 for one side effect.
- F1: FIXED in code (before-quit decides at once, and an idle quit is not prevented). Unverified on a Mac.
- F2: FIXED (same change as C1).
- F3: FIXED. Generation checks after the port check, in _waitReady, and on crash restarts.
- F4: FIXED. openAsHidden is gone, and the login state is read from the system. wasOpenedAtLogin is still unverified on macOS 13 and later.
- F5: FIXED. The dashboard window has the default title bar; the start window keeps hiddenInset plus its drag strip (start.html:18).
- F6: FIXED. Matches the mockup; checked above.
- F7: FIXED. The step is named "a --hidden launch".
- F8: FIXED as planned (moved to phase 3 and recorded in the journal).
- F9: FIXED. `--watch-stdin` is always passed, and the fallback is removed.
- F10: FIXED. The add-ons folder is created only in packaged mode.
- F11: FIXED in code (`app.focus({steal:true})`, and the dialog is attached to the visible window). Unverified on a Mac.
- F12: FIXED as planned (moved to phase 3 and recorded in the journal).

New defects introduced by the fixes: G1 (the 5-row cap), G2 (logout disclosure), G5 (stale journal), G6 (the log error never clears).

3. NEW FINDINGS, most severe first

G1. should-fix. CONFIRMED (node one-liner on logic.menuModel).
What happens: the 5-row cap can hide the one failed job while the menu still says a job failed.
Where: desktop/src/logic.js:152-157. Rows are sorted newest first only.
Scenario: he queues 7 links and closes the window. The first link fails and 6 more are saved. The menu shows a red dot and "anyscribe · 6 saved, 1 failed". The rows are Saved 6 down to Saved 2, then "and 2 more". The Failed row is the one he needs, and it is not shown. Output: `alert | anyscribe · 6 saved, 1 failed`, with rows `Saved 6..Saved 2, and 2 more`.
Fix: sort failed jobs first, then newest: `(b.status==='failed') - (a.status==='failed') || (toMillis(b.completed_at) ?? 0) - (toMillis(a.completed_at) ?? 0)`. Add the 7-job case to the existing cap test, asserting a 'Failed' row is present.

G2. nit. CONFIRMED by tracing the code; how macOS shows it is PLAUSIBLE.
What happens: logging out during a job is cancelled whatever he chooses, not only after Quit When Done.
Where: main.js:312-321. preventDefault runs before the question is shown.
Scenario: he logs out while jobs run and picks Stop and Quit (or Quit Anyway in the unknown box). The app quits, but macOS has already been told to cancel the log out, so he has to log out again. Mockup section 7 says only that Quit When Done cancels the logout. This is an Electron limit (the decision in before-quit cannot wait for an answer), but it is not disclosed.
Fix: one line in the README "Quit" bullet and in the journal: "During a logout, any question cancels it; after Stop and Quit, log out again."

G3. nit. CONFIRMED by tracing the code.
What happens: the menu cap covers finished rows only; waiting jobs are uncapped.
Where: logic.js:125 and 165. Twelve submitted links make a 14-line menu ("Transcribing · 2 running, 10 waiting", 12 rows). The same applies to the Quitting when these finish rows.
Fix, optional: apply the same 5 plus "and N more" to waiting rows. The running rows (at most 2) always show.

G4. nit. The menu is CONFIRMED; the cause is PLAUSIBLE.
What happens: the unknown-list quit box offers no way to let jobs finish, and the menu does not say when the engine stops answering.
Where: logic.js:218-225; main.js:338-344.
Scenario: the likeliest cause of an unanswered /api/jobs is an engine busy transcribing. At that moment he gets only Quit Anyway or Cancel, while the approved default for "jobs may be running" is Quit When Done. quitWhenDoneReady already waits on an unknown list, so the option would cost only one button. Separately, while reads keep failing, the menu keeps showing the last list (for example "Transcribing · 1 running") with nothing to say that the engine is not answering. That claims more than the app knows.
Fix (the lead's call; the plan chose these buttons): add Quit When Done to the unknown box, or at least end its message with "Try again in a moment." Optionally, append " · not answering" to the header after about 3 failed reads in a row.

G5. nit. CONFIRMED.
What happens: the journal still describes round 0 code.
Where: docs/building/journal/2026-11-20-mac-app-shell.md:22-24 still says "shutdown or roll forward" and names `decideQuit`, which no longer exists. logic.js exports quitDecision and has no roll-forward check.
Fix: reword to quitDecision and drop "roll forward".

G6. nit. CONFIRMED by tracing the code.
What happens: one failed log write blocks every later engine start until the app is quit.
Where: engine.js:52-60 sets log.error and never clears it; engine.js:203 refuses to launch while it is set.
Scenario: the disk fills once (one failed append), he frees space, then the engine crashes or he presses Try again. Every attempt says "Can't write the log file: ENOSPC..." until he quits the app, so Try again cannot succeed.
Fix: in _launch, retry the log (for example, clear error and re-run the folder check) before refusing.

4. PENDING CHECKS ON A REAL MAC (the lead or a delegate runs them; he only looks at the result)
- An idle Log Out completes. F1's fix assumes that a before-quit Electron does not prevent lets macOS terminate the app. That rests on Electron's internals and has never been watched on a Mac.
- A login launch opens no window (wasOpenedAtLogin on macOS 13 and later). Also check what the Start at login tick shows right after ticking it: if macOS reports requires-approval, the tick shows off with no words saying why.
- The default title bar over the dark-only dashboard (ui/src/index.css sets `color-scheme: dark`). On a Mac in Light mode this is a light strip above a dark app. It is acceptable until 2c, but he will see it.
- The header style on his macOS version: the section header on 14 and later, a greyed line on 13. Also the quit question shown as a sheet when the window is visible (the mockup draws a standalone box), the tray dots in light and dark, and the Dock modes.
- Not his to act on: G4's button choice and G1's sort order are the lead's calls.

5. COULD NOT CHECK; WHAT I INSPECTED
Not run, by instruction: npm test, the e2e, Electron. For the lead: `cd ~/labs/projects/anyscribe-wt/mac-shell/desktop && npm test`. Everything Mac-specific above is unchecked. I did not open the mockup in a browser; I read its HTML for sections 2, 6, 7, 9 and "For the build". I left lifecycle and race depth (the queue, the pid check, the group kills) to the correctness re-check, and checked only what he would see.
Inspected: the brief; ask.md, spec.md, target.md, proof.md (all of it, including "Round 1 fixes"), lens.md, declined.md, findings.md, review-log.md, fix-plan-r1.md; delta-r2.patch (the README, main.js, architecture and journal parts in full); the current desktop/src/main.js, logic.js and engine.js in full; start.html (drag strip); the C8 and F7 lines of e2e.js; electron.d.ts for LoginItemSettings and the menu item 'header' type; and, read-only from 2a at 4d9bb42, web/jobs.py (2 workers, the 50-row list), the dashboard title, the index.css colour scheme, and routes (no batch submit).
Node one-liners (read-only): menuModel and menuLayout for the 7-finished case, the 12-active case and the quitting case.

Skipped: the fake-engine and unit test bodies, and the icon images. Risk to pass on: F1 (idle logout) and the login launch are still unseen on a Mac, and they are the first things he will hit.
~~~~

# Round 3


## report-sol-r3.md

~~~~
**NOT YET.** The rebuild fixes the stale health response, HTTP shutdown, logging and menu findings. A plain `stop()` can still be overridden by a restart already waiting for the old engine to exit.

Reviewed shell **2383f26** against engine **4470a4d**. The shell worktree’s code matches the reviewed commit; later commits change review files only.

| Prior finding | Status | Evidence |
|---|---|---|
| A1 | FIXED | Exit clears the current run before readiness resumes. A delayed health reply produced `starting, stopped`, never `running`. |
| A2 | FIXED | Stop uses stdin and process-group signals, with no HTTP shutdown request. |
| A3 | FIXED | Each launch probes appendability; successful probes and writes clear the error. |
| A4 | PARTLY | Stop during the jobs read is handled. Stop during the subsequent termination wait still permits relaunch. See new A1 below. |
| R2, engine round 3 | FIXED | Every spawned run’s exit handler signals its process group, including exits before readiness. Real helper removal remains supplied test evidence. |
| G1 | FIXED | Failed completions sort first, then newest; reproduced with seven completions. |
| G2 | FIXED | README and journal disclose that any quit question cancels logout. Native behavior remains unchecked. |
| G3 | FIXED | Waiting rows are capped at five plus “and N more”; running rows remain visible, including while quitting. |
| G4 | FIXED | Unknown status offers the approved three choices; the header gains “not answering” after three failed reads. |
| G5 | FIXED | Journal names and descriptions reflect the rebuilt supervisor. |
| G6 | FIXED | A repaired log is probed again successfully; the old error no longer blocks retry. |

**New A1. should-fix | CONFIRMED | Stop does not cancel a restart’s pending relaunch.**

Where: engine.js:357 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:357`), particularly `_cancel()`, `_onExit()` at line 317, and `restart()` at line 419.

Scenario:

1. `restart()` obtains an idle jobs list, sets `restartRequested = true`, and starts terminating the old child.
2. Before that child exits, `stop()` is called.
3. `_cancel()` leaves `restartRequested` true.
4. The child exits. `_onExit()` launches its replacement because that flag remains true and the app is not quitting.

A read-only Node probe exercised the actual supervisor methods with in-memory children, logging, network checks and signal functions. No process or server was started. Its output was:

```text
Before stop:
state: restarting
restartRequested: true

After stop completed:
restartResult: {"ok":true,"reason":null}
state: running
spawnCount: 2
ownedPid: 90000001
```

The new regressions at engine.test.js:457 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/test/engine.test.js:457`) stop while the **jobs read** is suspended. They never reach this later termination phase.

**Fix:** make an explicit stop revoke the pending relaunch, while preserving restart’s own internal termination request. Add a regression that holds the old child alive after restart sends SIGTERM, calls `stop()`, then emits exit. Assert that stop finishes with no replacement child and state `stopped`; mutation-test that protection.

This is a supervisor contract defect. `main.js` currently uses `stopForQuit()`, whose permanent quitting flag prevents this relaunch. I separately reproduced that protection. This finding does **not** establish an engine surviving an actual Electron quit.

**Pending owner checks**

No owner decision is required for the correction. The builder or lead still needs to verify on a Mac:

- Idle logout and shutdown complete.
- Login launch opens no window; Login Items approval and external changes are reflected.
- Quit dialogs appear visibly and all three choices work with real jobs.
- Window dragging, Dock modes, menu headers and light/dark tray indicators work.

After technical verification, Rishabh should judge the actual startup screen, menu and quit flow. Those implementation checks are not his repair tasks.

**Verification limits and inspected material**

I read the named packet, complete round 3 delta, prior reports, verdict ledger, binding plans, diagnosis, proof and declined list. I inspected the supervisor, Electron wiring, logic, preloads, startup page, supervisor and logic tests, fake engine, e2e, icon generator, relevant documentation and approved mockup sections. I traced the exact engine commit’s health, jobs, cancellation, stdin watcher and process-group exit paths. Engine source at the e2e’s **62cba9c** matches **4470a4d**.

Read-only probes confirmed the dispositions described above. The desktop/building-documentation delta passes `git diff --check`. No files were changed.

I did not run test runners, Electron, servers, real signals or mutation tests, as prohibited. The reported **49 passing tests and 11 e2e steps remain supplied evidence**, not independently rerun results. Native rendering, real-job quitting and live helper cleanup were not independently verified.

After adding the missing regression, run:

```sh
cd ~/labs/projects/anyscribe-wt/mac-shell/desktop
npm test
```

Repeat the integrated e2e against the exact engine snapshot. The packet describes an exported engine and interpreter wrapper but does not provide the wrapper’s path or complete invocation, so that integrated command is not reproducible exactly from the supplied proof.
~~~~


## report-opus-r3.md

~~~~
FIT REVIEW, round 3: Mac app shell (feat/mac-app-shell at 2383f26; HEAD ffa8337 adds only review files, checked with git diff --stat)

1. VERDICT: CONDITIONAL on G7. Pressing Stop and Quit while the engine is not answering can freeze the app for many seconds with nothing on screen. The fix is one line. Everything else below is a nit or a check on a real Mac.

The round 3 changes are still the job he asked for, and nothing from slice 2c has crept in. These parts match the approved mockup: the menu separators (checked with a node one-liner on logic.menuLayout: Ready has no separator between the header and Open; rows are followed by a separator before Open; the quitting menu has none between "Don't quit" and "Stop and quit now"); the header (grey section header on macOS 14 and later, a greyed item before that, matching the mockup's .mi.hd style); the approved quit box, unchanged word for word. The dashboard window keeps the default title bar (main.js:167), as F5 settled. The rebuilt supervisor is smaller than round 2's: the queue, generations, verified and the HTTP shutdown are all gone. I found nothing more to delete there.

2. STATUS OF EARLIER FINDINGS
- A1: FIXED. _onExit clears this.run first (engine.js:307). _waitReady checks the gate again after the health answer (engine.js:263), so a late "ours" is dropped.
- A2: FIXED. The stop is stdin.end, then SIGTERM to the group, then a SIGKILL timer (engine.js:382-392). The only fetches left in engine.js are health, jobs and cancelJob.
- A3: FIXED. AppLog.probe() appends nothing to the file before every launch (engine.js:221). write() clears the error after a good write.
- A4: FIXED. restart() checks the gate after reading jobs (engine.js:408). A second restart is refused, not queued (engine.js:399).
- R2 (engine round 3): FIXED, and broader than the design: the exit handler kills the group on every exit (engine.js:311). proof.md discloses this and gives the reason.
- G1: FIXED. Failed jobs sort first, then newest (logic.js:166-169). The test checks that the Failed row itself appears, not just a count.
- G2: FIXED. README lines 99-101 and journal lines 75-77.
- G3: FIXED. Waiting rows capped at 5 plus "and N more", running rows always show, the quitting menu has the same cap. See G8.
- G4: FIXED as the lead specified. The unknown-list box now has Quit When Done (default), Stop and Quit and Cancel, and the header gains " · not answering" from the third failed read in a row. This routes the most likely "engine not answering" case through the slow stop path (G7), and creates the header in G9.
- G5: FIXED. A grep for decideQuit and "roll forward" in the journal finds nothing; the round 3 section is there.
- G6: FIXED. Same change as A3.
New defects the fixes introduced: G7 (from G4), G8 (from G3), G9 and G10 (from G4).

3. NEW FINDINGS, most severe first (numbered on from round 2's G1 to G6)

G7. should-fix. The timing is CONFIRMED by reading the code. That the engine stops answering while it transcribes is PLAUSIBLE.
Where: main.js:288-291, stopAndQuit.
What happens: stopAndQuit first reads the job list (up to a 2 s timeout). It then sends one cancel per active job in the last list it knew, one after another, each with its own 2 s timeout. The window stays up and nothing changes on screen. A second Cmd Q does nothing, because the app is already quitting. Before round 3, the unknown box offered Quit Anyway, which quit at once. Now its Stop and Quit, and the menu's "Stop and quit now", run this loop exactly when the engine is least likely to answer.
Scenario: the engine is busy and not answering. Its last known list held 2 running and 6 waiting jobs. He clicks Stop and Quit and nothing visible happens for about 2 + 8 x 2 = 18 s. He will think the app hung and force-quit it. No transcript is lost (the engine follows a killed app), but it looks broken.
Fix: send the cancels in parallel, `await Promise.all(jobs.filter(logic.isActive).map((j) => engine.cancelJob(j.job_id)))`, which caps the wait at about 4 s. Optionally, hide the windows at the start of stopAndQuit so the click visibly does something.

G8. nit. CONFIRMED (node one-liner on menuModel and menuLayout).
Where: logic.js:138 and 174. With waiting and finished jobs both present, the menu shows two bare "and N more" lines; the first sits directly above the Failed row ("W4 · Waiting / and 3 more / Fin 0 · Failed / Fin 6 · Saved ... / and 2 more") and reads as "3 more failed".
Fix: label them "and 3 more waiting" and "and 2 more finished", and update the two test strings.

G9. nit. CONFIRMED (the test at logic.test.js:281 asserts this exact text).
Where: logic.js:126. An idle engine that stops answering shows "anyscribe · Ready · not answering": a contradiction that claims more than the app knows.
Fix: in the idle case, replace the state word instead of appending ("anyscribe · Not answering"); keep the suffix for Transcribing and Quitting.

G10. nit. CONFIRMED.
Where: main.js:300, `if (choice === 'quit') return finalQuit();` is dead since G4; the two branches of quitDecision (logic.js:251-253) now differ only in which box they use.
Fix: delete the dead line; optionally merge the branches.

4. PENDING CHECKS ON A REAL MAC (the lead or a delegate runs these; he only looks at the result)
- An idle Log Out completes, and a launch at login opens no window (wasOpenedAtLogin on macOS 13 and later).
- The unknown-list box on screen (a sheet when the window is visible; the mockup draws a standalone box).
- The section header on his macOS version.
- The default title bar over the dark dashboard: a light strip in Light mode until 2c.
- The tray dots in light and dark, and the three Dock modes.
- Not his to act on: G7 to G10 are the lead's calls.

5. COULD NOT CHECK; WHAT I INSPECTED
Not run, by instruction: npm test, the e2e, Electron. I did not measure G7's delay live (a check: a fake engine that accepts connections but never answers, two active jobs in the last list, then time stopAndQuit). Mac rendering unchecked; lifecycle race depth left to the correctness re-check; A1 to A4 and R2 marked from reading the code.
Inspected: the brief and the whole packet (ask, spec with "Round 3 design", target, lens, declined, diagnosis-r3, fix-plan-r1, review-log, findings round 2, proof "Round 3 fixes"); the delta for logic.js, main.js, the README and logic.test.js; current logic.js, main.js and engine.js in full; the architecture "Mac app shell" section and journal lines 60-135; mockup sections 2, 6, 7, 9 and "For the build" as HTML including the header CSS. Node one-liners (read-only): menuModel and menuLayout for 2 running + 8 waiting + 7 finished, for "not answering" while idle and while quitting, for an empty quitting menu, and quitDecision for an unknown list.
Skipped: the supervisor test bodies and the icon images. A risk to pass on: G7 is the one thing he would notice. The others are wording.
~~~~

# Round 4


## report-sol-r4.md

~~~~
**GOOD TO GO for the round-4 changes in this development slice.** All five requested fixes are present. I found no new runtime defect. Native Mac validation remains pending.

Reviewed shell **787bfa1** against engine **b22df16**. Current shell HEAD **cd71ebf** differs only in review files; the inspected engine source matches its target.

| Finding | Status | Evidence |
|---|---|---|
| S3-A1 | **FIXED** | `stop()` revokes `restartRequested`. My in-memory reproduction finished stopped, with one child ever created and no current run. Omitting the guard in memory reproduced the second launch and successful restart. |
| G7 | **FIXED** | Both Stop and Quit actions call `finalQuit()` directly. `will-quit` calls `stopForQuit()`, which closes stdin, signals the owned process group and permanently prohibits relaunch. No job read or cancel loop remains in either action. |
| G8 | **FIXED** | Probes returned distinct “and 5 more waiting” and “and 2 more finished” rows, including when both appear together. |
| G9 | **FIXED** | Idle failure returned “anyscribe · Not answering”; Transcribing and Quitting retain the suffix. |
| G10 | **FIXED** | The dead `choice === 'quit'` branch is gone. Both question variants expose only the three supported choices. |

New findings:

**A1. nit | CONFIRMED | The README describes the new header too broadly.**

Where: desktop/README.md:103 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/README.md:103`).

It says the header reads “anyscribe · Not answering” when no job is active. With an unseen finished job and three failed reads, the actual result is:

```text
anyscribe · 1 saved · not answering
```

The implementation matches the disclosed round-4 choice to retain the finished summary. Change the README condition to “when otherwise showing Ready.” No runtime correction is needed.

The quit-path evidence supports the design, with a timing limit: the reported **39 ms measures app exit against the fake engine**, not termination of real transcription work. At engine `b22df16`, cancellation is an in-memory flag checked at progress events. Removing those requests therefore removes no persistent cancellation record. The real engine retains its process-group hard exit and stdin watchdog, whose grace period is **10 seconds**. Real-job termination should not be reported as independently measured in milliseconds.

Pending owner checks:

- The builder or lead should verify idle logout/shutdown, login launch without a window, Login Items approval changes, real-job quit choices, window dragging, Dock modes, native menu headers and light/dark tray rendering on Mac.
- Rishabh then judges the actual startup, menu and quit experience. Technical verification and the documentation correction are not his repair tasks.

Verification and limits:

I read every file named directly by the brief, the approved mockup text, the changed source and relevant regression bodies, e2e and fake-engine code, bridges, startup page, README, architecture section and journal. I traced the target engine’s jobs, cancellation, stdin watcher, signal handling and process-group exit paths.

Read-only Node probes reproduced the restart guard’s effect and menu results. The reviewed source/documentation delta passes `git diff --check`.

I ran no test runner, Electron instance, server, real signal or filesystem mutation. **50 passing tests and 12 e2e steps remain supplied evidence.** The suite command is:

```sh
cd ~/labs/projects/anyscribe-wt/mac-shell/desktop
npm test
```

The packet omits the interpreter-wrapper path used for the exact-engine e2e, so its complete invocation cannot be reconstructed from the supplied proof.
~~~~


## report-opus-r4.md

~~~~
FIT REVIEW, round 4: Mac app shell (feat/mac-app-shell at 787bfa1; HEAD cd71ebf adds only review files, checked with git diff --stat 787bfa1 HEAD)

1. VERDICT: GOOD TO GO (fit).

Round 4 is still the job he asked for, and nothing from slice 2c has crept in. Every change in it either deletes code or changes wording. Stop and Quit now does what the approved quit box (mockup section 7) implies: the app goes away at once, and the box's own sentence, "To finish a stopped one later, transcribe it again", stays true. The two new wordings fix contradictions I raised in round 3. The other things that rejoined this review all still match the mockup, checked again against the code and with node one-liners on logic.menuModel and menuLayout: the default title bar (main.js:167); the unknown-list question (three buttons, Quit When Done the default); separators (none between the header and Open when there are no rows, one before Open when there are rows, none between "Don't quit" and "Stop and quit now"); the header style (main.js:208); the 5-row cap. I found two nits and nothing worse.

2. STATUS OF ROUND 3 FINDINGS
- S3-A1: FIXED. engine.js:360 clears restartRequested in stop() before _cancel. When the old engine then exits, _onExit (engine.js:317) sees no restart was asked for, launches nothing and sets stopped. A seam test was added (engine.test.js:534), and proof.md records the mutant failing on "actual: true, expected: false". stop() has no production caller (grep finds none in src), so this protects the supervisor's contract, not any path he can reach today.
- G7: FIXED. Both the question's Stop and Quit (main.js:296) and the menu's "Stop and quit now" (main.js:218) now call finalQuit() directly. engine.cancelJob and stopAndQuit are gone. will-quit calls stopForQuit: stdin end and SIGTERM to the group, sent synchronously before the app exits. On the engine side (b22df16, app.py:244-268) every way out ends in _exit_hard, which SIGKILLs its own group, so no job survives. e2e step 10 proves the question was actually asked (the stand-in prints "ASKED Stop and Quit"), asserts no POST reached the engine and that the engine pid is gone. The 39 ms figure and the 2484 ms mutant are the builder's numbers, not rerun by me.
- G8: FIXED. Checked with a one-liner: "W4 · Waiting / and 3 more waiting / F0 · Failed / ... / and 2 more finished". The line above the Failed row no longer reads as more failures.
- G9: FIXED. Idle and not answering reads "anyscribe · Not answering". Transcribing, Quitting and the finished-while-closed header keep the " · not answering" suffix.
- G10: FIXED. The dead `choice === 'quit'` line is gone. quitDecision's two branches now return the same choices, which is harmless.
New defects the fixes introduced: none that he would see. One cosmetic leftover, G11.

Quit path with no cancels, traced, nothing found: Stop and Quit while the engine is not answering; Stop and Quit from the "Quitting when these finish" menu, tray or Dock; the question open while a menu Stop and Quit also fires (allowQuit makes the second before-quit a no-op); the engine crashing and restarting while the question is open (stopForQuit takes the current run, and quitting blocks a relaunch); a stubborn engine (the engine's own stdin-EOF timer leads to _exit_hard, same as before round 4). The engine keeps jobs only in memory (web/jobs.py) and its cancel is a flag read at the next progress event (jobs.py:112-119, 166), so the dropped cancels changed nothing that lasts.

3. NEW FINDINGS (numbered on from G10)
G11. nit. CONFIRMED. desktop/src/engine.js:438-439, two blank lines where cancelJob used to be. Fix: delete one.
G12. nit. PLAUSIBLE, not reachable today. engine.js:430 with _onExit:320. When stop() overtakes a restart, the restart returns ok false with the fallback reason "The engine didn't start.", because a cancelled exit sets lastExit to null. Nothing calls stop() outside the tests. If slice 2c wires stop() and shows restartEngine()'s reason, he would read "didn't start" after a deliberate stop. Fix when 2c needs it: return "The engine was stopped." when the run was cancelled without a restart; or record it as a 2c note.
Out of scope, for the backlog: every hard stop leaves the in-progress download in ~/.anyscribe/tmp. The cleanup is orchestrator.py:219-222's finally block, which a SIGKILL skips, and nothing sweeps ~/.anyscribe/tmp. Large video downloads could pile up. Engine-side fix: sweep the folder at startup.

4. PENDING CHECKS ON A REAL MAC (the lead or a delegate runs them; he only looks at the result)
- Stop and Quit with real jobs running: the app disappears at once, no python, yt-dlp or ffmpeg left, the next launch says Ready.
- The cap lines and "anyscribe · Not answering" in the real menu on his macOS version.
- Carried over: an idle Log Out completes; a launch at login opens no window; the unknown-list box on screen; the default title bar over the dark dashboard; the tray dots in light and dark; the three Dock modes.
- Not his to act on: G11 and G12 are the lead's calls; the tmp-folder note is an engine backlog item.

5. COULD NOT CHECK; WHAT I INSPECTED
Not run, as the brief requires: npm test, the e2e, Electron. The 50 passing tests, the 12 e2e steps, 39 ms and the mutant results are supplied evidence. Mac rendering, real logout and real-job quitting are unchecked. Race depth left to the correctness re-check.
Inspected: the brief and the full packet (ask, spec with "Round 3 design" and "Round 4 design", target, lens, declined, diagnosis-r3 and diagnosis-r4, review-log, fix-plan-r1, the round 3 reports, proof's "Round 4 fixes"); delta-r4.patch in full; current main.js in full; logic.js lines 100-300; engine.js stop, _cancel, restart, jobs and _onExit; grep of README, architecture.md and the journal for stale cancel or wording claims (none); mockup sections 6, 7 and "For the build"; the engine at b22df16 (app.py exit door, jobs.py cancel, orchestrator temp cleanup, paths.py); node one-liners on menuModel, menuLayout and quitDecision for the listed cases.
Skipped: the icon images and the bodies of the other supervisor tests. Risk to pass on: none for fit. The tmp-folder pile-up is the one thing he might notice in time, and it is not this PR's.
~~~~
