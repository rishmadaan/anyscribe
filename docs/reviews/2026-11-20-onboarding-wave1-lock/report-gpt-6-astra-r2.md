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