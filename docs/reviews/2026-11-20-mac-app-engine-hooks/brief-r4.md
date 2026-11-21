You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names. Test folders, leave
them alone: ~/labs/projects/anyscribe-wt/mac-engine/tests.

THE PACKET, read all of it first: ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/ask.md, ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/spec.md (its "Round 3 design"
section binds this round), ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/target.md, ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/proof.md (claims to check, not facts),
~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/lens.md, ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/diagnosis-r3.md; ~/labs/projects/anyscribe/docs/reviews/declined.md
(SETTLED, DO NOT REOPEN).
YOUR ROLE: correctness: reproduce and trace; is it true, does it work, what
breaks, what is claimed beyond the evidence.
THE CODE: repo ~/labs/projects/anyscribe-wt/mac-engine, branch feat/mac-app-engine at 4470a4d.
MUST NEVER HAPPEN: the six invariants in lens.md, plus the two in spec.md "Round 3
design" (a transcript's final path never holds part of its content; a watched
engine leaves nothing it started running, by any exit route).
BUDGET: round 4 of at most 5; the re-check after the second diagnosis; about 20 minutes.
ROUND 4: ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/findings.md (all reports verbatim), ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/review-log.md (the lead's
verdicts, rounds 1 and 2), the fix proofs in proof.md "Round 3 fixes".
DELTA: ~/labs/projects/anyscribe-wt/mac-engine/docs/reviews/2026-11-20-mac-app-engine-hooks/delta-r4.patch (git diff 4d9bb42..4470a4d, review files excluded). Read
the changes first; trace anywhere. Mark R1 FIXED /
PARTLY / NOT FIXED against spec.md "Round 4 design" (the atomic_write contract, five points) and diagnosis-r4.md, then look for anything new.
MIGRATION AND INTEGRATION RISKS to judge explicitly:
- every atomic_write caller (config, index, batch state, desktop manifest, tailnet
  file, transcripts): permissions kept for existing files, umask default for new ones;
  fsync cost; the hidden temp name in the vault (Obsidian, history listing, dedup scans);
  a stray temp after a hard kill;
- a watched engine now always ends by SIGKILL of its own group: the tailnet rule
  removal on each exit route, the shell's reading of exit codes, a bind failure in
  watch mode, uvicorn versions 0.27 to 0.54 (signal re-raise or return);
- "a stop is final": jobs and pip installs killed mid-way; the add-ons folder after a
  killed pip install;
- the CLI, MCP and Claude Code paths (no --watch-stdin, no ANYSCRIBE_APP) must be unchanged
  except for the write's fsync and permission behaviour.
LEAD EVIDENCE at 4470a4d: pytest 992 passed, 6 skipped (run with -B and no cache); ruff all passed; check-docs ok.
LEAD-MADE CHANGES: spec.md "Round 3 design", diagnosis-r3.md, review-log notes only.

YOU MAY RUN: read-only commands, and python one-liners that import and print
(no writes, no servers, no subprocesses). YOU MAY NOT: run tests, build, install,
start servers, write files. If a check needs a run, write the exact command.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. A1 to A4 and the follow-ups as FIXED / PARTLY / NOT FIXED, one line of evidence each;
   then NEW defects the fixes introduced.
3. New findings, most severe first, numbered R1, R2...: severity (blocker /
   should-fix / nit); CONFIRMED or PLAUSIBLE (what would settle it); where; scenario; fix.
4. Your judgement on each migration and integration risk above (one line each).
5. What you could not check, and why; what you inspected. No em dashes.
