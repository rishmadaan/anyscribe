Copied from the review run folder; absolute home-folder paths rewritten as ~ paths; the byte-exact original stays in ~/.review-runs/2026-11-19-local-first-parakeet/.

~~~~~
CORRECTNESS RE-CHECK, round 4 (final). Target: feat/local-first-parakeet @ 90bc0cf (HEAD verified), delta 5551230..90bc0cf. I wrote no files and ran no tests, builds or servers. The only things I ran were two in-memory Python probes (HOME pointed at a path that does not exist, load_config/save_config swapped for an in-memory store, no bytecode written).

## 1. Verdict

**GOOD TO GO.**

All six round-3 findings are fixed. I found no blocker and no should-fix. The lock design cannot deadlock: I traced every lock and then stress-ran 3,000 iterations across four racing threads. What remains is four nits, plus one false claim in the fixer's "left" notes that should be corrected in the record. None of them needs to block the merge.

## 2. Round-3 findings: status

| Id | Status | Evidence |
|---|---|---|
| R3C1 config lock | FIXED | The lock (`CONFIG_LOCK`, reentrant) covers the full read-change-save in `set_value` (`core/config_set.py:96-109`), every field plus the rollback of `PUT /api/config` (`web/routes/config.py:117-136`), headless onboarding (`onboard_headless.py:198-236`), teardown (`local_setup.py:466-477`) and `local setup`'s already-set-up save (`local_cmd.py:171-177`). `save_config` takes it too. Lock order is always tailnet lock, then queue lock, then config lock; nothing holds the config lock and then takes either of the other two. Stress probe (tailnet save, choose, setup activation and a PUT-style nested save racing, 3,000 iterations): no thread hung. |
| R3C2 choose snapshot | FIXED | `models.py:139-146`: the reply is built from `accepted`, copied under the queue lock. The shared pending state is never read after the worker can run. |
| R3C3 choice generation | FIXED for the Settings setup window and choose | Every bump of the generation also sets or clears `pending` (`models.py:132-133, 140-141, 156-158`). So "a pending record exists" means "its choose is the newest", and the fixer's argument that the worker's switch needs no number check holds. `activate` checks and writes under one lock, so a choose cannot slip in between the check and the write. The CLI path is unchanged: `(activate or (lambda m: set_value(...)))` is the old call when `activate` is None, and all three CLI or headless callers pass none. Gap: see R4C1. |
| R3F1 hint | FIXED | `providers/base.py:12-15` has the plan's text, and the pre-flight key error now carries it (`preflight.py:64`). "Once per run" is correct in both commands. `transcribe` strips the error's copy only when the plan printed it (and not with `--quiet`). `batch` prints it once after the table and never live, since `_process_url` prints nothing. The Next-run and Transcribe-error paragraphs get `whitespace-pre-line`. The tip after `local setup` is conditioned on the next run's provider (`resolve_run`), not on the stored provider. |
| R3F2 tip | FIXED | `check_status(web=True)` is called only from `/api/local/status`. The CLI, MCP and `cli/main.py` keep the command. The suggestion is set to null whenever a pending choice exists, downloading or failed (`local.py:98-99`). |
| R3F3 already default | FIXED | `current={selected}`, and Settings passes `selected={config.local_model}` (`SettingsPage.tsx:1110`). The green line shows only when every model in the suggestion is runnable (`LocalModelPicker.tsx:370-372, 447-452`). |

**The fixer's claim that the round-3 reviewer's "printed twice" was wrong: correct.** On 5551230:
- The pre-flight key error had no hint (`git show 5551230:src/anyscribe/core/preflight.py`).
- `orchestrator.py:114` runs the pre-flight check before `get_provider` at `:145`, so the six provider errors that carry the hint never fire inside a run.
- The CLI therefore printed the hint once, and the web error box printed none.

**New defects the fixes introduced:** none of blocker or should-fix weight. R4C1 below is a gap in the fixer's note rather than a new defect.

## 3. Findings, most severe first

**R4C1. nit. CONFIRMED (code read).** The fixer's leftover note says "the web wizard never uses [`POST /api/onboarding/save` with provider local]". That is false.
- **Where:** `OnboardingWizard.tsx:137-151`; `onboard_headless.py:283-287`.
- **What happens:** `finish()` always posts `provider: local` and `local_model`, so every web-wizard Finish runs `run_setup` with no generation check.
- **Scenario:** two tabs. The wizard sets up Parakeet. Meanwhile another tab chooses Small, so the setup is correctly marked superseded. The user then clicks Finish in the wizard, and Parakeet becomes the default anyway.
- **Why it is only a nit:** Finish is an explicit click on a screen that shows "Parakeet v3 · ready", so "newest user action wins" still roughly holds. The synchronous `run_setup` on the event loop is pre-existing (identical call on b2bafa7).
- **Fix:** correct the note in `proof.md`. Optionally pass `setup_activation(app)` through `save_onboarding` to `run_setup`.

**R4C2. nit. CONFIRMED (code read).** The plan line on the Transcribe page still shows the hint run together on one line, and in one edge case it shows the hint to someone already transcribing locally.
- **Where:** `TranscribePage.tsx:33-36` (`PlanNotes` `<p>` has no `whitespace-pre-line`); `resolve.py:80-83`.
- **What happens:** the fix plan named two paragraphs, but there are three that render notes.
- **Scenario:** a key-free local user picks "balanced" in Transcribe's options. The run succeeds locally, and the completed screen shows "WARNING … using local instead Or transcribe free on this computer…" as one line.
- **Fix:** add `whitespace-pre-line` to `PlanNotes`. In `resolve.py`, append `local_hint()` only when `provider != "local"`.

**R4C3. nit. PLAUSIBLE (settle with a two-tab walk on a fresh home).** A superseded setup can make the setup window claim a model is ready when it is not.
- **Where:** `LocalSetupModal.tsx:76-84, 144-149`.
- **Scenario:** a fresh install (default `local_model: base`, not downloaded) starts the Parakeet setup in the window. In another tab, the user clicks a card for a not-downloaded model, so the setup is superseded. If a tip is present, the window says "Whisper Base is ready and is your default", but Base is not runnable.
- **Fix:** when `setup_outcome === "superseded"`, say "A newer choice was made; your default is X", and check `runnable` before saying "ready".

**R4C4. nit. CONFIRMED (code read and probe).** Small edges in the lock and tip work:
- **Undo can drop a newer save of the same key.** `_undo_fields` (`config.py:146-161`) puts back this request's keys over another writer's newer save of the same key. The probe confirmed it. No UI sends `local_model` and `tailnet` together, so this is unreachable today.
- **The sargam migration saves outside the lock's read.** `maybe_migrate_sargam_model` (`migrate.py:164`, inside `load_config`) saves a copy read outside the lock when the caller holds no lock, such as GET handlers. The fixer's "covered, reentrant" holds only for callers that already hold the lock. It fires once per install, ever.
- **The tip can loop for a diarize-plus-free user.** With `diarize: true` and `quality: free`, `use_local_tip` still tells the user to `config set quality free`, because diarize skips the local tier (`resolve.py:66-75`).
- **Two onboard commands one line apart.** The pre-flight error says "Or: anyscribe onboard --force", and the hint below it says "run `anyscribe onboard`". After `local setup`, the bare command answers "Pass --force". It names the fix, so this matters little.

**Judgement on the fixer's other leftovers:**
- *Setup window skips its result screen on an instant setup:* does not matter before merge. The window opens only when `!setUp`, meaning no model is runnable (`SettingsPage.tsx:1014`), so a real setup always downloads. The one exception is ffmpeg missing.
- *No special superseded message:* only reachable with two tabs. See R4C3.
- *`onboard` after `local setup` asks for --force:* the message names the fix, and `local setup` now prints the shorter `quality free` tip.

**Checked and holding:**
- **Lock ordering with the tailnet lock:** the tailnet save takes the tailnet lock, then the config lock. `PUT /api/config` releases the config lock before the tailnet part, and its undo re-takes only the config lock. No path takes the config lock and then the tailnet lock. Startup `share.apply(True)` takes no config lock.
- **Reentrancy:** `set_value` inside a held config lock is fine (reentrant lock; the probe nested it). `activate` and `_settle_pending` hold the plain queue lock and call `set_value`, which never takes the queue lock.
- **Event-loop thread:** the PUT and `save_onboarding` critical sections contain no `await`, so the per-thread reentrant lock cannot be re-entered by another handler on the same thread.
- **Choose racing setup start:** the order is decided by who gets the queue lock first. Both orders were traced; the newer one wins.
- **Two setups:** the `running` flag is set synchronously on the event loop, so a second start gets 409.
- **A choose that takes a generation and then fails:** probe result: setup superseded, default unchanged (`large-v3-turbo`), pending `failed` with its error. This is defensible: the newest intent wins and fails loudly. The user ends up with neither model; say so in the release notes only if you want to.
- **Tests:** the new concurrency tests assert which provider, quality and model survived, and the fixtures use `tmp_path` plus the suite-wide temporary HOME.
- **Owner data:** no `/home/…`, `.env` or personal names in the delta's added lines. The rebuilt bundle `index-DYC4GSkO.js` contains "This is already your default" and `use_local_tip`.

## 4. Pending owner checks

- Mac re-measure with the CPU provider forced. Still not in the proof.
- `mockup.html` in the public repo still says "i5-10600K" and "your vault": keep or mask? Carried over from rounds 2 and 3.
- Representative Hindi and Hinglish quality.
- Optional: whether the web setup result should offer a "Make it my default" button instead of the `config set quality free` command. The window shows a terminal command with literal backticks, the same kind of complaint as R3F2.

## 5. Could not check; what I inspected

**Not run (brief forbids):**
- Unit and docs checks: `cd ~/labs/projects/anyscribe-wt/local-first && .venv/bin/pytest -q && .venv/bin/ruff check src tests && .venv/bin/python scripts/check-docs.py`
- UI checks: `cd ui && npx tsc -b && npm run lint && npm run build`
- The two-tab walk for R4C3: `HOME=/tmp/r4/home HF_HOME=/tmp/r4/hf .venv/bin/anyscribe ui --port 8497 --no-open`, then start a setup in one tab and click a card in another.
- No real download, browser or audio run.
- The test counts differ: the proof says 911 passed and 5 skipped; the lead says 912 and 4. 47f6973 adds a test, so the pass count fits, but the skip count is unexplained. I could not re-derive either.

**Inspected:**
- Packet: brief-r4, ask, target, lens, declined, review-log, fix-plan-r3, diagnosis-r2, spec section 5, the round-3 reports in findings.md, and proof.md's "Round 3 fixes".
- The full Python and UI delta. Code read beyond the delta: `web/routes/models.py` (whole file), `web/routes/local.py` (status, setup, choose), `core/tailnet.py` `Share`, `routes/system.py`, `routes/onboarding.py` save, `core/resolve.py`, `core/quality.py`, `core/local_setup.py` (run_setup, install), `local_models` readiness and pull, `cli/transcribe.py`, `cli/batch.py`, `orchestrator`'s pre-flight order, `OnboardingWizard` finish, `LocalSetupModal`, the Settings quality and setup buttons, `TranscribePage` `PlanNotes`, `tests/conftest.py`, and the new tests.
- Greps: every `save_config`, `CONFIG_LOCK`, lock and `CONFIG_FILE` writer; every `run_setup`, `check_status` and `parakeet_suggestion` caller; owner-data strings in the delta.

Not checked: real-browser rendering, install paths, Windows and macOS.
~~~~~
