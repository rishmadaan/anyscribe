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

## Round 2: report-gpt-6-astra-r2.md

~~~~
**CONDITIONAL on green CI for `03f65626718b3163847c22c5de52e476235f16c0`.** No new blocker or should-fix found. One new diagnostic nit is described below. L1 remains accepted, unfixed residue under the binding fix plan; this verdict does not certify the opening-status race as solved.

Reviewed branch `feat/onboarding-wave1-lock`, full change `b70c2a5..03f6562`, and round 2 delta `ffdb7cc..03f6562`. CONFIRMED means established by source trace or inspected saved evidence, not independently rerun.

**1. Round 1 findings**

Locations below are relative to `~/labs/projects/anyscribe-wt/wave1/`.

| Finding | Status | Evidence |
|---|---|---|
| L1 | **DECLINED-OK** | Intentionally unfixed. The opening callback still updates routing independently, and `useState(adopt)` only initializes watching. The required residue is recorded in `BACKLOG.md:691`. |
| L2 | **FIXED** | `OnboardingWizard.tsx:86` says “Setup didn't finish” without inventing a cause. Troubleshooting matches; final T4_notRunning, T5 and T12 assert the corrected sentence. |
| L3 | **FIXED** | At `OnboardingWizard.tsx:784`, server errors select a fixed plain sentence. The raw banner and automatic log opening are removed. L3 passes; M3 and M3L fail as intended. Diagnostic availability has the separate nit below. |
| LF1 | **FIXED** | The picker, Settings button, configuration guide, troubleshooting guide, skill reference and type comment no longer promise resumption. The scoped search finds only unrelated resume references and the explanatory comment. |
| LF2 | **FIXED** | `OnboardingWizard.tsx:84` explicitly says closing anyscribe stops the download. Troubleshooting separates shutdown from temporary loss of contact. |
| LF3 | **FIXED** | `OnboardingWizard.tsx:247` hides an open confirmation on Escape or backdrop click without dismissing the wizard. Final LF3 passes; MLF3 fails both checks. |
| LF4 | **FIXED** | CHANGELOG now includes Back and model choices among the disabled controls. |
| LF5 | **FIXED** | `OnboardingWizard.tsx:81` records the actual observed result: a download stopped at 35.6% restarted from zero. |

**2. New finding**

**R2L1. nit | CONFIRMED: failure details can become inaccessible after the raw banner is removed.**

Where: [OnboardingWizard.tsx:756](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:756), the ending branch at line 781, and the log control at line 903. Supporting server behavior: [local.py:131](~/labs/projects/anyscribe-wt/wave1/src/anyscribe/web/routes/local.py:131).

Concrete sequence:

1. Setup fails.
2. The status request succeeds and contains `setup_error`.
3. The subsequent log request fails or times out.
4. The step shows the new plain message and stops polling.
5. Opening the log only toggles already-fetched text; it does not fetch the missing error. If no earlier log request succeeded, the log control disappears entirely.

Previously, the raw banner exposed the error from the successful status response. Removing that banner is correct, but the replacement assumes the separate log request succeeded.

There is another deterministic route: once the browser’s log cursor reaches 500, the server’s capped buffer continues reporting `total: 500`. A later error shifts older lines out, but `log[500:]` remains empty. The error remains on the server yet never reaches the browser’s log.

The new L3 case does not cover either route. It supplies the error in an early successful log response before announcing setup failure (`instruments/cases.js:556`).

**Fix:** preserve the ending response’s `setup_error` as diagnostic content accessible only through the explicitly opened install log, deduplicating it if already fetched. Keep the plain banner and closed-by-default behavior. Test both a failed final log request and an already-full log buffer.

This is a nit because retry and closing remain available. The proof’s assertion that the raw error remains reachable through the log is stronger than the implementation supports.

**3. Spec and ordering checks**

| Rule | Assessment |
|---|---|
| 1. Never trapped | Met for downloads. Only Finish saving disables modal closing. All set still lacks Skip, the previously disclosed exception; Escape and backdrop remain available there before saving. |
| 2. Confirmation while watched or starting | Met once watching is established, including unreachable states. Accepted L1 limits the reload guarantee. |
| 3. Confirmation behavior | Met. Keep setting up receives focus; Close setup calls `dismiss(false)`. Escape and backdrop now cancel the question. |
| 4. One owner and retained machinery | One `onRunning` call site; bounded sequential polling, separate log handling and guarded completion remain. Raw-error sanitization is fixed; diagnostic retention has R2L1. |
| 5. Opening adoption | Works when the opening response precedes mounting. Delayed adoption remains accepted L1. |
| 6. Start ordering | The local poller rejects responses whose captured generation changed or was odd. The opening callback remains L1’s exception. |
| 7. Back and explanation | Back remains disabled while watching or starting; S13 matches. |
| 8. Unreachable wording | No promise that quitting preserves a running download. Desktop reconnection assumptions remain unverified. |
| 9. Interrupted setup | Null outcome selects cause-neutral S14 when the selected model cannot run and ffmpeg is present. |
| 10. Error placement | The plain error follows the picker and immediately precedes the buttons. Progress remains above the picker. |
| 11. Restart wording | S15 is supplied through the existing RestartBanner children; the shared component is unchanged. |
| 12. Resume evidence | Fallback wording is used. The recorded real run supports restarting, not guaranteed resumption. |

I traced all ten orderings in diagnosis section 2 against the code and recorded cases:

- Accepted start or 409 followed by failed reads retains watching.
- A stopped, runnable result advances once.
- Opening-first adoption survives failed or hanging step reads; delayed adoption remains L1.
- Repeated failures and hung requests retain an exit through confirmation.
- Failed log reads do not discard completion.
- Cleanup prevents the tested duplicate-completion path.
- T11 and R3C2 cover stale local reads and delayed starts.
- Restart cases distinguish interruption from a completed setup whose selected model cannot run.

**4. Answers to the brief**

This is the owner’s requested follow-up: replace the hard lock with closing after a warning.

The widened LF1 changes are appropriate. The binding fix plan explicitly requested searching those folders and correcting sibling resume claims. Settings’ change is a label only; its action is unchanged. The documentation and type-comment changes introduce no runtime dependency.

The widened LF3 backdrop behavior is also appropriate: clicking outside the open question means Keep setting up. It cannot confirm closure, and the recorded LF3 case checks this explicitly.

No unrelated runtime change from PR #26 was found. Server implementation, API client, shared setup notes, installers, tests, workflows and package configuration have no change from the base. The skill-reference change is documentation only.

**5. Pending owner checks**

Only release timing remains an owner decision. CI, native-platform testing, diagnostic coverage and desktop-port verification are engineering work, not tasks for the owner.

L1 is already settled by the brief and was not reopened.

**6. Evidence and limits**

Inspected the complete named review packet, declined list, diagnosis and both preceding round 3 reports; the full wizard and named supporting source files; changed Settings, picker and documentation passages; both source deltas; current harness, cases and mutation instruments; final result assertions and request traces; mutation failures and restored results; relevant real-download log entries; three new desktop screenshots and two earlier mobile screenshots.

The final saved run records **26 passing cases**. M3, M3L and MLF3 contain the claimed failures. The earlier T3 failure occurred during harness cleanup, before T3’s assertions; the final run passes after cleanup was repaired.

Read-only verification confirmed:

- HEAD and branch match the target.
- `git diff --check b70c2a5..03f6562` passes.
- Inspected source, static and documentation files match the target commit.
- Static `index.html` references `index-DyrxykgW.js`, which contains the revised strings.

I did not establish exact build equivalence, exact-SHA CI, live browser behavior, native Mac/Windows behavior, screen-reader behavior, desktop restart port stability, or behavior across older supported download-library versions. The finding above was traced, not executed.

The brief prohibited rerunning:

```sh
cd ~/labs/projects/anyscribe-wt/wave1
.venv/bin/ruff check src tests scripts
.venv/bin/python -m pytest -q
cd ui && npm run lint && npm run build
```

```sh
cd ~/labs/projects/anyscribe-wt/wave1
python3 scripts/build-docs.py && python3 scripts/check-docs.py
gh pr view 27 --repo rishmadaan/anyscribe --json headRefOid,statusCheckRollup
gh pr checks 27 --repo rishmadaan/anyscribe
```

Browser harness calls such as `window.__run("L3")`, `window.__run("LF3")` and `window.__run("R3C2")` were inspected, not executed. R2L1’s two variants have no existing test command.

Nothing was edited, started, stopped, installed, sent or written.
~~~~

## Round 2: report-opus-fit-r2.md

~~~~
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

~~~~
