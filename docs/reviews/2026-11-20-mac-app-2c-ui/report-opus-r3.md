## Fit review, round 3: Mac app 2c-ui (delta 9a3ed5d..99bb239; checks to f1aae31)

### 1. Verdict
**CONDITIONAL on H1 and H2.** There is no blocker.
- Every round 2 id is fixed. The approved screens and words hold, and the round 2 states read correctly at 1440 and 390 px.
- The browser dashboard is unaffected: every new path is gated on `desktop`, and `doneIncoming` is a no-op on an empty queue. The proof reports the browser run pixel-identical.
- Two should-fix items remain, both in what the new queue gate opens:
  - **H1:** the page that the app is about to reload can start a waiting file, so it runs twice or runs unseen.
  - **H2:** a file that waits for a stopped engine waits with nothing on screen.
- Both are small and sit in `TranscribePage.tsx` (plus one flag in `desktop.ts`).

### 2. Round 2 ids
- **A1 FIXED.** A file leaves the queue only when its submission returns ok. The error screen pauses the queue, and New drops only a failed head. The POST bodies are asserted. The wording and wrapping of the new line are H4.
- **A2 FIXED.** "Mine" is now the `ownCalls` counter. `resolveRemoval` runs only while the engine reads running and clears an unmatched note. Checked against engine.js `restart()` and old-launcher.js `removePausingEngine`.
- **A3 FIXED.** The reason is always shown (screenshot `r2-removed-engine-stopped`), and the stopped state has its red card.
- **A4 FIXED** for all six listed items.
  - One stub gap remains: the reload comes 30 ms after "running" and the routes answer instantly, so the old page can finish a whole POST before the reload. That gap hides H1.
- **A5 FIXED.** Screenshot `r2-settings-icon-only`: "Stopped the old menu bar icon. The launcher and login item were already gone."
- **G1 FIXED.** The lost-file scenario is closed. The gate opens H1 and H2.
- **G2 FIXED.** Heading, body, buttons, refusal line and Copy details line all match the plan.
- **G3 FIXED.**
- **G4 FIXED.** `r.shown` carries the pieces read before the call.
- **G5 FIXED.** Screenshot `first-mark-failed`: "The old launcher question may come back the next time anyscribe starts."
- **G6 FIXED.** Screenshots `first-terminal-added-reason` (no "Takes effect" note) and `first-terminal-bash-refused` ("…add this line to it by hand:", then the box). Matches terminal.js:397/405, which end the reason with the line.
- **G7 FIXED.**

### New findings

**H1. should-fix. PLAUSIBLE (timing).** A file waiting while the engine is down is started by the page the app is about to throw away. It then runs twice, or runs with nothing on screen.
- **Where:** `ui/src/pages/TranscribePage.tsx:115-129` (`engineUp` and the start effect), against 2c-app `main.js:347` (status sent to the page) and `:354` (`loadURL` right after).
- **Scenario:**
  1. The engine is restarting or stopped, and he drops or Dock-opens b.m4a. It waits, which is correct.
  2. The engine comes back. The old page gets "running", so `engineUp` turns true and the effect posts B. Meanwhile `loadURL('/')` is already loading the new page.
  3. **(a)** The POST reaches the engine but its answer arrives after the new page has replaced the old one. `doneIncoming` never runs, B stays in the stored queue, and the reloaded page posts B again. That is two jobs: two charges on a paid provider and two History entries.
  4. **(b)** The old page completes the whole cycle first. The queue empties, and the reloaded page is an idle Transcribe screen while B transcribes unseen.
  5. Only when the old page is slower than the reload is the result right.
- **Why the checks pass:** "G1: after the reload, exactly one post" counts requests across both pages. Case (b) passes it, and (b) is likely in the stub, which waits 30 ms and answers instantly.
- **Fix:** every return to running reloads the page, so a page that has seen the engine leave running must never start a waiting file. The reloaded page does it.
  - `desktop.ts`: a module flag, `let leftRunning = false; desktop?.onEngineStatus((s) => { if (s.state !== "running") leftRunning = true; });` and export a reader.
  - TranscribePage: `const engineUp = !desktop || (engine?.state === "running" && !engineLeftRunning());`
  - Check: the G1 case with `reloadDelay: 300`. After the reload, assert `posts == [B_]` and that B's progress (the Stop button) is on the reloaded page. Mutant: drop the flag.

**H2. should-fix. CONFIRMED by reading.** A file dropped or opened while the engine is stopped waits with nothing on screen.
- **Where:** TranscribePage's idle view. The "Up next" lines are only in the running view (`:313`) and the error view (`:422`). The gate holds the file while the engine is not running.
- **Scenario:**
  1. The red "anyscribe's engine stopped" card is up, and he drops b.m4a on the window.
  2. The overlay goes and Transcribe looks unchanged.
  3. He drops it again, and the queue is [b, b].
  4. After Restart engine, both copies run in turn: one file transcribed twice. The same silence covers the few seconds of any restart.
- **Fix:** in the idle view, when files wait and the engine is not running (or H1's flag is set):
  - "Up next: b.m4a. It starts once anyscribe's engine is running again."
  - Plural: "They start in turn once anyscribe's engine is running again."

**H3. nit. PLAUSIBLE.** After a removal from the first-launch question, the "One more option" Terminal card can flash before the "Old launcher removed" card.
- **Where:** `App.tsx:49-76`. Round 2 claimed the removal in the same `Promise.all` that sets `asked`. Round 3 claims it in a second effect that starts one engine-status read later. In between, `askTerminal` is true, because `removed` is still null.
- **Scenario:** an existing user with both questions unasked presses Remove, and the page reloads.
  1. `asked` lands first, so TerminalFlow mounts and calls `terminal.status()`, a login-shell query.
  2. Then `removed` lands and the Terminal card unmounts.
  3. After OK it mounts again, and its status call queues behind the first.
- **Why the checks miss it:** no check walks this order. Every removal check uses `terminalAsked: True`.
- **What would settle it:** in `first_launch`, use `firstLaunch={"oldLauncherAsked": False, "terminalAsked": False}`, press Remove, call `after_reload`, then assert `r.calls(p, "terminal.status") == []` before OK.
- **Fix:** hold the Terminal card until the removal check has finished, e.g. `const [removalChecked, setRemovalChecked] = useState(false)`, set true in that effect's `.then` and `.catch`, and add `&& removalChecked` to `askTerminal`.

**H4. nit. CONFIRMED** (screenshot `r2-queue-refused-head@390`). The new "Up next" line under the error.
- **(a) Wrapping:** `break-all` splits ordinary words: "or cho / ose New." The running view's line (`:314`) has the same class.
  - Fix: use `break-words` on both lines.
- **(b) Wording:** "It starts once you try this one again" is not what happens. After Try again, B waits until A finishes.
  - Words: "Up next: b.m4a. It waits until you try this one again or choose New."
  - Plural: "They wait until you try this one again or choose New."

### 3. The builder's three gap fills (advice)
1. **The live page, engine not running, shows what `remove()` returned; the note waits for the running engine. Agree.** It matches old-launcher.js: `lastRemoval` is saved before the relaunch, and the reason is appended when the relaunch fails.
   - Side effect: a card closed with Escape (LauncherQuestion's `onClose` is `launcherKept`, which keeps the note) comes back after the next reload. So does Settings' inline card, which has no OK. It comes back once, with "It is running again now." Acceptable, because it carries news. The A3 check relies on it.
2. **The New check refuses B too. Agree.** Starting B right after New is the designed behaviour, and the POST bodies (L, then B) prove it.
3. **Up next under the error. Agree** with showing it; change the words and wrapping as in H4.

### 4. Pending owner checks
**Deliberate departures still for him to accept** (carried from round 2):
- The drop overlay has no file name or size.
- Copy details carries no log; there is an Open log folder link instead.
- The wizard's Terminal step is titled "One last thing".
- Escape counts as the quiet answer.

**New words this round:**
- The stopped red card.
- "It is running again now."
- The icon-only sentence.
- The three "may come back" sentences.
- The Up next line under the error, after H4.

**On his Mac, with 2c-app and 2c-ui built together:**
- The first launch with both questions unasked: Remove, "Restarting anyscribe's engine.", the reload, "Old launcher removed" (watch for H3's flash), OK, then "One more option".
- Kill the engine during a job: the crash words, the reload, then "Running again" naming the job.
- With the red card up, drop a file, then press Restart engine. It must run once, with its progress on screen (H1, H2).
- The traffic lights against the 28 px strip, the native picker, and a Dock drop.

None of H1 to H4 is his to fix; they are the builder's.

### 5. Could not check; commands; inspected
**Could not check** (nothing was run, by rule):
- Which way H1's race goes in real Electron: an in-flight fetch against `loadURL`'s commit.
- How long H3's flash lasts.

**Commands for the lead, after adding the H1 and H3 assertions above:**
- `/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py --no-shots --only r2_facts,first_launch,removal_reload`
- Then `/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/mutate.py` with a mutant that drops H1's flag.

**Inspected:**
- The brief.
- The packet: ask, spec, bridge-v2 with its Amendments and Amendment 2, target, lens.
- proof.md in full, including "Round 2 fixes".
- Both declined.md files.
- From findings.md, the round 2 reports, then review-log, diagnosis-r3 and fix-plan-r2.
- The full delta-r3.patch, and the stub.js diff 9a3ed5d..f1aae31.
- The head versions of `App.tsx`, `desktop.ts`, `EngineBanner.tsx`, `MacCards.tsx` (RemovalResult, TerminalFlow's effect), the `Layout.tsx` queue, the `TranscribePage.tsx` queue and views, and `useJob` `submit`.
- The r2_facts, first_launch and removal_reload checks in `check_ui.py`, and the request recording.
- 2c-app at 70e911f:
  - main.js in full.
  - engine.js in full.
  - old-launcher.js: `status`, `remove`, `removePausingEngine`.
  - preload.js.
  - terminal.js: the addToPath reasons.
  - logic.js: the menu model.
- The mockup text for sections 3, 4, 5, 9, 10 and "For the build".
- Screenshots at 1440 and 390: `r2-queue-refused-head`, `r2-removed-engine-stopped`, `r2-settings-icon-only`, `first-mark-failed`, `first-terminal-added-reason`, `first-terminal-bash-refused`, `first-launcher-removed`, `first-launcher-failed`, `settings-launcher-removed`, plus `banner-keeps-stopping@390` for the shared red-card layout.

**Skipped:**
- The 1000 px shots.
- The pixel pairs.
- `desktop/README.md` (the code was read instead).
- The mutation logs beyond the proof's table.
