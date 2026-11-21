# Target

- Repo: ~/labs/projects/anyscribe, base commit 7ab1539 (main, v0.19.0). Your worktree is ~/labs/projects/anyscribe-wt/mac-engine on branch feat/mac-app-engine; commit there only, never on main, never push.
- In scope: src/anyscribe/cli/main.py, src/anyscribe/core/updater.py, src/anyscribe/core/local_setup.py, src/anyscribe/web/app.py, src/anyscribe/web/jobs.py, src/anyscribe/web/routes/transcribe.py (or a new route module), src/anyscribe/core/orchestrator.py (the title data only), a new small helper module, tests/, docs/building/ (architecture.md, journal, _index.md).
- Must not change: ui/ and src/anyscribe/web/static/ (another session's onboarding work is changing the UI right now), install.sh, install.ps1, src/anyscribe/web/routes/config.py, src/anyscribe/core/errors.py, src/anyscribe/cli/onboard.py, pyproject.toml version, CHANGELOG.md, BACKLOG.md.
- Test folder: tests/ (add tests; do not delete or weaken existing ones).
- Packet: this folder (docs/reviews/2026-11-20-mac-app-engine-hooks/) is already in your worktree, uncommitted; commit it as your first commit and write proof.md there.
- Review target: branch feat/mac-app-engine at 2dd8e64c9f02360f03aa89215f1bb829654eb778, diff 7ab1539..2dd8e64 (worktree ~/labs/projects/anyscribe-wt/mac-engine).
- Lead evidence at that sha: `.venv/bin/python -m pytest -q` 946 passed, 6 skipped; `ruff check src tests scripts` all passed; `scripts/check-docs.py` exit 0.
