# Proof — local-first build (Implementer, round 0)

Branch `feat/local-first-parakeet`, started at `c3e8105` (checked with
`git rev-parse HEAD` before editing). Commits on top:

```
6a2079f Add Parakeet to the local model registry, pin av<19, uv install fallback
c3375cf Language guard for Parakeet, English prompt for Whisper, notes on every surface
61ab665 Web UI: one local-model picker for Settings, setup and the first-run wizard
301ab2f Headless onboarding reports the local model it set up
530ba48 Test that a Parakeet pull fetches its int8 files and helpers
98709cb Web UI fixes found in the browser walk
f809b7a Docs for local-first transcription: Parakeet, language guard, Help me choose
(+ this proof commit)
```

Notation: `$S` is the session scratch folder named in `target.md`. Every real
run used `HOME=$S/real/home HF_HOME=$S/real/hf` (CLI) or
`HOME=$S/web/home HF_HOME=$S/web/hf` (Web UI); both started empty. The
owner's `~/.anyscribe` and `~/anyscribe` were never touched; no key file was
read. Transcript text from the test clips is not quoted here (only counts).

---

## 1. Full suite + ruff, and the new tests

```
$ .venv/bin/pytest -q
830 passed, 5 skipped, 134 warnings in 47.98s        (baseline at c3e8105: 754 passed, 5 skipped)
$ .venv/bin/ruff check src tests scripts
All checks passed!
$ .venv/bin/ruff format --check <every changed/new python file>
56 files already formatted
$ cd ui && npx tsc -b && npm run lint && npm run build
(clean; built in ~0.5 s)
$ python scripts/check-docs.py ; echo $?
0
```

New test files, by what the done-bar asked for:

| Ask | Tests |
|---|---|
| Registry consistency (every id has every field; featured order) | `tests/test_local_registry.py`: `test_every_model_has_every_field` (9 ids), `test_whisper_ids_unchanged_and_parakeet_added`, `test_featured_order_and_recommended`, `test_display_names` |
| Rating rule reproduces the spec table | `test_rating_rule_reproduces_measured_table` (all 9 rows: accuracy, speed, min/hour), `test_rating_rule_boundaries` |
| Guard routing | `tests/test_local_guard.py`: explicit Parakeet language (`fr` → parakeet, no check), explicit other (`hi` → turbo + note), auto→en (parakeet, real segment times), auto→hi (turbo, `language="hi"`, note), parakeet-v2 `de` → Whisper, no Whisper cached → error naming `anyscribe model pull large-v3-turbo`, tiny missing → error naming `anyscribe model pull tiny`, fallback order (turbo, then most accurate cached; never distil/tiny) |
| Install-command selection incl. uv fallback | `tests/test_local_install.py`: pip argv (exact list incl. `av<19`, `onnx-asr>=0.12.0`), pipx inject argv, uv fallback argv + `method: "uv"`, pip preferred when present, no pip + no uv, uv uninstall argv, older install without onnx-asr → install runs, PyAV 19 counts as not ready, failed install surfaced, `pyproject` `local` extra == `LOCAL_RUNTIME_SPECS` |
| recommend() rules | `tests/test_local_recommend.py`: English/European → parakeet-v3, Hindi/other ≥6 GB → turbo, Hindi 5 GB → small, mix → parakeet + turbo with the required sentence, <4 GB → base for all 5 answers, low disk steps down / drops the second model with a sentence, cached models need no disk, 1-3 sentences, bad answer rejected, real `detect_hardware()`, Parakeet suggestion only for Whisper users on en/auto, Web route `/api/local/recommend`, MCP `doctor` `local` block, `local status --json` `recommendations` |
| Note propagation to the result | `test_switch_note_reaches_result_and_markdown` (provider → `ProcessResult` → frontmatter `model:` + `notes:` + `> **Note:**` line), `test_parakeet_run_records_model_and_timestamps`, `test_guard_error_writes_nothing`, `test_cli_json_carries_the_note`, `test_mcp_transcribe_carries_the_note` (single + batch), `test_web_job_result_carries_the_note` (runs `JobManager._run_job`) |
| (extra) Parakeet pull fetches int8 files + helpers | `tests/test_local_pull.py`: parakeet → `[parakeet repo with PARAKEET_FILES, silero VAD, faster-whisper-tiny]`, tiny skipped when cached, Whisper pulls only its repo, teardown deletes the VAD repo |
| (extra) Credits ship | `test_parakeet_attribution_ships_in_both_notice_files` (NOTICE + built `THIRD-PARTY-LICENSES.md`) |

## 2. Mutation tests (failing with the guard removed, passing restored)

Each mutant edited the source, ran the named test, then `git checkout` restored
the file. Assertions name the model or the command, never a count.

**(a) Language guard removed** — `plan()` returns the configured model unconditionally:

```
$ pytest tests/test_local_guard.py -k auto_hindi        # mutant
E       AssertionError: assert 'parakeet-v3' == 'large-v3-turbo'
E         - large-v3-turbo
E         + parakeet-v3
1 failed, 16 deselected
$ (restored)
1 passed, 16 deselected
```

**(b) `av<19` removed from `LOCAL_RUNTIME_SPECS`:**

```
$ pytest tests/test_local_install.py -k av_pin           # mutant
E       AssertionError: assert ['<venv python>', ...] == ['<venv python>', ... 'av<19', ...]
E         At index 5 diff: 'onnx-asr>=0.12.0' != 'av<19'
E       AssertionError: assert ['pipx', 'inj...-asr>=0.12.0'] == ['pipx', 'inj...-asr>=0.12.0']
E         At index 4 diff: 'onnx-asr>=0.12.0' != 'av<19'
2 failed, 8 deselected
$ (restored)
2 passed, 8 deselected
```

(`test_pyproject_local_extra_matches_runtime_install` also fails under that mutant: the extra still carries `av<19`.)

**(c) English prompt applied unconditionally:**

```
$ pytest tests/test_local_guard.py -k hindi_gets_no_prompt    # mutant
E       assert 'initial_prompt' not in {'beam_size': 5, 'vad_filter': True, 'language': 'hi',
                                        'initial_prompt': "Hello, and welcome. Here's what we'll cover today."}
1 failed, 16 deselected
$ (restored)
1 passed, 16 deselected
```

Further guards, same method (script `$S/mut/run.py`):

| Mutant | Failing assertion | Restored |
|---|---|---|
| (d) Tiny-missing check removed | `Failed: DID NOT RAISE RuntimeError` (test_tiny_missing…) | 1 passed |
| (e) Distil allowed as fallback | `DID NOT RAISE RuntimeError`; `assert 'distil-large-v3.5' is None` | 2 passed |
| (f) uv fallback removed | `At index 0 diff: '<venv python>' != 'uv'` (install and uninstall) | 2 passed |
| (g) onnx-asr not required for "ready" | `assert True is False` (local_runtime_ready with onnx-asr missing) | 1 passed |
| (h) PyAV 19 not detected | `assert True is False` (local_runtime_ready with av 19.0.0) | 1 passed |
| (i) Tiny not pulled with Parakeet | `Right contains one more item: ('Systran/faster-whisper-tiny', None)` | 4 passed |

## 3. Real-engine runs (no mocks)

Fresh venv with pip (`uv venv --seed`), then the package's own extra:

```
$ $S/real/venv/bin/pip install -e '.[local]'     → rc=0
$ pip list
anyscribe 0.18.3 (editable) · av 18.1.0 · ctranslate2 4.9.0 · faster-whisper 1.2.1 · onnx-asr 0.12.0 · onnxruntime 1.32.0
```
→ the `av<19` pin resolved (18.1.0) on a clean resolve.

Headless onboarding into an **empty** `HF_HOME` (the fresh-download proof for parakeet-v3 + tiny):

```
$ anyscribe onboard --yes --provider local --local-model parakeet-v3      (35.7 s wall)
Onboarded. Provider: local (quality: custom, model: n/a), workspace: $S/real/home/anyscribe.
  Local transcription ready.
$ ls $S/real/hf/hub
models--istupakov--parakeet-tdt-0.6b-v3-onnx  models--istupakov--silero-vad-onnx  models--Systran--faster-whisper-tiny
$ (snapshot files) decoder_joint-model.int8.onnx  config.json  encoder-model.int8.onnx  vocab.txt     ← int8 only
$ grep config.yaml → provider: local · local_model: parakeet-v3
```
(The "model: n/a" in that summary line was fixed afterwards in `301ab2f`: the headless result now reports `parakeet-v3` for local.)

English clip → Parakeet:

```
$ anyscribe transcribe $S/testaudio/english-1.wav --json        (12.0 s wall incl. model load, 70 s clip)
"language": "en", "word_count": 273, "provider": "local", "model": "parakeet-v3", "notes": [], "cached": false
$ head of the written markdown:
provider: local
model: parakeet-v3
→ punctuation: 0.14 marks per word; 37 capitalised words in 273 (the clip starts mid-sentence)
```

Hindi clip with only Tiny + Parakeet cached → actionable error, nothing written:

```
$ anyscribe transcribe $S/testaudio/hindi-1.wav --json ; echo rc=$?
rc=1
"error": "Detected Hindi, which Parakeet v3 doesn't cover, and no Whisper model to use instead is downloaded.
          Download Whisper Large v3 Turbo: `anyscribe model pull large-v3-turbo`, or Settings → Local transcription.
          Nothing was written."
$ ls $S/real/home/anyscribe/sources/local/
english-1.md                ← unchanged; no hindi-1.md
```
(The existing recovery behaviour kept the prepared audio in `~/.anyscribe/recovery/`.)

Pull Turbo (a real 1.6 GB download into the throwaway cache), rerun:

```
$ anyscribe model pull large-v3-turbo --json        (54 s)
{"status": "downloaded", "size": "large-v3-turbo", "repo": "dropbox-dash/faster-whisper-large-v3-turbo", "bytes": 1621668947}
$ anyscribe transcribe $S/testaudio/hindi-1.wav --json        (73 s wall)
"language": "hi", "word_count": 82, "model": "large-v3-turbo",
"notes": ["Detected Hindi — Parakeet v3 doesn't cover Hindi, so this used Whisper Large v3 Turbo."]
stderr:   Note: Detected Hindi — Parakeet v3 doesn't cover Hindi, so this used Whisper Large v3 Turbo.
markdown: model: large-v3-turbo
          notes:
            - "Detected Hindi — Parakeet v3 doesn't cover Hindi, so this used Whisper Large v3 Turbo."
          line 26: > **Note:** Detected Hindi — Parakeet v3 doesn't cover Hindi, so this used Whisper Large v3 Turbo.
          transcript body: 300 of 387 non-space characters are Devanagari
$ (same command again) → cached: True, model: large-v3-turbo   ← read back from the frontmatter
```

Timestamped output with Parakeet (real VAD segment times):

```
$ anyscribe config set output_format timestamped
$ anyscribe transcribe $S/testaudio/english-1.wav --json --force → model parakeet-v3, notes []
$ grep -o '^\*\*\[..\]' english-1-2.md   (19 segments)
[0:00] [0:03] [0:07] [0:11] [0:15] [0:17] [0:21] [0:22] [0:28] [0:31] [0:34] [0:37] [0:41] [0:52] [0:57] [0:59] [1:01] [1:03] [1:06]
```

URL path (public video from `target.md`):

```
$ anyscribe transcribe "https://www.youtube.com/watch?v=jNQXAC9IVRw" --json    (13.7 s)
success True · model parakeet-v3 · language en · notes [] · 38 words · sources/youtube/me-at-the-zoo.md
```

CLI human surfaces (throwaway home, after the Web UI teardown below removed the engines from that venv, hence "not installed"):

```
$ anyscribe model info parakeet-v3
Parakeet v3 (parakeet-v3)
  For:       English and 24 European languages. Fastest accurate option.
  Accuracy:  5/5  (English word error 6.54%)
  Speed:     4/5  (1 hour of audio ≈ 10 min)
  Download:  ~670 MB · Memory: ~2200 MB while transcribing · Status: cached · Disk: 639 MB
$ anyscribe model list    → table: Model · Id · Accuracy · Speed · 1 h audio · Download · Status,
                            "Parakeet v3 · default, recommended", featured four first, tiny last
$ anyscribe local status  → engines rows (faster-whisper, onnx-asr), same model table, and with a Whisper default:
  Tip: Parakeet v3 is rated 5/5 for accuracy and 4/5 for speed (your Whisper Large v3 Turbo: 5/5, 2/5) on English.
  Try it: anyscribe local setup --model parakeet-v3
$ anyscribe doctor        → the same Tip line under Configuration (provider local, Whisper default)
```

Language-check data point I measured while building (40 FLEURS Hindi clips, first 30 s):
Tiny said `hi` 36, `ur` 2, `bn` 1, `tl` 1 (0.36 s/file); Turbo's own detection said `hi` 33, `ur` 6, `la` 1 (8.4 s/file).
So passing Tiny's language to the fallback (what the spec says, and what was built) beats letting Turbo re-detect.

## 4. Web UI walked in a real browser

Server: `HOME=$S/web/home HF_HOME=$S/web/hf anyscribe ui --port 8491 --no-open --local-only` (fresh home, empty cache), driven by headless Google Chrome through Playwright (scratch venv, not a repo dependency). Every effect was checked against `/api/...` or the cache on disk. Server stopped at the end by port (pid read first: `.../real/venv/bin/anyscribe ui --port 8491 --no-open --local-only`).

**Wizard** (`$S/web/wizard.py`):

```
[390px]  page scrollWidth=390 (no horizontal scroll) · local step scrollWidth=390
[1000px] page scrollWidth=1000 · local step scrollWidth=1000
With a cloud service → list: openai, deepgram, groq, elevenlabs, sargam, openrouter
On this computer → preselected card: parakeet-v3 | /api/local/status recommended_model: parakeet-v3
"A mix (e.g. English and Hindi)" → UI: "Suggested: Parakeet v3 + Whisper Large v3 Turbo"
   API /api/local/recommend?answer=mix: parakeet-v3 ['large-v3-turbo'] | reasons[0]: "You said a mix of languages, and this
   computer has 15.5 GB of memory, so anyscribe uses two models: Parakeet handles English fast; anyscribe switches to Turbo
   automatically for Hindi."   → every API reason sentence is on the page: yes
"Use this" → checked card parakeet-v3 · language-check box visible: True
Button label: "Download Parakeet v3 and set up" → clicked
setup finished in 37 s; progress buckets seen in /api/local/status: [0, 25, 50, 75, 100]
after setup: cached = ['parakeet-v3', 'tiny'] | default_model = parakeet-v3 | runtime_ready = True
download queue after setup (the 'also' from Help me choose): ['large-v3-turbo'] downloading=True
Finish → /api/config: provider = local | local_model = parakeet-v3 | quality = custom · onboarding completed: True
```

**Settings → Providers → local** (`$S/web/settings.py`, re-run after fixes; values from the final runs):

```
[390px] scrollWidth=390 · picker width 324 px | [1000px] 1000 · 670 px | [1440px] 1440 · 670 px
select Turbo card (default was parakeet-v3)  → /api/config local_model = large-v3-turbo, aria-checked true
language-check box hidden for a Whisper default: True
click uncached Base card → config unchanged, aria-disabled: true (only downloaded models can be the default)
Download Whisper Small → card text mid-download "… downloading 15.8%";
   progress buckets via /api/models/local: [0, 20, 40, 60, 80, 100] | cached True | repo dir on disk: True
Delete Whisper Small → /api/models/local cached False | models--Systran--faster-whisper-small on disk: False | card shows "Download"
Help me choose → English → UI "Suggested: Parakeet v3" | API primary parakeet-v3
   Use this → /api/config local_model = parakeet-v3 · language-check box shown: True
More models (5) — older or slower options → rows: parakeet-v2, medium, large-v3, distil-large-v3.5, tiny
   tiny row: "downloaded · 75 MB · needed for the language check", Delete button present: 0 (Parakeet is the default)
   Parakeet v2 radio disabled (not downloaded): True
Reinstall Whisper Tiny → reinstalled | freed 78207087 | downloaded 78207087 | cached after: True
```

**A transcription job through the dashboard** (`$S/web/job.py`, Hindi clip, Parakeet default):

```
POST /api/transcribe → provider local
result card note: "Detected Hindi — Parakeet v3 doesn't cover Hindi, so this used Whisper Large v3 Turbo."
result card provider cell: "local · large-v3-turbo"
GET /api/jobs/<id> → result.model = large-v3-turbo | result.notes = [that note]
```

**Teardown** (`$S/web/teardown.py`): "Remove local transcription" → "Uninstall the local engines and delete all models?" → Confirm →
`removed ['parakeet-v3','large-v3-turbo','tiny'] | uninstall: removed (… faster-whisper onnx-asr) | provider_reset: True`;
after: no cached models, total bytes 0, the HF hub folder holds no repo directories (VAD repo gone too); `pip list` in that venv shows only `av`.

Screenshots (moved by the lead out of the public repo to the review run folder `~/.review-runs/2026-11-19-local-first-parakeet/screens/`; the one path visible in the result screenshot is masked):

- `wizard-1-choice-390.png`, `wizard-1-choice-1000.png`, `wizard-1-choice-1440.png` — On this computer vs cloud
- `wizard-2-local-390.png`, `wizard-2-local-1000.png` — guided question open, cards
- `wizard-3-recommendation-1440.png` — mix answer, reasons, Parakeet selected
- `wizard-4-done-1440.png` — summary step
- `settings-local-390.png`, `settings-local-1000.png`, `settings-local-1440.png` — the local card
- `settings-downloading-1440.png` — Small downloading with percent
- `settings-help-me-choose-1440.png` — after Use this, with the language-check box
- `settings-more-models-1440.png` — the five tucked models with reasons and status
- `result-note-1440.png` — the switch note on the result card

Bugs the walk found, fixed in `98709cb`:
1. The wizard's model step was taller than a 900 px window and the shared `Modal` doesn't scroll, so "Download … and set up" was unreachable (Playwright: "element is outside of the viewport"). The dialog now scrolls (`max-h-[calc(100dvh-2rem)] overflow-y-auto`).
2. With the actions inside the `role="radio"` card, an undownloaded card's `aria-disabled` made its own Download button read as disabled (Playwright refused the click for that reason, as assistive tech would). The radio is now the left part only; actions are siblings.
3. At 390 px the fixed 224 px sidebar left the Settings page ~100 px wide (first 390 screenshot, a column of one word per line). The sidebar now stacks above the page below the `sm` breakpoint, and Settings uses 16 px side gutters.

## 5. Docs

Updated per `AGENTS.md` / `COMMIT_CHECKLIST.md`:
`docs/building/providers.md` (Local rewritten: engines, registry, rating rule + reference machine, guard, notes, prompt, cache, install pins, Help me choose),
`docs/building/architecture.md` (provider line, core modules, feature-coverage matrix row for Help me choose),
`docs/building/journal/2026-11-19-local-first-parakeet.md` (decision, measurement table and method, Hindi detection numbers, bugs) + `docs/building/_index.md` row,
`docs/user/getting-started.md`, `configuration.md` (measured model table, the language check), `commands.md`, `providers.md`, `troubleshooting.md` (new entries: onnx-asr missing, no pip, `metadata_errors`, the guard's two errors), `agents.md` (capability rows),
skill: `SKILL.md`, `references/commands.md`, `providers.md`, `config.md`, `troubleshooting.md`,
`README.md`, `CLAUDE.md`, `AGENTS.md`, `CHANGELOG.md` (Unreleased), `BACKLOG.md` (feature checklist line; no version row — release is the lead's),
`landing/docs/*.html` regenerated with `python scripts/build-docs.py`; `scripts/check-docs.py` exits 0 (three deliberate "faster-whisper 1.2.1" mentions carry `<!-- version-pin-ok -->`).
Stale-reference greps (`~145 MB`, `145 MB`, `large-v3-turbo (default)`, old "recommended" rows, `relative_speed`, "near large-v3, ~6x") across README, CLAUDE, AGENTS, docs/user, docs/building, src, ui/src: no hits. TODO/FIXME grep on the new files: none.
Credits: `NOTICE` and the web footer's `/THIRD-PARTY-LICENSES.md` (appended at build time from `ui/model-notices.md` by a 10-line Vite plugin, since that file is regenerated on every build) carry "Parakeet TDT 0.6B v3 by NVIDIA, CC BY 4.0, converted to ONNX by istupakov", v2, onnx-asr (MIT, Ilya Stupakov — from its package metadata), Silero VAD, faster-whisper/Whisper.

## 6. No owner data

Fixtures are synthetic (zero arrays, fake segments "Hello there." / "Second part."). Docs describe the benchmark generically. No transcript text from the test clips appears in the repo or here. `grep -rn "rish\|/home/"` over the new tests, journal and this file: none (the packet's own `target.md` already named the scratch path; this file writes `$S`). The result screenshot's file-path row is masked.

---

## Existing tests changed, and why

| Test | Change | Why |
|---|---|---|
| `tests/test_local_cli.py::test_setup_without_model_exits_2_with_json_error` | `recommended == "large-v3-turbo"` → `"parakeet-v3"` | Spec §1.3 changes `RECOMMENDED_MODEL` |
| `tests/test_onboard_headless.py::test_validation_requires_local_model_for_local_provider` | same | same |
| `tests/test_local_cli.py::test_setup_already_set_up_is_noop`, `test_setup_runs_run_setup_and_reports_set_up` | fake status gains `runtime_ready` | "already set up" now requires both engines (onnx-asr) and a usable PyAV, not just faster-whisper (spec §1.9) |
| `tests/test_local_setup.py::test_install_command_uses_pipx_inject_for_pipx_method` | expects `[... , *LOCAL_RUNTIME_SPECS]` | install now carries `av<19` and `onnx-asr` (spec §1.8) |
| `tests/test_local_setup.py::test_install_command_uses_pip_for_venv_method` | `cmd[-3:] == LOCAL_RUNTIME_SPECS`; pins `_pip_available=True` | same; and the dev venv (made by uv) has no pip, so without the pin the new uv fallback would (correctly) be chosen |
| `tests/test_local_setup.py::test_install_reports_failure_with_stderr` | pins `_pip_available=True` | same reason |
| `tests/test_local_setup.py::test_install_is_noop_when_already_importable` | patches `local_runtime_ready` instead of `faster_whisper_importable` | "already installed" is now the whole runtime |

No existing test was deleted or loosened.

## Beyond the spec (small, say if unwanted)

- `anyscribe local status --json` also carries `question`, `recommendations` (per answer) and `hardware`, so agents using the skill (CLI) get Help me choose, not only MCP. MCP gets it in `doctor` → `local`.
- `Settings`: Help me choose with a not-yet-downloaded pick downloads it (and any `also`) and makes it the default when the download lands (a "pending default"), since only downloaded models can be the default.
- Fixed a pre-existing interactive-onboarding bug: the wizard's final `save_config` wrote the stale in-memory `local_model` back over what `run_setup` had saved.
- Web `local` provider test (Diagnose) checks onnx-asr when the default is Parakeet; provider description reads "On this computer: free, private, no API key (Parakeet or Whisper)".
- The Modal scroll and phone-width sidebar fixes (section 4) touch shared components (`Modal.tsx`, `Layout.tsx`).

## Skipped or not proven, with reasons

1. **Interactive `anyscribe onboard` (the beaupy TUI)** was not driven in a real terminal; it was only type/lint-checked and its backend (`recommend`, `run_setup`, `pull_model`) is tested. Reason: it needs a TTY with arrow keys; I did not set up a pty driver. The headless path was run for real.
2. **Whisper English prompt on real audio**: covered by unit tests and the mutation (c); not re-measured here (the lead measured it in B3). The real English run used Parakeet.
3. **macOS / Windows / Apple silicon**: not run. RAM detection uses `os.sysconf` (Linux/macOS) and `GlobalMemoryStatusEx` on Windows; the Windows branch is untested.
4. **GPU path**: no GPU on this machine; `nvidia_gpu` is reported but no rule uses it (the spec's rules don't).

## Risks and spec notes for the lead

- **Tiny's language goes to the fallback** (spec §1.6, built as written). Tiny said Urdu for 2 of 40 Hindi clips, so those would come out in Urdu script from Turbo. Turbo's own detection was worse (6 of 40 Urdu), so this is still the better option; a future `hi`/`ur` merge would need a decision.
- **"Cached" means "any bytes on disk"** (pre-existing `is_cached`). During a download the model already counts as cached: `/api/models/local` showed `cached: true` at 28 % of Turbo. The card shows "downloading" first so the UI is right, but the guard's `pick_fallback` could choose a half-downloaded Turbo during that window (it would fail loudly loading it, not write gibberish). Not changed; it is how every model behaved before.
- **Silent downloads that remain**: if `local_model` is set to an uncached Parakeet via `config set`, or the 2 MB Silero VAD was deleted by hand, onnx-asr downloads it at run time (same as faster-whisper does for an uncached Whisper size today). Only Tiny got the spec's hard error.
- **Memory in the long-lived Web UI server**: the model cache keeps one big model plus Tiny loaded (up to ~3-4 GB with Turbo) after a job. That is the price of no per-file reload (B7).
- **Pre-existing Transcribe-page race**: submitting before the page has loaded `/api/config` sends `quality: "balanced"` (the page's initial state), which produced a "wants deepgram" WARNING plan note in my scripted job. Not touched (outside scope); the run still used local.
- The `av<19` pin lives in two places (the `local` extra and `LOCAL_RUNTIME_SPECS`); a test keeps them equal. Both carry the `shortcut:` comment.

---

## Round 1 fixes

Fixer: Claude Opus 5.5 (Agent tool), from 63039aa. Commits b1dbe53..5f33d1b on `feat/local-first-parakeet`.
Real-engine and browser runs used throwaway HOME/HF_HOME folders under `<lead scratch folder>/fixer/`; screenshots are in `~/.review-runs/2026-11-19-local-first-parakeet/screens/fx-*.png` (none committed). Every server started was stopped by port after reading its pid's command line.
Final checks at 5f33d1b: `pytest -q` 861 passed, 5 skipped; `ruff check src tests` clean; `ui`: `tsc -b`, `npm run lint`, `npm run build` clean, and the rebuilt `web/static` matches the commit (`git status` empty after a rebuild); `scripts/check-docs.py` exit 0; `landing/docs` regenerated with `scripts/build-docs.py`.

**C1 / F1 (stale quality after the wizard)** | Changed: TranscribePage sends `quality` only when picked on that page (`qualityPicked`), the URL box is disabled until config loads, and App remounts TranscribePage (key bump) when the wizard closes (c574cd4). | Ran: real-browser walk on a fresh HOME (`c1.py`: wizard, local, English, set up, Finish, then transcribe in the same page session), with the fix and with both parts reverted. | Saw: fixed: `quality sent: <not sent>`, `plan notes: []`, job ran `parakeet-v3`. Mutant (quality always sent, no remount): `quality sent: balanced`, `plan notes: ["WARNING: quality 'balanced' wants deepgram but no DEEPGRAM_API_KEY is set — using local instead"]`. Deliberate tier clicks still send `quality` (unchanged path). Note: each of the two parts alone fixes this path (the remount reloads `quality: custom`; not sending it lets the server use the config), so reverting only one would not show the warning; I proved the pair, not each half.

**C2 (language check)** | Changed: `_speech_windows` (Silero VAD from faster-whisper, speech only, up to three 30 s windows: start, middle, end; fewer for short speech); `plan()` routes to Whisper when ANY window's top language is outside the set; unsure (all windows < 0.5 or no speech) uses a ready Whisper with `language=None`, else Parakeet plus a note; Whisper-default `auto` passes `language=None` again with a VAD-filtered `detect_language` on the loaded model deciding only the English prompt; the fallback still passes the detected language (b53cbeb). Explicit-label bypass untouched (declined.md). | Ran: `tests/test_local_guard.py` (8 new tests) and four mutants; real engine on a throwaway HOME with parakeet-v3 as default: an ffmpeg clip of 35 s of English followed by the Hindi clip (72 s), a clip of 10 s of silence then English, plus English-35 s and Hindi alone. | Saw: mutant "only the opening window decides": `assert ('parakeet-v3' == 'large-v3-turbo'` in `test_english_start_then_hindi_routes_to_whisper` and `test_only_the_end_window_outside_still_routes_to_whisper`; mutant "unsure branch removed": `assert [] == ['The languag...']` and `ValueError: max() iterable argument is empty`; mutant "no VAD windows": `assert [(0, 30)] == [(0, 30), (30, 30), (60, 30)]`; mutant "Whisper-only auto forces a language": 3 failures incl. `test_whisper_auto_detected_hindi_is_not_forced`; restored 26 passed. Real: mixed clip -> `large-v3-turbo`, language `hi`, note "Detected Hindi in part of this recording — Parakeet v3 doesn't cover Hindi, so this used Whisper Large v3 Turbo. If your recordings switch language, make Whisper Large v3 Turbo your default in Settings."; leading-silence clip -> `parakeet-v3`, `en`, no note; English -> `parakeet-v3`; Hindi -> `large-v3-turbo` with the note ending "To skip the check, set your language to Hindi in Settings." Checked the language passed to Turbo on the mixed clip: `language=hi` kept the English part Latin (534 Latin, 0 Devanagari letters) and wrote the Hindi part in Devanagari (178); `language=None, multilingual=True` wrote the Hindi part in Latin (292 Latin, 0 Devanagari), so the detected language stays. Wording grep (`first 30|30 seconds|never writes|gibberish|switches to Turbo|listens to`) over tracked docs/src/ui outside reviews and Sarvam lines: only the historical journal and the module docstring's "confident gibberish" (describing Parakeet, not a promise) remain. Existing test changed: `test_whisper_auto_detected_english_gets_the_prompt` now expects `language is None` (behaviour restored to pre-Parakeet, as the plan says); the Hindi note string in `test_auto_hindi_runs_turbo_not_parakeet` gains the F5 tail.

**C3 (owner paths in the packet)** | Lead-fixed before this round. | Ran: `git diff 63039aa..HEAD` grep for `/tmp/claude`, `/home/rish`, the session id, outside the minified bundle. | Saw: none. The bundle only contains the existing public `github.com/rishmadaan/anyscribe` links.

**C4 (CoreML on Apple silicon)** | Changed: `onnx_asr.load_model(..., providers=["CPUExecutionProvider"])` and `load_vad("silero", providers=[...])` with the plan's `shortcut:` comment (b1dbe53). | Ran: new `test_parakeet_and_vad_load_on_the_cpu_provider`; mutant with `providers=` removed from both loads. | Saw: mutant `AssertionError: assert {'name': 'nem...tion': 'int8'} == {'name': 'nem...ionProvider']}` ("Right contains 1 more item: {'providers': ['CPUExecutionProvider']}"); restored 18 passed. Real Parakeet runs on Linux after the change: 35 s English in 6.7 s wall including load. Mac timing not re-measured here (lead does it).

**C5 (partial downloads counted as ready)** | Changed: `repo_ready`/`model_ready`/`helpers_ready`: ready = a snapshot holds every required file (`WHISPER_REQUIRED`, `PARAKEET_REQUIRED`, `VAD_REQUIRED`) and no live `.incomplete` blob; `cached` now means ready and `partial` is new; `pull_model` always calls `snapshot_download`; `model rm`/`reinstall` act on any bytes; the Web pull route queues a partial model and a ready Parakeet missing Tiny/VAD; making a Parakeet model the default via `PUT /api/config` queues its pull when helpers are missing; `config set local_model` names what to pull; `local setup`'s shortcut checks Tiny AND the VAD; the Settings card shows "Incomplete: resume download" (75b62a4, 4e17f75). | Ran: `tests/test_local_ready.py` (10 tests on a real on-disk HF cache layout) and six mutants; a real interrupted download: `timeout -s KILL 3 anyscribe model pull large-v3` into a fresh HF_HOME, then `model list`, then `model pull` again; the browser Settings walk with a real partial Small (pull killed after 1.5 s). | Saw: mutant "ready = any bytes": 3 failures incl. `assert 'large-v3-turbo' == 'small'` (fallback picked the half-downloaded Turbo); mutant ".incomplete ignored": `test_incomplete_blob_is_partial...` and the stale-blob test fail; mutant "pull skips a ready model": `assert ([] == ['Systran/fas...hisper-small']`; mutant "helpers ignore the VAD": `assert not True`; mutant "every .incomplete blocks readiness": the stale-blob test fails; mutant "PUT config doesn't queue helpers": `assert [] == ['parakeet-v3']`. Real: after the kill, `large-v3` = `cached False, partial True`, table "incomplete … anyscribe model pull large-v3"; the resumed pull finished it. That run found a real bug in my first version: huggingface_hub 2.x names temp blobs `<hash>.<tag>.incomplete` and a killed run's leftover stayed after the resume completed, so the model stayed "partial" for ever; fixed (a leftover whose `<hash>` blob exists is ignored) and covered by `test_a_stale_incomplete_left_by_a_killed_download_is_ignored`; afterwards the same cache read `large-v3 True False` and a second pull said `already_present`. Browser: `API small: {'cached': False, 'partial': True}`, card button "Incomplete: resume download"; clicking it gave `{'cached': True, 'partial': False}` (`fx-settings-1-partial-1440.png`). Existing tests changed: `test_local_cli.py` rm/reinstall tests patch `bytes_on_disk` instead of `is_cached` (a partial download can now be removed); `model list --json` reads `partial` with `.get` for the test's fake list.

**C6 / F3 (the second download)** | Changed: every suggestion ends with its sizes ("Downloads 670 MB + 1.6 GB, plus the 75 MB language check."); wizard and modal buttons read "Download Parakeet v3 + Whisper Large v3 Turbo (2.3 GB)"; the extra model is fixed when the button is clicked and queued after setup, queue-request failures are kept; All set and the modal's finished panel list it with live progress, "ready", or "download failed: …", and say switching for Hindi works once it finishes; CLI onboarding names both models with the size and draws a progress bar (dac811c, 4e17f75). | Ran: browser wizard walk on a fresh HOME and empty HF_HOME; the setup-modal walk on another fresh one; `tests/test_onboard_local_step.py`. | Saw: wizard: `setup button: Download Parakeet v3 + Whisper Large v3 Turbo (2.3 GB)`, after setup `queue = ['large-v3-turbo']`, All set immediately "Whisper Large v3 Turbo · downloading", later "ready" (`fx-wizard-3-allset-downloading-1440.png`, `fx-wizard-4-…`); modal: "Download Parakeet v3 + Whisper Large v3 Turbo (2.3 GB) & set up", then "Parakeet v3 is ready and is your default. | Whisper Large v3 Turbo | downloading (1.6 GB) | Switching to it for Hindi…", later ready, API ready `['parakeet-v3', 'large-v3-turbo', 'tiny']` (`fx-modal-finished-1440.png`); CLI test: "Suggested: Parakeet v3 + Whisper Large v3 Turbo", "Downloading Whisper Large v3 Turbo (1600 MB)", "Default model: Parakeet v3. Also ready: Whisper Large v3 Turbo." A first walk once reached the workspace step without queuing Turbo; I could not reproduce it in two fresh runs, but removed the fragile `rec.primary === default_model` check it depended on (the list is now fixed at the click).

**C7 (low disk)** | Changed: `recommend()` tries each answer's ordered picks and describes the one that fits; memory or disk are cited only when they changed it; mix goes parakeet+turbo -> turbo -> small -> base, never Parakeet alone; nothing fits -> `primary: null` and "Not enough free disk space: only 10 MB is free, and even the smallest suitable model (Whisper Base) needs about 154 MB. Free up space, then ask again."; CLI and Web show it and select nothing (dac811c). | Ran: `tests/test_local_recommend.py` and three mutants. | Saw: mutant "reasons from the first choice": `test_low_disk_steps_down_and_reasons_describe_the_final_pick` and the mix test fail; mutant "mix may drop to Parakeet alone": the mix low-disk test fails; mutant "nothing fits -> suggest base anyway": `test_nothing_fits…` fails; restored 24 passed. The reviewer's cases now: mix at 1,500 MB -> Small ("Only 1.5 GB … not enough for Parakeet v3 + Whisper Large v3 Turbo, so this suggests Whisper Small."), no "two models" text; English at 10 MB -> the no-space result. Existing tests rewritten for the new sentences: the English/Hindi/mix/low-disk/sentence-count tests in `test_local_recommend.py` (count is now 2-5 because the size line was added).

**C8 / F6 (claims)** | Changed: `BENCHMARK_CAPTION` ("Speed and accuracy measured on English audio on a 6-core desktop processor without a graphics card. Your computer may be faster or slower.") under the cards on every surface that shows them (Settings, setup modal, wizard, CLI onboarding list, `model list` table caption, via `/api/local/status` and `/api/local/registry`); the comparison reads "about 4 times faster on our test desktop"; the first-run line says "on our 6-core test desktop; your computer may be faster or slower." | Ran: browser walks; CLI onboarding test. | Saw: `caption: Speed and accuracy measured on English audio …` in the wizard, modal and Settings; CLI output contains the caption. Wording deviation, lead to rule: the plan's "about 4 times faster on that desktop" became "on our test desktop", because the suggestion sits above the cards and "that desktop" would have no referent there (F5's own complaint).

**C9 (notes on cached runs and in batch)** | Changed: the cached path restores `notes` from frontmatter; the human batch table prints each file's notes under its title (escaped) (a1affb6). | Ran: `test_cached_rerun_keeps_the_switch_note`, `test_human_batch_prints_each_files_note`, each against its mutant. | Saw: mutant (no notes restore): `assert ([] == ['Detected Hi...in Settings.']`; mutant (title only): the batch output had `│ 1 │ OK │ t │` and no note; restored both pass.

**C10 (restart after replacing a loaded engine)** | Changed: `install_faster_whisper` compares `av`/`faster-whisper`/`onnx-asr` versions before and after; if one already imported in this process changed, `restart_needed` goes on the result, `run_setup` and `/api/local/status`; the CLI (`local setup`, `onboard`) prints "Restart anyscribe to finish setting up local transcription."; the Web UI shows a banner (Settings, setup modal, wizard) saying how (2978547, 4e17f75). No reloads. | Ran: 4 unit tests plus two mutants; then for real: a throwaway uv venv with anyscribe (this branch), faster-whisper 1.2.1 and PyAV 19.0.2, server on a throwaway HOME, `POST /api/local/setup parakeet-v3`, then a local transcription in that same server, then a restart and the same job. | Saw: mutant "any changed package flags restart": 2 failures (`assert True is False`); mutant "flag never set": `assert False is True`. Real: before `runtime_ready False, restart_needed False`; the setup ran `uv pip install … faster-whisper>=1.0 av<19 onnx-asr>=0.12.0` and on disk became `av 18.1.0, onnx-asr 0.12.0`; status `restart_needed True`; banner shown (`fx-settings-restart-banner-1440.png`); the job in the un-restarted server **failed: "open() got an unexpected keyword argument 'metadata_errors'"** (the reviewer's mechanism, now visible to the person); after a restart `restart_needed False` and the same job completed with `parakeet-v3`.

**C11 (pending default overwritten)** | Changed: Settings keeps the pending default in a ref the poll reads after its await; any explicit choice goes through `chooseLocalModel`: a ready model becomes the default and clears the pending one; any other replaces it and starts its download; a failed download clears it (errors now merged into `/api/local/status`; a re-queue clears the old error) (4e17f75). | Ran: browser Settings walk: pick the not-downloaded Whisper Large v3 (2.9 GB), then the ready Turbo card while it downloads, wait until large-v3 is ready plus 5 s; same walk on a build with `setPendingDefault(null)` removed from the ready branch, then restored. | Saw: fixed: "Downloading; becomes your default when done" on the large-v3 row, config right after picking Turbo `large-v3-turbo`, after large-v3 landed (112 s) still `large-v3-turbo`. Mutant: after large-v3 landed (118 s) config `large-v3`, the superseded choice. Restored build re-run: `large-v3-turbo` again.

**F2 (pre-select)** | Changed: answering applies the suggestion at once (wizard and modal select the primary and remember the extra model; Settings makes a ready pick the default, or starts the download as a pending default); "Use this"/"Selected" button removed. | Ran: browser walks. | Saw: wizard `card checked right after answering (no extra click): parakeet-v3` for "A mix" and `large-v3-turbo` for Hindi; `'Use this' buttons left: 0`; Settings: answering English set `local_model = parakeet-v3` immediately. The Hindi walk exposed a race that F2 made likely: the step's first status response arriving after an early answer reset the pick to Parakeet, so the saved default was `parakeet-v3` although the Turbo card showed checked (request log: `POST /api/local/setup {"model":"parakeet-v3"}`). Fixed with a functional "preset only if nothing picked" update; two re-runs saved `local_model: large-v3-turbo`.

**F4 (mid-recording switches)** | Same change as C2 plus wording: "checks the language at the start, middle and end of each recording" in CHANGELOG, user docs, skill reference, picker explainer and the mix suggestion; the mix suggestion keeps Parakeet v3 + Turbo and adds "If one recording switches language mid-sentence (Hinglish), make Whisper Large v3 Turbo your default instead." | Ran/Saw: see C2; the mix reason sentence appears once on the wizard screen (the walk asserts every API reason appears exactly once).

**F5 (reasons)** | Changed: per the plan: "Something else" has its own sentence (95+ languages, no Hindi); English: "Parakeet v3 is as accurate as Whisper Large v3 Turbo on English, and about 4 times faster on our test desktop."; memory cited only when it changed the pick; Hindi answer carries `set_language: "hi"` with "Set your language to Hindi: Turbo is about 3 times more accurate on Hindi when it is told the language.", a "Set my language to Hindi" button (wizard saves it at Finish; Settings and modal at once) and a yes/no in CLI onboarding; detected switch notes end "To skip the check, set your language to <Language> in Settings." | Ran: recommend tests, CLI onboarding test, browser Hindi walks. | Saw: `test_something_else_has_its_own_reason_without_hindi` passes; Settings: after the button `language = hi`; wizard at 390 px: All set shows "Language | Hindi", config after Finish `language: 'hi'`; CLI test: confirm -> `settings.language == "hi"`, decline -> `auto`.

**F6** | = C8.

**F7 (first-run line)** | Settled on a fresh HOME: `/api/local/status` took 0.45 s first call, 0.25 s after; the line rendered 0.18 s after the provider step opened. So the reviewers' screenshots were most likely taken early, not a failing call. Changed anyway: the line reads `GET /api/local/registry` (specs only, no disk scan or engine import; a test makes `list_cached_models`/`check_status` raise inside it). | Saw: "Downloads Parakeet v3 (670 MB) once. About 10 min per hour of audio on our 6-core test desktop; your computer may be faster or slower." (`fx-wizard-1-choice-1440.png`).

**F8 (getting-started)** | Changed: "What you need" leads with "On this computer (recommended)" (Parakeet v3, Turbo for Hindi, no key, one download) then the cloud option; README's line likewise; docs also explain picking a not-downloaded model, "incomplete" models and the restart message (5f33d1b). | Ran: `scripts/build-docs.py`, `scripts/check-docs.py`. | Saw: exit 0; landing pages regenerated.

**F9 (nits)** | Changed: step labels count the chosen path ("Step 1", then "Step 2 of 3", "Step 3 of 3" on the local path); display names in the All set summary ("Transcribe: On this computer", "Model: Parakeet v3 · ready"), the plan line, the result card ("local · Parakeet v3") and the CLI final lines; one size per card (download size hidden once downloaded; status shows "downloaded · 639 MB"); a not-downloaded card's click downloads it and says "Downloading; becomes your default when done"; Reinstall, Delete and Manage/Hide models have visible text. | Ran: browser walks. | Saw: the labels above; `parakeet card shows 'Download 670 MB': False | status: ['downloaded · 639 MB']`; `visible labels: Reinstall / Delete`; result card `local · Whisper Large v3 Turbo` with the switch note (`fx-result-switch-note-1440.png`); 390 px: no horizontal scroll on the wizard and Settings. Not changed: Settings' "What runs by default" rows still show raw ids ("local · parakeet-v3"); the plan's list didn't name them.

**F10** | Lead-fixed; nothing committed under screens; see C3.

---

## Round 2 fixes

Fixer: Claude Opus 5.5 (Agent tool), from 6ba31ad. Commits e08ffcd..e32d799 and this proof fix on `feat/local-first-parakeet`.
Browser walks: scratch Playwright scripts (not committed) against a real `anyscribe ui` on throwaway HOME/HF_HOME folders under `<lead scratch folder>/fixer/r3/`. The server ran under a scratch harness that wraps `huggingface_hub.snapshot_download` per repo from a control file: sleep N seconds, fail once or always, or hard-link the repo from the shared cache instead of downloading (so a 1.6 GB Turbo "download" takes seconds). Every effect was read back from `/api/...` or `config.yaml`. Screenshots: `~/.review-runs/2026-11-19-local-first-parakeet/screens/r3-*.png` (none committed). Every server was stopped by port after reading its pid's command line (`.../fixer/r3/serve.py 8495`).
Final checks: `pytest -q` 893 passed, 5 skipped; `ruff check src tests` clean; `ui`: `tsc -b`, `npm run lint`, `npm run build` clean, rebuilt `web/static` committed (`git status` empty after a fresh rebuild); `scripts/check-docs.py` exit 0; `landing/docs` regenerated (5688bad).

### Spec section 5 (the shared mechanism), built first

Deleted, not left alongside: Settings' `pendingDefault` state, ref and the poll that wrote `local_model`; `handleRecommendation`; the wizard's and modal's `alsoRef` and browser `pullLocalModel` loops; the wizard's second Next; `web/routes/config.py::_ensure_parakeet_helpers`; `config_set._local_model_hint`; the hand-written "weights and helpers" checks in `web/routes/models.py` and `cli/local_cmd.py`.
Added: `local_models.runnable()` + `runnable` on every model entry; the guard in `config_set.set_value('local_model')`; `POST /api/local/choose` with the server-side pending default settled by the queue worker (`models._settle_pending`); `POST /api/local/setup {model, also}` queuing extras after a successful setup; `run_setup` switches through `set_value`; headless onboarding leaves the switch to `run_setup`.
Tests rewritten because behaviour changed on purpose: `test_local_ready.py::test_making_parakeet_the_default_queues_its_helpers` is now `..._is_refused_until_it_can_run` (422, default still exactly `large-v3-turbo`, queue empty); `test_web_pull_queues_a_partial_model_and_a_parakeet_missing_helpers` now patches `runnable`; `test_config_set.py::test_enum_values_accepted[local_model]` patches `runnable`; `test_local_setup.py::test_run_setup_short_circuits...` asserts the saved model is `base` through `set_value`; `test_local_cli.py::test_setup_already_set_up_is_noop` adds `runnable`; `any_model_cached` is now `any_model_runnable` (two tests renamed). New: `tests/test_local_choose.py` (15), two runnable tests on a real on-disk cache layout in `test_local_ready.py`.
Mutants (each applied, the named tests run, then restored; log at `<lead scratch folder>/fixer/r3mut/server-mutants.log`), asserting identity:
- `runnable` ignores helpers: `test_runnable_parakeet_needs_tiny_and_the_vad_on_disk` fails `(True, True, True) == (True, False, False)`.
- no `set_value` guard: 3 fail, e.g. `assert 'parakeet-v3' == 'large-v3-turbo'` (the default) and `assert (200 == 422)` on PUT /api/config.
- the worker switches on any download end (bypassing the runnable check): `test_weights_done_but_helper_failed_keeps_the_old_default` fails `'parakeet-v3' == 'large-v3-turbo'`.
- choose switches at once regardless: 3+ fail (`assert [] == ['large-v3', 'small']`: nothing queued).
- the worker ignores which model is pending: `test_a_later_choice_replaces_the_earlier_one` fails `'large-v3' == 'small'`.
- setup ignores extras: `assert [] == ['medium']`.
- headless writes the default before setup: `assert ['parakeet-v3'] == ['large-v3-turbo']` (the default seen while setup ran).

**R2C3 (Parakeet default before its helpers)** | Changed: spec items 1-3 above (18fb4f6, dfef7d5). | Ran: `test_local_choose.py` + `test_local_ready.py`; browser walk `w3_gap.py`: Turbo the default, Parakeet weights + VAD on disk, Tiny absent; the Tiny download sleeps 10 s and fails once; click the Parakeet card in Settings, poll every 2 s, then click it again. | Saw: before: Parakeet `cached True, runnable False`, card "Incomplete: resume download". Gap t+2..8 s: `pending {'model': 'parakeet-v3', 'state': 'downloading'}`, `config: large-v3-turbo` each time. After the failure: `pending state 'failed', error 'simulated: connection reset'`, config `large-v3-turbo`; the page: "Couldn't switch to Parakeet v3: simulated: connection reset. Your default is still Whisper Large v3 Turbo."; checked card `large-v3-turbo` (`r3-w3-helper-failed-1440.png`). Second pick: Tiny lands, `runnable True`, config `parakeet-v3`, pending None, alert gone, checked card `parakeet-v3`. Real CLI: `anyscribe config set local_model large-v3` (not downloaded) exit 1, "Whisper Large v3 isn't ready to use yet, so the default model is unchanged. Download it first: `anyscribe model pull large-v3` …", config unchanged; `config set local_model large-v3-turbo` (ready) exit 0.

**R2C4 (wizard skips the second download)** | Changed: the second Next is gone; every forward path is the setup button, which sends `also`; the server queues it after setup (18fb4f6, dfef7d5). | Ran: `w1_wizard_mix.py` with Parakeet + Tiny + VAD installed before the wizard, "A mix", then the forward button; same with Turbo failing; `w1c_turbo_only.py` (only Turbo installed, keep Parakeet); `test_setup_queues_the_extras_itself`. | Saw: forward buttons offered: exactly one, `Download Parakeet v3 + Whisper Large v3 Turbo (1.6 GB)` (only Turbo downloads); request `POST /api/local/setup {"model":"parakeet-v3","also":["large-v3-turbo"]}`; right after setup queue `['large-v3-turbo']`, `setup_also ['large-v3-turbo']`, default `parakeet-v3`; All set "Whisper Large v3 Turbo · downloading" then "ready", API Turbo `runnable True` (`r3-w1-*.png`). Turbo-only case: one button `Download Parakeet v3 (745 MB)`; All set "Parakeet v3 · ready" only after setup, API `runnable True`. Test: queue exactly `['medium']` when Turbo is already runnable; failed setup queues nothing.

**R2C2 (older recommendation overwrites a newer choice)** | Changed: the picker counts a reply only if no later answer or card click came after its question (`seqRef`) (dfef7d5). | Ran: `w2_reorder.py` in the wizard and in Settings: Playwright holds the `answer=indian` reply, clicks English, waits for its reply, then releases the Hindi one; then the same walks on a build with the guard line removed, then restored and rebuilt (bundle hash back to the committed one, no "MUTANT" in it). | Saw: reply order `['english', 'indian']` both times. Fixed: wizard pick `parakeet-v3`, checked card `parakeet-v3`, button `Download Parakeet v3 (670 MB)`; Settings "Suggested: Parakeet v3", suggested cards `['parakeet-v3']`, button `Use Parakeet v3 (downloads 670 MB)`, POST/PUT sent `[]`, config `large-v3-turbo` before and after. Mutant: wizard pick and checked card `large-v3-turbo`; Settings suggestion `large-v3-turbo`, `Use Whisper Large v3 Turbo (already downloaded)` (`r3-w2*-*.png`).

**R2C5 (no-fit leaves a download selected)** | Changed: every current reply reaches the parent, including primary null, which clears the selection (dfef7d5). | Ran: `w4_nofit.py`: `/api/local/recommend` fulfilled with `primary: null` by interception, in the wizard and the setup modal, after Parakeet was preselected. | Saw: wizard: checked before `parakeet-v3`, "Not enough disk space", 0 cards checked, button disabled; modal: same, `Download & set up` disabled; POSTs sent `[]` (`r3-w4-*.png`). In Settings the Use button renders only for a non-null primary.

**R2F1 (Settings answer switches or downloads)** | Changed: in Settings an answer only highlights ("Suggested" label, dashed border) and shows one button; only it, or a card click, calls choose (dfef7d5). | Ran: `w5_settings.py`: Turbo user answers English, Hindi, Something else, A mix; then clicks Use. | Saw: after four answers writes `[]`, config `large-v3-turbo`, queue `[]`; buttons per answer: `Use Parakeet v3 (downloads 670 MB)`, `Use Whisper Large v3 Turbo (already downloaded)` (twice), `Use Parakeet v3 + Whisper Large v3 Turbo (downloads 670 MB)`. After Use: writes exactly `[('POST', '/api/local/choose', '{"model":"parakeet-v3","also":["large-v3-turbo"]}')]`, queue `['parakeet-v3']` (Turbo already runnable), config still `large-v3-turbo` until Parakeet landed (`r3-w5-settings-suggested-1440.png`).

**R2C1 (weak uncovered guess forced a language)** | Changed: spec item 7's disjoint rules in `LocalProvider.plan` (e08ffcd). | Ran: 5 new tests in `test_local_guard.py`; mutant = the previous `local.py` (old order); real runs on a throwaway home. | Saw: `[("hi", 0.2)]` with Turbo: Turbo, `language None`, unsure note; without Whisper: Parakeet, `language 'unknown'`, unsure note (used to raise); `[("en",0.9),("ja",0.3)]`: Turbo unsure, language None; doubt without Whisper takes `en` from the covered window; a sure `hi` 0.7 beside a weak `ja` still switches to Hindi. Mutant: 4 fail (`assert 'hi' is None`, `assert 'ja' is None`, …). Neighbours, real engines: `english-1.wav` -> `parakeet-v3`, `en`, notes `[]`; `hindi-1.wav` -> `large-v3-turbo`, `hi`, "Detected Hindi — Parakeet v3 doesn't cover Hindi, so this used Whisper Large v3 Turbo. …".

**R2C7 (onboard --yes omits restart)** | Changed: human output prints `RESTART_MESSAGE` when `local_setup.restart_needed` (69deda4). | Ran: new `test_yes_human_output_says_restart_when_setup_replaced_a_loaded_engine`; mutant with the condition forced False. | Saw: pass with the message for `restart_needed: True`, absent for False; mutant fails (stdout ends at "Local transcription ready.").

**R2F2 (Hindi advice to every Indian-language user)** | Changed: reason, Web button "My audio is Hindi: set language to Hindi", CLI prompt, skill reference, each with the fix plan's words (f8af827). Siblings: `grep "Set your language to Hindi\|Set my language"` over src/ui/docs/tests finds none left outside review records. | Ran: `test_hindi_advice_is_conditional_and_says_it_applies_to_every_recording`, `test_local_recommend.py`, `test_onboard_local_step.py`. | Saw: 29 passed; the reason reads "If your audio is Hindi, set your language to Hindi: Turbo is about 3 times more accurate on Hindi when it is told the language. Every recording is then treated as Hindi."

**Mix reason** | Changed: adds "Parakeet v3 is the main one because it is about 4 times faster on English." (f8af827). | Saw: `test_mix_says_why_parakeet_is_the_main_model` passes; the walk shows it in Settings.

**R2F3 (no-key messages)** | Changed: `providers.base.local_hint()` adds "Or transcribe free on this computer, no key needed: `anyscribe local setup --model parakeet-v3` (or Settings, then Local transcription)." to all six "<KEY> not set" errors and the keyless-tier WARNING, only when no cloud key is set; dataclass defaults untouched (aa2fad7). | Ran: `tests/test_local_hint.py` (8); two mutants. | Saw: pass; `local_hint` returning "" -> 7 fail; ignoring set keys -> 2 fail (`test_no_local_hint_once_any_cloud_key_is_set`, the tier test's second half). Real: `OpenAIProvider()._get_api_key()` on an empty HOME prints the key line then the hint line.

**R2F4 ("typical")** | Changed: CHANGELOG, getting-started (2), providers, troubleshooting -> "our (6-core) test desktop/CPU"; siblings found by grep in the skill (`SKILL.md`, `references/troubleshooting.md`: "on a 6-core CPU") too (467fc2f). | Ran: `grep -rni "a typical" CHANGELOG.md docs/user README.md src/anyscribe/skill/references` | Saw: no hits; `landing/docs` regenerated.

**R2F5 (All set text vs status)** | Changed: `ExtraDownloads` shows the "works once it finishes downloading" note only while a download is pending; on failure "Hindi and other languages won't work until you download Whisper Large v3 Turbo in Settings." (dfef7d5). | Ran: `w1_wizard_mix.py` with Turbo succeeding and with it failing. | Saw: downloading: note shown; ready: note gone, no failure line; failed: "download failed: simulated: connection reset", note gone, the failure sentence shown, API Turbo `last_error` the same (`r3-w1f-allset-failed-1440.png`).

**R2F7 (restart banner assumes a terminal)** | Changed: banner adds "Using the app icon? Quit anyscribe from its menu-bar or tray icon, then open it again." (dfef7d5). | Ran: `tsc`/build. | Not walked: triggering a real engine replacement needs a PyAV 19 install; the string is in the built bundle.

**R2F8 (amber "needs API key" for a local user)** | Changed: when the active provider is local, cloud tier rows say "add a key to use" in muted text (dfef7d5). | Ran: `w8_rows.py` on a local user and on a key-free cloud user. | Saw: local user: accuracy/balanced/cost "add a key to use", muted; cloud user (neighbour): all "needs API key", amber (`r3-w8-settings-rows-local-user-1440.png`).

**F9 leftover (raw ids)** | Changed: display names in the Model line and the tier rows (dfef7d5). | Saw: "Parakeet v3 · change it on the local card below"; rows "free | local · Parakeet v3"; 390 px Settings with a suggestion: scrollWidth 390 = innerWidth (`r3-w9-settings-suggested-390.png`).

**R2C6 / R2F6** | Lead-fixed; untouched. Note: `git grep tmp/claude-1000` still finds R2F6's own quoted grep command in `findings.md:536` and `report-opus-r2.md:90` (a prefix with the OS uid, no session id). Left for the lead.

### Diagnosis extra cases

- **Pending default lost on reload** | `w5_settings.py`: Use -> reload while Parakeet is "downloading" (15 s) | after reload the card reads "Downloading; becomes your default when done", `pending_default` still `downloading`, config `large-v3-turbo`; 12 s later config `parakeet-v3`, pending None, the reloaded page checks the Parakeet card and the Model line says "Parakeet v3" (`r3-w5-settings-pending-after-reload-1440.png`). In memory only: a server restart forgets it and the default stays (docstring in `models._download_state`).
- **Extras lost on closing the wizard** | `w1b_close.py`: click the mix setup button, close the browser while setup runs | with no page open: default `parakeet-v3`, queue `['large-v3-turbo']`, `setup_also ['large-v3-turbo']`.
- **PUT with helpers ready but weights missing** | `set_value` refuses any change to a non-runnable model, whatever is missing | `test_making_parakeet_the_default_is_refused_until_it_can_run`: 422, default exactly `large-v3-turbo`, queue `[]`.
- **Headless onboarding wrote the default before setup** | `run_headless_onboard` no longer sets `local_model` for provider local; `run_setup` switches after the download | `test_headless_local_onboarding_switches_only_after_setup`: the default seen during setup `large-v3-turbo`, unchanged after a failed setup; mutant fails. A non-local provider with an unready `--local-model` is refused with `anyscribe local setup --model <id>` (`test_headless_onboarding_refuses_a_local_model_that_cannot_run`).

### Not proven / left
- Browser walks are scratch scripts; there is still no committed UI test (spec 5 item 8: no new dependency).
- Interactive CLI onboarding (`cli/onboard.py`) still sets `settings.local_model` after `run_setup` succeeded (sequential; out of scope per spec 5 item 8).
- Whether `huggingface_hub` is safe when setup and the queue fetch the same repo at once: not tested (the queue now starts only after setup finishes, so the only overlap is a manual Download clicked during setup).

## Round 3 fixes

Fixer, round 4 (Claude-only), from `2778624`. Commits: 24fa08d (R3C1), 4737ef3 (R3C2), c1dcd62 + 47f6973 (R3C3), aaf8704 + 8093234 (R3F1), eee89ce (R3F2), 5fcfc21 (R3F3), e13372b (web/static rebuilt). "Old code" below means the test run against 5551230's `src` (`git stash push src`, the new tests left in place), or for the browser a server run from `git archive 5551230 src` on `PYTHONPATH`, serving 5551230's own `web/static`.

Final checks on the last code commit: `pytest -q` 911 passed, 5 skipped (all environmental: iconutil, WScript.Shell, PIL, opt-in network test, Windows probe); `ruff check src tests` clean; `ui`: `tsc -b`, `npm run lint`, `npm run build` clean, static committed; `scripts/check-docs.py` exit 0 (no docs changed, nothing regenerated). Browser walks: scratch Playwright scripts `r4_walk.py` / `r4_modal.py` with the round-3 harness (`serve.py`, throwaway HOME/HF_HOME under `<lead scratch folder>/fixer/r3/r4-*`), screenshots `~/.review-runs/2026-11-19-local-first-parakeet/screens/r4-*.png` (none committed). Every server was stopped by port after reading its pid's command line (8591-8596).

**R3C1 (lost config updates)** | Changed: `config/settings.py` gains `CONFIG_LOCK` (a `threading.RLock`; `save_config` writes under it) with the shortcut comment the plan names. Every in-process read-modify-write holds it from load to save: `config_set.set_value` (so `run_setup`'s switch, the worker's `_settle_pending`, `choose`, MCP and CLI `config set` all go through it); `PUT /api/config` (all fields and the 422 rollback in one critical section); `run_headless_onboard` (CLI `--yes` and web `/api/onboarding/save`); `run_teardown`; `local setup`'s already-set-up save. The PUT's tailnet part stays outside the lock (the tailnet lock is always taken first, since `save_and_apply` calls `set_value`; holding both the other way round could deadlock two requests), so its undo, `_undo_fields`, re-takes the lock: if nothing else wrote since the fields it restores the exact old file (or removes it), otherwise it puts back only the keys this request changed plus `tailnet`, keeping the other writer's change. Writers found by `grep save_config`: the ones above, `migrate.maybe_migrate_sargam_model` (runs inside `load_config`, covered by `save_config`'s lock, reentrant), and interactive `cli/onboard.py` (loads at the start, saves at the end after prompts; a CLI process with no other writer thread, its own `run_setup` call already synced at line 349; `save_config` takes the lock). Deviation: the plan's `update_config(mutator)` helper was written and then removed: every caller needed a conditional save or a raise path, so it ended up unused; the callers use `with CONFIG_LOCK:` directly. | Ran: new `tests/test_config_concurrency.py`: (1) the worker's `set_value("local_model","small")` pauses inside the lock (in the runnable guard) while a `PUT {"provider":"local"}` arrives from another thread; (2) a PUT whose tailnet part fails after the worker saved Small; (3) a PUT whose first field saved and whose second is invalid, with the worker trying to save during the request; (4) the no-config tailnet failure leaves no file. Mutants: no lock in `set_value`; no lock in the PUT; the undo always restoring the snapshot; the exact-restore branch removed. | Saw: all pass. Old code: (1) `('openai', 'balanced', 'small') == ('local', 'custom', 'small')` fails (the provider choice erased), (2) `local_model 'large-v3-turbo' != 'small'`, (3) `('auto', 'clean', 'large-v3-turbo') == ('auto', 'clean', 'small')`. Mutant no `set_value` lock: (1) and (3) fail; no PUT lock: (3) fails with `large-v3-turbo`; undo always snapshot: (2) fails; no exact-restore branch: (4) fails (`not True`). Out of scope, as planned: a CLI write while the server runs (separate processes).

**R3C2 (choose response)** | Changed: `choose()` copies the pending record it just set while still holding the queue lock (`accepted`) and replies from that copy. | Ran: `test_choose_answers_after_the_worker_already_finished` (the worker runs to completion inside `enqueue_pull`) and `test_choose_answers_when_a_second_choose_finished_first` (a choose of the ready Tiny completes while the first is queuing Parakeet); mutant = reply read from shared pending again. | Saw: both 200 with body `{"status": "pending", "pending": {"model": "parakeet-v3", "also": [], "state": "downloading", "error": None}, "queued": ["parakeet-v3"]}`; saved default `parakeet-v3` in the first, `tiny` in the second (and still `tiny` after Parakeet's download lands). Old code and mutant: both `TypeError: 'NoneType' object is not iterable` (the reviewer's exact failure).

**R3C3 (one owner of activation)** | Changed: the download-queue state has `generation`. Every accepted `choose` (ready or pending) and every web setup start takes the next number. `setup_activation(app)` (called by `POST /api/local/setup`) returns `activate(model)`, which under the queue lock switches the default only if no number was taken since, else returns None; `run_setup(..., activate=None)` then returns status `superseded` with the default left alone (the CLI calls `run_setup` without it: unchanged). `/api/local/status` gains `setup_outcome` (`set_up` / `superseded` / `failed`); a superseded setup logs "a newer choice was made meanwhile; default left as it is" and drops its extras (they belonged to the older choice). For the worker's switch, starting a web setup drops the pending choice at once, so an older choice's download can never switch after a newer setup; I did not also store the number in the pending record: with pending dropped there, a number check in `_settle_pending` cannot be told apart by any test (an equivalent mutant), and the existing pending-body tests stay exact. | Ran: `test_a_choose_made_during_setup_wins_over_the_setup` (setup of Parakeet held in its download; choose Small; release) and `test_a_choice_pending_before_setup_never_switches_after_it` (choose Parakeet, pending; run setup of Base; then the Parakeet download lands), and `test_a_pending_choose_made_during_setup_also_wins` (setup of Parakeet held; choose the not-downloaded Base; Base's download lands and switches first; then the setup finishes); four mutants. The third test was added after the first mutant run showed the "pending choose takes no number" mutant surviving: the queue runs beside setup, not after it, so an older setup could switch after a newer pending choice had already landed. Existing test changed: `test_local_choose.py::test_setup_queues_the_extras_itself`'s fake `run_setup` takes the new `activate` argument. | Saw: pass: default exactly `small`, status `setup_outcome "superseded"`, `setup_error None`, `default_model "small"`; second: default `base` after setup and still `base` after the old download, `setup_outcome "set_up"`, `pending_default None`; third: default `base` after Base lands and still `base` after the setup ends, `setup_outcome "superseded"`. Old code (5551230 `src` on `PYTHONPATH`): `'parakeet-v3' == 'small'`, `'parakeet-v3' == 'base'`, `'parakeet-v3' == 'base'`. Mutants: activation ignores the number -> first fails (`parakeet-v3`); ready choose takes no number -> first fails; pending choose takes no number -> third fails (`('parakeet-v3', 'set_up') == ('base', 'superseded')`); setup start keeps the older pending -> second fails (`parakeet-v3`).

**R3F1 (free-option hint)** | Changed: `LOCAL_HINT` is now exactly the plan's text ("Or transcribe free on this computer, no key needed: run `anyscribe onboard` and choose On this computer (in the dashboard: Settings, then Run setup wizard)."). Found while walking: every run meets `preflight_check`'s key test before any provider, so on 5551230 the real CLI printed the hint once (the WARNING only; the reviewer's "twice" came from the provider errors, which never fire in a run) and the web Transcribe error box showed no hint at all. The pre-flight key error now carries it too (8093234). Once per run: `anyscribe transcribe` drops the error's copy when the plan's WARNING already printed it; `batch` rows are cut at 80 characters (the hint is never visible in them), so batch prints the hint once after the table when the plan didn't. Web: the Next run notes `<p>` and the Transcribe error `<p>` have `whitespace-pre-line`. When the next run would not be local (`resolve_run(...).provider != "local"`), `anyscribe local setup` (both success paths, human and `--json` as `use_local_tip`) and the Settings setup window end with "To use it for every transcript: `anyscribe config set quality free` (or pick 'free' under What runs by default)."; `/api/local/status` carries `use_local_tip`, and the window stays open on its result when there is a tip. Sibling grep: `grep -rn "local setup --model parakeet-v3\` (or Settings" src ui/src docs` finds none left (only review records). | Ran: `tests/test_local_hint.py` new tests: following the hint headless (`onboard --yes --provider local --local-model parakeet-v3`) then `resolve_run`; the pre-flight error; `transcribe` once; `batch` once with and without the WARNING (`provider groq`); local setup's tip for openai vs local plus `check_status()["use_local_tip"]`. Mutants: pre-flight without the hint; transcribe not dropping the copy; batch never printing after the table; batch ignoring the notes. Real CLI on a throwaway home (Tiny + VAD only, no keys): transcribe `english-1.wav`; `local setup --model tiny --yes`; `onboard --yes [--force] --provider local --local-model tiny`; transcribe again; and the same on a second fresh home following the hint directly. Browser: `r4_walk.py keyfree` on new and old servers; `r4_modal.py` (provider openai, Settings, Set up local transcription, Parakeet, 4 s download). | Saw: tests pass; old code: the headless test fails on the hint text, the pre-flight test fails, local-setup tests `ImportError: USE_LOCAL_TIP`, batch-without-WARNING fails `0 == 1` (no hint at all). Mutants: pre-flight -> 2 fail; transcribe -> `2 == 1`; batch after-table -> `0 == 1`; batch ignoring notes -> `2 == 1`. Real CLI: run 1 prints the WARNING, the hint once, then the pre-flight error; `local setup` prints "Already set up. Default model is now tiny." + the tip; `onboard` after that says "Already configured … Pass --force" (config.yaml now exists; it names the fix), `--force` -> "Onboarded. Provider: local (quality: custom, model: tiny)"; next transcribe `→ local (config)`, "Transcription saved: …/english-1.md", `Model: tiny`; `local setup` again prints no tip; fresh home: `onboard` straight away -> `→ local (config)`, saved. Browser new: Next run note renders two lines, `white-space: pre-line` (`r4-f1-nextrun-note.png`, `r4-f1-settings-nextrun-1440.png`); Transcribe error box shows the key error, Fix, Or, and the hint on its own lines (`r4-f1-transcribe-error-1440.png`). Old: one run-on line with the old command, `white-space: normal`, and the error box without any hint (`r4-f1-old-*`). Setup window: "Local transcription is set up / Parakeet v3 is ready and is your default. / To use it for every transcript: … / Done", config after `provider openai, quality balanced` (`r4-f1-modal-result-1440.png`).

**R3F2 (Parakeet tip)** | Changed: `parakeet_suggestion(..., web=True)` ends "Try it: click the Parakeet v3 card below."; `check_status(web=True)` only from `/api/local/status` (CLI `local status`, MCP and the CLI dashboard keep the command); `/api/local/status` sets `suggestion` to null while `pending_default` exists (downloading, or its switch failed). | Ran: new `tests/test_local_tip.py` (web text vs `check_status()`; tip null while Parakeet is pending, and after the pending record turns `failed`); mutants: not hidden; web gets the CLI text. Browser `r4_walk.py settings` on new and old (local Turbo user, Parakeet download held 8 s then failing). | Saw: pass; old code: web text `assert False`, and the tip present while pending. Mutants: each fails its test. Browser new: tip "… Try it: click the Parakeet v3 card below."; after clicking the Parakeet card: pending `downloading`, `tip on page = 0`, API `None` (`r4-f23-pending-1440.png`); after the failure: pending `failed`, alert "Couldn't switch to Parakeet v3: simulated: connection reset. Your default is still Whisper Large v3 Turbo.", `tip on page = 0` (`r4-f23-failed-1440.png`). Old: command text, `tip on page = 1` in both states (`r4-f23-old-*`).

**R3F3 (Use for the current default)** | Changed: `HelpMeChoose` gets `current` (Settings' default); when the suggestion's primary is it and every model in it is downloaded, a green "This is already your default" replaces the Use button. | Ran: browser `r4_walk.py settings` (Turbo user: Hindi, then English) on new and old; `r4_walk.py mix` on a Parakeet v3 user without Turbo (A mix, then English); a mutant build that ignores the extras' readiness, walked with `mix`, then the real source restored and rebuilt (same bundle hash, `index-DYC4GSkO.js`). No UI test framework exists (no new dependency), so the browser walk is the test. | Saw: new: Hindi -> "Suggested: Whisper Large v3 Turbo", Use buttons `[]`, already-default line 1 (`r4-f23-suggest-hindi-1440.png`); English -> `['Use Parakeet v3 (downloads 670 MB)']`. Old: Hindi -> `['Use Whisper Large v3 Turbo (already downloaded)']`, no line (`r4-f23-old-suggest-hindi-1440.png`). Mix walk: A mix -> `['Use Parakeet v3 + Whisper Large v3 Turbo (downloads 1.6 GB)']`, English -> already-default line (`r4-f3mix-*`). Mutant: A mix -> Use buttons `[]` and the already-default line although Turbo isn't downloaded (`r4-f3mix-mutant-*`).

### Not proven / left
- `POST /api/onboarding/save` with provider local runs `run_setup` synchronously without the choice number (the web wizard never uses that path; it calls `/api/local/setup`). It holds the config lock but can still overwrite a choose made during its download.
- The setup window misses its own result screen when setup finishes before the window's first status read (seen with an instant fake download; real downloads take long enough). Pre-existing, not changed.
- A superseded web setup shows no special message in the setup window; the default it names is the true (newer) one, and `/api/local/status` says `setup_outcome: "superseded"`.

## Lead-made changes after round 4 (0659c0a, lead-verified)

R4F1 | `core/local_setup.py`: `use_local_tip(web=True)` returns "New transcripts still go to <provider>. To transcribe on this computer instead, pick 'free' under What runs by default." (no terminal command); `check_status(web)` passes it through; `LocalSetupModal.tsx` says "is your default local model" when the tip shows | Ran: `pytest tests/test_local_hint.py -k web_setup_tip` against 90bc0cf's local_setup.py | Saw: `assert web_tip.startswith("New transcripts still go to openai.")` fails on 90bc0cf; passes on 0659c0a; CLI keeps USE_LOCAL_TIP (same test).
R4F2 | `providers/base.py` hint names `anyscribe onboard --force`; `tests/test_local_hint.py` WANTED_HINT updated | Ran: grep for the old wording outside docs/reviews | Saw: none.
R4C2 | `core/resolve.py` appends the hint only when the fallback provider is not local; `TranscribePage.tsx` PlanNotes `whitespace-pre-line` | Ran: `pytest -k fallback_is_already_local` against 90bc0cf's resolve.py | Saw: fails on 90bc0cf (`LOCAL_HINT not in plan.notes[0]`), passes on 0659c0a.
Whole: `pytest -q` 914 passed, 4 skipped; `ruff check src tests` clean; `npx tsc -b && npm run lint && npm run build` clean, web/static rebuilt; `scripts/check-docs.py` exit 0.
Correction (R4C1): the round-3 fixer's note that the web wizard never posts provider local to `/api/onboarding/save` is false; `finish()` does. Left as residue (explicit click, pre-existing synchronous call).
