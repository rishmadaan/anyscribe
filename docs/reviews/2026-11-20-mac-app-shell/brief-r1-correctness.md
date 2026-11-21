You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names. Test folders, leave
them alone: ~/labs/projects/anyscribe-wt/mac-shell/tests and
~/labs/projects/anyscribe-wt/mac-shell/desktop/test.

THE PACKET, read all of it first: ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/ask.md (the owner's ask, in his words; the
first question is whether this is the job he asked for and the right instrument
for it; if the brief, the goal or the spec is wrong, say so instead of reviewing
around it), ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/spec.md, ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/target.md (the exact thing), ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/proof.md (what the
builder ran and saw: claims to check, not facts; its "where the spec is wrong"
points are the builder's, judge them too), ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/lens.md;
~/labs/projects/anyscribe/docs/reviews/declined.md (SETTLED, DO NOT REOPEN).
YOUR ROLE: correctness: reproduce and trace; is it true, does it work, what breaks, what is claimed beyond the evidence.
THE CODE: git repo ~/labs/projects/anyscribe-wt/mac-shell, branch
feat/mac-app-shell. Review the diff 7ab1539..880ed2c (desktop/ and docs); the commit
e97ef9d after it adds only review files. Skip desktop/node_modules except to check
an Electron API's behaviour. The approved design: the mockup at
the approved mockup (kept privately; its sha256 starts bcf26037)
(sections 2, 6, 7, 9 and "For the build").
MUST NEVER HAPPEN: the six invariants in lens.md, section "Code PR".
BUDGET: this is round 1 of at most 3; about 30 minutes.
LEAD-MADE CHANGES: only the review files in e97ef9d.

LENS: everything in ~/labs/projects/anyscribe-wt/mac-shell/docs/reviews/2026-11-20-mac-app-shell/lens.md.

YOU MAY RUN: read-only commands (git log/show/diff/grep, cat, sed, rg, ls), and
node one-liners that only require a module and print (no Electron launch, no servers, no writes).
YOU MAY NOT: run npm test, npm install, electron, any test runner or build, or write files.
If a check needs a run, write the exact command; the lead will run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Findings, most severe first, numbered C1, C2...: severity
   (blocker / should-fix / nit, only these words); CONFIRMED (you reproduced
   or traced it) or PLAUSIBLE (you did not; say what would settle it); where
   (file:line); what goes wrong, as a concrete scenario; the fix.
3. Answers: judge the builder's seven "spec is wrong or open" points in proof.md (advice).
4. Pending owner checks: things only the owner can confirm.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
