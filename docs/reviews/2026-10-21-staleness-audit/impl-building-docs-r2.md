# Implementer report, round 2 fix: audit/building-docs commit 198758d (parent d34ae8a)

A1 FIXED: local_cmd.py exits 2 on non-TTY without --yes; providers.md Local Setup line and CLAUDE.md local bullet now require --yes for agents/scripts with the example, and say the [local] extra installs the runtime only.
A2 FIXED: migrate_app_home_once called in load_config and load_env (config/settings.py) and ensure_app_dirs (config/paths.py), once per process; architecture.md migrate row uses the exact wording.
A3 FIXED: release-checklist step 6 replaced.
A4 FIXED: BACKLOG shim parenthetical records the 2026-10-21 wheel download and the three entry_points.txt lines verbatim.
B1 FIXED: journal pattern paragraph replaced (verified check-docs.py gates version strings, MCP names, CHANGELOG heading; CI does the HTML diff).
B2 FIXED: tldr and _index say "filed as five PRs for review"; index row adds "(#15 to #19)"; body lists PR numbers (gh confirms #15 merged, #16-#19 open).
B3 FIXED: verified deepgram.py transcribe calls needs_chunking/chunk_audio then _transcribe_chunked (25 MB / 30 min, 18-min pieces); OpenAI diarize raises when chunking needed; _transcribe_chunked does not renumber speakers. providers.md:92 note rewritten; chunking bullet added to the Deepgram section.
B4 FIXED: hardcoded hi-latn check confirmed at core/resolve.py:115-116; CLAUDE.md step 5, languages.py docstring rule 3 and the DEEPGRAM_LANGUAGES comment name _build_params and the resolve.py run-line note.
B5 FIXED: Groq bullet carries the gap note; BACKLOG Icebox line added after "Deepgram diarizer v2". No code change.
B7 FIXED: Python 3.10 sentence reworded.
B8 FIXED: routes/config.py comment replaced (wrapped over two lines). No code change.
B9 FIXED: 2b/2c are indented `- [ ]` sub-bullets under item 2.
B10 FIXED: providers.md sargam.py:148 -> SargamProvider._parse_response; settings.py:49 -> Settings.local_model; local.py:30 -> _resolve_model_size; architecture.md sargam.py:29 -> providers/sargam.py (SARVAM_MAX_DURATION); deepgram.py:47 -> _build_params. Audio-profile row citations left (inline settings, no symbol).
C1 FIXED: whats-automated.md publishing list is now 9 steps matching PR #16's fixed publish.yml (commit 52ef77f, since pushed), including frontend lint; journal paragraph added under "Infra changes in #16".

Checks: pytest 484 passed, 1 skipped; ruff check src passed; check-docs exit 0; git diff b3cddc1 on routes/config.py and languages.py changes only comment/docstring lines.

Not fixed (routed to PR #18): core/resolve.py:58-59 comment and providers/openai.py:111-118 error string still say Deepgram handles large files natively / without chunking.
