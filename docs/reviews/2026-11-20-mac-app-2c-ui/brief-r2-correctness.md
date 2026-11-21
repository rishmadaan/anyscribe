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
THE CODE: git repo ~/labs/projects/anyscribe-wt/mac-2c-ui, branch feat/mac-app-2c-ui. Review head 9a3ed5d (round 1 reviewed
6dc70b2..12aa942); c867050 after it adds review files only. The approved design:
the approved mockup (kept privately; its sha256 starts bcf26037)
(sections 3, 4, 5, 9, 10 and "For the build"). The real bridge the screens run against (read-only):
~/labs/projects/anyscribe-wt/mac-2c-app at 70e911f: desktop/src/preload.js, main.js
(note the engine status handler's reload to / on every return to running), terminal.js,
old-launcher.js, desktop/README.md.
MUST NEVER HAPPEN: the invariants in lens.md.
BUDGET: this is round 2 of at most 5; about 30 minutes.
ROUND 2: findings.md holds both round 1 reports verbatim and review-log.md the lead's verdicts;
fix-plan-r1.md the lead's binding choices; the fix proofs are in proof.md "Round 1 fixes". DELTA:
~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/delta-r2.patch (git diff 12aa942..9a3ed5d, review files and the built bundle excluded).
Read the changes first; trace anywhere. Mark C1 to C7 and F1 to F16 FIXED / PARTLY / NOT FIXED /
DECLINED-OK, then look for anything new, especially problems the fixes introduced: what survives
the app's reload (sessionStorage across loadURL to the same origin), the stored queue and the
preload's ack, the removal note's lifetime and the refusal test (no restart seen during the call),
the readiness gate, the quiet answers that now mark a question asked. Trace against the real
bridge, not only checks/stub.js: any place the stub and the real bridge differ is a finding.
LEAD-MADE CHANGES: review files only.

YOU MAY RUN: read-only commands (git, cat, sed, rg, ls) and node or python one-liners
that only read and print. YOU MAY NOT: build, run npm scripts, start servers or browsers,
or write files. If a check needs a run, write the exact command; the lead will run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round 1 id as FIXED / PARTLY / NOT FIXED / DECLINED-OK, one line each; then
   new findings, most severe first, numbered A1, A2...: severity (blocker /
   should-fix / nit, only these words); CONFIRMED or PLAUSIBLE (say what would settle
   it); where (file:line); the concrete scenario; the fix (for wording, the exact words).
3. Answers: judge the builder's six departures from the fix plan in proof.md (advice).
4. Pending owner checks.
5. What you could not check, and why; any check you could not run, as the exact command;
   what you inspected. No em dashes.
