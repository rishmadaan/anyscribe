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
```