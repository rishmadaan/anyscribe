You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names. Test folders, leave
them alone: ~/labs/projects/anyscribe-wt/mac-shell/desktop/test.

THE PACKET, read all of it first: ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/ask.md, ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/spec.md, ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/target.md,
~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/proof.md (claims to check, not facts), ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/lens.md;
SETTLED, DO NOT REOPEN: ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/declined.md
(includes the round 1 decline of C5).
YOUR ROLE: correctness: reproduce and trace; is it true, does it work, what
breaks, what is claimed beyond the evidence.
THE CODE: repo ~/labs/projects/anyscribe-wt/mac-shell, branch feat/mac-app-shell
at 04986cc. The engine it targets (read-only): ~/labs/projects/anyscribe-wt/mac-engine
at 4d9bb42 (its /api/health has "pid"; --watch-stdin; one exit door that kills its own group).
MUST NEVER HAPPEN: the six invariants in lens.md, section "Code PR".
BUDGET: this is round 2 of at most 3; about 25 minutes.
ROUND 2: ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/findings.md (both round 1 reports verbatim), ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/review-log.md (the
lead's verdicts), ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/fix-plan-r1.md (binding choices), proof.md "Round 1 fixes".
DELTA: ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/delta-r2.patch (git diff 880ed2c..04986cc, review files excluded). Read
the changes first; trace anywhere. Mark every round 1 id FIXED / PARTLY / NOT FIXED /
DECLINED-OK, then look for anything new, especially problems the fixes introduced
(the lifecycle queue, the synchronous quit decision, the pid check, process-group
spawning and killing, the frame and redirect guards).
LEAD EVIDENCE at 04986cc: npm test 43 pass 0 fail; the builder's e2e 11 steps against 4d9bb42.
LEAD-MADE CHANGES: review files only.

YOU MAY RUN: read-only commands, and node one-liners that require a module and
print (no Electron, no servers, no writes). YOU MAY NOT: npm test, npm install,
electron, any test runner, or writes. If a check needs a run, write the exact command.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round 1 id as FIXED / PARTLY / NOT FIXED / DECLINED-OK, one line each;
   then NEW defects the fixes introduced.
3. New findings, most severe first, numbered A1, A2...: severity (blocker /
   should-fix / nit); CONFIRMED or PLAUSIBLE; where; scenario; fix.
4. Pending owner checks.
5. What you could not check, and why; what you inspected. No em dashes.
