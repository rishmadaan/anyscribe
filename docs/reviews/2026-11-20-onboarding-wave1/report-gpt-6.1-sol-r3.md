**NOT YET.** The seven original round 2 findings are repaired on their reported paths, but the new handoff can let a customer leave a confirmed running download without the required confirmation. A further request-ordering risk remains untested.

Reviewed `feat/onboarding-wave1` at `c07a65cf74c9cd3dbe2d2a4184b32a715d6e8013`, against `248ee2b`. The work still matches the approved wave 1 scope. CONFIRMED below means established by source trace or existing recorded evidence; runtime execution was prohibited.

**Round 2 findings**

Locations below are within `~/labs/projects/anyscribe-wt/wave1/`.

| Finding | Status | Evidence |
|---|---|---|
| R2C1 | **FIXED** | `OnboardingWizard.tsx:795` sends only the start request; subsequent status failures no longer enter its refusal handler. Recorded T1, T1_500 and T2 support this. |
| R2C2 | **FIXED** | The wizard no longer writes a running lock from its opening read. T5 and T5_late show the original true-then-false handoff no longer leaves a stale lock. |
| R2C3 | **FIXED** | The watcher bounds requests, retries sequentially, handles log failure separately, and exposes the unreachable notice and confirmation. T7, T8 and T9 support these paths. |
| R2F1 | **FIXED** | `FfmpegNotice.tsx:76` and `install.ps1:368` directly instruct Windows users to quit from the tray and reopen. Native Windows operation remains unverified. |
| R2F2 | **FIXED** | `OnboardingWizard.tsx:901` places progress above the picker. Both supplied desktop and mobile screenshots show it near the top. |
| R2F3 | **FIXED** | Only the header retains the lock explanation, now “Skip and Back are off until setup finishes.” |
| R2F4 | **FIXED** | `missingPart()` returns null for the specified restart case; the single RestartBanner includes the route back to the wizard. Recorded F4 and its screenshot support this. |

**New findings**

1. **R3C1 | should-fix | CONFIRMED: the running-download handoff starts unlocked, and Back can bypass the unreachable confirmation.**

   Where: [OnboardingWizard.tsx:162](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:162), especially lines 696, 712, 715 and 953.

   Concrete sequence:

   - Reopen the wizard during a real download.
   - The wizard’s opening read returns `setup_running: true` and routes to Local transcription.
   - The local step initializes `watching` and `starting` to false. It receives neither the running state nor the opening response.
   - Its next status read hangs or fails.

   Until that step receives a successful running response, it reports `idle`. Skip is available, Escape closes immediately, and Back is enabled. This discards the already confirmed running state before the two failures required for the approved exit.

   There is also a persistent bypass after the unreachable notice appears: Back remains enabled because `busy` is still false. Clicking Back unmounts the step, whose cleanup reports `idle`; Escape or Skip can then close without S11.

   The final-bundle evidence already exposes part of this defect: [lead-final.json:476](~/.review-runs/2026-11-20-onboarding-wave1/logs/fix2-instruments/results/lead-final.json:476), T6’s `afterTwoFails`, records `"back": "enabled"`. T6 checks the notice and eventual recovery, but never attempts Back or an early close.

   Fix: transfer the opening read’s running knowledge into the single owner, retaining it until a qualifying stopped response. Keep navigation guarded during reconciliation. Test Escape, Skip and Back both before the second read settles and after S12 appears.

2. **R3C2 | should-fix | PLAUSIBLE: a status response can start and finish watching before the start request settles.**

   Where: [OnboardingWizard.tsx:723](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:723), particularly lines 750–765, 782 and 795–804.

   Rule 6 requires the ending status request to have been sent after the start request settled. The implementation achieves that in the ordinary path by switching `watching` after the POST, but does not enforce it generally.

   On returning to the local step with a previous selection, Download is enabled while the first status read is pending. If that read reports another running setup while a new start request remains pending, it sets `watching=true`. The watcher can then consume a stopped response and advance to Workspace before the pending POST settles. With requests reordered across connections, that pending request could subsequently start work after the step has been left.

   The existing T11 delays a stopped response and gives the POST an immediate answer. It does not cover an earlier running response combined with a delayed POST.

   What would settle it: extend T11 with an initial running response arriving during a delayed start request, followed by stopped-and-runnable status. Assert that completion cannot occur before the start settles, and that only a subsequently sent read can end watching.

   Fix: explicitly track the start request’s lifetime and invalidate earlier status reads. Do not rely solely on `watching` changing to establish request ordering.

3. **R3C3 | nit | CONFIRMED: recovery documentation promises continuation that a server restart does not guarantee.**

   Where: [CHANGELOG.md:60](~/labs/projects/anyscribe-wt/wave1/CHANGELOG.md:60) and [troubleshooting.md:571](~/labs/projects/anyscribe-wt/wave1/docs/user/troubleshooting.md:571), also generated `landing/docs/troubleshooting.html`.

   The changelog says the download carries on after describing an unreachable server, including quitting it. Troubleshooting says reopening makes progress come back.

   Setup runs inside the server process, and its tracking state is in memory. After termination or a crash, reopening can instead produce the Try again state. The journal and recorded restart walk correctly describe that outcome.

   Fix: say the download continues **if anyscribe remains running**. After reopening, the page reconnects and may ask the customer to retry setup.

**The 14 binding rules**

| Rule | Assessment |
|---|---|
| 1. One owner | **MET structurally:** one reporting effect and no wizard poll. The handoff loses information, as R3C1 explains. |
| 2. Lock and confirmed unreachable exit | **PARTLY:** correct after watching starts; adoption has an unlocked interval and Back bypass. The implemented two-failure threshold follows rules 1 and 11, as the proof discloses. |
| 3. S11 and buttons | **MET** on paths reaching it. Close setup uses `dismiss(false)`. |
| 4. Start/adopt watching | **PARTLY:** local running reads and POST outcomes work; the wizard’s confirmed running response is not inherited. |
| 5. Explicit refusals | **MET:** non-409 HTTP failures show the plain refusal sentence without their body. |
| 6. Qualified ending read | **PARTLY:** failures never end watching, but the post-start ordering is implicit and has the R3C2 gap. |
| 7. Exactly once | **MET within a watcher:** `stop` and cleanup discard replaced or unmounted results. The premature-completion concern is rule 6. |
| 8. Status separate from log | **MET:** failed logs no longer discard status. A hanging log can still delay applying it by the bounded log wait. |
| 9. Bounded and sequential | **MET for the polling loop.** This is not a global single-request guarantee: the wizard opening read and manual Check again can overlap step reads. |
| 10. First-status recovery | **MET:** reads continue until status arrives, with S12 after repeated failures. |
| 11. Unreachable notice | **MET in the loop:** two failures show it; a good loop response clears it; percentages disappear while unreachable. |
| 12. No raw text | **PARTLY:** fetch-layer errors are suppressed, but `setup_error` still renders verbatim at line 886. This is pre-existing behavior explicitly disclosed in the proof, not a new regression. |
| 13. Previous guards | **PARTLY:** checkbox, Back, picker and start are disabled while busy; adoption is not initially busy. Selected-model runnable checks and key-check guards remain. |
| 14. Progress and one explanation | **MET:** progress precedes the picker and only one lock explanation remains. |

**Ordering and test assessment**

The diagnosis’s section 2 contains **ten numbered orderings, not twelve**. There are no rows 11 and 12 to assess.

| Cases | Assessment from source and recorded evidence |
|---|---|
| Orderings 1–2; T1–T2 | Accepted start or 409 followed by a failed read retains watching and hides raw errors. |
| Ordering 3; T3 | Stopped-and-runnable status advances without showing 409. |
| T4 and variants | Network failure, timeout and explicit refusal are distinguished. Final T4v2 covers the lead’s start-time lock. |
| Ordering 4; T5 | Original stale lock is removed, including the delayed opening response. |
| Ordering 5; T6 | Recovery eventually works, but early closing and Back expose R3C1. |
| Ordering 6; T7, T9 | Established watchers expose server loss; hung reads abort and retry. |
| Ordering 7; T8 | Log failure no longer blocks successful completion. |
| Ordering 8; T10 | Sequential polling and cleanup prevent the reported duplicate completion path. |
| Ordering 9; T11 | The recorded fast-POST ordering works; the delayed-POST variant remains R3C2. |
| Ordering 10; T12 | A non-runnable selected model produces Try again rather than ready after restart. |
| T13 | Established watching supports the intended reachable lock, unreachable confirmation and reopening path. It does not exercise R3C1’s initial handoff. |

The mutation records demonstrate failures for M1, M6 with HTTP 500, M6b, M8 and M9, followed by restored passes. The final lead run’s old T4_hang failure is explained by its obsolete expectations; the replacement T4v2 checks the actual request timeout.

**Integration, bundle and retained behavior**

- `onRunning` has one code call site, inside the local step’s reporting effect. Settings, LocalSetupModal and App do not consume that callback.
- `fetchJSON` itself is unchanged. The three API wrappers gained optional signals; existing callers omit them and retain their previous behavior. The 10-second limit lives in the wizard’s `limited()` helper, not globally in the API client.
- Settings and LocalSetupModal retain their existing polling behavior and receive no new timeout or unreachable exit. Their known limitations are recorded in BACKLOG.
- RestartBanner’s optional children leave its other callers’ content unchanged.
- Static `index.html` references `index-2r9Aqod2.js`. Inspection of that bundle confirms the final `busy` lock expression, timeout helper and revised header text. **I found no inspected mismatch, but did not independently establish exact build equivalence.**
- The delta does not change provider error classification, transcript rendering, key-check endpoints, dependencies, tailnet code or Host/security middleware. The retained key input and navigation guards remain present.
- The records describe the chosen hard lock with an unreachable exit, rather than design B. Their unconditional lock claims overstate the implementation because of R3C1.

**Pending owner checks**

Only release timing remains an owner decision: whether and when to release the dashboard changes to PyPI alongside merge-time installer and website publication. Native-platform verification and the findings above are engineering work, not actions assigned to the owner.

**Inspection and verification limits**

I read the named packet, earlier findings and verdicts, both fix plans, diagnosis, declined list, lead-made changes, source delta and relevant callers. I inspected the harness, cases, mutations, saved result records, walk log and all seven `fix2` screenshots. The settled Homebrew finding was not reopened.

These permitted checks passed:

```text
git -C ~/labs/projects/anyscribe-wt/wave1 diff --check 248ee2b..c07a65c
bash -n ~/labs/projects/anyscribe-wt/wave1/install.sh
git -C ~/labs/projects/anyscribe-wt/wave1 diff --exit-code c07a65c -- ui/src src/anyscribe/web/static install.sh install.ps1 docs/user
```

The brief prohibited running these checks:

```text
cd ~/labs/projects/anyscribe-wt/wave1 && .venv/bin/python -m pytest -q
cd ~/labs/projects/anyscribe-wt/wave1 && .venv/bin/ruff check src tests scripts
cd ~/labs/projects/anyscribe-wt/wave1/ui && npm run lint && npm run build
cd ~/labs/projects/anyscribe-wt/wave1 && python3 scripts/build-docs.py && python3 scripts/check-docs.py
gh pr checks 26 --repo rishmadaan/anyscribe
```

I ran no tests, builds, servers, installers or provider calls, and wrote nothing. Exact-SHA CI, runtime reproduction of the new sequences, native macOS and Windows behavior, screen-reader behavior, and timeout suitability during a real installation remain unverified. The round 3 walk used simulated setup state over real status requests; it did not perform a real download.