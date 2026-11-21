Note: home-folder paths rewritten to `~`.

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
