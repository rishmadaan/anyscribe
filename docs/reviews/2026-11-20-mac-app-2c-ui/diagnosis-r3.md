# Diagnosis before round 3 (claude-fable-5-2, Agent tool; verbatim hand-back)

Round 3 diagnosis, 2c-ui at 9a3ed5d against the bridge at 70e911f. Read only; nothing was run.

**1. Is it right?** Yes. It closes A1, G1, A2, G7, A3, G2, G3 and A4 as a class. I confirmed the two facts it rests on:
- `restart()` returns only after the engine is running or stopped (engine.js).
- `lastRemoval` is saved before the engine is spawned again, and a refusal never saves one (old-launcher.js `removePausingEngine`, main.js:445).

Not closed, because the five points do not mention them:
- **Wording nits:** A5, G4, G5, G6.
- **A3 and G2 extras:** the stopped banner must also show the Restart refusal and its own Copy details line.
- **A4, second item:** the stub's removal must also change `installed` and `startAtLogin`.

New holes:
- **Refusal clear:** the old page must never clear the note on `ok:false` with no pieces. A thrown removal has that same shape, is saved, and is followed by a reload, so clearing it loses the result.
- **Crash inside his own call:** if the engine crashes during the job check of his own click, the banner uses the asked-for wording and records no outage, once.
- **Early note clear:** a page loaded before the old engine exits clears the note too early. Clear an unmatched note only when the status reads running.
- **Up next:** the failed file would show both as the error and in Up next, so exclude it from that list.
- **New:** drop the head only when `lastUrl === incoming[0]`, otherwise a failed typed link deletes a waiting file.
- **Stale card:** after a failed restart, the result card left open reappears after the next reload, still saying the engine didn't start.

**2. Delete:**
- `NOTE_LIFE_MS`.
- The `restarted` listener in `removeOldLauncher`.
- `RESTART_MINE` and `restartConsumed`.
- Stub ids and duplicate handling. preload.js hides them, and the page only sees "acknowledged when the callback returns, even if it throws".
- Moving stub state "outside the page". `sessionStorage` already survives the reload; use it as app memory and `localStorage` as disk.
- Any stored "paused" flag. The error phase is the pause.

**3. Checks, each asserting identity:**
- **Refused A, with B waiting:** stored queue is exactly [A, B] and nothing is posted for B. Try again posts A, then the queue is [B]. Mutants: drop the accepted test; drop the error pause.
- **Engine down, B opened:** no post and no "Transcription failed" while down; after the reload, one post carrying B's path. Mutant: drop the running gate.
- **A2 sequence** (removal pending, crash, refusal, reload, then a crash while watching job J): the note key is gone, the heading is "anyscribe's engine stopped. Restarting it.", and "Running again" names J. Mutants: the note feeds `restartIsMine`; no unmatched clear.
- **Thrown removal settling before the reload:** the reloaded card shows its reason. Mutant: clear on the refusal shape.
- **Removal ok, carried over, reason X, engine stopped:** the card shows X, the stopped heading shows, and a refused Restart shows its reason. Mutants: restore the carry-over guard; drop the stopped branch.
- **Stub self-check:** after removal and reload, `startAtLogin` is true, `installed` is false and the Terminal state is kept. A failed mark reads asked until `sessionStorage` is cleared.

**4. Decline as documented limits:**
- The crash-inside-own-call window. It is one HTTP read long.
- A window reopened during his own restart reads as a crash.
- Queued files are lost at quit.
- Real Electron reload timing. No stub proves it; it stays an owner check on the Mac.

Files: `~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/desktop.ts`, `components/EngineBanner.tsx`, `components/Layout.tsx` and `pages/TranscribePage.tsx` under the same `ui/src`.

Not checked: MacCards and ThisMac beyond grep, the stub's body, and the mockup.
