You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names. Test folders, leave
them alone: ~/labs/projects/anyscribe-wt/mac-2c-ui/tests and ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks.

THE PACKET, read all of it first: ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/ask.md (the owner's ask, in his words; the
first question is whether this is the job he asked for), ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/spec.md, ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/bridge-v2.md
(with its Amendments and Amendment 2), ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/target.md, ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/proof.md (claims to check,
not facts; its "spec is wrong" points are the builder's, judge them), ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/lens.md;
~/labs/projects/anyscribe/docs/reviews/declined.md (SETTLED, DO NOT REOPEN).
YOUR ROLE: correctness: reproduce and trace; is it true, does it work, what breaks, what is claimed beyond the evidence.
THE CODE: git repo ~/labs/projects/anyscribe-wt/mac-2c-ui, branch feat/mac-app-2c-ui.
Review the diff 6dc70b2..12aa942 (ui/src and docs; the static bundle is built output).
The approved design: the approved mockup (kept privately; its sha256 starts bcf26037)
(sections 3, 4, 5, 9, 10 and "For the build").
Trace each screen's calls against the stub (checks/stub.js) AND against 2c-app's real bridge (read-only, ~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/preload.js, main.js, terminal.js, old-launcher.js, and desktop/README.md): any call shape, field or result the screens rely on that the real bridge does not provide is a finding.
MUST NEVER HAPPEN: the invariants in lens.md.
BUDGET: this is round 1 of at most 5; about 30 minutes.
LEAD-MADE CHANGES: review files only.

YOU MAY RUN: read-only commands (git, cat, sed, rg, ls) and node or python one-liners
that only read and print. YOU MAY NOT: build, run npm scripts, start servers or browsers,
or write files. If a check needs a run, write the exact command.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Findings, most severe first, numbered C1, C2...: severity (blocker /
   should-fix / nit, only these words); CONFIRMED or PLAUSIBLE (say what would settle
   it); where (file:line, or screen and state); the concrete scenario; the fix (for
   wording, the exact replacement words).
3. Answers: judge the builder's five "spec is wrong" points (advice).
4. Pending owner checks.
5. What you could not check, and why; what you inspected. No em dashes.
