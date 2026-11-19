---
summary: Compare transcription providers — features, languages, pricing, and when to use each.
read_when:
  - Choosing which provider to use
  - Choosing which model to use within a provider
  - Transcribing in a specific language
  - Comparing cost vs accuracy
  - Setting up a new provider
---

# Providers

anyscribe supports 7 transcription providers. Here's how they compare and when to use each.

> **Commands below use `anyscribe`.** The shorter aliases `scribe` and `ascli` work identically — swap in whichever you prefer.

> **Don't want to choose?** Use the **`quality`** setting — pick `accuracy`,
> `balanced`, `cost`, or `free` and anyscribe selects the provider for you. See
> [Quality presets](#quality-presets) below.

## What it costs to start

**Start with a tier, not a provider.** Pick `accuracy`, `balanced`, `cost`, or
`free` and anyscribe chooses for you — that's the whole decision for most people.
The table below is a reference for when you'd rather pick yourself.

| Provider | Free to start? | Card needed? | Rough cost |
|----------|----------------|--------------|------------|
| **Local** | Yes — $0, no account | No — no account at all | Free |
| **Deepgram** | Yes — $200 credit on signup | No | ~$0.30/hr |
| **Sarvam** | Yes — ~$12 in credits | See [dashboard.sarvam.ai](https://dashboard.sarvam.ai) | ~$0.35/hr |
| **Groq** | See [console.groq.com/keys](https://console.groq.com/keys) | See [console.groq.com/keys](https://console.groq.com/keys) | ~$0.04/hr |
| **OpenAI** | See [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | See [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | ~$0.18–0.36/hr (by model) |
| **ElevenLabs** | See [elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys) | See [elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys) | ~$0.22–0.40/hr (by plan) |
| **OpenRouter** | See [openrouter.ai/keys](https://openrouter.ai/keys) | See [openrouter.ai/keys](https://openrouter.ai/keys) | Varies by model |

> **Why so many "see the provider's page" cells?** Because signup terms change
> whenever the provider feels like it, and a stale promise of "free, no card"
> is worse than no answer. The two we state outright — Deepgram's $200 credit
> and Local costing nothing — are the ones anyscribe itself depends on. Everything
> else, check at the source before you sign up.

> **Cheapest honest path to a first transcript:** `free` (Local, $0 forever,
> nothing to sign up for) or `balanced` (Deepgram, $200 of credit is a lot of
> hours at ~$0.30/hr).

## Privacy — who sees your audio?

Worth knowing before you pick. anyscribe itself doesn't phone home — everything runs on your own machine — but your audio has to go wherever the transcription happens.

- **Local provider:** audio stays on your machine. Nothing leaves. Fully offline once the model is downloaded.
- **API providers (OpenAI / Deepgram / ElevenLabs / Sarvam / Groq / OpenRouter):** anyscribe sends your audio to the API you picked and nothing else. No intermediary, no third party, no anyscribe-operated cloud. Your trust boundary is exactly the provider you chose — same as if you called their API directly.
- **YouTube / Instagram source URLs:** downloading the video obviously requires internet, and the source host sees the request. The transcribed audio then follows the same rule above (stays local with the local provider; goes to the API provider otherwise).

If privacy is the main reason you're evaluating anyscribe, use the **Local** provider + local files for an end-to-end-offline pipeline.

## Quality presets

The easiest way to use anyscribe: pick **what you want** and it chooses the provider.

| `--quality` | Picks | Best for |
|-------------|-------|----------|
| `balanced` (default) | Deepgram `nova-3` | Strong accuracy + speaker labels |
| `accuracy` | ElevenLabs `scribe_v2` | Highest accuracy, primarily-English |
| `cost` | Groq `whisper-large-v3-turbo` | Cheapest + fastest cloud (~$0.04/hr) |
| `free` | Local (Parakeet or Whisper) | Offline, $0 |
| `custom` | Whatever your `provider` setting says | You picked a provider yourself |

```bash
anyscribe "<url>" --quality accuracy     # per run
anyscribe config set quality cost         # change the default
anyscribe config set provider sargam      # picks the provider directly (writes quality: custom)
```

**It's one knob, not two.** Either a tier picks the provider for you, or
`quality` is `custom` and your `provider` setting is used as-is. Setting a
provider — on the CLI, in the Web UI, or through MCP — writes `quality: custom`
in the same save, so your choice sticks instead of being overridden by the tier
on the next run.

If you pass `--provider` on a single run, it wins for that run only.

Each tier needs that provider's key (accuracy → `ELEVENLABS_API_KEY`, cost →
`GROQ_API_KEY`, …); `free` needs none. **If the key is missing, anyscribe warns and
falls back** to your configured provider rather than failing:

```
→ openai · gpt-transcribe (config)
    WARNING: quality 'balanced' wants deepgram but no DEEPGRAM_API_KEY is set — using openai instead
```

Run `anyscribe config` to see the provider and planned model selected from current defaults, including substitution notes. Per-run flags can change that plan.

## Choosing a model within a provider

A **provider** is the company doing the transcribing. A **model** is the specific engine inside it. Each provider ships with a default model, so you can skip this section entirely and everything works.

Change it for one run:

```bash
anyscribe "<url>" -p openai -m gpt-transcribe
```

Or make it permanent:

```bash
anyscribe config set provider_models.openai gpt-transcribe
```

See what you have:

```bash
anyscribe config            # every provider, its model, and which one runs next
anyscribe providers list    # same model info, provider-focused
```

| Provider | Default model | Also available |
|----------|---------------|----------------|
| OpenAI | `gpt-transcribe` | `whisper-1`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe` |
| Deepgram | `nova-3` | `nova-2` (the previous generation) |
| ElevenLabs | `scribe_v2` | — only one |
| Sarvam | `saaras:v3` | — only one |
| Groq | `whisper-large-v3-turbo` | `whisper-large-v3` |
| OpenRouter | `openai/gpt-audio-mini` | Several listed, **plus any audio model on OpenRouter** |
| Local | — | Downloaded separately, see [Local](#local-parakeet-and-whisper) |

> **The one gotcha worth knowing: timestamps.** Some models return only plain text, with no record of *when* each sentence was said. This affects OpenAI's `gpt-transcribe`, `gpt-4o-transcribe`, and `gpt-4o-mini-transcribe`, plus Sarvam and OpenRouter generally.
>
> For OpenAI, anyscribe handles this for you: if your `output_format` is `timestamped` or `diarized` and the model can't do timestamps, it switches that run to `whisper-1` and prints a note. It only stands back if *you* named the model with `-m` — then you get exactly what you asked for, paragraphs and all. Sarvam and OpenRouter have no timestamped model to fall back to, so with those you simply get paragraphs.

> **Adding models OpenRouter offers but anyscribe doesn't list:**
>
> ```bash
> anyscribe config set extra_models.openrouter "qwen/qwen3-omni-flash"
> ```
>
> They join the pickers everywhere, marked `(custom)`. This works for OpenRouter
> only — it forwards any model name unchanged. The other providers' lists are
> curated per release because anyscribe needs code that understands each model's
> response format, so **"how do I add a model to Deepgram?" is answered by
> `anyscribe update`, not by config.**

> **In the Web UI:** a model dropdown appears on the **Transcribe** page once you explicitly pick a provider, and on the **Settings** page under your default provider. For OpenRouter it's a free-text box with your merged list as suggestions.

## Quick Comparison

| | OpenAI Whisper | Deepgram Nova | ElevenLabs Scribe | Sarvam AI | Groq | OpenRouter | Local |
|---|---|---|---|---|---|---|---|
| **Best for** | General purpose | Diarization (auto-selected) + Hinglish | Highest accuracy | Indian languages | Cheapest + fastest | Model flexibility | Offline / free |
| **Bundled language list** | 100 codes | 89 codes (languages and modes) | 92 codes | 22 Indian + English | No bundled picker list | Model-dependent | 100 codes (Whisper's list) |
| **Timestamps** | Segment-level (`whisper-1`; auto-used when needed) | Segments of ~30 words (speaker turns with `--diarize`) | Segments of ~30 words | No | Segment-level | No | Segment-level |
| **Diarization** | Yes (`--diarize`) | Yes (`--diarize`) | No (via anyscribe) | No | No | No | No |
| **Pricing** | ~$0.18–0.36/hr (by model) | ~$0.30/hr | ~$0.22–0.40/hr | ~$0.35/hr | ~$0.04/hr | Varies by model | Free |
| **Long files** | Split over 25 MB / 30 min (with `--diarize`: refused instead) | Split over 25 MB / 30 min | Split over 25 MB / 30 min | Always 28-second pieces | Split over 25 MB / 30 min | Split over 25 MB / 30 min | RAM only |
| **Offline** | No | No | No | No | No | No | Yes |
| **API key** | Required | Required | Required | Required | Required | Required | Not needed |
| **Quality tier** | — | `balanced` | `accuracy` | — | `cost` | — | `free` |

> The language numbers are the sizes of the language lists that ship with anyscribe (what the language picker offers). They are not a promise of what each provider supports today.
>
> Groq currently has no bundled language-picker list. Type the code yourself: `--language <code>` on the command line, or in the Web UI's language field.

## Provider Details

### OpenAI Whisper (default)

The most widely used speech-to-text API. Good accuracy across most languages. Segment-level timestamps included.

```bash
anyscribe config set provider openai
```

- **API key env var:** `OPENAI_API_KEY`
- **Get a key:** [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Cost:** $0.003–$0.006 per minute depending on the model (see below)
- **File limit:** files over 25 MB or 30 minutes are split automatically into pieces of about 18 minutes. With `--diarize` there is no splitting: OpenAI refuses files over either limit, so use Deepgram for long recordings with speakers
- **Default model:** `gpt-transcribe`
- **Diarization:** Yes — use `--diarize` flag to enable speaker-labeled transcripts

**Models you can pick:**

| Model | Cost per minute | Timestamps? | What it's for |
|-------|-----------------|-------------|---------------|
| `gpt-transcribe` (default) | $0.0045 (~$0.27/hr) | No | OpenAI's newest and recommended transcription model. Around half the error rate of Whisper in OpenAI's own testing, and 25% cheaper |
| `whisper-1` | $0.006 (~$0.36/hr) | **Yes** | The OpenAI model that tells you *when* things were said. anyscribe falls back to it automatically for timestamped or diarized output |
| `gpt-4o-transcribe` | $0.006 | No | An older model. `gpt-transcribe` is better and cheaper ($0.0045) |
| `gpt-4o-mini-transcribe` | $0.003 (~$0.18/hr) | No | The cheapest option, at some cost to accuracy |

```bash
anyscribe config set provider_models.openai whisper-1   # if you'd rather always use Whisper
```

> **You don't have to manage the timestamp tradeoff.** `gpt-transcribe` is more accurate and cheaper than Whisper, so it's the default — but it can't produce `[mm:ss]` markers. When your `output_format` is `timestamped` or `diarized`, anyscribe switches that run to `whisper-1` and tells you:
>
> ```
> → openai · whisper-1 (config)
>     switched to whisper-1 — gpt-transcribe can't produce timestamps
> ```
>
> The one case where it doesn't intervene is when you name the model yourself with `-m` — an explicit choice is always honoured.

> **Upgrading from an older anyscribe?** OpenAI's default used to be `whisper-1`. Unpinned OpenAI runs now use `gpt-transcribe`: cheaper, more accurate, and timestamps still work because of the automatic switch above. To go back permanently: `anyscribe config set provider_models.openai whisper-1`.

> **You may have heard of `gpt-live-transcribe`.** That one is for live, streaming audio (phone calls, real-time captions). anyscribe works on finished files, so it isn't supported here.

> **Diarization is handled for you.** When you pass `--diarize`, OpenAI runs a dedicated model (`gpt-4o-transcribe-diarize`) regardless of what you've pinned. There's nothing to configure.

> **When to use:** Good default for most use cases. Best balance of cost, accuracy, and language coverage. Use `--diarize` for meetings and multi-speaker content.

### Deepgram Nova

Fast, accurate speech-to-text with native speaker diarization and Hindi Latin script (`hi-Latn`) support. **The default provider for diarization** — anyscribe auto-routes `--diarize` to Deepgram when configured.

```bash
anyscribe config set deepgram_api_key YOUR_KEY    # $200 free credit on signup
```

- **API key env var:** `DEEPGRAM_API_KEY`
- **Get a key:** [console.deepgram.com](https://console.deepgram.com/) — $200 free credit, no credit card required
- **Cost:** ~$0.30/hour
- **Default model:** `nova-3` (auto-falls back to `nova` for `hi-Latn`, which isn't supported on nova-3 yet)
- **Also available:** `nova-2` — the previous generation. Pin it only if you're comparing against older transcripts: `anyscribe config set provider_models.deepgram nova-2`
- **File limit:** files over 25 MB or 30 minutes are split into pieces of about 18 minutes. Each piece is labelled on its own, so on long recordings `Speaker 0` in one piece is not guaranteed to be the same person in the next.
- **Diarization:** Native — automatically detects the number of speakers from audio characteristics. No need to specify a speaker count.
- **Hindi Latin:** Set `--language hi-Latn` for romanized Hindi / Hinglish output

**Diarization language guide:**

| Your audio | Language flag | Why |
|-----------|--------------|-----|
| English (or mostly English with some Hindi) | None (auto-detect) | Auto-detect handles English well, Hindi words transcribed phonetically |
| Mostly Hindi / Hinglish (Hindi-English mix) | `--language hi-Latn` | Outputs romanized Hindi in Latin script, better code-switching |
| Pure Hindi (want Devanagari) | `--language hi` | Outputs in Devanagari script |

> **When to use:** Best choice for multi-speaker transcripts (meetings, interviews, podcasts). Excellent for Hinglish content with `--language hi-Latn`. This is the provider anyscribe auto-selects when you use `--diarize`, and what the **`balanced`** quality tier (the default) selects.

### ElevenLabs Scribe

High-accuracy transcription. Timestamps come in segments of about 30 words (anyscribe groups ElevenLabs' word timings; it doesn't show a time for every word). anyscribe does not request ElevenLabs speaker labels; use Deepgram for diarization.

```bash
anyscribe config set provider elevenlabs
```

- **API key env var:** `ELEVENLABS_API_KEY`
- **Get a key:** [elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys)
- **Cost:** ~$0.22–0.40/hour depending on plan
- **File limit:** The ElevenLabs API accepts up to 3 GB, but anyscribe splits files over 25 MB or 30 minutes into pieces of about 18 minutes, the same as OpenAI
- **Model:** `scribe_v2` (the most accurate model currently measured)

> **When to use:** When you need the highest accuracy. This is what the **`accuracy`** quality tier selects.

### Sarvam AI

Specialized for Indian languages. Supports 22 Indian languages plus English with Indian accent optimization.

```bash
anyscribe config set provider sargam
```

> **`sargam` or `sarvam`?** The company is Sarvam AI, but anyscribe's internal name for the provider is `sargam`. Where you name the *provider* you can type either — `--provider sarvam`, `anyscribe config set provider sarvam`, `anyscribe providers test sarvam`, `anyscribe onboard --provider sarvam`, and the Web UI — and it's stored as `sargam`. **The API-key setting is the exception:** it's spelled `anyscribe config set sargam_api_key`, and the env var is `SARGAM_API_KEY`. `sarvam_api_key` is rejected.

- **API key env var:** `SARGAM_API_KEY`
- **Get a key:** [dashboard.sarvam.ai](https://dashboard.sarvam.ai)
- **Cost:** ~$0.35/hour; free tier: ~$12 in credits
- **File limit:** the sync API is limited to 30 seconds (exclusive) — anyscribe automatically chunks audio into 28-second segments
- **Model:** `saaras:v3` — Sarvam's flagship model, and the only one anyscribe offers
- **Supported languages:** Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Gujarati, Marathi, Punjabi, Odia, Assamese, Urdu, Sanskrit, and more

> **Upgrading from an older anyscribe?** The older `saaras:v2.5` model has been removed — Sarvam deprecated the endpoint it ran on. If you had it pinned, anyscribe drops the pin for you on your next transcription and prints `Sarvam saaras:v2.5 is retired — using saaras:v3`. Nothing for you to do. v3 behaves the same way — still translates to English, still chunked — just more accurately.

> **Important — Sarvam *translates to English*.** Sarvam transcribes in translate mode, so the output is an **English translation**, not a verbatim Hindi/Hinglish transcript. Use it when you want Indic audio rendered as English; use Deepgram `--language hi-Latn` (see below) when you want to keep the spoken Hinglish.

> **When to use:** Getting an English version of Indian-language audio. Not the right choice if you want to preserve the original words.

> **Hinglish — what to keep?** For Hindi-English audio, **store the verbatim transcript, not a translation** — translation is one-way (you can't recover the original) and LLMs read Hinglish fine. **Deepgram `--language hi-Latn`** (the default `balanced` tier) gives clean romanized Hinglish; **ElevenLabs** (`accuracy` tier) gives native Devanagari. Either is a lossless source of truth an LLM can summarize or translate on demand. See the [building doc](https://github.com/rishmadaan/anyscribe/blob/main/docs/building/journal/2026-06-29-hinglish-transcript-format-and-llm-consumption.md) for the research behind this.

### Groq

The cheapest and fastest cloud option. Runs OpenAI's Whisper `large-v3-turbo` on Groq's accelerators and returns the same Whisper output anyscribe already parses (segment timestamps included).

```bash
anyscribe config set groq_api_key gsk-...
```

- **API key env var:** `GROQ_API_KEY`
- **Get a key:** [console.groq.com/keys](https://console.groq.com/keys)
- **Cost:** ~$0.04/hour — the cheapest cloud provider
- **File limit:** files over 25 MB or 30 minutes are split into pieces of about 18 minutes, the same as OpenAI
- **Default model:** `whisper-large-v3-turbo` — the fastest and cheapest
- **Also available:** `whisper-large-v3` — more accurate, a bit slower, and Groq allows bigger uploads for it. Worth switching to if the turbo model is dropping words: `anyscribe config set provider_models.groq whisper-large-v3`
- **Diarization:** No. For speaker labels, add a Deepgram key and run `anyscribe "<url>" --provider deepgram --diarize`

> **When to use:** the **`cost`** quality tier maps here. Great for bulk, low-cost transcription where you don't need speaker labels. Fast enough that long files fly through.

### OpenRouter

Access to various AI models through a unified API. Since OpenRouter doesn't have a dedicated speech-to-text endpoint, this uses audio-capable chat models with a transcription prompt.

```bash
anyscribe config set provider openrouter
```

- **API key env var:** `OPENROUTER_API_KEY`
- **Get a key:** [openrouter.ai/keys](https://openrouter.ai/keys)
- **Cost:** Varies by model (per-token pricing, generally more expensive than dedicated STT)
- **File limit:** files over 25 MB or 30 minutes are split into pieces of about 18 minutes, the same as OpenAI
- **No timestamps** — returns plain text only
- **Default model:** `openai/gpt-audio-mini`
- **Also suggested:** `google/gemini-2.5-flash-lite`, `google/gemini-2.5-flash`, `google/gemini-3-flash-preview`, `mistralai/voxtral-small-24b-2507`, `openai/gpt-audio`

```bash
anyscribe config set provider_models.openrouter google/gemini-2.5-flash
```

> **OpenRouter takes any model name.** Unlike the other providers, anyscribe doesn't check your choice against a list — type any audio-capable model name from [openrouter.ai/models](https://openrouter.ai/models) and it gets passed straight through. The flip side: a typo isn't caught until OpenRouter rejects it.

> **Keep your own models in the list.** Add the ones you use so they show up in every picker instead of being retyped:
>
> ```bash
> anyscribe config set extra_models.openrouter "qwen/qwen3-omni-flash,openai/gpt-audio"
> anyscribe config set extra_models.openrouter ""     # clears them
> ```
>
> They appear next to the built-ins, marked `(custom)`. OpenRouter is the only provider that accepts this — see [configuration.md](configuration.md#extra_models).

> **The old default is gone.** anyscribe used to default to `openai/gpt-4o-audio-preview`, which OpenRouter has since removed — requests to it now fail with a "model not found" error. The default is now `openai/gpt-audio-mini`. If you pinned the old one yourself, change it to a current model name.

> **`OPENROUTER_MODEL` in `.env` is no longer read** (removed in 0.15.0). Use `anyscribe config set provider_models.openrouter <slug>` instead, and delete the line from `~/.anyscribe/.env`. <!-- version-pin-ok -->

> **When to use:** When you need a specific model that's only available on OpenRouter. Not recommended as a primary transcription provider — dedicated STT APIs are faster, cheaper, and more accurate.

### Local (Parakeet and Whisper)

Runs entirely on your machine. No API key, no internet connection after setup, no cost. Two engines sit behind the one `local` provider: **Parakeet v3** (NVIDIA's speech model, run with onnx-asr) for English and 24 European languages, and **Whisper** (run with faster-whisper) for Hindi and 95+ other languages.

> **Also needs `ffmpeg`** on your system PATH. anyscribe uses ffmpeg to pre-process audio before handing it to the model — if ffmpeg isn't installed, local transcription will fail even after setup. Install via `brew install ffmpeg` (macOS), `winget install Gyan.FFmpeg` (Windows), or your distro's package manager (Linux).

**Setup is a single action** — pick whichever path fits your workflow; all of them do the same thing:

```bash
anyscribe local setup --model parakeet-v3
```

or in the Web UI, either:
- **First-run onboarding wizard** (opens automatically on your first `anyscribe ui` launch) — choose **On this computer**, answer "What language is most of your audio?", and click **Download … and set up**.
- **Settings → Providers → Local → "Set up local transcription"** at any time after onboarding.

or in the terminal wizard, choose **On this computer** when `anyscribe onboard` asks how to transcribe.

Setup installs the engines (faster-whisper and onnx-asr) into the same Python environment as anyscribe, downloads the model you picked, and records it as your local default. After that, local transcription is fully offline.

**Which model?**

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

- **English or another European language:** `parakeet-v3`. It was as accurate as the best Whisper model in our test, at about four times its speed.
- **Hindi or another Indian language:** `large-v3-turbo` (or `small` on a computer with less than 6 GB of memory).
- **A mix, e.g. English and Hindi:** keep `parakeet-v3` as the default and also run `anyscribe model pull large-v3-turbo`. anyscribe switches between them by itself.
- **Not sure?** Click **Help me choose** in **Settings → Providers → Local**: one question, and a suggestion in plain words based on your answer and your computer.

> **The language check (Parakeet only).** Parakeet writes nonsense on a language it doesn't know, so before it runs, anyscribe checks the language at the start, middle and end of each recording with Whisper Tiny (speech only, a few seconds; a 75 MB helper downloaded with Parakeet). If any of them is another language, it uses Whisper Large v3 Turbo (or the best other Whisper model you have) instead, and says so: in the terminal, in `--json` `notes`, in the dashboard's result, and in the transcript (`model:` and `notes:` in the frontmatter, plus a **Note** line under the details). If no Whisper model is downloaded it stops, tells you what to download, and writes nothing. If the check can't tell, it uses Whisper when one is downloaded, or runs Parakeet and says the check was unsure. If one recording switches language mid-sentence (Hinglish), make Whisper Large v3 Turbo your default instead. Set your language explicitly (for example `--language en`) to skip the check.

**Switching the default model:**

```bash
anyscribe config set local_model parakeet-v3
```

or pick a card in the Web UI's Local provider panel. In the Web UI, picking a model that isn't downloaded yet downloads it (and, for Parakeet, its language check) and makes it the default only once it's ready; if the download fails, your default stays as it was. `config set` only accepts a model that is ready and otherwise names the command, so pull it first with `anyscribe model pull <id>`.

**Managing downloaded models** (after setup):

| Command | What it does |
|---------|--------------|
| `anyscribe model list` | Show all 9 models with accuracy, speed, download size and cache status |
| `anyscribe model pull large-v3-turbo` | Download an additional model |
| `anyscribe model rm small --yes` | Delete a cached model (asks first; `--yes` skips the prompt) |
| `anyscribe model info parakeet-v3` | Inspect a single model: what it's for, its languages, its measured numbers |

Or use the model cards inside **Settings → Providers → Local** in the Web UI (Download, Delete and Reinstall on each card; the rest under **More models**).

- **GPU:** Whisper uses an NVIDIA CUDA graphics card automatically if one is available; Parakeet runs on the CPU.
- **Env-var override:** `ASCLI_LOCAL_MODEL=small anyscribe "<url>"` wins over the configured default for one invocation.
- **Existing setups don't change.** If you set up local transcription before Parakeet existed, your model stays what it was; `anyscribe local status` shows a one-line tip if Parakeet v3 would suit you.

**Removing local transcription** (uninstalls the engines and deletes every cached model):

```bash
anyscribe local teardown --yes
```

or click **"Remove local transcription"** at the bottom of the Local provider panel in the Web UI.

> **When to use:** When you're offline, want zero cost, or have privacy concerns about sending audio to cloud APIs. On our 6-core test desktop, Parakeet v3 transcribes an hour of audio in about 10 minutes; Whisper Large v3 Turbo takes about 40.

## Switching Providers

Change your default provider:

```bash
anyscribe config set provider elevenlabs
```

Override for a single transcription:

```bash
anyscribe "<url>" --provider local
```

## Switching Models

Change the model a provider uses, permanently:

```bash
anyscribe config set provider_models.openai gpt-transcribe
```

Or just for one transcription:

```bash
anyscribe "<url>" -p openai -m gpt-transcribe
```

Check what's in effect:

```bash
anyscribe providers list
```

See [Choosing a model within a provider](#choosing-a-model-within-a-provider) for the full list and the timestamps caveat.

## Adding API Keys

The quickest way to add an API key:

```bash
anyscribe config set deepgram_api_key YOUR_KEY
anyscribe config set openai_api_key sk-proj-...
anyscribe config set elevenlabs_api_key xi-...
anyscribe config set openrouter_api_key sk-or-...
anyscribe config set sargam_api_key YOUR_KEY
anyscribe config set groq_api_key gsk-...
```

These are stored in `~/.anyscribe/.env` automatically.

Or use the onboarding wizard:

```bash
anyscribe onboard --force
```

Or edit `~/.anyscribe/.env` directly.

Check that a provider loads and its API key is set. This does not validate the key or available credit:

```bash
anyscribe providers test elevenlabs
```

## Picking a language (Web UI)

Open Transcribe → Options to choose a language. The picker shows
anyscribe's bundled suggestions where available; these are not an exhaustive
list of current provider support. Groq currently has no bundled suggestions:
type the code yourself (`--language en` on the command line, or in the Web
UI's language field, which accepts typed codes).

OpenRouter is the exception: it accepts a prose instruction in the prompt
("Spanish", "French"), not a code, so the input stays free-text for that
provider.

The same dropdown drives the **Default language** field on the Settings
page — it follows whichever provider you pick as default.

## Diarization Auto-Routing

When you use `--diarize` without specifying a provider (`-p`), anyscribe automatically switches to **Deepgram** if a Deepgram API key is configured. This is because Deepgram's diarization is native and produces the most consistent speaker labels.

To override and use a specific provider for diarization:

```bash
anyscribe "url" --diarize --provider openai
```

> **Web UI naming:** "Diarize" appears as a `Multi-speaker` toggle in `anyscribe ui` and the `diarized` output format is labelled `with-speaker-labels` — the underlying behavior is identical.
