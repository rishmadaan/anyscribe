# anyscribe infra audit (read-only, HEAD b3cddc1, v0.16.5)

Read-only Opus audit. Commands run: git, grep, PyPI JSON API, npm view, npm audit (lockfile only), gh api, OSV.dev API, python3 scripts/check-docs.py (exit 0).

## Findings, most severe first

1. MUST FIX (decision for the owner): YouTube downloads may be degraded because the yt-dlp dependency predates its JavaScript-runtime requirement.
   - Where: pyproject.toml:44 (`yt-dlp>=2024.0`), core/deps.py:306 (auto-update runs `pip install --upgrade yt-dlp` with no extras), install.sh, install.ps1, `anyscribe doctor` (none check for Deno).
   - Verified: yt-dlp 2025.11.12 release notes and yt-dlp/yt-dlp#15012: "An external JavaScript runtime is now required for full YouTube support". Deno recommended. Challenge-solver scripts ship as yt-dlp-ejs==0.8.0, pulled only by the `yt-dlp[default]` extra; there is a `[deno]` extra (deno>=2.6.6). anyscribe runs `sys.executable -m yt_dlp` (deps.py:84-96), so it gets neither. No file in src/ or docs/user/ mentions deno, ejs or a JS runtime.
   - Caveat: no download was run; actual failure mode unconfirmed.
   - Recommended: depend on `yt-dlp[default]>=2025.11.12`; add `[deno]` or have doctor and installers check for Deno; make deps.py upgrade the same extras.

2. MUST FIX: beaupy 4 (breaking major) now installs on every fresh install.
   - Where: pyproject.toml:47 (`beaupy>=3.0`, no cap). Used in cli/onboard.py:11 and ~20 call sites.
   - Verified: beaupy 4.0.1 released 2026-10-15 (gh api repos/petereon/beaupy/releases), after the 2026-09-13 clean-install check. Breaking: args after the first keyword-only, global console removed (anyscribe's calls use cursor, cursor_index, cursor_style as keywords, so compatible); Ctrl+C raises KeyboardInterrupt instead of returning None (onboard.py treats None as "use default" at 247, 320, 538, 644, 680, 748, 791, so cancel now aborts); RuntimeError without a TTY; needs rich>=14.3.
   - Same unbounded-major pattern that broke mcp and ruff. Recommended: cap `beaupy>=3.0,<4` with a comment, or test on 4.0.1 and set >=4,<5.

3. MUST FIX: publish workflow skips gates regular CI runs.
   - .github/workflows/publish.yml:26-36: no scripts/check-docs.py (CHANGELOG gate only after the fact; release.sh pushes commit and tag together so publish runs in parallel with CI); no build-docs.py / landing/docs drift check; installs .[dev] without mcp (publish.yml:29; the blind spot ci.yml:24-27 warns about); lints `src tests` not `scripts` (publish.yml:33 vs ci.yml:32); no rehearse-migration.sh.
   - Recommended: install .[dev,mcp], lint scripts too, run check-docs.py before the Publish step (or make publish depend on CI).

4. MUST FIX (low severity): both installers present `scribe` as the main command.
   - install.sh: lines 3, 5, 16, 72, 99, 118, 271-273, 316-330, 337-338, banners 383-400 ("scribe installer", "Next step: scribe ui", `command_exists scribe`). install.ps1: 2, 5, 12-13, 23, 154-166, 212-223.
   - Related bugs in install.sh: line 340 falls back to `python3 -m anyscribe` instead of `"$PY"` (wrong interpreter when resolve_python picked python3.12); line 325 hardcodes `Library/Python/3.12/bin` regardless of Python found.
   - Recommended: rename to anyscribe throughout, use $PY at 340, derive PATH hint from $PY.

5. COULD UPDATE (will start failing): GitHub Actions 2-3 majors behind, target deprecated Node 20.
   - actions/checkout@v4 (ci.yml:15, 46, 72; publish.yml:14); actions/setup-python@v5 (ci.yml:17, 74; publish.yml:16); actions/setup-node@v4 (ci.yml:48; publish.yml:20).
   - Latest: checkout v7.0.1, setup-python v7.0.0, setup-node v7.1.0. Last CI run 37311086649 warns "Node.js 20 is deprecated... forced to run on Node.js 24" and that ubuntu-latest moves to Ubuntu 26 from 2026-10-19 (setup-python has 26.04 builds for 3.10 to 3.15, safe).
   - pypa/gh-action-pypi-publish@release/v1 current (v1.14.3).
   - Recommended: checkout@v7, setup-python@v7, setup-node@v7.

6. COULD UPDATE (decision for the owner on 3.10): Python version support story.
   - pyproject.toml:13 requires-python >=3.10; classifiers 26-30; CI matrix ci.yml:13 ["3.10", "3.12"].
   - Python 3.10 EOL 2026-10-01. 3.14 (2025-10) and 3.15 (2026-10-09; 3.15.1 out) missing from classifiers. 3.13 classified but untested.
   - markdown 3.11.2 and Pillow 13.0.0 require 3.11+; on 3.10 pip falls back to older.
   - Trap: ctranslate2 4.8.3 (faster-whisper dep) has wheels only up to cp314, no sdist; `local` extra cannot install on 3.15.
   - Recommended: test 3.13 and 3.14 in CI, add 3.14 classifier; hold 3.15 until ctranslate2 ships cp315 wheels or document that local does not work on 3.15. Dropping 3.10 is the owner's call.

7. COULD UPDATE: dependency minimums allow versions with known advisories (OSV.dev).
   - python-multipart>=0.0.6 (pyproject.toml:51): 18 advisories at 0.0.6; 0.0.31 first clean. Used by upload route (web/routes/transcribe.py:21).
   - fastapi>=0.110 allows old starlette (0.36.3: 14 advisories).
   - Pillow>=10.0 (tray extra) and yt-dlp>=2024.0 (16 advisories) same.
   - Only matters for existing envs with old copies. Recommended: python-multipart>=0.0.31, fastapi>=0.115.

8. COULD UPDATE: ruff cap `<0.16` now excludes 0.16 and 0.17.1. Deliberate; raising means working through new lint findings. Leave.

9. COULD UPDATE: frontend (ui/package.json; lockfile ui/package-lock.json v3).
   - One major behind: eslint ^9.39.4 -> 10.13.0; @eslint/js ^9.39.4 -> 10.0.1; typescript ~6.0.2 -> 7.0.2 (do NOT bump: typescript-eslint 8.72.0 supports <6.1.0); @types/node ^24 -> 26 (low priority, CI uses Node 22).
   - Current within major: react/react-dom 19.3.1, react-router-dom 7.18.4, vite 8.3.5, tailwindcss and @tailwindcss/vite 4.3.3, lucide-react 1.61.0, @vitejs/plugin-react 6.1.2, eslint-plugin-react-hooks 7.1.1, eslint-plugin-react-refresh 0.5.7, globals 17.13.0, @types/react and @types/react-dom 19.3.0.
   - npm audit: 11 advisories (9 high). All build-time except react-router 7.14.1, bundled in shipped UI. Most cover server-rendering modes not used (client-side BrowserRouter, ui/src/App.tsx:41), but the <Link>/useNavigate open-redirect advisory (fixed 7.18.0) applies.
   - Recommended: refresh lockfile within current ranges, rebuild src/anyscribe/web/static, regenerate THIRD-PARTY-LICENSES.md.

10. COULD UPDATE: COMMIT_CHECKLIST.md:68 landing/index.html version badge line (no version string since ff48224); Quick grep block greps 0.1.0 which check-docs.py covers; check-docs.py scans only docs/user, landing, README.md, src/anyscribe/skill (.md/.html), so it would not catch stale versions or command names in install.sh, install.ps1, CONTRIBUTING.md, AGENTS.md, docs/building/ops/*.

## Checked and current

- Version strings: __init__.py, pyproject.toml, latest tag all 0.16.5; tag v0.16.5 (9ea09e0) ancestor of HEAD. check-docs.py passes. Historical mentions marked version-pin-ok. README has no version badge. ui/package.json 0.0.0 placeholder. 0.5.0 in release.sh is usage text.
- Python deps inside ranges: typer 0.27.3 (<1); mcp 2.3.0 (>=2,<3); fastapi 0.157.0; uvicorn 0.54.0; httpx 0.28.1; rich 15.0.0; pyyaml 6.0.3; python-dotenv 1.2.4; pytest 9.1.1; markdown 3.11.2 (<4); faster-whisper 1.2.1; pystray 0.19.5; pyobjc-framework-Cocoa 12.2.2; hatchling 1.32.4.
- CI wiring: runs tests, lint, docs check, migration rehearsal; every referenced script/path exists. Node 22 matches CONTRIBUTING 22.12+ and Vite 8 engines.
- Release files: vercel.json, rehearse-migration.sh, release.sh contain no stale names/paths/versions.
- Licensing consistent: LICENSE and skill/LICENSE byte-identical AGPLv3; NOTICE, README, landing (6 mentions), ui/package.json, SKILL.md frontmatter all AGPL-3.0-or-later; pyproject expression matches THIRD-PARTY-LICENSES.md (lucide-react ISC, rest MIT; versions match lockfile).

Not checked: no installs, builds or tests run; beaupy 4 and yt-dlp JS-runtime impacts inferred from upstream notes plus code reading.
