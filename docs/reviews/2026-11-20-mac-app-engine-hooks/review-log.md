# Review log: anyscribe Mac app, phase 2a engine hooks
Size: L
Sized because: changes a security boundary (HostCheck gains an Origin check on every HTTP and WebSocket request)
Cap: 5 (security and data loss: the Origin check and transcript writes)
Packet: v1

| Round | Role | Model, effort | Lane | Target (sha/version) | Verdict | Raised | Upheld | Minutes | Fixer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | correctness | gpt-6.1-sol, high | Codex | 2dd8e64 | NOT YET | 6 | 6 | 6 | opus (Agent tool, the builder) |
| 1 | fit | claude-opus-5-5, high | Claude (Agent tool; ran with this session's instruction files and hooks) | 2dd8e64 | CONDITIONAL | 4 | 4 | 5 | opus (Agent tool, the builder) |
| 2 | correctness (re-check, the one Astra pass) | gpt-6-astra, high | Codex | 2b1c2bc | NOT YET | 4 | 4 | 6 | opus (Agent tool, the builder) |
| 3 | correctness (re-check after diagnosis) | gpt-6.1-sol, high | Codex | 4d9bb42 | NOT YET | 2 | 2 | 7 | opus (Agent tool, the builder) |
| 4 | correctness (re-check after the second diagnosis) | gpt-6.1-sol, high | Codex | 4470a4d | GOOD TO GO | 0 | 0 | 4 | none |

| Id | Round | Reviewer | Severity | Lead verdict | Evidence | Also raised by |
|---|---|---|---|---|---|---|
| C1 | 1 | sol | blocker | UPHELD | web/app.py hard exit can land mid-write; vault/writer.py:138 writes the final path directly; dedup.py:32 accepts a file once its source line matches | F1 (opus noted the same write, not traced) |
| C2 | 1 | sol | blocker | UPHELD | jobs.py summaries() caps the newest 50 regardless of status; reproduced: a running job hidden behind 50 finished ones | F1 |
| F1 | 1 | opus | should-fix | UPHELD | jobs.py:17 JOB_TTL_SECONDS 3600 drops finished jobs the menu promises to keep until the window opens | C2 |
| C3 | 1 | sol | should-fix (lead lowered from blocker: reachable only through the app's Terminal command, which exists only after the Terminal switch already installed the skill) | UPHELD | cli/onboard.py:939 copy_skill_files without an app-mode check | |
| C4 | 1 | sol | should-fix | UPHELD | web/app.py: share.close() (two tailscale calls, 10 s timeouts each) runs before the 10 s clock starts; a failing print skips the hard exit | |
| C5 | 1 | sol | should-fix | UPHELD | reproduced: http://127.0.0.1:80@evil.example accepted (netloc then a colon split); a second Origin header ignored. Not browser-reachable (browsers send a serialized origin), still wrong | |
| C6 | 1 | sol | should-fix | UPHELD | os._exit leaves child processes (pip, yt-dlp, ffmpeg) running on POSIX | |
| F2 | 1 | opus | should-fix | UPHELD | updater._pip_update and local_setup install into sys.executable's site-packages without app mode; the Terminal command must carry the app environment | |
| F3 | 1 | opus | nit | UPHELD | cli/main.py ui rolls forward to the next port; in app mode it should refuse | |
| F4 | 1 | opus | nit | UPHELD | tests/test_engine_process.py docstring vs fixture env; Windows claims not run | |
| A1 | 2 | astra | blocker | UPHELD | core/fileutil.py:45 os.write result ignored; reproduced 49 of 404 bytes published and dedup accepting it | |
| A2 | 2 | astra | should-fix | UPHELD | graceful exit path (server.run returns) never signals owned children; model worker's pip child survives | |
| A3 | 2 | astra | nit | UPHELD | test decodes cp1252 output as UTF-8 | |
| A4 | 2 | astra | nit | UPHELD | Origin port regex allows 65536 to 99999 | |
| R1 | 3 | sol | should-fix | UPHELD | fileutil.py: the temp file is created at umask default and chmodded to the target's private bits only after write and fsync; traced order open, write, flush, fsync, chmod, replace | |
| R2 | 3 | sol | should-fix | UPHELD (transferred to the shell review, its round 3 design item 3) | desktop/src/engine.js _exitedEarly skips the group kill before readiness | |

Round 2 plan: correctness re-check only (the one Astra pass). Fit does not rejoin: the round 1 fixes change no screen and nothing the owner does; F3 (strict port) changes only what the shell sees.

Round 2 snapshot note: only gitignored __pycache__ files in src changed during the round (the shell fixer's e2e imports this tree read-only through PYTHONPATH); git status clean; the reviewed sources are unchanged.

Round 2 not clean (A1 blocker, A2 should-fix UPHELD). At L, round 3 starts with a diagnosis read (independent-review step 7).

Cap corrected from 3 to 5 (independent-review step 1: L reviews in the security and data-loss classes cap at 5; this one touches both). Diagnosis read before round 3: diagnosis-r3.md (claude-fable-5-2). Lead's choice written into spec.md, section "Round 3 design".

Round 3 plan: correctness re-check after the diagnosis (Sol, high); the brief names the migration and integration risks. Fit does not rejoin: no screen or owner action changes.

Round 3: A1 to A4 FIXED; follow-up 2 FIXED; follow-up 1 PARTLY (R1). Not clean (R1). Round 4 starts with a diagnosis read (risk class: security and data loss).

Round 4 plan: correctness re-check after the second diagnosis (Sol, high). Fit does not rejoin.

Round 4 clean: R1 FIXED; no new finding. Review closed at 4470a4d (code); review files after it.

Residue for Rishabh to pick (limits named by the reviewers, none a defect against the spec): an interrupted pip install in the add-ons folder has no recovery proof (check before packaging release); on Windows the hard exit ends only the engine, not its children; a Tailscale rule can remain after an abrupt death or a cleanup failure; fsync cost is unmeasured; a hard kill can leave a hidden partial .tmp in the vault (never published, no scavenger).

Relay note: the fit seat was a Claude-lane reviewer (claude-opus-5-5) that ran with this session's instruction files and hooks loaded; correctness seats were GPT (Sol rounds 1, 3, 4; Astra round 2).

## Cost (phlinux, 2026-11-20 18:02)

| Round | Codex runs | Codex tokens used | Codex minutes | Claude agents | Claude fresh+out tokens | Claude minutes |
|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0.0 | 1 | 1,326,213 | 243.2 |
| 1 | 1 | 195,570 | 6.0 | 1 | 165,911 | 5.3 |
| 2 | 1 | 174,463 | 5.9 | 0 | 0 | 0.0 |
| 3 | 1 | 210,393 | 6.4 | 1 | 152,316 | 3.1 |
| 4 | 1 | 144,941 | 3.8 | 1 | 78,876 | 1.2 |

A round run on the other machine is added by running this there. Claude usage counted once per message id; Codex tokens are the last figure Codex prints. A duration shown as ? could not be measured (no rollout file or no timestamps): unknown, not zero. Codex children in T3 and anything on the other machine are not counted here. The lead's own tokens are not separable and are not counted.
