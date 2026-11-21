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
