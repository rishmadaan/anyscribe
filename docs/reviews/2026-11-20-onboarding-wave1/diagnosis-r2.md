# Diagnosis, round 2 (Claude Fable 5.2, high effort, Agent tool, read-only)

Brief: `~/.review-runs/2026-11-20-onboarding-wave1/brief-diagnosis-r2.md`. The report, verbatim:

~~~~
DIAGNOSIS, W6 download lock (C1, R2C1 to R2C3). Read at 4def0e4 on feat/onboarding-wave1, clean tree. Source trace only: nothing run, nothing written.

**Recommendation in one line:** stop making the lock hard. Let the customer close during a download after one plain confirmation, and give the "is a setup running" belief one owner (the local step). This changes W6's first bullet, so it needs the owner's yes before the fixer starts.

## 1. Why the fixes keep failing

Two causes, one in the requirement and one in the code.

- **The requirement cannot be met as written.** A hard lock is released only by "the server says the setup stopped". The page learns that through status reads that can fail, hang or arrive late, and the server has no cancel. When the page cannot tell, the code must pick a side:
  - Treat "can't tell" as stopped: the lock opens during a live download (C1, R2C1).
  - Treat it as running: the customer is held with no way out (R2C2, R2C3).
  - Round 1's fix plan ("nothing can unlock the wizard while a setup runs") pushed to the second side, so round 2 found the stuck cases plus one leftover unlock. A round 3 patch of the same shape will move the defect again.
- **The belief has two copies and about nine writers.** `localRunning` (wizard) and `settingUp` (step) are kept in step by hand:
  - Wizard: mount read (`OnboardingWizard.tsx:131-145`) and its own poll (`:149-159`).
  - Step: mount read (`:662-673`), a one-way push that only sends true (`:675-677`), the poll (`:693-696`), and `handleStartSetup` (`:722`, `:742-744`).
  - Each writer handles only the outcomes its author walked. `settingUp` also means four things at once: I asked, the server confirmed, keep polling, lock the controls.
  - The hand-off rule "the wizard does not poll on the local step" (`:150`) leaves the step as sole owner there, and its mount read ignores the "not running" answer. That is R2C2.

## 2. What the checks and walks miss

- **No automated UI test exists.** `ui/package.json` has no test script. The lock was proven by walks plus a tab harness.
- **The harness cannot fail, hang or reorder a request.** `harness.js` and `c1-scenario.js` only rewrite fields of a successful status answer. So only two points were exercised: steady running and normal completion.
- **The mutation tests removed only the guards that were just added**, on the reported path (untick, Skip, Escape). They show those guards matter there and nothing about other paths.
- **The walk machine showed the hazard and it was read as noise.** Status took about 1 s and clicks timed out; the response was to drop a poller, not to bound requests.

States and orderings never exercised:

| # | Ordering | What happens today |
|---|---|---|
| 1 | Start accepted, next status read fails | Unlocks, shows raw error text (R2C1) |
| 2 | Start answers 409, follow-up read fails | Raw `409: {"detail":...}` on screen, unlocks (`:733-744`) |
| 3 | Start answers 409, follow-up read says "not running" (setup ended in between) | Same raw 409. Not in the reports |
| 4 | Wizard read says running, step read says stopped | Stale lock (R2C2) |
| 5 | Wizard read says running, step read fails | "Loading models…" forever, locked, no message; `:663` has no catch. Back is the only exit. Not in the reports |
| 6 | Every poll fails, or one hangs | Silent and locked (R2C3). No time limit in `client.ts:25-35`; `setInterval` lets ticks overlap |
| 7 | Status fine and says stopped, log read fails | Result thrown away by `Promise.all` (`:684`) |
| 8 | Two ticks in flight when setup stops, or a tick lands after the step unmounted | `onNext()` can fire twice and pull the customer back to Workspace. Plausible by trace |
| 9 | A status read sent before Download was accepted lands after it | `settingUp` is set before the POST (`:722`), so a "not running" answer reads as "finished" and shows the previous run's error. Plausible by trace, low odds |
| 10 | Server restarted mid-download | Setup state is in memory (`routes/local.py:46-60`), so status returns "not running, no error" |

The spec and fix plan never said what the customer sees when status is unknown, or what their exit is. Only the round 2 fit advice raised it.

## 3. Candidate designs

**A. One owner, hard lock kept.** A wizard-level hook with idle / running / stopped / unknown, one poll, lock while running or unknown.
- Guarantees: no disagreement between wizard and step; R2C1 and R2C2 gone; R2C3 becomes a visible state.
- Does not guarantee: an exit while a download really runs (the fit reviewer's 27 minutes for Turbo at 1 MB/s). "Unknown" still needs an exit, and that exit is design B's confirmation by another name.
- Cost: about 150 lines net, about 250 touched (new hook, both components rewired, an unknown screen).
- Risk: a third rewrite in the last allowed round, and any future mismatch is again a broken invariant.

**B. Soft lock, one watcher in the step (recommended).** Closing is always possible; while a setup is watched, closing asks first.
- Guarantees: never stuck, because Skip is always visible and Close always works. A wrong belief costs at most one extra or one missing confirmation.
- Does not guarantee: a customer who clicks "Close anyway" keeps their choices. That is now an informed click, not an accident.
- Cost: about 40 lines net, about 150 touched. It deletes the wizard poll and all but one `onRunning` call.
- Risk: it reverses W6's first bullet. A customer who closes is left with the default provider (`settings.py:39`, openai, no key) until they rerun the wizard, because setup never changes the provider (`local_setup.py:380`).

**C. Take the download out of the wizard.** Start it, let the customer go on to Finish, show "still downloading" on All set and the Transcribe page.
- Guarantees: nobody waits in a dialog at all.
- Cost: wave 2 sized. Finish would have to save a model that is not yet runnable, and `/api/onboarding/save` runs local setup synchronously.
- Not for this round. It fits wave 2's "download MB count, time and stall warning".

Rejected:
- **A cancel endpoint.** Server work on a thread running pip and a model download, and useless when the server is unreachable. A cooperative cancel exists for jobs only.
- **Saving choices early.** Breaks the keep-list's "config written once at Finish" and would put a key in browser storage.

Against standard primitives, the current repair is a hand-synchronised pair of flags. The pieces already exist:
- `LocalSetupModal.tsx:121` derives running from the last status instead of holding a second flag.
- `AbortSignal.timeout` bounds a request, and `fetchJSON` already passes `init` through.
- Separate awaits decouple the log from the status.
- `beforeunload` is the platform's guard for reload. I would not build it this round; log it for wave 2, since reload already drops a cloud choice.

## 4. What the fixer should build (design B)

Why B: it is the only candidate where a wrong belief is harmless, which is what "cannot fail this way" needs. It also answers the fit reviewer's "no exit" and the owner's third invariant directly.

Rules a reviewer can check:

1. `disableClose` is `saving` only. No download ever switches closing off.
2. "Skip for now" is visible on every step, including during a download.
3. While the step is watching, Escape, a backdrop click and Skip open one confirmation inside the wizard. Suggested words for the lead to fix as a string: "Close setup? The download carries on in the background. Your choices on these screens are saved only when you click Finish. To come back: Settings, then Run setup wizard."
4. The confirmation has two buttons. "Keep setting up" hides it. "Close anyway" closes without setting `scribe_onboarding_dismissed`.
5. When not watching, Escape and backdrop close at once, as on every other step.
6. One owner. `onRunning` is called from exactly one effect in the step (`onRunning(watching)`, cleanup false). The wizard's poll (`:149-159`) and the `setLocalRunning(true)` at `:135` are deleted. The wizard's mount read only routes to the local step.
7. Watching starts when a good status read says `setup_running: true` (adopt `setup_last_model`, turn local on), or when the start request was answered 2xx or 409, or got no answer at all.
8. Watching does not start only when the server answered the start with a refusal other than 409. That shows a plain sentence.
9. Watching ends only on a good status read, sent after the start request settled, that says `setup_running: false`. A failed, timed-out or earlier-sent read never ends it. No other line sets it false.
10. That ending read runs the existing completion branch exactly once. A later tick, or one landing after unmount, is dropped.
11. Status is read on its own. A failed log read changes only the log panel.
12. Every status read has a time limit (about 10 s; the fixer tunes it). The next read is scheduled only after the previous one settles.
13. The step keeps reading until it has a first status. No endless "Loading models…".
14. After two failed reads in a row, a plain notice shows and reads continue. Suggested: "Can't reach anyscribe right now. If you quit it, open it again; this page picks the download back up." It clears on the next good read. While it shows, the progress line does not claim a live percent.
15. No raw server text from this step reaches the screen: no "409: {…}", no "Failed to fetch".
16. Kept from round 1: checkbox, Back, picker and start button disabled while watching; C2's adoption and runnable check.
17. Fold in R2F2 and R2F3, since the same lines move: progress block above the picker, and one "off until setup finishes" line instead of three.

Places the change must reach:
- `OnboardingWizard.tsx` and `client.ts`, plus the rebuilt static bundle.
- Spec W6 bullet 1 and the fixed strings.
- `CHANGELOG.md:57-59`, `BACKLOG.md:669`, the journal entry (INSTALL-owned records).
- A backlog line: `LocalSetupModal.tsx` has the same shape (`disableClose={running}`, `Promise.all`, swallowed errors) and predates this diff.

Test cases. The harness first needs a scripted queue of outcomes per endpoint: ok, override, fail, hang, delay.

| Case | Sequence | Expect | Catches |
|---|---|---|---|
| T1 | Start 200, next status fails once, then running | Still watching, controls off, no error text, Escape gives the confirmation | R2C1 |
| T2 | Start 409, next status fails | Watching, no "409" on screen | R2C1 |
| T3 | Start 409, next status says not running and the model is runnable | Advances, no "409" | new |
| T4 | Start gets no answer, then status says running; variant: not running | Adopts and watches; variant: plain "couldn't start", button back | new |
| T5 | Wizard read running, step read not running | Not watching, Escape closes at once, no stale header | R2C2 |
| T6 | Wizard read running, step read fails three times, then running | Notice after the second failure, Skip visible, then adopts | new |
| T7 | Watching, then all status reads fail for 30 s | Notice, Escape then "Close anyway" closes; when reads return, notice clears | R2C3 |
| T8 | Status says stopped and runnable, log read fails | Advances | R2C3 |
| T9 | One status read hangs | Aborted at the limit, counted as a failure, never more than one status request in flight | R2C3 |
| T10 | Two ticks around the stop; customer clicks Next on Workspace | Stays on All set | new |
| T11 | A read sent before Download lands after it, carrying an old `setup_error` | Ignored, still watching | new |
| T12 | Server restarted mid-download | "Try again" sentence, never "ready" | new |
| T13 | Escape while watching, "Keep setting up", Escape, "Close anyway", then Settings, Run setup wizard | Panel, gone, panel, closed with the flag unset, reopens on the progress | new |

Mutations to watch fail:
- Rule 9: put the status read back inside the start's try. T1 must fail.
- Rule 11: put `Promise.all` back. T8 must fail.
- Rule 12: remove the time limit. T9 must fail.
- Rule 6: `git grep` shows exactly one `onRunning(` call site.

Each test asserts what is on screen and which requests were sent, not a count of open dialogs.

If the owner wants the hard lock kept, build A with rules 6 to 15 plus an exit inside the unknown state, and accept that a slow real download has no exit until wave 2.

## 5. What I could not establish

- **The owner's choice.** "Lock the wizard during download" is his list item, and B changes it. One PM-level question: "During the download, should closing be impossible, or allowed after a plain warning?"
- **Whether the wizard reopens after "Close anyway" once the download has finished.** `completed` needs the workspace folder to exist (`onboarding.py:65-73`). The server does not create it at startup; I did not check whether the installers do.
- **Orderings 8 and 9.** Plausible by trace only. They depend on how the server orders requests under load; `local_status` runs the blocking `check_status` on the event loop (`routes/local.py:72-74`).
- **How a quit server looks to the page on real Windows and Mac** (refused at once, or a hang), and what time limit suits a slow laptop during pip install. The only measurement is the fixer's 1 s per read at load 41.
- **The browser floor for `AbortSignal.timeout`.** From memory it is Chrome 103, Firefox 100, Safari 16. The repo states no supported-browser list (tsconfig targets ES2023).

Skipped: I did not read the screenshots, the raw run logs, `proof-app.md`, `proof-install.md`, or `LocalModelPicker.tsx`.
Risk: round 3 is the cap, so the re-check sees a changed mechanism with no round left; B is the choice whose leftover mistakes are cosmetic.
~~~~
