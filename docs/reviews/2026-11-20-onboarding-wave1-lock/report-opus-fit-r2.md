FIT REVIEW, round 2 (final re-check). Onboarding wave 1 lock follow-up, PR #27.
Target checked: ~/labs/projects/anyscribe-wt/wave1, HEAD 03f6562 (confirmed with git rev-parse). Delta read: ffdb7cc..03f6562, plus the full change b70c2a5..03f6562 where I needed to trace.

1. VERDICT: CONDITIONAL on two things.
(a) R2LF1 below: one sentence. The new setup-failure line gives the customer no way out if Try again keeps failing.
(b) CI green on 03f6562. I was not allowed to run it.

Everything else is good to go.
- It is still the job he asked for: closing is allowed after a warning, and nothing locks except saving at Finish.
- Every round 1 finding is either fixed or settled.
- The fixes stayed inside the copy and the one close callback.
- The committed bundle is index-DyrxykgW.js, as index.html references. It has the new strings once each, and 0 hits for "the download resumes" and "resume download".

2. ROUND 1 STATUS

- L1 (opening reply not handed to a mounted step): DECLINED-OK. This is settled residue. BACKLOG.md:691 carries the fix plan's wording verbatim (commit 2cfb7b9).
- L2 (S14 named a cause it could not know): FIXED. OnboardingWizard.tsx:86 is now "Setup didn't finish. Click Try again to start it again." The troubleshooting heading and entry (troubleshooting.md:598-602), the journal and the CHANGELOG all match, and none of them claims a cause.
- L3 (raw server text on screen): FIXED.
  - The setupError state and its raw block are deleted.
  - Line 784 now sets SETUP_FAILED through the existing `missing` block, so the button reads Try again.
  - The log no longer opens by itself.
  - Screenshot r1fix-setup-failed-1440.png shows only the plain sentence.
  - The sentence itself has a gap: see R2LF1.
- LF1 (false "resumes" claims): FIXED. LocalModelPicker.tsx:85 and troubleshooting.md:645-647 are fixed. The widening was the right call:
  - The other four places carried the same false claim: the SettingsPage button, configuration.md, the skill's commands.md and a types.ts comment.
  - Each now matches the real-run evidence ("starts again" / "download again").
  - The Settings label came from PR #25 (15d08c5), not PR #26, so the "nothing PR #26 shipped changes" rule is not touched.
  - "Incomplete: download again" reads plainly to a creator.
  - One sibling is left: the CLI line (R2LF4).
- LF2 (S12 confused someone who closed anyscribe): FIXED. OnboardingWizard.tsx:83. Troubleshooting now has one bullet for each reader (closed it / still open). It reads right.
- LF3 (Escape on the open confirmation did nothing): FIXED. OnboardingWizard.tsx:247. The click outside is also right:
  - Escape and a click outside the dialog are both "back out of this question" gestures.
  - Hiding the question keeps both the download and the wizard, which is the safe default.
  - The choice that loses something (Close setup) still needs its own button.
  - onWatched still clears the confirmation when watching ends (line 121), so it cannot stick around after the download finishes.
  - No trap: Skip and Close setup stay reachable.
- LF4 (CHANGELOG said only Back is off): FIXED. CHANGELOG now reads "Back and the model choices are off until the setup finishes."
- LF5 (code comment did not say what the check found): FIXED. OnboardingWizard.tsx:81-82 states the 35.6% to 0% finding.

NEW FINDINGS

R2LF1. should-fix. CONFIRMED (code plus screenshot r1fix-setup-failed-1440.png).
Where: ui/src/components/OnboardingWizard.tsx:88 (SETUP_FAILED) and its use at line 784.
What goes wrong:
- A creator's setup fails for a reason that does not go away: no internet, a full disk, a refused engine install.
- Before L3 they at least saw the raw reason. Now they see only "anyscribe couldn't finish setting up local transcription. Click Try again."
- They click Try again, it fails the same way, and the same sentence comes back. Nothing tells them there is another way forward.
- Every other failure sentence in this step ends with "if it fails again, <untick local transcription and go on / choose a cloud service instead>" (lines 829, 1029, 1031). This one is the odd one out.
- The install log control that holds the reason sits above the model cards, out of view, and the sentence does not point to it.
- Not a trap (Skip, Back and the checkbox all work), but it is a loop with no stated exit.

Fix: make it match its siblings (otherwise() needs `required`, so build it inline at line 784 instead of as a constant):
`anyscribe couldn't finish setting up local transcription. Click Try again; if it fails again, ${otherwise(required)}.`
Update the CHANGELOG quote to match ("...Click Try again; if it fails again, choose another way to transcribe." or just quote the first sentence). I would not add "the install log says why": if the last log read failed, the log may not hold the error line.

R2LF2. nit. CONFIRMED (screenshot r1fix-s12-1440.png; OnboardingWizard.tsx:908-912).
What goes wrong:
- While anyscribe cannot be reached, the new S12 says "If you closed it, the download stopped too".
- Directly below it, the progress line still spins "Installing the local engines and downloading the model…".
- For the reader S12 now addresses, the two lines contradict each other. LF2 made this sharper, though it was already in PR #26 (rule 14).
Fix: one ternary. While `unreachable`, the progress line reads "Waiting for anyscribe…". Or log it as a wave 2 BACKLOG line.

R2LF3. nit. CONFIRMED (grep of docs/user finds no hit for "couldn't finish setting up").
The new on-screen sentence has no troubleshooting entry. S11, S12 and S14 each got one, per the spec. A customer who searches the docs for the red line finds nothing, and the raw reason is now hidden behind the log.
Fix: add to docs/user/troubleshooting.md after the S14 entry (then regenerate landing/docs):
### "anyscribe couldn't finish setting up local transcription." (setup wizard)
The setup ran but stopped with an error. The reason is in the install log: click **show install log** above the model cards; the last line starting with `[error]` names it. Click **Try again**. If it fails again, untick local transcription and go on (or choose a cloud service), and look up that error line on this page.

R2LF4. nit. CONFIRMED.
Where: src/anyscribe/cli/models_cmd.py:415, which prints "Resume the download: anyscribe model pull {size}"; the BACKLOG line is BACKLOG.md:692.
What goes wrong:
- This is the same false claim LF1 removed everywhere else. It sits in wave 2 with no "before the next PyPI release" marker, so it reaches customers with the release.
- This is the CLI, not the server, so changing it does not break the spec's "no server change" rule.
Fix: change the string to "Download it again: anyscribe model pull {size}". Or prefix BACKLOG.md:692 with "**Before the next PyPI release:**".

3. ANSWERS
- Widened LF1: correct and well bounded. All four extra changes are string or comment only, each fixes the same disproven claim, and none was shipped by PR #26.
- LF3's click outside: correct; see above. It is consistent with Escape and never loses the download or the choices.
- Simplest thing: yes. L3 reused the existing `missing` block and deleted a state and its block instead of adding one. Net, the code got smaller.

4. PENDING OWNER CHECKS
- L1 is a lock edge case. He was told the lock's leftovers would never reach a customer, but L1 is going to wave 2 without a "before PyPI" marker. Rare and harmless (the download keeps running; one close skips the warning), but it is his promise, so he should know.
- The final S11 wording is longer than the line he approved: it adds "while anyscribe stays open" and "To come back: Settings, then Run setup wizard". It is more honest; he should see it.
- Release timing, his call.
- Untested by anyone: a real Mac and Windows run, and whether a reopened desktop app comes back on the same port. If it does not, S12's "this page shows a Try again button" never comes true in the old tab.

5. COULD NOT CHECK; WHAT I INSPECTED
Could not check:
- CI on 03f6562: `gh pr checks 27 --repo rishmadaan/anyscribe`
- No harness, test or build was run (the brief does not allow it). The mutant results claimed in proof.md (M3, M3L, MLF3) were not re-run or opened.
- Whether the final log read reliably carries the `[error]` line was traced only, not run. The status is read before the log on the ending tick, and the server appends `[error]` before it sets running to false, so it normally does.

Inspected:
- Brief and packet: brief-r2-fit.md, ask.md, spec.md, lens.md, declined.md, findings.md (both round 1 reports), review-log.md, fix-plan-r1.md, and proof.md's round 1 fix section.
- The full non-generated delta ffdb7cc..03f6562.
- OnboardingWizard.tsx: the shell at lines 110-330 and the local step at lines 700-1032.
- Modal.tsx's Escape handling.
- web/routes/local.py's setup thread and outcome fields; core/local_setup.py's return statuses (ffmpeg never fails setup, so SETUP_FAILED and the ffmpeg notice do not collide).
- troubleshooting.md lines 566-647.
- The committed bundle's string counts.
- Screenshots r1fix-s12-1440, r1fix-s14-1440 and r1fix-setup-failed-1440.

Skipped: the harness files and the other screenshots. Risk: R2LF1 leaves anyone whose setup keeps failing with no stated way forward, unless the one sentence is changed.
