Copied from the review run folder; absolute home-folder paths rewritten as ~ paths and the lead's scratch path masked; the byte-exact original stays in ~/.review-runs/2026-11-19-local-first-parakeet/.

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
