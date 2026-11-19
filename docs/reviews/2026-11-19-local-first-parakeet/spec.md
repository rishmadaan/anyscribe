# Spec: local-first anyscribe (Parakeet v3, language guard, guided picker)

Lead: Claude Opus 5.5 (session lead). Approved by the owner on 2026-11-19 (see `ask.md`).
Goal in one line: a new user with no API keys gets a fast, accurate, private
transcript, picks a local model the way Spokenly users do, and is told in
plain words why a model suits them; nothing a model can't do is ever silent.

## 0. Evidence this spec rests on (lead's own measurements, 2026-11-19)

Machine: Linux desktop, Intel i5-10600K (6 cores / 12 threads), 15 GB RAM,
no GPU. Test set A: 6 English clips (business pitch videos and creator voice
messages, 15.2 min, 3,244 words), reference = a commercial cloud transcript.
Test set B: 40 Hindi utterances from Google FLEURS `hi_in` dev (7.7 min, gold
human transcripts). Scoring: jiwer WER after lowercasing, stripping
punctuation and fillers (um/uh/…); CER for Hindi. Speed = audio seconds /
wall seconds of `transcribe()`, model already loaded, int8, CPU.

| Model (engine) | EN WER | × realtime | peak RAM | download |
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

Hindi (set B): turbo with `language=hi` CER 9.9 / WER 29.4; turbo with
`auto` CER 28.5 (auto-detect misfires on short clips); small `hi` CER 21.6;
parakeet-v3 CER 92.9 (romanized gibberish; Hindi is not one of its languages).
Language ID with Whisper `tiny` `detect_language` on the first 30 s: 40/40
Hindi clips and 6/6 English clips land on the correct side of "in Parakeet's
25 languages or not" (tiny said hi/ur/bn/tl for the Hindi ones), ~0.4 s/file.

Bugs found while testing the shipped v0.18.3 (each reproduced):
- B1. Fresh `pip install faster-whisper` now pulls PyAV 19.x (released
  2026-09-29); faster-whisper 1.2.1 (latest on PyPI, 2025-10-31) calls
  `av.open(..., metadata_errors=...)`, which PyAV 19 removed, so every local
  transcription crashes with `TypeError: open() got an unexpected keyword
  argument 'metadata_errors'`. Fixed upstream in SYSTRAN/faster-whisper#1495
  (merged 2026-09-30) but unreleased. With `av<19` it works.
- B2. `local setup` installs with `sys.executable -m pip`; an install made by
  `uv tool install` has no pip in its venv, so setup fails ("No module named pip").
- B3. Whisper turbo sometimes emits a whole file in lowercase with no
  punctuation (3 of 6 English clips that start mid-sentence). Passing
  `initial_prompt="Hello, and welcome. Here's what we'll cover today."`
  restored punctuation on all 3 (0 → ~0.2 marks per word), WER within noise.
  `condition_on_previous_text=False` did not help.
- B4. `MODEL_SPECS` text is contradicted by measurement ("large-v3: highest",
  "distil: near large-v3", turbo "~6x realtime").
- B5. JSON/frontmatter record `model: null` for local runs; the local model
  used is never recorded.
- B6. `OnboardingWizard.tsx` says "~145 MB for the recommended size" (stale
  since the recommendation became turbo) and falls back to `"base"`.
- B7. `LocalProvider.transcribe` reloads the model on every call (6–17 s per
  file in a batch). Cache the loaded model per (model, device) in the
  provider instance or module; keep it simple.

## 1. Decisions already made (do not reopen)

1. Engine for Parakeet: `onnx-asr` (MIT, PyPI, pure Python over onnxruntime
   + numpy; onnxruntime is already pulled in by faster-whisper). Install with
   the `hub` extra semantics (huggingface-hub is already present); no torch,
   no NeMo. Load `nemo-parakeet-tdt-0.6b-v3` with `quantization="int8"` and
   silero VAD (`onnx_asr.load_vad("silero")`, `.with_vad(vad)`); each VAD
   segment has `start`, `end`, `text` and becomes a `TranscriptSegment`.
   Model files come from HF repo `istupakov/parakeet-tdt-0.6b-v3-onnx` (and
   `istupakov/silero-vad-onnx`); they must land in the same HF cache the
   app already scans, so the existing list / delete / disk-usage code sees
   them. Pull only the files int8 needs if onnx-asr allows it.
2. Model ids (the strings in `settings.local_model`, the CLI, the API):
   keep the seven Whisper ids unchanged; add `parakeet-v3` and `parakeet-v2`.
   Display names: "Parakeet v3", "Parakeet v2", "Whisper Large v3 Turbo",
   "Whisper Large v3", "Whisper Medium", "Whisper Small", "Whisper Base",
   "Whisper Tiny", "Distil-Whisper Large v3.5".
3. `RECOMMENDED_MODEL = "parakeet-v3"`. `Settings.local_model` dataclass
   default stays `base` (an existing config keeps whatever it holds;
   nothing changes for existing users without them choosing).
4. Featured models (shown as cards, in this order): parakeet-v3
   (badge "recommended"), large-v3-turbo (badge "for Hindi" — wording may be
   "for Hindi & 95+ languages" where room allows), small, base. Everything
   else lives under "More models (5)" with a one-line honest reason
   (parakeet-v2: English only, v3 is as fast and more accurate; medium:
   slower than real time, no better than Small; large-v3: needs a graphics
   card to be practical; distil-large-v3.5: scored below Small in our test;
   tiny: very rough, used for the language check).
5. Every model carries measured, honest data in ONE registry (extend
   `MODEL_SPECS` in `providers/local_models.py`; nothing hard-coded in the UI):
   display name, engine (`whisper` | `parakeet`), accuracy 1–5, speed 1–5,
   minutes per hour of audio on the reference machine, download MB, RAM MB,
   languages (human text + a machine set for Parakeet), one "use it for"
   line, featured flag + order, badge, "why tucked away" line. Rating rule
   (so it can be re-derived): accuracy from EN WER — ≤6.7 → 5, ≤7.6 → 4,
   ≤10.5 → 3, else 2; speed from ×realtime — ≥12 → 5, ≥6 → 4, ≥2.5 → 3,
   ≥1.2 → 2, else 1. Minutes per hour = 60 / ×realtime, rounded. Record the
   reference machine and date next to the table (code comment + docs).
6. Language guard (the core safety rule: never write Parakeet gibberish
   silently). When the chosen local model is Parakeet:
   - language explicitly set to one of Parakeet v3's 25 (bg hr cs da nl en
     et fi fr de el hu it lv lt mt pl pt ro sk sl es sv ru uk; v2: en only)
     → run Parakeet.
   - language explicitly set to anything else → do not run Parakeet.
   - language `auto` → run Whisper `tiny` `detect_language` on the first
     30 s. In Parakeet's set → Parakeet. Not in it → do not run Parakeet.
   - "do not run Parakeet" means: use `large-v3-turbo` if cached, else the
     most accurate other cached multilingual Whisper model (by the registry
     ratings; never distil, which is English-weak), passing the detected or
     explicit language; and attach a note, e.g. "Detected Hindi — Parakeet v3
     doesn't cover Hindi, so this used Whisper Large v3 Turbo." If no
     suitable Whisper model is cached, fail with a clear, actionable error
     ("…download Whisper Large v3 Turbo: `anyscribe model pull
     large-v3-turbo`, or Settings → Local transcription") and write nothing.
   - If `tiny` is not cached when the guard needs it, fail with an
     actionable error (no silent network download mid-run). Setting up or
     pulling a Parakeet model always also pulls `tiny` (say so in the UI:
     "+ 75 MB language-check helper").
   - The note must reach every surface: CLI output and `--json` `notes`,
     the Web UI job result, MCP tool result, and the transcript's
     frontmatter/details (`model:` records the model actually used — fixes B5).
7. Whisper punctuation fix (B3): pass the `initial_prompt` above only when
   the language is English (explicit `en`, or `auto` whose detection says
   `en` — use `model.detect_language` on the loaded model first, it's cheap).
   Never for other languages.
8. Dependency pins: the `local` extra and the runtime install command used by
   `local setup` both install `faster-whisper>=1.0`, `av<19`, `onnx-asr`
   (pin a floor at the version tested, 0.12.0). Mark the `av` pin
   `# shortcut: faster-whisper 1.2.1 breaks on PyAV 19; drop once a
   faster-whisper release includes SYSTRAN/faster-whisper#1495`.
9. Install fallback (B2): when the running interpreter has no pip and `uv` is
   on PATH, install/uninstall with `uv pip install --python <sys.executable>`.
   Keep the existing pipx and pip paths. Existing users who already have
   faster-whisper but not onnx-asr must get onnx-asr when they first pick a
   Parakeet model (setup / pull of a parakeet id runs the install step if
   `onnx_asr` isn't importable) — not only on first-ever setup.
10. Guided choice ("help me choose" — the owner's addition). One backend
    function, e.g. `core/local_recommend.py: recommend(language_answer,
    hardware) -> {primary, also, reasons[]}`, used by CLI onboarding, the
    Web UI (setup wizard + Settings), and MCP (via an existing tool's
    output or the config/doctor surface — nothing is terminal-only or
    web-only). Inputs:
    - One question: "What language is most of your audio?" — English /
      Hindi or another Indian language / Another European language /
      A mix (e.g. English and Hindi) / Something else.
    - Hardware, detected, not asked: total RAM, CPU cores, Apple silicon,
      NVIDIA GPU present (cheap check: `ctranslate2.get_cuda_device_count()`
      if importable, else absent), free disk space in the model cache.
    Rules (keep them this small):
    - English or European → parakeet-v3 (reasons: "matches the most
      accurate local model on English at about 4× its speed", languages).
    - Hindi/Indian or Something else → large-v3-turbo if RAM ≥ 6 GB, else
      small (reasons name the RAM figure).
    - A mix → parakeet-v3 + large-v3-turbo, explained: "Parakeet handles
      English fast; anyscribe switches to Turbo automatically for Hindi."
    - RAM < 4 GB → base (any language), say why.
    - Not enough free disk for the pick → say so and offer the next smaller.
    Every recommendation renders as 1–3 plain sentences that cite the
    person's answer and the detected facts ("You said mostly English, and
    this computer has 16 GB of memory, so…"). Defaults pre-select the
    recommendation; the person can still pick any card.
11. Keyless-first onboarding: in the Web UI setup wizard and `anyscribe
    onboard` (interactive), the first choice is "On this computer — free,
    private, no API key (recommended)" vs "With a cloud service (needs an API
    key)". Choosing local runs the guided question, then setup. Headless
    `onboard --yes --provider local --local-model <id>` keeps working and
    accepts the new ids.
12. UI (Web, React in `ui/`, built into `src/anyscribe/web/static`): match
    the approved mockup `mockup.html` in this packet (cards with radio, badge,
    one-line "for", Accuracy n/5 + Speed n/5 shown as dots AND the number,
    "1 hour of audio ≈ N min", download, memory; status per card:
    downloaded / Download / downloading %; the language-check explainer box;
    "More models (5)" disclosure table). Use the existing theme tokens and
    components. Replace the pill strip + bare table on the Settings local
    card, `LocalSetupModal`, and the wizard's model step with the same card
    component (one component, three places). Keep existing capabilities:
    pull queue + progress, delete (with the "can't delete the only cached
    default" guard), reinstall, teardown, set default. A "Help me choose"
    control opens the guided question in place. Nothing on hover only;
    status in words, not colour alone; numbers in the mono font. Works at
    390 px wide.
13. CLI: `anyscribe model list` and `local status` show display name,
    accuracy n/5, speed n/5, min/hour, download, cached, default, and mark
    the recommended one; the onboarding wizard's model step shows the
    featured four first with their "for" line and offers "more models".
14. Existing users: nothing switches automatically. `doctor` / `local
    status` may print one line suggesting Parakeet v3 when the default is a
    Whisper model and the configured language is English or auto — a
    suggestion only.
15. Credits: add NVIDIA Parakeet (CC-BY-4.0, attribution: "Parakeet TDT
    0.6B v3 by NVIDIA, CC BY 4.0, converted to ONNX by istupakov") and
    onnx-asr (MIT) to the repo's third-party notices file(s) wherever the
    existing ones are listed (the web footer links `/THIRD-PARTY-LICENSES.md`).

## 2. Left to the builder

File layout inside the existing structure; how the provider dispatches
between engines (keep `LocalProvider` as the single `local` provider; no new
provider name); caching of loaded models; exact copy within the meaning
above; test structure.

## 3. Out of scope

GPU-specific Parakeet builds, Apple CoreML/MLX acceleration, Qwen3-ASR,
Nemotron, Cohere, any cloud provider change, Hinglish fine-tunes, a
"local only" switch, diarization for local, version bump and PyPI release
(lead does the release after the owner's yes).

## 4. Done-bar (the builder proves each in proof.md)

1. Full test suite green (`pytest -q`) plus ruff per repo config; new tests for:
   registry consistency (every id has every field; featured order),
   rating rule reproduces the table above, guard routing (explicit
   Parakeet language / explicit other / auto→en / auto→hi / no Whisper
   cached → error / tiny missing → error), install-command selection incl.
   the uv fallback, recommend() rules, note propagation to the result.
2. Mutation test, each run shown failing then passing: (a) remove the
   language guard → the auto→hi test must fail by asserting WHICH model ran
   (identity, not a count); (b) remove the `av<19` pin from the install
   spec → a test reading the actual install command must fail; (c) apply
   the English prompt unconditionally → a test asserting no prompt for `hi`
   must fail.
3. Real-engine runs, no mocks, with `HOME` and `HF_HOME` pointed at a
   throwaway folder (never the owner's real `~/.anyscribe`): fresh venv,
   `pip install -e '.[local]'` (proves av pin resolves),
   `anyscribe onboard --yes --provider local --local-model parakeet-v3`,
   then `anyscribe transcribe <english wav> --json` → Parakeet, punctuated
   text, `model: parakeet-v3`; `anyscribe transcribe <hindi wav> --json`
   with only tiny+parakeet cached → actionable error, no file written; pull
   `large-v3-turbo`, rerun → Turbo used, note present in JSON and in the
   written markdown. Test audio: the lead supplies paths in `target.md`.
   Timestamped output format with Parakeet produces real segment times.
4. Web UI walked in a real browser against a throwaway-HOME server
   (`anyscribe ui --port <spare> --no-open --local-only`): wizard with the
   guided question, Settings card (select, download with progress, delete,
   "Help me choose", More models), at 1440, ~1000 and 390 px; screenshots
   saved in this packet folder; every control clicked and its effect checked
   against `/api/...` responses or files on disk, not the DOM alone.
5. Docs per `AGENTS.md`: `docs/building/providers.md`, a journal entry
   (decision: why Parakeet + guard; include the measurement table and
   method), `docs/building/_index.md` row, user docs (`docs/user/…`
   local transcription / configuration / commands / getting-started as
   touched), the skill references under `src/anyscribe/skill/references/`
   that list model sizes, `CHANGELOG.md` (Unreleased), BACKLOG if it tracks
   this, and run `docs/building/COMMIT_CHECKLIST.md`'s greps for stale
   references (e.g. "~145 MB", "large-v3-turbo (default)", old size lists).
   Rebuild the docs site if the repo's checklist says so.
6. No owner data anywhere in the repo: no personal file names, paths, or
   transcript text in fixtures, docs or tests (the benchmark is described
   generically as above).

## 5. Round 3 design (lead's choice after the round-2 diagnosis, 2026-11-19)

Why: "choose a local model" is a five-step transaction (remember the intent,
download the model, download its helpers, download extras, switch the
default) that nothing owned; the browser sequenced it three times and each
fix guarded one interleaving. The server now owns it. This replaces the
client-side pending-default and extras logic.

1. **One readiness definition.** `runnable(model)` in
   `providers/local_models.py`: engine importable, weights complete, and for
   Parakeet also Tiny and VAD complete. `list_cached_models()` reports
   `runnable` beside `cached`; `cached` keeps meaning "weights on disk" for
   sizes and disk maths only. Every "is it ready / set up / testable" reader
   (status, the Test button, the CLI, `run_setup`'s set_up, the browser cards'
   "downloaded / ready" state) uses `runnable`.
2. **The one guarded switch.** `set_value("local_model", X)` in
   `core/config_set.py` refuses a model that is not runnable, naming the
   command (`anyscribe model pull X`) or the Settings action. This covers
   `PUT /api/config`, `anyscribe config set` and MCP `set_config` (a
   deliberate behaviour change: a not-ready default only fails later anyway;
   say so in CHANGELOG). Remove `_ensure_parakeet_helpers` and the config-set hint.
3. **One web "choose" operation.** `POST /api/local/choose {model, also}` on
   the existing download queue: records one server-side `pending_default`
   (a later call replaces it), queues the model and each `also` model plus
   helpers that are not runnable, and the queue worker switches the default
   only when the model is runnable; on any failure it clears the pending
   record with the error and the old default stays. If everything is already
   runnable it switches at once. `/api/local/status` reports
   `pending_default` (model, also, state, error). The pending record lives in
   server memory (a restart drops it; say so in the UI only if it is cheap).
4. **Setup takes the extras.** `POST /api/local/setup {model, also}`: after
   `run_setup` succeeds, the background setup queues the extras itself and
   reports them in status. `run_setup` keeps its order (download model and
   helpers, then switch the default).
5. **Help me choose only suggests in Settings.** The shared picker ignores
   any recommendation response that is not for the latest answer and passes
   every latest result to the parent, including "nothing fits" (which clears
   the selection and disables the download button). In Settings an answer
   highlights the suggested cards with a "Suggested" label and shows one
   button ("Use Parakeet v3 + Whisper Large v3 Turbo (downloads 2.3 GB)" /
   "Use Whisper Large v3 Turbo (already downloaded)"); only that button calls
   choose. Clicking a card in Settings calls choose for that card. In the
   wizard and setup modal an answer still moves the selection (nothing commits
   until the setup button); the redundant second Next button goes; every
   forward path sends `also`.
6. **Headless onboarding** writes the new default only after setup succeeds.
7. **R2C1 language routing, disjoint rules** (order no longer matters):
   (1) language set by the person: unchanged; (2) any uncovered-language
   window at probability >= 0.5: Whisper with that language, existing notes,
   error if no Whisper is runnable; (3) otherwise, if every window is below
   0.5, or any uncovered window is below 0.5: unsure path, Whisper with no
   forced language when one is runnable, else Parakeet with the unsure note
   and the result language taken from covered windows only (else "unknown");
   (4) otherwise Parakeet, language from the top covered window.
8. **Not in scope:** Playwright or any new UI test dependency (proof stays
   browser walks in a scratch folder, now including reply-reordering via
   request interception); the delete route not checking Parakeet's helpers
   (run-time message covers it); unifying the CLI paths (sequential, no races).
