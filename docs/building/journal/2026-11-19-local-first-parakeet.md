---
type: decision
tags: [providers, local, parakeet, whisper, onboarding, web-ui, mcp]
tldr: "Parakeet v3 (onnx-asr, int8) becomes the recommended local model: as accurate as Whisper Large v3 Turbo on English at about 4x its speed. A Whisper Tiny language check keeps it off languages it can't transcribe. Also fixes the PyAV 19 crash (av<19), uv installs without pip, lowercase Whisper output, and model: null for local runs."
---

# Local-first: Parakeet v3, a language guard, and a guided picker

## The decision

A new user with no API keys should get a fast, accurate, private transcript.
We added NVIDIA's Parakeet TDT 0.6B (v3 and v2) as local models next to the
seven Whisper sizes, made `parakeet-v3` the recommended model, and redesigned
the picker on every surface (Spokenly-style cards with honest ratings and a
"Help me choose" question).

Engine: `onnx-asr` (MIT, pure Python over onnxruntime + numpy; onnxruntime
already comes with faster-whisper). No torch, no NeMo. Weights are the int8
ONNX conversions from `istupakov/parakeet-tdt-0.6b-v3-onnx`, pulled into the
same Hugging Face cache the existing list/delete code scans. Canary-1B-v2 was
tried and rejected (less accurate and 3x slower than Parakeet).

## Measurements (2026-11-19)

Machine: Intel i5-10600K (6 cores / 12 threads), 15 GB RAM, no GPU.
English set: 6 clips (business pitch videos and voice messages), 15.2 min,
3,244 words; reference = a commercial cloud transcript. Hindi set: 40
utterances from Google FLEURS `hi_in` dev (7.7 min, human transcripts).
Scoring: jiwer WER after lowercasing and stripping punctuation and fillers
(um/uh/…); CER for Hindi. Speed = audio seconds / wall seconds of
`transcribe()` with the model already loaded, int8, CPU.

| Model (engine) | EN WER | x realtime | peak RAM | download |
|---|---|---|---|---|
| parakeet-tdt-0.6b-v3 (onnx-asr, int8, silero VAD) | 6.54 | 6.3 | 2.2 GB | ~670 MB |
| parakeet-tdt-0.6b-v2 (onnx-asr) | 7.50 | 6.5 | 2.5 GB | ~670 MB |
| canary-1b-v2 (onnx-asr) | 9.94 | 2.1 | 3.5 GB | ~1 GB (rejected) |
| large-v3-turbo (faster-whisper) | 6.63 | 1.5 | 3.1 GB | 1.6 GB |
| large-v3 | 7.19 | 0.4 | 6.4 GB | 2.9 GB |
| medium | 7.28 | 0.9 | 3.2 GB | 1.5 GB |
| small | 7.06 | 2.7 | 1.3 GB | 460 MB |
| base | 10.16 | 7.8 | 1.0 GB | 140 MB |
| tiny | 11.90 | 14.4 | 0.9 GB | 75 MB |
| distil-large-v3.5 | 10.01 | 1.9 | 2.7 GB | 1.4 GB |

Hindi: turbo with `language=hi` CER 9.9 / WER 29.4; turbo with `auto` CER
28.5 (auto-detect misfires on short clips); small `hi` CER 21.6; parakeet-v3
CER 92.9 (romanized gibberish; Hindi is not one of its languages).

Language ID on the first 30 s: Whisper `tiny` put 40/40 Hindi and 6/6
English clips on the right side of "in Parakeet's 25 languages or not", at
about 0.4 s per file. As an exact language it said Hindi for 36/40 (2 Urdu,
1 Bengali, 1 Tagalog). Turbo's own detection did worse on the same clips
(33/40 Hindi, 6 Urdu, 1 Latin) at 8.4 s per file, so the guard passes Tiny's
language to the fallback model instead of letting Turbo detect again.

The 1-5 ratings and "minutes per hour of audio" are derived from these
numbers by a fixed rule (see `docs/building/providers.md` → Local), so they
can be re-derived when someone re-measures.

## Why the guard

Parakeet writes confident gibberish on a language it doesn't know (CER 92.9
on Hindi). Silent gibberish is the worst outcome, so Parakeet never runs on a
language outside its set: an explicit language outside it, or an `auto` run
where Tiny hears another language, goes to Whisper Large v3 Turbo (or the
best other cached multilingual Whisper) with a note on every surface:
"Detected Hindi — Parakeet v3 doesn't cover Hindi, so this used Whisper Large
v3 Turbo." If no Whisper model is cached, or Tiny itself is missing, the run
fails with the download command and writes nothing. Pulling a Parakeet model
always pulls Tiny (+75 MB), so the normal path never hits that error.

## Bugs fixed on the way (all reproduced on v0.18.3)

- **PyAV 19**: a fresh `pip install faster-whisper` pulls PyAV 19.x (released
  2026-09-29); faster-whisper 1.2.1 calls `av.open(..., metadata_errors=...)`,
  which PyAV 19 removed, so every local run crashed. Pinned `av<19` in the
  `local` extra and in what `local setup` installs; fixed upstream in
  SYSTRAN/faster-whisper#1495 but not yet released. Marked as a `shortcut:`.
- **uv installs**: `local setup` ran `sys.executable -m pip`; a `uv tool
  install` venv has no pip. Falls back to `uv pip install --python
  <interpreter>` when uv is on PATH.
- **Lowercase Whisper**: turbo sometimes wrote a whole file lowercase with no
  punctuation (3 of 6 English clips that start mid-sentence). An English-only
  `initial_prompt` restored punctuation on all 3 with WER within noise;
  `condition_on_previous_text=False` did not help.
- **Model specs** claimed "large-v3: highest", turbo "~6x realtime": replaced
  by measured figures.
- **`model: null`** in JSON/frontmatter for local runs: the model that ran is
  now recorded.
- **Wizard copy** said "~145 MB for the recommended size" and fell back to
  `base`; it now reads the registry.
- **Model reload per file** (6-17 s each in a batch): loaded models are cached.
- Found in the browser walk: tall dialogs pushed their buttons off-screen
  (the dialog now scrolls), and the sidebar ate a phone's width (it stacks
  on narrow screens).

## What did not change

Existing users: `Settings.local_model` still defaults to `base`, and nothing
switches on its own. `local status`, `doctor` and the Settings card show a
one-line suggestion to try Parakeet v3 when the default is a Whisper model
and the language is English or auto. Cloud providers are untouched.

## Out of scope

GPU Parakeet builds, Apple CoreML/MLX, Qwen3-ASR, Nemotron, diarization for
local, a "local only" switch.
