# Fix plan, round 2 findings, built in round 3 (lead's choices; binding)

Read diagnosis-r2.md first. The lead chose the diagnosis's design A in its smallest safe form ("hard lock kept, one owner, an exit inside the unknown state"), not design B, because the owner approved a lock and B removes it. spec.md W6 carries the amendment.

## The lock (R2C1, R2C2, R2C3, and the diagnosis's orderings 1 to 12)

Build exactly these rules; each is something a reviewer can check:

1. **One owner.** The local step owns a single `watching` state and an `unreachable` state. `onRunning` is called from exactly one effect in the step (`onRunning(watching && !unreachable)` style, cleanup false). Delete the wizard-level poll and every other writer of the lock. The wizard's mount read only routes to the local step (and preselects local) when a setup is running; it does not set the lock itself.
2. **Locked only when confirmed.** `disableClose` and the hidden "Skip for now" apply only while `watching` and the last status read succeeded. While `unreachable`, Escape, a backdrop click and "Skip for now" (visible again) open one confirmation inside the wizard.
3. **The confirmation** has the text S11 and two buttons, "Keep waiting" (hides it) and "Close setup" (closes without setting `scribe_onboarding_dismissed`).
4. **Watching starts** when a good status read says `setup_running: true` (adopt `setup_last_model`, turn local on), or when the start request was answered 2xx or 409, or got no answer at all (network error or timeout).
5. **Watching does not start** only when the server answered the start with a refusal other than 409; show a plain sentence, never the raw body.
6. **Watching ends** only on a good status read, sent after the start request settled, that says `setup_running: false`. A failed, timed-out or earlier-sent read never ends it. No other line sets it false.
7. **Exactly once.** That ending read runs the completion branch (round 1's runnable check, missingPart, ffmpeg notice) exactly once; a later tick, or one landing after unmount, is dropped.
8. **Status alone.** The status read is separate from the log read; a failed log read changes only the log panel.
9. **Bounded and sequential.** Every status read has a time limit (start at 10 s; use `AbortController` with `setTimeout`, not `AbortSignal.timeout`, so no browser-floor question). The next read is scheduled only after the previous one settles (no overlapping `setInterval` ticks).
10. **First status.** The step keeps reading until it has a first status; no endless "Loading models…". If the first reads fail, the S12 notice shows.
11. **Unreachable notice.** After two failed reads in a row, S12 shows and reads continue; it clears on the next good read. While it shows, the progress line does not claim a live percent.
12. **No raw text** from this step reaches the screen: no "409: {…}", no "Failed to fetch".
13. **Kept from round 1:** checkbox, Back, picker and start button disabled while watching; C2's adoption and runnable check; C3's key-check rules.
14. **R2F2 and R2F3 folded in:** the progress block sits above the model picker while watching; one line, S13, replaces the three "until the download finishes" lines.

## The other round 2 findings

- **R2F1** (Windows): on Windows, S4's body and the installer's Windows S5 box say the working step directly. S4 (Windows): "anyscribe needs ffmpeg, a free audio tool, to read audio and video. Install it with the command below. Then quit anyscribe from the tray (the icon near the clock) and open it again from the Start menu: Check again can't see a new install before that." Windows S5 (desktop route): "...Install it with: winget install Gyan.FFmpeg, then quit anyscribe from the tray (the icon near the clock) and open it again." Mac and Linux keep "then click Check again".
- **R2F4** (restart case): show only the existing RestartBanner in the restart case, with no red missingPart alert; if a sentence is still needed, it ends "then open the setup wizard again (Settings, then Run setup wizard); the download is kept."

## Fixed strings for this round

- **S11** (confirmation): "Close setup? If the download is still running it carries on in the background. Your choices on these screens are saved only when you click Finish. To come back: Settings, then Run setup wizard."
- **S12** (unreachable notice): "Can't reach anyscribe right now. If you quit it, open it again; this page picks the download back up."
- **S13** (the one lock line, in the header while locked): "Skip, Back and the local checkbox are off until setup finishes."

## Tests and proof

- Build a small scripted harness for the tab (outside the repo, under `~/.review-runs/2026-11-20-onboarding-wave1/`): a queue of outcomes per endpoint (ok, override fields, fail, hang, delay). Run the diagnosis's T1 to T13, adapted to this design: T1 and T2 stay watching and locked while reads succeed; T6, T7: notice after the second failure, Skip visible, Escape opens S11, "Close setup" closes with the flag unset, "Keep waiting" keeps it; T13: Escape while reachable does nothing; while unreachable it opens S11. Each case asserts what is on screen and which requests were sent.
- Mutations, each seen failing then passing: rule 6 (status read back inside the start's try: T1 fails), rule 8 (`Promise.all` back: T8 fails), rule 9 (no time limit: T9 fails), rule 1 (`git grep -n "onRunning("` shows exactly one call site; a second writer reintroduced fails T5).
- One real walk without downloading anything new: the dashboard from this worktree with the local model step, then stop the server mid-"watch" (start a fake running state via the harness, or a real setup only if disk allows; do not download if free disk is under 2 GB) and confirm S12 then S11 appear; restart the server and confirm the notice clears.
- Update the records the change reaches: CHANGELOG's W6 wording, BACKLOG (W6 line; new wave 2 lines: "a way out of a slow download: confirm-to-close or continue in the background, the owner's call", "LocalSetupModal has the same lock shape: disableClose={running}, Promise.all, swallowed errors", "beforeunload guard on reload"), the journal entry, and docs/user/troubleshooting.md for S12 and the Windows ffmpeg wording; regenerate landing/docs.
