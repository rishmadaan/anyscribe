# Target

- Repo: `rishmadaan/anyscribe` (public). The live checkout `~/labs/projects/anyscribe` stays on `main`: do not touch it, do not run git commands in it.
- Base: `main` @ `7ab1539` (v0.19.0) plus the packet commit on branch `feat/onboarding-wave1` (the lead's integration branch, worktree `~/labs/projects/anyscribe-wt/wave1`). Your prompt names the exact base SHA; check `git rev-parse HEAD` and your branch before editing and stop if they differ.
- Builder INSTALL: worktree `~/labs/projects/anyscribe-wt/wave1-install`, branch `feat/onboarding-wave1-install`.
  - In scope: `install.sh`, `install.ps1`, `landing/index.html`, `landing/docs/**` (regenerated only), `docs/user/**`, `docs/building/**`, `src/anyscribe/skill/**` (docs only), `CHANGELOG.md`, `BACKLOG.md`, `README.md` only if a statement there becomes false.
  - Proof file: `docs/reviews/2026-11-20-onboarding-wave1/proof-install.md`.
- Builder APP: worktree `~/labs/projects/anyscribe-wt/wave1-app`, branch `feat/onboarding-wave1-app`.
  - In scope: `src/anyscribe/**` except `skill/` (Python), `ui/src/**`, `src/anyscribe/web/static/**` (rebuilt from `ui/` only), `tests/**`.
  - Proof file: `docs/reviews/2026-11-20-onboarding-wave1/proof-app.md`.
- Must not change (either builder): `src/anyscribe/core/tailnet.py`, the web app's Host check and other security middleware in `src/anyscribe/web/app.py`, the version in `pyproject.toml` and `src/anyscribe/__init__.py`, `.github/`, `scripts/release.sh`, transcription behaviour of any provider (W4 changes only how a no-credit error is classified and worded), anything the other builder owns, anything outside the spec's items.
- Test folders: `tests/` (pytest). Delete or weaken no existing test; where a test encodes behaviour the spec changes (for example the old Groq "API key is set" message), update it and list it in your proof file.
- Owner data: never read or print `~/.anyscribe/.env` or any key; never run anything against the owner's real `~/.anyscribe` or `~/anyscribe`. Every real run uses `HOME=<a new empty folder under ~/.review-runs/2026-11-20-onboarding-wave1/>` and a spare port (APP: 8491 to 8499) with `--local-only`. The owner's own anyscribe server and tray may be running on this machine (port 8457 and up): never stop, restart or touch them. Stop only processes you started, by a pid whose command line you have read; never by pattern.
- Screenshots and run logs go in `~/.review-runs/2026-11-20-onboarding-wave1/screens/` (outside the repo). Never commit screenshots.
- Disk is tight (about 6 GB free on this machine). Keep each builder under about 2 GB: delete model downloads and throwaway homes when your proof is written; remove every Docker container and image you created, by ID.
- Python: make your own venv in your worktree (`uv venv` then `uv pip install -e ".[dev,mcp]"`; it is gitignored). Node: `cd ui && npm ci && npm run build` per `ui/package.json`.
- Commit after each item on your own branch only, in the repo's message style, each message ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not push, do not open a PR, do not merge (the lead does).
