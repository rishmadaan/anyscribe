FIT REVIEW: PR #17 (audit/user-docs), round 3, head 396d912. Reviewer: Opus 5.5, effort high (Claude lane).

VERDICT: CONDITIONAL on CI green on 396d912 and D1 fixed (one-row "planned model shown as used" overclaim). D2 pre-existing, cheap, recommend folding in. Docs and landing only; diff byte-identical to git diff.

EARLIER: Astra D1 FIXED (local_cmd.py:132, models_cmd.py:181/245 refuse; rm.py:45-46 and service_cmd.py:45/67 confirm; service skips with --json). Astra D2 FIXED (doctor no params main.py:295; providers test no --json). Astra D3 FIXED (config_cmd.py:349-361; routes/config.py:297-300). Astra D4 PARTLY (fixed at commands.md:208, :600, :1279-1282, troubleshooting.md:337; missed :725, :729 = D1). Astra D5/Opus D2 FIXED (languages.py:357-364; routes/config.py:177-178). Astra D6 FIXED (main.py:56-114, :193). Astra D7/Opus D1 FIXED (local.py:90-104; groq inherits chunking). Opus D3 FIXED in docs; landing "92 language codes" DECLINED-OK (count is 92); React wizard DECLINED-OK follow-up. Opus D4 FIXED (main.py:284-287, :365). Opus D5 DECLINED-OK. Opus D6 FIXED (README:20, getting-started:29). --timeout 300 dropped (commands.md:1293). Skill sentences shortened (README:7, landing:1526).

NEW: D3 (tone) and an unnumbered nit (README:7 lost "if Claude Code is set up on this machine"; heading implies it).

FINDINGS
D1. should-fix. CONFIRMED. commands.md:725 "the model that would actually be used right now": providers list shows pin or first model (config_cmd.py:284-305); timestamped output swaps to whisper-1 (resolve.py:104-112); hi-Latn sends nova (deepgram.py:47); no notes printed. :729 "For what will actually run, use anyscribe config" contradicts :1279-1282. Replacements supplied.
D2. should-fix. CONFIRMED (pre-existing). commands.md:421, :442 `anyscribe rm "sources/youtube/my-video.md"` works only from inside the vault (vault/index.py:143-153; slug fallback searches my-video.md.md); JSON example :454 shows a relative deleted path but a slug match returns an absolute path. Fix: full path example plus one line about relative paths; absolute path in the JSON example. Same example in SKILL.md:282 belongs to PR #18 (already fixed there).
D3. nit (fit). CONFIRMED. landing:1536 and :1661 now read like disclaimers on the showcase page. Honest replacements: "Transcription, batch, config, logs, and model commands take --json for structured results. The docs list every command that supports it." and "--json on transcription, batch, config, and more."
D4. nit. PLAUSIBLE (lead verified: GET https://openrouter.ai/api/v1/models returns 200 without a key). getting-started.md:91 should say Groq, Sarvam and OpenRouter only confirm a key was entered.
D5. nit. CONFIRMED. providers.md:162 "Use --language" covers only the CLI; the Web UI language field is free text (LanguageInput.tsx:35). Replacement supplied.
D6. nit. CONFIRMED (pre-existing). configuration.md:64 "exactly what your next transcription will use" -> "the provider and model your next transcription would pick, and why"; landing Local card ~:1835 "no network" -> "no internet needed".

ANSWERS: fresh render EQUAL 7/7 (in-memory, markdown 3.10.3), zero link problems; spot-checks present; check-docs exit 0; the six greps clean except the correct Local column hit; bug-class sweep clean; landing card counts match the lists. Advice: `anyscribe install-skill` on a fresh machine prints "already installed" because the main callback installs first (main.py:193-194, skill_cmd.py:59); confusing, small code fix in a separate PR.

PENDING OWNER CHECKS: landing tone choice (D3); React wizard card rebuild follow-up.

NOT RUN: CI; pytest/ruff (no code); OpenRouter probe (lead ran it). INSPECTED: brief, impl report, both diffs; cli/rm.py, service_cmd.py, local_cmd.py, models_cmd.py, onboard.py, main.py, skill_cmd.py, config_cmd.py, transcribe.py, batch.py; core/resolve.py, deps.py; providers/deepgram.py, groq.py, local.py, languages.py; web/routes/config.py; ui LanguageInput.tsx; vault/index.py; scripts; ci.yml; README, docs/user, landing and rendered HTML.
