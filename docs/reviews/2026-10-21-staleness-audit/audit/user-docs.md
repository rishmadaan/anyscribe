# anyscribe user-docs staleness audit (HEAD b3cddc1, v0.16.5)

Read-only Opus audit. landing/docs/*.html is generated from docs/user/*.md (scripts/build-docs.py:1-22), so every fix to docs/user needs a rebuild. landing/index.html is hand-written.

## Three cross-file problems (fix first)

A. `anyscribe --clipboard` errors instead of transcribing (high). Stale in docs/user/getting-started.md:173, docs/user/commands.md:154, :245. (Also skill references/commands.md:11, :131, handled in the skill PR.) Code: DefaultToTranscribe.parse_args (cli/main.py:24-27) only prepends `transcribe` when the first arg does not start with `-`; `--clipboard`/`-c` exists only on transcribe (cli/transcribe.py:53). Replacement: `anyscribe transcribe --clipboard`. The `download --clipboard` example at commands.md:541 is fine.

B. CLI `--json` transcribe output has the wrong shape (high, breaks scripts). Stale in docs/user/commands.md:274-300, :302, :1163. Code: result wrapped as {"success", "data": {...}, "error"}; data also carries via and notes (cli/transcribe.py:130-150). On error: {"success": false, "data": null, "error": "..."} (cli/transcribe.py:119). So `jq '.file'` returns null.
Replacement for :274-287:
```json
{
  "success": true,
  "data": {
    "file": "/Users/you/anyscribe/sources/youtube/video-title.md",
    "title": "Video Title", "platform": "youtube", "duration": "12:34",
    "language": "en", "word_count": 1500, "provider": "openai",
    "model": "gpt-transcribe", "via": "config", "notes": [], "cached": false
  },
  "error": null
}
```
Error block (:295-300): {"success": false, "data": null, "error": "yt-dlp download failed: Video unavailable"}. :302 and :1163: `.file` -> `.data.file`. "The `cached` field"/"The `model` field" -> "`data.cached`"/"`data.model`". Note: MCP transcribe tool really returns the flat shape (mcp/server.py:104-117), so agents.md is fine.

C. "Deepgram never chunks" is false (high-medium). Stale in docs/user/commands.md:311-312, configuration.md:267, providers.md:155 ("No hard limit"), :220, :232 ("Handles long recordings (3+ hours) without chunking"), :483. Code: providers/deepgram.py:89-103 chunks whenever needs_chunking (over 25 MB or 30 min) into 18-min pieces (core/audio.py:9-20, :24-38), since v0.7.4.3. providers/base.py:54+ (_transcribe_chunked) does not match speaker labels across pieces.
Replacement (providers.md:220; adapt elsewhere): "**File limit:** files over 25 MB or 30 minutes are split into 18-minute pieces, like the other cloud providers. Each piece is labelled on its own, so on long recordings `Speaker 0` in one piece is not guaranteed to be the same person in the next." Table cell providers.md:155: "25 MB / 30 min (auto-chunked)". Drop "without chunking" at :232 and "no chunking needed" at :483. Related: core/resolve.py:58-59 comment and docs/building/providers.md:92 repeat the claim.

## docs/user/commands.md

1. :357-371 batch flag table missing `--resume` (medium). Code: cli/batch.py:33, :66-77; progress in `<file>.state.json`; without --resume an existing state file is deleted. Add row: `| --resume | | Skip entries finished in the previous run of this file (tracked in <file>.state.json). Without it, that record is discarded and every entry is attempted again (already-transcribed ones still return CACHED) | Off |`
2. :179-180 example calls gpt-transcribe "cheaper and more accurate than the default", but it IS the default (providers/__init__.py:41). Replacement: `# OpenAI's cheapest model` / `anyscribe "https://youtube.com/watch?v=abc123" -p openai -m gpt-4o-mini-transcribe`
3. :89-99 wizard step list missing "Also enable offline/local transcription?" (cli/onboard.py:583-590) and local-file handling (onboard.py:709); disagrees with getting-started's 12 steps. Insert after step 4: "5. Optionally enable offline/local transcription too". After keep-audio step: "Choose what happens to original local files (skip/copy/move/ask)". Renumber.
4. :597 Notes column "the cached size for `local`". Code prints `local_model: <size>` (cli/config_cmd.py:128-129). Replacement: "...and `local_model: <size>` for `local`".
5. :769 teardown description leaves out quality reset. Code: core/local_setup.py:325-333 sets quality: custom when provider was local or quality was free. Replacement: "...resets `provider` to `openai` if it was `local`, and sets `quality` to `custom` if the provider was `local` or the tier was `free`, so runs stop routing to what you just removed."
6. :775 "`pull` and `rm` error out" without setup. Code: model rm returns not_present (models_cmd.py:171-177); reinstall errors (:234-241). Replacement: "otherwise `pull` and `reinstall` error out with a hint pointing you at setup".
7. :805 (and :813, providers.md:366) "`--yes` required". Code: in a terminal it asks; --yes only required without a terminal (models_cmd.py:179-191, :208-213). Replacement: "Asks before deleting; pass `--yes` to skip the prompt (required when run from a script or agent)."
8. :998 "by pulling from git and reinstalling"; :1008, :1020 stashing. Code: pip installs run pip install --upgrade anyscribe (core/updater.py:186-197, :259-276); git pull/stash only for editable clones (:99-122). Replacement :998: "Update anyscribe to the latest version: `pip install --upgrade` for normal installs, or `git pull` plus reinstall for a cloned (editable) install." :1008: "Git (editable) installs only: update even with local changes (stashes them first)".
9. :1223 onboard `--model` / `-m`: no -m (cli/onboard.py:398-401). Replacement: "`--model`".
10. :164 and :364 language default shown as `auto`; comes from config (cli/transcribe.py:98-99). Replacement: "From config (`auto`)".
11. :660 example error text one line; code prints `Unknown model 'whisper-2' for openai.` then `Available: ...` on a second line (core/config_set.py:186, cli/config_cmd.py:194-196). Cosmetic.

## docs/user/providers.md

12. Deepgram claims at :155, :220, :232, :483. See C.
13. :236 and :248 ElevenLabs "optional speaker diarization (up to 32 speakers)" / "or speaker identification" (medium). Contradicts own table :153 and code: providers/elevenlabs.py:62 accepts diarize and never uses it. Replacement :236: "High-accuracy transcription with word-level timestamps. anyscribe does not request ElevenLabs speaker labels; use Deepgram for diarization." :248: "When you need the highest accuracy or word-level timestamps."
14. :151 Sarvam "23 Indian + English". SARVAM_LANGUAGES has 23 codes including en-IN = 22 Indic + English (matches own line 252). Replacement: "22 Indian + English".
15. :358 "(The model has to be cached first)". Only the Web UI enforces; config set local_model accepts any of 7 sizes (core/config_set.py:38). Replacement: "(Pull it first with `anyscribe model pull <size>`; the Web UI only lists cached models, but `config set` does not check.)"

## docs/user/configuration.md

16. :116 "Local provider requires `pip install faster-whisper`. Models download automatically on first use." (medium). Code: setup via `anyscribe local setup --model <size>` (providers/local.py:39-46, core/local_setup.py). Replacement: "**Local provider** needs a one-time `anyscribe local setup --model base` (or the Web UI's "Set up local transcription" button), which installs faster-whisper and downloads the model. Runs on CPU, or on an NVIDIA GPU with CUDA."
17. :265 "providers that support diarization (OpenAI, Deepgram, Sarvam)" (medium). Sarvam sends none (sargam.py:69-70, CHANGELOG 0.14.1). Groq refuses (groq.py:34-37). Replacement: "(OpenAI and Deepgram)".
18. :267 see C.
19. :107 "23 Indic languages + English" -> "22 Indic languages + English".
20. :316 "You can only select a model that's been cached" -> same fix as #15.
21. :17-25 and :410-415 file locations incomplete: missing ~/.anyscribe/recovery/ (failed-run audio, listed by `logs`), ~/.anyscribe/checkpoints/ (chunk resume), ~/.anyscribe/tray.pid (config/paths.py:15-16, core/tray.py:16). Add rows.

## docs/user/getting-started.md

22. :173 `anyscribe --clipboard` see A.
23. :21 CLI-only list leaves out download, migrate, install-skill (commands.md:32, :57, :59). Replacement: "A few commands are CLI-only: `batch`, `download`, `logs`, `doctor`, `update`, `migrate`, `install-skill`, and `tray`."
24. :109 wizard provider order. Actual (cli/onboard.py:166-207): OpenAI (default), OpenRouter, ElevenLabs, Sarvam AI, Deepgram, Groq, Local.
25. :108-119 12-step list missing offline opt-in step (onboard.py:583-590). Insert after step 4: "**Also enable offline transcription?** (optional) installs faster-whisper and a Whisper model as a free fallback."
26. :163 file-type comment leaves out aac and wma (downloaders/local_file.py:12-23). Replacement: "(mp3, mp4, m4a, wav, opus, ogg, flac, webm, aac, wma)".
27. :29 privacy statement, see #29.

## README.md

28. No command, flag, port, extras or version errors. "ten tools" matches mcp/server.py.
29. :21 (and getting-started.md:29) privacy statement says only automatic network contact is `update --check` (low-medium). Code: `anyscribe doctor` also asks PyPI (cli/main.py:365 -> core/updater.py:167-183, :231-249); every YouTube/Instagram download upgrades yt-dlp from PyPI when over 60 days old (core/deps.py:18-19, :274-306). Replacement: "No analytics, no phone-home. `anyscribe update --check` and `anyscribe doctor` ask PyPI for the latest version, and a download upgrades yt-dlp from PyPI if your copy is over 60 days old. Nothing else reaches out."

## docs/user/agents.md

30. :76 "the tools will start by telling your agent there's no provider configured". Code: defaults load (config/settings.py:101-102); transcription fails pre-flight with `OPENAI_API_KEY not set for provider 'openai'` (core/preflight.py:59-64). Replacement: "...or the first transcription fails with a missing-API-key error (for example `OPENAI_API_KEY not set for provider 'openai'`)."

## docs/user/troubleshooting.md

31. :236 error heading only for config set; per-run -m prints `Unknown model 'whisper-2' for provider 'openai'. Available: ...` (providers/__init__.py:103-105). Add: "(or, for a per-run `-m`, `Unknown model 'whisper-2' for provider 'openai'.`)"
32. :348-349 "Local transcription on CPU is 2-5x real-time". Conflicts with providers/local_models.py:47-89 (tiny ~10x, base ~7x, large-v3 ~1x) and providers.md:398. Replacement: "Local transcription on CPU ranges from about real time (`large-v3`) to about 7x faster than real time (`base`)."

## landing/index.html (hand-written)

33. :1761-1765 OpenAI card says "word-level timestamps", "~$0.006 / min", "57 languages" (medium). Default gpt-transcribe returns no timestamps; whisper-1 segment-level (providers/openai.py:23, :32; providers.md:152, :181). Default costs $0.0045/min. providers.md says 99 languages. Replacement desc: "The reliable workhorse. General-purpose, multilingual. Defaults to gpt-transcribe and switches to whisper-1 automatically when you want timestamps. Files >25 MB get auto-chunked." Chips: "~$0.0045 / min", "99 languages", "segment ts".
34. :1826 OpenRouter "through GPT-4o-audio-preview" (medium). Removed upstream; default now openai/gpt-audio-mini (providers/__init__.py:46; providers.md:324). Replacement: "Audio-via-chat through models like gpt-audio-mini and Gemini Flash. One API key, many models, pay per-token."
35. :1813-1816 Sarvam "11 Indic langs", no mention of translation (medium). Code runs mode: translate (sargam.py:39-41, :63-64; providers.md:269); list has 22 Indic. Replacement desc: "Purpose-built for Indic languages; renders Hindi, Tamil, Telugu, Bengali and more as an English translation." Chip: "22 Indic langs".
36. :1777 Deepgram "36+ languages" vs 89 in providers/languages.py and providers.md:151. :1790 ElevenLabs "99 languages" vs "90+" (92 codes). Replace with "89 languages" and "90+ languages". Also :1787 and :1791 "per-word confidence scores": anyscribe never writes confidence. Replace chip with "word-level ts".
37. :1661 `pip install anyscribe[mcp]` unquoted; zsh rejects. Replace with `pip install "anyscribe[mcp]"` (as :1532 does).
38. :1486, :1527, :1989 "skill installs itself during onboarding". Installs on first run of any command when ~/.claude exists (cli/main.py:56-114). Replacement: "installs itself the first time you run any anyscribe command" (matches README.md:7). :1527: `# or automatic on first run`.
39. :1945 "opens a wizard in your browser that checks your system". Web wizard steps: welcome, provider, key, offline, workspace, done (ui/src/components/OnboardingWizard.tsx:239); ffmpeg check lives in the setup banner. Replacement: "...opens a wizard in your browser that walks you through picking an engine".
40. :1449 and :1971 `pip install anyscribe`. README.md:55 and getting-started.md:69 recommend `pip install "anyscribe[tray]"`.
41. :1619 and :1913 sample frontmatter tags coffee/meetings, and SPEAKER 1 at :1921-1923 (cosmetic). Writer emits tags `transcript` plus platform (vault/writer.py:92-94); speaker labels start at Speaker 0.

## install.sh / install.ps1 (handled in the infra PR)

42. Every user-facing message still says `scribe` (low-medium). CHANGELOG 0.16.2 says every message says anyscribe. install.sh: banner :118; verify/PATH :316-330; post-install :337-338; final boxes :379-398; header comments :3, :16. install.ps1: :2, :12-13, :23, :157-165, :212-215. Replacement: `anyscribe` throughout (`anyscribe --version`, `anyscribe ui`, "anyscribe is installed!"); `command_exists scribe` at :316 and :337 -> anyscribe. Everything else checked out.

## CONTRIBUTING.md

No stale statements.

## Checked and current

Command coverage complete both ways. Flags/defaults match except noted. Providers, env vars, sarvam alias, model lists, quality tiers, resolve ladder, via values match. Config keys/defaults match. Paths match. Web UI port/labels match. Tray/autostart match. MCP matches. Platforms/sizes/ages match. No hardcoded current-version strings.

Not checked: external facts (prices, credits, upstream language counts), generated landing/docs HTML, skill files.
