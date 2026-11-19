Copied from the review run folder; absolute home-folder paths rewritten as ~ paths and the lead's scratch path masked; the byte-exact original stays in ~/.review-runs/2026-11-19-local-first-parakeet/.

~~~~~
You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names (and the code it points
to). Test folders, leave them alone: ~/labs/projects/anyscribe-wt/local-first/tests.

THE PACKET, read all of it first, in
~/labs/projects/anyscribe-wt/local-first/docs/reviews/2026-11-19-local-first-parakeet/ :
ask.md (the owner's ask, in his words; the first question is whether this is
the job he asked for and the right instrument for it; if the brief, the goal
or the spec is wrong, say so instead of reviewing around it), spec.md,
target.md, proof.md (what the builder ran and saw: claims to check, not
facts), lens.md, mockup.html (the design the owner approved), and the screenshots in ~/.review-runs/2026-11-19-local-first-parakeet/screens/ (fx-*.png are after the fixes; the rest are round 1)
(the builder's screenshots). Declined list (SETTLED, DO NOT REOPEN; empty so
far): ~/labs/projects/anyscribe-wt/local-first/docs/reviews/declined.md

TARGET (frozen): repo worktree ~/labs/projects/anyscribe-wt/local-first,
branch feat/local-first-parakeet, commit 8c5d10d (after round-1 fixes;
findings.md and review-log.md hold round 1). Diff under review: `git -C <worktree> diff b2bafa7..8c5d10d`
(base b2bafa7 = main, v0.18.3). target.md's "c3e8105" was the build's start.

YOUR ROLE: given in the prompt that sent you here.

MUST NEVER HAPPEN:
- A user with no API key cannot get a working local transcript, or is shown an API-key warning on the local path.
- Parakeet output is written for audio in a language Parakeet does not cover, without the switch or a loud failure.
- An existing user's provider, model or quality changes without their choice.
- A feature exists on one surface only (CLI vs Web UI vs MCP).
- Owner data (personal file names, paths, transcript text) lands in the public repo.

BUDGET: round 2 of at most 2 (you rejoin because the fixes changed what the owner sees); about 30 minutes. Mark each round-1 F finding FIXED / PARTLY / NOT FIXED first.

LEAD EVIDENCE (the lead ran these; treat as evidence, re-derive what you can):
1. Mac (Apple M1 Pro, macOS 26.6, onnxruntime from onnx-asr 0.12.0): loading
   parakeet-v3 int8 + silero with onnx-asr DEFAULT providers picks
   CoreMLExecutionProvider (partial support: "number of partitions supported by
   CoreML: 319") -> load 110.6 s, transcription 3.1x realtime on a 70 s clip.
   With providers=["CPUExecutionProvider"]: load 0.9 s, 23.6x realtime, same
   text. The branch's src/anyscribe/providers/local.py loads with defaults
   (line ~120). An earlier full Parakeet bench on that Mac died with no result
   under the default provider. Same Mac: Whisper large-v3-turbo 3.2x, small 6.2x.
2. The builder's screenshot screens/result-note-1440.png (throwaway HOME, no
   keys) shows, under a successful local transcript, "WARNING: quality
   'balanced' wants deepgram but no DEEPGRAM_API_KEY is set - using local
   instead". Find where that config came from and whether a real key-free user
   on the new wizard/onboard path can reach it.
3. Picker cards state "1 hour of audio ≈ 10 min" etc. These are from one Linux
   desktop (i5-10600K, CPU only); the Mac does Parakeet at ~2.5 min/hour.
   Judge whether the screen claims more than it knows.
4. Full suite on 87dbd2f: `pytest -q` -> 831 passed, 4 skipped; `ruff check src tests` clean.

LENS: read lens.md (Code PR + Screen packs) and apply every line. Also: the
Every-review basics: is anything claimed in docs/CHANGELOG/journal beyond what
the code does; anything left half-done; anything the owner would object to.

YOU MAY RUN: read-only commands (git log/diff/show, grep, cat, python -c that
imports and inspects without writing, reading the HF cache listing). YOU MAY
NOT: run tests, builds, servers, installs, downloads, or anything that writes.
Name any check you could not run as an exact command.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Findings, most severe first, numbered with your prefix (R2C1.. for
   correctness, R2F1.. for fit): severity (blocker / should-fix / nit, only these
   words); CONFIRMED (you reproduced or traced it) or PLAUSIBLE (you did not;
   say what would settle it); where (file:line); what goes wrong, as a concrete
   scenario; the fix.
3. Answers to any questions in this brief (advice, not findings).
4. Pending owner checks: things only the owner can confirm.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
~~~~~
