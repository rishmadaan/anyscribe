FIT REVIEW, onboarding wave 1 lock follow-up, round 1. Target checked: ~/labs/projects/anyscribe-wt/wave1, branch feat/onboarding-wave1-lock, HEAD bc144d4 (git rev-parse). Change read: b70c2a5..bc144d4.

1. VERDICT: CONDITIONAL on two things.
(a) LF1 gets handled one of two ways: fix the two old "resumes" strings in this PR (two strings, my recommendation), or mark that BACKLOG line "Before the next PyPI release".
(b) CI is green on bc144d4. I was not allowed to run it.

This is the job he asked for. He picked "Allowed after a warning", and that is what was built:
- Nothing ever turns closing off except saving at Finish (`disableClose={saving}`).
- Skip for now shows on every step except All set.
- While a setup is being watched, Escape, a click outside and Skip open the warning first.
- "Close setup" closes without setting `scribe_onboarding_dismissed`.

The round 3 leftovers he was promised are all in: R3C1, R3C2, F3-1 (with the optional S14 part), F3-2, F3-3 and F3-4. Nothing in the diff goes beyond the spec, apart from one type-only line in types.ts that rule 9 needs.

The new sentences are honest. Each one is either true in the server code or uses the fallback wording, because the builder's real run showed that resume does not work. Simplest thing: yes. One boolean replaces the three-value watch state. The other additions are one `adopt` flag cleared at the two exits, and one counter of about 5 lines. I would not add more.

2. FINDINGS

LF1. should-fix. CONFIRMED (screenshot real-s14-after-restart-1440.png, plus code).
Where: ui/src/components/LocalModelPicker.tsx:85 ("incomplete: the download resumes") and docs/user/troubleshooting.md:642-643 ("the download picks up where it stopped"). These lines are outside this diff, but they show on the exact screen this PR builds.
What goes wrong:
- A customer closed anyscribe mid-download and reopened it.
- On the Whisper Base card they read "incomplete: the download resumes".
- Right below it, the new S14 says "Click Try again to start it again".
- Two sentences on one screen contradict each other, and the builder's own real run proves the card wrong: the download started again from 0%.
- The card shows "incomplete" even though 0 bytes of the model were saved. Only the five small files (2.7 MB) were on disk, and that is enough for `partial` to be true (local_models.py:422).
- The BACKLOG line that records this sits in wave 2 with no "before PyPI" marker, so it ships with the next release. That works against the "leftovers never reach a customer" promise he was given when he chose Merge now.
Fix, smallest: two strings in this PR, as a lead-approved scope addition.
- LocalModelPicker.tsx:85: "incomplete: the download resumes" becomes "incomplete: setup downloads it again".
- troubleshooting.md:643: "the download picks up where it stopped." becomes "the download starts again."
If the lead keeps it out of scope, prefix the BACKLOG line with "**Before the next PyPI release:**".

LF2. nit. CONFIRMED (code: OnboardingWizard.tsx:85; screenshot real-s12-server-stopped-1440.png).
S12 reads: "If you closed it, open it again: this page then shows the download if it is still running, or a Try again button to start it again."
What goes wrong:
- For the reader the sentence is addressed to (someone who closed anyscribe), the download is never "still running". Quitting stops it, which is the whole point of F3-1.
- The "if it is still running" half only fits a case where the customer did nothing (a blip), and there the notice simply clears by itself.
- A creator reading it in the middle of a long download comes away unsure whether closing kept the download going or not.
Fix, exact wording for S12 (also in troubleshooting.md's S12 entry and the CHANGELOG if quoted): "Can't reach anyscribe right now. If you closed it, the download stopped too: open anyscribe again and this page shows a Try again button to start it again."

LF3. nit. CONFIRMED (Modal.tsx:68-71 sends Escape to `askOrClose`; OnboardingWizard.tsx:198).
While the "Close setup?" box is open, Escape just reopens the same box, so nothing visible happens. A keyboard user expects Escape to back out of a question. This is not a trap: Close setup is one Tab away, and "Keep setting up" has focus.
Fix: `onClose={() => (confirmClose ? setConfirmClose(false) : askOrClose(false))}` on the Modal, so Escape means "Keep setting up". The builder's proof states "Escape while S11 is open leaves it open" as intended, so treat this as a lead call.

LF4. nit. CONFIRMED (CHANGELOG.md, the new W6 entry; OnboardingWizard.tsx:880-946).
"the wizard is never locked, and only Back is off until the setup finishes" is wrong. The checkbox, the model cards and the start button are also off while a setup is watched.
Fix: "the wizard is never locked; Back and the model choices are off until the setup finishes."

LF5. nit. CONFIRMED (OnboardingWizard.tsx:81-82).
The code comment "Whether Try again resumes a half-downloaded model was checked with a real download" does not say what the check found. A future builder could put "carries on from where it stopped" back.
Fix: "Try again does not resume a half-downloaded model: a real download stopped at 35.6% restarted from 0% (docs/reviews/2026-11-20-onboarding-wave1-lock/proof.md, rule 12)."

3. ANSWERS AND ADVICE

- Right job: yes. The S11 the customer sees is longer than the line he approved ("The download carries on in the background; your choices are saved only when you click Finish."). It adds "while anyscribe stays open" and "To come back: Settings, then Run setup wizard." Both make it more honest, not less, so I would keep them. He should know the wording moved (section 4).

- Read as a creator in the middle of a long download:
  - S11 is plain and accurate. Focus on "Keep setting up" is the safe default, and at 390 px it scrolls into view (s11-s13-escape-after-scroll-390.png).
  - S13 ("Back is off until setup finishes. Skip for now asks first.") is understandable. "asks first" is a little terse, but acceptable.
  - S14 is clear, and the red block now sits right above Try again (s14 screenshots). One caveat: "because anyscribe was closed" also shows after a crash, or after a start request that got no answer (proof item 2). Optional softer wording: "The setup stopped before it finished, because anyscribe was closed or restarted. Click Try again to start it again."
  - The troubleshooting entries for S11, S12 and S14 match the code, apart from LF2's sentence.

- Must-never list, from the fit side:
  - No trap: saving is the only lock.
  - "Close setup" does not set the flag.
  - No "ready" or "carries on" claims.
  - The RestartBanner change is the F3-3 sentence only. The red blocks moved per F3-2.
  - Nothing else from PR #26 changed in the source diff.
  - Two edges for the correctness reviewer, not findings from me:
    - (i) Right after a reload, before the wizard's opening status read answers (normally milliseconds, up to 10 s under load), the wizard sits on Welcome with nothing watched, so Escape or Skip close it at once. Skip then sets the dismissed flag. The download itself is unaffected.
    - (ii) If "Close setup" is confirmed while the start request is still in flight and that start is then refused (a non-409 answer), S11's "keeps going" was never true. On localhost this is rare.

- What he would object to: LF1 first. A brand-new honest sentence next to an old false one on the same screen undoes the point of this PR. Second, S12's mixed message (LF2).

- Unchanged from round 3, for awareness: while S12 shows, the progress line falls back to "Installing the local engines and downloading the model…" with a spinner, even when anyscribe was closed and nothing is running. That is rule 14 from PR #26 and outside this PR. A wave 2 tweak could say "Waiting for anyscribe…" while unreachable.

4. PENDING OWNER CHECKS
- The final S11 wording, which differs from the line he approved (section 3).
- LF1: fix the two old "resumes" strings now, or accept them reaching customers at the next PyPI release.
- Release timing: everything here reaches customers only with a PyPI release, his call.
- Untested by anyone: a real Mac and Windows run, and whether a reopened desktop app comes back on the same port. If it does not, S12's "this page shows…" never comes true in the old tab.

5. COULD NOT CHECK; WHAT I INSPECTED
Could not check:
- CI on bc144d4: `gh` is not on my allow-list. Command: `gh pr checks 27 --repo rishmadaan/anyscribe`
- Whether "incomplete" ever resumes within one process with no restart. I did not run it, and did not trace huggingface_hub myself; I relied on the proof's trace and its real restart run.
- Nothing was run, built or tested.

Inspected:
- The packet: ask.md, spec.md, target.md, proof.md, lens.md, review-log.md, declined.md.
- diagnosis-r2.md section 4 and report-opus-fit-r3.md in full.
- The source diff b70c2a5..bc144d4: OnboardingWizard.tsx (the wizard shell and the local step in full), types.ts.
- Modal.tsx in full.
- The records diff: CHANGELOG, BACKLOG, troubleshooting.md, _index.md, the journal.
- web/routes/local.py: the state, status and setup thread; `outcome` is set on every ending, so S14's condition holds.
- core/local_setup.py's return statuses.
- LocalModelPicker.tsx:85.
- Screenshots: real-s14-after-restart-1440, real-s12-server-stopped-1440, s11-s13-escape-after-scroll-390.
- I did not read report-gpt-6.1-sol-r3.md, the harness files and results, or LocalSetupNotes.tsx (not touched by the diff).

What I skipped: the harness and its results, and the generated bundle and landing/docs. Risk: LF1's false "resumes" card ships with the next release unless someone acts on it.
