# Diagnosis before round 4 (claude-fable-5-2, Agent tool; verbatim hand-back)

Round 4 diagnosis, 2c-ui at 99bb239 against the bridge at 70e911f. Read only; nothing was run.

**1. Is it right?** Yes, and it closes round 3 as a class, with three conditions.

- **Set the flag from the first status read too, not only from events.** A crash before the page subscribes is missed, and the later "running" event reopens H1. The flag never resets, so a late read is safe.
- **"When it begins" must be page load.** Read the note once at module scope in `desktop.ts`. The App effect starts only after an awaited engine read. A Remove click before that would be captured as the predecessor's note and cleared (B1 again).
- **The recovery callback checks the flag as well as `at`.** Today a page that claims and is then reloaded loses the card. This replaces Sol's "revalidate engine state". Add no extra read.

The four cases hold:
- **Restart click on a doomed page:** works. Clicks are not gated.
- **Engine never returns:** files wait, and H2's line says so.
- **The removal's live page:** it only displays, and the note stays for the reloaded page. Tie its refusal clear to its own `at`.
- **First page after launch:** main.js loads the dashboard only from a running engine, so it is not doomed.

Two limits on scope:
- The flag has two readers only: the queue start and the recovery claim. EngineBanner's outage record must keep working on a doomed page.
- Leave the Terminal card held on a doomed page.

H2 also needs the line in the completed and cancelled views. A file dropped there waits unseen too.

**2. More than needed.** Delete `removeSettlesFirst`. The stub's default path already emits running, then settles. Use `reloadDelay: 300` instead. Drop the literal `true` in `resolveRemoval`. No drop dedupe.

**3. Checks.**

| Pins | Setup | Asserts | Mutant |
|---|---|---|---|
| H1 | Engine down, B opened, `reloadDelay: 300` | One POST, body B, sent by the reloaded page (tag posts with `__stub_reloads`); Stop shows there | Drop the flag |
| H1, first read | Page loads with the stub at restarting | Same | Flag from events only |
| B1 | No note, slow second `oldLauncher.status` (new per-call delay), Remove | `oldLauncher.status` called once before the click; reloaded card shows reason X | Drop the no-note skip |
| B1, note at load | Remove from Settings while the read is pending | Stored note's `at` is the click's; card shows X | Drop the `at` match |
| Doomed recovery | Restarting arrives before the read returns | No card on the old page, note unchanged, reloaded card shows X | Drop the flag check |
| H3 | Both questions unasked, Remove, reload | `terminal.status` calls are `[]` until OK, then one | Drop the hold |
| B2 | Partial cleanup, reason X | Card contains X and the checklist | Drop the line |
| B3 | Stub records engine state when `remove()` settles | Equals "running" | Settle before the emit |
| H2 | Engine stopped, drop in idle and completed views | Exact line naming b.m4a; zero POSTs | Drop each line |

**4. Decline as limits.**
- A crash during a queued file's POST can run it twice.
- A click on a doomed page in the instant before the reload.
- A removal result is lost if anyscribe quits before a page claims it; `lastRemoval` is memory only.
- A second Remove overwrites an unclaimed note.
- Real Electron timing stays a check on his Mac.

Not checked: EngineBanner, the MacCards body, check_ui.py beyond a grep.

Files: `~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/desktop.ts`, `App.tsx` and `pages/TranscribePage.tsx` under the same `ui/src`, and `~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/stub.js`.
