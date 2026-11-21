Note: home-folder paths rewritten to `~`.

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
