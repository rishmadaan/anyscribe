**CONDITIONAL on successful CI for `e4fd0707c6b9490ccd7d8848981d5837bfa74ebe`, including Python 3.14, frontend bundle verification, and documentation checks.**

No new defects found in the round-three fixes. The PR is an appropriate infrastructure update for the requested audit. Its six changed files cover installers, dependency constraints, release checks, and the installer regression test.

**Earlier findings**

| Finding | Status | Evidence |
|---|---|---|
| Round 2 Astra I1: skipped launch still says “ready” | **FIXED** | `install.sh:365` sets `POST_INSTALL_SKIPPED`; line 410 checks it; lines 419 and 429 report installation and the skipped launch. Independently reproduced. |
| Round 2 Opus I1: unexplained missing-pip failure | **FIXED** | `install.sh:283` now exits through `die` with recovery instructions. A stubbed failure returned exit 1 with those instructions. The underlying Python error remains visible, but is no longer the only explanation. |
| Round 2 Opus I2: module fallback versus “anyscribe ui” box | **DECLINED-OK** | The earlier interpreter-specific hint remains at `install.sh:347`. The brief explicitly accepts the remaining mismatch. |
| Round 2 Opus I3: apt install without refreshing indexes | **FIXED** | `install.sh:280` runs `apt update -qq` before installation. Stubbed calls confirmed the order. |
| Round 1: pipx launch uses the wrong interpreter | **FIXED** | `install.sh:361` resolves pipx’s executable; lines 379 and 388 invoke the quoted command array. |
| Round 1: missing-pip route | **FIXED** | `install.sh:310` detects missing pip and enters `install_with_pipx`. Package-manager installation no longer depends on pip being present. |
| Round 1: hardcoded Python PATH hint | **FIXED** | `install.sh:335` queries the selected interpreter and checks for an executable before recommending its directory. |
| Round 1: missing publish gates | **FIXED** | `publish.yml:30–66` includes MCP dependencies, scripts linting, documentation checks, and migration rehearsal before publishing at line 80. |
| Round 1: box widths | **FIXED** | Both installers have 37-character box interiors after accounting for shell-escaped quotation marks. |
| Round 1: building documentation | **DECLINED-OK** | Assigned to PR #19 by the brief; not reopened here. |

**Reproduction and regression-test assessment**

I ran no-write shell probes using the actual extracted installer functions, with installation commands replaced by stubs:

| Input | Observed result |
|---|---|
| `RUN_UI=true`, pipx used, executable absent | Exit 0; skip explanation; “installed” box; no “ready” |
| `RUN_ONBOARD=true`, same missing executable | Same correct result |
| Neither action requested | `run_post_install` returns 0 with no output; `main` prints “installed” |
| Banner guard reverted in memory | “ready” reappears, violating the regression assertion |

The executable-present pipx branch was **traced, not launched**: it passes `ui` or `onboard --skip-deps` to the executable found in pipx’s bin directory.

`tests/test_install_sh.py:40` tests the right failure. It keeps the real launch-selection and banner logic while stubbing installation. Its assertion fails when the old banner condition is restored. It does not cover onboarding, successful launch, or require the replacement “installed” box; those are coverage limits, not evidence that the existing test is ineffective.

`bash -n install.sh` and `git diff --check` also passed.

**Answers to the brief**

- **Installer branches:** The supported package-manager routes are coherent by inspection. Python is resolved again after installation; missing ffmpeg/ffprobe enters the dependency-install route; pipx is installed when necessary. This is not evidence that every fresh macOS/Linux installation succeeds. Actual package-manager availability, permissions, downloads, and installed executable locations were not exercised.
- **PATH handling:** The code checks the interpreter’s default scripts directory before its user directory, so a venv is not automatically given a user-install PATH recommendation. Pipx installations bypass this probe. Python 3.10 execution remains untested here.
- **Commands and aliases:** `anyscribe ui`, `anyscribe onboard --skip-deps`, `anyscribe --version`, and the bare-URL form match the CLI declarations and routing. `scribe` and `ascli` remain entry-point aliases in `pyproject.toml:83`.
- **PowerShell:** The edited function declaration and call agree. The changed strings preserve balanced quoting and introduce no backtick or here-string syntax. This was a textual check, not a PowerShell parser run.
- **Release ordering:** All added gates precede PyPI publishing and GitHub Release creation. The migration rehearsal itself installs into a temporary environment; it is not a read-only check.
- **Python 3.14:** CI installs `.[dev,mcp]`, not `[local]`. The declared installation path therefore does not request faster-whisper or its CTranslate2 dependency. This removes that particular compatibility concern, but does not prove the remaining dependency graph passes.
- **Dependency constraints:** No contradictory constraint appears in `pyproject.toml`. Onboarding visibly handles `bselect(...) is None` as a default choice. The upstream claims about beaupy 4.0.1, its Rich requirement, and python-multipart’s advisory boundary were not independently verified.
- **GitHub Actions:** The audit reports that the v7 tags exist. Network access was prohibited, so I cannot independently certify those tags or their input definitions from this review.

**Pending owner checks**

None required for the reviewed fixes. CI verification and upstream metadata checks belong to the lead, not the owner. The Deno and Python 3.10 support decisions remain outside this PR.

**Checks not run and inspection limits**

The brief prohibited pytest, builds, installs, servers, and network calls. The implementer’s “485 passed, 1 skipped” remains their reported result.

The lead can verify this exact commit’s checks with:

```bash
gh api --paginate 'repos/rishmadaan/anyscribe/commits/e4fd0707c6b9490ccd7d8848981d5837bfa74ebe/check-runs?per_page=100' --jq '.check_runs[] | {name,status,conclusion,head_sha,html_url}'
```

Local checks, from the supplied checkout:

```bash
pytest tests/test_install_sh.py -q
pytest
ruff check src tests scripts
python scripts/check-docs.py
python scripts/build-docs.py
git diff --exit-code -- landing/docs
npm --prefix ui ci
npm --prefix ui run lint
npm --prefix ui run build
git diff --exit-code -- src/anyscribe/web/static
python -m build
bash scripts/rehearse-migration.sh
```

For upstream action definitions:

```bash
gh api 'repos/actions/checkout/contents/action.yml?ref=v7' -H 'Accept: application/vnd.github.raw+json'
gh api 'repos/actions/setup-python/contents/action.yml?ref=v7' -H 'Accept: application/vnd.github.raw+json'
gh api 'repos/actions/setup-node/contents/action.yml?ref=v7' -H 'Accept: application/vnd.github.raw+json'
```

Clean-machine installation commands, only in disposable environments:

```bash
bash ./install.sh --ui
bash ./install.sh --onboard
```

On Windows:

```powershell
powershell -NoProfile -File .\install.ps1
```

Inspected the brief, saved diff, audit, implementer report, all six changed files, release and documentation scripts, CHANGELOG and BACKLOG, and relevant CLI/dependency/upload paths. All Python files matched by the brief’s source patterns were read through an AST syntax/import/surface scan; detailed tracing focused on the changed behavior. Bundled skill text and its copy mechanism were also inspected. This was not an exhaustive correctness audit of every unchanged provider and route.

No files were edited or deleted, and no real installer, server, or publication action was run.