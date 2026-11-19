# Findings (every reviewer report, verbatim)

## report-gpt-6.1-sol-r1.md (round 1)

Absolute home-folder paths rewritten as ~ paths.

~~~~~
**NOT YET.**

The build addresses the owner’s job: guided, key-free local transcription with Parakeet and Whisper. However, the normal onboarding path still produces an API-key warning, the language guard does not uphold the stated safety guarantee, and several download states are reported as ready prematurely.

Reviewed frozen commit `87dbd2f`, against `b2bafa7`. CONFIRMED below means reproduced through permitted read-only inspection or traced through the code; supplied runtime measurements are identified separately.

1. **C1 | blocker | CONFIRMED: Normal onboarding leaves the Transcribe page using its old quality setting.**

   **Where:** [TranscribePage.tsx:48](~/labs/projects/anyscribe-wt/local-first/ui/src/pages/TranscribePage.tsx:48), [App.tsx:44](~/labs/projects/anyscribe-wt/local-first/ui/src/App.tsx:44), [OnboardingWizard.tsx:125](~/labs/projects/anyscribe-wt/local-first/ui/src/components/OnboardingWizard.tsx:125).

   The Transcribe page mounts behind the wizard, reads the initial `balanced` configuration once, and stays mounted after onboarding saves `provider=local, quality=custom`. Its next submission still sends `quality=balanced`. The backend then generates the screenshot’s Deepgram API-key warning. This requires no fast-click race. With a Deepgram key present, the same stale override can route audio to cloud after the person chose local.

   **Fix:** Refresh the page’s configuration after onboarding completes, and prevent submissions before initial configuration loads. Preserve warnings for deliberate cloud-tier choices.

2. **C2 | blocker | CONFIRMED: The specified guard cannot guarantee that unsupported-language audio never reaches Parakeet.**

   **Where:** [local.py:178](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/providers/local.py:178), [local.py:197](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/providers/local.py:197), [CHANGELOG.md:23](~/labs/projects/anyscribe-wt/local-first/CHANGELOG.md:23).

   Direct inspection returned `('parakeet-v3', 'en', [])` for `plan("parakeet-v3", "en", None)`: an explicit supported label bypasses audio checking completely. Consequently, Hindi audio labelled English reaches Parakeet without a switch note.

   In auto mode, only the first 30 seconds determine the model for the entire recording. English followed by Hindi remains on Parakeet. Leading silence is also unchecked: probability is discarded and no speech-presence check occurs.

   This additionally changes existing Whisper behavior. Previously, faster-whisper detected language after its silence filtering; the new `_whisper()` forces a language detected from the unfiltered opening window.

   **Fix:** Correct the safety design before claiming “never writes Parakeet gibberish.” Detect from actual speech, handle uncertain detection explicitly, and either support language changes within recordings or clearly limit the feature to switching between separate recordings. Real mixed-language and leading-silence runs remain necessary.

3. **C3 | blocker | CONFIRMED: The tracked review packet contains owner-specific machine paths.**

   **Where:** [target.md:9](~/labs/projects/anyscribe-wt/local-first/docs/reviews/2026-11-19-local-first-parakeet/target.md:9).

   The public-repository diff includes the owner’s absolute scratch paths, embedded username and session identifier. These would travel with the branch when published, contrary to the explicit no-owner-paths invariant. I have not established that they are already public.

   **Fix:** Keep private dispatch paths outside the public repository and sanitize the packet in the unpublished history. The inspected new fixtures use generic content; I found no committed benchmark transcript text there.

4. **C4 | should-fix | CONFIRMED: Parakeet takes the known slow CoreML path on Apple silicon.**

   **Where:** [local.py:120](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/providers/local.py:120).

   Both model and VAD loading omit an execution-provider choice. The installed onnx-asr loader defaults to ONNX Runtime’s available-provider list. This matches the supplied Mac evidence: default loading took 110.6 seconds versus 0.9 seconds with CPU, and transcription ran at 3.1× versus 23.6× realtime.

   **Fix:** Explicitly select the tested CPU provider for both loads within this CPU-focused scope, then repeat the actual application path on the Mac. I traced provider selection but did not repeat those timings.

5. **C5 | should-fix | CONFIRMED: Partial downloads count as usable models and cannot resume through ordinary Pull.**

   **Where:** [local_models.py:340](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/providers/local_models.py:340), [local_models.py:485](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/providers/local_models.py:485), [SettingsPage.tsx:159](~/labs/projects/anyscribe-wt/local-first/ui/src/pages/SettingsPage.tsx:159).

   Any repository bytes make `cached=True`. After an interrupted download, Pull skips downloading and reports `already_present`. The language guard can select that incomplete Turbo over a complete Small. Settings can also make a pending model the default before its download finishes.

   Readiness does not include helpers either. A person can switch to Whisper, delete Tiny, then select the still-cached Parakeet card. Selection does not restore Tiny; the next auto transcription fails.

   **Fix:** Separate disk presence from complete, usable readiness. Validate the required model files and helpers, resume incomplete downloads, and require readiness before fallback selection or default activation.

6. **C6 | should-fix | CONFIRMED: “A mix” setup finishes before its required second model is ready.**

   **Where:** [OnboardingWizard.tsx:539](~/labs/projects/anyscribe-wt/local-first/ui/src/components/OnboardingWizard.tsx:539), [LocalSetupModal.tsx:79](~/labs/projects/anyscribe-wt/local-first/ui/src/components/LocalSetupModal.tsx:79).

   Both flows enqueue Turbo and immediately advance or close. Queue acceptance is treated as completion, and request failures are swallowed. The builder’s proof explicitly records the wizard finishing while Turbo is downloading. An immediate Hindi job can fail despite the promise of automatic switching.

   **Fix:** Track all accepted recommendation downloads to completion, show failures, and keep “ready” wording consistent with what can actually run.

7. **C7 | should-fix | CONFIRMED: Low-disk recommendations contradict their own instructions and can recommend an impossible download.**

   **Where:** [local_recommend.py:191](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/core/local_recommend.py:191).

   Read-only evaluation reproduced:

   - `mix`, 16 GB RAM, 1,500 MB free: returns Parakeet alone while retaining “uses two models” and “switches to Turbo automatically.”
   - `english`, 16 GB RAM, 10 MB free: returns Base, although its stated download is 140 MB, while retaining the original Parakeet explanation.

   **Fix:** Generate reasons from the final feasible selection. When nothing fits, return an explicit insufficient-space result. For mixed-language use, prefer a fitting multilingual model over dropping the only unsupported-language fallback.

8. **C8 | should-fix | CONFIRMED: The picker presents reference-machine measurements as unqualified performance expectations.**

   **Where:** [LocalModelPicker.tsx:174](~/labs/projects/anyscribe-wt/local-first/ui/src/components/LocalModelPicker.tsx:174).

   The cards show “1 hour of audio ≈ 10 min,” accuracy and speed ratings without identifying the benchmark machine or saying accuracy was measured on English. Neither the rendered picker nor its guidance supplies that context. The approved mockup included this qualification; the CLI table also has one.

   **Fix:** Put a visible benchmark explanation beside the shared picker: English sample, reference CPU, model already loaded, and actual times vary by machine. Describe the recommendation’s “4×” comparison on the same basis.

9. **C9 | should-fix | CONFIRMED: Switch notes disappear on cached runs and ordinary batch output.**

   **Where:** [orchestrator.py:98](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/core/orchestrator.py:98), [batch.py:143](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/cli/batch.py:143), [batch.py:196](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/cli/batch.py:196).

   Cached results restore `model` from frontmatter but omit saved `notes`. Repeating a switched Hindi transcription therefore loses the explanation from CLI JSON, MCP and the Web result.

   Human batch processing always invokes the pipeline quietly, then prints only status and title. Although JSON rows contain notes, ordinary terminal batches never display them.

   **Fix:** Restore notes from cached frontmatter and print per-file switch notes in human batch results. Current propagation tests cover fresh results, not these paths.

10. **C10 | should-fix | CONFIRMED: Repairing PyAV inside the running Web server leaves the incompatible module loaded.**

    **Where:** [local_setup.py:143](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/core/local_setup.py:143), [local_setup.py:205](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/core/local_setup.py:205).

    Readiness checking imports faster-whisper, which imports `av`. Setup can then downgrade PyAV 19 on disk, but `importlib.invalidate_caches()` does not replace imported modules. Subsequent decoding in that server still uses the old `av` object and can retain the `metadata_errors` failure despite reported setup success.

    I verified the retained-module mechanism; I did not perform an installation downgrade.

    **Fix:** Require and communicate a server restart after replacing an already-loaded incompatible runtime, or run transcription in a fresh process. Verify decoding in the process that will serve the next job.

11. **C11 | should-fix | CONFIRMED: A pending recommendation can overwrite a later explicit model choice.**

    **Where:** [SettingsPage.tsx:159](~/labs/projects/anyscribe-wt/local-first/ui/src/pages/SettingsPage.tsx:159), [SettingsPage.tsx:603](~/labs/projects/anyscribe-wt/local-first/ui/src/pages/SettingsPage.tsx:603).

    Accept an uncached Parakeet recommendation, then select an already-downloaded Whisper card while Parakeet downloads. The later selection does not clear `pendingDefault`; polling subsequently writes Parakeet back over it.

    **Fix:** Cancel or supersede pending activation whenever the person makes another model choice. Tie completion to the latest accepted selection.

**Answers to the brief**

The overall instrument is appropriate for the owner’s request. The language-safety specification needs correction, however; implementing its explicit bypass and opening-window rule faithfully does not satisfy its stronger invariant.

The API-key warning is reachable through normal wizard completion. Calling it only a scripted submission race understates the defect.

The card timings exceed what the screen knows about the current computer. The measured numbers remain useful when visibly labelled as reference measurements.

The supplied green suite and mutation results support the tested routing and command construction. They do not establish complete-download readiness, mixed-recording safety, first-run state refresh, or the running-server upgrade path.

**Pending owner checks**

Confirm whether “A mix” includes both languages within one recording, and whether representative Hindi/Hinglish output is acceptable. These are product acceptance checks. The code defects above do not require owner action to investigate or fix.

**Inspection and limits**

I read every packet file, the declined list, approved mockup and all 14 screenshots; inspected the frozen diff, local provider, registry, installation and recommendation code, CLI/Web/MCP propagation, onboarding, relevant documentation and new tests; and traced installed faster-whisper and onnx-asr implementation details. The worktree remained clean.

Per the brief, I ran no tests, builds, installs, downloads, servers or real transcription. The following checks were not repeated:

```sh
cd ~/labs/projects/anyscribe-wt/local-first
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts
.venv/bin/python scripts/check-docs.py
```

```sh
cd ~/labs/projects/anyscribe-wt/local-first/ui
npx tsc -b
npm run lint
npm run build
```

Real onboarding and engine checks also remain unexecuted under this review’s restrictions:

```sh
cd ~/labs/projects/anyscribe-wt/local-first
HOME=/tmp/anyscribe-correctness/home HF_HOME=/tmp/anyscribe-correctness/hf \
  .venv/bin/anyscribe onboard --yes --provider local --local-model parakeet-v3 --json

HOME=/tmp/anyscribe-correctness/home HF_HOME=/tmp/anyscribe-correctness/hf \
  .venv/bin/anyscribe transcribe \
  <lead scratch folder>/testaudio/english-1.wav --json

HOME=/tmp/anyscribe-correctness/home HF_HOME=/tmp/anyscribe-correctness/hf \
  .venv/bin/anyscribe transcribe \
  <lead scratch folder>/testaudio/hindi-1.wav --json
```

Interactive onboarding, interrupted-download recovery, actual runtime replacement, Windows behavior and Mac application performance remain unverified by this reviewer.~~~~~

## report-opus-r1.md (round 1)

Absolute home-folder paths rewritten as ~ paths.

~~~~~
FIT REVIEW, round 1. Target: feat/local-first-parakeet @ 87dbd2f (code 0aff252), diff b2bafa7..87dbd2f

## 1. Verdict

**NOT YET.** This is the job the owner asked for, and the spec mostly fits it. The Parakeet engine, the language check, the "On this computer vs cloud" first choice, the cards and Help me choose are all there, and the Settings card follows the approved mockup closely. One problem breaks a must-never rule. A brand-new key-free user who finishes the new wizard and transcribes straight away is shown "WARNING: quality 'balanced' wants deepgram but no DEEPGRAM_API_KEY is set" (F1). This is not a rare race: it happens every time on the main new-user path. After F1, the Help me choose guidance has gaps. It does not always explain *why*, it does not apply its own suggestion until a second click, and it hides a 1.6 GB extra download (F2 to F6).

## 2. Findings (most severe first)

**F1. blocker. CONFIRMED by trace (not run in a browser).** `ui/src/pages/TranscribePage.tsx:48` and `:56-67`, `ui/src/App.tsx:47-52`.
- **Scenario:** fresh install, no keys. `anyscribe ui` opens. The Transcribe page mounts behind the wizard and fetches `/api/config` once (`useEffect(..., [])`). No config has been saved yet, so it gets the dataclass default `quality: "balanced"` (`config/settings.py:41`). The user picks On this computer, sets up Parakeet and clicks "Finish & start transcribing". `onClose` only hides the modal. The Transcribe page is not remounted and does not refetch, so its `quality` state is still "balanced".
- **Result:** the first paste-and-transcribe sends `quality: "balanced"`. `web/routes/transcribe.py:74-75` applies it, and `core/resolve.py:79-83` emits the deepgram-key WARNING on the local path. The options summary under the URL box also reads "balanced", even though onboarding saved `custom`.
- **Lead question 2:** this is exactly the builder's `result-note-1440.png`. It is deterministic on the wizard path, not a load-time race.
- **Fix:** send `quality` only when the user actually changed it, so the server uses the saved config. Also refetch config when the wizard closes (for example, App bumps a key on TranscribePage, or the wizard calls a refresh callback).
- **Test that settles it:** walk wizard, then Finish, then transcribe in one page session, and assert the job's `plan.notes` carry no "WARNING".

**F2. should-fix. CONFIRMED (code).** `ui/src/components/LocalModelPicker.tsx:286` (`ask`) and `:356` (`onUse` only on the button).
- **Problem:** answering the language question does not select the suggestion. Only a second click on "Use this" does. The spec says "Defaults pre-select the recommendation".
- **Scenario:** in the wizard a Hindi speaker clicks "Hindi or another Indian language" and sees "Suggested: Whisper Large v3 Turbo". Parakeet stays selected, and the big button still says "Download Parakeet v3 and set up" (`OnboardingWizard.tsx:689`). They click it. Their first Hindi transcript then fails with "download Turbo".
- The same gap applies to "A mix": without "Use this", Turbo is never queued.
- **Fix:** apply the suggestion when the question is answered, and drop the "Use this" / "Selected" button. The "Selected" label also looks like a primary call to action that does nothing.

**F3. should-fix. CONFIRMED (code).** Mix path: Turbo downloads without the user being told. See `OnboardingWizard.tsx:540-545` (pulls `rec.also` after setup), `cli/onboard.py:334`, and the Settings `handleRecommendation`.
- **Problem:** the user is told "Download Parakeet v3 and set up" (670 MB). Another 1.6 GB of Turbo then downloads in the background.
- Neither the recommendation box, the button, the "All set" summary (`OnboardingWizard.tsx:791-796`, which lists only parakeet-v3) nor the CLI line ("Downloading Whisper Large v3 Turbo for the other language…", no size) states the size or that it is still running.
- **Second effect:** if the user transcribes Hindi while that download is still running, the guard can pick the half-downloaded Turbo. The builder's own risk note says "cached" means any bytes on disk. That fails loudly, but confusingly.
- **Fix:**
  - Put the total in the suggestion, e.g. "downloads 670 MB + 1.6 GB".
  - Put it on the button: "Download Parakeet v3 + Whisper Large v3 Turbo (2.3 GB)".
  - Show Turbo's download progress on All set.
  - Make the CLI title say "Parakeet v3 + Whisper Large v3 Turbo", with sizes.

**F4. should-fix. PLAUSIBLE (spec-level, not reproduced).** The "A mix (e.g. English and Hindi)" answer, `core/local_recommend.py:168-174`, plus the CHANGELOG line "anyscribe never writes Parakeet gibberish" (`CHANGELOG.md:23`).
- **Problem:** the language check listens only to the first 30 seconds of each file. Someone who picks "a mix of English and Hindi" most likely has recordings that switch language mid-file (Hinglish). That is the owner's own market.
- **Scenario:** a voice note opens in English for 30 seconds, then goes to Hindi. It passes the check, and Parakeet writes the Hindi part as romanized gibberish with no note. That is the must-never, at the level of parts of a file.
- The reason text "anyscribe switches to Turbo automatically for Hindi" promises more than this, and "never writes gibberish" in the CHANGELOG over-claims.
- **Fix, owner's call:**
  - (a) For "mix", make Turbo the main model. It is equally accurate on English in the spec's own table; it is just slower.
  - (b) Or keep Parakeet, and say plainly: "Each recording is checked by its first 30 seconds; if one recording switches between English and Hindi, Turbo is the safer pick."
  - Either way, reword the CHANGELOG to "checks the language of the first 30 seconds".
- **How to settle:** one code-switched clip through `anyscribe transcribe` with parakeet-v3 as the default.

**F5. should-fix. CONFIRMED (code).** The Help me choose reasons do not always explain *why*. See `local_recommend.py:147-185`.
- **"Something else" cites Hindi.** "Indian" and "other" share one branch. A Japanese speaker reads "You said a language outside English and Europe… Turbo fits: it was the most accurate local model on Hindi in our test."
- **The English reason is confusing:**
  - "Parakeet v3 fits: it matches the most accurate local model on English at about 4× its speed." A reader cannot tell what "it" and "its" refer to. Parakeet is itself the top-rated model.
  - It cites "15.5 GB of memory", which plays no part in that pick, so it reads like reasoning without being reasoning.
- **The Hindi pick leaves language on auto.** The spec's own numbers show Turbo on auto-detect is about 3× worse on Hindi (character error rate 28.5) than with language set to Hindi (9.9). Nothing tells the user to set it, or offers to. The mockup's note had "set your language to Hindi in Settings"; the built note dropped it.
- **Fix:**
  - Give "other" its own sentence, about 95+ languages.
  - English: "As accurate as Whisper Large v3 Turbo on English, and about 4 times faster on a typical desktop."
  - Cite memory only when it changed the pick.
  - For the Hindi answer, add one line plus a one-click "Set my language to Hindi", and restore the mockup's next step on the switch note.

**F6. should-fix. CONFIRMED (code + screenshots).** The speed numbers on the web cards claim more than anyone knows. See `LocalModelPicker.tsx:176`, the `use_for` text, and `local_recommend.py` "4×".
- **Problem:** "1 hour of audio ≈ 10 min", "Fastest accurate option" and "about 4×" are shown with no note on which machine they were measured.
  - The approved mockup had that footnote.
  - The CLI table has a caption (`cli/models_cmd.py:123`).
  - The web picker has neither.
- **On the owner's Mac (lead evidence 1),** with the shipped default runtime settings:
  - Parakeet loads in 110 s and runs at 3.1× realtime.
  - Turbo runs at 3.2×.
  - So "Fastest" and "4× faster" are false there.
  - With the CPU fix they become understated: 23.6× against 3.2×.
- **Lead question 3:** yes, the screen claims more than it knows.
- **Fix:** add one caption line under the cards: "Times measured on a 6-core desktop without a graphics card; your computer may differ." This depends on the correctness side forcing `CPUExecutionProvider`; without that fix, the Mac claim is wrong even with the caption.

**F7. should-fix. PLAUSIBLE.** `OnboardingWizard.tsx:315-321`.
- **Problem:** the approved first-run line "Downloads Parakeet v3 (670 MB) once. About 10 minutes per hour of audio…" is missing from all three wizard-1 screenshots (390, 1000, 1440). It renders only after `/api/local/status` resolves, so either the screenshots were taken early or the call failed on a fresh home.
- **Settle:** open the wizard on a fresh HOME, wait 3 s, look again.
- **Fix if it is slow:** show the size from a static fallback, or show a loading state.

**F8. should-fix. CONFIRMED.** `docs/user/getting-started.md:36-37` ("What you need") still says the local provider "runs Whisper on your machine" and "Or an API key… OpenAI is the default". That contradicts the local-first story told 70 lines later. Fix: lead with local (Parakeet), cloud second.

**F9. nit. CONFIRMED (screenshots).** Smaller issues:
- **Step numbering:** the local path jumps from "Step 1 of 5" to "Step 3 of 5" because the API-key step is skipped.
- **Raw IDs instead of names:**
  - The "All set" summary shows raw IDs ("Provider local", "Local model parakeet-v3").
  - So does the result card ("local · large-v3-turbo").
  - So does the CLI's final "Default model: parakeet-v3" (`cli/onboard.py:343`).
  - The rest of the UI uses display names.
- **Two sizes on one card:** "downloaded · 639 MB" sits beside "Download 670 MB", and 1547 MB beside 1.6 GB.
- **Clicking a not-downloaded card in Settings does nothing and says nothing.** It is aria-disabled with no visible reason. Add "Download it first to make it the default".
- **Icons with no visible label:** the reinstall and delete icons have no visible text (aria-label only).

**F10. nit. CONFIRMED.** Repo hygiene on the public repo:
- The packet adds about 7 MB of PNGs, the first screenshots ever committed under `docs/reviews`.
- `target.md` carries `<lead scratch folder>/...` paths. `/Users/rish` paths already exist in earlier packets on main, so this has precedent.
- `mockup.html` says "measured on your desktop (i5-10600K)" and "scored against the ElevenLabs transcripts already in your vault".
- None of this is transcript text. Owner's call whether the screenshots and mockup belong in the public repo or should stay in the review-runs folder.

## 3. Answers to the brief's questions

- **Q2 (where the WARNING came from):** see F1. It comes from TranscribePage's stale "balanced" state, captured before the wizard saved `quality: custom`. A real key-free user reaches it every time on the wizard, then Finish, then transcribe path. CLI and headless onboarding set `custom` and do not hit it.
- **Q3 (card numbers):** see F6. They come from one Linux desktop, and the web UI does not say so. On the Mac they are wrong in both directions, depending on the CoreML/CPU fix.
- **Is this what he asked for / is it the simplest thing?** Yes on scope. The Spokenly-style cards and Help me choose match the ask and the mockup. The Settings card is a faithful build of mockup panel 1. Not gold-plated: the "beyond spec" items are small and useful. The one place it is not simplest is the extra "Use this" click (F2). The 5-step wizard, including the workspace step, is pre-existing; it is heavier than the mockup's one-screen first run, but acceptable.

## 4. Pending owner checks

- For "A mix", should the main model be Turbo (safe for Hinglish recordings) or Parakeet with a plain warning (F4)?
- Is a 1.6 GB background download acceptable on the mix path, provided it is shown up front (F3)?
- On his Mac, after the CPU-runtime fix: does the first Parakeet run feel fast, and does the "4× faster" sentence hold?
- Do the screenshots and the mockup belong in the public repo (F10)?

## 5. Could not check, and what I inspected

- I ran no browser, server or tests, per the brief.
- F1 is traced, not reproduced. To settle it: fresh `HOME`/`HF_HOME`, `anyscribe ui --port <spare> --no-open --local-only`, then wizard, then On this computer, set up, Finish, then submit a local file, then `GET /api/jobs/<id>` and check `plan.notes` for "WARNING".
- F4 needs a code-switched English-then-Hindi clip: `anyscribe transcribe <clip> --json` with `local_model: parakeet-v3`.
- F7 needs the wizard opened and given time to load.
- I did not drive the interactive `anyscribe onboard` TUI; I read it in `cli/onboard.py`.
- **Inspected:**
  - The packet: ask, spec, target, proof, lens, mockup.html, all 14 screenshots.
  - UI files: `OnboardingWizard.tsx`, `LocalModelPicker.tsx`, `SettingsPage.tsx` (diff), `TranscribePage.tsx`, `App.tsx`, `ResultCard.tsx` (diff).
  - Backend files: `core/local_recommend.py`, `core/resolve.py`, `config/settings.py`, `web/routes/local.py`, `web/routes/transcribe.py`, `cli/onboard.py` (diff), `cli/models_cmd.py`, `cli/main.py` doctor, `providers/local_models.py` (copy fields).
  - Docs: CHANGELOG Unreleased, README and getting-started diffs, greps over docs and skill for "4×" claims.

Skipped: correctness of the engine, the guard internals and the install paths. Those belong to the correctness reviewer. Biggest risk: F1 shows an API-key warning to exactly the user this build is for.
~~~~~


## report-gpt-6-astra-r2.md (round 2)

Absolute home-folder paths rewritten as ~ paths.

~~~~~
**NOT YET.** The main onboarding warning and Mac performance fixes are present, but readiness, recommendation handling and packet sanitization still have confirmed gaps.

Reviewed `feat/local-first-parakeet` at `8c5d10d7cd4175112afb7e6a502f27bc5cc19e40`, against `87dbd2f`. The worktree remained clean. “CONFIRMED” below means traced in the code or reproduced with read-only, in-memory probes, not a real-engine or browser run.

All relative paths below are under `~/labs/projects/anyscribe-wt/local-first/`.

**Earlier findings**

| Finding | Status | Evidence |
|---|---|---|
| C1 | FIXED | `TranscribePage.tsx:83` sends quality only after an explicit selection; `App.tsx:55` remounts the page after onboarding. Submission waits for configuration. |
| C2 | PARTLY | Speech windows and Whisper auto behavior are repaired, but uncertain uncovered-language guesses bypass uncertainty handling. See R2C1. The explicit-language exception remains DECLINED-OK. |
| C3 | PARTLY | Screenshots are absent from the target tree and `target.md` is sanitized, but newly tracked reports repeat owner-specific paths. See R2C6. |
| C4 | FIXED | `providers/local.py:126` explicitly selects CPU for both Parakeet and VAD. The supplied Mac measurement supports this; I did not repeat it. |
| C5 | PARTLY | Required-file checks, resumable pulls and stale-blob handling work as inspected. Default activation still ignores helper readiness. See R2C3. |
| C6 | PARTLY | Normal setup now discloses and tracks the second download, but the wizard’s separate Next path bypasses it. See R2C4. |
| C7 | PARTLY | Backend probes return Small for mix/1,500 MB and no recommendation for English/10 MB. The UI retains its previous selection when nothing fits. See R2C5. |
| C8 | FIXED | The shared picker renders the benchmark caption; comparison wording uses the accepted “our test desktop” qualification. |
| C9 | FIXED | Cached results restore notes at `core/orchestrator.py:107`; batch rows retain and print each file’s notes at `cli/batch.py:200`. |
| C10 | PARTLY | Running-server restart detection and banners are implemented. Unchanged package versions produce no restart flag. Human headless onboarding omits the message. See R2C7. |
| C11 | FIXED | The original pending-download scenario is repaired: explicit selection clears the pending ref, and polling reads that ref after awaiting status. |
| F1 | FIXED | Same evidence as C1. |
| F2 | PARTLY | Answers now apply immediately, but an older response can overwrite a newer choice. See R2C2. |
| F3 | PARTLY | Sizes, progress and failures are displayed on the normal path; the Next bypass remains. See R2C4. |
| F4 | FIXED | The binding three-window design and Hinglish qualification are implemented. A controlled English/Hindi/English detection sequence routes to Whisper. |
| F5 | FIXED | Separate “other” guidance, final-pick explanations and the explicit Hindi-setting action are present. |
| F6 | FIXED | Same evidence as C8. |
| F7 | FIXED | The first screen uses the lightweight registry endpoint; the supplied corrected screenshot shows the size and qualified timing. |
| F8 | FIXED | `docs/user/getting-started.md:36` now leads with local transcription; README agrees. |
| F9 | FIXED | The named step-count, display-name, duplicate-size, selectable-card and visible-button-label changes are present. |
| F10 | PARTLY | PNGs were removed from the tracked tree, but reports still contain machine paths. See R2C6. |

**Remaining and newly introduced defects, most severe first**

1. **R2C1 | should-fix | CONFIRMED: Uncertain language detection can force the wrong language.**

   Where: [local.py:228](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/providers/local.py:228), uncertainty handling at line 250.

   The uncovered-language branch runs before the “all probabilities below 0.5” branch. Supplying `[("hi", 0.2)]` returned Turbo with forced `language="hi"` and “Detected Hindi”. With no fallback, it raised the Hindi download error. The equally uncertain `[("en", 0.2)]` correctly took the unsure path.

   A short or unclear recording can therefore receive a confidently stated, forced language that the checker did not establish. Existing uncertainty tests use only covered-language guesses and miss this case.

   Fix: handle the defined all-low-confidence condition before ordinary language switching. Preserve the agreed behavior: Whisper auto when available, otherwise Parakeet with an uncertainty note.

2. **R2C2 | should-fix | CONFIRMED: Automatic recommendations can overwrite a newer choice. NEW.**

   Where: [LocalModelPicker.tsx:296](~/labs/projects/anyscribe-wt/local-first/ui/src/components/LocalModelPicker.tsx:296), `SettingsPage.tsx:207`.

   Select Hindi, then English while the first recommendation request is pending. If English returns first and Hindi returns last, both responses call `onUse`. The older Hindi response becomes the final model selection, although the selected answer remains English. Settings can immediately save that obsolete choice or start its download.

   The new automatic application makes the existing response-order race affect persisted settings. Clearing `pendingDefault` does not protect this path.

   Fix: invalidate obsolete recommendation responses when another answer or model card is selected. Apply only the latest choice. Verify with deliberately reversed response completion order.

3. **R2C3 | should-fix | CONFIRMED: Parakeet becomes the default before its helpers are ready. Residual C5.**

   Where: [SettingsPage.tsx:172](~/labs/projects/anyscribe-wt/local-first/ui/src/pages/SettingsPage.tsx:172), `SettingsPage.tsx:194`, `providers/local_models.py:363`, `web/routes/config.py:138`.

   `cached` checks the model files alone. Settings activates a pending Parakeet as soon as those files exist, even while Tiny or VAD is still downloading. Selecting an already-cached Parakeet also saves the default immediately, then queues missing helpers.

   A probe confirmed that Parakeet can report ready while `helpers_ready()` is false. With Tiny missing, the next auto transcription fails at `detect_languages`, despite the promise that the model becomes the default “when done”. A helper-download failure does not restore the previously working default.

   Fix: distinguish downloaded weights from runnable readiness. Keep the existing default until the selected model and its required helpers are ready; retain a visible failed/pending state otherwise.

4. **R2C4 | should-fix | CONFIRMED: The wizard can skip its promised second download. Residual C6/F3.**

   Where: [OnboardingWizard.tsx:770](~/labs/projects/anyscribe-wt/local-first/ui/src/components/OnboardingWizard.tsx:770), `OnboardingWizard.tsx:583`, `core/onboard_headless.py:270`.

   The separate Next button appears whenever *any* model makes `status.set_up` true. It calls `onNext` directly, bypassing the code that captures and queues the extra models.

   With Parakeet already installed but Turbo absent, choose “A mix”, then Next. The summary loses Turbo, and Finish sets up only the primary model. The next Hindi recording still fails asking for Turbo.

   With only Turbo already downloaded, the same path labels the newly selected Parakeet “ready” before downloading it; Finish then performs the missing setup synchronously.

   Fix: permit continuation only when the current selection’s setup requirements have been satisfied. All continuation paths must retain the chosen extra models and their actual status.

5. **R2C5 | should-fix | CONFIRMED: A no-space recommendation leaves an impossible download selected. NEW integration gap.**

   Where: [LocalModelPicker.tsx:305](~/labs/projects/anyscribe-wt/local-first/ui/src/components/LocalModelPicker.tsx:305), `OnboardingWizard.tsx:740`, `LocalSetupModal.tsx:338`.

   The backend correctly returns `primary: null` when nothing fits. However, `onUse` is called only for a non-null primary. The wizard and modal therefore keep their previous selection, normally Parakeet, and leave its download button enabled.

   With 10 MB free, the screen can simultaneously say “Not enough disk space” and offer the still-selected Parakeet download. This contradicts the proof’s claim that Web selects nothing.

   Fix: propagate the no-fit result to the parent and clear or suspend the obsolete selection. Require a fresh explicit choice before attempting another download.

6. **R2C6 | should-fix | CONFIRMED: The review reports reintroduce the paths that cleanup was meant to remove. NEW copies of C3/F10.**

   Where: [findings.md:258](~/labs/projects/anyscribe-wt/local-first/docs/reviews/2026-11-19-local-first-parakeet/findings.md:258) and [report-opus-r1.md:90](~/labs/projects/anyscribe-wt/local-first/docs/reviews/2026-11-19-local-first-parakeet/report-opus-r1.md:90).

   Both tracked files quote owner-specific scratch/home path prefixes. These are present in the final target tree, not merely its earlier history. Squashing alone will therefore retain them.

   Fix: sanitize the public copies while preserving verbatim originals outside the repository. Check the complete final tree and the eventual squashed artifact, not only changes after the cleanup commit.

7. **R2C7 | nit | CONFIRMED: Human headless onboarding omits the restart notice. Residual C10.**

   Where: [onboard.py:148](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/cli/onboard.py:148).

   The `onboard --yes` human-output path prints “Local transcription ready” without inspecting `result["local_setup"]["restart_needed"]`. JSON retains the nested result, and interactive onboarding prints the notice correctly.

   Fix: render the restart notice here too. The command itself exits, so this is narrower than the repaired long-lived-server failure.

**Probe results and evidence limits**

The permitted probes established:

- A Hindi middle-window detection switches to Whisper, or fails loudly when no fallback exists.
- Two-second and five-second speech inputs produce one appropriately sized window. No-speech input produces no windows and reaches the unsure policy.
- A stale `.incomplete` file is ignored when its completed blob exists; an unfinished blob blocks readiness.
- Tiny ready/VAD missing correctly makes `helpers_ready()` false, but does not make Parakeet’s own `cached` state false.
- Three controlled batch results preserve model identities and attach the switch note only to the second file.
- Unchanged package versions do not raise the restart flag.
- `config set local_model parakeet-v3` supplies a missing-helper download hint; it does not provision the helpers.

These probes used controlled detection results, filesystem objects or downstream results. They do not establish real short-clip recognition, silence transcription quality, actual download recovery or browser behavior.

**Pending owner checks**

Representative Hindi/Hinglish output quality and whether the Mac experience feels acceptable remain owner acceptance checks. Diagnosing and fixing the defects above requires no owner action.

**Inspection and checks not run**

I read the named brief, delta, packet files and declined list; traced the changed provider, cache, setup, recommendation, CLI, Web and MCP paths; inspected the relevant tests, documentation, approved mockup and all 14 corrected `fx-*` screenshots. I also inspected installed faster-whisper window collection/detection and Hugging Face snapshot-loading code.

Per the brief, I ran no tests, builds, servers, installs, downloads or real transcription. The supplied 862-pass result and Mac timings remain attributed lead evidence. Commands not repeated include:

```sh
cd ~/labs/projects/anyscribe-wt/local-first
.venv/bin/pytest -q
.venv/bin/ruff check src tests
.venv/bin/python scripts/check-docs.py
```

```sh
cd ~/labs/projects/anyscribe-wt/local-first/ui
npx tsc -b
npm run lint
npm run build
```

The browser reproduction would start with:

```sh
HOME=/tmp/anyscribe-r2-review/home HF_HOME=/tmp/anyscribe-r2-review/hf ~/labs/projects/anyscribe-wt/local-first/.venv/bin/anyscribe ui --port 8493 --no-open --local-only
```

Real audio checks additionally require the neutral fixtures whose actual locations are masked in `target.md`. I did not invent their paths or treat the controlled probes as substitutes for those runs.~~~~~

## report-opus-r2.md (round 2)

Absolute home-folder paths rewritten as ~ paths.

~~~~~
FIT REVIEW, round 2. Target: feat/local-first-parakeet @ 8c5d10d, diff b2bafa7..8c5d10d. Read-only. I wrote no files and ran no tests, builds or servers.

## 1. Verdict

**CONDITIONAL on R2F1 and R2F2.** Both are small copy or behaviour changes, not rework.

The round-1 fit problems are fixed or mostly fixed. The headline one is gone: a key-free user no longer sees an API-key warning after the wizard. The fixer proved it with a browser walk, including a failing run with the fix removed, and I traced the code (App.tsx key bump, TranscribePage `qualityPicked`).

Help me choose now explains why in plain words. English gets "as accurate as Turbo on English, about 4 times faster on our test desktop". Hindi gets "most accurate on Hindi in our test" plus the reason to set the language. "Something else" has its own sentence. It also states the download sizes and shows what it selected. The screens match the approved mockup closely, and they now carry the benchmark caption.

Two things remain that the owner would object to:
- **R2F1:** in Settings, clicking an answer to the language question now switches an existing user's default model or starts a download of up to 2.3 GB.
- **R2F2:** the Hindi advice tells every "Indian language" user to set their language to Hindi, which is wrong for a Tamil or Bengali speaker.

## 2. Round-1 F findings: status

| Id | Status | Evidence |
|---|---|---|
| F1 stale quality / API-key warning | FIXED | Traced `ui/src/App.tsx` (TranscribePage `key={configVersion}`, bumped on wizard close) and `TranscribePage.tsx` (quality sent only when picked; submit blocked until config loads). Proof shows the mutant reproducing the WARNING and the fix removing it. |
| F2 pre-select | FIXED in wizard and setup modal; over-applied in Settings | `fx-wizard-2-mix-1440.png` shows Parakeet checked right after answering, with no "Use this" button. In Settings the same change now commits a model change or a download. See R2F1. |
| F3 hidden second download | FIXED | The suggestion ends with "Downloads 670 MB + 1.6 GB, plus the 75 MB language check." The button names both models and 2.3 GB. All set and the modal list Turbo with live status. Leftover nit R2F5. |
| F4 mid-recording switches | FIXED | Three-window check. The wording "start, middle and end of each recording" is used in CHANGELOG, picker, recommendation and docs; "never writes gibberish" is gone. The mix advice adds the Hinglish sentence. Proof shows a real 35 s English plus Hindi clip routed to Turbo. |
| F5 reasons explain why | FIXED, with one new gap | "Something else" has its own branch. The English sentence is clear. Memory is cited only when it changed the pick. "Set my language to Hindi" exists on the Web (a button) and in the CLI (yes/no). The switch note ends "To skip the check, set your language to <Language> in Settings." New gap: R2F2. |
| F6 card numbers unqualified | FIXED on screens; docs leftover | Caption under the cards in Settings, the wizard, the modal and the CLI. "on our test desktop" in the reasons and the first-run line. The docs still say "typical": R2F4. |
| F7 first-run line missing | FIXED | Visible in `fx-wizard-1-choice-1440.png`; now reads the static `/api/local/registry`. |
| F8 getting-started cloud-first | FIXED | "What you need" leads with "On this computer (recommended)". |
| F9 nits | PARTLY | Fixed: step labels ("Step 1", then "Step 2 of 3"), display names in All set, the result card and the CLI, one size per card, visible Reinstall/Delete labels, and a not-downloaded card saying "Downloading; becomes your default when done". Still left: Settings "Model parakeet-v3 · change it on the local card below" and the "What runs by default" rows show raw ids (the fixer named this himself). |
| F10 repo hygiene | PARTLY | Screenshots are out of the repo and target.md is masked. But see R2F6: two tracked files still hold the scratch path. `mockup.html` (tracked) still says "your desktop (i5-10600K)" and "ElevenLabs transcripts already in your vault". The lead left that as owner's call. |

## 3. New findings, most severe first

**R2F1. should-fix. CONFIRMED (code trace).** This touches must-never 3 ("an existing user's model changes without their choice").
- **Where:**
  - `ui/src/components/LocalModelPicker.tsx:305`: `if (r.primary) onUse(r); // answering applies the suggestion`
  - `ui/src/pages/SettingsPage.tsx:194-214`: `handleRecommendation`, then `chooseLocalModel`, then `handleSave({local_model})` or `handlePull`, then a pull of every `also` model.
- **Scenario (the lens's own job):** an existing Whisper Turbo user upgrades, opens Settings and clicks Help me choose. They click "A mix (e.g. English and Hindi)" just to see the advice.
  - With nothing else downloaded, Parakeet v3 (670 MB) and Whisper Tiny start downloading at once, and Parakeet is set to become the default when done.
  - If Parakeet is already on disk, the default flips immediately.
  - Clicking through the other answers to compare fires more downloads and moves the pending default each time.
- **Why it happens:** in the wizard and modal, "selected" means nothing until the big setup button. In Settings, selecting a card is the commit, so the round-1 F2 fix turned "pre-select" into "switch and download". The owner's market includes metered connections, and a surprise 2.3 GB download from a click labelled with a language is exactly what he would object to.
- **Fix (Settings only; keep the wizard and modal as they are):**
  - Answering highlights the suggested card(s) and adds a "Suggested" label.
  - Show one button that commits: "Use Parakeet v3 + Whisper Large v3 Turbo (downloads 2.3 GB)", or "Use Whisper Large v3 Turbo (already downloaded)".
  - Change the header from "Selected:" to "Suggested:" until that button is clicked.
- **Test:** in Settings, answer "English" with Parakeet not on disk. Assert `/api/config` `local_model` is unchanged and the pull queue is empty until the button is clicked.

**R2F2. should-fix. CONFIRMED (code).** The Hindi advice is given to every "Hindi or another Indian language" answer.
- **Where:**
  - `src/anyscribe/core/local_recommend.py:172-176`: the reason reads "Set your language to Hindi: Turbo is about 3 times more accurate…".
  - The same file sets `set_language: "hi"` for every `indian` answer.
  - `src/anyscribe/cli/onboard.py:272`: the CLI asks "Set your language to Hindi?".
  - The Web button "Set my language to Hindi" in `LocalModelPicker.tsx`.
- **Scenario 1:** a Tamil or Bengali speaker answers "Hindi or another Indian language". They are told, as an instruction, to set their language to Hindi. Following it forces Whisper to treat Tamil audio as Hindi.
- **Scenario 2:** a Hindi speaker who also has English recordings is not told that `language: hi` then applies to every file, English included, and switches off the language check.
- **Fix (copy only):**
  - Reason: "If your audio is Hindi, set your language to Hindi: Turbo is about 3 times more accurate on Hindi when it is told the language. Every recording is then treated as Hindi."
  - Button: "My audio is Hindi: set language to Hindi".
  - CLI: "Is most of your audio Hindi? Setting the language to Hindi makes Turbo about 3 times more accurate on it."

**R2F3. should-fix. CONFIRMED (code trace). Owner's call on scope.** A key-free person who skips onboarding still meets two API-key messages and no hint of the free option.
- **Where:**
  - `src/anyscribe/config/settings.py:38,41`: the defaults are `provider: openai`, `quality: balanced`.
  - `src/anyscribe/core/resolve.py:79-83`: produces the WARNING line.
  - `src/anyscribe/providers/openai.py:41-42`: "OPENAI_API_KEY not set. Run 'anyscribe onboard'…".
- **Scenario:**
  - Someone clicks "Skip for now" in the wizard, or runs `pip install anyscribe` and then `anyscribe transcribe <url>` without onboarding.
  - They get "WARNING: quality 'balanced' wants deepgram but no DEEPGRAM_API_KEY is set, using openai instead", then a failure about OPENAI_API_KEY.
  - `fx-settings-restart-banner-1440.png` shows the same WARNING in Settings' "Next run" box on a key-free throwaway HOME.
- **Where this sits:** not the local path, so must-never 1 holds as worded. But the owner's ask was "nobody has to worry about API keys", and the first thing this user reads is about two keys. The spec never addressed the un-configured default.
- **Fix:** smallest safe one: when no cloud key is set, add one line to that error and warning: "Or transcribe free on this computer, no key needed: `anyscribe local setup --model parakeet-v3` (or Settings, then local)." Changing the dataclass default would only affect people with no config file, since saved configs write every field. But it would also catch env-key users without a config, so I would not do that in this PR.

**R2F4. nit. CONFIRMED.** The docs still generalise one machine as "typical".
- **Where:**
  - `CHANGELOG.md:21` ("on a typical 6-core desktop")
  - `docs/user/getting-started.md:36` and `:108` ("a typical desktop")
  - `docs/user/providers.md:410`
  - `docs/user/troubleshooting.md:414`
- **Problem:** the screens now say "our test desktop … your computer may be faster or slower". The lead's own Mac does Parakeet at about 2.5 min per hour once the CPU fix is in.
- **Fix:** replace "a typical" with "our".

**R2F5. nit. CONFIRMED (code + screenshot).** The All set and modal "finished" text does not follow the status beside it.
- **Where:** `OnboardingWizard.tsx:882-886` and `LocalSetupModal.tsx:178-181`.
- **Problem:** `fx-wizard-4-allset-ready-1440.png` shows "✓ ready" next to "…works once it finishes downloading. You can start transcribing now; the download carries on." After a failure it still says the same.
- **Fix:** render that sentence only while the status is downloading or waiting. On failure, say "Hindi and other languages won't work until you download it in Settings."

**R2F6. nit. CONFIRMED.** Tracked files still carry the lead's scratch path, including the OS username.
- **Where:** `docs/reviews/2026-11-19-local-first-parakeet/findings.md` and `report-opus-r1.md`. Both quote "`<lead scratch folder>/...`" inside round-1 F10's own text; `git ls-files | xargs grep -l tmp/claude-1000` finds both.
- **Fix:** mask it the way target.md was masked, before the squash and first push.

**R2F7. nit. CONFIRMED (code).** The restart banner assumes a terminal.
- **Where:** `ui/src/components/LocalSetupNotes.tsx:18-22`, which says "in the terminal where `anyscribe ui` runs, press Ctrl+C".
- **Problem:** the one-line installer's default is desktop mode: a tray or launchd service started at login, with no terminal. The people most likely to hit this banner are existing users upgrading from v0.18.3 with PyAV 19, many of them in desktop mode.
- **Fix:** add "Using the app icon? Quit anyscribe from its menu-bar or tray icon, then open it again."

**R2F8. nit. CONFIRMED.** A key-free local user's Settings page leads with three amber "needs API key" markers in "What runs by default" (`fx-settings-2-pending-1440.png`, `fx-settings-3-hindi-1440.png`).
- **Why it matters:** this is informational, and it predates this PR. But it is the most prominent thing on the page for the exact user this build serves.
- **Fix:** when the active tier is local or custom-local, use muted wording: "add a key to use".

## 4. Answers to the brief

- **Is this the job he asked for, and the simplest instrument?** Yes.
  - It delivers the ask's three parts: keyless local by default, Spokenly-style cards, and guidance that explains why.
  - It is not gold-plated. The extra surfaces (restart banner, incomplete-download state) each answer a real failure that was found.
  - The one place it got less simple than intended is R2F1, where one rule was applied to three surfaces with different commit semantics.
- **Does "help me choose" explain why?** Mostly yes, now.
  - Every answer opens by citing what the person said and gives a concrete comparison: "as accurate as Turbo on English, about 4 times faster on our test desktop"; "most accurate on Hindi in our test". It ends with sizes.
  - The mix answer explains what happens (two models, the check, the Hinglish caveat). It does not say why Parakeet is the main model rather than Turbo. One clause would do it: "Parakeet is the main one because it is about 4 times faster on English."
  - The only wrong "why" is R2F2.
- **Card numbers (lead evidence 3):** now qualified on every screen by the caption. Only the docs over-claim (R2F4).
- **Lead evidence 2 (the WARNING):** resolved for the wizard path (F1). It is still reachable for a key-free user who skipped onboarding (R2F3).

## 5. Pending owner checks

- **The Mac re-measure.** Fix plan item 3 says the lead would re-measure with the CPU provider forced. proof.md says "Mac timing not re-measured here (lead does it)", and I saw no Mac numbers after the fix. Until that run, "about 10 min per hour" and "4 times faster" are unverified on his own machine.
- **R2F3 scope:** should a key-free person who skips the wizard get a pointer to local setup in this PR?
- **R2F1 behaviour:** in Settings, should answering only suggest (my recommendation), or switch?
- **F10 leftovers:** does `mockup.html` with "your vault" and "i5-10600K" stay in the public repo?

## 6. What I could not check, and what I inspected

**Could not check:**
- No browser walk. To settle R2F1: run `anyscribe ui --port <spare> --no-open --local-only` on a throwaway HOME with only Turbo cached. Open Settings, click Help me choose, click "English", then `GET /api/config` (local_model) and `GET /api/local/status` (queue).
- The 390 px wizard screenshots are full-page captures of a fixed modal over Settings, so I could not judge the wizard's own scroll at 390 px from them.
- I did not drive the interactive CLI onboarding; I read the new strings in the diff of `src/anyscribe/cli/onboard.py`.

**Inspected:**
- **Brief and packet:** brief-r2-fit.md, ask.md, spec.md, target.md, lens.md, declined.md, findings.md (my round-1 report), review-log.md, fix-plan-r1.md, proof.md (the round-1 fixes section) and mockup.html (text).
- **Screenshots:** every fx-*.png (wizard 1-4 at 1440, Hindi wizard and All set at 390, Settings partial/pending/Hindi/390/restart banner, modal finished, both result cards).
- **Code:**
  - `core/local_recommend.py` (all)
  - `LocalModelPicker.tsx` (cards, explainer, HelpMeChoose)
  - `SettingsPage.tsx` (choose and recommendation handlers)
  - `OnboardingWizard.tsx` (All set)
  - `LocalSetupModal.tsx`, `LocalSetupNotes.tsx`
  - App/TranscribePage diff
  - `core/resolve.py`, `config/settings.py`, `providers/local.py` (load and error paths)
  - `mcp/server.py` (doctor, set_config)
  - `core/config_set.py`, `web/routes/system.py`
- **Docs and grep:** CHANGELOG Unreleased, README diff, getting-started, skill SKILL.md lines; a grep of the diff for owner data.

Skipped: engine and guard internals, install paths and test validity (the correctness reviewer's lane). Advice outside this PR's scope: MCP has no tool to install engines or download a model. On main it had none either, so an MCP-only agent can recommend but not set up local transcription. Worth a backlog line.
~~~~~

## report-gpt-6.1-sol-r3.md (round 3)

Absolute home-folder paths rewritten as ~ paths.

~~~~~
**NOT YET.** The round-2 fixes are present, but three confirmed concurrency defects remain. A background save can undo a provider choice, `choose()` can fail after successfully changing the default, and an older setup can overwrite a later model choice.

Reviewed `feat/local-first-parakeet` at `5551230740a24d796067781453783217c9402f11`, against `8c5d10d`. The worktree remained clean. Reproductions below used source functions with in-memory substitutes for persistence and downloads, with deterministic interleavings. No tests, servers, downloads, installs or builds ran.

All relative paths below are under `~/labs/projects/anyscribe-wt/local-first/`.

**Round-2 findings**

| ID | Status | Evidence |
|---|---|---|
| R2C1 | FIXED | `providers/local.py:231-267` separates confident uncovered detections from uncertainty. Both requested weak-detection inputs produced the specified results with and without Whisper. |
| R2C2 | FIXED | `LocalModelPicker.tsx:337-348` rejects replies superseded by another answer or card click. Browser reply reordering was not repeated. |
| R2C3 | FIXED | `runnable()` includes Tiny and VAD; `config_set.py:119-120` guards changes. A simulated helper failure preserved Turbo and recorded the failure. |
| R2C4 | FIXED | The wizard’s separate Next button is removed. Its setup request sends `also`; `web/routes/local.py:196-198` queues extras on the server. |
| R2C5 | FIXED | Current null recommendations reach the parent, clear selection, and disable setup through `!selected`. |
| R2C6 | FIXED | Public records mask the previously identified scratch paths. Remaining quoted grep prefixes are accepted by the lead; not reopened. |
| R2C7 | FIXED | `cli/onboard.py:156-159` prints the restart notice in human headless output. |
| R2F1 | FIXED | Settings answers only update suggestions. Choosing a card or clicking Use invokes `chooseLocal`. |
| R2F2 | FIXED | Hindi advice is conditional, explains its effect on every recording, and the Web button explicitly identifies Hindi audio. |
| R2F3 | FIXED | `providers/base.py:16-24` supplies the local option when no cloud key exists; all six provider errors and the tier warning append it. |
| R2F4 | FIXED | The changed user documentation and CHANGELOG identify “our test desktop” rather than a typical computer. |
| R2F5 | FIXED | `LocalSetupNotes.tsx:43-47,99-104` distinguishes pending, ready and failed extras, with corresponding explanation text. |
| R2F6 | FIXED | Same evidence and settled exception as R2C6. |
| R2F7 | FIXED | `LocalSetupNotes.tsx:21-23` includes quitting and reopening through the tray or menu-bar icon. |
| R2F8 | FIXED | `SettingsPage.tsx:301-303` and `QualityChoice` use muted “add a key to use” text for local users. |

**Diagnosis’s four extra cases**

| Case | Status | Evidence |
|---|---|---|
| Pending choice lost on page reload | FIXED | Pending state resides on `app.state.download_queue` and is returned by `/api/local/status`; page reload does not recreate it. Server restart still loses it by design. |
| Extras lost when the wizard closes | FIXED | Extras are arguments to `_background_setup`, which queues them after successful setup without browser participation. |
| PUT with helpers ready but weights missing | FIXED | The shared `set_value` guard refuses a changed default unless `runnable()` succeeds. |
| Headless onboarding saves the default before setup | FIXED | For provider `local`, `onboard_headless.py:213-225` leaves the model unchanged; successful `run_setup` performs the switch. |

**New defects and integration failures, most severe first**

1. **R3C1 | blocker | CONFIRMED: Background model saves can erase a foreground provider or quality change.**

   **Where:** [config_set.py:96](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/core/config_set.py:96), [models.py:112](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/web/routes/models.py:112), `web/routes/config.py:103-135`.

   `set_value()` reads the whole configuration, changes one field, then saves the whole configuration without protecting that complete operation. The queue lock protects queue users, but foreground configuration writes do not acquire it. Atomic file replacement prevents a torn file; it does not prevent an old configuration from overwriting newer settings.

   Reproduced this ordering in memory:

   ```text
   Background model setter reads: openai / balanced / large-v3-turbo
   Foreground provider save commits: local / custom / large-v3-turbo
   Background model save finishes: openai / balanced / small
   ```

   Both saves report success. The person’s explicit local choice disappears, and the next run can return to a cloud provider. Other settings can be lost similarly.

   **Fix:** Protect the complete configuration read, modification and save across all participating writers. Multi-field Web updates and their rollback must participate in the same protection. Add a coordinated concurrency check asserting the surviving provider, quality and model identities.

2. **R3C2 | should-fix | CONFIRMED: `choose()` can raise after its choice has already succeeded.**

   **Where:** [models.py:134](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/web/routes/models.py:134), particularly line 137.

   The function stores pending state, starts the worker, then constructs its response from the current shared pending state without holding the lock.

   The worker can finish and set pending to `None` before that response is constructed. A second choice of an already-runnable model can also clear it.

   Both deterministic interleavings reproduced:

   ```text
   Fast completion:
     saved default = small
     pending = None
     TypeError: 'NoneType' object is not iterable

   Second choice completes during first enqueue:
     saved default = tiny
     pending = None
     TypeError: 'NoneType' object is not iterable
   ```

   The exception propagates through the endpoint. Settings reports failure despite a successful choice and skips its normal configuration/status refresh. A concurrently completing setup of the same repository makes a fast queue completion particularly relevant.

   **Fix:** Construct the response from a stable, request-owned snapshot captured under the lock. Do not assume shared pending state still exists after starting work. Verify completion-before-response and overlapping choose calls.

3. **R3C3 | should-fix | CONFIRMED: An older setup can overwrite a later successful model choice.**

   **Where:** [local_setup.py:399](~/labs/projects/anyscribe-wt/local-first/src/anyscribe/core/local_setup.py:399), `web/routes/local.py:180`, `web/routes/models.py:120-137`.

   Setup and choose remain independent owners of the default. Setup always writes its requested model after downloading, without checking whether a newer choice superseded it.

   Concrete scenario: start Parakeet setup, then choose an already-runnable Small through another tab while setup continues. Small becomes the default successfully. When the older setup finishes, Parakeet replaces it.

   Reproduced with the actual `run_setup()` and `choose()` functions, replacing only installation, downloads and persistence:

   ```text
   Later choose: status switched, default small
   Older setup completion: status set_up, default parakeet-v3
   ```

   Serializing individual configuration writes alone will not fix this. The writes are individually valid, but the older operation no longer owns the person’s latest intent.

   **Fix:** Coordinate setup and choose activation through one ordering mechanism, or reject conflicting operations explicitly. Verify that completing an older setup cannot replace a later accepted choice.

**Why the supplied checks miss these**

The choose-test fixture disables automatic worker startup at [test_local_choose.py:52](~/labs/projects/anyscribe-wt/local-first/tests/test_local_choose.py:52), then drains the queue after requests return. That proves sequential state transitions but cannot expose completion before response construction. The inspected checks also do not interleave a foreground configuration save with worker activation, or setup activation with a newer choose call.

The reported **894 passed, 4 skipped** remains lead evidence. It does not establish thread safety.

**Migration and integration risks**

- **Existing non-runnable defaults remain unchanged intentionally.** Re-saving the current `base` succeeds even when it is not runnable; I reproduced that approved exception. Upgrading therefore does not establish that the saved default works.
- **Scripts must pull before setting a different default.** `config set local_model X` now refuses an unready change. CHANGELOG and configuration guidance disclose this behavior change.
- **Page reload and server restart differ.** Reload preserves pending intent; process restart loses it. Cached files may survive, but the pending switch is not recovered.
- **Concurrent Hugging Face downloads:** the installed downloader uses per-blob locks and atomic placement. That supports cache safety, but I did not perform overlapping downloads. Those locks do not coordinate application-level default choices.
- **Readiness has limits.** `runnable()` checks imports, files and Parakeet helpers. It does not prove successful decoding or engine loading. The existing PyAV 19 repair still relies on running setup and restarting when requested.
- **Preinstalled Parakeet plus “A mix”:** the inspected wizard now has one forward path and sends Turbo as an extra. I did not repeat the browser walk.

**Pending owner checks**

Representative Hindi/Hinglish transcript quality and whether the Mac experience feels acceptable remain owner acceptance checks. None of the three defects above requires owner action to diagnose or fix.

**Inspection and limits**

I read the brief, delta, every named packet file and declined list; traced the changed provider, readiness, setup, configuration, CLI, MCP, Web and UI paths; inspected the affected tests and documentation; and inspected installed Hugging Face locking code. The built JavaScript contains the new choose endpoint, pending/default fields and corrected Hindi button text.

In-memory probes confirmed the requested weak-language routing, weights-only readiness rejection, helper-failure preservation, unchanged-default exception, and the three failures above. They were not real download, browser or transcription runs.

The brief prohibited repeating these checks:

```sh
cd ~/labs/projects/anyscribe-wt/local-first
.venv/bin/pytest -q
.venv/bin/ruff check src tests
.venv/bin/python scripts/check-docs.py
```

```sh
cd ~/labs/projects/anyscribe-wt/local-first/ui
npx tsc -b
npm run lint
npm run build
```

Real onboarding and browser checks were also not run:

```sh
HOME=/tmp/anyscribe-r3-review/home HF_HOME=/tmp/anyscribe-r3-review/hf \
  ~/labs/projects/anyscribe-wt/local-first/.venv/bin/anyscribe \
  onboard --yes --provider local --local-model parakeet-v3 --json

HOME=/tmp/anyscribe-r3-review/home HF_HOME=/tmp/anyscribe-r3-review/hf \
  ~/labs/projects/anyscribe-wt/local-first/.venv/bin/anyscribe \
  ui --port 8497 --no-open --local-only
```

No real-audio or cross-platform run was repeated. The neutral audio locations are masked in `target.md`; I cannot supply their exact transcription commands without inventing paths.~~~~~

## report-opus-r3.md (round 3)

Absolute home-folder paths rewritten as ~ paths.

~~~~~
FIT REVIEW, round 3 (final). Target: feat/local-first-parakeet @ 5551230, diff b2bafa7..5551230. Read-only. I wrote no files and ran no tests, builds or servers.

## 1. Verdict

**CONDITIONAL on R3F1**, a copy and text-display fix of a few lines.

Every round-2 fit finding is fixed except R2F3, which is only partly fixed. Settings and the wizard now read right against the approved mockup:
- In Settings, Help me choose only suggests. It shows a "Suggested:" header, a dashed "Suggested" card and one honest button: "Use Parakeet v3 + Whisper Large v3 Turbo (downloads 670 MB)".
- The wizard still pre-selects, which is correct there because nothing is saved until its setup button.
- All set shows the right text for downloading, ready and failed.
- A local user's tier rows are muted ("add a key to use").
- The Hindi advice is now conditional.

What is left: the free-option hint added for R2F3 sends a key-free user round in a circle. The command it names does not switch them to local transcription. On the Web, the hint also renders as one run-on line. In fairness, the command came from my own round-2 recommendation, and it was wrong.

## 2. Round-2 findings: status

| Id | Status | Evidence |
|---|---|---|
| R2F1 Settings answer switched the model or downloaded | FIXED | `LocalModelPicker.tsx:136-142`: with `onUseSuggestion` set, an answer only records the suggestion. `:443-455`: only the Use button calls choose. `r3-w5-settings-suggested-1440.png` and `r3-w2-settings-reorder-1440.png` show the "Suggested:" header, the dashed Suggested card and the Turbo card still checked. Proof records no writes after four answers and config unchanged. |
| R2F2 Hindi advice for every Indian language | FIXED | `local_recommend.py:175` says "If your audio is Hindi, …"; the button reads "My audio is Hindi: set language to Hindi" (`LocalModelPicker.tsx:470`); the CLI asks "Is most of your audio Hindi? … (Every recording will then be treated as Hindi.)" (`cli/onboard.py:276`). |
| R2F3 key-free user who skips onboarding | PARTLY | The hint exists and shows in Settings' "Next run" box (`r3-w4-modal-nofit-1440.png`), but see R3F1. |
| R2F4 "typical" desktop | FIXED | `grep typical` over CHANGELOG, README, docs/user, the skill, ui/src, core and cli finds no hits. |
| R2F5 All set text vs status | FIXED | `r3-w1-allset-downloading` shows the "works once it finishes downloading" note; `r3-w1-allset-ready` drops it; `r3-w1f-allset-failed` says "Hindi and other languages won't work until you download Whisper Large v3 Turbo in Settings." |
| R2F6 scratch path in tracked files | FIXED in substance | Three review records (`findings.md:536`, `proof.md:435`, `report-opus-r2.md:90`) still quote the grep command `tmp/claude-1000`: a default user id, no session id, nothing personal. The lead knows; not raised again. |
| R2F7 restart banner assumed a terminal | FIXED (code only) | `LocalSetupNotes.tsx:21` adds "Using the app icon? …". Not walked. |
| R2F8 amber "needs API key" for a local user | FIXED | `r3-w5-settings-rows-1440.png` shows the muted "add a key to use". |
| Also fixed | | The F9 leftover: display names now show in the Model line and the tier rows. The mix advice now says why Parakeet v3 is the main model. |

## 3. New findings, most severe first

**R3F1. should-fix. CONFIRMED (code trace + screenshot).** The free-option hint names a command that does not finish the job, and on the Web it is garbled.

- **Where:**
  - `src/anyscribe/providers/base.py:10-13` (the hint text)
  - `src/anyscribe/core/local_setup.py` (`run_setup` docstring: "Does NOT change settings.provider")
  - `src/anyscribe/core/resolve.py:78-83` (no fallback to local when no key is set)
  - `ui/src/pages/SettingsPage.tsx:1279-1287` and `ui/src/pages/TranscribePage.tsx:384` (plain `<p>`, so the hint's leading `\n` collapses)
- **Scenario (CLI):**
  - A key-free person runs `anyscribe transcribe <url>` without onboarding. They read the warning and the error, both ending "Or transcribe free on this computer, no key needed: `anyscribe local setup --model parakeet-v3`". The hint is printed twice per run.
  - They run that command and see "Local transcription ready. Default model: Parakeet v3."
  - They run `anyscribe transcribe <url>` again. The provider is still `openai` and the quality is still `balanced` (the dataclass defaults; setup never touches them). They get the same warning, the same error and the same hint. It is a loop.
  - The same happens on the Web: the Settings setup window also leaves the provider alone (`SettingsPage.tsx:907-913` only refreshes), so the Next run box keeps showing the warning.
- **Web rendering:** `r3-w4-modal-nofit-1440.png` shows the line as one run-on sentence: "…using openai instead Or transcribe free on this computer, no key needed: `anyscribe local setup --model parakeet-v3` (or Settings, then Local transcription)."
  - The backticks show as literal characters.
  - It tells a person who is already in Settings to go to "Settings, then Local transcription", but no section there has that name; the card is labelled "local".
  - The Transcribe page error box has the same problem, so the hint fails exactly the person R2F3 was meant to help.
- **Fix (smallest):**
  1. Point the hint at the path that does switch the provider: "Or transcribe free on this computer, no key needed: run `anyscribe onboard` and choose On this computer (in the dashboard: Settings, then Run setup wizard)." Both wizards set `provider: local`.
  2. Add `whitespace-pre-line` to the two `<p>` elements.
  3. Optionally, when the provider is not local, `anyscribe local setup` could end with: "To use it for every transcript: `anyscribe config set quality free`."
- **Test:** on an empty HOME, the hint text contains "onboard", and a test asserts the next plan's provider after the step it names.

**R3F2. nit. CONFIRMED (code + screenshots).** The Settings "Tip" gives a Web user a terminal command, and it stays up after it no longer applies.

- **Where:** `core/local_recommend.py:287-300` and `SettingsPage.tsx:1100-1104`.
- **Problem:** "Tip: Parakeet v3 is rated 5/5 … Try it: anyscribe local setup --model parakeet-v3" sits directly above the Parakeet card, which does this in one click.
  - It stays while Parakeet is already "Downloading; becomes your default when done" (`r3-w5-settings-pending-after-reload-1440.png`).
  - It stays after a failed switch (`r3-w3-helper-failed-1440.png`).
- **Fix:** hide it while `pending_default` is set. On the Web, end it with "Try it: click the Parakeet v3 card below." Keep the command for the CLI and MCP.

**R3F3. nit. CONFIRMED (code + proof).** Settings offers "Use" for the model already in use.

- **Where:** `LocalModelPicker.tsx:443-455`.
- **Problem:** a Turbo user who answers "Hindi" or "Something else" gets "Use Whisper Large v3 Turbo (already downloaded)" (the proof records it twice). Clicking it changes nothing.
- **Fix:** when the primary is the current default and every extra is ready, show "This is already your default" instead of the button.

## 4. Answers to the brief

- **Is this the job he asked for, and the simplest instrument?** Yes.
  - It delivers keyless local by default, Spokenly-style cards, and a guide that explains why.
  - Round 3 made it simpler: the server now owns "choose", and three browser copies of the pending/extras logic were deleted.
  - Nothing is gold-plated.
- **Does it read right to its reader?** Yes on every screen I checked, apart from R3F1's hint and the two nits.
  - The mix explanation is clear.
  - Download sizes match the button: 670 MB when Turbo is already present, 1.6 GB in the wizard.
  - The no-fit state says why and what to do ("Free up space, then ask again").
  - The 390 px Settings layout holds.
- **Card numbers (lead evidence 3):** every card set carries "measured on English audio on a 6-core desktop processor … your computer may be faster or slower". That is honest.
- **The WARNING (lead evidence 2):** unreachable on the wizard and onboard paths. A user who skips setup still sees it; that is R3F1.

## 5. Pending owner checks

- **Mac re-measure with the CPU provider forced** (the fix is in, at `local.py:125-127`). The proof still says the lead does it, and I saw no Mac numbers after the fix.
- **mockup.html in the public repo:** it says "your desktop (i5-10600K)" and "transcripts already in your vault". Keep it or mask it? Carried over from round 2.
- **Should a key-free person who skips the wizard default to local?** A bigger change than this PR. My advice: not now; fix the hint (R3F1).

## 6. What I could not check, and what I inspected

**Could not check:**
- No browser or CLI walk. To settle R3F1 on a throwaway HOME with no keys, run `anyscribe local setup --model parakeet-v3 --yes`, then `anyscribe transcribe <short English file>`. I expect the deepgram WARNING plus the OPENAI_API_KEY error, with the hint printed twice.
- `r3-w4-wizard-nofit-1440.png` shows the Parakeet card with an amber border but an empty radio. The code uses one `checked` value for both (`LocalModelPicker.tsx:160-170`), so this is probably a screenshot taken mid colour transition. Re-taking it after 300 ms would settle it.
- R2F7 not walked; it needs a PyAV 19 install.

**Inspected:**
- **Packet:** brief-r3-fit.md, ask.md, lens.md, declined.md, spec.md section 5, diagnosis-r2.md, fix-plan-r2.md, review-log.md, findings.md (round-2 fit report), proof.md (round-2 fixes), mockup.html (text).
- **Screenshots:**
  - `r3-w5-settings-suggested`, `r3-w5-settings-rows`, `r3-w5-settings-pending-after-reload`
  - `r3-w1-mix`, `r3-w1-allset-downloading`, `r3-w1f-allset-failed`
  - `r3-w3-helper-failed`
  - `r3-w4-wizard-nofit`, `r3-w4-modal-nofit`
  - `r3-w9-settings-suggested-390`
  - `r3-w2-settings-reorder`
- **Code:** `LocalModelPicker.tsx` (the cards, HelpMeChoose, the language-check box), `SettingsPage.tsx` (the local card, the notes box, NoteText, the modal hook-up), `providers/base.py` (local_hint), `core/resolve.py`, `config/settings.py` (defaults), `core/local_setup.py`, `cli/local_cmd.py` (setup), `cli/onboard.py` (the Hindi prompt, the where-to-transcribe choice), `core/local_recommend.py` (the reasons, parakeet_suggestion), `LocalSetupNotes.tsx`, `local.py` (CPU provider), the CHANGELOG Unreleased section.
- **Greps:** "typical", the scratch path and i5-10600K across tracked files.

Skipped: engine and guard internals, install paths and test validity (the correctness reviewer's lane).
~~~~~

## report-opus-correctness-r4.md (round 4)

Absolute home-folder paths rewritten as ~ paths.

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

## report-opus-fit-r4.md (round 4)

Absolute home-folder paths rewritten as ~ paths.

~~~~~
FIT REVIEW, round 4 (final). Target: feat/local-first-parakeet @ 90bc0cf. Read-only: I wrote no files and ran no tests, builds or servers.

## 1. Verdict

**CONDITIONAL on R4F1.** R4F1 is a one-line copy change in the Settings setup window, small enough for the lead to make without another fix round.

- **R3F1: FIXED.** The hint now names a step that really switches transcription to this computer, prints once per run, and shows on its own lines on the web.
- **R3F2: FIXED.**
- **R3F3: FIXED.**
- **New problem:** the fix for R3F1 added a contradictory sentence to the Settings setup window. That is R4F1.

## 2. Status of the round-3 fit findings

| Id | Status | Evidence |
|---|---|---|
| R3F1 hint loops and renders as one run-on line | FIXED | **Code:** `providers/base.py:12-15` now says "run `anyscribe onboard` and choose On this computer (in the dashboard: Settings, then Run setup wizard)". The pre-flight error carries the hint (`core/preflight.py:64`). The CLI drops the duplicate copy (`cli/transcribe.py:124-127`, `cli/batch.py:208-212`).<br>**Screens:** `r4-f1-transcribe-error-1440.png` shows the key error, Fix, Or and the hint, each on its own line. `r4-f1-settings-nextrun-1440.png` shows the WARNING and the hint as two lines.<br>**Proof:** the proof's real CLI walk on a fresh home goes onboard, then `→ local (config)`, then the transcript is saved. The hint is not a loop any more. |
| R3F2 tip gives a CLI command on the web and stays while pending | FIXED | **Code:** `local_recommend.py:300-304` adds the web wording. `web/routes/local.py:99-100` drops the tip while a default is pending (downloading or failed).<br>**Screens:** `r4-f23-suggest-hindi-1440.png` shows "Try it: click the Parakeet v3 card below." `r4-f23-pending-1440.png` has no tip while "Downloading; becomes your default when done" is showing. The CLI and MCP keep the command (`check_status()` defaults to `web=False`; `mcp/server.py:589`). |
| R3F3 Use offered for the current default | FIXED | **Code:** `LocalModelPicker.tsx:447-452`.<br>**Screen:** `r4-f23-suggest-hindi-1440.png` shows "Already downloaded." and a green "This is already your default", with no Use button.<br>**Proof:** the mutant walk shows the extras' readiness is checked. A mix without Turbo downloaded still gets the 1.6 GB Use button. |

## 3. New findings, most severe first

**R4F1. should-fix. CONFIRMED (code + screenshot).** After setup, the Settings setup window says the new model is the default, then says it is not used yet.

- **Where:** `ui/src/components/LocalSetupModal.tsx:144-152`, the text set at `core/local_setup.py:62-65` (`USE_LOCAL_TIP`), and screenshot `r4-f1-modal-result-1440.png`.
- **What the window shows:**
  - "✓ Parakeet v3 is ready and is your default."
  - "To use it for every transcript: `anyscribe config set quality free` (or pick 'free' under What runs by default)."
- **Scenario:**
  1. A key-free person is on Settings. The loudest button on the page is the orange "Set up local transcription" on the local card, not the hint's "Run setup wizard".
  2. They click it, wait for the download, and read "is ready and is your default" with a green tick.
  3. They click Done and go to Transcribe. The proof records the saved settings as `provider openai, quality balanced`, so the run fails with the same missing-key error.
- **Why the second line doesn't help:** it reads as an optional extra, not as "you are not done". On a web screen it also leads with a terminal command, and the backticks show as literal characters.
- **Who it hits:** the reader this PR is for, and exactly the case the hint was added to cover.
- **Fix (copy only):**
  1. When `use_local_tip` is set, change the first line to "… is ready and is your default local model."
  2. On the web, make the tip "anyscribe still uses openai for new transcripts. To use this computer instead, pick 'free' under What runs by default." Drop the CLI command there; keep it for the CLI output, the same split as R3F2.
- **Optional, simpler for him:** a "Use it for every transcript" button that saves quality free. This is a scope call for the lead, not required.

**R4F2. nit. CONFIRMED (code + proof).** The hint says `anyscribe onboard`, but onboard refuses on any home that already has a config file.

- **Where:** `providers/base.py:13` and `cli/onboard.py:92-103, 555-559`. The pre-flight error stacks "Or: anyscribe onboard --force" directly above the hint's "run `anyscribe onboard`" (`r4-f1-transcribe-error-1440.png`).
- **Scenario:**
  1. A person has already run `anyscribe local setup`, or saved anything in Settings, so the config file exists.
  2. They follow the hint.
  3. Onboard prints "Already configured … Pass --force to re-run". The proof's own walk hit exactly this.
- **Why it's only a nit:** onboard's message names the fix, so this costs one extra step, not a loop. But two near-identical commands on adjacent lines read as a puzzle.
- **Fix:** make the hint say `anyscribe onboard --force`, or drop the "Or: anyscribe onboard --force" line from the pre-flight error when the hint follows it.

**R4F3. nit. PLAUSIBLE (screenshot only). Not introduced by the round-3 fixes; same kind of problem as R3F3.**

- **Where:** `LocalModelPicker.tsx:452` (the Use button condition) and screenshot `r4-f23-pending-1440.png`.
- **Problem:** while Parakeet v3 is already "Downloading; becomes your default when done", the earlier English suggestion still offers "Use Parakeet v3 (downloads 670 MB)". Clicking it most likely repeats an action already under way.
- **What would settle it:** click Use in that state and check the download queue gets no second entry.
- **Fix:** treat "primary equals the pending default" the same way as "already your default", and show "Downloading; becomes your default when done" instead of the button.
- **Can wait:** yes, this can wait for a later change.

## 4. Answers to the brief (advice, not findings)

- **Is this the job he asked for, and the simplest instrument?**
  - Yes. Round 4 did not widen scope: copy, two CSS classes, one server-computed tip and one condition.
  - Computing `use_local_tip` on the server (`local_setup.py:352-363`) means the CLI and the web give the same answer.
- **Does it read right to its reader?**
  - Yes on the Transcribe error box, the Next run box, the Parakeet tip and "This is already your default".
  - The exception is R4F1: the setup window is the one screen where a non-developer will believe they are finished when they are not.
- **The WARNING (lead evidence 2):**
  - A key-free person who skips setup still sees it. It now carries a working way out on its own line.
  - It is unreachable after either wizard. After the Settings setup window it remains, which is R4F1.
- **Card numbers (lead evidence 3):** unchanged since round 3, and honestly captioned. The screenshot footer reads "measured on English audio on a 6-core desktop processor without a graphics card. Your computer may be faster or slower."

## 5. Pending owner checks

- **Mac re-measure with the CPU provider forced:** still not recorded in the proof.
- **mockup.html in the public repo:** it says "your desktop (i5-10600K)" and "transcripts already in your vault". Keep it or mask it? Carried over from rounds 2 and 3.
- **R4F1's direction (copy or button):** whether he wants the setup window to offer a one-click "Use it for every transcript" or just say plainly that the default is still the cloud.

## 6. What I could not check, and what I inspected

**Could not check:**
- No browser or CLI walk.
- To settle R4F3, on a local Turbo user's Settings: answer English, click the Parakeet v3 card, then click "Use Parakeet v3 (downloads 670 MB)", then run `curl -s localhost:<port>/api/local/status | python -c "import sys,json;d=json.load(sys.stdin);print(d['pending_default'],[m['size'] for m in d['models'] if m.get('queue_position',-1)>=0])"`. The field names come from `web/routes/local.py:96-110` and the queue field name is my guess.
- To see R4F2: on a throwaway home with no keys, run `anyscribe local setup --model tiny --yes && anyscribe onboard` (the proof already shows the refusal).

**Inspected:**
- **Packet:** brief-r4-fit.md, ask.md, lens.md, declined.md, review-log.md, fix-plan-r3.md, the round-3 fit report in findings.md, and proof.md's "Round 3 fixes".
- **Diff:** `git diff 5551230..90bc0cf` for cli/, core/local_setup.py, core/preflight.py, core/local_recommend.py, providers/base.py, web/routes/local.py and ui/src. Also the `local_hint()` call sites, onboard's refusal on an existing config, the Settings tier rows (selectable, `SettingsPage.tsx:398-412`) and the MCP status block.
- **Screenshots:** `r4-f1-transcribe-error-1440`, `r4-f1-settings-nextrun-1440`, `r4-f1-modal-result-1440`, `r4-f23-suggest-hindi-1440`, `r4-f23-pending-1440`.
- **Not opened:** the other r4-*.png (the old-code and mutant variants); I relied on the proof's description of those.
~~~~~
