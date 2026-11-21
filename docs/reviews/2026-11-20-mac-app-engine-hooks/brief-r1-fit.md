You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names. Test folders, leave
them alone: ~/labs/projects/anyscribe-wt/mac-engine/tests.

THE PACKET, read all of it first: ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/ask.md (the owner's ask, in his words; the
first question is whether this is the job he asked for and the right instrument
for it; if the brief, the goal or the spec is wrong, say so instead of reviewing
around it), ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/spec.md, ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/target.md (the exact thing), ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/proof-bar.md,
~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/proof.md (what the builder ran and saw: claims to check, not facts), ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/lens.md;
~/labs/projects/anyscribe/docs/reviews/declined.md (SETTLED, DO NOT REOPEN).
YOUR ROLE: fit: is this what he asked for, does it serve the approved Mac app, is it the simplest thing, what would he or a future maintainer object to.
THE CODE: git repo ~/labs/projects/anyscribe-wt/mac-engine, branch
feat/mac-app-engine. Review the diff 7ab1539..2dd8e64 (code and docs); the commit
8ab28d0 after it adds only review files. Read surrounding code as needed.
MUST NEVER HAPPEN: the six invariants in lens.md, section "Code PR".
BUDGET: this is round 1 of at most 3; about 30 minutes.
SOURCES beyond the packet: the repo (src/anyscribe, tests, docs/building, AGENTS.md,
CLAUDE.md, docs/building/COMMIT_CHECKLIST.md). The approved mockup's "For the build"
section: the approved mockup (kept privately; its sha256 starts bcf26037)
LEAD-MADE CHANGES: only the review files in 8ab28d0 (lens.md, review-log.md, target.md lines).

LENS: everything in ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/lens.md.

YOU MAY RUN: read-only commands (git log/show/diff/grep, cat, sed, rg, ls), and
python one-liners that only import and print (no writes, no servers).
YOU MAY NOT: run pytest or any test runner, build, install, start servers, write files.
If a check needs a run, write the exact command; the lead will run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Findings, most severe first, numbered F1, F2...: severity
   (blocker / should-fix / nit, only these words); CONFIRMED (you reproduced
   or traced it) or PLAUSIBLE (you did not; say what would settle it); where
   (file:line); what goes wrong, as a concrete scenario; the fix.
3. Answers to any questions in this brief (advice, not findings).
4. Pending owner checks: things only the owner can confirm.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
