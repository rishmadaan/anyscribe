# Providers

**Last updated:** 2026-10-21

## Model Picker

Every cloud provider has a pickable model list in
`providers/__init__.py::PROVIDER_MODELS` (first entry = default;
`OPEN_MODEL_PROVIDERS` marks openrouter as freeform). Read it through
`get_models(name, settings.extra_models)`, never `PROVIDER_MODELS` directly —
that merge is what makes user-added openrouter slugs visible in the pickers.
Pin per-run with `--model/-m`, persistently via
`settings.provider_models` (`scribe config set provider_models.<provider> <model>`),
or in the Web UI (Transcribe + Settings). `validate_model(name, model, extra)`
raises on an unknown model; `get_provider(name, model)` calls it and sets
`provider.model`; providers read `self.model or <default>`.

`settings.extra_models` is a `provider -> [slug]` map, **openrouter only** by
owner decision (`core/config_set.py` rejects every other key). Rationale: an
open-model provider forwards any slug, while a closed provider needs
response-parsing code per model, so its catalog belongs to a release.

| Provider | Default | Also pickable | Notes |
|----------|---------|---------------|-------|
| openai | gpt-transcribe | whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe | Non-whisper models have **no segment timestamps** (json-only). `core/resolve.py` auto-switches to whisper-1 when `output_format ∈ {timestamped, diarized}` and no per-run `-m` was given |
| deepgram | nova-3 | nova-2 | hi-Latn still auto-routes to legacy `nova` |
| elevenlabs | scribe_v2 | — | scribe_v1 removed upstream 2026-07-09, excluded |
| sargam | saaras:v3 | — | always `/speech-to-text` + `mode=translate`; saaras:v2.5 and the legacy endpoint deleted, migration drops old pins |
| openrouter | openai/gpt-audio-mini | gemini flash family, voxtral, gpt-audio + any slug (freeform) + `extra_models.openrouter` | old default `gpt-4o-audio-preview` was removed by OpenRouter; `OPENROUTER_MODEL` env var removed in 0.15.0 |
| groq | whisper-large-v3-turbo | whisper-large-v3 | |
| local | (settings.local_model) | parakeet-v3, parakeet-v2, tiny…large-v3, large-v3-turbo, distil-large-v3.5 | `PROVIDER_MODELS["local"] = []`; separate lifecycle: `anyscribe model pull`, HF cache. Registry: `MODEL_SPECS` in `providers/local_models.py` |

## Language Lists

Per-provider supported-language lists live in `src/anyscribe/providers/languages.py`
and are exposed via `GET /api/providers/{name}/languages`. The web UI's
language picker (Transcribe + Settings pages) consumes that endpoint and
renders a native HTML `<datalist>` — suggestions drop down, but free
typing is also accepted.

OpenRouter is the exception (`freeform: true`) — it accepts a prose
language instruction in the prompt rather than a code, so the UI shows a
plain text input for that provider.

To update a list when upstream changes, see CLAUDE.md → "Updating Provider
Language Lists".

## Available Providers

| Name | API | Status | Best For | Env Var | Diarization |
|------|-----|--------|----------|---------|-------------|
| openai | Whisper / gpt-4o-transcribe-diarize | Active (default) | General purpose, multilingual | `OPENAI_API_KEY` | Yes |
| deepgram | Deepgram Nova-3 | Active | Diarization, Hinglish, hi-Latn | `DEEPGRAM_API_KEY` | Yes |
| elevenlabs | ElevenLabs Scribe v2 | Active | Highest accuracy, ~30-word timestamped segments, 90+ langs | `ELEVENLABS_API_KEY` | No |
| openrouter | OpenRouter chat API | Active | Model flexibility (audio-via-chat) | `OPENROUTER_API_KEY` | No |
| sargam | Sarvam AI REST API | Active | Indic languages (Hindi, Tamil, etc.) | `SARGAM_API_KEY` | No (Batch API only, not integrated) |
| groq | Groq whisper-large-v3-turbo | Active | Cheapest + fastest cloud | `GROQ_API_KEY` | No |
| local | Parakeet (onnx-asr) or Whisper (faster-whisper) | Active | Offline, free, CPU/GPU | None | No |

## Quality Routing

`quality` (accuracy/balanced/cost/free) is a friendly alias that resolves to a
provider; `custom` is the sentinel meaning "respect `settings.provider`".
`QUALITY_TIERS` (`core/quality.py`) maps: accuracy→elevenlabs,
balanced→deepgram, cost→groq, free→local.

The whole ladder lives in **`core/resolve.py::resolve_run`** — one function, four
surfaces (CLI, batch, web, MCP). Precedence: explicit `--provider` → `--diarize`
→ `quality` tier → configured provider. It returns a `RunPlan(provider, model,
via, notes)`; `via` ∈ `flag | diarize | quality: <tier> | config`. Nothing else
should reimplement this ladder — that duplication is exactly what it replaced
(`apply_quality` is gone).

If the tier's provider has no key, `resolve_run` keeps `settings.provider` and
appends a WARNING note (keyless users still run, but the fallback is now visible
instead of silent).

**The provider→custom invariant:** any write that sets a provider also sets
`quality="custom"` in the same save — `core/config_set.py::set_value("provider", …)`
(CLI/web/MCP all route through it) and `core/onboard_headless.py`. Without it a
tier would silently re-override the user's choice on the next run.

## Provider-Specific Notes

### OpenAI (`providers/openai.py`)
- `MODEL = "gpt-transcribe"` (default) or `gpt-4o-transcribe-diarize` when `diarize=True`
- `NO_SEGMENT_MODELS` is the set `resolve_run` checks before falling back to `whisper-1` for timestamped/diarized output — keep it in sync when the catalog changes
- `verbose_json` response format (whisper-1 only; the gpt-* models are json-only), segment-level timestamps
- 25MB file limit — auto-chunked into 18-min segments (standard mode)
- Diarize mode: `gpt-4o-transcribe-diarize` model, 25MB upload limit applies (same as standard)
- Diarize response includes `speaker` field per segment
- **Note (v0.7.2):** `--diarize` auto-routes to Deepgram when no explicit `-p` is given and a Deepgram key is configured (`core/resolve.py`). OpenAI's diarize model has a 25MB limit and anyscribe refuses diarized OpenAI runs on files over 25 MB or 30 minutes; Deepgram chunks them into 18-min pieces instead, and speaker numbers are not matched across pieces.

### Deepgram (`providers/deepgram.py`)
- Uses `nova-3` model with `smart_format=true` (auto-falls back to `nova` for `hi-Latn` — nova-3 doesn't support that language yet)
- Raw audio POST to `https://api.deepgram.com/v1/listen`
- `Token` auth header (not `Bearer`)
- Native `diarize=true` query param — returns per-word speaker IDs
- Supports `hi-Latn` language code for romanized Hindi
- Response parsed from word-level: consecutive words by same speaker grouped into segments
- Without diarize: words grouped into ~30-word segments for timestamps
- Files over 25 MB or 30 min are chunked into 18-min pieces (`needs_chunking`/`chunk_audio`, shared `_transcribe_chunked`); speaker numbers restart per piece.

### ElevenLabs (`providers/elevenlabs.py`)
- Uses `scribe_v2` model, `xi-api-key` auth header (migrated from `scribe_v1`, which ElevenLabs removed 2026-07-09; v2 is the current top-accuracy model)
- Returns word-level timestamps (grouped into ~30-word segments for readability)
- ElevenLabs API accepts up to 3GB, but anyscribe chunks at 25MB (same `WHISPER_MAX_BYTES` threshold) for consistency
- This is the provider the `accuracy` quality tier selects

### OpenRouter (`providers/openrouter.py`)
- No dedicated STT endpoint — sends base64 audio to chat models
- Default model: `openai/gpt-audio-mini` (pin any slug via the model picker; `settings.extra_models["openrouter"]` keeps user slugs in the picker). The `OPENROUTER_MODEL` env var was removed in 0.15.0 — the pin supersedes it
- No timestamps returned — plain text only
- Auto-chunked at 25MB (same `WHISPER_MAX_BYTES` threshold as OpenAI/ElevenLabs)
- More expensive than dedicated STT APIs

### Sargam/Sarvam (`providers/sargam.py`)
- Always `saaras:v3` on `/speech-to-text` with `mode=translate`, so output is an **English translation**, not verbatim Hindi/Hinglish (same behaviour as the legacy `/speech-to-text-translate` endpoint, which Sarvam deprecated). That legacy path and `LEGACY_API_URL` are deleted; `core/migrate.py::maybe_migrate_sargam_model` drops a stale `saaras:v2.5` pin on first run.
- REST sync API limited to 30 seconds **exclusive** — a clip of exactly 30.0s is rejected. `SARVAM_MAX_DURATION = 28` chunks just under the boundary (raised from 30 in 0.10.1 after `v2.5` enforced the limit strictly).
- Auto-chunks audio into 28s segments (different from the standard 18-min Whisper chunks)
- `api-subscription-key` auth header
- Best for Indian languages; not suited for non-Indian languages
- Diarization: not sent (Sarvam's sync endpoints don't support it; Batch API only). The response parser (`SargamProvider._parse_response`) still reads `turns` if present
- **Future:** adopt Sarvam's batch API (no 30s cap, native diarization, 2hr/file) to escape sync chunking — see the [landscape audit](journal/2026-06-27-transcription-landscape-and-config-audit.md).

### Groq (`providers/groq.py`)
- Subclass of `OpenAIProvider` — Groq's STT API is OpenAI-compatible (same multipart request, `verbose_json` + segment timestamps, same response shape)
- Only overrides `name`, `API_URL` (`https://api.groq.com/openai/v1/audio/transcriptions`), `_get_api_key` (`GROQ_API_KEY`), and `MODEL` (`whisper-large-v3-turbo`)
- Chunking and `_parse_response` inherited unchanged
- Diarize path overridden to raise — Groq has no diarization model
- This is the provider the `cost` quality tier selects
- No entry in `PROVIDER_LANGUAGES` (`providers/languages.py`), so the Web UI language picker shows no list for Groq (a gap, not a design choice: Groq runs Whisper; tracked in BACKLOG)

### Local (`providers/local.py`)
- One `local` provider, two engines: **Parakeet** (NVIDIA Parakeet TDT 0.6B, int8 ONNX via `onnx-asr`, Silero voice-activity segments) and **Whisper** (`faster-whisper`, CTranslate2). The engine comes from `MODEL_SPECS[id]["engine"]`
- Model: `settings.local_model` (dataclass default `base`, so existing configs never change on their own); `ASCLI_LOCAL_MODEL` overrides (`_resolve_model_size`). `RECOMMENDED_MODEL = "parakeet-v3"` (what pickers preselect)
- Ids: `parakeet-v3`, `parakeet-v2`, plus the seven Whisper ids (`tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo`, `distil-large-v3.5`). Featured cards in order: parakeet-v3, large-v3-turbo, small, base; the other five sit under "More models" with a `tucked` reason
- **Registry** (`MODEL_SPECS`, the only place model facts live; CLI, Web UI and MCP all read it): display name, engine, measured `en_wer` and `x_realtime`, derived `accuracy`/`speed` (1-5) and `min_per_hour`, `download_mb`, `ram_mb`, `languages` (+ `language_codes` for Parakeet), `use_for`, `featured`, `badge`, `tucked`
- **Rating rule** (re-derivable; `accuracy_rating` / `speed_rating`): accuracy from English WER: <=6.7 -> 5, <=7.6 -> 4, <=10.5 -> 3, else 2. Speed from x realtime: >=12 -> 5, >=6 -> 4, >=2.5 -> 3, >=1.2 -> 2, else 1. Minutes per hour = round(60 / x realtime). Measured 2026-11-19 on an Intel i5-10600K (6 cores / 12 threads), 15 GB RAM, no GPU, CPU int8, model already loaded; method in `journal/2026-11-19-local-first-parakeet.md`
- **Language guard** (`LocalProvider.plan`): Parakeet only runs on a language in its set (v3: 25 European languages incl. English; v2: English). Explicit language outside the set, or `auto` where Whisper `tiny` `detect_language` says so on ANY of up to three 30 s speech-only windows (start, middle, end of the speech after faster-whisper's Silero VAD; `_speech_windows`), goes to `large-v3-turbo` if ready, else the most accurate other ready Whisper (never distil, never tiny), with the detected/explicit language and a note (passing `hi` beat Turbo's own `multilingual` mode on an English-then-Hindi clip: it kept the English part Latin and wrote the Hindi part in Devanagari). Unsure (every window's top probability < 0.5, or no speech): a ready Whisper with `language=None`, else Parakeet plus a note. Whisper-default `auto` runs pass `language=None` as before Parakeet; a VAD-filtered `detect_language` on the loaded model only decides the English prompt. No suitable Whisper cached -> error naming `anyscribe model pull large-v3-turbo`, nothing written. `tiny` not cached when the guard needs it -> error (no silent download mid-run)
- **Notes and model**: `TranscriptResult.model` / `.notes` -> `ProcessResult.model` / `.notes` -> CLI output and `--json` (`model`, `notes` merged with the plan's), batch, MCP, the Web job result, and the transcript (frontmatter `model:` + `notes:`, and a `> **Note:**` line under the details)
- **Whisper English prompt**: when the language is `en` (explicit, or `auto` detected as English on the loaded model) Whisper gets `initial_prompt="Hello, and welcome. Here's what we'll cover today."`, which stops large-v3-turbo writing a whole mid-sentence file lowercase without punctuation. Never for other languages
- Loaded models are cached per process (`lru_cache`): one big model (Whisper or Parakeet) plus the Tiny checker, so a batch doesn't reload per file but a long-lived Web UI server holds at most ~3 GB
- Audio is decoded once with `faster_whisper.audio.decode_audio` (PyAV, 16 kHz mono) and the array goes to either engine, so Parakeet also needs faster-whisper installed
- Setup: `anyscribe local setup --model <id>` installs `faster-whisper>=1.0`, `av<19` and `onnx-asr>=0.12.0` (`LOCAL_RUNTIME_SPECS` in `core/local_setup.py`, same as the `local` extra) and pulls the model. `av<19` is a shortcut: faster-whisper 1.2.1 calls `av.open(metadata_errors=...)`, which PyAV 19 removed; drop it once a faster-whisper release includes SYSTRAN/faster-whisper#1495. A venv without pip (`uv tool install`) installs with `uv pip install --python <interpreter>` when `uv` is on PATH. `local_runtime_ready()` is false when onnx-asr is missing or PyAV is 19+, so an older install gets fixed on the next setup or Parakeet pull. Refuses a non-TTY run without `--yes` (exit 2)
- Pulling a Parakeet model downloads only its int8 files (`PARAKEET_FILES`), the Silero VAD repo and Whisper `tiny` (the language checker), all into the same HF cache the list/delete code scans. Teardown also deletes the VAD repo and uninstalls both engines
- **Readiness** (`repo_ready`, `model_ready`, `helpers_ready`): `cached` means READY: a snapshot holds every file the engine loads (`WHISPER_REQUIRED` / `PARAKEET_REQUIRED` / `VAD_REQUIRED` globs) and no blob is `.incomplete` (a `<hash>.<tag>.incomplete` whose `<hash>` blob later completed is a killed run's leftover and ignored). Bytes without that = `partial`. The guard's fallback, the Settings "downloaded" state, default activation and the setup shortcut use readiness. `pull_model` always calls `snapshot_download` (resumes; a no-op when complete, also offline). A Parakeet default set in the Web UI without its helpers queues the model's pull; `config set` names what to pull
- **Restart**: `install_faster_whisper` compares `av` / `faster-whisper` / `onnx-asr` versions before and after; if one this process had imported changed, `restart_needed` goes on the result and `/api/local/status`, and every surface says "Restart anyscribe to finish setting up local transcription" (Python keeps the loaded module; a downgraded PyAV kept failing with `metadata_errors` until the server restarted)
- **Help me choose**: `core/local_recommend.py::recommend(answer, hardware)` — one question (English / Hindi or another Indian language / another European language / a mix / something else) plus detected RAM, cores, Apple silicon, NVIDIA GPU, free disk. Rules: English or European -> parakeet-v3; Hindi/other -> large-v3-turbo if RAM >= 6 GB else small; mix -> parakeet-v3 + large-v3-turbo; RAM < 4 GB -> base. Disk: each answer has an ordered pick list (`_CANDIDATES`), first that fits wins (mix: parakeet+turbo -> turbo -> small -> base, never Parakeet alone); nothing fits -> `primary: null` and a reason naming the space needed. Reasons describe the final pick and cite memory or disk only when they changed it; the last reason states the download sizes; `set_language: "hi"` for the Hindi answer. Used by `anyscribe onboard`, the Web UI (`GET /api/local/recommend`), and MCP `doctor` (`local.recommendations` for every answer)

## Adding a Provider

1. Create `src/anyscribe/providers/<name>.py`
2. Implement `TranscriptionProvider` from `base.py`:
   - `name` property returning the provider name
   - `transcribe(audio_path, language="auto", diarize=False)` returning `TranscriptResult`
3. Add to `PROVIDER_REGISTRY`, `PROVIDER_KEY_ENV` and `PROVIDER_MODELS` in `providers/__init__.py`
4. Add provider info to `PROVIDER_INFO` in `cli/onboard.py`
5. Add to `PROVIDER_LANGUAGES` in `providers/languages.py`
6. Update `docs/user/providers.md` and `docs/user/commands.md`
7. Update `src/anyscribe/skill/references/providers.md`
8. Update this doc

## Provider Interface

```python
class TranscriptionProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def transcribe(self, audio_path: Path, language: str = "auto", diarize: bool = False) -> TranscriptResult: ...
```

## TranscriptResult Fields

- `text`: Full transcript text
- `language`: Detected or specified language code
- `segments`: List of `TranscriptSegment(id, start, end, text, speaker)` (for timestamped/diarized output)
- `duration`: Audio duration in seconds
- `word_count`: Total word count (auto-calculated if not set)

## TranscriptSegment Fields

- `id`: Segment index
- `start`: Start time in seconds
- `end`: End time in seconds
- `text`: Segment text content
- `speaker`: Speaker label (e.g. "Speaker 0") or None if not diarized
