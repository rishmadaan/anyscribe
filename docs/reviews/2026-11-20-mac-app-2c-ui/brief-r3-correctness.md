You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names. Test folders, leave
them alone: ~/labs/projects/anyscribe-wt/mac-2c-ui/tests and ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks.

THE PACKET, read all of it first: ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/ask.md (the owner's ask, in his words; the
first question is whether this is the job he asked for; if the brief, the goal or the spec
is wrong, say so instead of reviewing around it), ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/spec.md, ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/bridge-v2.md
(with its Amendments and Amendment 2), ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/target.md, ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/proof.md (claims to check,
not facts; the builder's departures from the fix plan are listed there, judge them), ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/lens.md;
~/labs/projects/anyscribe/docs/reviews/declined.md and ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/declined.md (SETTLED, DO NOT REOPEN).
YOUR ROLE: correctness: reproduce and trace; is it true, does it work, what breaks, what is claimed beyond the evidence.
THE CODE: git repo ~/labs/projects/anyscribe-wt/mac-2c-ui, branch feat/mac-app-2c-ui. Review head 99bb239 (round 1 reviewed 6dc70b2..12aa942, round 2
12aa942..9a3ed5d); f1aae31 after it adds review files only. The approved design:
the approved mockup (kept privately; its sha256 starts bcf26037)
(sections 3, 4, 5, 9, 10 and "For the build"). The real bridge the screens run against (read-only):
~/labs/projects/anyscribe-wt/mac-2c-app at 70e911f: desktop/src/preload.js, main.js
(note the engine status handler's reload to / on every return to running), terminal.js,
old-launcher.js, desktop/README.md.
MUST NEVER HAPPEN: the invariants in lens.md.
BUDGET: this is round 3 of at most 5; about 30 minutes.
ROUND 3: findings.md holds the round 1 and round 2 reports verbatim and review-log.md the lead's
verdicts. After round 2 a diagnosis ran (~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/diagnosis-r3.md); fix-plan-r2.md is the lead's binding
round 3 design (decisions from facts only: "mine" only while this page's own call is in flight, the
removal note resolved only against the app's saved lastRemoval while the engine reads running, a queued
file leaves only once accepted, a stopped-engine banner, a stub that models the real bridge) with its
documented limits (SETTLED, do not reopen them). Fix proofs: proof.md "Round 2 fixes", including the
builder's three gap fills. DELTA: ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/delta-r3.patch (git diff 9a3ed5d..99bb239, review files and the
built bundle excluded); the stub and checks changed too (git diff 9a3ed5d..f1aae31 -- ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks).
Read the changes first; trace anywhere. Mark A1 to A5 and G1 to G7 FIXED / PARTLY / NOT FIXED, then look
for anything new, especially what the new design opens: a queued file that never starts or starts twice,
a removal result never shown or shown twice, a restart misread as his or as a crash outside the
documented limits, a stub behaviour the real bridge (2c-app at 70e911f) does not have.
LEAD-MADE CHANGES: review files only.

YOU MAY RUN: read-only commands (git, cat, sed, rg, ls) and node or python one-liners
that only read and print. YOU MAY NOT: build, run npm scripts, start servers or browsers,
or write files. If a check needs a run, write the exact command; the lead will run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round 2 id as FIXED / PARTLY / NOT FIXED / DECLINED-OK, one line each; then
   new findings, most severe first, numbered B1, B2...: severity (blocker /
   should-fix / nit, only these words); CONFIRMED or PLAUSIBLE (say what would settle
   it); where (file:line); the concrete scenario; the fix (for wording, the exact words).
3. Answers: judge the builder's three gap fills in proof.md "Round 2 fixes" (advice).
4. Pending owner checks.
5. What you could not check, and why; any check you could not run, as the exact command;
   what you inspected. No em dashes.
