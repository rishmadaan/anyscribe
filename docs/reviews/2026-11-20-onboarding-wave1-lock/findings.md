# Findings, verbatim

Note: absolute home-folder paths are written as `~` paths in these copies; originals stay in ~/.review-runs/2026-11-20-onboarding-wave1-lock/. The fit report was relayed through the Agent tool and saved with its one home path already as a `~` path.

## Round 1: report-gpt-6.1-sol-r1.md

~~~~
**NOT YET.** The ordinary watched-download path now allows closing after confirmation, but the opening status request still bypasses adoption and request-ordering protections. Two error messages also violate the required accuracy guarantees.

Reviewed `feat/onboarding-wave1-lock` at `bc144d4043fb3e66109afb7ef948fc991ca2079f`, against `b70c2a5`. CONFIRMED below means established by source trace or inspected recorded evidence. Runtime execution was prohibited.

**1. Findings**

**L1. should-fix | CONFIRMED: the opening status reply is not reconciled with an already-mounted step or a newer start.**

Where: [OnboardingWizard.tsx:169](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:169), especially the unconditional form/routing updates at lines 173–180, the `useState(adopt)` initializer at line 711, and closing at line 198.

Concrete failure:

1. Open or reload the wizard during a download. Its opening status request is delayed.
2. Navigate to Local transcription before that request answers. The step mounts with `adopt=false`.
3. The step’s own status reads fail.
4. The opening request then answers `setup_running:true`. The wizard changes `adopt` to true, but `useState(adopt)` only uses its initial value. Watching remains false.
5. Escape and backdrop close immediately. Skip closes immediately **and sets the dismissal flag**. Back remains enabled, including after the unreachable notice appears.

There is confirmed running knowledge, with no newer successful response contradicting it, yet confirmation is bypassed.

The recorded `T5_late` demonstrates that a late opening reply does not update watching, but its newer step response says stopped. It does not test the failure sequence above. `R3C1` tests only the ordering where adoption arrives before the step mounts.

The same opening callback is outside `startGenRef` protection. If its old running reply arrives after a newer, quick setup has completed and advanced to Workspace or All set, it unconditionally routes back to Local transcription. That remount starts watching from `adopt=true`, using an old reply sent before the newer start.

Before the opening request answers, `watched` also starts false; an opening failure is silently discarded. Reload reconciliation therefore has an unguarded closing interval.

**Fix:** reconcile the opening request through the same owner and request-ordering rules as the step. Deliver eligible adoption to an already-mounted step, while rejecting opening replies superseded by a newer successful status or start. Keep unresolved reload reconciliation closable through confirmation. Merely synchronizing every `adopt` change would revive stale responses.

Verify both missing variants: delayed opening-running plus failed step reads; and delayed opening-running arriving after a newer setup completes.

**L2. should-fix | CONFIRMED: S14 states a cause the payload cannot establish.**

Where: [OnboardingWizard.tsx:86](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:86), its selection at line 792, and [troubleshooting.md:594](~/labs/projects/anyscribe-wt/wave1/docs/user/troubleshooting.md:594).

Concrete failure: the start request fails before reaching a server that remains open. The next status response has no running setup, outcome or error. The wizard says:

> The setup stopped before it finished, because anyscribe was closed.

Neither a started setup nor a closed server is established. The server initializes this same empty state before any setup has run. The builder’s `T4_notRunning` reproduces this path and currently asserts the inaccurate sentence as a pass. `proof.md` explicitly acknowledges the guess.

**Exact replacement for S14:**

> Setup isn't complete. Click Try again to start it again.

Replace the troubleshooting explanation with:

> anyscribe isn't reporting a running setup or its result. This can happen after a restart, or if the start request never reached anyscribe. Click **Try again** to start it again.

Update the fixed-string assertions, journal quotation and generated documentation accordingly.

**L3. should-fix | CONFIRMED: setup failures still render raw server text.**

Where: [OnboardingWizard.tsx:781](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:781), rendered at line 957; [local.py:195](~/labs/projects/anyscribe-wt/wave1/src/anyscribe/web/routes/local.py:195) and line 210.

Concrete failure: setup ends with an installer or download error. The server stores `result.error`, installer stderr, or `str(e)` as `setup_error`. The wizard displays that value verbatim, truncating only its length, and automatically opens the raw log.

HTTP exception details, status codes and other technical text can therefore appear directly in the error banner. Suppressing failed status-fetch messages does not protect this path.

This behavior predates the follow-up, but remains inside the download step and contradicts rule 4 and the brief’s explicit prohibition. The harness never supplies a current setup failure containing raw text. Its `noRaw` check also recognizes only a small set of strings, so empty results do not prove the general claim.

**Fix:** show a plain failure message and leave technical details behind an explicitly opened diagnostic log. Exact banner wording:

> anyscribe couldn't finish setting up local transcription. Click Try again.

Make the button read **Try again** for this failure too. Add a case with a current `setup_error` containing a status code and JSON, and assert their absence from the normal error display.

**2. Spec and ordering checks**

| Rule | Assessment |
|---|---|
| 1. Never trapped | Closing is disabled only during Finish saving. Skip remains visible during downloads. It is still absent on All set, contrary to the literal “every step” wording, as the proof discloses. |
| 2. Confirmation while watched or starting | Works after `busy` is established. Opening/reload reconciliation fails as described in L1. |
| 3. Confirmation buttons and focus | Met. Keep setting up receives focus; Close setup calls `dismiss(false)`. Desktop and mobile screenshots support visibility. |
| 4. One owner and retained machinery | One `onRunning` call site. The polling loop retains bounded reads, failure handling and completion cleanup. Raw-error guarantee fails under L3. |
| 5. Opening-read adoption | Works when adoption precedes mounting. Fails when it arrives after mounting, under L1. |
| 6. Start-request ordering | The local poller’s generation guard handles the supplied R3C2 sequence. The separate opening callback remains unguarded, under L1. |
| 7. Back and S13 | Back is disabled while `busy`; S13 is correct. L1 can leave a real download outside that state. |
| 8. Unreachable wording | New S12 removes the resume promise. Reconnection after desktop restart still assumes the same origin/port. |
| 9. Interrupted setup | The null-outcome branch and Try again appear. Its asserted cause is unsupported, under L2. |
| 10. Error placement | Met. Error blocks follow the picker and precede the buttons; progress remains above the picker. |
| 11. RestartBanner wording | Met. S15 is supplied through the existing children property, without changing the shared component. |
| 12. Resume evidence | Met for the new wording: fallback text is used. The recorded real run does not support promising resumption. |

The diagnosis contains ten numbered orderings:

| Ordering | Trace and recorded evidence |
|---|---|
| 1–2: accepted start or 409, then failed status | T1, T1_500 and T2 retain watching and suppress fetch-layer errors. |
| 3: 409, then stopped and runnable | T3 advances without showing 409. |
| 4–5: opening running, then stopped or failed step read | T5 and R3C1 cover opening-first handoff. Delayed handoff remains L1. |
| 6: repeated failures or hanging request | T7 and T9 retain watching; the hung request aborts around 10 seconds. |
| 7: stopped status, failed log | T8 completes despite log failure. A hanging log can still delay applying status by its bounded wait. |
| 8: late or duplicate completion | Per-loop cleanup and T10 cover the poller. The independent opening callback remains L1. |
| 9: status sent before start | T11 and R3C2 cover the local poller. They do not cover the opening callback. |
| 10: server restart | T12 avoids advancing for a different runnable model. The recovery sentence has L2’s cause error. |

**3. Answers and evidence assessment**

This is the follow-up the owner approved: confirmation replaces the hard lock. No further owner decision is needed on that choice.

The added `setup_outcome` type declaration is justified by the existing server payload and introduces no runtime dependency.

I inspected all seven result files. `final-all.json` records 24 passing cases. The mutation records contain the claimed failures for M2, M5, M6g and M9s, followed by restored passes. Those checks establish the specific paths exercised, not the missing opening-request orderings.

The real-download log supports the fallback wording: the first run reached 35.6%, the server became unreachable, and the second run began at 0.6% before finishing. The before/after-uninstall package lists match. This evidence does not justify a general resume promise.

The older model-card resume claim remains visible in the real-restart screenshot and is already recorded for wave 2. This follow-up cannot claim that every existing resume statement is now accurate.

**4. Pending owner checks**

Only release timing remains an owner decision: when to release these dashboard changes through PyPI after the engineering findings and checks are resolved.

Native-platform verification, the missing adversarial cases, exact-SHA CI and desktop-port behavior are engineering checks, not tasks assigned to the owner.

**5. Inspection and limits**

I read the complete named packet, declined list, diagnosis and both prior round 3 reports; all six named source files; the complete wizard; source and record changes; generated documentation changes; all six instrument files; all seven saved result files; supplied logs and package snapshots; and all nine screenshots.

Read-only checks established:

- HEAD and branch match the requested target.
- Inspected source and static files have no working-tree delta from `bc144d4`.
- `git diff --check b70c2a5..bc144d4` passes.
- Server code, installers, website entry page, tests, workflows, package configuration, API client and shared setup notes have no delta from the base.
- The committed static entry references `index-CBp6eUC1.js`, which contains the revised strings and closing logic.

Exact build equivalence, live UI reproduction, native Mac/Windows behavior, screen-reader operation and desktop restart reconnection were not independently established.

The brief prohibited running these checks:

```text
cd ~/labs/projects/anyscribe-wt/wave1 && .venv/bin/python -m pytest -q
cd ~/labs/projects/anyscribe-wt/wave1 && .venv/bin/ruff check src tests scripts
cd ~/labs/projects/anyscribe-wt/wave1/ui && npm run lint && npm run build
cd ~/labs/projects/anyscribe-wt/wave1 && python3 scripts/build-docs.py && python3 scripts/check-docs.py
gh pr checks 27 --repo rishmadaan/anyscribe
```

Browser harness entry points such as `window.__run("R3C1")` and `window.__run("R3C2")` were inspected, not executed. No tests, builds, servers, downloads or provider calls were run. Nothing was written or changed.
~~~~

## Round 1: report-opus-fit-r1.md

~~~~
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

~~~~
