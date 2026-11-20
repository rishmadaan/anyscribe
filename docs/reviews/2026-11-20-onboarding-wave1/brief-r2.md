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
feat/onboarding-wave1 at 248ee2b (GitHub PR rishmadaan/anyscribe#26). The last
reviewed commit was 8d63221.

YOUR ROLE: correctness re-check. Reproduce and trace: is each fix real, does it
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

BUDGET: this is round 2 of at most 3; about 30 minutes.

ROUND 2: findings.md holds every earlier report verbatim and review-log.md
the lead's verdicts; the fix proofs are in proof.md. DELTA:
~/.review-runs/2026-11-20-onboarding-wave1/delta-r2.patch
(`git diff 8d63221..248ee2b`); read the changes first, trace anywhere you need
to. Check that each fix is real (read the code, probe it, try to break it with
concrete inputs: cloud path with the local backup during a download; reload
mid-download then Finish; a 409 while a different model downloads; a check
answer arriving after the key text changed or after Back; ffmpeg present only
in the PowerShell session's own PATH; a transcript URL with nested or unbalanced
parentheses; a 402 or insufficient_quota from each provider), and look for
anything new, especially problems the fixes introduced (the new server-following
lock: can it stay locked forever, can the wizard ever be stuck with no way out
if the server dies or the status call fails; timers left running after close).

SOURCES beyond the packet: the files the delta touches and their callers.
Screenshots and run logs from the fix walk: ~/.review-runs/2026-11-20-onboarding-wave1/screens/fix1-*.png
and ~/.review-runs/2026-11-20-onboarding-wave1/logs/fix1-*.

LEAD-MADE CHANGES in this range: commits 97aca0f, f348666 and 37f066c only add
review records (reports, verdicts, fix plan, the F2 line in declined.md,
review-log timings). No code.

LENS: ~/labs/projects/anyscribe-wt/wave1/docs/reviews/2026-11-20-onboarding-wave1/lens.md

YOU MAY RUN: read-only commands: git log/show/diff on that checkout, grep,
sed -n, cat, `bash -n`. YOU MAY NOT: run tests, builds, servers, installers,
Docker, package installs, anything that writes; push, comment on the PR, or call
any provider API.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round 1 finding (C1 to C5, F1 to F10) as FIXED / PARTLY / NOT FIXED /
   DECLINED-OK, one line of evidence each (F1 is an owner decision with no code
   change; F2 is REFUTED and settled); then NEW defects the fixes introduced.
3. New findings, most severe first, numbered R2C1, R2C2...: severity
   (blocker / should-fix / nit, only these words); CONFIRMED or PLAUSIBLE (say
   what would settle it); where (file:line); what goes wrong, as a concrete
   scenario; the fix.
4. Pending owner checks: things only the owner can confirm.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
