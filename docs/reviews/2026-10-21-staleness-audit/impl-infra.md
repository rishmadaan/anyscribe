# Implementer report: audit/infra (commits 4882e83, 5ab8825, 981a7eb)

Worktree: <checkout>

Five of six findings applied in three commits; fastapi floor declined.

Diff stat: ci.yml 14 lines, publish.yml 16, install.ps1 30, install.sh 55, pyproject.toml 7 (65+, 57-).

Applied:
- #2 beaupy capped `>=3.0,<4` with a two-line comment (beaupy 4.0.1 of 2026-10-15: Ctrl+C raises KeyboardInterrupt where it used to return None; needs rich>=14.3). anyscribe imports only confirm and select, so the select-all key change does not matter.
- #3 publish.yml: installs .[dev,mcp]; lints src tests scripts; new step "Version + capability drift gates" running scripts/check-docs.py, placed after the static-bundle check and before Build package. check-docs.py imports only re, sys, pathlib. release.sh:107 pushes commit and tag together, which is why the gate is needed.
- #4 installers: every `scribe` in install.sh and install.ps1 is now `anyscribe` (headers, help, banners, verify messages, PATH hints, next-step boxes, command_exists / Test-CommandExists checks, install function names). Neither script mentions aliases. Box padding narrowed so borders line up (one pre-existing off-by-one left as is). Post-install fallback is `cmd="$PY -m anyscribe"`. PATH hint now asks `$PY` for `sysconfig.get_path("scripts", sysconfig.get_preferred_scheme("user"))`, falling back to `$HOME/.local/bin`; on this Mac's 3.13 it returns ~/Library/Python/3.13/bin (old hard-coded 3.12 was wrong here). get_preferred_scheme needs 3.10+, already required. install.ps1: only comments, strings and the function name edited.
- #5 actions: checkout, setup-python, setup-node at @v7 in both workflows; v7 tags confirmed via gh api. pypi-publish unchanged.
- #6 CI matrix ["3.10", "3.12", "3.14"]; classifier 3.14 added; 3.10 kept; 3.15 not added.
- #7 partly: python-multipart>=0.0.31 with a one-line comment (OSV: 2 advisories at 0.0.30, 0 at 0.0.31; latest 0.0.32).

Declined: #7 fastapi>=0.115. fastapi 0.110.0 has 0 OSV advisories itself; the risk is Starlette. fastapi 0.115.0 requires starlette>=0.37.2,<0.39.0 and OSV shows 14 advisories against each of 0.36.3, 0.37.2, 0.38.6, so raising to 0.115 removes nothing. Latest Starlette fix is 1.3.1; no fastapi floor reaches it (0.158.0 requires starlette>=0.46.0). The working fix would be a direct `starlette>=1.3.1` dependency, outside the spec; owner's call.

Gate mutation test: baseline check-docs exit 0. With `## 0.16.5` renamed to `## 0.16.4x` in CHANGELOG.md: "CHANGELOG.md: no '## 0.16.5' entry for the version being released", exit 1. Reverted, exit 0, tree clean.

Checks: pip --dry-run resolves (would install python-multipart 0.0.32; beaupy 3.11.0 satisfies). pytest 484 passed, 1 skipped (worktree src confirmed). ruff All checks passed. YAML ok. bash -n ok. shellcheck not installed.

Missed by audit: the shared venv has fastapi 0.136.0, Starlette 1.0.0 (below 1.3.1), and python-multipart older than 0.0.31.

Not checked: GitHub Actions not run (3.14 and v7 actions unverified until pushed); install.ps1 not executed. Scratch scripts in /tmp/anyscribe-infra-fix/.
