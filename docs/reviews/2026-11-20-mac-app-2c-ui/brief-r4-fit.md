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
YOUR ROLE: fit: is this the job he asked for, the approved screens and words, judged as the owner will meet them. Read the screenshots in ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/shots for every state round 3 changed or added (proof.md names them), at 1440 and 390 px.
THE CODE: git repo ~/labs/projects/anyscribe-wt/mac-2c-ui, branch feat/mac-app-2c-ui. Review head 6e7a335 (rounds 1 to 3 reviewed 6dc70b2..12aa942, 12aa942..9a3ed5d,
9a3ed5d..99bb239); 97d35b4 after it adds review files only. The approved design:
the approved mockup (kept privately; its sha256 starts bcf26037)
(sections 3, 4, 5, 9, 10 and "For the build"). The real bridge the screens run against (read-only):
~/labs/projects/anyscribe-wt/mac-2c-app at 70e911f: desktop/src/preload.js, main.js
(note the engine status handler's reload to / on every return to running), terminal.js,
old-launcher.js, desktop/README.md.
MUST NEVER HAPPEN: the invariants in lens.md.
BUDGET: this is round 4 of at most 5; about 30 minutes. Round 5 is the cap: rank what you find by what he would hit.
ROUND 4: findings.md holds the round 1 to 3 reports verbatim and review-log.md the lead's verdicts.
The round 2 design (fix-plan-r2.md, from diagnosis-r3.md) held; after round 3 a second diagnosis ran
(~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/diagnosis-r4.md) and fix-plan-r3.md is the lead's binding round 4 change: a doomed-page flag (a page
that has seen the engine leave running starts nothing new: two readers only, the queue start gate and the
startup recovery claim), startup recovery bound to the removal note present at page load, the Terminal
card held until that recovery finishes, plus B2, B3, H2 and H4. Its documented limits and the earlier
ones are SETTLED, do not reopen them. Fix proofs: proof.md "Round 3 fixes". DELTA: ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/delta-r4.patch
(git diff 99bb239..6e7a335, review files and the built bundle excluded); the stub and checks changed too
(git diff 99bb239..97d35b4 -- ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks). Read the changes first; trace anywhere. Mark B1 to B3 and H1 to
H4 FIXED / PARTLY / NOT FIXED, then look for anything new the two rules open (a waiting file that never
starts, a removal result never shown or shown twice, the Terminal card never shown, a click on a doomed
page that misbehaves outside the documented limit), and any stub behaviour the real bridge (2c-app at
70e911f) does not have.
LEAD-MADE CHANGES: review files only.

YOU MAY RUN: read-only commands (git, cat, sed, rg, ls) and node or python one-liners
that only read and print. YOU MAY NOT: build, run npm scripts, start servers or browsers,
or write files. If a check needs a run, write the exact command; the lead will run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round 3 id as FIXED / PARTLY / NOT FIXED / DECLINED-OK, one line each; then
   new findings, most severe first, numbered K1, K2...: severity (blocker /
   should-fix / nit, only these words); CONFIRMED or PLAUSIBLE (say what would settle
   it); where (file:line); the concrete scenario; the fix (for wording, the exact words).
3. Answers: the builder notes that B2's reason and the generic advice under it can repeat "Log out and back in"; give the exact words to use (advice).
4. Pending owner checks.
5. What you could not check, and why; any check you could not run, as the exact command;
   what you inspected. No em dashes.
