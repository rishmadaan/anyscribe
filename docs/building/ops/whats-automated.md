---
type: reference
tags: [automation, updater, doctor, internals, maintenance]
tldr: "What the app already handles automatically — update detection, self-update, install type detection, doctor checks — and what remains manual."
---

# What's Automated vs Manual

This doc explains what anyscribe already does automatically behind the scenes, so you know what's handled and what needs your attention.

---

## Automated: Self-Update System

**File:** `src/anyscribe/core/updater.py`

The app has a built-in self-update system that users interact with via `anyscribe update`.

### Install Type Detection

The updater auto-detects how the user installed the app:

- **Git install** — if the package directory lives inside a `.git` repo (developer workflow, editable installs)
- **Pip install** — everything else (standard user installs from PyPI or `git+https://`)

Detection is fully automatic. No config needed.

### What `anyscribe update` Does

**For git installs:**
1. Checks for uncommitted changes (aborts if found, unless `--force`)
2. With `--force`: stashes local changes first
3. Runs `git fetch` → `git pull --rebase`
4. Reinstalls with `pip install -e .`
5. Reads new version from disk (Python caches the module, so re-import wouldn't work)
6. Reports old → new version

**For pip installs:**
1. Runs `pip install --upgrade anyscribe` (tries PyPI first)
2. If PyPI fails: falls back to `git+https://github.com/rishmadaan/anyscribe.git`
3. Spawns a subprocess to read the new version (avoids module cache)
4. Reports old → new version

### What `anyscribe update --check` Does

Checks for available updates **without installing**:

- **Git:** fetches remote, checks `git log HEAD..origin/main` for new commits, reads remote `__init__.py` for version
- **Pip:** runs `pip index versions anyscribe` to check PyPI for latest

### Timeouts

All operations have timeouts to prevent hanging:

| Operation | Timeout |
|-----------|---------|
| `git fetch` | 30s |
| `git log`, `git show`, `git status` | 10s |
| `git pull --rebase` | 60s |
| `pip install` / `pip upgrade` | 120s |
| Version read subprocess | 10s |

---

## Automated: Doctor Command

**File:** `src/anyscribe/cli/main.py`

`anyscribe doctor` runs a health check that includes:

- Dependency checks (yt-dlp, ffmpeg, etc.)
- Config validation
- Workspace integrity
- **Silent update check** — calls `check_for_updates(quiet=True)`, only prints if an update is available

This is the only place the app checks for updates without the user explicitly running `anyscribe update`.

---

## Automated: Version Display

`anyscribe --version` (or `anyscribe -v`) reads from `src/anyscribe/__init__.py:__version__` and prints it.

---

## Automated: PyPI Publishing

**File:** `.github/workflows/publish.yml`

When you push a tag matching `v*`, GitHub Actions runs these steps in order. A failure in steps 1 to 7 stops the release before anything reaches PyPI; step 9 runs after the upload, so if it fails the package is live and only the GitHub Release is missing (see release-checklist step 6):
1. Lints (`ruff check src tests scripts`) and runs `pytest`, with the `[dev,mcp]` extras installed
2. Rebuilds the frontend (`npm ci`, `npm run lint`, `npm run build`) and checks the committed bundle in `src/anyscribe/web/static` is current
3. Runs `scripts/check-docs.py` (version and capability drift gates)
4. Renders the docs (`scripts/build-docs.py`) and checks `git diff --exit-code landing/docs`
5. Rehearses the app-home migration (`scripts/rehearse-migration.sh`)
6. Builds the package (`python -m build`)
7. Verifies the tag matches `pyproject.toml` version (fails if mismatched)
8. Publishes to PyPI via trusted publishing (no API token in secrets needed after setup)
9. Creates the GitHub Release with generated notes (`gh release create --generate-notes`)

**Setup (one-time):** Configure trusted publishing on [pypi.org](https://pypi.org/manage/project/anyscribe/settings/publishing/) — add GitHub as a trusted publisher with repository `rishmadaan/anyscribe`, workflow `publish.yml`.

### Release Script

**File:** `scripts/release.sh`

One command to bump + commit + tag + push:
```bash
./scripts/release.sh X.Y.Z "description of changes"
```

Replace X.Y.Z with the next unused version under the versioning policy in CLAUDE.md.

Includes safety checks: clean working tree, semver format, no duplicate tags, branch warning.

---

## Automated: CI Checks

GitHub Actions runs lint, tests, and package build on pushes to `main` and pull requests. It also rebuilds the frontend and verifies the committed `src/anyscribe/web/static/` bundle is current. It also runs a fake-HOME migration rehearsal (`scripts/rehearse-migration.sh`) and a docs job (renders `docs/user` with `scripts/build-docs.py`, then `scripts/check-docs.py`).

---

## Automated: GitHub Releases

**GitHub Releases:** the publish workflow creates a release with generated notes for every `v*` tag.

---

## NOT Automated (You Do These Manually)

### Documentation Updates

Doc *content* is manual. CI enforces: rendered `landing/docs` HTML matches `docs/user`, no stale version strings, every MCP tool in `agents.md`, and a `CHANGELOG.md` entry for the shipped version.

The `COMMIT_CHECKLIST.md` covers the rest; your discipline enforces it.

---

## What Users Experience

From a user's perspective, the update flow is:

```
anyscribe doctor          # Tells them if an update is available (passively)
anyscribe update --check  # Explicitly check
anyscribe update          # Install the update
anyscribe --version       # Verify
```

anyscribe itself updates only when requested. Before YouTube or Instagram downloads it checks the installed yt-dlp release date and runs a pip upgrade if that release is more than 60 days old (core/deps.py). `anyscribe doctor` and `anyscribe update --check` also check the update source for a newer anyscribe. The bundled Claude Code skill refreshes itself when its installed version differs. There is no telemetry.

---

## Future Automation Candidates

Things that could be automated but aren't yet:

| What | How | Priority |
|------|-----|----------|
| Version sync check | Pre-commit hook comparing `__init__.py` with `pyproject.toml` (publish already checks tag vs `pyproject.toml`; `check-docs.py` catches doc drift) | Medium |
| Changelog generation | From git tags/commits | Low |
| Startup update notification | Opt-in check on `anyscribe` launch with TTL | Low |
