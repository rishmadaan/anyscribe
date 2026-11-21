# Fix plan, round 2 (the lead's choices after diagnosis-r3.md; binding where it decides)

The round 1 fixes made the page infer what the app did from side signals: any status other than running, any answer to a POST, the mere existence of a note. The round 3 design reads only facts, and deletes the inference. Same scope as round 1: 2c-ui only (ui/src, the packet's checks/, docs); 2c-app at 70e911f is not changed. If the plan is wrong anywhere, say so instead of building it.

## Delete first

- `RESTART_MINE`, `restartConsumed`, and the note's part in `restartIsMine`.
- `NOTE_LIFE_MS`, and the `restarted` status listener in `removeOldLauncher`.
- Nothing stored as a "paused" flag: the page's error phase is the pause.

## The design

1. **"This restart is mine" (A2, G7, F2).** True only while this page's own `restartEngine()` or `removeOldLauncher()` call is in flight: a module variable, set before the call and cleared in `finally`. No storage. The app reloads only once the engine is running again, so the new page never needs it.

2. **The removal note (A2, C7).** `{at, before}` in localStorage, set before the call. It is resolved in one function, against the app's saved `lastRemoval`, and only while the engine reads running:
   - The reloaded page resolves it on its first running status.
   - The live page resolves it after `remove()` settles, by reading `oldLauncher.status()` again.
   - If `lastRemoval.at >= note.at`, the removal ran. The page shows the result. The reloaded page clears the note when it claims it. The live page keeps it until the card is closed (OK or Close), so a reload just after the call settles still finds it.
   - Otherwise nothing ran (a refusal), and the note is cleared at once.
   - Never decide by the shape of the result: a thrown removal also has `ok:false` and no pieces, and its result is saved.
   - A result claimed after a reload that says the engine didn't start again: add "It is running again now." The engine reads running at claim time.

3. **The queue (A1, G1).**
   - A queued file starts only when both hold:
     - the engine reads running (always true outside the app);
     - the page is idle or done, not running and not in error.
   - A file leaves the stored queue only once the engine accepted it.
   - On any failure (refusal or unreachable), it stays at the head, and the error screen is the pause. Up next leaves out the head while the error is shown for it (`lastUrl === incoming[0]`).
   - Try again resubmits it, and removes it once accepted.
   - New drops the head only when `lastUrl === incoming[0]`. A failed typed link must never delete a waiting file.

4. **Words that were missing (A3, G2, G3).**
   - EngineBanner handles `state === "stopped"` without `stoppedRestarting` in the same red card as keeps-stopping:
     - heading "anyscribe's engine stopped";
     - body "It couldn't start again. Your transcripts are safe. {exitWords(lastExit)}.";
     - the same buttons (Restart engine, Copy details, Open log folder, Troubleshooting guide) and `refused` under the body;
     - Copy details reads "Engine: stopped, couldn't start again".
   - The removal card always shows `result.reason`, whatever the carry-over.

5. **The stub (A4).** It models the real bridge by default:
   - sessionStorage acts as the app's memory, which survives a reload; localStorage acts as its disk.
   - Removal restarts and reloads by default, saves `lastRemoval`, and changes `installed` and `startAtLogin` (when carried over). Terminal and Dock state survive the reload.
   - `remove()` resolves after running, with the settle-just-before-replacement variant kept as its own case.
   - A failed mark is held in memory as asked and is not written to disk.
   - An engine-down mode makes `/api` requests fail while the stub says stopped or restarting.
   - Open-file needs no ids: the preload hides them. The page sees "acknowledged when the callback returns, even if it throws", so model exactly that.
   - Simplified component cases are labelled as such in the checker.

6. **Nits.**
   - **A5/G4.** The pieces read before the removal travel with its result, including the Settings path (`setRemoval({result, before})`). The sentence names only what was there before. For the icon-only case: "Stopped the old menu bar icon. The launcher and login item were already gone." With no snapshot: "Cleanup finished. Nothing of the old launcher is left on this Mac."
   - **G5.** The save-failed card names the question:
     - "The old launcher question may come back the next time anyscribe starts."
     - "The Terminal question may come back the next time anyscribe starts."
     - Both: "These questions may come back the next time anyscribe starts."
   - **G6.** In the added-but-missing card, drop "Takes effect in new Terminal windows..." (keep it in the path view only). When the by-hand reason ends with the line, show it without the line, then the box.

## Checks (each asserts identity; mutation-test each guard)

- Refused A, B waiting: the stored queue is exactly [A, B] and nothing is posted for B. Try again posts A, then the queue is [B]. Mutants: drop the accepted test; drop the error pause.
- Engine down, B opened: no post and no "Transcription failed" while down. After the reload, exactly one post, carrying B's path. Mutant: drop the running gate.
- A failed typed link while B waits, then New: the queue is still [B]. Mutant: New drops the head unconditionally.
- The A2 sequence: removal pending, crash, refusal, reload, then a crash while watching job J. The note key is gone, the heading is "anyscribe's engine stopped. Restarting it.", and "Running again" names J. Mutants: the note feeds `restartIsMine`; no unmatched clear.
- A thrown removal settling just before the reload: the reloaded card shows its reason. Mutant: clear on the refusal shape.
- Removal ok, carried over, reason X, engine stopped: the card shows X, the stopped heading shows, and a refused Restart shows its reason. Mutants: restore the carry-over guard; drop the stopped branch.
- Stub self-check: after removal and reload, `startAtLogin` is true, `installed` is false, and the Terminal state is kept. A failed mark reads asked until sessionStorage is cleared.

## Documented limits (record in the journal; not built)

- A crash during the job check of his own Restart or Remove click (one HTTP read long) shows the asked-for wording and records no outage, once.
- A window reopened while his own restart runs may read it as a crash.
- Files waiting in Up next are lost if anyscribe quits before they start.
- Real Electron reload timing and sessionStorage across `loadURL`: no stub proves them; they stay a check on a Mac.

## proof.md
Append "## Round 2 fixes (one entry per finding)": one line per UPHELD round 2 id (A1 to A5, G1 to G7): change | ran | saw. Mutation results for every guard above. Then the full checker run with screenshots (read the changed states yourself), ui lint and build, the rebuilt bundle committed, and the browser run pixel-identical. Commit after each finding.
