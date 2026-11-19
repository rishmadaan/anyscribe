Copied from the review run folder; absolute home-folder paths rewritten as ~ paths; the byte-exact original stays in ~/.review-runs/2026-11-19-local-first-parakeet/.

~~~~~
You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names (and the code it points
to). Test folders, leave them alone: ~/labs/projects/anyscribe-wt/local-first/tests.

THE PACKET, in ~/labs/projects/anyscribe-wt/local-first/docs/reviews/2026-11-19-local-first-parakeet/ :
ask.md (the owner's ask, in his words), spec.md, target.md, lens.md,
findings.md (every round-1, 2 and 3 report verbatim), review-log.md (the lead's verdict
on each finding: the ledger), fix-plan-r1.md, fix-plan-r2.md and fix-plan-r3.md (the lead's binding choices for
the fixes), proof.md (the builder's proof, then "## Round 1 fixes": one entry
per finding, then "## Round 2 fixes", then "## Round 3 fixes"; claims to check, not facts), diagnosis-r2.md (why round-2 defects recurred), spec.md section 5 (the round-3 design). Declined list (SETTLED, DO NOT
REOPEN): ~/labs/projects/anyscribe-wt/local-first/docs/reviews/declined.md

TARGET (frozen): worktree ~/labs/projects/anyscribe-wt/local-first,
branch feat/local-first-parakeet, commit 90bc0cf. Last reviewed commit 5551230.

YOUR ROLE: given in the prompt that sent you here.

MUST NEVER HAPPEN:
- A user with no API key cannot get a working local transcript, or is shown an API-key warning on the local path.
- Parakeet output is written for audio in a language Parakeet does not cover, without the switch, a note, or a loud failure.
- An existing user's provider, model or quality changes without their choice.
- A feature exists on one surface only (CLI vs Web UI vs MCP).
- Owner data (personal file names, paths, transcript text) lands in the public repo.

BUDGET: round 4, approved by the owner over the cap; the last one; about 30 minutes.

ROUND 2: findings.md holds every earlier report verbatim and review-log.md the
lead's verdicts; the fix proofs are in proof.md. DELTA:
~/.review-runs/2026-11-19-local-first-parakeet/delta-r4.patch
(`git diff 5551230..90bc0cf`, minus the rebuilt web/static bundle and
regenerated landing/docs). Read the changes first, trace anywhere you need to.
Check that each fix is real (read the code, probe it, try to break it), and
look for anything new, especially problems the fixes introduced. This is the FINAL re-check of the round-3 fixes (R3C1 config lock, R3C2 choose
snapshot, R3C3 choice generation, R3F1 hint, R3F2 tip, R3F3 already-default).
Try to break them: lock ordering against the tailnet lock (deadlock?); a
save_config caller left outside CONFIG_LOCK (grep every caller); reentrancy
(set_value inside a held lock); choose racing setup start; two setups; a
generation taken by a choose that later fails; the CLI run_setup path still
unchanged; the hint printed once per run in transcribe and batch; the
fixer's claim that the reviewer's "printed twice" was wrong. The fixer listed
known leftovers (POST /api/onboarding/save local setup without the
generation; setup modal skipping its result screen on an instant setup;
no special superseded message; `anyscribe onboard` after `local setup` says
pass --force): judge whether any matters before merge.

LEAD EVIDENCE (re-derive what you can):
1. Full suite on 90bc0cf: 912 passed, 4 skipped; `ruff check src tests` clean.
2. Round 3's correctness reviewer was gpt-6.1-sol; this round is Claude-only
   by the owner's choice.

LENS: lens.md (Code PR + Screen packs), every line.

YOU MAY RUN: read-only commands (git log/diff/show, grep, cat, python -c that
imports and inspects without writing). YOU MAY NOT: run tests, builds,
servers, installs, downloads, or anything that writes. Name any check you
could not run as an exact command.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round-3 finding (R3C1..R3C3, R3F1..R3F3) as FIXED / PARTLY / NOT FIXED /
   DECLINED-OK, one line of evidence each; then NEW defects the fixes introduced.
3. Findings, most severe first, numbered with your prefix (R4C1.. for
   correctness, R4F1.. for fit): severity (blocker / should-fix / nit, only
   these words); CONFIRMED or PLAUSIBLE (say what would settle it); where
   (file:line); what goes wrong, as a concrete scenario; the fix.
4. Pending owner checks.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
~~~~~
