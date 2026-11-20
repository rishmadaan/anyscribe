You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names. Test folders, leave
them alone: ~/labs/projects/anyscribe-wt/wave1/tests.

THE PACKET, read all of it first: ~/labs/projects/anyscribe-wt/wave1/docs/reviews/2026-11-20-onboarding-wave1-lock/
ask.md (the owner's words: his approval and his two answers; the first question
is whether this is the job he asked for), spec.md, target.md, proof.md (what the
builder ran and saw: claims to check, not facts), lens.md;
~/labs/projects/anyscribe-wt/wave1/docs/reviews/declined.md (SETTLED, DO NOT REOPEN).
Background the spec builds on: ~/labs/projects/anyscribe-wt/wave1/docs/reviews/2026-11-20-onboarding-wave1/diagnosis-r2.md
(section 4, design B) and that folder's report-gpt-6.1-sol-r3.md and report-opus-fit-r3.md.

THE TARGET: checkout ~/labs/projects/anyscribe-wt/wave1, branch
feat/onboarding-wave1-lock at 03f6562 (GitHub PR rishmadaan/anyscribe#27). The
change is `git -C ~/labs/projects/anyscribe-wt/wave1 diff b70c2a5..03f6562`
(b70c2a5 is main after PR #26). Review sources; the static bundle and
landing/docs are generated.

YOUR ROLE: correctness. Reproduce and trace: is it true, does it work, what breaks, what is claimed beyond the evidence. Check every spec rule (1 to 12) against the code and try to break it with the orderings in diagnosis-r2.md section 2 and its test table.

MUST NEVER HAPPEN:
- The setup wizard traps the customer: any state where closing is impossible other than while saving at Finish.
- Escape, a click outside or Skip closes the wizard during a watched download without the confirmation (including right after a reload, and while anyscribe is unreachable).
- Any sentence claims something the code or the server does not do (the download carrying on after quitting; Try again resuming; "ready").
- "Close setup" hides the wizard for good (sets scribe_onboarding_dismissed).
- An old status reply ends or starts watching for a newer start request.
- Raw server text (status codes, JSON, "Failed to fetch") reaches the screen.
- Anything PR #26 shipped outside the download lock changes.

BUDGET: this is round 2 of at most 2, the final re-check; about 30 minutes.

ROUND 2: findings.md (in the packet) holds every round 1 report verbatim; review-log.md the lead's verdicts (L1 was kept as a nit and NOT fixed: it is settled residue, logged in BACKLOG); fix-plan-r1.md the lead's binding choices; proof.md's last section the fixer's proof per finding. DELTA: ~/.review-runs/2026-11-20-onboarding-wave1-lock/delta-r2.patch (`git diff ffdb7cc..03f6562`); read the changes first, trace anywhere you need to. Mark every round 1 finding (L1 to L3, LF1 to LF5) FIXED / PARTLY / NOT FIXED / DECLINED-OK with one line of evidence; then name NEW defects the fixes introduced. The fixer widened LF1 to SettingsPage.tsx, docs/user/configuration.md, the skill's references/commands.md and a types.ts comment (string-only), and LF3 also makes a click outside the open confirmation hide it: judge both.

SOURCES beyond the packet: ui/src/components/OnboardingWizard.tsx in full,
ui/src/components/Modal.tsx, ui/src/components/LocalSetupNotes.tsx,
ui/src/api/client.ts and types.ts, src/anyscribe/web/routes/local.py (what the
status payload holds). The builder's harness, cases, results and screenshots:
~/.review-runs/2026-11-20-onboarding-wave1-lock/ (instruments/, logs/, screens/).

LEAD-MADE CHANGES: ffdb7cc (round 1 records and fix plan) only; no code.

LENS: ~/labs/projects/anyscribe-wt/wave1/docs/reviews/2026-11-20-onboarding-wave1-lock/lens.md

YOU MAY RUN: read-only commands: git log/show/diff on that checkout, grep,
sed -n, cat. YOU MAY NOT: run tests, builds, servers, Docker, package installs,
anything that writes; push, comment on the PR, or call any provider API.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Round 1 findings status, then new findings, most severe first, numbered R2L1, R2L2...: severity
   (blocker / should-fix / nit, only these words); CONFIRMED (you traced it) or
   PLAUSIBLE (say what would settle it); where (file:line); what goes wrong, as a
   concrete scenario; the fix (for copy, the exact replacement wording).
3. Answers to any questions in this brief (advice, not findings).
4. Pending owner checks: things only the owner can confirm.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
