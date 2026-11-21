# Fix plan, round 3 (the lead's choices after diagnosis-r4.md; binding where it decides)

Round 2's design holds. Both reviewers mark every round 2 id fixed, and the round 3 findings are two gaps in it, plus direct fixes. The scope is unchanged: 2c-ui only, and 2c-app at 70e911f is not changed. If the plan is wrong anywhere, say so instead of building it.

## Two rules

1. **A doomed page starts nothing new (H1, B1).** main.js reloads the dashboard on every return to running. So a page that has seen the engine leave running will be replaced, and it is "doomed".
   - The flag lives in desktop.ts, at module scope. It is set by the first engine status read and by any status event that is not running. It never resets.
   - It has exactly two readers. The queue start gate needs the engine running and the page not doomed. The startup recovery claim does nothing on a doomed page.
   - Everything else on a doomed page works as now, including his clicks (Restart engine, Remove, Try again) and EngineBanner's outage record.
   - The first page after launch is not doomed, because main.js loads it only from a running engine.

2. **An async callback acts only on the state it started from (B1, H3).**
   - The note is read once, at module scope in desktop.ts, when the page loads. Startup recovery resolves only that note: the same `at`, checked again just before it clears or claims anything. With no note at load, there is no recovery.
   - The live page's own refusal clear is tied to the `at` of the note it wrote.
   - Drop the literal `true` arguments in `resolveRemoval` (pass the real state).
   - The Terminal card (`askTerminal`) waits until the startup recovery has finished, or starts at once when there was no note. On a doomed page it stays held.

## Direct fixes

- **B2.** The checklist branch of RemovalResult shows `result.reason` (the bridge's exact words), above the generic advice.
- **B3.** Delete `removeSettlesFirst`. The stub's default removal already emits running, then settles. Add `reloadDelay` (for example 300 ms) between the running status and the reload, so the old page can act before it is replaced. Record the engine state at the moment `remove()` settles, so a check can assert it.
- **H2.** While files wait and the engine is not running (or the page is doomed), the idle, completed and cancelled views show "Up next: b.m4a. It starts once anyscribe's engine is running again." The plural is "They start in turn once anyscribe's engine is running again."
- **H4.** Use `break-words` (not `break-all`) on every Up next line. Under the error: "Up next: b.m4a. It waits until you try this one again or choose New." The plural is "They wait until you try this one again or choose New."

## Checks (identity; mutation-test each)

| Pins | Setup | Asserts | Mutant |
|---|---|---|---|
| H1 | Engine down, B opened, `reloadDelay` 300 | Exactly one POST, body B, sent by the reloaded page (tag requests with the stub's reload count); Stop shows there | Drop the flag |
| H1, first read | The page loads with the stub at restarting | Same | The flag set from events only |
| B1 | No note at load, a slow second `oldLauncher.status` (a per-call delay in the stub), then Remove | The reloaded card shows reason X | Drop the no-note skip |
| B1, note at load | A note at load, then Remove from Settings while the recovery read is pending | The stored note's `at` is the click's; the reloaded card shows X | Drop the `at` match |
| Doomed recovery | Restarting arrives before the recovery read returns | No card on the old page, the note unchanged, the reloaded card shows X | Drop the flag check |
| H3 | Both questions unasked, Remove, reload | `terminal.status` calls are `[]` until OK, then exactly one | Drop the hold |
| B2 | Partial cleanup with reason X | The card contains X and the checklist | Drop the line |
| B3 | Normal removal | The engine state recorded when `remove()` settled is "running" | Settle before the emit |
| H2 | Engine stopped; a drop in the idle and the completed views | The exact line naming b.m4a; zero POSTs | Drop each line |

## Documented limits (journal; not built)

- A crash during a queued file's POST can run that file twice.
- A click on a doomed page in the instant before its reload.
- A removal result is lost if anyscribe quits before a page claims it (`lastRemoval` is in the app's memory only).
- A second Remove overwrites an unclaimed note.
- Real Electron timing stays a check on a Mac.

## proof.md
Append "## Round 3 fixes (one entry per finding)": one line per UPHELD round 3 id (B1, B2, B3, H1, H2, H3, H4): change | ran | saw. Mutation results for every check above. Then:
- the full checker run with screenshots (read the changed states yourself);
- ui lint and build;
- the rebuilt bundle committed;
- the browser run pixel-identical.

Commit after each finding.
