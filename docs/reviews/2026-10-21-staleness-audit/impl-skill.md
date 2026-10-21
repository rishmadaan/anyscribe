# Implementer report: audit/skill-cli-text (commits 88423a6, 0b90724)

Worktree: <checkout>

12 files, 181+, 85-: cli/config_cmd.py 2, cli/models_cmd.py 3, cli/onboard.py 2, cli/transcribe.py 4, core/errors.py 1, core/resolve.py 4, skill/SKILL.md 29, skill/references/commands.md 92, config.md 13, providers.md 30, troubleshooting.md 72, tests/test_local_cli.py 14 (new test).

Applied: skill findings 1 to 39, all. Code fixes: onboard --local-model help lists every size from MODEL_SIZES; model info looks up MODEL_REPOS[size]; transcribe.py prompt hints (lines 67, 222) say `anyscribe transcribe`; providers test docstring says it makes no API call; Groq key URL https://console.groq.com/keys added to _KEY_URLS; resolve.py comment no longer says Deepgram never chunks.

Wording changes while applying:
- #15: kept the existing {"success", "data": {"deleted": ...}, "error"} wrapper, which is what rm.py prints; only changed the path to absolute.
- #22: added "the Web UI sends a list" (web/routes/config.py passes values to set_value, which accepts lists).
- #35: Groq diarize entry says the cost tier is skipped on diarized runs (resolve.py:70-74), so Groq only meets --diarize through -p groq or provider: groq.
- #12: error example uses the `yt-dlp metadata failed:` prefix, to match #37.

Declined: none.

Mutation test tests/test_local_cli.py::test_model_info_repo_matches_model_repos: with lookup pointed back at f"Systran/faster-whisper-{size}": AssertionError 'Systran/faster-whisper-large-v3-turbo' != 'dropbox-dash/faster-whisper-large-v3-turbo', 1 failed. Fix restored: 1 passed. Worktree src confirmed as the code under test.

Checks: pytest 485 passed, 1 skipped (includes test_skill_license.py; SKILL.md lines 1-14 only allowed-tools changed). ruff check all passed. ruff format --check: 2 pre-existing files would be reformatted (cli/main.py, cli/migrate_cmd.py), untouched by this branch. check-docs.py exit 0.

Missed by the audit, fixed in docs: providers.md said Sarvam uses 30-second chunks (28 s); said Groq chunks over 25 MB only (also over 30 min, reuses OpenAI code); still told Claude to recommend OpenAI as "Default choice" (reworded).

Not fixed (outside allowed code changes): providers/openai.py:113 diarize error says Deepgram "handles large files natively"; core/quality.py:23 comment says Deepgram does "no chunking"; SKILL.md safety rule 1 says .env holds "API keys and passwords" (passwords dropped; harmless but stale).

Not checked: #27 key prefixes not verified externally; no command run against real providers.
