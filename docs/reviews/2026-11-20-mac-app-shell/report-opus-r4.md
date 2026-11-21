Note: home-folder paths rewritten to `~`.

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
