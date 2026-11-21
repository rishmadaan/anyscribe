# Proof: phase 2c-ui, the dashboard's Mac screens

Implementer, round 0. Worktree `~/labs/projects/anyscribe-wt/mac-2c-ui`, branch `feat/mac-app-2c-ui`, based on 6dc70b2 (checked before editing). Head: see the last commit on the branch (the commit that adds this file).

## What was built, screen by screen

| Spec item | Built | Where |
|---|---|---|
| Helper module for the bridge, types for bridge v2 and its amendments | Yes | `ui/src/desktop.ts` (the only reader of `window.anyscribeDesktop`) |
| 1. Layout inside the app: no Shutdown; macOS drag strip and top padding | Yes | `components/Layout.tsx`, `.app-drag` in `index.css` (28 px strip above the logo; the logo row is draggable too, links and buttons inside are no-drag) |
| 2. Engine trouble banner on every page | Yes | `components/EngineBanner.tsx` (restarting; Running again, naming the watched job only when there was one; keeps stopping with code or signal, Restart engine with the bridge's refusal reason, Copy details, Troubleshooting guide) |
| 3. Settings "This Mac" in place of Startup | Yes | `components/ThisMac.tsx` (all rows; Updates shows the version only, as the spec says) |
| 4. First launch: old launcher question, result card, Terminal card (wizard last step / "One more option"), marked once | Yes | `App.tsx`, `components/MacCards.tsx`, `OnboardingWizard.tsx` (step `terminal` after Finish saved) |
| 5. Transcribe inside the app: Browse by path, drop overlay, Dock files | Yes, with one limit | `components/URLInput.tsx`, `Layout.tsx`, `pages/TranscribePage.tsx`. The overlay cannot name the file during a real drag (see "Spec problems") |
| Bridge v2 amendments (three messages from the coordinator, recorded in `bridge-v2.md`) | Yes | see "Amendments" below |
| Docs | Yes | `docs/building/architecture.md` (Web UI layer: "The dashboard inside the Mac app", one coverage-matrix row), `docs/building/journal/2026-11-20-mac-app-2c-ui.md`, `_index.md` row. `docs/user` unchanged: no browser behaviour changed |
| Rebuilt bundle | Yes | `src/anyscribe/web/static/` |

Kept: `index.css` tokens and today's components (the This Mac rows reuse the Settings card, `Toggle` moved unchanged into `components/Toggle.tsx`), the sidebar credits and KraftedX mark (checked present in the app), the wizard's close-asks-during-download behaviour (untouched; the Terminal step only appears after Finish has saved, when no download watch is open). BACKLOG items L1 and R2L1 not touched.

## Amendments (from the coordinator, during the build)

Recorded in `bridge-v2.md` under "Amendments" and "Amendment 2" (both committed with this branch).

1. `terminal.turnOff({choice: "keep-current" | "restore"})` answers `needsChoice`: wired to Keep current command and Restore previous command. Checked: `AMEND 1: the two answers reach turnOff({choice})`.
2. `ok: true` with a `reason` is information: the Settings row shows it as a plain line (not red), the ready card and the path card show it as a note. Checks `AMEND 2: ...` (row class has no `text-red`; ready card carries it).
3. bash `addToPath` refusal with the line to add by hand: the reason in red, the line in a selectable box (`select-all`), and no second "Add it for me". Checked for a returned line equal to ours and for a different one.
4. `occupant`: "Switch to this app's copy" only when `occupant` is set (Settings link, toggle and first-launch card); without it the status reason shows, and the switch writes ours with `replace: false`. Checks `AMEND occupant: ...`.
5. `uses.via`: "Terminal runs this app's anyscribe" only when `via` is "app"; `uses: null` shows the reason. Checks `AMEND uses: ...`.
6. Old launcher refusal (`ok: false`, no pieces): the reason under the question or the Settings row, no checklist. Superseded by amendment 2's wording; checks `AMEND launcher: ...` and `AMEND2: a refusal ...`.
7. `startAtLoginCarriedOver` false with a reason: the Removed card gives the reason instead of "This app now starts at login". Checks `AMEND carry-over: ...`.
8. Amendment 2: removal restarts the engine and the page reloads mid-call. `removeOldLauncher()` notes the start (localStorage); after the reload `App` shows `oldLauncher.status().lastRemoval` once, only when newer than the note (`claimRemoval`), for removals started from the question or from Settings. The stub keeps `lastRemoval`, emits "restarting" and reloads the page 600 ms into `remove()`. Checks `AMEND2: ...`: the restarting banner covers the gap, the page really reloaded (navigation type `reload`), Removed or the checklist after the reload, Try again reloads again and ends Removed, the result never repeats after another reload, an older `lastRemoval` is never shown, a refusal answers at once without a reload.

## Checks

Everything is in `checks/` beside this file:
- `check_ui.py`: the click-through (`/usr/bin/python3 check_ui.py`; `--only`, `--no-shots`). Starts engines from `~/labs/projects/anyscribe/.venv/bin/python` with throwaway HOMEs (`tempfile.mkdtemp`) and free ports, stops each by its pid, headless Chromium only. Engine A serves this worktree's bundle (`PYTHONPATH` = worktree `src/`) with setup finished by a fake key; B and B2 fresh HOMEs for the wizard; C is the main checkout's code and bundle (6dc70b2) on A's HOME, for the browser baseline.
- `stub.js`: the stub `window.anyscribeDesktop`, injected before load; records every call (kept across a reload) and can be put into every state, including engine events (`__emit`), Dock files (`__openFile`, also before load) and the reload around removal.
- `drag_probe.py` + `drag_probe.out`: what a real browser drag exposes before the drop.
- `mutate.py` + `mutate.out` + `mutants.json`: the mutation run.
- `run-full.out`: the last full click-through log; `shots/` (gitignored, regenerated by the script) holds the screenshots.

### Build and lint

`npm run build` and `npm run lint` in `ui/`: both clean (no errors, no warnings) at the final commit.

### Click-through

`checks/run-full.out`: **173 passed, 0 failed** across 12 scenarios (browser, browser_pixels, app_layout, drop, browse, open_file, banner, settings, first_launch, first_launch_marked, wizard, wizard_browser).

Every control in every state was clicked: each check names what was clicked, what the stub recorded and what the screen then said. Real engine traffic is checked too (the drop, Browse and Dock submissions are the actual `POST /api/transcribe` bodies; no `POST /api/upload` in the app; one in the browser). Two routes are served by the check instead of the engine: `GET /api/jobs` (the main checkout's engine predates the job list from 2a; the fallback HTML it returns would read as "unknown") and, for jobs that must stay running, `POST /api/transcribe` plus a silent job WebSocket.

Browser mode (no bridge): Shutdown present, Startup present (the engine says autostart is supported here), no This Mac, no drag strip, no overlay on a drag, a drop submits nothing, Browse uploads as today, the wizard's Finish closes with no Terminal step. Pixel check: `/`, `/history` and `/settings` at 1440, 1000 and 390 px are identical to the main checkout's bundle. Two kinds of noise vary between two loads of the same bundle, so both runs block web fonts (they arrive from Google at varying times) and hide the caret; a pair that differs is shot again up to three times and passes only on an exact match (one `/history` 1440 load differed by 9 pixels at one level of antialiasing and matched on the next load).

### Screenshots

59 states, each at 1440, 1000 and 390 px (177 images, plus the pixel-comparison pairs). I read every one, as one sheet per state with the three widths side by side. Notes from reading them:
- Today's look holds: same card, border, type and amber accents; the This Mac rows wrap under 640 px like the mockup's narrow layout (toggle under the label).
- The sidebar credits and the KraftedX mark are present at every width; the drag strip adds 28 px above the logo on macOS only.
- On a phone-width window the drop overlay covers the stacked sidebar too (fixed to the window); fine for an app window, which is never that narrow.
- After a bash refusal the path card still begins "anyscribe can add this line to ~/.zprofile ..." above the red reason. Readable, but the first paragraph is now stale; a reviewer may want it swapped for the reason.
- The other-copy card without an occupant says where the other copy is twice (from `uses` and from the status reason).
- `first-launcher-removing`: only the 1440 shot catches the restarting banner and the spinner on Remove; the page has reloaded by the 1000 and 390 shots (the stub reloads 600 ms in), which show the Removed card instead.

### Drag probe

`drag_probe.out`: a CDP drag (the browser's own drag path) over a page gives `types: ["Files"]` and `files: 0` on dragenter and dragover, and the file (name and size) only on drop. Chromium 156.

## Mutation results (the four guards)

`checks/mutate.py`, output `checks/mutate.out`, details `checks/mutants.json`. Each mutant was written into `ui/src`, built with `npm run build`, run against its scenarios, then the file was restored byte for byte, rebuilt and run again. **15 of 15 killed; every restored run passed its whole scenario.**

| Guard | Mutant (what the guard removal does) | Check that failed with the mutant (quoted) | Restored |
|---|---|---|---|
| 1. Nothing app-only without the bridge | `bridge/settings`: Settings renders This Mac without the bridge (`desktop ||` …) | FAIL `Startup section as today` | PASS |
| 1. Nothing app-only without the bridge | `bridge/drag-strip`: drag strip without the macOS bridge check | FAIL `no drag strip` | PASS |
| 1. Nothing app-only without the bridge | `bridge/drop-listener`: window drag/drop listeners attached without the bridge | FAIL `dragging a file shows no overlay` | PASS |
| 1. Nothing app-only without the bridge | `bridge/shutdown`: Shutdown shown inside the app | FAIL `app: no Shutdown button` | PASS |
| 1. Nothing app-only without the bridge | `bridge/first-launch`: first-launch questions run without the bridge | FAIL `Shutdown button present`; scenario stopped: `Error: Page.evaluate: TypeError: Cannot read properties of null (reading 'dispat` | PASS |
| 2. addToPath only after the person's yes | `addToPath/settings-row`: Settings row's Add it for me calls addToPath directly | FAIL `GUARD addToPath: the row's button only asks`; scenario stopped: `TimeoutError: Locator.click: Timeout 30000ms exceeded.` | PASS |
| 2. addToPath only after the person's yes | `addToPath/after-turn-on`: Turn on calls addToPath itself when the result is path-missing | FAIL `GUARD addToPath: not called before the yes` | PASS |
| 3. First-launch questions never repeat once marked | `repeat/launcher-flag`: launcher question ignores oldLauncherAsked | FAIL `GUARD repeat: not asked again after reload`; FAIL `GUARD repeat: both marked, nothing asked`; scenario stopped: `TimeoutError: Locator.click: Timeout 30000ms exceeded.` | PASS |
| 3. First-launch questions never repeat once marked | `repeat/terminal-flag`: Terminal card ignores terminalAsked | FAIL `GUARD repeat: neither question again after reload`; FAIL `GUARD repeat: both marked, nothing asked`; scenario stopped: `TimeoutError: Locator.click: Timeout 30000ms exceeded.` | PASS |
| 3. First-launch questions never repeat once marked | `repeat/keep-marks`: Keep both no longer marks the question | FAIL `GUARD repeat: not asked again after reload` | PASS |
| 3. First-launch questions never repeat once marked | `repeat/terminal-marks`: Terminal answers no longer mark | FAIL `GUARD repeat: neither question again after reload` | PASS |
| 3. First-launch questions never repeat once marked | `repeat/removal-result-once`: post-reload result does not clear its note | FAIL `AMEND2: the result never repeats after another reload` | PASS |
| 3. First-launch questions never repeat once marked | `repeat/removal-result-newer`: post-reload result ignores the 'newer than the question' test | FAIL `AMEND2: an older lastRemoval is never shown` | PASS |
| 4. Restart engine disabled while transcriptions run | `restart/disabled`: Restart engine not disabled by running jobs | FAIL `GUARD restart: disabled while transcriptions run`; FAIL `GUARD restart: a click while disabled calls nothing` | PASS |
| 4. Restart engine disabled while transcriptions run | `restart/pending-counts`: pending jobs not counted as running | FAIL `engine with jobs line` | PASS |

Notes on the mutants:
- `bridge/settings`: This Mac needs the bridge, so without the guard the browser's Settings page crashes instead of showing This Mac; the check that sees it is "Startup section as today". An earlier run listed "no This Mac section" too, which a blank page also passes; it was taken off the list rather than counted.
- `bridge/drop-listener`: the first version of this mutant crashed the whole page (the open-file subscription needs the bridge) and so proved nothing about the drop listener; the counted version removes only the listener guard.
- Equivalent mutants left out on purpose: the banner's and Browse's `desktop` checks cannot render anything without a bridge (no status ever arrives; there is no path to read), so removing them changes nothing a check can see.
- First run of the set: two mutants did not compile (`tsc` unused-variable) and stopped the run; they were rewritten to compile, never counted as kills.

## New wording (not in the mockup)

Every sentence below is mine, for a state the bridge can produce that the mockup did not draw. For review.

Engine banner
- "The engine was stopped by {signal}" / "The engine exited with code {n}: {reason}" (the mockup has only "exited with code 1; the reason wasn't reported"), and "The engine stopped; the reason wasn't reported" when neither code nor signal came.
- "Its log is in ~/.anyscribe/logs/app.log." replaces "Copy details includes its log." (see Spec problems).
- Fallbacks: "The engine couldn't be restarted.", "Couldn't copy the details.", "Copied".
- "Running again" with no watched job: the heading and Dismiss only.

Old launcher
- Question without a login item: the mockup's sentences minus "and a login item that starts it" and "This app will start at login in its place."
- Removed card without carry-over and without a reason: "Removed the old launcher, its login item and its menu bar icon." alone.
- Checklist when the menu bar icon is not the piece left: "Try again. If it still doesn't finish, Copy details shows what was left."
- First-launch checklist adds a "Close" link (the mockup's card has no way out).
- Fallback: "The old launcher couldn't be removed."

Terminal
- "installed separately by another anyscribe app" (via "app"), and no "with ..." for an unknown installer.
- "anyscribe can add this line to ~/.zprofile (~/.bash_profile if your Terminal uses bash):" (the mockup names ~/.zprofile only; see Spec problems).
- "The line was added, but Terminal still can't see the command. Open a new Terminal window and check, or add it by hand."
- Settings row: "On. Terminal can't see the command yet: it doesn't look in ~/.local/bin." with "Add it for me"; "On. ... Claude Code isn't on this Mac."; "On." alone followed by the status reason (ours written but another first, or the shell not asked); "Off. anyscribe isn't in Terminal." without the skill clause when no skill was involved.
- Fallbacks: "That didn't work.", "anyscribe couldn't add the line.", "anyscribe couldn't turn this on.", "anyscribe couldn't turn this off.", "The skill still couldn't be installed.", "The anyscribe command was changed since it was turned on."

Settings
- "On. anyscribe starts in {the menu bar | the menu bar and the Dock | the Dock} when you log in, with no window." (the mockup draws Off only).
- "macOS hasn't turned it on yet. If it asks, allow anyscribe in System Settings, under Login Items." (turned on here, the system still reads off).
- Engine: "Starting.", "Restarting.", "Stopped." (plain stop), "Running · 1 transcription."
- Updates: "Version {v}." only (update states are phase 3).

Transcribe
- "Up next: {names}. It starts when this one finishes." / "They start in turn when this one finishes." (a dropped or Dock file arriving while a job runs here).

Wizard
- The Terminal step reuses the title "All set" (setup is saved by then) above the card's own heading.

## Spec problems (said, not silently built)

1. **The drop overlay cannot show the file's name and size.** The mockup draws "team-sync-recording.m4a · 48 MB" while dragging; Chromium (Electron's renderer) does not give a page the file until the drop (`drag_probe.out`). Built: "Drop to transcribe" always, the name and size only when the browser gives them (never in a real drag). Showing them would need the app to learn the dragged file another way; I know of no Electron API for that.
2. **"Copy details includes its log" is not possible from the dashboard.** The bridge has no call that reads the log (the start window's copy is not exposed to the dashboard). Built: Copy details copies the version, state, last exit and the log's path, and the banner says where the log is. A bridge call (for example `copyDetails()`) would let the mockup's sentence stand.
3. **The path card cannot know the file before asking.** `terminal.status()` does not say the login shell, so the dashboard cannot name ~/.zprofile or ~/.bash_profile before `addToPath()` answers. Built: both named, as above. A `profile` field in the status would let the card name one.
4. **A transcription watched across an engine restart stays "running" on the Transcribe page.** The restarted engine no longer knows the job, the WebSocket fails, and the page's fallback poll ignores a 404, so the progress view spins until the person clicks New or leaves; the banner's "Check History before starting it again" is the only guidance. Not built (outside this slice's words); a small fix in `useJob` (treat 404 as "the engine no longer knows this job") would also change the browser, so it needs its own yes.
5. **Restart engine when the job list cannot be read.** The spec says disabled while transcriptions run; when `GET /api/jobs` fails the dashboard cannot know. Built: enabled, and the app's own refusal ("couldn't check for running transcriptions") is shown. Disabling it there would also block the restart when the engine is wedged, which is when it is needed.

## What I could not check

- Nothing ran inside the real Electron app: the bridge is a stub, so the 2c-app side (its real results, the reload timing, `hiddenInset` traffic lights against the 28 px strip, `app-region` dragging the window, the native file picker) is unverified here. The traffic-light clearance is a guess at 28 px until seen on a Mac.
- No macOS: the drag strip is checked by computed style only; a real drag of a Finder file and a Dock drop were not done.
- The engine used is main's (6dc70b2), without 2a's `GET /api/jobs`; the job count path is checked against a served list of 2a's shape (`status` field) only.
- The wizard was walked on the cloud path with the key check served by the route (no real key); the local-download path through the Terminal step was not walked.

## Lead's own run (2026-11-20, at 12aa942)

- Ran: `/usr/bin/python3 docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py --no-shots --out <lead scratch folder>/ui-check`, from the worktree, a throwaway HOME for the engine.
- Saw: "173 passed, 0 failed", exit 0. Afterwards no Python listener was left on any port (checked with `ss -ltnp`). Same count as the builder's full run (`checks/run-full.out`, 173); `--no-shots` only skips taking the 177 screenshots.

## Round 1 fixes (one entry per finding)

**The stub first.** `checks/stub.js` now does what 2c-app does at 70e911f: on every return to running it sends the status and then loads `/` (as `main.js`'s engine status handler, `mainWin.loadURL`); Restart engine emits restarting, then running; the removal emits restarting, keeps its result (`lastRemoval`) before the engine is back, and can settle before the old page is replaced; `firstLaunch.mark` returns `{ok}` and can fail with 2c-app's wording; held Dock files and the engine's state survive reloads. Run against it before any fix (`checks/run-r1-stub-before-fixes.out`): **153 passed, 5 failed**: "running again names the watched job" (C1/F1), "the page reloaded during remove()" and "after the reload the result card comes from lastRemoval" (C7: `finally` cleared the note when remove() settled just before the reload), and two scenario stops behind them. That is the evidence the round-0 checks did not cover the real app.

| Id | Change | Ran | Saw |
|---|---|---|---|
| C1 / F1 | `EngineBanner`: an outage (engine stopped by itself after running, or seen restarting) writes `{job, at}` to sessionStorage; the first status of a reloaded page that reads running shows "Running again" naming the job and removes the note; Dismiss removes it | `check_ui.py --only banner` | PASS "R1: the stub reloaded the page to / when the engine came back", "C1: after the reload, running again names the watched job" (the URL by name), "C1: the note is used once" |
| C2 | `RemovalResult` handles `pieces: null` itself: "Cleanup didn't finish", the reason, Try again, Close; type allows `pieces: null` | `--only removal_reload` with the stub keeping 2c-app's `{ok:false, pieces:null, reason:"The removal failed: …"}` through the reload | PASS "C2: a kept result with no pieces shows its reason, Try again and Close (no crash)" (no page error), "C2: Close consumes it" |
| C3 (and F15's queue half) | Drops and Dock files are written to sessionStorage inside the callback (the preload acks right after it); the Transcribe page submits from that queue and a file leaves it only once the engine answered (`useJob.submit` now resolves true/false) | `--only open_file`: job A running, B arrives, engine stops and returns, the stub reloads | PASS "C3: B survives the reload and is submitted by its path" (asserted: the POST bodies are exactly A's URL then B's path), "C3: B leaves the stored queue once the engine accepted it" |
| C5 | Readiness gate `runsOurs`: state on with the shell not asked shows "The anyscribe command is added", the reason, and "Open a new Terminal window and type `anyscribe --help` to check."; the skill card and the Settings row follow; the old check expecting "ready" is corrected | `--only first_launch,settings` | PASS "C5: shell not asked: …", "C5: the skill card's title when the shell wasn't asked", "C5: Settings row for a shell not asked", "C5: shell not asked and skill missing: no 'Terminal is ready', Try again offered" |
| C6 | Escape and a click outside are the quiet answer and are marked (launcher: Keep both; Terminal card and the wizard's Terminal step: Skip for now). `markAsked()` reads mark's result: on `{ok:false, reason}` the choice still goes ahead and the reason is shown | `--only first_launch,wizard_escape`, stub `markFails` | PASS "C6: Escape on the Terminal card is Skip for now", "C6: and it is not asked again", "C6: a click outside the launcher question is Keep both", "C6: Escape on the wizard's Terminal step is Skip for now", "C6: a failed save is shown with its reason", "C6: with the save failing, the removal still runs and its result shows", "C6: then the failed save is explained (kept across the reload)" |
| C7 | The removal note (`{at, before}`) stays until consumed: claimed by the reloaded page or its card closed (OK, Close); cleared at once on a refusal | `--only removal_reload`, stub `removeSettlesFirst` | PASS "C7: settled before the reload, the reloaded page still shows the result", "C7: claimed, the note is gone", "C7: closed with Escape, not shown again after another reload", "C7: the note is kept while the result card is open, gone once it is closed", "C7: a refusal clears the note at once" |
| F2 | Restart engine (`restartEngine()` in desktop.ts) and the removal are noted as this page's restart: "Restarting anyscribe's engine." and no outage | `--only banner,first_launch` | PASS "F2: a restart he asked for says so, not the crash words", "F2: Restart engine in Settings, the asked-for words", "F2: no Running again after Settings' restart", "AMEND2/F2: the restarting banner covers the gap, in the asked-for words" |
| F3 | addToPath `ok: true` with a reason: that reason in the added-but-missing card; otherwise "The line was added, but Terminal still can't see the command." | `--only first_launch` with 2c-app's ~/.zshrc wording | PASS "F3: the app's reason replaces the generic sentence" |
| F4 | After a refusal with a line: no "anyscribe can add this line …" paragraph, no standard box; the reason as plain text, then the line box with the returned line; stub uses 2c-app's bash wording | `--only first_launch` | PASS "AMEND 3/F4: bash refusal shows its reason and only its line, selectable" (both lines), "F4: no stale offer to add the line; the reason is guidance, not red" |
| F5 | `occupant` set and state off: the offer card says "Another anyscribe 0.19.0 is already at ~/.local/bin/anyscribe, installed with uv." with Switch to this app's copy and Skip for now; Settings row: Off, the same sentence, the Switch link; the toggle asks first | `--only first_launch,settings` | PASS "F5: the offer names the copy and offers Switch instead of Turn on", "F5: Switch calls turnOn({replace:true})", "F5: Settings row names the copy at our spot and offers Switch", "F5: the switch asks first when a copy sits there", "F5: Switch replaces it" |
| F6 | "Removing the old launcher restarts the engine. " + the reason, under the question and in Settings | `--only first_launch,settings` | PASS "AMEND launcher/F6: …" (both places), "AMEND2/F6: a refusal answers at once, says the removal restarts the engine, no reload" |
| F7 | Browse in the app puts the path in the box and focuses it; Transcribe submits it. **The spec's "submits" was the lead's error** (the mockup says "As today"); drop and Dock still start at once | `--only browse` | PASS "F7: Browse puts the picked file's path in the box and focuses it", "F7: nothing submitted and no upload copy until he clicks Transcribe", "F7: Transcribe then submits that path" |
| F8 | "Off. anyscribe isn't in Terminal." alone; the skill clause only right after a turnOff in this view that removed an installed skill | `--only settings` | PASS "F8: plain off line when nothing was removed here", "F8: right after a turnOff that removed the skill, the off line says so" |
| F9 | The Removed card names only what was there before ("Removed the old launcher and its menu bar icon."), from the launcher status read before the removal (kept in the removal note) | `--only removal_reload` | PASS "F9: names only what was there (no login item)" |
| F10 | Keeps-stopping banner: an Open log folder link (`openLogFolder()`) instead of the path sentence | `--only banner` | PASS "F10: no hidden log path in the banner", "F10: Open log folder in the banner calls openLogFolder()" |
| F11 | Overlay's name-and-size branch, `mb()` and the second line deleted: "Drop to transcribe" only | `--only drop` | PASS "F11: the overlay says Drop to transcribe only" |
| F12 | Ready card: "In Claude Code, ask it to transcribe a link." only with Claude Code; "If Claude Code isn't on this Mac yet …" only without | `--only first_launch` | PASS "F12: with Claude Code, its sentence only", "F12: without Claude Code, its note only" |
| F13 | The wizard's Terminal step is titled "One last thing" | `--only wizard` | PASS "Terminal is the wizard's last step, titled One last thing (F13)" |
| F15 | Queue half: as C3. The remove button is declined (declined.md) and not built | as C3 | as C3 |
| F16 | Other-copy card with no Switch: the only button reads "OK" | `--only first_launch` | PASS "F16: its only button reads OK" |

Commits: one per finding where the finding had its own code; where two findings were the same component's single edit they share a commit and its message lists both (C1/F1+F2+F10 in `EngineBanner`; C3+F11 in `Layout`; C7+C2+F9+F6 in the removal cards; C5+F3+F4+F5+F8+F12+F16 in the Terminal cards; C6+F13). F7 has its own.

### Where the plan and I differ (said, not silently built)
1. **C3's test wording.** "B … is submitted when A finishes": a reload only happens when the engine has come back after stopping by itself (Restart engine and the removal are refused while a job runs), and a stopped engine has lost A. After the reload the page follows no job, so B starts as soon as the page is ready. Built and asserted that way (B's path submitted after the reload).
2. **C3, a refused submission.** It also leaves the stored queue: kept, the page would submit it again on every render. Its error stays on screen with Try again.
3. **C6, where the reason shows.** The question card closes on the answer, so a failed save is shown in a small card afterwards ("anyscribe couldn't save your answer", the reason, "This question may come back the next time anyscribe starts."), kept across the removal's reload, after the removal's own result.
4. **C7, "clear it at once on a refusal (ok false and no pieces)".** A removal that throws also comes back `{ok:false, pieces:null}` after the engine restarted, with its result kept for the reloaded page. Clearing then would lose it. A refusal is told apart by the engine's own events: no status other than running during the call.
5. **F9, "from pieces".** The result's pieces describe what is there after (all "removed" once gone), so they cannot say what existed. The card uses the status read before the removal (stored in the note); without it (an old note), carry-over or a login note stands for the login item.
6. **F2 after an outage.** When the engine had stopped by itself before he pressed Restart engine (the keeps-stopping banner), "Running again" still reports that earlier outage. His restart adds no outage of its own.
7. **F7** is recorded as the lead's spec error, as asked.
8. Declined and not built: C4, F14, F15's remove button. F14 still shows: a removal started in Settings shows its result over Transcribe after the reload to `/`.

### Mutation results (round 1)
**25 of 25 mutants killed**, and in every one the restored source passed its whole scenario again. Each mutant is written into `ui/src`, built with `npm run build`, its scenarios run, the file restored byte for byte, rebuilt and run again. Of the 25, 13 are round 0's four guards, carried over to the renamed code; 12 guard round 1.

Where it ran: `checks/mutate-part1.out` (19 mutants, at 8f6ce75). That run stopped at the 20th, `r1/readiness-gate-card`, whose first version did not compile (`if (false)` left `status` narrowed). The mutant was rewritten so it compiles (`&& Date.now() < 0`, which is never true and cannot be narrowed) and run on its own: `checks/mutate-part2a.out`. `r1/readiness-gate-row` and `r1/mark-failure-shown` were also rewritten the same way after a type check. They ran with the last three: `checks/mutate-part2.out` (details `checks/mutants-part2.json`). Each mutant was type-checked before it ran. A mutant that did not compile stopped the run and was never counted. `checks/mutants.json` is still round 0's file: round 1's full run never reached the point where it is written.

| Guard (round 1) | Mutant | Check that failed with the mutant | Restored |
|---|---|---|---|
| The outage note | `r1/outage-note`: the note is not written to sessionStorage | FAIL "C1: after the reload, running again names the watched job" (the watched URL by name) | PASS |
| Asked-for restart is not an outage | `r1/asked-restart-no-outage`: the "asked" test dropped | FAIL "F2: no Running again after Settings' restart" | PASS |
| The queue written before the ack | `r1/queue-before-ack`: the dropped/Dock path kept only in React state | FAIL "C3: B survives the reload and is submitted by its path" (POST bodies: A's URL then B's path) | PASS |
| The removal note kept until consumed | `r1/removal-note-kept`: the note cleared when remove() settles | FAIL "C7: settled before the reload, the reloaded page still shows the result" | PASS |
| … and cleared once consumed | `r1/removal-note-consumed`: OK/Close no longer consumes it | FAIL "C7: the note is kept while the result card is open, gone once it is closed" | PASS |
| … used once by the claim | `repeat/removal-result-once`: the claim leaves the note | FAIL "C7: closed with Escape, not shown again after another reload" | PASS |
| … only a newer result | `repeat/removal-result-newer`: the at-or-after test dropped | FAIL "AMEND2: an older lastRemoval is never shown" | PASS |
| The no-pieces branch | `r1/no-pieces-branch`: the branch never taken (`pieces!`) | FAIL "C2: a kept result with no pieces shows its reason, Try again and Close" (the page crashed on `null.launcher`) | PASS |
| The readiness gate (card) | `r1/readiness-gate-card` | FAIL "C5: shell not asked: 'The anyscribe command is added' …" | PASS |
| The readiness gate (Settings) | `r1/readiness-gate-row` | FAIL "C5: Settings row for a shell not asked" | PASS |
| Quiet answer marks | `r1/quiet-answer-marks`: a click outside no longer marks | FAIL "C6: a click outside the launcher question is Keep both (marked, nothing removed)" | PASS |
| A failed save is shown | `r1/mark-failure-shown`: mark's `{ok:false}` ignored | FAIL "C6: a failed save is shown with its reason" | PASS |

Round 0's guards, again at round 1's code: `bridge/settings`, `bridge/drag-strip`, `bridge/drop-listener`, `bridge/shutdown`, `bridge/first-launch`, `addToPath/settings-row`, `addToPath/after-turn-on`, `repeat/launcher-flag`, `repeat/terminal-flag`, `repeat/keep-marks`, `repeat/terminal-marks`, `restart/disabled`, `restart/pending-counts`: each FAIL with the mutant on the same check as round 0, PASS restored (the files above have every line).

### Full run, screenshots, build
- **Full checker run** at the final source (`checks/run-full.out`): **212 passed, 0 failed**, 14 scenarios (browser, browser_pixels, app_layout, drop, browse, open_file, banner, settings, first_launch, removal_reload, first_launch_marked, wizard, wizard_escape, wizard_browser). Before any fix the same stub gave 153 passed, 5 failed (`checks/run-r1-stub-before-fixes.out`).
- **Browser run pixel-identical**: `/`, `/history` and `/settings` at 1440, 1000 and 390 px are identical to the main checkout's bundle (all nine PASS in `run-full.out`). Both bundles get the same frozen caret and animations; this round adds the animation freeze. One `/history` spot (8 by 32 px, one antialias level) differed between two loads of the *same* bundle while History's loading line animated, so it was noise, not a change.
- **Screenshots**: 66 states at 1440, 1000 and 390 px (198 images in `checks/shots/`, gitignored, regenerated by the script). I read every state that round 1 changed or added, three widths side by side: banner-running-again-job, banner-restarting-asked, banner-keeps-stopping, app-drop-overlay, app-browse-filled, app-up-next, first-launcher-removing, first-launcher-removed-after-reload, first-launcher-threw-after-reload, first-mark-failed, first-terminal-added-unknown, first-terminal-added-reason, first-terminal-occupant, first-terminal-bash-refused (both lines), first-terminal-other-elsewhere, first-terminal-ready, settings-terminal-occupant, settings-terminal-unknown, settings-terminal-off, wizard-terminal-step. What I saw: today's look holds at every width; "Running again" names the URL after the reload; the asked-for restart reads "Restarting anyscribe's engine."; the keeps-stopping row now has Open log folder; the overlay has one line; Browse shows the path in the box with Transcribe lit; the bash refusal shows its guidance (not red) and only the returned line; the occupant offer has Switch and Skip for now; the other-copy card without an occupant has a single OK; the wizard step reads "One last thing". Two things to note:
  - The real bash reason already contains the line, so the line appears twice: in the sentence and in the box. The plan asks for both.
  - In `first-launcher-removing` the question card stays visible under the restarting banner with the spinner until the reload. That is the gap amendment 2 describes.
- **ui**: `npm run lint` exit 0, no warnings; `npm run build` clean; bundle `index-jap_fLlu.js` (built from the final source, the one the full run served) committed with `index.html`.
- **Left running**: nothing. Every engine is stopped by its pid. A check for Python listeners after the runs (`ss -ltnp`) found none. `git status ui/` was clean after every mutation run.

### New wording in round 1
From the plan: "Restarting anyscribe's engine."; "Removing the old launcher restarts the engine. "; "The anyscribe command is added"; "The anyscribe command is added, but the Claude Code skill couldn't be installed"; "Open a new Terminal window and type anyscribe --help to check."; "On. The command is added; anyscribe couldn't check that Terminal finds it."; "Another anyscribe{version} is already at ~/.local/bin/anyscribe{, installed with …}."; "The line was added, but Terminal still can't see the command."; "One last thing"; "OK".
Mine: "Removed the old launcher and its menu bar icon." (and the other combinations of what was there); " The Claude Code skill isn't installed." after the C5 Settings line; "anyscribe couldn't save your answer" and "This question may come back the next time anyscribe starts."; the fallback "Add this line by hand:" when a refusal brings a line but no reason; "Cleanup didn't finish" reused as the title of a no-pieces result.

### What I could not check (round 1)
- Still no real Electron: the reload, the preload's acknowledgement and the removal's timing are modelled in the stub from reading 2c-app at 70e911f (`main.js` status handler, `preload.js` open-file, `old-launcher.js` `removePausingEngine`), not observed.
- Whether sessionStorage survives `loadURL` to the same origin in Electron is the browser's rule (same tab, same origin) and the stub's reload exercises it in Chromium; not seen in Electron. A restart that changes the port would lose these notes (2c-app keeps the port; the fit reviewer raised the same doubt).

## Lead's own run after round 1 (2026-11-21, at c867050; code 9a3ed5d)

- Ran: `/usr/bin/python3 docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py --no-shots --out <lead scratch folder>/ui-check-r1`, from the worktree.
- Saw: "212 passed, 0 failed", exit 0; no Python listener left afterwards (`ss -ltnp`). Mutation outputs read: 19 + 1 + 5 = 25 killed, each restored run passing its scenario (`checks/mutate-part1.out`, `mutate-part2a.out`, `mutate-part2.out`).

## Round 2 fixes (one entry per finding)

**Stub first (A4).** `checks/stub.js` now behaves as the bridge at 70e911f by default:
- sessionStorage is the app's memory (it survives the app's reload of the page); localStorage is its disk;
- removal restarts the engine and reloads the page, saves `lastRemoval`, and changes `installed` and Start at login when carried over;
- Terminal, Dock and launcher state survive reloads;
- a failed `firstLaunch.mark` is held in memory as asked and is not written to disk;
- `/api` requests fail while the engine reads stopped or restarting;
- an opened file is acknowledged when the callback returns, even if it throws (the preload's ids never reach the page).

Simplified cases (removal with no restart) are labelled "[component]" in the checker. Run before any round 2 code change (`checks/run-r2-stub-before-fixes.out`): **192 passed, 8 failed**. The failures were tests that had leaned on the old stub: removals without a reload, and an engine that served `/api` while "stopped".

| Id | Change | Ran | Saw |
|---|---|---|---|
| A1 | A queued file leaves the stored queue only once the engine accepted it. On a refusal it stays at the head and the error screen is the pause: no next file starts. Try again resubmits it and drops it once accepted. New drops the head only when the head is the one that failed. Up next leaves out the failed head and shows under the error. | `--only r2_facts` | PASS "A1: refused A, B waiting: the stored queue is exactly [A, B] and only A was posted"; "A1: Up next names B, not the failed head"; "A1: Try again posts A, then the queue is exactly [B]"; "A1: B waits behind the typed link's error, not posted"; "A1: New after a typed link's failure keeps B …" (POST bodies asserted: L, then B) |
| A2 | "Mine" only while this page's own `restartEngine()` or `removeOldLauncher()` is in flight (a module counter). The removal note is resolved in one function against the app's saved `lastRemoval`, only while the engine reads running. Deleted: `RESTART_MINE`, `restartConsumed`, `NOTE_LIFE_MS`, the `restarted` status listener. | `--only r2_facts` | PASS "A2: after the reload, the unmatched note is gone and no result is shown"; "A2: a later crash reads as a crash"; "A2: and Running again names J"; "A2: a thrown removal settled just before the reload: the reloaded card shows its reason" |
| A3 | The removal card always shows `result.reason`. Claimed after a reload, a "didn't start again" reason gets "It is running again now." The stopped engine has its banner (G2). | `--only r2_facts` | PASS "A3/G3: carried over and the engine reason: both shown"; "A3: claimed after the reload, the card adds that it is running again now" |
| A4 | The stub, as above. | `--only r2_facts,first_launch` | PASS the self-checks: "stub self-check: after removal and reload, Start at login on, launcher gone, Terminal kept"; "… a failed mark is held in memory, not written to disk"; "… while the app runs, a failed mark still reads asked"; "… after the app's memory is gone, the unsaved question comes back" |
| A5 | The sentence names only what was there before. Icon only: "Stopped the old menu bar icon. The launcher and login item were already gone." No snapshot: "Cleanup finished. Nothing of the old launcher is left on this Mac." | `--only r2_facts,removal_reload` | PASS "A5/G4: Settings' card names the icon only, from the pieces read before"; "A5: no snapshot, no guess about pieces"; "F9: names only what was there (no login item)" |
| G1 | A queued file starts only while the engine reads running. | `--only r2_facts` | PASS "G1: engine down: nothing posted, no failure, B kept"; "G1: after the reload, exactly one post, carrying B's path" |
| G2 | `state === "stopped"` without `stoppedRestarting` uses the red card. Heading "anyscribe's engine stopped"; body "It couldn't start again. Your transcripts are safe. {exitWords}."; the same buttons; `refused` under the body; Copy details "Engine: stopped, couldn't start again". | `--only r2_facts` | PASS "G2: the stopped engine gets its red card"; "G2: a refused Restart shows its reason under the stopped card"; "G2: Copy details names the stopped state" |
| G3 | As A3 (the carry-over guard is gone). | as A3 | as A3 |
| G4 | Settings keeps the pieces read before the call with its result (`setRemoval(r.shown)`, a `Removal` carrying `before`). | `--only r2_facts` | PASS "A5/G4: Settings' card names the icon only …" (the in-place card, the engine stopped, so no reload) |
| G5 | The save-failed card names the question: the old launcher one, the Terminal one, or "These questions may come back …". | `--only first_launch` | PASS "C6: a failed save is shown with its reason, naming the question (G5)"; "G5: both questions named when both saves failed" |
| G6 | The added-but-missing card drops "Takes effect in new Terminal windows …", which stays in the path view only. A by-hand reason that ends with the line is shown without it; the box holds the line. | `--only first_launch` | PASS "G6: no 'takes effect in new windows' under the finding that it doesn't"; "AMEND 3/F4/G6: bash refusal shows its reason (without a repeated line) and only its line, selectable" (both lines) |
| G7 | As A2: the note never counts as his restart. | `--only r2_facts` | PASS "[component] A2/G7: with the removal's card still open (its note kept), a crash reads as a crash" |

Commits: A4 alone (the stub). A1 and G1 alone (`Layout`, `TranscribePage`). A2, G7, A3, G2, A5, G4, G5 and G6 in one commit, because all eight edit the same five files (`desktop.ts`, `EngineBanner`, `MacCards`, `ThisMac`, `App`); its message lists them. Then the checks, the mutants, and the docs.

### The plan, checked against the bridge
I found nothing in fix-plan-r2.md that the bridge at 70e911f contradicts, and built it as written. Three notes:
1. **The live page with the engine not running.** When `remove()` settles while the engine is not running, the note cannot be resolved yet. That happens when the engine didn't start again, or when a crash is being restarted. The live page then shows what `remove()` returned. The note waits for the running engine, which settles it: a refusal's note is cleared on the next running status, as in the A2 check.
2. **The A1 check "New … the queue is still [B]".** After New the page is idle, so B starts at once. The check refuses B too, so it stays at the head and the queue reads exactly [B]. The POST bodies show L, then B.
3. **"Up next" under the error.** The plan says Up next leaves out the failed head while its error is shown. Up next was only on the running view, so it now also shows under the error: "Up next: b.m4a. It starts once you try this one again or choose New." These words are new, mine.

### Mutation results (round 2)
**33 of 33 killed**, and in each one the restored source passed its whole scenario again. Each mutant is written into `ui/src`, built, its scenarios run, then the file restored byte for byte, rebuilt and run again. Every mutant was type-checked before the run.

Files:
- `checks/mutate-r2.out`: the full run of 33 (details in `checks/mutants.json`).
- `checks/mutate-r2-recheck.out`: one mutant re-run (details in `checks/mutants-r2-recheck.json`). In the full run `r1/removal-note-consumed` read as surviving, but only because its check had been renamed "[component] C7: …" and the mutant still looked for the old name, so the check was never found. With the name corrected, it is killed. I also reproduced the kill by hand.

| Guard (the plan's "Checks") | Mutant | Check that failed with the mutant | Restored |
|---|---|---|---|
| Accepted test | `r2/queue-accepted-only`: the file leaves after any answer | FAIL "A1: refused A, B waiting: the stored queue is exactly [A, B] …" | PASS |
| Error pause | `r2/queue-error-pause`: the next file starts from the error screen | FAIL "A1: refused A, B waiting: …" (B posted) | PASS |
| Running gate | `r2/queue-running-gate` | FAIL "G1: engine down: nothing posted, no failure, B kept" | PASS |
| New drops the head only when it failed | `r2/new-drops-head-only` | FAIL "A1: New after a typed link's failure keeps B" | PASS |
| The note never counts as his restart | `r2/note-not-mine`: `restartIsMine()` also reads the note | FAIL "[component] A2/G7: with the removal's card still open (its note kept), a crash reads as a crash" | PASS |
| Unmatched note cleared | `r2/unmatched-clear` | FAIL "A2: after the reload, the unmatched note is gone and no result is shown" | PASS |
| Never decide by the result's shape | `r2/no-shape-clear`: clear on `ok:false` with no pieces | FAIL "A2: a thrown removal settled just before the reload: the reloaded card shows its reason" | PASS |
| The reason always shows | `r2/reason-always`: the carry-over guard restored | FAIL "A3/G3: carried over and the engine reason: both shown" | PASS |
| The stopped branch | `r2/stopped-branch` | FAIL "G2: the stopped engine gets its red card" | PASS |

The other 24 come from rounds 0 and 1, re-run at this code: bridge ×5, addToPath ×2, repeat ×6, `r1/*` ×9, restart ×2. Each is killed and each restored scenario passes; every line is in `checks/mutate-r2.out`. `r1/removal-note-kept` was dropped: the code it mutated is gone, and `r2/no-shape-clear` plus the C7 checks cover the same rule.

### Full run, screenshots, build (round 2)
- **Full checker run** at the final source (`checks/run-full.out`): **237 passed, 0 failed**, across 15 scenarios. The new `r2_facts` scenario has 20 checks.
- **Browser run pixel-identical**: all nine pairs PASS (`/`, `/history`, `/settings` at 1440, 1000 and 390 px against the main checkout's bundle).
- **Screenshots**: 69 states at three widths (207 images in `checks/shots/`, gitignored). I read every state round 2 changed or added:
  - **r2-queue-refused-head**: the error for a.m4a, with "Up next: b.m4a. It starts once you try this one again or choose New." beneath it.
  - **r2-removed-engine-stopped**: the Removed card carries the carry-over sentence and the engine reason; the red "anyscribe's engine stopped" card sits behind it.
  - **r2-settings-icon-only**: "Stopped the old menu bar icon. The launcher and login item were already gone." in the Settings row, with the reason, and the Engine row reading Stopped.
  - **first-mark-failed**: names "The old launcher question".
  - **first-terminal-added-reason**: no "Takes effect" note.
  - **first-terminal-bash-refused**: "Your bash reads ~/.profile; add this line to it by hand:", then the box. The path view keeps its "Takes effect" note, as the plan says.
  - **first-launcher-removed, first-launcher-failed, settings-launcher-removed**: now reached through the app's reload. Settings shows Start at login On, because the removal carried it over, and the old launcher row is gone.

  The look matches today's at every width.
- **ui**: `npm run lint` exit 0; `npm run build` clean; bundle `index-BZ7pkZGv.js` committed with `index.html`.
- **Left running**: nothing. Engines are stopped by their pid, and `ss -ltnp` shows no Python listener. `git status ui/` was clean after the mutation runs.

### New wording in round 2
From the plan:
- "anyscribe's engine stopped" and "It couldn't start again. Your transcripts are safe. …";
- "Engine: stopped, couldn't start again";
- "It is running again now.";
- "Stopped the old menu bar icon. The launcher and login item were already gone.";
- "Cleanup finished. Nothing of the old launcher is left on this Mac.";
- the three "… may come back the next time anyscribe starts." sentences.

Mine:
- "Up next: {names}. It starts once you try this one again or choose New." ("They start in turn …" for more than one);
- "the old login item" and "the old menu bar icon", when the launcher itself was already gone and other pieces were there.

### Documented limits (in the journal, not built)
- A crash during the job check of his own Restart or Remove click shows the asked-for wording and records no outage, once. The window is one HTTP read long.
- A window reopened while his own restart runs may read it as a crash.
- Files waiting in Up next are lost if anyscribe quits before they start.
- Real Electron reload timing and sessionStorage across `loadURL`: no stub proves them. They stay a check on a Mac.

## Lead's own run after round 2 (2026-11-21, at f1aae31; code 99bb239)

- Ran: `/usr/bin/python3 docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py --no-shots --out <lead scratch folder>/ui-check-r2`, from the worktree.
- Saw: "237 passed, 0 failed", exit 0; no Python listener left afterwards (`ss -ltnp`). Mutation outputs read: `checks/mutate-r2.out` "32 of 33" plus `checks/mutate-r2-recheck.out` "1 of 1" for the mutant whose check had been renamed; no survivor line in any mutate output.

## Round 3 fixes (one entry per finding)

| Id | Change | Ran | Saw |
|---|---|---|---|
| H1 | **Rule 1, the doomed page.** In `desktop.ts`, a module flag is set by the first engine status read and by any status that is not running, and never resets. Exactly two readers: the queue's start gate (`engine running && !isDoomed()`) and the startup recovery claim. Clicks and the banner's outage record are unchanged. | `--only r3_facts` with `reloadDelay` 300; every `/api` request carries the stub's page number | PASS "H1: exactly one POST, body B, sent by the reloaded page; its progress (Stop) is there" (`tagged == [(b.m4a, "1")]`); PASS "H1: a page that first read 'restarting' is doomed too: only the reloaded page posts B" |
| B1 | **Rule 2, act only on the starting state.** The note is read once at module load (`noteAtLoad`), and startup recovery resolves only that note: the same `at`, checked again inside `resolveRemoval` just before it clears or claims. With no note at load there is no recovery read at all. The live page's refusal clear is tied to the `at` it wrote. The literal `true` arguments are gone: the real engine state (`engineRunningNow()`, or the state just read) is passed instead. | `--only r3_facts`. The stub answers `oldLauncher.status` with what it knew when asked, after an optional per-call or per-page delay; a removal's job check (`removeCheckMs`) keeps the engine reading running for a while after the click. | PASS "B1: no note at load, no recovery read; the reloaded card shows the removal's reason X" (one status read before the click); PASS "B1: the stored note is the click's, not the predecessor's; the reloaded card shows X"; PASS "Doomed recovery: no card and the note unchanged on the old page; the reloaded card shows X" |
| B2 | The checklist card shows `result.reason` (the bridge's own words) above the generic advice. | `--only r3_facts` | PASS "B2: the checklist card shows the bridge's reason X" |
| B3 | Deleted `removeSettlesFirst`. The stub's removal emits running, then settles, and the reload follows `reloadDelay` (now 300 ms by default) later. The stub records the engine state at the moment `remove()` settles. | `--only r3_facts` (and every removal check, now on this path) | PASS "B3: the engine read 'running' when remove() settled" |
| H2 | Files that wait while the engine is not running, or the page is doomed, are named in the idle, completed (both kinds) and cancelled views: "Up next: b.m4a. It starts once anyscribe's engine is running again." (plural "They start in turn …") | `--only r3_facts` | PASS "H2: idle view names the waiting file; zero POSTs"; PASS "H2: completed view names the waiting file; no POST for it" (a completed job over a scripted WebSocket, then the engine stopped) |
| H3 | `askTerminal` waits for the startup recovery (`removalChecked`), starts at once when there was no note, and stays held on a doomed page. | `--only r3_facts`: both questions unasked, Remove, the reload | PASS "H3: terminal.status calls are [] until OK, then exactly one" |
| H4 | `break-words` on every Up next line. Under the error: "Up next: b.m4a. It waits until you try this one again or choose New." (plural "They wait …") | `--only r2_facts` | PASS "A1: Up next names B, not the failed head" with the new words in the screenshot `r2-queue-refused-head` |

Commits:
- H1, B1 and H3: `desktop.ts` and `App.tsx`.
- H2 and H4, plus H1's start gate: `TranscribePage.tsx`.
- B2: its own commit.
- B3: in the checks commit with the new `r3_facts` table.
- Then the mutants, the docs, the bundle and this proof.

### The plan, checked
I found nothing in fix-plan-r3.md contradicted by the bridge at 70e911f, and built it as written. Two notes on the checks:
1. **"B1, note at load" and "Doomed recovery"** need the recovery read to answer at a chosen moment. The stub's per-page delay (`"0:2"`, the first page's second status read) slows only the old page's recovery read; the reloaded page's read stays fast. On Settings the order is: 1 the App's question read, 2 the recovery read, 3 the This Mac row. I checked this order with a probe of the recorded calls.
2. **"B1, no note at load"** needs the engine to still read running when the mutant's late recovery read returns. The real `engine.restart()` reads the job list before it says "restarting", and `removeCheckMs` models that read.

### Mutation results (round 3)
**43 of 43 killed**, and every restored scenario passed again. Each mutant is type-checked first, then written in, built, run, restored byte for byte, rebuilt and run again.

The first full run (`checks/mutate-r3.out`, 43 mutants, details in `checks/mutants.json`) left two survivors:
- `r3/at-match`: the slow recovery read answered *before* the click, so its window never opened.
- `r3/doomed-recovery`: the read answered while the engine read "restarting", so the engine-state test alone hid the flag.

Both checks were reworked so the windows open, and they now assert their own timing:
- `r3/at-match`: the read answers after the click and while the removal's job check keeps the engine running (`clicked_ms < 4000` asserted).
- `r3/doomed-recovery`: the read answers after "running" but before the app's reload, on the old page (`window.__oldPage` asserted).

Re-run in `checks/mutate-r3-recheck.out` (details `checks/mutants-r3-recheck.json`): both are now killed and both restored scenarios pass.

| Check (fix-plan-r3 table) | Mutant | Failed with the mutant | Restored |
|---|---|---|---|
| H1 | `r3/doomed-flag`: the start gate ignores the flag | FAIL "H1: exactly one POST, body B, sent by the reloaded page …" | PASS |
| H1, first read | `r3/doomed-first-read`: the flag is set from events only | FAIL "H1: a page that first read 'restarting' is doomed too …" | PASS |
| B1 | `r3/no-note-skip`: recovery runs with no note, resolving whatever note is there at callback time | FAIL "B1: no note at load, no recovery read; …" | PASS |
| B1, note at load | `r3/at-match`: the `at` match dropped | FAIL "B1: the stored note is the click's, not the predecessor's; …" (recheck) | PASS |
| Doomed recovery | `r3/doomed-recovery`: the flag check dropped | FAIL "Doomed recovery: no card and the note unchanged on the old page; …" (recheck) | PASS |
| H3 | `r3/terminal-hold`: the hold dropped | FAIL "H3: terminal.status calls are [] until OK, then exactly one" | PASS |
| B2 | `r3/checklist-reason`: the line dropped | FAIL "B2: the checklist card shows the bridge's reason X" | PASS |
| B3 | `r3/stub-settles-after-running`, in the stub: it settles (and records) before emitting running | FAIL "B3: the engine read 'running' when remove() settled" | PASS |
| H2 idle | `r3/idle-line`: the idle line dropped | FAIL "H2: idle view names the waiting file; zero POSTs" | PASS |
| H2 completed | `r3/completed-line`: the completed line dropped | FAIL "H2: completed view names the waiting file; no POST for it" | PASS |

The other 33 mutants are from rounds 0 to 2, re-run at this code; all are killed and restored. The two removal-result mutants follow the renamed `savedAt` in `resolveRemoval`.

### Full run, screenshots, build (round 3)
- **Full checker run** at the final source (`checks/run-full.out`): **247 passed, 0 failed**, across 16 scenarios. `r3_facts` has 10 checks.
- **Browser run pixel-identical**: 9 of 9 PASS.
- **Screenshots**: 72 states at three widths (216 images in `checks/shots/`, gitignored). I read the states round 3 changed or added:
  - `r3-partial-reason`: the checklist, then the bridge's reason, then the advice. The real reason's last sentence and the generic advice both say "Log out and back in"; the plan puts the bridge's words above the advice, and I left it so.
  - `r3-idle-waiting` and `r3-completed-waiting`: under the red stopped card, "Up next: b.m4a. It starts once anyscribe's engine is running again."
  - `r2-queue-refused-head`: "Up next: b.m4a. It waits until you try this one again or choose New."
  - `app-up-next`: at 390 px both lines now wrap between words, not inside them.
  - The look holds at every width.
- **ui**: `npm run lint` exit 0; `npm run build` clean; bundle `index-BPHHF8_E.js` committed with `index.html`.
- **Left running**: nothing. Engines are stopped by their pid; `ss -ltnp` shows no Python listener; `git status ui/` and the stub were clean after the mutation runs.

### New wording in round 3
All from the plan:
- "Up next: {names}. It starts once anyscribe's engine is running again." (plural "They start in turn once …")
- "Up next: {names}. It waits until you try this one again or choose New." (plural "They wait …")

### Documented limits (in the journal, not built)
- A crash during a queued file's POST can run that file twice.
- A click on a doomed page in the instant before its reload.
- A removal result is lost if anyscribe quits before a page claims it: `lastRemoval` is in the app's memory only.
- A second Remove overwrites an unclaimed note.
- Real Electron timing stays a check on a Mac.

## Lead's own run after round 3 (2026-11-21, at 97d35b4; code 6e7a335)

- Ran: `check_ui.py --no-shots` from the worktree: "247 passed, 0 failed", exit 0; no Python listener left (`ss -ltnp`).
- Ran: `npm run lint` in ui/: exit 0. `npx tsc -b`: exit 0. `npx vite build --outDir <lead scratch folder>`: the bundle `index-BPHHF8_E.js` is byte-identical (`cmp`) to the committed one. (Building to another folder appends the model notices to the committed THIRD-PARTY-LICENSES.md, since the plugin writes to that fixed path; restored with `git checkout` of that one file. A normal build regenerates the file first, so it is not a defect.)
- Read: `checks/mutate-r3.out` "41 of 43", the two survivors named by the builder, then `checks/mutate-r3-recheck.out` "2 of 2".

## Lead-made after round 4 (K1 to K4; the lead, 2026-11-21)

Both roles were GOOD TO GO in round 4; the fit nits were fixed by the lead (16 production lines in two files, plus the checks), then sent for one correctness re-check (round 5, the cap).

| Id | Change | Ran | Saw |
|---|---|---|---|
| K1 | MacCards checklist: the reason's opening "Cleanup didn't finish: <what is left>." is stripped (`/^Cleanup didn't finish: [^.]*\.\s*/`; the bridge's left-phrases hold no full stop, old-launcher.js:194-198); what remains shows below the advice; Copy details keeps the full reason | full checker with screenshots; mutant K1-strip | PASS "B2, K1: ... below the advice, without repeating its opening sentence"; read `r3-partial-reason@1440`: the mockup's card, then the approval note; mutant KILLED |
| K2 | check_ui.py: REMOVE_FAIL, REMOVED_NOT_CARRIED, both X and the login note now use old-launcher.js:189/200 and engine.js wordings (the engine reason bare, no full stop); stub.js:148 comment corrected | full checker | 249 passed, 0 failed |
| K3 | TranscribePage: the running view's and the error view's Up next use the engine-down words while the engine is down (`onceUp`, shared with the H2 line) | two new checks (running, error); mutants K3-running, K3-error | both PASS; read `r4-running-waiting@390`, `r4-error-waiting@1440`; both mutants KILLED |
| K4 | MacCards `reasonWords`: a full stop before "It is running again now." when the reason ends bare | A3 check now asserts `X + ". It is running again now."`; mutant K4-stop | PASS; mutant KILLED |

- Correction to "Round 3 fixes" (K2): the note on `r3-partial-reason` saying the real reason's last sentence says "Log out and back in" is wrong; no file in desktop/src at 70e911f contains "Log out". It came from the checker's own fixture, now replaced.
- Full run: `check_ui.py --out <lead scratch folder>/ui-check-lead` (with screenshots): **249 passed, 0 failed**; browser pixel-identical 9 of 9; no Python listener left. Screenshots kept in the lead's scratch folder, not committed; `checks/shots` still holds the builder's round 3 set.
- Mutation: `checks/mutate-lead-r4.py`, output `checks/mutate-lead-r4.out`: **4 of 4 killed**; the restored code rebuilt to the same bundle name (`index-vyVB1epK.js`) and passed r2_facts and r3_facts (32 passed, 0 failed).
- `npm run lint` exit 0; `npm run build` exit 0; THIRD-PARTY-LICENSES.md unchanged by the normal build.

## Lead-made after round 5 (E1, E2; wording-only leftovers at the cap, lead-verified)

| Id | Change | Ran | Saw |
|---|---|---|---|
| E1 | TranscribePage error view, engine down: when the failed file is the queue's head (`incoming[0] === lastUrl`), Up next says "It starts after a.m4a, which is tried again once anyscribe's engine is running again." (`afterHead`); otherwise the K3 words | new check E1 (A and B dropped, A refused, engine stops, then returns: A is tried again first, refused again, B still waits); mutant E1-head | PASS; read `r5-failed-head-waiting@1440` and `@390`; mutant KILLED |
| E2 | check_ui.py: the partial-cleanup fixture's `startAtLoginCarriedOver` is False (the approval note comes only with False, old-launcher.js:187) | full checker | PASS (B2, K1 unchanged) |

- Full run with screenshots: **250 passed, 0 failed**; browser pixel-identical 9 of 9; no Python listener left. Log committed this time: `checks/run-full-lead.out` (round 5 noted the round 4 run's log was not in the packet). The lead's changed-state screenshots are copied into `checks/shots` (r3-partial-reason, r4-running-waiting, r4-error-waiting, r5-failed-head-waiting, each at 1440, 1000 and 390); that folder is local only (`checks/.gitignore`), so the screenshots are not in the repo.
- Mutation, all five lead-made changes: `checks/mutate-lead-r4.py`, output `checks/mutate-lead-r5.out`: **5 of 5 killed**; the restored code rebuilt to `index-DEtcgFqh.js` and passed r2_facts and r3_facts (33 passed, 0 failed). A first run stopped at a mutant that did not compile (removing a branch left `afterHead` unused); both affected mutants were rewritten to compile and the whole set re-run.
- `npm run lint` exit 0; `npm run build` exit 0.
