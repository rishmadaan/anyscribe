Copied from the review run folder; absolute home-folder paths rewritten as ~ paths; the byte-exact original stays in ~/.review-runs/2026-11-19-local-first-parakeet/.

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
