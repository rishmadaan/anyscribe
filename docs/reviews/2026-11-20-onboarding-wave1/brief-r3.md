You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names. Test folders, leave
them alone: ~/labs/projects/anyscribe-wt/wave1/tests.

THE PACKET, read all of it first: ~/labs/projects/anyscribe-wt/wave1/docs/reviews/2026-11-20-onboarding-wave1/
ask.md (the owner's ask, in his words; the first question is whether this is
the job he asked for), spec.md, target.md, proof.md (its last section, "Round 1
fixes (one entry per finding)", holds the fix proofs: claims to check, not
facts), proof-install.md, proof-app.md, lens.md, findings.md (every round 1
report verbatim), review-log.md (the lead's verdict on each finding),
fix-plan-r1.md (the lead's binding choices for the fixes);
~/labs/projects/anyscribe-wt/wave1/docs/reviews/declined.md (SETTLED, DO NOT REOPEN; it now includes F2).

THE TARGET: checkout ~/labs/projects/anyscribe-wt/wave1, branch
feat/onboarding-wave1 at c07a65c (GitHub PR rishmadaan/anyscribe#26). The last
reviewed commit was 248ee2b.

YOUR ROLE: final correctness re-check (round 3, the last round allowed). Reproduce and trace: is each fix real, does it
work, what breaks, what is claimed beyond the evidence.

MUST NEVER HAPPEN:
- A customer's install stops silently, or the Windows window closes and takes the error with it.
- Any screen or box says ready, valid, accepted or set up when it is not (including "<model> · ready" for a model that cannot run).
- The setup wizard can be left, closed or skipped while a local download runs, or loops silently.
- A key-check answer moves the wizard on with a key other than the one it checked.
- A customer's API key is logged, echoed, stored before Finish, or sent anywhere but its own provider over HTTPS.
- Transcript content runs as HTML or script, or produces a live non-http(s) link.
- An ordinary rate limit (429 without insufficient_quota) stops being retried.
- Anything on spec.md's keep-list breaks; tailnet code or the web app's Host check changes.

BUDGET: this is round 3 of at most 3, the final re-check; about 30 minutes.

ROUND 3: findings.md holds every earlier report verbatim (rounds 1 and 2);
review-log.md the lead's verdicts; diagnosis-r2.md why the round 1 lock kept
failing; fix-plan-r2.md the lead's binding design for round 3 (hard lock kept,
ONE owner, a bounded sequential status read, an exit only when the server is
unreachable; NOT the diagnosis's design B); spec.md W6 carries the amendment.
The fix proofs are in proof.md, sections "Round 2 fixes, built in round 3" and
"Lead-made changes before the round 3 re-check". DELTA:
~/.review-runs/2026-11-20-onboarding-wave1/delta-r3.patch
(`git diff 248ee2b..c07a65c`); read the changes first, trace anywhere you need
to. Mark every round 2 finding (R2C1, R2C2, R2C3, R2F1 to R2F4) FIXED / PARTLY /
NOT FIXED with evidence, check each of fix-plan-r2.md's 14 rules against the
code, and try to break the lock with the orderings in diagnosis-r2.md (section 2
table, rows 1 to 12) and its test table T1 to T13.
MIGRATION AND INTEGRATION RISKS this round must name (from the review skill):
- the wizard and the local step changed how they share the lock (a new
  three-value report, one call site); any other caller of the wizard's lock or of
  `onRunning` (Settings, LocalSetupModal, App) that now behaves differently;
- the new request time limit and abort plumbing in ui/src/api/client.ts: every
  other caller of fetchJSON, getLocalStatus, getSetupLog, setupLocal is affected;
- the rebuilt static bundle is what customers load: it must be built from this
  exact source (CI checks this; say if you see a mismatch);
- the docs, CHANGELOG, BACKLOG and journal must describe the shipped behaviour
  (the lock with an exit only when unreachable), not round 1's or design B's.
LEAD-MADE CHANGES in this range: commit c07a65c (two source lines: the lock
value uses `busy` instead of `watching`, and the S13 wording), with its proof in
proof.md; review records in 4def0e4 and ae8f460. Read these first: the lead
cannot see its own blind spot.
SOURCES beyond the packet: the files the delta touches and their callers.
Screenshots and run logs from the round 3 fix: ~/.review-runs/2026-11-20-onboarding-wave1/screens/fix2-*.png,
~/.review-runs/2026-11-20-onboarding-wave1/logs/fix2-results.txt, logs/fix2-walk.txt and
logs/fix2-instruments/ (the harness, the cases and the results JSON).

LENS: ~/labs/projects/anyscribe-wt/wave1/docs/reviews/2026-11-20-onboarding-wave1/lens.md

YOU MAY RUN: read-only commands: git log/show/diff on that checkout, grep,
sed -n, cat, `bash -n`. YOU MAY NOT: run tests, builds, servers, installers,
Docker, package installs, anything that writes; push, comment on the PR, or call
any provider API.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round 2 finding (R2C1 to R2C3, R2F1 to R2F4) as FIXED / PARTLY / NOT
   FIXED, one line of evidence each; then NEW defects the round 3 changes introduced.
3. New findings, most severe first, numbered R3C1, R3C2...: severity
   (blocker / should-fix / nit, only these words); CONFIRMED or PLAUSIBLE (say
   what would settle it); where (file:line); what goes wrong, as a concrete
   scenario; the fix.
4. Pending owner checks: things only the owner can confirm.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
