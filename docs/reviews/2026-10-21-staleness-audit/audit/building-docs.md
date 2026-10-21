# Developer-docs audit: anyscribe @ b3cddc1 (v0.16.5)

Read-only audit by an Opus subagent. Severity: [H] an agent following the doc produces broken work or red CI; [M] wrong fact; [L] cosmetic/historical.

## CLAUDE.md

1. [H] CLAUDE.md:78-104 (User documentation section). Docs pipeline never mentioned. CI `docs` job (.github/workflows/ci.yml "Render docs" then `git diff --exit-code landing/docs`) fails whenever docs/user/*.md changes without re-rendering. File list at :82-86 names 4 docs; docs/user/ holds 6: agents.md and troubleshooting.md missing.
   Replacement: add `agents.md` (skill vs MCP guide for AI-agent users; every MCP tool must appear in it, enforced by scripts/check-docs.py) and `troubleshooting.md` (common errors and plain-English fixes) to the list. Add bullet: "**Render after editing:** `docs/user/*.md` is the source; run `python scripts/build-docs.py` and commit the regenerated `landing/docs/*.html` in the same commit. CI fails on stale HTML, on any version string that does not match `pyproject.toml`, and on an MCP tool missing from `agents.md`."

2. [H] CLAUDE.md:110. "3. Add any new env vars to the onboarding wizard". Single source is now PROVIDER_KEY_ENV (providers/__init__.py:25). Catalogs in PROVIDER_MODELS (:40). Onboarding card is PROVIDER_INFO (cli/onboard.py:166). Languages in PROVIDER_LANGUAGES (providers/languages.py:357).
   Replacement for steps 2-3: "2. Register it in `providers/__init__.py`: `PROVIDER_REGISTRY`, `PROVIDER_KEY_ENV` (its API-key env var, or None), and `PROVIDER_MODELS` (first entry is the default). 3. Add its card to `PROVIDER_INFO` in `cli/onboard.py`, and its language list to `PROVIDER_LANGUAGES` in `providers/languages.py`."

3. [H] CLAUDE.md:118. "3. Update URL detection regex in `registry.py`". registry.py has no regex. Each downloader detects in can_handle() (youtube.py:26, instagram.py:50, local_file.py:29); registry iterates DOWNLOADERS (registry.py:12-16).
   Replacement: "3. Put URL detection in the downloader's own `can_handle()`; order in `DOWNLOADERS` matters (first match wins, `LocalFileDownloader` stays first)."

4. [H] CLAUDE.md:139-141. "set `"model": "nova"` on the entry. The router in `deepgram.py:47` reads this." False. deepgram.py:47 hardcodes: `model = "nova" if language.lower() in {"hi-latn"} else (self.model or "nova-3")`. The "model" key in languages.py:188 is never read. languages.py:14 and :134 repeat the false claim.
   Replacement: "For Deepgram entries that need the legacy Nova model (currently only `hi-Latn`), set `"model": "nova"` on the entry as documentation, **and** add the lowercased code to the hardcoded set in `deepgram.py:47`; the router does not read the list."

5. [M] CLAUDE.md:9-20 (Architecture tree). Missing files (__init__ excluded):
   - cli/: logs_cmd.py, migrate_cmd.py, rm.py, service_cmd.py, tray_cmd.py
   - downloaders/: local_file.py
   - providers/: groq.py
   - core/: checkpoint.py, config_set.py, dedup.py, errors.py, fileutil.py, preflight.py, quality.py, resolve.py, service.py, tray.py
   - web/: models.py, progress.py
   - Whole directories: mcp/ (server.py), skill/ (SKILL.md, references/, LICENSE), assets/ (tray-icon.png)
   - Root: __main__.py
   Nothing extra. Replacement lines:
   - `├── cli/  # Typer commands (main.py, onboard.py, transcribe.py, download.py, batch.py, rm.py, logs_cmd.py, migrate_cmd.py, config_cmd.py, local_cmd.py, models_cmd.py, skill_cmd.py, tray_cmd.py, service_cmd.py)`
   - `├── downloaders/  # Input handlers (base.py, local_file.py, youtube.py, instagram.py, registry.py)`
   - `├── providers/  # Transcription APIs (base.py, openai.py, groq.py, openrouter.py, elevenlabs.py, sargam.py, deepgram.py, local.py, local_models.py, languages.py)`
   - `├── core/  # Pipeline + routing + setup (orchestrator.py, resolve.py, quality.py, config_set.py, preflight.py, dedup.py, checkpoint.py, errors.py, fileutil.py, audio.py, deps.py, updater.py, migrate.py, local_setup.py, onboard_headless.py, tray.py, service.py)`
   - `├── mcp/  # MCP server, stdio (server.py): 10 tools, 3 resources`
   - `├── skill/  # Bundled Claude Code skill (SKILL.md, references/, LICENSE)`
   - `├── assets/  # tray-icon.png`
   - web line: `(app.py, jobs.py, models.py, progress.py, routes/{...}.py, static/)`

6. [M] CLAUDE.md:41. "Downloaders ... (youtube, instagram)". registry.py:12-16 registers three. Replacement: "(local_file, youtube, instagram; first match wins, local files first)".

7. [M] CLAUDE.md:42. "secrets in `.env` (API keys, Instagram password)". Instagram password removed in 0.8.3; cookies via instagram.browser (downloaders.md:24-27); onboard.py:850 only warns about leftover INSTAGRAM_PASSWORD. Replacement: "secrets in `.env` (API keys only; Instagram uses browser cookies via `instagram.browser`)".

8. [M] CLAUDE.md:50. "30s segments for Sarvam". Real: SARVAM_MAX_DURATION = 28 (providers/sargam.py:29). Replacement: "28 s segments for Sarvam (its sync REST limit is 30 s, exclusive)".

9. [L] CLAUDE.md:5. "downloads video/audio from YouTube/Instagram, transcribes it via API". Misses local files and offline. Replacement: "transcribes YouTube/Instagram URLs or local audio/video files via a cloud API or offline Whisper".

10. [L] CLAUDE.md:194. "ruff check src/". CI runs `ruff check src tests scripts`. Replacement: `ruff check src tests scripts  # lint (matches CI)`.

Other Key Patterns bullets (:40, :43-49, :51-53) verified true.

## docs/building/COMMIT_CHECKLIST.md

11. [H] :89. "`downloaders/registry.py` — added to `_load_downloaders()`". No such function. Replacement: "`downloaders/registry.py`: added to the `DOWNLOADERS` list (order matters, first match wins)".

12. [H] :68. "`landing/index.html` — version badge strings (2 places...)". landing/index.html has no version string; scripts/check-docs.py:23 fails CI on any non-current version in landing/. Replacement: delete the line, or say "`landing/`: no hardcoded versions; `scripts/check-docs.py` enforces this".

13. [H] Missing sections. No step for skill files (CLAUDE.md:30-36 says same commit). No step for re-rendering landing/docs via scripts/build-docs.py. :18-37 omits agents.md and troubleshooting.md.
    Add under "After every commit that changes user-facing behavior":
    - "[ ] `src/anyscribe/skill/` (SKILL.md + references/) matches the change"
    - "[ ] `docs/user/agents.md` lists every MCP tool (CI-enforced)"
    - "[ ] `docs/user/troubleshooting.md` covers new errors"
    - "[ ] Ran `python scripts/build-docs.py` and committed `landing/docs/` (CI fails on stale HTML)"

14. [M] :77-84 (new provider). Missing steps for PROVIDER_KEY_ENV, PROVIDER_MODELS (providers/__init__.py:25, :40), PROVIDER_LANGUAGES (languages.py:357) and skill references/providers.md. Add: "2b. `providers/__init__.py`: `PROVIDER_KEY_ENV` + `PROVIDER_MODELS`", "2c. `providers/languages.py`: `PROVIDER_LANGUAGES`", "9. `src/anyscribe/skill/references/providers.md`".

15. [L] :73. "Git tag created: `git tag vX.Y.Z`". release.sh creates and pushes it. Replacement: "Released with `./scripts/release.sh X.Y.Z "desc"` (bumps both files, tags, pushes)".

## docs/building/architecture.md

16. [M] :88. REST list missing most routes. Replacement from web/routes/*.py:
    - Config/keys: GET/PUT /api/config, GET /api/providers, GET /api/providers/{name}/languages, POST /api/providers/{name}/test, GET /api/keys/status, PUT /api/keys, DELETE /api/keys/{provider_name}
    - Jobs: POST /api/upload, POST /api/transcribe, GET /api/jobs/{job_id}, POST /api/jobs/{job_id}/cancel
    - History: GET /api/transcripts, GET/DELETE /api/transcripts/{transcript_id}, GET /api/workspace/info
    - System: GET /api/health, GET/PUT /api/autostart, POST /api/shutdown
    - Local: GET /api/local/status, GET /api/local/setup/log, POST /api/local/setup, POST /api/local/teardown
    - Models: GET /api/models/local, POST /api/models/local/{size}/pull, POST /api/models/local/{size}/reinstall, DELETE /api/models/local/{size}
    - Onboarding: GET /api/onboarding/status, POST /api/onboarding/save
    WebSocket at :89 (/api/ws/jobs/{job_id}) is correct.

17. [M] :61. Commands list omits `migrate` (main.py:219). Append `, migrate` after `install-skill`.

18. [M] :251 (matrix). "Menu-bar tray + login auto-start | ✓ ... | — | CLI-only by nature". Web UI has open-at-login toggle: GET/PUT /api/autostart (routes/system.py:28-37) calls service.install_service(), shipped 0.16.1. Replacement rows: "| Menu-bar tray | ✓ (`anyscribe tray`) | — | CLI-only. |" and "| Login auto-start | ✓ (`install-service`/`uninstall-service`) | ✓ (Settings open-at-login toggle, macOS, needs `[tray]` extra) | Same `core/service.py` |".

19. [M] matrix missing row for `anyscribe migrate`. Add: "| Legacy config migration | ✓ (`anyscribe migrate`, `--dry-run`) | — | CLI-only; also runs automatically at every app-home read (core/migrate.py:97) |".

20. [M] :95. "Port conflict detection before starting uvicorn". Now rolls forward up to 10 ports (main.py:47 PORT_SCAN_SPAN = 10, :247-262). Replacement: "Busy port: `anyscribe ui` rolls forward up to 10 ports (clamped to 65535) and only errors when all are busy".

21. [M] :96. "17 smoke tests via FastAPI TestClient". tests/test_web.py alone has 33; plus test_web_local.py, test_web_onboarding.py, test_autostart_route.py, test_keys_status.py, test_ui_port.py. Replacement: "Web tests: `tests/test_web*.py`, `test_autostart_route.py`, `test_keys_status.py`, `test_ui_port.py` (FastAPI TestClient)".

22. [M] :197. "Sarvam chunk | 30 s (`SARVAM_MAX_DURATION`) | `providers/sargam.py:27`". Real 28 s at sargam.py:29. Replacement: "| Sarvam chunk | 28 s (`SARVAM_MAX_DURATION`) | `providers/sargam.py:29` | Sarvam sync REST cap is 30 s, exclusive |".

23. [M] :193. "`instagram.py:149`" should be instagram.py:105. Other refs OK.

24. [M] :140-146 (Core Layer). Undocumented modules: preflight.py (pre-flight prerequisite checks), checkpoint.py (chunk save/resume), errors.py (structured provider errors + retry), fileutil.py (atomic writes + file locking), local_setup.py (local faster-whisper install/teardown), config_set.py (single validated settings write path). :146 migrations list omits app-home move ~/.anyscribecli -> ~/.anyscribe (migrate.py:13, :97) and Sarvam model-pin migration (migrate.py:145). Add a bullet per module; change :146 to: "Migrations run at startup: app home `~/.anyscribecli` → `~/.anyscribe`, workspace path rename, media → downloads, date-folder flattening, stale Sarvam model pin".

25. [L] :3. "Last updated: 2026-07-04 (v0.13.0 ...)". Replacement: "Last updated: 2026-10-21 (v0.16.5)".

26. [L] :161. CI description omits rehearse-migration.sh and the docs job. Append: "plus a fake-HOME migration rehearsal and a docs job (rendered-HTML freshness, version drift, MCP-tool and CHANGELOG gates)".

27. [L] :154. "Dataclasses over pydantic: fewer deps". web/models.py uses pydantic. Replacement: "Dataclasses over pydantic for config/results; pydantic only for web request/response models (web/models.py), via FastAPI".

## docs/building/web-ui-spec.md (and _index.md row)

28. [H] Whole file. Labelled "Status: Proposed" (:3), listed in _index.md:41 as a plan. Contradicts shipped UI: port 6227 (:11) vs 8457; "Starlette" (:29) and "ui/dist/" (:475) vs FastAPI serving src/anyscribe/web/static (app.py:49-56); Zustand/Framer Motion/shadcn (:54-57) not in package.json; Batch view (:162-189) not built; Instagram username/password settings (:240-244) removed in 0.8.3; API contract (:267-317) names /api/batch, /api/history, /api/history/:id, POST /api/providers/test, /ws/jobs, none exist (real: /api/transcripts, /api/providers/{name}/test, /api/ws/jobs/{job_id}); file tree (:409-450) wrong (real: ui/src/{App.tsx, main.tsx, index.css, api/{client,models,types}.ts, components/{LanguageInput,Layout,LocalSetupModal,Modal,ModelInput,OnboardingWizard,ProgressTracker,ResultCard,SetupBanner,URLInput}.tsx, hooks/useJob.ts, pages/{HistoryPage,SettingsPage,TranscribePage,TranscriptView}.tsx}).
    Replacement for :3: "> **Status:** Historical. The original April 2026 proposal, superseded by the v0.7.4 build. The shipped UI, routes and file layout differ; the current API is in `architecture.md` → Web UI Layer." For _index.md:41, append to TL;DR: "(Historical: shipped in v0.7.4 with a different API and file layout; see architecture.md.)"

## docs/building/providers.md

29. [M] :107. "the provider the `accuracy` quality tier (default) selects". Default tier is balanced (settings.py:41) -> Deepgram (quality.py:28). Replacement: "This is the provider the `accuracy` quality tier selects".

30. [M] :122. "Diarize support: `with_diarization=true` param, parses speaker turns". sargam.py:69-70: no with_diarization sent (dropped 0.14.1). Table at :56 is right. Replacement: "Diarization: not sent (Sarvam's sync endpoints don't support it; Batch API only). The response parser still reads `turns` if present (sargam.py:148)". Delete :123.

31. [M] :136-139 (Local). Models list missing large-v3-turbo and distil-large-v3.5 (local_models.py:18-26). Default source not stated. "Requires: pip install faster-whisper" is not how setup works.
    Replacement: "Model: `settings.local_model` (default `base`, settings.py:49); `ASCLI_LOCAL_MODEL` env var overrides (local.py:30). Sizes: `MODEL_SIZES` in local_models.py (tiny, base, small, medium, large-v3, large-v3-turbo, distil-large-v3.5). Setup: `anyscribe local setup --model <size>` (installs faster-whisper + downloads the model) or `pip install "anyscribe[local]"`".

32. [M] :141-151 (Adding a Provider). Step 2 shows transcribe(audio_path, language) without diarize (base at :162 has it). No steps for PROVIDER_KEY_ENV, PROVIDER_MODELS, PROVIDER_LANGUAGES. Replacement: step 2 "`transcribe(audio_path, language="auto", diarize=False)`". Step 3 "Add to `PROVIDER_REGISTRY`, `PROVIDER_KEY_ENV` and `PROVIDER_MODELS` in `providers/__init__.py`". Add "Add to `PROVIDER_LANGUAGES` in `providers/languages.py`" and "Update `src/anyscribe/skill/references/providers.md`".

33. [L] :3. "Last updated: 2026-07-29". Bump when fixed.

Note (not a doc error): PROVIDER_LANGUAGES (languages.py:357-364) has no groq entry, so the Groq language picker gets no list. Doc should say so.

## docs/building/downloaders.md

34. [M] :5-10 table and :12-32. local_file missing. First in registry (registry.py:13), 10 extensions via ffmpeg (local_file.py:12-23). Add row "| local_file | ffmpeg (subprocess) | No | Active |" and section: "### Local file (`downloaders/local_file.py`): `can_handle` matches an existing file with a supported extension (mp3, mp4, m4a, wav, opus, ogg, flac, webm, aac, wma), never http(s); converts to 16 kHz mono 64 kbps mp3 with ffmpeg."

35. [M] :44-51 (Registry snippet). Shows two; real (registry.py:6-16) has three:
    ```python
    from anyscribe.downloaders.local_file import LocalFileDownloader
    from anyscribe.downloaders.youtube import YouTubeDownloader
    from anyscribe.downloaders.instagram import InstagramDownloader

    DOWNLOADERS = [LocalFileDownloader(), YouTubeDownloader(), InstagramDownloader()]
    ```
    Add: "Order matters: first `can_handle()` match wins; local files are checked before URL patterns."

36. [L] :3. "Last updated: 2026-04-29". Bump when fixed.

## AGENTS.md

37. [M] :74. "Web UI routes: ... (transcribe, history, config, health, system)" missing local, models, onboarding (app.py:42-44). Replacement: "(transcribe, history, config, health, system, local, models, onboarding)".

38. [M] :59-76 (Quick Context). Missing entry points. Add:
    - "MCP server: `src/anyscribe/mcp/server.py` (10 tools, 3 resources)"
    - "Provider/model resolution: `src/anyscribe/core/resolve.py` (the only run ladder)"
    - "Settings writes: `src/anyscribe/core/config_set.py`"
    - "Headless onboarding (all surfaces): `src/anyscribe/core/onboard_headless.py`"
    - "Claude Code skill: `src/anyscribe/skill/`"

39. [L] :86. "All code must work on macOS and Linux". Windows supported (install.ps1, __main__.py). Replacement: "All code must work on macOS, Linux and Windows."

## docs/building/ops/whats-automated.md

40. [M] :116-123. "GitHub Releases: No automation". publish.yml's last step runs `gh release create ... --generate-notes` on every tag. Move to Automated: "**GitHub Releases:** the publish workflow creates a release with generated notes for every `v*` tag."

41. [M] :125-133. "All docs are manual. No auto-generation ... Changelog ... your discipline". Docs HTML rendered by scripts/build-docs.py; CI enforces freshness, version drift, MCP-tool coverage, CHANGELOG entry (ci.yml docs job, check-docs.py:23, :64, :74). Replacement: "Doc *content* is manual. CI enforces: rendered `landing/docs` HTML matches `docs/user`, no stale version strings, every MCP tool in `agents.md`, and a `CHANGELOG.md` entry for the shipped version."

42. [L] :112. CI description omits docs job and rehearse-migration.sh; add both. :158 lists "Version sync check" as future, but publish.yml verifies tag vs pyproject and check-docs.py catches doc drift; only __init__.py vs pyproject match remains unchecked.

## docs/building/ops/release-checklist.md

43. [M] :119-137. "Create a GitHub Release (Optional but Recommended)" with manual gh release create. Now automatic (publish.yml); running it would fail. Replacement: "### 10. Check the GitHub Release: the publish workflow creates it automatically; edit the notes on GitHub if needed."

44. [L] :54-58. SemVer table says new feature/command = MINOR, contradicting CLAUDE.md:159-163. Replacement row: "| New feature (backwards compatible) | PATCH for a bounded addition, MINOR only for a milestone | 0.13.2 → 0.13.3 |". Step numbering jumps 4 to 9 (cosmetic).

## docs/building/ops/pypi-guide.md

45. [L] :113-123. "Publishing for Real ... twine upload dist/*". Releases go via tag push + publish.yml + trusted publishing; "trusted" appears nowhere. Replacement: "Normal releases: `./scripts/release.sh X.Y.Z "desc"`; the tag triggers `.github/workflows/publish.yml`, which publishes via PyPI trusted publishing (no token). Manual twine is only for the legacy `anyscribecli` shim or a failed workflow."

## docs/building/plans/*

46. [M] plans/rename-to-anyscribe.md:4-5. "Status: approved, not started / Target release: 0.14.0". Shipped in 0.16.0 (CHANGELOG.md:78-84; BACKLOG.md:72). Replacement: "**Status:** shipped in 0.16.0 (2026-07-31). Kept for its hazard analysis."

47. [L] plans/v0.1.0-original-plan.md:6. `status: phase-1-complete`. Phases 2-3 shipped in 0.2.0. Optional. Replacement: `status: historical (all phases shipped by 0.2.0)`.

plans/flatten-workspace-structure.md is current.

## docs/building/_index.md

48. [L] :36. Tray plan row says "Deferred ... (~v0.9.x)". Shipped 0.13.0. Append to row: "(Shipped in v0.13.0; see 2026-07-04 tray-releases-landing.)"

49. [L] plans/rename-to-anyscribe.md and plans/v0.1.0-original-plan.md have no index rows (flatten plan does at :49). Add: "| 2026-07-21 | plan | [[plans/rename-to-anyscribe.md\|Rename plan + hazard analysis]] | Shipped as 0.16.0. |" and "| 2026-03-26 | plan | [[plans/v0.1.0-original-plan.md\|Original v0.1.0 plan]] | Historical. |".

Index integrity otherwise clean: all 50 journal files have one row, links resolve, newest-first.

## BACKLOG.md

50. [M] :67-72 version table order: runs ascending through 0.15.1 then 0.16.3, 0.16.5, 0.16.4, 0.16.2, 0.16.1, 0.16.0. Re-sort ascending 0.16.0..0.16.5.

51. [M] Version table missing tags v0.5.5 (2026-04-05, "Rename CLI to scribe, bare URL as default action"), v0.7.4.6.2 (2026-04-18, "KraftedX branding: sidebar logo + footer doodles"), v0.7.4.6.3 (2026-04-18, version-string bump). Add rows. Conversely rows 0.3.1, 0.8.0, 0.8.4 have no git tag (0.8.0 explained in its row).

52. [M] :68. 0.16.5 status "**Current**". Published 2026-09-13. Replacement: "Released 2026-09-13 (current)".

53. [M] :422-444. "## v0.14.0 — Rename to anyscribe / Status: in progress (branch rename/anyscribe)". Shipped as 0.16.0. Replacement heading "## v0.16.0 (planned as v0.14.0): Rename to anyscribe ✅", status "released 2026-07-31"; tick :439 shim item if anyscribecli 0.15.2 is live on PyPI (unverified offline).

54. [M] :659-667 (Landing page). Says pages.yml deploys landing/, Pages not enabled, human must flip Settings. No pages.yml exists; hosting is Vercel (vercel.json; _index.md:21; BACKLOG.md:60). Replacement: "**Status:** shipped; hosted on Vercel (`vercel.json`) since 0.13.2. The GitHub Pages workflow was removed." Delete :667.

55. [M] :374, :376 (v0.8.0). "[ ] Full test suite": tests/ has 40 files. "[ ] Suppress instaloader's noisy retry output": instaloader removed. Tick :374 "shipped incrementally 0.11.0-0.16.x"; strike :376 "moot: instaloader removed in 0.8.3/0.10.0".

56. [M] :678 (Icebox). "GUI (web UI via FastAPI + React, or TUI via Textual)". Web UI shipped 0.7.4. Replacement: "TUI via Textual (the web UI shipped in 0.7.4)".

57. [L] :677 (Icebox Windows PATH). Uses python -m anyscribecli, pip install anyscribecli, ascli, proposes install.ps1 which exists. Replacement: "`python -m anyscribe` ... `pip install anyscribe` → `anyscribe` just works"; drop install.ps1 suggestion. :681 `ascli search` -> `anyscribe search`.

58. [L] :407, :409 (tray). `anyscribecli[tray]` and `~/.anyscribecli/tray.pid` -> `anyscribe[tray]` (pyproject.toml:74) and `~/.anyscribe/tray.pid` (core/tray.py:16).

59. [L] :9-10 SemVer contradicts patch-first rule. Replacement: "- **PATCH**: bug fixes and bounded feature additions (a new flag, a UI control)" and "- **MINOR**: milestones (identity change, new surface, config-model redesign)".

60. [L] :687. "## v0.16.5 — AGPLv3 migration" sits after Icebox. Move after v0.16.4 section (:539).

Hosted MCP connector section (:602) correctly says planned/parked. Parakeet plan correctly "Not implemented yet".

## Checked and current

Command registration (main.py:213-227 + ui/update/doctor) matches architecture.md:61 except migrate. Entry points match pyproject. 7 providers + sarvam alias; "7 active" counts correct; quality tiers match; model catalogs match; NO_SEGMENT_MODELS and Groq diarize override match. MCP: 10 tools, 3 resources match. Extras match. Hard-coded constants table OK except #22, #23. Downloaders YouTube patterns, Instagram SUPPORTED_BROWSERS, two-step --dump-json match. CI publish flow matches publish.yml; CHANGELOG enforcement real. Skill install target and .version marker match. Updater behaviour matches. Journal index complete. COMMIT_CHECKLIST :103-110 and :112-119 current.

Not checked: anyscribecli 0.15.2 on PyPI; docs/user content (other audit); journal bodies.
