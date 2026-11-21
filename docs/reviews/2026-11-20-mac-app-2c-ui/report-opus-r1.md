## Fit review, round 1: Mac app 2c-ui (diff 6dc70b2..12aa942)

### 1. Verdict
**NOT YET.** Most of the work is right. It is the job he asked for: mockup sections 3, 4, 5, 9 and 10 are inside the app, the browser dashboard is unchanged, and the mockup's words are used almost everywhere. One approved state cannot appear in the real app (F1), and a few screens say things that are wrong or contradict themselves in front of him (F2 to F6).

### 2. Findings

**F1. blocker. CONFIRMED by reading both sides.** The "Running again" banner never reaches him in the real app.
- **Where:** `ui/src/components/EngineBanner.tsx:24-38` keeps the outage and the watched job only in memory. 2c-app reloads the whole page to `/` every time the engine comes back to running: `~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/main.js:354` (`mainWin.loadURL(\`${engineOrigin()}/\`) // after a restart`), and README "Crash: ... restarts the engine and reloads the dashboard". The stub does not do this. `checks/stub.js:45` `__emit` switches to running without a reload, so checks `check_ui.py:406-431` pass against behaviour the app does not have.
- **Scenario:** he is watching "Weekly team sync" when the engine crashes. He sees the amber restarting banner. The page then reloads to an empty Transcribe page, with no "Running again", no job name and no Open History. Mockup section 10's middle state, and the lens job "the engine stopping and coming back while he watches a job", silently disappear. The proof's claim that section 10 is covered is stronger than its evidence.
- **Fix:**
  1. When the banner records an outage, also write `{job, at}` to localStorage (the same pattern as `removeOldLauncher` / `claimRemoval`).
  2. On load, when `engineStatus()` reads running and that note exists, show "Running again" naming the job once, then clear the note.
  3. Make the stub reload on every return to running (`location.href = "/"`), and re-run the banner checks.
- The builder's point 4 (the Transcribe page spinning forever) does not happen in the real app because of the same reload, so the useJob change is not needed for this.

**F2. should-fix. CONFIRMED (screenshot `first-launcher-removing@1440`).** His very first click reads like a crash.
- **Where:** `EngineBanner.tsx:100-108`.
- **Scenario:** on first launch he clicks "Remove the old launcher". An amber banner then says "anyscribe's engine stopped. Restarting it." The same thing happens after he clicks Restart engine in Settings. Both restarts are deliberate, but the words are the ones for a crash.
- **Fix:** when the page started the restart (the removal note exists, or a `restartEngine()` call from this page is pending), show "Restarting anyscribe's engine. This usually takes a few seconds." Keep the mockup's words for automatic restarts.

**F3. should-fix. CONFIRMED by reading.** `addToPath`'s own explanation is thrown away.
- **Where:** `ui/src/components/MacCards.tsx:266-283`. On `ok: true` the result `r` is dropped and only `status()` is shown.
- **Scenario:** 2c-app returns `ok: true` with the reason "The line is in ~/.zprofile, but your shell setup removes it again later (check ~/.zshrc)." He sees the generic "The line was added, but Terminal still can't see the command. Open a new Terminal window and check, or add it by hand." The app has already asked a fresh login shell, so opening a new window will not help, and the specific cause is hidden.
- **Fix:** keep `r.reason` and show it in the added-but-missing card in place of that sentence. Use the generic sentence only when no reason came back, and shorten it to "The line was added, but Terminal still can't see the command."

**F4. should-fix. CONFIRMED (screenshot `first-terminal-bash-refused@1440`).** The path card contradicts itself after a refusal.
- **Where:** `MacCards.tsx:357-368`.
- **Scenario:** the paragraph above still says "anyscribe can add this line to ~/.zprofile (~/.bash_profile if your Terminal uses bash):" while the red line below says it left the file alone. The real 2c-app reason also repeats the line itself ("Your bash reads ~/.profile; add this line to it by hand: export PATH=..."). The stub's wording differs.
- **Fix:** when `byHand` is set, drop that paragraph. Show the reason as plain text (not red: it is guidance, not a failure) above the line box.

**F5. should-fix. CONFIRMED in code; how often this state happens is PLAUSIBLE.** A dead end when a stray copy sits at `~/.local/bin` but Terminal does not use it.
- **Where:** `MacCards.tsx:219-224` and `289-306`; `ThisMac.tsx:193-206`. 2c-app's `status()` reports state "off" with `occupant` set when `~/.local/bin/anyscribe` exists but the login shell finds no anyscribe (`terminal.js:204-206` and `235-240`).
- **Scenario:**
  1. He clicks Turn on (card or Settings toggle).
  2. `turnOn({replace:false})` refuses with "Another anyscribe is already at ~/.local/bin/anyscribe. Keep it, or switch to this app's copy ...".
  3. That text appears in red, but no Switch button exists in either place. He is told to switch and given no way to.
- **Fix:** whenever `occupant` is set, offer "Switch to this app's copy" (which calls `turnOn({replace:true})`) in the offer card and in the Settings row, not only in the other-copy state. The contract says to offer Switch when `occupant` is set, not only in that state.

**F6. should-fix. CONFIRMED (screenshot `first-launcher-refused@1440`).** The refusal under the launcher question talks about something he did not ask for.
- **Where:** `MacCards.tsx:176`; `ThisMac.tsx:139`.
- **Scenario:** he clicks "Remove the old launcher" and reads "Wait for transcriptions to finish before restarting the engine." He never asked to restart the engine.
- **Fix:** prefix the reason in both places: "Removing the old launcher restarts the engine. " + reason.

**F7. should-fix. CONFIRMED by reading (judgement call; the spec says "submits").** Browse inside the app starts transcribing straight away.
- **Where:** `ui/src/components/URLInput.tsx`, the new `pathForFile` branch.
- **Scenario:** today, Browse fills the box so he can tweak the options first (the code's own comment says so). The mockup says "As today" and only changes how the file is read. In the app, picking a file starts the job with whatever options are set. Drop and Dock starting at once makes sense; Browse sits inside the box.
- **Fix:** `setUrl(path)` and focus the input, instead of `onSubmit(path)`. This is one line, and it matches the browser.

**F8. nit. CONFIRMED (screenshot `settings-terminal-off`).** "Off. anyscribe isn't in Terminal, and its Claude Code skill is removed." also shows on a fresh Mac where the skill was never installed.
- **Where:** `ThisMac.tsx:193-199` shows it whenever `claudeCode && skill !== "installed"`.
- **Fix:** add the skill clause only right after a successful `turnOff` in this view. Otherwise show "Off. anyscribe isn't in Terminal."

**F9. nit. CONFIRMED by reading.** The Removed card claims a login item that did not exist.
- **Where:** `MacCards.tsx:81-85`.
- **Scenario:** without carry-over and without a reason, the card always says "Removed the old launcher, its login item and its menu bar icon." Per 2c-app, that combination means there was no login item before.
- **Fix:** in that case say "Removed the old launcher. Nothing of it is left on this Mac."

**F10. nit. CONFIRMED.** The keeps-stopping banner names a hidden path he cannot click.
- **Where:** `EngineBanner.tsx:86`.
- **Fix:** replace "Its log is in ~/.anyscribe/logs/app.log." with an "Open log folder" link that calls the existing `openLogFolder()`. Keep Copy details as built.

**F11. nit. CONFIRMED (code and docs say the name is never given in a real drag).** The drop overlay's name-and-size branch is dead code.
- **Where:** `ui/src/components/Layout.tsx`: the `dragging` object, the `mb()` helper and the second line of the overlay.
- **Fix:** delete it, keeping only "Drop to transcribe". Less code, and the same screen.

**F12. nit.** The ready card (`MacCards.tsx:392-397`) always shows "In Claude Code, ask it to transcribe a link." and "If Claude Code isn't on this Mac yet, turn this off and on again ...". The dashboard knows `claudeCode`. Show the first sentence only when it is true and the second only when it is false.

**F13. nit.** The wizard's Terminal step is headed "All set", then "Last step · optional" (`OnboardingWizard.tsx` stepTitle). The two signals clash. Use the title "One last thing" for the `terminal` step.

**F14. nit, cross-slice (2c-app), PLAUSIBLE.** Because of the reload to `/` (F1):
- Restart engine pressed in Settings lands him on Transcribe.
- The old-launcher result after a removal started from Settings opens over Transcribe, not Settings. The stub's `location.reload()` keeps the route, so the screenshots show Settings.
- Fix on the app side: reload the current URL (for example `webContents.reload()` when the port is unchanged).

**F15. nit.** The "Up next" queue (`TranscribePage.tsx`) has no way to remove a wrongly dropped file. It also lives only in page memory, after the app has already acknowledged the files, so a restart mid-job loses the queued ones. Acceptable for now; note it.

**F16. nit.** On the other-copy card with no `occupant`, the only button is "Keep the one I have", and there is nothing to choose between. Label it "OK" when no Switch is offered.

### 3. The builder's five "spec is wrong" points
1. **Drop overlay can't name the file.** Agree; the drag probe supports it. Delete the dead branch (F11) and tell Rishabh, since it differs from the approved mockup.
2. **Copy details can't include the log.** Agree. Better than naming the path: give him an Open log folder link through the existing bridge call (F10).
3. **The path card can't know the profile file in advance.** Agree. Naming both files is truthful; a `shell` field in the status can come later.
4. **The job spins after an engine restart.** In the real app the page reloads to `/`, so it does not spin. The real problem is that the job disappears without a word, which is F1. The useJob 404 change is not needed now.
5. **Restart engine stays enabled when the job list can't be read.** Agree, for the reason given. The app's refusal covers it.

### 4. Pending owner checks
- The drop overlay shows "Drop to transcribe" without the file's name and size: a deliberate change from the approved mockup.
- Browse in the app: fill the box (today's behaviour, recommended) or start at once (F7).
- On his own Mac, as he will use it: the first-launch walk with his old launcher and his uv copy (launcher question, Remove, the reload, the Removed card, then "One more option"). Also the traffic lights against the 28 px strip, dragging the window by the strip, a Finder drag onto the window, a Dock drop, and Browse with the native picker.

### 5. What I could not check, and what I inspected
**Could not check:** nothing ran (read-only, by rule), so no real Electron app, no Mac, and no live 2c-app results. Stub drift I found:
- automatic restart without a reload (F1);
- removal reload keeps the route;
- the bash refusal wording;
- an other-copy reason shown when the command is not ours, which real 2c-app only sends when ours is written;
- `getSettings` not reflecting carry-over (the Settings shot shows Start at login Off under "This app now starts at login").

I did not verify that localStorage survives a port change after a restart; 2c-app's `settings.port` can change. If it does not, both the removal result and the F1 fix would be lost.

**Inspected:**
- The packet: `ask.md`, `spec.md`, `bridge-v2.md` with both amendments, `target.md`, `proof.md` (including every New wording line), `lens.md`, and `declined.md` (nothing reopened).
- The mockup's sections 3, 4, 5, 9, 10 and "For the build" (sha starts bcf26037, matches).
- The diff 6dc70b2..12aa942: `desktop.ts`, `EngineBanner.tsx`, `MacCards.tsx`, `ThisMac.tsx`, `App.tsx`, `Layout.tsx`, `OnboardingWizard.tsx`, `URLInput.tsx`, `TranscribePage.tsx`, `SettingsPage.tsx`, `index.css`, and the docs diff.
- 2c-app's contract and code: `desktop/README.md`; `terminal.js` (status, turnOn, addToPath, askLoginShell); `main.js` (the reload on running).
- `stub.js` (restart and removal).
- About 30 screenshots at 1440 px, plus 390 px for the launcher question, the Terminal offer, Settings default and the keeps-stopping banner.

I skipped the 1000 px shots and the pixel-comparison pairs.
