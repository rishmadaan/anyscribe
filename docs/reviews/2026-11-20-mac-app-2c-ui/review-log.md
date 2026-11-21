# Review log: anyscribe Mac app, phase 2c-ui

Size: L
Sized because: the screens are the only gate before writes to the owner's shell profile and Terminal command and before the old launcher's removal (data loss class), and they consume the bridge (security class)
Cap: 5 (data loss and security: consent gates for owner-file writes; the bridge)
Packet: v1

| Round | Role | Model, effort | Lane | Target (sha/version) | Verdict | Raised | Upheld | Minutes | Fixer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | correctness | gpt-6.1-sol, high | Codex | 12aa942 | NOT YET | 7 | 6 | 5 | opus (Agent tool, the builder) |
| 1 | fit | claude-opus-5-5, high | Claude (Agent tool; ran with this session's instruction files and hooks) | 12aa942 | NOT YET | 16 | 15 | 6 | opus (Agent tool, the builder) |
| 2 | correctness (re-check, the one Astra pass) | gpt-6-astra, high | Codex | 9a3ed5d | NOT YET | 5 | 5 | 6 | opus (Agent tool, the builder) |
| 2 | fit (re-check) | claude-opus-5-5, high | Claude (Agent tool; ran with this session's instruction files and hooks) | 9a3ed5d | CONDITIONAL | 7 | 7 | 11 | opus (Agent tool, the builder) |
| 3 | correctness (re-check after diagnosis) | gpt-6.1-sol, high | Codex | 99bb239 | NOT YET | 3 | 3 | 13 | opus (Agent tool, the builder) |
| 3 | fit (re-check) | claude-opus-5-5, high | Claude (Agent tool; ran with this session's instruction files and hooks) | 99bb239 | CONDITIONAL | 4 | 4 | 11 | opus (Agent tool, the builder) |
| 4 | correctness (re-check after the second diagnosis) | gpt-6.1-sol, high | Codex | 6e7a335 | GOOD TO GO | 0 | 0 | 6 | none |
| 4 | fit (re-check) | claude-opus-5-5, high | Claude (Agent tool; ran with this session's instruction files and hooks) | 6e7a335 | GOOD TO GO | 4 | 4 | 9 | lead (lead-made: 16 production lines plus checks) |
| 5 | correctness (re-check of the lead-made K1 to K4; the cap) | gpt-6.1-sol, high | Codex | 4abb653 | NOT YET | 2 | 2 | 4 | lead (wording-only leftovers at the cap: lead-made, lead-verified) |

| Id | Round | Reviewer | Severity | Lead verdict | Evidence | Also raised by |
|---|---|---|---|---|---|---|
| C1 | 1 | sol | blocker | UPHELD | main.js reloads the dashboard to / on every return to running; EngineBanner keeps the outage only in memory, so "Running again" never shows; the stub switches to running without a reload | F1 |
| F1 | 1 | opus | blocker | UPHELD | same trace as C1 (main.js:354 loadURL; stub.js __emit) | C1 |
| C2 | 1 | sol | blocker | UPHELD | removePausingEngine saves {ok:false, pieces:null} when remove() throws; RemovalAfterReload passes it to RemovalResult, which dereferences result.pieces! | |
| C3 | 1 | sol | should-fix | UPHELD | preload acks an opened file once the callback ran; the "Up next" queue lives in React state and the reload after a restart drops it | F15 |
| C4 | 1 | sol | should-fix | DECLINED | traced: after the command is changed, status reads Off (or another copy) truthfully; turnOn with replace keeps the older backup under a timestamped name, so nothing is lost; reaching the restore question needs a new status field in 2c-app (closed at its cap); declined.md | |
| C5 | 1 | sol | should-fix | UPHELD | state "on" with uses null (shell not asked) shows the green "ready in Terminal" card and "Terminal is ready" in the skill card and Settings | |
| C6 | 1 | sol | should-fix | UPHELD | Escape or backdrop leaves the question unasked, against "offer once" (the owner's answer); firstLaunch.mark's {ok:false, reason} is ignored | |
| C7 | 1 | sol | should-fix (PLAUSIBLE) | UPHELD | removeOldLauncher clears the note in finally; a settle before the old document is replaced loses the post-reload result; cheap to close by keeping the note until consumed | |
| F2 | 1 | opus | should-fix | UPHELD | a removal or Restart engine he started shows the crash wording "anyscribe's engine stopped. Restarting it." | |
| F3 | 1 | opus | should-fix | UPHELD | addToPath ok:true with a reason: the reason is dropped for the generic "open a new Terminal window" line | |
| F4 | 1 | opus | should-fix | UPHELD | after a refusal the card still offers to add the line to ~/.zprofile above the refusal | |
| F5 | 1 | opus | should-fix | UPHELD | state off with occupant set: Turn on refuses with "Keep it, or switch", and no Switch button exists in the card or Settings | |
| F6 | 1 | opus | should-fix | UPHELD | the refusal under "Remove the old launcher" talks about restarting the engine without saying removal restarts it | |
| F7 | 1 | opus | should-fix | UPHELD | the mockup changes only how Browse reads the file; the lead's spec added "submits", against today's fill-the-box behaviour; spec error, the lead's | |
| F8 | 1 | opus | nit | UPHELD | "its Claude Code skill is removed" shows on a Mac where it was never installed | |
| F9 | 1 | opus | nit | UPHELD | the Removed card names a login item that did not exist | |
| F10 | 1 | opus | nit | UPHELD | the keeps-stopping banner names a hidden path instead of the existing Open log folder | |
| F11 | 1 | opus | nit | UPHELD | the overlay's name-and-size branch never runs in a real drag (drag_probe.out); delete it | |
| F12 | 1 | opus | nit | UPHELD | the ready card ignores claudeCode | |
| F13 | 1 | opus | nit | UPHELD | the wizard's Terminal step is titled "All set" above "Last step · optional" | |
| F14 | 1 | opus | nit | DECLINED | the route is lost on the app's reload to / (Restart from Settings lands on Transcribe); an app-side change in 2c-app, closed at its cap; phase 3 backlog; declined.md | |
| F15 | 1 | opus | nit | UPHELD (in part) | queue loss is C3; a remove button for a queued file is declined (not in the mockup); declined.md | C3 |
| F16 | 1 | opus | nit | UPHELD | with no Switch offered, "Keep the one I have" has nothing to choose between | |
| A1 | 2 | astra | should-fix | UPHELD | traced TranscribePage startIncoming: doneIncoming runs after any answer, and the start effect allows phase error, so a second failure replaces the first; reproduced in memory by the reviewer | G1 |
| G1 | 2 | opus | should-fix | UPHELD | same family as A1: a file arriving while the engine is down fails to post, leaves the stored queue, and the reload drops the error; the stub never takes the engine offline | A1 |
| A2 | 2 | astra | should-fix | UPHELD | traced engine.js restart: a crash during the job pre-check refuses with "stopped while the restart was being checked" after a restarting status; the removal note survives and restartIsMine reads it with no expiry | G7 |
| G7 | 2 | opus | nit (PLAUSIBLE) | UPHELD | same as A2: the removal note counts as this page's restart for as long as it exists | A2 |
| A3 | 2 | astra | should-fix | UPHELD | MacCards hides result.reason when carry-over succeeded; removePausingEngine appends the failed-restart reason to an ok result; and EngineBanner renders nothing for state stopped without stoppedRestarting | G2, G3 |
| G2 | 2 | opus | should-fix | UPHELD | EngineBanner has no words for a plain stopped engine (failed manual or automatic restart); traced engine.js _onExit and _failBeforeSpawn | A3 |
| G3 | 2 | opus | should-fix | UPHELD | same trace as A3's first half | A3 |
| A4 | 2 | astra | should-fix | UPHELD | stub.js: removal does not restart or save a result by default, app state resets on reload, a failed mark persists, removeSettlesFirst resolves before running, open-file has no ids or ack; the checks do not establish real-bridge behaviour | |
| A5 | 2 | astra | nit | UPHELD | the Removed sentence always names the launcher; Settings passes post-removal pieces as before | G4 |
| G4 | 2 | opus | nit | UPHELD | same as A5's second half | A5 |
| G5 | 2 | opus | nit | UPHELD | the save-failed card does not say which question may come back | |
| G6 | 2 | opus | nit | UPHELD | the added-but-missing card keeps "Takes effect in new Terminal windows"; the by-hand reason and the box repeat the line | |
| B1 | 3 | sol | should-fix | UPHELD | App.tsx: the startup recovery's status read can return after a new Remove click wrote its note; resolveRemoval then clears that note as unmatched; reproduced in memory by the reviewer; the bridge's status handler is outside its queue | |
| B2 | 3 | sol | should-fix | UPHELD | MacCards RemovalResult: the checklist branch renders no reason; old-launcher.js returns ok:false with pieces and a reason (login guidance, failed restart) | |
| B3 | 3 | sol | should-fix | UPHELD | stub.js removeSettlesFirst resolves while the engine reads restarting; the real remove() settles only after restart() returned (ready or failed) | |
| H1 | 3 | opus | should-fix (PLAUSIBLE timing) | UPHELD | TranscribePage: the page about to be reloaded sees running and can post a waiting file before loadURL replaces it (main.js sends the status, then loads); the file runs twice or unseen | |
| H2 | 3 | opus | should-fix | UPHELD | the idle view has no Up next line; a file waiting for a stopped engine shows nothing | |
| H3 | 3 | opus | nit (PLAUSIBLE) | UPHELD | App.tsx: askTerminal is true until the second effect claims the removal, so the Terminal card can mount before the Removed card | |
| H4 | 3 | opus | nit | UPHELD | break-all splits words in the Up next lines; "It starts once you try this one again" is not what happens | |
| K1 | 4 | opus | nit | UPHELD | the bridge's partial-cleanup reason opens with "Cleanup didn't finish: <what is left>." (old-launcher.js:200), repeating the title and checklist; above the advice its extra notes take the advice's "it"; fixed lead-made: the opening sentence stripped, the rest shown below the advice | |
| K2 | 4 | opus | nit | UPHELD | checker fixtures used reasons the bridge never sends (no "Log out" in desktop/src at 70e911f); fixed lead-made: REMOVE_FAIL, REMOVED_NOT_CARRIED, both X and the login note now use old-launcher.js and engine.js wordings; stub comment corrected; the proof's "Log out" note corrected | |
| K3 | 4 | opus | nit | UPHELD | the running and error views' Up next promise their old trigger while the engine is down; fixed lead-made: both use the engine-down words | |
| K4 | 4 | opus | nit | UPHELD | "It is running again now." glued after the engine's bare reason (engine.js reasons end without a full stop); fixed lead-made: a full stop added when missing | |
| E1 | 5 | sol | should-fix | UPHELD | the error view's engine-down line promised B starts once the engine runs, but a failed dropped file at the head is tried again first and can pause B again; wording-only; fixed lead-made at the cap (afterHead), lead-verified | |
| E2 | 5 | sol | nit | UPHELD | the partial-cleanup fixture paired the approval note with startAtLoginCarriedOver true; the bridge gives that note only with false (old-launcher.js:187); fixed lead-made | |

Round 3 plan: diagnosis first (diagnosis-r3.md, claude-fable-5-2), fix plan fix-plan-r2.md, then a correctness re-check (Sol) of the delta; fit rejoins for the visible changes.
Round 4 plan: diagnosis first (diagnosis-r4.md), fix plan fix-plan-r3.md, then a correctness re-check (Sol) of the delta; fit rejoins.
Round 4 result: both roles GOOD TO GO; the fit nits K1 to K4 fixed lead-made (proof.md "Lead-made after round 4"). Round 5 (the cap): a correctness re-check of that lead-made delta only. Sol's B2 wording advice ("Try again. Use Copy details to share what is still there.") not taken: the fit answer keeps the mockup's advice verbatim, which the approved design binds.
Closed (2026-11-21): GOOD TO GO. Rounds 4 (both roles) cleared the design; round 5 (the cap) raised E1 and E2, wording-only leftovers, fixed lead-made and lead-verified (proof.md "Lead-made after round 5": 250 passed, 5 of 5 mutants killed). Not re-reviewed after that fix, by the cap rule. Residue for a Mac: real Electron reload timing and sessionStorage across loadURL, the native picker, Finder and Dock drops, traffic lights against the drag strip.
