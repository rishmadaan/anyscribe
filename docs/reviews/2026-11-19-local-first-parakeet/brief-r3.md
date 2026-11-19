Copied from the review run folder; absolute home-folder paths rewritten as ~ paths; the byte-exact original stays in ~/.review-runs/2026-11-19-local-first-parakeet/.

~~~~~
You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names (and the code it points
to). Test folders, leave them alone: ~/labs/projects/anyscribe-wt/local-first/tests.

THE PACKET, in ~/labs/projects/anyscribe-wt/local-first/docs/reviews/2026-11-19-local-first-parakeet/ :
ask.md (the owner's ask, in his words), spec.md, target.md, lens.md,
findings.md (every round-1 and round-2 report verbatim), review-log.md (the lead's verdict
on each finding: the ledger), fix-plan-r1.md and fix-plan-r2.md (the lead's binding choices for
the fixes), proof.md (the builder's proof, then "## Round 1 fixes": one entry
per finding, then "## Round 2 fixes"; claims to check, not facts), diagnosis-r2.md (why round-2 defects recurred), spec.md section 5 (the round-3 design). Declined list (SETTLED, DO NOT
REOPEN): ~/labs/projects/anyscribe-wt/local-first/docs/reviews/declined.md

TARGET (frozen): worktree ~/labs/projects/anyscribe-wt/local-first,
branch feat/local-first-parakeet, commit 5551230. Last reviewed commit 8c5d10d.

YOUR ROLE: given in the prompt that sent you here.

MUST NEVER HAPPEN:
- A user with no API key cannot get a working local transcript, or is shown an API-key warning on the local path.
- Parakeet output is written for audio in a language Parakeet does not cover, without the switch, a note, or a loud failure.
- An existing user's provider, model or quality changes without their choice.
- A feature exists on one surface only (CLI vs Web UI vs MCP).
- Owner data (personal file names, paths, transcript text) lands in the public repo.

BUDGET: round 3 of at most 3 (the cap, after an approved resize to L and a diagnosis); about 30 minutes.

ROUND 2: findings.md holds every earlier report verbatim and review-log.md the
lead's verdicts; the fix proofs are in proof.md. DELTA:
~/.review-runs/2026-11-19-local-first-parakeet/delta-r3.patch
(`git diff 8c5d10d..5551230`, minus the rebuilt web/static bundle and
regenerated landing/docs). Read the changes first, trace anywhere you need to.
Check that each fix is real (read the code, probe it, try to break it), and
look for anything new, especially problems the fixes introduced. This is the FINAL re-check: name the migration and integration risks of the
round-3 design (server-owned choose, runnable(), the set_value guard, the
download worker now a plain thread instead of the event loop's executor,
in-memory pending default, config written from background threads, an
existing v0.18.3 user upgrading with a non-runnable default saved, scripts
that run `config set local_model X` before pulling). Concrete inputs to try:
two choose calls in quick succession; choose while the setup thread downloads
the same repo; a helper download that fails after the weights finish; reload
during a pending choice; `config set local_model parakeet-v3` with only the
weights cached; detection [("en",0.9),("ja",0.3)] and [("hi",0.2)] with and
without Whisper ready; the wizard with Parakeet pre-installed choosing "A mix".

LEAD EVIDENCE (re-derive what you can):
1. Full suite on 5551230: 894 passed, 4 skipped; `ruff check src tests` clean.
2. Mac (Apple M1 Pro) on 8c5d10d (round-3 changes are UI/choice/routing, not
   the engine load): fresh keyless onboard with parakeet-v3 ok; 70 s English
   clip 7 s wall clock; Hindi with no Whisper -> actionable error, nothing written.
3. Lead rulings on the fixer's open calls: set_value guards only a CHANGE
   (re-saving the current, never-downloaded default such as a fresh config's
   `base` is allowed); the download worker as a plain thread is accepted
   subject to your thread-safety check.
4. R2C6/R2F6: the remaining hits for the scratch prefix are the reviewers'
   own quoted grep commands (findings.md, report-opus-r2.md); the lead
   accepts those as verbatim record.

LENS: lens.md (Code PR + Screen packs), every line.

YOU MAY RUN: read-only commands (git log/diff/show, grep, cat, python -c that
imports and inspects without writing). YOU MAY NOT: run tests, builds,
servers, installs, downloads, or anything that writes. Name any check you
could not run as an exact command.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round-2 finding (R2C1..R2C7, R2F1..R2F8) and the diagnosis's four extra cases as FIXED / PARTLY / NOT FIXED /
   DECLINED-OK, one line of evidence each; then NEW defects the fixes introduced.
3. Findings, most severe first, numbered with your prefix (R3C1.. for
   correctness, R3F1.. for fit): severity (blocker / should-fix / nit, only
   these words); CONFIRMED or PLAUSIBLE (say what would settle it); where
   (file:line); what goes wrong, as a concrete scenario; the fix.
4. Pending owner checks.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
~~~~~
