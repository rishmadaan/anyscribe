You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names. Test folders, leave
them alone: ~/labs/projects/anyscribe-wt/mac-engine/tests.

THE PACKET, read all of it first: ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/ask.md, ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/spec.md, ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/target.md,
~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/proof.md (builder and fixer claims to check, not facts), ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/lens.md;
~/labs/projects/anyscribe/docs/reviews/declined.md (SETTLED, DO NOT REOPEN).
YOUR ROLE: correctness: reproduce and trace; is it true, does it work, what
breaks, what is claimed beyond the evidence.
THE CODE: git repo ~/labs/projects/anyscribe-wt/mac-engine, branch
feat/mac-app-engine at 2b1c2bc.
MUST NEVER HAPPEN: the six invariants in lens.md, section "Code PR".
BUDGET: this is round 2 of at most 3; about 25 minutes.
ROUND 2: ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/findings.md holds both round 1 reports verbatim and ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/review-log.md
the lead's verdicts; ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/fix-plan-r1.md the lead's binding choices (with two
addenda: C1 keeps the platform encoding; S-C2 adds "pid" to /api/health); the fix
proofs are in proof.md "Round 1 fixes". DELTA: ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/delta-r2.patch
(git diff 2dd8e64..2b1c2bc, review files excluded). Read the changes first, trace
anywhere you need to. Check that each fix is real (read the code, try to break it
with the lens inputs and: an Origin with a trailing slash, a port of 0 or 99999,
IPv6 with and without brackets, mixed case scheme; a job list with 0, 1, 50, 51
and 600 jobs mixing states; stdin closing during tailnet cleanup; the group kill
when the engine is not the group leader; the strict port when the port frees
during the check), and look for anything new, especially problems the fixes introduced.
LEAD EVIDENCE at 2b1c2bc: pytest 974 passed, 6 skipped; ruff all passed; check-docs 0.
LEAD-MADE CHANGES: the two fix-plan addenda and this round's review-log note only.

YOU MAY RUN: read-only commands (git log/show/diff/grep, cat, sed, rg, ls), and
python one-liners that import and print (no writes, no servers, no subprocesses).
YOU MAY NOT: run pytest or any test runner, build, install, start servers, write files.
If a check needs a run, write the exact command; the lead will run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round 1 id (C1 to C6, F1 to F4, S-C2) as FIXED / PARTLY / NOT FIXED /
   DECLINED-OK, one line of evidence each; then NEW defects the fixes introduced.
3. New findings, most severe first, numbered A1, A2...: severity (blocker /
   should-fix / nit, only these words); CONFIRMED or PLAUSIBLE (say what would
   settle it); where (file:line); the concrete scenario; the fix.
4. Pending owner checks.
5. What you could not check, and why; what you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
