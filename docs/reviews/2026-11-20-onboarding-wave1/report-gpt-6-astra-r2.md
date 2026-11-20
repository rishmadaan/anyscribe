**NOT YET.** Most fixes are sound, but C1 remains incomplete: a failed status request can unlock an active download, while other failure paths leave the wizard locked indefinitely. The new polling handoff also introduces a stale-lock race.

Reviewed `feat/onboarding-wave1` at `248ee2bd80dfafd8aca34f3fa87c7aefea19aaad`, against `8d63221`. CONFIRMED means confirmed by source trace; runtime execution was prohibited. The scope still matches the owner’s approved wave 1.

All source locations below are within `~/labs/projects/anyscribe-wt/wave1/`.

| Finding | Result | Evidence |
|---|---|---|
| C1 | **PARTLY** | `OnboardingWizard.tsx:783` disables the backup checkbox, and normal completion clears the lock. Status failures still defeat the guarantee; see R2C1 and R2C3. |
| C2 | **FIXED** | Lines 668 and 738 adopt `setup_last_model`; line 700 requires the selected model’s `runnable` flag before advancing. Reload and 409 evidence supports both changes. |
| C3 | **FIXED** | Lines 526, 576 and 588 prevent key edits, bypass and Back during checking. The supplied mutation walk demonstrates the original race and restored protection. |
| C4 | **FIXED** | `install.ps1:407` rechecks both binaries after `Install-Anyscribe` changes PATH, before desktop launch and the banner. The recorded mutant prints “ready”; restored code prints “can’t transcribe yet.” |
| C5 | **FIXED** | `TranscriptBody.tsx:18` supports the binding plan’s one level of balanced parentheses. Deeper nesting remains literal text, as documented. |
| F1 | **NOT FIXED, owner decision pending** | Intentionally no code change. The packet still separates merge-time installer/website publication from the later dashboard release. |
| F2 | **DECLINED-OK** | REFUTED and settled in `docs/reviews/declined.md`; not reopened. |
| F3 | **FIXED** | Opened both replacement ffmpeg screenshots and the Sarvam screenshot. The notice is visible; the original blank-panel evidence gap is closed. |
| F4 | **FIXED** | `BACKLOG.md:668` now says “Not checked yet”; line 685 records the Settings-modal follow-up. |
| F5 | **FIXED** | `core/errors.py:111` restricts “is prepaid” to OpenAI/OpenRouter. Other providers receive the agreed wording; docs and mutation evidence match. |
| F6 | **FIXED** | `install.sh:678` describes typing commands later, after the click-the-app instruction. |
| F7 | **FIXED** | `install.sh:674` uses the approved plain “Cmd and Space” wording; recorded box and width checks support it. Native Spotlight discovery remains untested. |
| F8 | **FIXED** | `install.ps1:373` tells non-desktop users to open a new PowerShell window; the fallback instruction remains explained. |
| F9 | **FIXED** | `OnboardingWizard.tsx:514` shows the amber note immediately; line 493 advances Sarvam directly. The recorded walk shows no key-check request. |
| F10 | **FIXED** | `OnboardingWizard.tsx:940` uses plain recovery messages and the matching “Try again” button. Engine/restart branches were inspected, not visually exercised. |

The newly found defects follow. R2C2 is introduced by this delta; R2C1 and R2C3 are remaining failure paths in the lock being repaired.

1. **R2C1 | blocker | CONFIRMED: a successful setup followed by one failed status read unlocks an active download.**

   Where: [OnboardingWizard.tsx:728](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:728), particularly lines 729 and 742–744.

   Concrete sequence: choose a cloud provider, enable local backup, and start downloading. `POST /api/local/setup` succeeds and the server starts its background worker. The immediately following `getLocalStatus()` fails before the first polling tick.

   Both operations share one `try`. Its catch sets `settingUp` and `localRunning` false, treating the status-read failure as proof that setup never started. The polling effect is then removed, and the parent poll also stays off. The checkbox becomes enabled; the customer can untick it, select “Skip, next”, and close the wizard while the server continues downloading. A 409 followed by a failed status read reaches the same unsafe unlock.

   Fix: separate setup-request failure from status-read failure. After an acknowledged start, or a 409, retain an explicit running/unknown state and reconcile with the server. An unsuccessful read must not establish that the download stopped.

2. **R2C2 | should-fix | CONFIRMED: the new handoff can leave the close lock active after setup has finished.**

   Where: [OnboardingWizard.tsx:135](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:135), [line 150](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:150), and [line 663](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:663).

   Concrete sequence: reload near the end of a download. The wizard’s opening request reports `setup_running: true`, sets the close lock, and mounts the local step. The download finishes before that step’s separate status request returns `setup_running: false`.

   The step only handles the true case. Its `settingUp` remains false, so it starts no poll and never clears the parent lock. Meanwhile, the parent explicitly refuses to poll on this step. “Skip is off until the download finishes” therefore remains after completion, with Escape and backdrop disabled.

   Back or another setup cycle can recover, so this is not an unavoidable permanent trap. It is a new stale lock with no automatic reconciliation.

   Fix: process both running and stopped results during the handoff, preferably through one owner of setup status. Verify the ordered response sequence `true`, then `false`, without requiring another click.

3. **R2C3 | should-fix | CONFIRMED: persistent polling failures leave a silent, locked wizard.**

   Where: [OnboardingWizard.tsx:684](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:684) and [line 711](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:711); request handling in [client.ts:23](~/labs/projects/anyscribe-wt/wave1/ui/src/api/client.ts:23).

   Concrete sequence: setup starts and the initial status read succeeds. The server then dies, or subsequent status requests consistently fail. Every polling exception is discarded as “transient”. Back, the checkbox, setup, Skip, Escape and backdrop remain unavailable, with no connection-loss message or recovery action.

   Additionally, status and log retrieval use `Promise.all`. A failing log request discards a successful status response saying setup stopped, unnecessarily preserving the lock. There is no application-level fetch timeout.

   Fix: handle status independently of optional log output, bound requests, and display a connection-lost state with retry/restart guidance. Do not resolve this by blindly unlocking an operation whose state is unknown. Test server loss and log-only failure separately.

The supplied lock tests cover steady running and successful completion. They do not cover these request failures or the `true`-then-`false` mount handoff, so they cannot substantiate the broader claim that the lock always follows server state.

Other requested checks passed by inspection:

- All six cloud providers reach `classify_api_error`; Groq inherits OpenAI’s implementation. HTTP 402 and 429 containing `insufficient_quota` produce non-retried `NoCreditError`. Ordinary 429 remains retryable.
- The renderer still constructs React elements and restricts live links to HTTP(S). The parentheses change introduces no identified script or non-HTTP link path.
- Key checks use fixed provider HTTPS endpoints and do not persist the typed key before Finish.
- Interval effects clear their timers on unmount. Outstanding requests are not cancelled; this is not proof of complete asynchronous cleanup.
- Tailnet code, Host/security middleware, version files, release script and `.github/` are unchanged in this delta.

**Pending owner checks:** F1 remains the release decision: whether to publish the dashboard release alongside merge-time installer and website changes. Native-platform verification and the defects above are engineering work, not tasks for the owner.

**Verification limits:** I read the complete named packet, declined list, source delta, relevant callers, provider error paths, transcript writer, all six `fix1` screenshots, supplied `fix1` logs and their instruments. Generated assets were assessed through their sources and recorded build evidence, not independently rebuilt. The three named lead commits contain review records only.

These permitted checks passed:

```text
git -C ~/labs/projects/anyscribe-wt/wave1 diff --check 8d63221..248ee2b
bash -n ~/labs/projects/anyscribe-wt/wave1/install.sh
```

The final HEAD still matched the target, with no tracked working-tree differences.

The brief prohibited independently running these checks:

```text
cd ~/labs/projects/anyscribe-wt/wave1 && .venv/bin/python -m pytest -q
cd ~/labs/projects/anyscribe-wt/wave1 && .venv/bin/ruff check src tests scripts
cd ~/labs/projects/anyscribe-wt/wave1/ui && npm run lint && npm run build
cd ~/labs/projects/anyscribe-wt/wave1 && python3 scripts/build-docs.py && python3 scripts/check-docs.py
gh pr checks 26 --repo rishmadaan/anyscribe
```

Exact-SHA CI, native macOS installation, Windows PowerShell 5.1/registry behavior, real desktop installation, and runtime reproduction of R2C1–R2C3 remain unverified here. The recorded Windows proof uses PowerShell 7 on Linux with a substituted registry PATH; it does not establish native Windows behavior.