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

Actual Electron reload timing, sessionStorage survival through `loadURL`, native interactions, screenshots and the local-download wizard path remain unverified by this review. A combined Mac run is still required; the stub cannot supply that evidence.