FIT REVIEW, onboarding wave 1, round 3 (final). Target: feat/onboarding-wave1 at c07a65c, checked with `git rev-parse HEAD`. The change is 7ab1539..c07a65c. I read the round 3 part, ae8f460..c07a65c, line by line.

1. VERDICT: CONDITIONAL on three things.
(a) F3-1 below is fixed. It is wording only (the S12 notice, one troubleshooting paragraph and one CHANGELOG clause), so the lead can do it at the cap and prove it by diff.
(b) CI is green on c07a65c. I could not run it; the command is in section 5.
(c) The owner decides when the PyPI release happens. This is round 1's F1, still open by design.

No blocker. Nothing on the must-never list is broken by round 3:
- No screen says ready.
- The lock has one writer, and the committed bundle index-2r9Aqod2.js carries the new lock line.
- tailnet.py, app.py, the version files, .github and release.sh have an empty diff against main.

It is still the job he asked for. Round 3 stayed inside W6, plus the four fit nits, plus the records. The one new behaviour is a way to close the wizard when anyscribe can't be reached, behind one confirmation. That is the lead's spec amendment, not something the owner approved, so it is listed under owner checks.

2. FINDINGS (new in round 3)

F3-1. should-fix. CONFIRMED (the builder's own real walk and its screenshot, plus code).
Where:
- ui/src/components/OnboardingWizard.tsx:866, S12: "If you quit it, open it again; this page picks the download back up."
- docs/user/troubleshooting.md:572-574: "...as soon as anyscribe answers the message goes away and the progress comes back."
- CHANGELOG.md:61: "...can be closed after one question; the download carries on."

What goes wrong: the download runs inside the anyscribe process. Setup state lives in memory in the app (web/routes/local.py:46-58), and the thread is started at :144. So quitting anyscribe kills the download. A customer who does exactly what S12 says (quit, then reopen) does not get the download back. The restarted server says "not running, no error". The step ends watching and shows, in red, "A part anyscribe needs to transcribe on this computer didn't install. Click Try again; if it fails again, untick local transcription and go on."
- This is the builder's real walk: proof.md, the "real walk" bullets, and screens/fix2-after-restart-try-again-1440.png.
- If the engines had already installed, the red line would instead read "Setup finished, but Whisper Base can't run yet", and "finished" is false.
- So the notice promises a resume, and what follows reads as an install failure the customer caused. It even suggests giving up on local.
- Try again does work, because the model download resumes (providers/local_models.py:17 and :528, traced from the docstrings, not run). Nothing tells the customer that.

The fix is wording, the S12 shape the lead already owns:
- S12: "Can't reach anyscribe right now. If you quit it, open it again: this page then shows the download again, or a Try again button that carries on from where it stopped."
- troubleshooting.md:574: the same two outcomes.
- CHANGELOG:61: "...can be closed after one question." Drop "the download carries on", or say "if anyscribe is still running".

Optional, and code: when the ending read has `setup_outcome` null (the server restarted mid-setup), say "The setup stopped before it finished (anyscribe was closed). Click Try again; it carries on from where it stopped." instead of the missingPart sentences. That fact is knowable from the payload (local.py:81).

F3-2. nit. CONFIRMED (screenshot).
Where: OnboardingWizard.tsx:892. The "missing" alert, moved above the picker by R2F2's commit 6a375b3, while the Try again button stays at the bottom (around :960).
What goes wrong: the red "Click Try again; ..." sits at the top of the dialog, and the button it names is below five model cards, out of sight at 1440 px (fix2-after-restart-try-again-1440.png). A first-time customer reads "Click Try again", sees no such button and hesitates. R2F2 asked for the progress block to move up. The setup-error and missing alerts went along with it.
Fix: move only the `missing` (and `setupError`) block back below the picker, just above the button row, and keep the progress block on top.

F3-3. nit. CONFIRMED (screenshot fix2-f4-restart-banner-1440.png).
Where: OnboardingWizard.tsx:875-878, the RestartBanner children.
What goes wrong: one box says restart twice in a row. First "...Quit anyscribe from its menu-bar or tray icon, then open it again. Until then, local transcription may fail..." and then "Restart anyscribe, then open the setup wizard again...". It reads as two separate instructions.
Fix: children text "Then open the setup wizard again (Settings, then Run setup wizard); the download is kept."

F3-4. nit. PLAUSIBLE.
Where: OnboardingWizard.tsx:275 (the S11 box renders at the top of the dialog) and Modal.tsx:118 (the dialog scrolls inside itself, overflow-y-auto).
What goes wrong: a customer who has scrolled down to the model cards or the Back button and presses Escape while S12 shows gets the "Close setup?" box at the top, out of view. On their screen nothing happens. Focus also stays where it was, so a keyboard or screen-reader user isn't taken to the choice.
To settle it: at 390 px, while unreachable, scroll to the bottom and press Escape.
Fix: `autoFocus` on the "Keep waiting" button. One attribute: it scrolls the box into view and gives keyboard users the choice.

3. ROUND 2 FIT FINDINGS: STATUS
- R2F1 (Windows Check again can't see winget): FIXED.
  - FfmpegNotice.tsx:199-202 says to quit from the tray and reopen from the Start menu.
  - install.ps1:367-368 says the same in the box.
  - The hint under the buttons dropped "then click Check again", and troubleshooting.md has a Windows bullet.
  - Not run on Windows.
- R2F2 (progress below the fold): FIXED. fix2-lock-progress-above-picker-390.png shows "Downloading Whisper Base… 37%" at the top, above Help me choose. The side effect is F3-2.
- R2F3 (three "until the download finishes" lines): FIXED. Only one remains, OnboardingWizard.tsx:260, "Skip and Back are off until setup finishes." It is in the committed bundle. The checkbox suffix and the Back line are gone.
- R2F4 (two restart messages in the restart case): FIXED. missingPart returns null when a restart is needed (:759-760), and only the RestartBanner shows, ending with the way back to the wizard. A wording leftover is F3-3.

4. ANSWERS AND ADVICE
- Right job, right instrument: yes.
  - The fix plan's choice (keep the owner's hard lock, add an exit only while anyscribe can't be reached) is the smallest step that keeps what he approved.
  - The confirm-to-close question is correctly parked in BACKLOG wave 2 (BACKLOG.md:686) rather than built.
- Simplest thing: yes, given the lock.
  - One writer, one loop, a 10 s limit, and a three-value report to the wizard.
  - The lead's `busy` change (locked from the click) removes the fixer's gap without a new state.
  - I'd not add more.
- What he would object to:
  - F3-1 first: the one sentence written for "something went wrong" is the one that misleads.
  - Second, a customer is still held in the wizard for the whole download while anyscribe answers. For Turbo's 1.6 GB on a slow line that is a long wait, with Back and Skip off. This is his approved design, but he should hear it plainly when the wave 2 question goes to him.
- Read as a first-time customer:
  - S11, S12, S13 and the Windows ffmpeg sentence are short and plain, with no jargon and no em dashes in the new strings.
  - S11's "Close setup" is the bright button and "Keep waiting" the quiet one. That is fine for an exit someone asked for by pressing Escape or Skip.

5. PENDING OWNER CHECKS
- Release timing (round 1 F1): merging puts both installers and the website docs live at once. The dashboard changes, including everything in round 3, reach customers only with a PyPI release.
- The W6 amendment: he approved "lock the wizard during download". The lead added "closable, after one question, when anyscribe can't be reached". He should confirm, and answer the wave 2 question (confirm-to-close, or download in the background).
- A real Mac run and a real Windows (PowerShell 5.1) run, including the Windows "quit from the tray" wording. Nobody has run either.
- After quitting and reopening the desktop app, does it come back on the same port, so the old tab reconnects? If not, S12 waits forever in the old tab. Not checked; see section 5.

6. COULD NOT CHECK, AND WHAT I INSPECTED
Not checked:
- CI on c07a65c. The brief's allow-list does not cover `gh`. Command: `gh pr checks 26 --repo rishmadaan/anyscribe`
- Whether a killed download resumes on Try again (traced from local_models.py docstrings only), and whether the reopened app keeps its port. Both need a real run: a real local setup, quit the tray mid-download, reopen, click Try again.
- Nothing was run beyond `bash -n install.sh` (ok) and read-only git and grep. No tests, builds, servers or installers.

Inspected:
- The packet: ask.md, spec.md (including the W6 amendment), target.md, lens.md, declined.md, fix-plan-r2.md, review-log.md, my round 2 report, and proof.md's round 3 fixer and lead sections.
- `git log 7ab1539..c07a65c`.
- The full source diff ae8f460..c07a65c: OnboardingWizard.tsx, FfmpegNotice.tsx, LocalSetupNotes.tsx, api/client.ts, install.ps1, BACKLOG.md, CHANGELOG.md, docs/user/troubleshooting.md and the journal.
- c07a65c's own diff.
- web/routes/local.py: state, status and the setup thread.
- Modal.tsx's scroll container.
- A grep of the committed bundle for the S13 and S12 strings.
- An empty-diff check on tailnet.py, app.py, the version files, .github and release.sh.

Screenshots viewed:
- fix2-s12-unreachable-1440
- fix2-s11-confirmation-1440
- fix2-after-restart-try-again-1440
- fix2-lock-progress-above-picker-390
- fix2-f4-restart-banner-1440

Not re-read this round:
- The installers apart from install.ps1's one changed box.
- W1 to W5, W7 and W8 code unchanged since round 2.
- findings.md and diagnosis-r2.md in full (I read the fix plan that binds them).
- The harness logs.

What I skipped: the raw harness logs and the unchanged items. The risk the owner must know: S12 tells a customer that quitting and reopening resumes the download, but it actually ends in a red failure line until they click Try again.
