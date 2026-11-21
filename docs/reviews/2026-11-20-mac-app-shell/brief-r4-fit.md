You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names. Test folders, leave
them alone: ~/labs/projects/anyscribe-wt/mac-shell/desktop/test.

THE PACKET, read all of it first: ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/ask.md, ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/spec.md, ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/target.md,
~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/proof.md (claims to check, not facts), ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/lens.md;
SETTLED, DO NOT REOPEN: ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/declined.md
(includes the round 1 decline of C5).
YOUR ROLE: fit (you are a fresh fit reviewer rejoining because the fixes change what the owner sees: the default title bar, the new quit question for an unknown job list, menu separators, header style, the 5-row cap): is this what he asked for, does it match the approved mockup (the approved mockup (kept privately; its sha256 starts bcf26037), sections 2, 6, 7, 9), is it the simplest thing, what would he object to.
THE CODE: repo ~/labs/projects/anyscribe-wt/mac-shell, branch feat/mac-app-shell
at 787bfa1. The engine it targets (read-only): ~/labs/projects/anyscribe-wt/mac-engine
at b22df16 (rebased onto main; engine review closed GOOD TO GO at 4470a4d) (its /api/health has "pid"; --watch-stdin; one exit door that kills its own group).
MUST NEVER HAPPEN: the six invariants in lens.md, section "Code PR".
BUDGET: this is round 4 of at most 5, the re-check after the third diagnosis; about 20 minutes.
ROUND 2: ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/findings.md (all reports verbatim, rounds 1 to 3), ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/review-log.md (the
lead's verdicts), ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/fix-plan-r1.md (binding choices), proof.md "Round 3 fixes" and "Round 4 fixes"; diagnosis-r4.md and spec.md "Round 4 design" (binding for this round).
DELTA: ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/delta-r4.patch (git diff 2383f26..787bfa1, review files excluded). Read
the changes first; trace anywhere. Mark S3-A1 and G7 to G10 FIXED / PARTLY / NOT FIXED, then look for anything new,
especially in the quit path now that Stop and Quit sends no cancels.
LEAD EVIDENCE at 787bfa1: npm test 50 pass 0 fail; the builder's e2e 12 steps against the engine at b22df16 (Stop and Quit exits in 39 ms).
LEAD-MADE CHANGES: review files only.

YOU MAY RUN: read-only commands, and node one-liners that require a module and
print (no Electron, no servers, no writes). YOU MAY NOT: npm test, npm install,
electron, any test runner, or writes. If a check needs a run, write the exact command.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. S3-A1 and G7 to G10 as FIXED / PARTLY / NOT FIXED, one line each;
   then NEW defects the fixes introduced.
3. New findings, most severe first, numbered G1, G2...: severity (blocker /
   should-fix / nit); CONFIRMED or PLAUSIBLE; where; scenario; fix.
4. Pending owner checks.
5. What you could not check, and why; what you inspected. No em dashes.
