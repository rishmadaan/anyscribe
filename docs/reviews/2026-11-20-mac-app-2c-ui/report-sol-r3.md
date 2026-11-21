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
```