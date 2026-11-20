# Proof: onboarding wave 1, integration branch feat/onboarding-wave1, 2026-11-20

Two builders worked in parallel on disjoint files; their full proofs are beside this file and are part of this proof:

- `proof-install.md`: builder INSTALL (Claude Opus 5.5, Agent tool, lead-made worktree; W1, W2, W3 installer half, W7, docs and records). Branch `feat/onboarding-wave1-install`, tip `1b21839`.
- `proof-app.md`: builder APP (Claude Opus 5.5, Agent tool, lead-made worktree; W3 wizard half, W4, W5, W6, W8). Branch `feat/onboarding-wave1-app`, tip `9bd08b7`.

Lane note: the T3 child lane could not run (registering the code repo as a T3 project was refused: "Changing projects or environment settings needs a live full-access/default calling thread"), so the lead made the worktrees with `git worktree add` and ran the builders through the Agent tool, the lane this repo used on 2026-11-19.

## Integration (lead)

- Merged INSTALL (`d92be63`) then APP (`53356fd`) into `feat/onboarding-wave1`; no conflicts (disjoint files).
- Lead-made change (wording only, both builders flagged it): S3e said "Saved, not checked" while the wizard saves the key only at Finish. Reworded to "Not checked yet: Sarvam has no way to check a key in advance. It will be checked on your first transcript." in `web/routes/config.py`, its test, `docs/user/troubleshooting.md`, `docs/user/getting-started.md`, the skill's troubleshooting reference, CHANGELOG, the journal entry and `_index.md`; `landing/docs` regenerated. 10 files, 10 lines each way.

## What was run on the integrated tree (after the lead change)

- `ruff check src tests scripts`: All checks passed!
- `pytest -q`: 926 passed, 6 skipped (the APP builder's 927/5 included one local-engine test its venv could run; this fresh venv has no local engines).
- `cd ui && npm ci && npm run lint && npm run build`: lint clean; build emits `index-HNoFjoKn.js`, identical to the committed bundle; `git status` shows no change under `src/anyscribe/web/static`.
- `python scripts/build-docs.py` then `python scripts/check-docs.py`: exit 0.
- `bash -n install.sh`: ok.

## Not proven anywhere in this round

- A real Mac (W1 was proven with Homebrew's Linux installer, which has the same non-interactive check) and real Windows / PowerShell 5.1 (W3 and W7 Windows parts were run in Linux PowerShell 7 only; winget and the registry PATH refresh could not run there).
- The desktop-mode "click the app" box after a real desktop install (shown with `--dry-run` only; containers have no display).
