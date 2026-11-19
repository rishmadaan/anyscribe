Copied from the review run folder; absolute home-folder paths rewritten as ~ paths and the lead's scratch path masked; the byte-exact original stays in ~/.review-runs/2026-11-19-local-first-parakeet/.

~~~~~
You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names (and the code it points
to). Test folders, leave them alone: ~/labs/projects/anyscribe-wt/local-first/tests.

THE PACKET, in ~/labs/projects/anyscribe-wt/local-first/docs/reviews/2026-11-19-local-first-parakeet/ :
ask.md (the owner's ask, in his words), spec.md, target.md, lens.md,
findings.md (every round-1 report verbatim), review-log.md (the lead's verdict
on each finding: the ledger), fix-plan-r1.md (the lead's binding choices for
the fixes), proof.md (the builder's proof, then "## Round 1 fixes": one entry
per finding; claims to check, not facts). Declined list (SETTLED, DO NOT
REOPEN): ~/labs/projects/anyscribe-wt/local-first/docs/reviews/declined.md

TARGET (frozen): worktree ~/labs/projects/anyscribe-wt/local-first,
branch feat/local-first-parakeet, commit 8c5d10d. Last reviewed commit 87dbd2f.

YOUR ROLE: given in the prompt that sent you here.

MUST NEVER HAPPEN:
- A user with no API key cannot get a working local transcript, or is shown an API-key warning on the local path.
- Parakeet output is written for audio in a language Parakeet does not cover, without the switch, a note, or a loud failure.
- An existing user's provider, model or quality changes without their choice.
- A feature exists on one surface only (CLI vs Web UI vs MCP).
- Owner data (personal file names, paths, transcript text) lands in the public repo.

BUDGET: round 2 of at most 2 (the cap); about 30 minutes.

ROUND 2: findings.md holds every earlier report verbatim and review-log.md the
lead's verdicts; the fix proofs are in proof.md. DELTA:
~/.review-runs/2026-11-19-local-first-parakeet/delta-r2.patch
(`git diff 87dbd2f..8c5d10d`, minus the rebuilt web/static bundle and
regenerated landing/docs). Read the changes first, trace anywhere you need to.
Check that each fix is real (read the code, probe it, try to break it), and
look for anything new, especially problems the fixes introduced. Concrete
inputs to try: a recording whose middle window is Hindi but start and end are
English; a 5-second clip; a clip that is all silence; tiny cached but VAD
missing; a Parakeet default chosen via `anyscribe config set local_model
parakeet-v3` on a machine with no tiny; a stale `.incomplete` blob next to a
complete snapshot; the wizard's "A mix" path when Turbo is already downloaded;
the restart banner after a setup that changed nothing; batch of three files
where the second switches to Whisper.

LEAD EVIDENCE (the lead ran these after the fixes; re-derive what you can):
1. Full suite on 8c5d10d: 862 passed, 4 skipped; `ruff check src tests` clean.
2. Mac (Apple M1 Pro), branch 8c5d10d installed from `git archive` into a
   throwaway venv, throwaway HOME/HF_HOME, no keys: `onboard --yes --provider
   local --local-model parakeet-v3` -> onboarded, set_up, default parakeet-v3;
   `transcribe english-1.wav --json` (70 s) -> success, model parakeet-v3,
   notes [], 7 s wall clock including process start, model load and language
   check (round 1 code: 110 s model load alone); `transcribe hindi-1.wav` with
   only parakeet+tiny cached -> success false, "Detected Hindi, which Parakeet
   v3 doesn't cover, and no Whisper model to use instead is downloaded.
   Download Whisper Large v3 Turbo: `anyscribe model pull large...", nothing written.
3. Lead accepted the fixer's wording deviation in C8: "about 4 times faster on
   our test desktop" (the sentence sits above the cards).

LENS: lens.md (Code PR + Screen packs), every line.

YOU MAY RUN: read-only commands (git log/diff/show, grep, cat, python -c that
imports and inspects without writing). YOU MAY NOT: run tests, builds,
servers, installs, downloads, or anything that writes. Name any check you
could not run as an exact command.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every earlier finding (C1..C11, F1..F10) as FIXED / PARTLY / NOT FIXED /
   DECLINED-OK, one line of evidence each; then NEW defects the fixes introduced.
3. Findings, most severe first, numbered with your prefix (R2C1.. for
   correctness, R2F1.. for fit): severity (blocker / should-fix / nit, only
   these words); CONFIRMED or PLAUSIBLE (say what would settle it); where
   (file:line); what goes wrong, as a concrete scenario; the fix.
4. Pending owner checks.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
~~~~~
