# Findings (verbatim reports)

Note: home-folder paths rewritten to `~`; originals in ~/.review-runs/2026-11-20-mac-app-2c-ui/. Both reports are verbatim (the fit report is the Agent-tool reviewer's hand-back, extracted from its transcript).


# Round 1


## report-sol-r1.md

~~~~
**NOT YET.** The requested screens are present and largely within scope, but recovery across the real app’s reload is incomplete. A supported removal-error result can also crash rendering. The recorded 173 passing checks do not cover these failures.

**Findings**

**C1. blocker, CONFIRMED: the recovery message disappears during the real engine restart.**  
Where: [EngineBanner.tsx:24](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/EngineBanner.tsx:24), [main.js:345](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/main.js:345).

Scenario: a transcription is being watched when the engine stops. The banner remembers its name only in the current page’s memory. When the engine reports `running`, the real app immediately loads `/` again. The new page has neither the remembered job nor the outage, so “Running again”, the unfinished-job warning and Open History disappear.

I reproduced the banner’s state transitions in memory using its actual handler: before document replacement, the remembered job was `"Weekly sync"`; after a fresh page received `running`, it was `null`. The banner check emits status changes without reproducing the app’s reload.

Fix: preserve the outage and watched job across document replacement, consume them after recovery, and clear them on Dismiss. Test the real reload path.

**C2. blocker, CONFIRMED: a persisted removal error without pieces crashes the dashboard.**  
Where: [MacCards.tsx:94](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/MacCards.tsx:94), [App.tsx:85](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/App.tsx:85), [old-launcher.js:218](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:218).

Scenario: removal throws, the app catches it and saves `{ok:false, pieces:null, reason:…}`, then the engine returns and the dashboard reloads. `claimRemoval()` accepts that saved result. `RemovalAfterReload` passes it directly to `RemovalResult`, which assumes `pieces` exists.

Rendering the actual component with this supported result produced:

```text
Cannot read properties of null (reading 'launcher')
```

Fix: handle no-pieces results inside `RemovalResult`, including persisted results. Show the returned reason with Retry and Close. Allow `pieces: null` in the TypeScript type.

**C3. should-fix, CONFIRMED: queued Dock files are forgotten across an engine reload.**  
Where: [Layout.tsx:23](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/Layout.tsx:23), [preload.js:12](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/preload.js:12).

Scenario: job A runs, then file B arrives through the Dock and waits in “Up next”. The preload acknowledges B after the callback merely adds its path to React state. If the engine crashes before B starts, the dashboard reload destroys that queue, while the app has already acknowledged delivery and will not resend B.

The original file remains intact, but the requested transcription silently disappears.

Fix: persist pending paths before acknowledging delivery and restore them after reload, or retain app ownership until submission is acknowledged. Test the identity of B after recovery, not just the queue length.

**C4. should-fix, CONFIRMED: the restore choice becomes inaccessible after reopening Settings.**  
Where: [ThisMac.tsx:150](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/ThisMac.tsx:150), [ThisMac.tsx:202](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/ThisMac.tsx:202), [terminal.js:341](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/terminal.js:341).

Scenario: Switch replaced an existing command, then another program or the person changes the app’s command. On reopening Settings, the real bridge returns `command:null`, so the switch already appears Off. Clicking it takes the Turn on/Switch path. There is no action that reaches `turnOff()` and its Keep current command / Restore previous command question.

I reproduced the real Terminal module against an in-memory filesystem: status returned `command:null`, while a direct `turnOff()` returned `needsChoice:"keep-current-or-restore"`. The existing check starts with stale “On” status, which hides this problem.

Fix: expose outstanding restoration state through the bridge and provide an explicit way to resolve it after a fresh status read.

**C5. should-fix, CONFIRMED: unknown Terminal availability is presented as success.**  
Where: [MacCards.tsx:219](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/MacCards.tsx:219), [MacCards.tsx:343](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/MacCards.tsx:343), [terminal.js:204](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/terminal.js:204).

Scenario: writing the command succeeds, but asking the login shell fails. The real bridge legitimately returns `state:"on"`, `uses:null` and an explanatory reason. The card still displays a green “anyscribe is ready in Terminal”. With a missing skill, it instead claims “Terminal is ready” in the warning heading and Settings row.

I reproduced the ready heading with `uses:null`. The check at `check_ui.py:860` explicitly expects that unsupported success claim.

Fix: gate readiness on confirmed command resolution. For the unknown state, use:

> **Command added; Terminal availability could not be checked.**

Show the bridge’s reason underneath.

**C6. should-fix, CONFIRMED: the once-only question guarantee is incomplete.**  
Where: [App.tsx:62](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/App.tsx:62), [App.tsx:91](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/App.tsx:91), [main.js:451](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/main.js:451).

Two cases:

- Escape or a backdrop click updates only React state, so the question returns next launch. The builder deliberately implemented and tested this exception, but the supplied spec says each question is asked once.
- The real `firstLaunch.mark()` can resolve with `{ok:false, reason}` when saving fails. Callers ignore that result and proceed as though persistence succeeded. The stub always succeeds and returns no result, so this contract difference is untested.

Fix: resolve the dismissal policy explicitly against the once-only requirement. Handle the real mark result and explain persistence failures instead of silently claiming completion. The consent question must remain separate from permission to perform removal or Terminal changes.

**C7. should-fix, PLAUSIBLE: removal can lose its post-reload result through a settlement race.**  
Where: [desktop.ts:164](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/desktop.ts:164), [main.js:354](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/main.js:354), [stub.js:88](~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/stub.js:88).

Scenario: the real removal promise settles after navigation starts but before the old document is destroyed. Its `finally` deletes the recovery note. The replacement page then cannot claim `lastRemoval`.

The stub prevents this ordering by returning a promise that never settles on its reload path. I reproduced the helper’s loss when settlement precedes document replacement: `claimRemoval()` returned `null`.

Fix: retain the recovery token until the result is explicitly consumed or dismissed. A real Electron integration run with a delayed replacement-page response would settle whether this ordering occurs in practice.

**Answers to the builder’s five “spec is wrong” points**

1. **Dragged filename and size:** agree for the renderer path implemented here. The recorded Chromium probe supports the generic overlay. It does not establish that every possible native Electron approach is unavailable. Avoid adding native machinery solely for this detail.
2. **Copy details including the log:** agree that the current dashboard bridge cannot supply the log. The replacement wording is truthful, but the approved diagnostic feature remains reduced until that change is accepted.
3. **Knowing the shell profile beforehand:** agree. Status does not expose the shell or target profile. Naming both supported profiles is reasonable. After a refusal, replace the stale promise with: “anyscribe could not add the line automatically. Add it by hand as described below.”
4. **The watched transcription keeps spinning after restart:** partly correct for a page that survives. It misses the real app’s document reload, which loses the watched job and warning entirely. C1 is the required app recovery fix; changing browser behavior is not necessary to address it.
5. **Restart when the job list is unknown:** reasonable. An enabled button that delegates the decision to the real bridge is preferable to inventing certainty. Keep showing its refusal reason. This is distinct from the confirmed busy-list case, where the button is disabled.

**Pending owner checks**

No owner-only technical action is needed to resolve these findings. After the builder supplies a working Mac integration, Rishabh’s remaining check is whether the native window and approved screens look and read as intended. The reduced drag-overlay and log-copy behavior should be presented as explicit design deviations.

**Inspection and limits**

I inspected the packet, declined findings, specified mockup sections and build promises, the source and documentation diff, all supplied check scripts and recorded outputs, and the five named real bridge files. The app checkout is at `70e911f`. UI source matches the requested target; later commits change review files only. `git diff --check` passed.

I ran only read-only inspections and in-memory reproductions. Nothing was edited, built, started or stopped. I did not independently rerun the recorded 173 checks, lint, build, mutation suite or Mac interactions. Native picker behavior, traffic-light clearance, Finder dragging, actual reload timing and the local-download wizard path remain unverified.

After adding the missing regression cases, the relevant existing checker command is:

```bash
/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py --no-shots --only banner,open_file,settings,first_launch,wizard
```

That remains a stub-based check. It must be supplemented with the combined app and engine running on a Mac.~~~~


## report-opus-r1.md

~~~~
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
~~~~


# Round 2


## report-astra-r2.md

~~~~
**NOT YET.** The requested screens are present, and the ordinary reload recovery now works by source trace. However, failed queued submissions can still disappear, a removal refusal can suppress later crash warnings, and a successful cleanup can hide a failed engine restart. The stub also retains material differences from the real bridge.

The work matches the approved job. The settled exclusions remain closed.

| Round 1 ID | Status | Evidence |
|---|---|---|
| C1 | FIXED | Outage and watched-job identity survive the ordinary reload through sessionStorage. |
| C2 | FIXED | Actual `RemovalResult` rendering with `pieces:null` showed the reason, Try again and Close without crashing. |
| C3 | PARTLY | Waiting files survive reload, but unsuccessful submissions are still discarded. A1. |
| C4 | DECLINED-OK | Settled restoration-access limitation; not reopened. |
| C5 | FIXED | Ready wording now requires `uses.via === "app"` in both cards and Settings. |
| C6 | FIXED | Quiet dismissals mark the question; failed saves produce a retained explanation. |
| C7 | PARTLY | Settlement no longer deletes the result note, but refusal detection can retain a stale note. A2. |
| F1 | FIXED | Same recovery fix as C1. |
| F2 | PARTLY | Normal requested restarts use the correct words; stale removal notes misclassify subsequent crashes. A2. |
| F3 | FIXED | The added-but-missing card preserves `addToPath`’s explanation. |
| F4 | FIXED | A manual-add refusal replaces the stale offer and standard line box. |
| F5 | FIXED | An unused occupant gets Switch in both the card and Settings. |
| F6 | FIXED | Both refusal locations explain that removal restarts the engine. |
| F7 | FIXED | Browse fills and focuses the input; Transcribe submits. |
| F8 | FIXED | A fresh Off state no longer claims a skill was removed. |
| F9 | PARTLY | Login-item and icon wording uses prior state, but launcher presence is ignored. A5. |
| F10 | FIXED | Open log folder calls the existing bridge method. |
| F11 | FIXED | The unsupported filename-and-size overlay branch is removed. |
| F12 | FIXED | Claude Code instructions follow `claudeCode`. |
| F13 | FIXED | The final wizard step reads “One last thing”. |
| F14 | DECLINED-OK | Reloading to Transcribe remains the settled app-side limitation. |
| F15 | PARTLY | Queue persistence improved; A1 remains. The remove-button exclusion stays declined. |
| F16 | FIXED | The other-copy card without Switch now says OK. |

**A1. should-fix, CONFIRMED: unsuccessful submissions drain the stored queue and overwrite earlier failures.**

Where: [TranscribePage.tsx:113](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/pages/TranscribePage.tsx:113), [useJob.ts:158](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/hooks/useJob.ts:158), [Layout.tsx:81](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/Layout.tsx:81).

`submit()` returns false for both refusal and an unreachable engine. `startIncoming()` ignores that boolean and removes the file anyway. Because the scheduling effect permits `phase === "error"`, the next file immediately starts and replaces the error and retry target.

I reproduced the actual submission, queue-consumption and scheduling code in memory with two rejected paths:

```text
After A: queue=[B], retry target=A
After B: queue=[], retry target=B
```

A has neither an accepted job nor a retained retry entry. With one file, a subsequent reload also loses its memory-only error and retry target. The original media remains intact.

Fix: consume only accepted submissions. Retain a failed item and pause automatic advancement until an explicit retry or other resolution. Test two failures by file identity, then reload and verify both remain recoverable.

**A2. should-fix, CONFIRMED: an unrelated crash during removal’s pre-check leaves a stale “requested restart” note.**

Where: [desktop.ts:270](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/desktop.ts:270), [EngineBanner.tsx:32](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/EngineBanner.tsx:32), real [engine.js:425](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/engine.js:425).

Scenario: Remove starts checking running jobs. The engine crashes while that check is pending. Its automatic restart emits `restarting`, which the UI treats as evidence that removal ran. The real engine instead refuses because its current run changed.

Using the actual `Engine.restart`, `removePausingEngine` and UI helper with controlled events produced:

```text
refusal: "The engine was stopped while the restart was being checked."
removal note retained: true
claimRemoval(lastRemoval:null): null
restartIsMine(): true
```

After recovery, the unmatched note remains. Subsequent genuine crashes use requested-restart wording and create no outage record. The ten-minute expiry is checked only during `claimRemoval`, not while classifying events.

Fix: distinguish execution from refusal using the app’s persisted removal result, rather than any non-running event. Clear unmatched refused-operation notes and preserve the genuine outage. Add this exact pending-job-check/crash sequence to the regression cases.

**A3. should-fix, CONFIRMED: successful cleanup hides a failed engine restart when login carry-over succeeded.**

Where: [MacCards.tsx:93](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/MacCards.tsx:93), real [old-launcher.js:228](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:228).

The real removal helper can return successful cleanup with `startAtLoginCarriedOver:true` and a reason explaining that the engine failed to restart. The result card displays `reason` only when carry-over is false.

Rendering that supported result showed “Old launcher removed” and the login confirmation, but omitted the engine failure. A plain stopped engine also falls through the banner without a message when `stoppedRestarting` is false.

Fix: show every returned removal reason independently of carry-over. Preserve the exact engine explanation and provide a visible recovery route, for example: “Open Settings → This Mac → Engine → Restart engine.”

**A4. should-fix, CONFIRMED: the stub still gives integration evidence for behavior the real bridge does not have.**

Where: [stub.js:31](~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/stub.js:31), [stub.js:123](~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/stub.js:123).

I executed the stub in isolated memory contexts and confirmed:

- Successful removal defaults to no restart and no saved result unless `reloadOnRemove` is explicitly enabled.
- Successful carry-over can leave `getSettings().startAtLogin` false and `oldLauncher.status().installed` true.
- Terminal and Dock changes reset to the initial configuration after page reload.
- A failed first-launch save is nevertheless written to localStorage, unlike the real app’s memory-only retention.
- `removeSettlesFirst` resolves before `running`; the real successful promise resolves after `running`, potentially before document replacement.
- File delivery omits the real preload’s IDs, duplicate handling and separate acknowledgement.

These differences do not invalidate every component check, but the recorded 212 passes do not establish real-bridge integration.

Fix: make real lifecycle behavior the default, retain app state across renderer reloads, separate failed disk persistence from process memory, and model the actual settlement and acknowledgement boundaries. Label deliberately simplified component cases separately.

**A5. nit, CONFIRMED: removal wording still names a launcher that was already absent.**

Where: [MacCards.tsx:66](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/MacCards.tsx:66), [ThisMac.tsx:145](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/ThisMac.tsx:145).

The real bridge considers a running old menu-bar icon alone sufficient for `installed:true`. With only that icon present, the actual wording function returned:

> Removed the old launcher and its menu bar icon.

It always includes the launcher, ignoring `before.launcher`. Settings also passes its refreshed, post-removal pieces as `before` when rendering an inline result.

Fix: preserve a distinct pre-removal snapshot and check all three pieces. For the icon-only case, use: “Stopped the old menu bar icon. The launcher and login item were already absent.” Without a trustworthy snapshot, say: “Cleanup finished. No old launcher components remain.”

The builder’s six departures are judged as follows:

1. **Start B after recovery rather than waiting for A:** agree. A belonged to the stopped engine and cannot finish there.
2. **Discard refused submissions:** disagree. Avoiding an automatic retry loop requires a paused failure state, not losing the request. A1.
3. **Show failed-save information afterwards:** agree. This preserves the selected action and explains possible repetition.
4. **Distinguish refusal through engine events:** disagree with the implementation. The distinction is necessary, but unrelated events do not prove removal ran. A2.
5. **Use pre-removal status instead of result pieces:** agree with the approach. Result pieces describe the final state. The implementation still needs A5.
6. **Keep an earlier outage after a requested restart:** agree. That warning describes the earlier interruption.

F7’s Browse correction is consistent with the mockup. The declined items remain accepted exclusions.

Pending owner checks: after the builder verifies the combined app, Rishabh should check the native window and wording on his Mac: open anyscribe, complete the launcher and Terminal cards, then visit **Settings → This Mac**. Traffic-light clearance, window dragging, Finder drops, Dock drops and the native Browse picker still need a real Mac walkthrough. Technical integration and the findings above are the builder’s responsibility.

I read the complete review packet, both declined lists, round 1 reports and decisions, delta, specified mockup sections and build promises, all five named real bridge files, and the relevant UI and checker code. I additionally traced `engine.js`. Production source, bundle and building docs match `9a3ed5d`; their diff whitespace check passed. The broader check flags whitespace in archived review logs.

The recorded logs support **212 passing checks** and **25 killed mutants with passing restored scenarios**. I did not rerun them. My independent executions were read-only, in-memory reproductions and component rendering. No files were written and no app, browser or server was started.

The lead should run these after adding the missing cases:

```bash
npm --prefix ~/labs/projects/anyscribe-wt/mac-2c-ui/ui run lint
npm --prefix ~/labs/projects/anyscribe-wt/mac-2c-ui/ui run build
/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py --no-shots
/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/mutate.py
```

Actual Electron reload timing, sessionStorage survival through `loadURL`, native interactions, screenshots and the local-download wizard path remain unverified by this review. A combined Mac run is still required; the stub cannot supply that evidence.~~~~


## report-opus-r2.md

~~~~
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
~~~~


# Round 3


## report-sol-r3.md

~~~~
**NOT YET.** The work matches the approved job, and most round 2 findings are fixed. Three issues remain: a delayed startup callback can erase a new removal’s recovery note, partial cleanup still hides its explanation, and one lifecycle test still models an ordering the real bridge does not have.

Reviewed production code at `99bb239`. The current checkout’s later commits change review files only. The real bridge checkout is `70e911f`. Settled exclusions remain closed.

**Round 2 findings**

| ID | Status | Evidence |
|---|---|---|
| A1 | FIXED | Failed submissions retain the head; error pauses advancement; retry consumes only acceptance; New checks head identity. |
| A2 | FIXED | The original stale restart classification is removed. A separate recovery-note race is B1 below. |
| A3 | PARTLY | Successful cleanup now shows the engine reason; partial cleanup still hides it. B2. |
| A4 | PARTLY | State persistence, failed marks, engine-down requests and default removal improved. The settlement variant remains wrong. B3. |
| A5 | FIXED | Wording checks all three previous pieces and handles a missing snapshot without guessing. |
| G1 | FIXED | Automatic queue submission requires a running engine. |
| G2 | FIXED | Plain stopped state has the red banner, refusal reason and appropriate copied details. |
| G3 | FIXED | The successful-cleanup case now shows its reason regardless of login carry-over. |
| G4 | FIXED | Settings carries the previous pieces alongside the result. |
| G5 | FIXED | Failed-save information identifies one or both questions. |
| G6 | FIXED | Added-but-missing drops the misleading note; the manual-add line is removed from the preceding sentence. |
| G7 | FIXED | A retained removal note no longer makes subsequent crashes count as requested restarts. |

**B1. should-fix, CONFIRMED: a delayed startup status callback can erase a newly started removal’s note.**

Where: [App.tsx:63](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/App.tsx:63), [desktop.ts:269](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/desktop.ts:269).

App makes two independent launcher-status requests during startup. One supplies the launcher question. The other, started after observing `running`, later calls `resolveRemoval(l, true, true)`.

Concrete ordering:

1. The question’s request finishes, so Remove is available.
2. The recovery request remains pending.
3. The person clicks Remove. A new note is written and the engine starts restarting.
4. The earlier recovery request returns with no saved removal yet.
5. Its callback passes the earlier `running` observation as literal `true`, reads the newly created note, and deletes it as unmatched.
6. Removal finishes and the page reloads. The replacement page cannot claim its saved result.

I executed the actual App effect and desktop helpers in memory with controlled promises:

```text
new removal note exists: true
engine when delayed initial status resolves: restarting
note survived delayed App callback: false
replacement page claims saved result: null
```

The real bridge permits overlapping status calls: its status handler is outside the mutation queue.

Fix: bind startup recovery to the particular predecessor note present when recovery begins. A delayed callback must not consume a note created by a subsequent click. Revalidate engine state before resolving it. Add this overlapping-request regression and assert the saved result’s identity after replacement.

**B2. should-fix, CONFIRMED: partial cleanup still hides `result.reason`.**

Where: [MacCards.tsx:153](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/MacCards.tsx:153), real [old-launcher.js:228](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:228).

The successful and no-pieces branches display the reason. The checklist branch does not.

A supported result can have `ok:false`, some pieces removed, and a reason containing uninstall diagnostics, macOS login approval guidance, or a failed engine restart. The card shows only the checklist and generic advice. Copy details includes the reason, but the card itself hides it.

Rendering the actual component in memory produced:

```text
Partial-cleanup reason rendered: false
Checklist rendered: true
```

Fix: display the computed `reason` in the checklist branch too:

```tsx
{reason && <p>{reason}</p>}
```

Use the bridge’s exact explanation. Test partial cleanup with both login guidance and an appended engine failure. The proof’s claim that the card “always shows `result.reason`” is currently false.

**B3. should-fix, CONFIRMED: the settlement test still resolves before running.**

Where: [stub.js:185](~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/stub.js:185).

With `removeSettlesFirst:true`, the stub schedules `running` 250 ms later and returns immediately. The real removal awaits `engine.restart()`, which settles after readiness or failure. Successful settlement can precede document replacement, but it does not precede readiness.

Executing the stub with virtual timers showed:

```text
remove resolved at: 230 engine: restarting
```

Consequently, the C7 and thrown-removal tests exercise the helper’s non-running fallback, rather than the real running-state resolution path they claim to cover.

Fix: emit `running`, settle removal, then delay document replacement. Assert that `engineStatus().state === "running"` when successful removal settles. Repeat for a thrown uninstall whose engine successfully restarts.

**Builder’s three gap fills**

1. **Show the returned result while the engine remains down:** agree. Keep the note unresolved until recovery can determine it from the saved result. B1 concerns an unrelated callback consuming that note prematurely.
2. **Refuse B in the New test:** agree. The POST identities establish that New preserves B and then attempts it.
3. **Show Up next beneath the error:** agree with placement. Clearer wording would be: “Up next: {names}. Try again to retry this transcription, or choose New to move on.”

**Pending owner checks**

The findings and technical verification belong to the builder. No owner action is needed to fix them.

After both slices are combined and checked, Rishabh’s Mac walkthrough remains:

- Open anyscribe, remove the old launcher, observe the reload and result, then the Terminal option.
- Visit **Settings → This Mac** and check the Terminal and engine controls.
- Check native Browse, Finder and Dock drops, window dragging and traffic-light clearance.
- Interrupt a watched transcription and verify that recovery names it.
- Confirm the documented presentation departures, including the generic drop overlay and Copy details without log contents.

**Verification and limits**

I read the named packet, prior reports and verdicts, diagnosis, binding plan, production delta, changed checks, both declined lists, specified mockup sections, and all five named real bridge files. I also traced engine restart behavior.

Independent executions were limited to in-memory source execution, component rendering and virtual-timer stub execution. Production diff whitespace checks passed; the working tree remains clean.

The supplied records support **237 passing checks** and, after the documented recheck, **33 distinct killed mutants with passing restored scenarios**. I did not independently rerun those suites.

No files were written, and no app, browser, server or build was started. Screenshots, native interactions, actual Electron replacement timing, storage survival through `loadURL`, and the local-download wizard path remain unverified by this review.

After adding the regressions, the lead should run:

```bash
npm --prefix ~/labs/projects/anyscribe-wt/mac-2c-ui/ui run lint
npm --prefix ~/labs/projects/anyscribe-wt/mac-2c-ui/ui run build
/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py --no-shots
/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/mutate.py
```

From the combined checkout’s root on the Mac, the native walkthrough starts with:

```bash
ANYSCRIBE_DEV_PYTHON="$PWD/.venv/bin/python" npm --prefix desktop start
```~~~~


## report-opus-r3.md

~~~~
## Fit review, round 3: Mac app 2c-ui (delta 9a3ed5d..99bb239; checks to f1aae31)

### 1. Verdict
**CONDITIONAL on H1 and H2.** There is no blocker.
- Every round 2 id is fixed. The approved screens and words hold, and the round 2 states read correctly at 1440 and 390 px.
- The browser dashboard is unaffected: every new path is gated on `desktop`, and `doneIncoming` is a no-op on an empty queue. The proof reports the browser run pixel-identical.
- Two should-fix items remain, both in what the new queue gate opens:
  - **H1:** the page that the app is about to reload can start a waiting file, so it runs twice or runs unseen.
  - **H2:** a file that waits for a stopped engine waits with nothing on screen.
- Both are small and sit in `TranscribePage.tsx` (plus one flag in `desktop.ts`).

### 2. Round 2 ids
- **A1 FIXED.** A file leaves the queue only when its submission returns ok. The error screen pauses the queue, and New drops only a failed head. The POST bodies are asserted. The wording and wrapping of the new line are H4.
- **A2 FIXED.** "Mine" is now the `ownCalls` counter. `resolveRemoval` runs only while the engine reads running and clears an unmatched note. Checked against engine.js `restart()` and old-launcher.js `removePausingEngine`.
- **A3 FIXED.** The reason is always shown (screenshot `r2-removed-engine-stopped`), and the stopped state has its red card.
- **A4 FIXED** for all six listed items.
  - One stub gap remains: the reload comes 30 ms after "running" and the routes answer instantly, so the old page can finish a whole POST before the reload. That gap hides H1.
- **A5 FIXED.** Screenshot `r2-settings-icon-only`: "Stopped the old menu bar icon. The launcher and login item were already gone."
- **G1 FIXED.** The lost-file scenario is closed. The gate opens H1 and H2.
- **G2 FIXED.** Heading, body, buttons, refusal line and Copy details line all match the plan.
- **G3 FIXED.**
- **G4 FIXED.** `r.shown` carries the pieces read before the call.
- **G5 FIXED.** Screenshot `first-mark-failed`: "The old launcher question may come back the next time anyscribe starts."
- **G6 FIXED.** Screenshots `first-terminal-added-reason` (no "Takes effect" note) and `first-terminal-bash-refused` ("…add this line to it by hand:", then the box). Matches terminal.js:397/405, which end the reason with the line.
- **G7 FIXED.**

### New findings

**H1. should-fix. PLAUSIBLE (timing).** A file waiting while the engine is down is started by the page the app is about to throw away. It then runs twice, or runs with nothing on screen.
- **Where:** `ui/src/pages/TranscribePage.tsx:115-129` (`engineUp` and the start effect), against 2c-app `main.js:347` (status sent to the page) and `:354` (`loadURL` right after).
- **Scenario:**
  1. The engine is restarting or stopped, and he drops or Dock-opens b.m4a. It waits, which is correct.
  2. The engine comes back. The old page gets "running", so `engineUp` turns true and the effect posts B. Meanwhile `loadURL('/')` is already loading the new page.
  3. **(a)** The POST reaches the engine but its answer arrives after the new page has replaced the old one. `doneIncoming` never runs, B stays in the stored queue, and the reloaded page posts B again. That is two jobs: two charges on a paid provider and two History entries.
  4. **(b)** The old page completes the whole cycle first. The queue empties, and the reloaded page is an idle Transcribe screen while B transcribes unseen.
  5. Only when the old page is slower than the reload is the result right.
- **Why the checks pass:** "G1: after the reload, exactly one post" counts requests across both pages. Case (b) passes it, and (b) is likely in the stub, which waits 30 ms and answers instantly.
- **Fix:** every return to running reloads the page, so a page that has seen the engine leave running must never start a waiting file. The reloaded page does it.
  - `desktop.ts`: a module flag, `let leftRunning = false; desktop?.onEngineStatus((s) => { if (s.state !== "running") leftRunning = true; });` and export a reader.
  - TranscribePage: `const engineUp = !desktop || (engine?.state === "running" && !engineLeftRunning());`
  - Check: the G1 case with `reloadDelay: 300`. After the reload, assert `posts == [B_]` and that B's progress (the Stop button) is on the reloaded page. Mutant: drop the flag.

**H2. should-fix. CONFIRMED by reading.** A file dropped or opened while the engine is stopped waits with nothing on screen.
- **Where:** TranscribePage's idle view. The "Up next" lines are only in the running view (`:313`) and the error view (`:422`). The gate holds the file while the engine is not running.
- **Scenario:**
  1. The red "anyscribe's engine stopped" card is up, and he drops b.m4a on the window.
  2. The overlay goes and Transcribe looks unchanged.
  3. He drops it again, and the queue is [b, b].
  4. After Restart engine, both copies run in turn: one file transcribed twice. The same silence covers the few seconds of any restart.
- **Fix:** in the idle view, when files wait and the engine is not running (or H1's flag is set):
  - "Up next: b.m4a. It starts once anyscribe's engine is running again."
  - Plural: "They start in turn once anyscribe's engine is running again."

**H3. nit. PLAUSIBLE.** After a removal from the first-launch question, the "One more option" Terminal card can flash before the "Old launcher removed" card.
- **Where:** `App.tsx:49-76`. Round 2 claimed the removal in the same `Promise.all` that sets `asked`. Round 3 claims it in a second effect that starts one engine-status read later. In between, `askTerminal` is true, because `removed` is still null.
- **Scenario:** an existing user with both questions unasked presses Remove, and the page reloads.
  1. `asked` lands first, so TerminalFlow mounts and calls `terminal.status()`, a login-shell query.
  2. Then `removed` lands and the Terminal card unmounts.
  3. After OK it mounts again, and its status call queues behind the first.
- **Why the checks miss it:** no check walks this order. Every removal check uses `terminalAsked: True`.
- **What would settle it:** in `first_launch`, use `firstLaunch={"oldLauncherAsked": False, "terminalAsked": False}`, press Remove, call `after_reload`, then assert `r.calls(p, "terminal.status") == []` before OK.
- **Fix:** hold the Terminal card until the removal check has finished, e.g. `const [removalChecked, setRemovalChecked] = useState(false)`, set true in that effect's `.then` and `.catch`, and add `&& removalChecked` to `askTerminal`.

**H4. nit. CONFIRMED** (screenshot `r2-queue-refused-head@390`). The new "Up next" line under the error.
- **(a) Wrapping:** `break-all` splits ordinary words: "or cho / ose New." The running view's line (`:314`) has the same class.
  - Fix: use `break-words` on both lines.
- **(b) Wording:** "It starts once you try this one again" is not what happens. After Try again, B waits until A finishes.
  - Words: "Up next: b.m4a. It waits until you try this one again or choose New."
  - Plural: "They wait until you try this one again or choose New."

### 3. The builder's three gap fills (advice)
1. **The live page, engine not running, shows what `remove()` returned; the note waits for the running engine. Agree.** It matches old-launcher.js: `lastRemoval` is saved before the relaunch, and the reason is appended when the relaunch fails.
   - Side effect: a card closed with Escape (LauncherQuestion's `onClose` is `launcherKept`, which keeps the note) comes back after the next reload. So does Settings' inline card, which has no OK. It comes back once, with "It is running again now." Acceptable, because it carries news. The A3 check relies on it.
2. **The New check refuses B too. Agree.** Starting B right after New is the designed behaviour, and the POST bodies (L, then B) prove it.
3. **Up next under the error. Agree** with showing it; change the words and wrapping as in H4.

### 4. Pending owner checks
**Deliberate departures still for him to accept** (carried from round 2):
- The drop overlay has no file name or size.
- Copy details carries no log; there is an Open log folder link instead.
- The wizard's Terminal step is titled "One last thing".
- Escape counts as the quiet answer.

**New words this round:**
- The stopped red card.
- "It is running again now."
- The icon-only sentence.
- The three "may come back" sentences.
- The Up next line under the error, after H4.

**On his Mac, with 2c-app and 2c-ui built together:**
- The first launch with both questions unasked: Remove, "Restarting anyscribe's engine.", the reload, "Old launcher removed" (watch for H3's flash), OK, then "One more option".
- Kill the engine during a job: the crash words, the reload, then "Running again" naming the job.
- With the red card up, drop a file, then press Restart engine. It must run once, with its progress on screen (H1, H2).
- The traffic lights against the 28 px strip, the native picker, and a Dock drop.

None of H1 to H4 is his to fix; they are the builder's.

### 5. Could not check; commands; inspected
**Could not check** (nothing was run, by rule):
- Which way H1's race goes in real Electron: an in-flight fetch against `loadURL`'s commit.
- How long H3's flash lasts.

**Commands for the lead, after adding the H1 and H3 assertions above:**
- `/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py --no-shots --only r2_facts,first_launch,removal_reload`
- Then `/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/mutate.py` with a mutant that drops H1's flag.

**Inspected:**
- The brief.
- The packet: ask, spec, bridge-v2 with its Amendments and Amendment 2, target, lens.
- proof.md in full, including "Round 2 fixes".
- Both declined.md files.
- From findings.md, the round 2 reports, then review-log, diagnosis-r3 and fix-plan-r2.
- The full delta-r3.patch, and the stub.js diff 9a3ed5d..f1aae31.
- The head versions of `App.tsx`, `desktop.ts`, `EngineBanner.tsx`, `MacCards.tsx` (RemovalResult, TerminalFlow's effect), the `Layout.tsx` queue, the `TranscribePage.tsx` queue and views, and `useJob` `submit`.
- The r2_facts, first_launch and removal_reload checks in `check_ui.py`, and the request recording.
- 2c-app at 70e911f:
  - main.js in full.
  - engine.js in full.
  - old-launcher.js: `status`, `remove`, `removePausingEngine`.
  - preload.js.
  - terminal.js: the addToPath reasons.
  - logic.js: the menu model.
- The mockup text for sections 3, 4, 5, 9, 10 and "For the build".
- Screenshots at 1440 and 390: `r2-queue-refused-head`, `r2-removed-engine-stopped`, `r2-settings-icon-only`, `first-mark-failed`, `first-terminal-added-reason`, `first-terminal-bash-refused`, `first-launcher-removed`, `first-launcher-failed`, `settings-launcher-removed`, plus `banner-keeps-stopping@390` for the shared red-card layout.

**Skipped:**
- The 1000 px shots.
- The pixel pairs.
- `desktop/README.md` (the code was read instead).
- The mutation logs beyond the proof's table.
~~~~


# Round 4


## report-sol-r4.md

~~~~
**GOOD TO GO for the round 4 UI delta, within the documented limits.** The changes match the approved job. I found no new correctness defect. Native Mac integration remains unverified.

Reviewed production target `6e7a335` against bridge `70e911f`. The current UI checkout’s later changes are review files only. Settled exclusions remain closed.

| Round 3 ID | Status | Evidence |
|---|---|---|
| B1 | FIXED | `desktop.ts:276,292` and `App.tsx:78` bind recovery to the note present at page load. In-memory execution confirmed an older callback cannot clear a newer note, and a matching result is claimed once. |
| B2 | FIXED | `MacCards.tsx:168` renders the checklist’s reason. Actual component execution retained the exact explanation above the generic advice. |
| B3 | FIXED | `checks/stub.js:203` emits running before settlement. Virtual-timer execution confirmed this for successful and thrown removals. |
| H1 | FIXED | `desktop.ts:99` records non-running observations permanently; `TranscribePage.tsx:117` blocks automatic starts on that page. Recorded checks identify the replacement page as the sole sender. |
| H2 | FIXED | `TranscribePage.tsx:127` supplies the waiting-file line in idle, both completed views and cancelled. Recorded checks exercise idle and ordinary completion; the other placements are confirmed by source. |
| H3 | FIXED | `App.tsx:76,93` holds Terminal through recovery. In-memory execution confirmed it stays held on a doomed page and becomes available after the recovered result is dismissed. |
| H4 | FIXED | All Up next lines use `break-words`; the error line uses the planned “It waits until…” wording. The wrapping utility exists in the committed CSS. |

**New findings:** none.

The builder’s timing adjustments are justified: they make the recovery callbacks return inside the windows the guards must protect. The recorded mutation evidence supports 43 distinct killed mutants with passing restored scenarios: 41 passed initially, then the two survivors passed after the timing checks were corrected.

For B2’s generic advice, use these exact words:

> Try again. Use Copy details to share what is still there.

Keep the bridge’s explanation immediately above it. One correction to the proof: the repeated logout sentence comes from the checker’s `X` fixture. The real bridge at `70e911f` does not append that sentence.

My independent checks used source execution in memory, component execution and virtual timers. They confirmed:

- A newer removal note survives an older callback.
- A matching result is claimed once; an unmatched note clears only while running.
- An initial restarting observation permanently dooms that page.
- Terminal remains held through pending recovery.
- Successful and thrown stub removals followed this order: restarting at 30 ms, running at 480 ms, settlement at 500 ms, reload at 780 ms.

Those timings describe the stub, not Electron.

Pending owner checks: after the builder verifies the combined app, Rishabh should walk **Open anyscribe → Remove the old launcher → result → OK → One more option**, then **Settings → This Mac**. He should assess the native window, traffic-light clearance, dragging, Browse and Dock drops, and accept the documented presentation departures. Technical integration and regression checks remain the builder’s responsibility.

I inspected every file named by the brief, the specified mockup sections, production delta, changed checker and mutation code, recorded outputs, relevant UI paths, and all five named real bridge files. I additionally traced `engine.js` restart behavior. Production whitespace checks passed; the worktree remained clean.

The records show **247 passing checks**, including nine browser pixel comparisons. I did not independently rerun those checks, lint, build or mutations, or inspect screenshots. Actual Electron reload timing, storage survival through `loadURL`, native interactions and the local-download wizard path remain unverified. Nothing was written, built, started, stopped or deleted.

Exact commands for the lead:

```bash
npm --prefix ~/labs/projects/anyscribe-wt/mac-2c-ui/ui run lint
npm --prefix ~/labs/projects/anyscribe-wt/mac-2c-ui/ui run build
/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py --no-shots
/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/mutate.py
```

From the combined checkout’s root on the Mac:

```bash
ANYSCRIBE_DEV_PYTHON="$PWD/.venv/bin/python" npm --prefix desktop start
```~~~~


## report-opus-r4.md

~~~~
## Fit review, round 4: Mac app 2c-ui (code 99bb239..6e7a335; checks to 97d35b4)

### 1. Verdict
**GOOD TO GO.** There are no blockers and no should-fix items.
- All seven round 3 ids are fixed.
- The two rules hold against the real bridge. In 2c-app at 70e911f, engine.js:282 is the only place that emits "running", and it is always preceded by a state that is not running. main.js:347-354 then reloads the page every time. So every doomed page is reloaded.
- The browser dashboard is untouched. Every new path is behind `desktop`, `engineUp` is always true without the bridge, and `waitingForEngine` is null there.
- Four nits are below. Three are small screen edits (K1, K3, K4) and one is checks-only (K2). He would meet K1 first: it is on the card for any partial cleanup.

### 2. Round 3 ids
- **B1 FIXED.**
  - The note is read once at load (desktop.ts:276).
  - With no note there is no recovery read (App.tsx:78).
  - `resolveRemoval` checks `n.at === at` again before it clears or claims anything (desktop.ts:292-294).
  - The live page's refusal clear is tied to `mine.at` (desktop.ts:307-313).
  - The literal `true` arguments are gone.
- **B2 FIXED** (the reason now shows). Its wording with the real bridge is K1.
- **B3 FIXED.** `removeSettlesFirst` no longer appears anywhere in checks/ or ui/src. The stub emits "running", then settles, then reloads 300 ms later, and records the engine state when the removal settled.
- **H1 FIXED.**
  - Flag: desktop.ts:100-112. Start gate: TranscribePage.tsx:117.
  - The check tags each request with the page that sent it and asserts `[(b.m4a, "1")]`: exactly one post, from the reloaded page.
- **H2 FIXED.**
  - The line is in the idle view, both completed views and the cancelled view (TranscribePage.tsx:156/360/391/402).
  - Screenshots `r3-idle-waiting` and `r3-completed-waiting`, at 1440 and 390, read plainly under the red card.
  - The running and error views still have their old wording: see K3.
- **H3 FIXED.** `removalChecked` starts as `!noteAtLoad` and is set after the recovery read. The check asserts `terminal.status` is `[]` until OK.
- **H4 FIXED.** `break-words` is on both lines, and the new words are in place. At 390 px, "choose New." no longer splits inside a word (`r2-queue-refused-head`).

### New findings (ranked by what he would hit)

**K1. nit. CONFIRMED by reading.** On a partial cleanup, the real reason repeats the card's title and checklist.
- **Where:** MacCards.tsx:168, against old-launcher.js:200 in 2c-app.
- **What the bridge sends:** the reason always starts `Cleanup didn't finish: <what is left>.` After that it may add "The uninstall said: …", the macOS approval note, and "anyscribe's engine didn't start again afterwards: …".
- **Scenario (the common failure the mockup itself draws: the old menu bar icon survives):**
  - Title: Cleanup didn't finish
  - Checklist: Launcher: removed / Login item: removed / Old menu bar icon: still running
  - Then: "Cleanup didn't finish: the old menu bar icon is still running."
  - Then: "Log out and back in to stop it, or try again."
- The new line says nothing the title and checklist don't already say.
- **Placement:** with the extra notes sitting between the checklist and the mockup's advice, the "it" in "stop it" can read as the login-approval or engine note instead of the icon.
- **Fix:**
  - Show only what the bridge adds: `const extra = reason?.replace(/^Cleanup didn't finish: [^.]*\.\s*/, "") || null;`
  - Render `{extra && <p>{extra}</p>}` below the advice paragraph, not above.
  - Copy details keeps the full `result.reason`.
  - I checked the expression with node on the three real shapes. "Icon only" gives null, so the card is exactly the mockup's. "Uninstall failed" gives "The uninstall said: …". "Login plus engine" gives both notes.
  - Showing it below departs from fix-plan-r3's "above"; the reason is that "it".

**K2. nit. CONFIRMED.** The checks use removal reasons the real bridge never sends. That hid K1 and K4 and produced a false note in the proof.
- **Where:**
  - check_ui.py:1382: X = "Cleanup didn't finish: … Log out and back in to stop it."
  - :128-129: REMOVE_FAIL "The old menu bar icon is still running."
  - :1385: "…macOS needs your approval." The real text ends ": System Settings, General, Login Items." (old-launcher.js:189).
  - :1309: the engine note ends with a period. The real one usually does not: K4.
- **Proof note:** the proof says "The real reason's last sentence and the generic advice both say 'Log out and back in'". That is false. No file in desktop/src at 70e911f contains "Log out".
- **Also:** the comment at stub.js:148 says the stub reads `lastRemoval` "as the real IPC handler", when asked. The real handler (main.js:437) reads it after the pieces read finishes. No current check depends on this difference.
- **Fix:** build these reasons from old-launcher.js:200/189/228, and correct the comment.

**K3. nit. CONFIRMED by reading.** While the engine is down, the running and error views still promise the old trigger.
- **Where:** TranscribePage.tsx:327 ("It starts when this one finishes.") and :439 ("It waits until you try this one again or choose New.").
- **Running view scenario:** b.m4a waits behind a running job, then the engine keeps stopping. Proof spec problem 4 says the progress view stays up. The line under it says B starts when this one finishes, which never happens.
- **Error view scenario:** with the engine down, the line says B waits for his Try again or New. In fact the reloaded page starts B on its own.
- **Fix:** when `!engineUp`, both views use H2's words for `waiting`: "Up next: b.m4a. It starts once anyscribe's engine is running again." The plural is "They start in turn once anyscribe's engine is running again." These are not new words.

**K4. nit. CONFIRMED by reading.** "It is running again now." is glued onto a reason that has no final period.
- **Where:** MacCards.tsx:86, against old-launcher.js:228 and engine.js:240/287/325/447.
- **What the bridge sends:** the engine note is `anyscribe's engine didn't start again afterwards: ${reason}`. That reason is often unpunctuated, for example "another program is using port 8470".
- **What he sees after the reload:** "…another program is using port 8470 It is running again now." This happens in both the Removed card and the checklist.
- **Fix:** `${r.reason}${/[.!?]$/.test(r.reason) ? "" : "."} It is running again now.` I checked it with node.

No new issue found in the areas the brief asked about:
- **A waiting file that never starts:** a doomed page always gets its reload. Every reloaded page reads running and is not doomed.
- **A removal result never shown or shown twice:**
  - A note left from an earlier app run is cleared quietly as "refused", because `lastRemoval` lives in memory only.
  - The live page's in-place card and the reloaded card appear one after the other, not side by side.
  - Superseded notes are the documented limit.
- **The Terminal card never shown:** it is held only while a note from page load is being settled, and the read's success and failure paths both release it.
- **Clicks on a doomed page with the engine stopped:** Remove, Try again, Restart and Turn on all work and end in the reload.

### 3. Answer: B2's reason and the advice under it
With the real bridge they cannot repeat "Log out and back in". Only the checker's invented X says it (K2). What the real reason repeats is "Cleanup didn't finish" and the piece that is left (K1).

Keep the mockup's advice verbatim:
- "Log out and back in to stop it, or try again." when the icon is left;
- "Try again. If it still doesn't finish, Copy details shows what was left." otherwise.

Under it, show the bridge's reason minus its opening "Cleanup didn't finish: …." sentence, and only when something is left after removing it.

For the common case the card then reads exactly as the mockup:
- Cleanup didn't finish
- Launcher: removed / Login item: removed / Old menu bar icon: still running
- Log out and back in to stop it, or try again.
- Try again · Close · Copy details

When the bridge adds something, for example:
- Log out and back in to stop it, or try again.
- This app is set to start at login, but macOS needs your approval: System Settings, General, Login Items.

### 4. Pending owner checks
**Departures from the mockup still for him to accept:**
- The drop overlay shows no file name or size.
- Copy details carries no log text; there is an Open log folder link instead.
- The wizard step is titled "One last thing".
- Escape counts as the quiet answer.

**New words he has not seen:**
- The two H2 sentences.
- The two H4 sentences.

**On his Mac, with 2c-app and 2c-ui built together:**
1. First launch with both questions unasked: Remove, "Restarting anyscribe's engine.", the reload, "Old launcher removed", OK, then "One more option" with no Terminal flash.
2. With the red card up, drop a file. Up next should name it. Press Restart engine: it must run once, with its progress on screen.
3. Kill the engine during a job: "Running again" names the job.
4. The traffic lights against the 28 px strip, the native picker, and a Dock drop.
5. Session storage surviving the app's reload. This is proven in Chromium only.

None of K1 to K4 is his to fix; they are the builder's (or lead-made, with proof).

### 5. Could not check; commands; inspected
**Could not check:**
- Anything in real Electron: reload timing, session storage across the reload, the native picker.
- The 1000 px screenshots.
- A screenshot of the cancelled view with the H2 line (none was taken).
- Mutation logs beyond their summary lines.

**Ran:** only read-only git, grep and sed, plus two node one-liners that print (the K1 and K4 expressions on the real reason shapes).

**For the lead, after K1 to K4:**
- `/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py --only r3_facts,r2_facts,removal_reload,first_launch,settings`
- With screenshots, then read `r3-partial-reason`, `first-launcher-failed` and `r2-removed-engine-stopped`.

**Inspected:**
- The brief, ask, spec, bridge-v2 (both amendments), target, lens, proof.md in full, and both declined.md files.
- Review records: review-log, diagnosis-r4, fix-plan-r3, and the round 3 reports (opus, sol).
- Code: delta-r4.patch in full; App.tsx, desktop.ts:90-320, MacCards.tsx:60-330 and TranscribePage.tsx:95-160 at 6e7a335.
- Checks: the stub.js diff 99bb239..97d35b4 and stub.js:140-215; the check_ui.py r3_facts and reason constants; run-full.out (247 passed, 0 failed); mutate-r3.out and mutate-r3-recheck.out (41 of 43, then 2 of 2).
- Bundle: new strings present in index-BPHHF8_E.js.
- 2c-app at 70e911f: main.js:125-260 and 335-370 plus the IPC handlers, engine.js:160-464, old-launcher.js:120-234, preload.js in full, and a grep of desktop/README.md.
- Mockup sections 3 to 10 (its sha256 starts bcf26037, matching the spec).
- Screenshots at 1440 and 390: `r3-partial-reason`, `r3-idle-waiting`, `r3-completed-waiting`, `r2-queue-refused-head`, `app-up-next`, `first-launcher-failed@1440` and `settings-launcher-failed@390`.

Skipped: terminal.js and old-launcher.js above line 120 (nothing in this delta touches them).
~~~~


# Round 5


## report-sol-r5.md

~~~~
**NOT YET.** K3 introduces a false start promise when a failed dropped file remains ahead of “Up next.” No new data-loss defect found.

- **K1 FIXED:** Only the opening cleanup summary is stripped. Uninstall messages, including embedded full stops, login notes and engine notes survive. Copy details retains the original reason.
- **K2 PARTLY:** The replacement words match the bridge, but the partial-cleanup fixture combines an approval note with an impossible carry-over flag.
- **K3 PARTLY:** Correct for the tested typed-link scenario; overpromises when a failed queued file remains at the head.
- **K4 FIXED:** Bare engine reasons receive a full stop before “It is running again now.” Existing terminal punctuation is preserved.

**E1. should-fix. CONFIRMED.**  
Where: [TranscribePage.tsx:440](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/pages/TranscribePage.tsx:440), using the helper at line 128.

Drop A and B; A is refused, leaving `[A, B]`. While the engine is down, the error view now says: “Up next: b.m4a. It starts once anyscribe’s engine is running again.”

Recovery reloads the page and retries **A first**. If A is refused again, the error pause blocks B indefinitely until another action. Engine recovery alone therefore does not start B.

I reproduced this using the source’s extracted waiting-list expression and start gate. The new check at [check_ui.py:1546](~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py:1546) uses a failed typed link, so B is the queue head, and closes before recovery.

Fix: when the failed file remains at the queue head, use: **“Still queued behind the failed file, which will be tried again after the engine restarts.”** Extend the check through recovery with `[A, B]` and A refusing again.

**E2. nit. CONFIRMED.**  
Where: [check_ui.py:1477](~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py:1477).

`PART` now includes the macOS approval note while setting `startAtLoginCarriedOver: True`. The real bridge sets that flag only for `enabled`; `requires-approval` produces this note with **false** ([old-launcher.js:187](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:187)).

I executed the bridge’s extracted `remove()` body with simulated inputs and reproduced the same reason with `false`. Set this fixture’s flag to `False`. The mismatch does not invalidate the stripping assertion, but the fixture is not a producible bridge result.

**Verification and limits**

Inspected both deltas, the round-4 report, the specified proof section, both declined lists, both fix plans, production context, bridge reason construction, changed checks, stub, mutation script and recorded output. Production source matches `4abb653`; the bridge is at `70e911f`.

Read-only Node checks passed **520 generated reason cases**. No unintended supplementary reason disappeared or duplicated.

The mutation output records all four targeted failures and a restored **32 passed, 0 failed**. These demonstrate detection of the four reversions, not the retained-head recovery scenario above.

I did not run builds, browsers, servers or mutation scripts. The claimed **249-check** run and new screenshots were not independently verified: the committed full-run log contains **247 passed**, and the proof places the newer artifacts in an unspecified scratch folder. No files were changed.~~~~
