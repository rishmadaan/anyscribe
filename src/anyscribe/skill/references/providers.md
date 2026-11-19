# Transcription Providers

anyscribe supports 7 providers. Each has different strengths.

## Quality presets — the provider knob

`quality` and `provider` are one setting with two positions. A tier picks the
provider; `custom` means "use `provider` as written".

| `quality` | Picks | Best for |
|-------------|-------|----------|
| `balanced` (default) | Deepgram `nova-3` | Strong accuracy + speaker labels |
| `accuracy` | ElevenLabs `scribe_v2` | Highest accuracy, primarily-English |
| `cost` | Groq `whisper-large-v3-turbo` | Cheapest + fastest (~$0.04/hr) |
| `free` | Local (Parakeet or Whisper) | Offline, $0 |
| `custom` | whatever `provider` says | The user chose a provider |

Recommend a tier first; only name a provider when the user wants a specific one.
**Setting a provider anywhere (CLI, Web UI, MCP `set_config`) writes
`quality=custom` in the same save** — don't set it yourself.

`--provider` on a run overrides everything for that run only.

**Keyless tier:** anyscribe warns and falls back to the configured provider rather
than failing — `WARNING: quality 'balanced' wants deepgram but no
DEEPGRAM_API_KEY is set — using openai instead`. Relay that note plus the fix.

**Never infer the effective provider from `provider` alone.** `anyscribe config --json`
returns a `resolved` block — `{provider, model, via, notes}` — where `via` is one
of `config`, `quality: <tier>`, `flag`, `diarize`.

## Picking a model within a provider

Every cloud provider has a small list of pickable models. **The first is the default** — most users never touch this. Three ways to change it:

```bash
anyscribe "url" -p openai -m whisper-1                # this run only
anyscribe config set provider_models.openai whisper-1 # persistent, per provider
anyscribe config --json                               # what's in effect + alternatives
```

Precedence: `-m` > `provider_models.<provider>` in config > provider default.

| Provider | Default | Also available |
|---|---|---|
| `openai` | `gpt-transcribe` | `whisper-1`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe` |
| `deepgram` | `nova-3` | `nova-2` |
| `elevenlabs` | `scribe_v2` | — (single model) |
| `sargam` | `saaras:v3` | — (single model) |
| `groq` | `whisper-large-v3-turbo` | `whisper-large-v3` |
| `openrouter` | `openai/gpt-audio-mini` | 5 listed below, **plus any audio-capable OpenRouter slug** |
| `local` | — | Sizes are downloaded, not picked with `-m`. See the local section. |

Unknown models are rejected up front with the valid list. `openrouter` is the exception — any slug passes through and only fails at the API.

### Adding models (openrouter only)

```bash
anyscribe config set extra_models.openrouter "qwen/qwen3-omni-flash,openai/gpt-audio"
anyscribe config set extra_models.openrouter ""     # clears
```

Added slugs merge into every picker (CLI dashboard, `providers list` where they
show `(custom)`, the Web UI dropdown, the MCP provider list).

**`extra_models` is rejected for every other provider, deliberately.** Their
lists are curated per anyscribe release because anyscribe needs code that parses each
model's response shape. If a user asks "how do I add a model to Deepgram?", the
answer is `anyscribe update` — not a config key. Don't hunt for a workaround.

### Timestamps — what to tell users

`gpt-transcribe`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `sargam`, and
`openrouter` return plain text with no `[mm:ss]` markers. `whisper-1`,
`deepgram`, `elevenlabs`, `groq`, and `local` return segment timestamps.

For OpenAI this is handled automatically: with `output_format: timestamped` or
`diarized`, anyscribe swaps in `whisper-1` and emits
`switched to whisper-1 — gpt-transcribe can't produce timestamps`.
**A per-run `-m` turns the swap off** (explicit beats automatic); a config pin
does not. So don't pass `-m gpt-transcribe` for a user who wants timestamps.

## Quick Comparison

| | OpenAI Whisper | Deepgram Nova | ElevenLabs Scribe | Sarvam AI | Groq | OpenRouter | Local |
|---|---|---|---|---|---|---|---|
| **Best for** | General purpose | Diarization + Hinglish | Highest accuracy | Indian languages → English | Cheapest + fastest | Model variety | Offline / free |
| **Languages** | 99 | 89 | 90+ | 22 Indian + English | 99 | Varies | 99 |
| **Timestamps** | Segment-level (`whisper-1`; swapped in automatically) | Segment-level (~30-word groups; speaker turns with `--diarize` on Deepgram) | Segment-level (~30-word groups) | No | Segment-level | No | Segment-level |
| **Diarization** | Yes (`--diarize`) | Yes (`--diarize`) | No | No (Sarvam Batch API only — not integrated) | No | No | No |
| **Cost** | ~$0.18–0.36/hr (by model) | ~$0.30/hr | ~$0.22–0.40/hr | ~$0.35/hr | ~$0.04/hr | Varies | Free |
| **File limit** | Auto-chunked over 25 MB / 30 min (diarize: 25 MB / 30 min, no chunking) | Auto-chunked over 25 MB / 30 min | Auto-chunked over 25 MB / 30 min | Auto-chunked into 28-sec pieces | Auto-chunked over 25 MB / 30 min | Auto-chunked over 25 MB / 30 min | RAM only |
| **Offline** | No | No | No | No | No | No | Yes |
| **API key env** | `OPENAI_API_KEY` | `DEEPGRAM_API_KEY` | `ELEVENLABS_API_KEY` | `SARGAM_API_KEY` | `GROQ_API_KEY` | `OPENROUTER_API_KEY` | None |
| **Quality tier** | — | `balanced` | `accuracy` | — | `cost` | — | `free` |

## OpenAI Whisper (provider: `openai`)

The `provider` setting's default value; the default `balanced` tier routes runs to Deepgram when a Deepgram key exists. Reliable, well-documented, good across most languages. Supports diarization. Four pickable models — this is the only provider where the model choice really matters.

- **Default model:** `gpt-transcribe` (auto-swapped to `whisper-1` when the output format needs timestamps)
- **Auto-chunking:** Files over 25 MB or 30 min split into 18-min segments. Diarize mode sends the whole file (`chunking_strategy=auto`) and refuses files over 25 MB / 30 min, suggesting Deepgram.
- **Diarization:** Yes — `--diarize` routes to `gpt-4o-transcribe-diarize` automatically, whatever model is pinned. Not part of the picker.
- **Get key:** https://platform.openai.com/api-keys

| Model | Cost | Segment timestamps | Notes |
|---|---|---|---|
| `gpt-transcribe` **(default)** | $0.0045/min (~$0.27/hr) | No | OpenAI's newest and recommended file-transcription model (released 2026-07-28). Roughly half Whisper's error rate in OpenAI's benchmarks, and 25% cheaper |
| `whisper-1` | $0.006/min (~$0.36/hr) | **Yes** | The OpenAI model that returns timestamps. anyscribe swaps to it automatically when the output format needs them |
| `gpt-4o-transcribe` | $0.006/min | No | Older 4o-family model; `gpt-transcribe` beats it at a lower price ($0.0045) |
| `gpt-4o-mini-transcribe` | $0.003/min | No | Cheapest OpenAI option, lowest accuracy of the three |

**When to recommend:** General purpose when it's the key the user has. Best cost/accuracy/language balance. Use `--diarize` for multi-speaker content.

**Model advice:** leave it on `gpt-transcribe` — cheaper and more accurate, and the timestamp case handles itself. Only pin `whisper-1` if the user wants every run on Whisper regardless of format. Never pass `-m gpt-transcribe` to a user whose format is `timestamped`/`diarized`: an explicit `-m` suppresses the automatic swap and they'll get plain paragraphs.

> Upgrade note: the default used to be `whisper-1`. Unpinned OpenAI runs now use `gpt-transcribe`.

> OpenAI also shipped `gpt-live-transcribe`. It's a realtime/streaming Realtime-API model; anyscribe transcribes files, so it isn't supported and isn't in the picker.

## Deepgram Nova (provider: `deepgram`)

Fast, accurate transcription with native speaker diarization and Hindi Latin script support.

- **Default model:** `nova-3` (auto-falls back to `nova` for hi-Latn, which isn't supported on nova-3 yet)
- **Also available:** `nova-2`, the previous generation. Only pin it to match transcripts made before nova-3.
- **Cost:** ~$0.005/min ($0.30/hr). $200 free credit on signup, no credit card needed.
- **Long files are auto-chunked into 18-min pieces** (over 25 MB or 30 min); speaker numbering may not stay consistent across chunks
- **Diarization:** Native — automatically detects the number of speakers from audio. No need to specify a speaker count.
- **Hindi Latin:** Use `--language hi-Latn` for romanized Hindi (Hinglish) output — this is the recommended default for any Hindi multi-speaker content
- **Get key:** https://console.deepgram.com/
- **Quick setup:** `anyscribe config set deepgram_api_key YOUR_KEY`

**Language guide for diarization:**
- Mostly English (with some Hindi words) → no language flag needed, auto-detect works
- Mostly Hindi / Hinglish → `--language hi-Latn` for romanized Latin script
- Pure Hindi (Devanagari) → `--language hi`

**When to recommend:** Best for multi-speaker transcripts (meetings, interviews, podcasts). Handles long recordings (auto-chunked). Ideal for Hinglish content with `--language hi-Latn`. This is the provider anyscribe auto-selects when `--diarize` is used.

## ElevenLabs Scribe (provider: `elevenlabs`)

Premium accuracy. anyscribe groups ElevenLabs' word timings into ~30-word timestamped segments. anyscribe does not request speaker labels from ElevenLabs; use Deepgram or OpenAI for diarization.

- **Model:** scribe_v2 (top-accuracy model; replaced scribe_v1 which ElevenLabs removed 2026-07-09)
- **Cost:** ~$0.22–0.40/hr depending on plan
- **Get key:** https://elevenlabs.io/app/settings/api-keys

**When to recommend:** User needs the highest accuracy. This is what the `accuracy` quality tier selects (the default is `balanced` → Deepgram).

## Sarvam AI (provider: `sargam`)

Specialized for Indian languages. Dramatically better than Whisper for Hindi, Tamil, Telugu, and 19 other Indian languages.

- **Model:** `saaras:v3` — Sarvam's Feb-2026 flagship, on `/speech-to-text` with `mode=translate`. The only model anyscribe offers.
- **Retired:** `saaras:v2.5` and its deprecated endpoint are gone. `anyscribe config set provider_models.sargam saaras:v2.5` is now rejected, and an existing pin is dropped automatically on the next run (`Sarvam saaras:v2.5 is retired — using saaras:v3`). If a user asks for it, explain it no longer exists upstream.
- **Cost:** ~$0.35/hr; free tier ~$12 in credits
- **Supported:** Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Gujarati, Marathi, Punjabi, Odia, Assamese, Urdu, Sanskrit, and more
- **Chunking:** sync API limited to 30 seconds — anyscribe auto-chunks into 28-sec segments, just under the limit (unchanged on v3)
- **Behavior:** translates to English (this is `mode=translate`, not a verbatim transcript)
- **Get key:** https://dashboard.sarvam.ai
- **Spelling:** the canonical provider name is `sargam`. `sarvam` (the vendor's real spelling) is accepted wherever a *provider* is named — `--provider`, `config set provider`, `providers test`, `onboard --provider`, the web routes — and canonicalized to `sargam`. Don't correct a user who types it, and don't expect it back in `config` output. **Exception: the key name is not aliased.** `config set sarvam_api_key` exits 1 with *Unknown key*; use `sargam_api_key` / `SARGAM_API_KEY`.

**When to recommend:** Indian-language audio when an English transcript is wanted (it translates; it never returns the original language). For an original-language transcript use Deepgram (`--language hi` / `hi-Latn`) or OpenAI. Handles code-mixed audio (e.g., Hindi-English) well. Not suited for non-Indian languages. Leave the model on `saaras:v3`.

## Groq (provider: `groq`)

Cheapest and fastest cloud option. Runs Whisper `large-v3-turbo` on Groq accelerators; OpenAI-compatible output (segment timestamps included).

- **Default model:** `whisper-large-v3-turbo` — cheapest and fastest
- **Also available:** `whisper-large-v3` — higher accuracy, and Groq allows a larger upstream file limit for it. Pin with `-m whisper-large-v3` when the turbo output is missing words.
- **Cost:** ~$0.04/hr — the cheapest cloud provider
- **Chunking:** over 25 MB or 30 min auto-chunked (same as OpenAI)
- **Diarization:** No. For speaker labels use `--diarize` with a Deepgram key set (it auto-routes), or `-p deepgram` / `-p openai` (remove any per-run `-m` or `--model` flag, since Groq model names are rejected by other providers). Quality tiers are not applied to diarized runs.
- **Get key:** https://console.groq.com/keys
- **Quick setup:** `anyscribe config set groq_api_key ...`

**When to recommend:** The `cost` quality tier maps here. Bulk/low-cost transcription where speaker labels aren't needed.

## OpenRouter (provider: `openrouter`)

Routes to various AI models via a unified API. Uses audio-capable chat models with a transcription prompt.

- **Default model:** `openai/gpt-audio-mini`
- **Listed models:** `openai/gpt-audio-mini`, `google/gemini-2.5-flash-lite`, `google/gemini-2.5-flash`, `google/gemini-3-flash-preview`, `mistralai/voxtral-small-24b-2507`, `openai/gpt-audio`
- **Any slug works:** OpenRouter is the one provider where `-m` isn't validated — pass any audio-capable slug and anyscribe forwards it. A wrong slug fails at the API (404), not at anyscribe.
- **Keep slugs in the picker:** `anyscribe config set extra_models.openrouter "<slug>,<slug>"` (empty value clears). Openrouter-only.
- **Removed:** the `OPENROUTER_MODEL` env var is no longer read (0.15.0). Migrate to `provider_models.openrouter` and delete the `.env` line. <!-- version-pin-ok -->
- **Cost:** Per-token pricing, generally more expensive than dedicated STT
- **No timestamps** — returns plain text only
- **Get key:** https://openrouter.ai/keys

> **The old default is gone.** `openai/gpt-4o-audio-preview` was removed from OpenRouter — requests to it now 404. If a user has it pinned, clear the pin or set a current slug.

**When to recommend:** Only when user needs a specific model available through OpenRouter. Not recommended as primary — dedicated STT APIs are faster, cheaper, more accurate.

## Local / Parakeet + Whisper (provider: `local`)

Transcription runs on-device without an API key, at no cost. Package installation and model downloads require internet. Download the selected model before going offline; choosing an uncached model can trigger a download on the next local run. Installation is **opt-in** through `anyscribe local setup`, onboarding with the local provider, or the Web UI's local setup flow.

- **Engines:** Parakeet (NVIDIA Parakeet TDT 0.6B, int8 ONNX via `onnx-asr`) and Whisper (`faster-whisper`). One provider; the model id picks the engine
- **Recommended model:** `parakeet-v3` (English + 24 European languages; as accurate as `large-v3-turbo` on English at ~4x its speed). `large-v3-turbo` for Hindi and other languages
- **All ids:** `parakeet-v3`, `parakeet-v2`, `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo`, `distil-large-v3.5`
- **Also needs:** `ffmpeg` on the system PATH (local setup does not install ffmpeg)
- **GPU:** Whisper auto-detects NVIDIA CUDA; Parakeet runs on CPU

### Setup — one command, one action

```bash
anyscribe local setup --model parakeet-v3 --yes --json
```

`--model` is **required**. The CLI never picks a model silently. In a non-TTY (agent) context, `--yes` is also required. Setup:

1. Detects the install method (pipx / venv-pip / system pip; `uv pip --python` when the venv has no pip, as with `uv tool install`).
2. Installs `faster-whisper`, `av<19` (PyAV 19 breaks faster-whisper 1.2.1) and `onnx-asr` into the same Python env as anyscribe. <!-- version-pin-ok -->
3. Downloads the chosen model from HuggingFace; a Parakeet model also downloads Whisper `tiny` (~75 MB, the language check).
4. Persists `local_model` in `config.yaml`.
5. Does not change `provider`, `quality` or `diarize`. For one local run pass `-p local` (local has no speaker labels). To make local the default: (1) if the user already uses another provider, ask first; (2) if `diarize` is true in `anyscribe config --json`, run `anyscribe config set diarize false` (local has no speaker labels; otherwise runs still go to Deepgram when a key is set); (3) run `anyscribe config set provider local` (sticks, also writes `quality=custom`), or `anyscribe config set quality free`. Confirm `resolved.provider` is `local`.

Idempotent — re-running with an already-set-up model just updates the default. An install from before Parakeet gets onnx-asr when it first sets up or pulls a Parakeet model.

### Models — use this to advise the user

| Model | Id | Accuracy | Speed | 1 hour of audio | Download | Memory | Languages |
|-------|----|----------|-------|-----------------|----------|--------|-----------|
| **Parakeet v3** (recommended) | `parakeet-v3` | 5/5 | 4/5 | ~10 min | ~670 MB | ~2.2 GB | English + 24 European languages |
| **Whisper Large v3 Turbo** (for Hindi) | `large-v3-turbo` | 5/5 | 2/5 | ~40 min | ~1.6 GB | ~3.1 GB | Hindi and 95+ others |
| **Whisper Small** | `small` | 4/5 | 3/5 | ~22 min | ~460 MB | ~1.3 GB | Hindi and 95+ others |
| **Whisper Base** | `base` | 3/5 | 4/5 | ~8 min | ~140 MB | ~1 GB | Hindi and 95+ others |
| Parakeet v2 | `parakeet-v2` | 4/5 | 4/5 | ~9 min | ~670 MB | ~2.5 GB | English only (v3 is as fast and more accurate) |
| Whisper Medium | `medium` | 4/5 | 1/5 | ~67 min | ~1.5 GB | ~3.2 GB | slower than real time, no better than Small |
| Whisper Large v3 | `large-v3` | 4/5 | 1/5 | ~2.5 hours | ~2.9 GB | ~6.4 GB | needs a graphics card to be practical |
| Distil-Whisper Large v3.5 | `distil-large-v3.5` | 3/5 | 2/5 | ~32 min | ~1.4 GB | ~2.7 GB | English; scored below Small in our test |
| Whisper Tiny | `tiny` | 2/5 | 5/5 | ~4 min | ~75 MB | ~0.9 GB | very rough; used for the language check |

Times and ratings were measured on a 6-core desktop processor (Intel i5-10600K) with
no graphics card, on 15 minutes of real English recordings. A Mac with Apple silicon
or a computer with an NVIDIA graphics card will likely be faster. `anyscribe model list`
shows the same table with what you have downloaded.

**Default guidance (ask "What language is most of your audio?" if you don't know):** English or another European language → `parakeet-v3`. Hindi or another Indian language, or anything else → `large-v3-turbo` (`small` under ~6 GB RAM). A mix (e.g. English and Hindi) → `parakeet-v3` as the default **and** `anyscribe model pull large-v3-turbo`; the language check switches between them. Under ~4 GB RAM → `base`. `anyscribe local status --json` → `recommendations[<answer>]` gives the same pick with plain-language `reasons` (answers: `english`, `indian`, `european`, `mix`, `other`) and the detected `hardware`; read the reasons to the user. When `set_language` is set (Hindi or another Indian language), ask whether most of their audio is Hindi before offering `anyscribe config set language hi`: Turbo is about 3 times more accurate on Hindi when told the language, but every recording is then treated as Hindi (wrong for Tamil or Bengali audio, and it turns off the language check). `primary: null` means not enough disk space (the reason says how much is needed).

**The language check (Parakeet only).** Before Parakeet runs on `language: auto`, Whisper Tiny checks the language at the start, middle and end of each recording (speech only). If any of them isn't one of Parakeet's languages, anyscribe uses `large-v3-turbo` (or the best other ready Whisper, never distil or tiny) and adds a note, e.g. `Detected Hindi — Parakeet v3 doesn't cover Hindi, so this used Whisper Large v3 Turbo. To skip the check, set your language to Hindi in Settings.` If the check can't tell (low confidence or no speech), it uses a ready Whisper, or runs Parakeet with a note saying the check was unsure. For recordings that switch language mid-sentence (Hinglish), suggest making `large-v3-turbo` the default. It appears in `--json` `notes` (merged with the plan notes) and in the transcript's frontmatter (`model:`, `notes:`); `model` in `--json` is the model that actually ran. **Always tell the user about such a note.** If no Whisper model is cached, the run fails with `anyscribe model pull large-v3-turbo` in the error and writes nothing; if Tiny was deleted, it fails asking for `anyscribe model pull tiny`. An explicit Parakeet language (`--language en`) skips the check.

### Cache management (after setup)

| Task | Command |
|------|---------|
| See what's cached (with ratings) | `anyscribe model list --json` |
| Add another model | `anyscribe model pull <id> --json` |
| Delete a cached model | `anyscribe model rm <id> --yes --json` (keep `tiny` while the default is Parakeet) |
| Inspect a model | `anyscribe model info <id> --json` |
| Switch default model | `anyscribe model pull <id>`, then `anyscribe config set local_model <id>` (refused, with the command, while the model isn't ready) |

### Teardown

```bash
anyscribe local teardown --yes --json
```

Uninstalls faster-whisper and onnx-asr, deletes every cached model; if provider was `local` it becomes `openai`, and if provider was `local` or quality was `free`, quality becomes `custom`.

**When to recommend local:** offline workflows, privacy-sensitive content, bulk processing where API cost matters, or users without API keys. Don't push it for casual one-off transcriptions — the API providers are simpler and the model download is big.

## Switching Providers

**Change default:**
```bash
anyscribe config set provider elevenlabs
```

If `diarize` is on (per run or saved) and a DEEPGRAM_API_KEY is set, Deepgram runs instead unless `-p` is passed.

**Override for one transcription:**
```bash
anyscribe transcribe "url" --provider local
anyscribe transcribe "url" -p openai -m gpt-transcribe    # provider + model
```

**Pin a model for a provider:**
```bash
anyscribe config set provider_models.openai gpt-transcribe
anyscribe providers list                                   # confirm what's in effect
```

**Add/update API keys:**
```bash
anyscribe config set deepgram_api_key YOUR_KEY     # Quick — stored in .env
anyscribe onboard --force                           # Interactive — re-enter keys
```

Or edit `~/.anyscribe/.env` directly (never display this file to the user).

**Diarization auto-routing:** When `--diarize` is used without `-p`, anyscribe auto-switches to Deepgram if configured. Deepgram auto-chunks files over 25 MB or 30 min, so speaker numbering may not stay consistent across chunks.
