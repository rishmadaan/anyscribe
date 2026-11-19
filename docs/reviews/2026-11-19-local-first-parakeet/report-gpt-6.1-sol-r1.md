Copied from the review run folder; absolute home-folder paths rewritten as ~ paths and the lead's scratch path masked; the byte-exact original stays in ~/.review-runs/2026-11-19-local-first-parakeet/.

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
