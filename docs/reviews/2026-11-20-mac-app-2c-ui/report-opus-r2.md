## Fit review, round 2: Mac app 2c-ui (delta 12aa942..9a3ed5d)

### 1. Verdict
**CONDITIONAL on G1, G2 and G3.** There is no blocker. Every round 1 finding is fixed or properly declined, except F9, which is partly fixed. The approved screens and words hold. The new sentences read plainly, and the browser dashboard is untouched. Three small should-fix items remain, all on the real-app path where the engine is down. None of them can be seen in the stub, because the stub's "restarting" and "stopped" never take the real engine offline.

### 2. Round 1 ids
- C1 FIXED. The outage note goes to sessionStorage and the fresh page takes it on its first running status. Traced against main.js:347/354: the status is sent first, then loadURL.
- C2 FIXED. The no-pieces branch in RemovalResult matches old-launcher.js's real `{ok:false, pieces:null, reason}`.
- C3 FIXED for its scenario: B queued, the engine crashes, the reload, B is submitted. The preload acknowledges after the callback, and `add` writes storage synchronously. The engine-down case next to it is G1.
- C4 DECLINED-OK (declined.md).
- C5 FIXED. `runsOurs` gates all three places, and state "on" without `uses` only arises when the shell wasn't asked (terminal.js terminalState).
- C6 FIXED. Wording nit G5.
- C7 FIXED. The "no restart seen" test matches the real bridge: refusals emit no status, and every accepted removal emits "restarting" before its step. Linger nit G7.
- F1 FIXED (same as C1).
- F2 FIXED.
- F3 FIXED.
- F4 FIXED. Repeat-line nit in G6.
- F5 FIXED.
- F6 FIXED.
- F7 FIXED.
- F8 FIXED.
- F9 PARTLY. Correct after the reload; Settings passes the wrong "before" (G4).
- F10 FIXED.
- F11 FIXED.
- F12 FIXED.
- F13 FIXED.
- F14 DECLINED-OK.
- F15: queue half FIXED (see G1); remove button DECLINED-OK.
- F16 FIXED.

### New findings

**G1. should-fix. CONFIRMED by reading; no check covers it.** A file dropped or opened from the Dock while the engine is down is lost after the reload.
- **Where:** `ui/src/pages/TranscribePage.tsx:113-122`. `startIncoming` calls `doneIncoming(path)` after any answer, and `useJob.ts:177` returns false on a fetch failure as well as on a refusal. Real bridge: `main.js:463-465` and `logic.js` `OpenFiles.add` hand the file to the subscribed page whatever the engine state, and `preload.js` acknowledges it after the callback.
- **Scenario:**
  1. He is on Transcribe and the engine is restarting (a crash, the old-launcher removal's uninstall, or the keeps-stopping state).
  2. He drops a file on the window or the Dock icon.
  3. The POST fails ("Failed to fetch"), so the file leaves the stored queue.
  4. The engine comes back, the app reloads `/`, and both the error and the file are gone. The app has already acknowledged it, so it is never resent.
- **Why the checks miss it:** the stub's `__emit({state:'restarting'})` leaves the real engine serving.
- **Fix:** start a queued file only while the engine reads running. In TranscribePage, `const engine = useEngineStatus();` and in the effect `if (!next || !config || phase === "running" || (desktop && engine?.state !== "running")) return;`. Keep departure 2 for real refusals. Add a check: emit "restarting", route `POST /api/transcribe` to abort, `__openFile(B)`, emit "running", then assert B's path is posted after the reload.

**G2. should-fix. CONFIRMED by reading engine.js and EngineBanner.** When the engine stops and is not restarting, the dashboard looks healthy, including right after he presses Restart engine on the keeps-stopping banner.
- **Where:** `ui/src/components/EngineBanner.tsx:67` and `:150`.
- **Scenario:**
  1. Keeps-stopping appears and he clicks Restart engine.
  2. `engine.restart()` resets `stoppedRestarting` and the new engine exits before it is ready. Because the restart was not automatic, `_onExit` goes to `_stopped('exited')`: state "stopped", `stoppedRestarting` false.
  3. The banner renders nothing, so the refusal reason in `refused` is never seen.
  4. The red banner vanishes, which reads as success, while every page fails underneath.
- The same silence follows a failed automatic restart (port taken, log unwritable).
- The bridge can produce this state. The mockup has no words for it, so the spec asks for plain words.
- **Fix:** handle `status.state === "stopped"` in the same red card as keeps-stopping, with this heading and body when `!stoppedRestarting`:
  - Heading: "anyscribe's engine stopped"
  - Body: "It couldn't start again. Your transcripts are safe. {exitWords(lastExit)}."
  - Same buttons: Restart engine, Copy details, Open log folder, Troubleshooting guide. Show `refused` under the body.
  - In Copy details, use "Engine: stopped, couldn't start again" for this state.

**G3. should-fix. CONFIRMED (old-launcher.js `removePausingEngine`; README line 169: "If the engine does not start again, `reason` says so").** The "Old launcher removed" card hides that the engine did not come back.
- **Where:** `ui/src/components/MacCards.tsx:100`, `{!result.startAtLoginCarriedOver && result.reason && ...}`.
- **Scenario:** after the removal the engine fails to start, so there is no reload. The result arrives as ok true, carried over, with the reason "anyscribe's engine didn't start again afterwards: …". The card shows "This app now starts at login instead" and drops the reason.
- **Fix:** change the line to `{result.reason && <p>{result.reason}</p>}`. The bridge only adds its macOS-approval note when the setting was not carried over, so the guard only ever hides the engine sentence.

**G4. nit. CONFIRMED by reading.** Settings' in-place Removed card names only "the old launcher".
- **Where:** `ThisMac.tsx:363` passes `before={launcher?.pieces}`, but `removeLauncher` has already replaced `launcher` with the status read after the removal, where everything is absent.
- **When:** only when no reload follows, which is G3's case.
- **Fix:** keep the pieces read before the call alongside the result, for example `setRemoval({ result: r, before })`, and pass that.

**G5. nit. CONFIRMED (screenshot first-mark-failed).** The save-failed card says "This question may come back" without saying which question. By the time it shows, after the removal card and the Terminal card, two questions have been answered.
- **Where:** `App.tsx:120-129`.
- **Fix:** store the key with the problem and use exact words:
  - "The old launcher question may come back the next time anyscribe starts."
  - "The Terminal question may come back the next time anyscribe starts."
  - Both: "These questions may come back the next time anyscribe starts."

**G6. nit. CONFIRMED (screenshots first-terminal-added-reason, first-terminal-bash-refused).**
- **Where:** `MacCards.tsx:451`, and lines 432 and 441.
- **(a)** The added-but-missing card still says "Takes effect in new Terminal windows. Claude Code picks it up the next time it starts." right under the app's finding that it does not take effect. Show that note only in the "path" view.
- **(b)** The by-hand reason ends with the line, and the box below repeats it. When the reason ends with `byHand.line`, show it without the line, for example "Your bash reads ~/.profile; add this line to it by hand:", then the box.

**G7. nit. PLAUSIBLE.** The removal note counts as "this page's restart" for as long as it exists.
- **Where:** `desktop.ts:142-144`. The note is in localStorage, lasts up to 10 minutes, and survives a relaunch when there is nothing to claim.
- **Scenario:** a removal whose engine didn't come back, or a refusal that coincided with a crash. A crash in that window reads "Restarting anyscribe's engine." and records no outage, so there is no "Running again" naming a watched job.
- **What would settle it:** a check that leaves the note, then crashes during a watched job.
- **Fix:** count the removal only while this page's `remove()` call is in flight (a module flag set in `removeOldLauncher` and cleared in its `finally`).

### 3. The builder's six departures (advice)
1. **B starts at once after the reload.** Agree. The real bridge reloads only after the engine comes back by itself, and that engine lost A. Restart and removal are refused while jobs run, and the menu-bar restart exists only in the stopped state.
2. **A refused submission leaves the queue.** Agree for refusals from a running engine, since keeping it would loop. Disagree for "unreachable", which is the engine-down window C3 was about. That is G1, and gating on engine state removes the loop concern.
3. **The failed save shown in its own card afterwards.** Agree with the placement. Fix the wording (G5).
4. **A refusal is told apart by "no status other than running during the call".** Agree. This is the correct signal against old-launcher.js, and the plan's literal rule would have lost a thrown removal's kept result. Bound its side effect (G7).
5. **F9 from the status read before the removal.** Agree, since pieces after the removal cannot say what existed. Settings feeds the wrong "before" (G4).
6. **"Running again" after he restarts from keeps-stopping.** Agree. The earlier outage did lose the watched job, so reporting it once is truthful.

### 4. Pending owner checks
These are not his to fix; they are for him to see and accept.
- **Deliberate departures from the approved mockup:**
  - The drop overlay says only "Drop to transcribe", with no file name or size.
  - Copy details carries no log; the banner gains an "Open log folder" link instead.
  - The wizard's Terminal step is titled "One last thing".
  - Escape or a click outside counts as Keep both or Skip for now, following his "offer once".
- **On his own Mac, with 2c-app and 2c-ui built together:**
  - The first-launch walk: launcher question, Remove, "Restarting anyscribe's engine.", the reload, "Old launcher removed", OK, then "One more option" showing his uv copy with Keep or Switch.
  - Killing the engine during a transcription: "anyscribe's engine stopped. Restarting it.", the reload, then "Running again" naming the job.
  - A Dock drop while a job runs (Up next), and Browse filling the box.
  - The traffic lights against the 28 px strip.

### 5. Could not check; inspected
**Could not check:** nothing ran, by rule.
- That sessionStorage survives `loadURL` to the same origin in Electron is the browser's rule (same tab, same origin), and the README relies on it ("per-port browser storage stays put"). Saved ports are reused (logic.js choosePort), so the origin holds. It has not been observed in Electron.
- Exact commands for the lead:
  - After adding G1's check: `/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py --no-shots --only open_file,banner,first_launch,removal_reload`
  - On a Mac, from a branch with both slices: `cd desktop && ANYSCRIBE_DEV_PYTHON=$(pwd)/../.venv/bin/python npm start`. Then find and kill the engine during a job: `lsof -iTCP:8470 -sTCP:LISTEN -t`, then `kill -9 <pid>`.

**Inspected:**
- The packet: ask, spec, bridge-v2 with both amendments, target, proof including the lead's new run section, lens, both declined.md files, findings, review-log and fix-plan-r1.
- The full delta-r2.patch, plus the head versions of EngineBanner, App, MacCards, ThisMac, Layout, the TranscribePage queue, the OnboardingWizard close path and desktop.ts.
- 2c-app at 70e911f: preload.js, main.js (status handler, the reload, IPC handlers, firstLaunch.mark), engine.js (restart, crash and stop paths, port), old-launcher.js (`removePausingEngine`), terminal.js (status, addToPath), logic.js (OpenFiles, choosePort, menu, restart refusal), and the README contract.
- stub.js and the check_ui open_file scenario.
- Mockup sections 3, 4, 5, 9, 10 and "For the build" (sha bcf26037).
- Screenshots at 1440 and/or 390 for:
  - The three banners (running again, restarting asked, keeps stopping).
  - The launcher states (removing, removed after the reload, threw after the reload).
  - mark-failed.
  - The Terminal states (added-unknown, added-reason, occupant, bash-refused, other-elsewhere, ready).
  - Settings terminal states (occupant, unknown, off).
  - up-next, browse-filled and the wizard Terminal step.
- Skipped: the 1000 px shots, a few 390 duplicates of cards already read, and the pixel pairs.
