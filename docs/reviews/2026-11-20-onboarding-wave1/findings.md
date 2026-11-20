# Findings, verbatim

Note: in these Markdown copies, absolute home-folder paths are written as `~` paths; the byte-exact originals stay in the run folder (~/.review-runs/2026-11-20-onboarding-wave1/). The fit report was relayed through the Agent tool and its one home-folder path was already written as a `~` path when saved.

## Round 1: report-gpt-6.1-sol-r1.md

~~~~
**NOT YET.** The implementation covers the approved wave 1 scope, but the download lock can be bypassed, recovery can claim the wrong model is ready, and key-check results can advance an edited key without checking it.

Reviewed `feat/onboarding-wave1` at `8d632214835e865c44484515452f0bbaec7ccdfc`, against `7ab1539`. “CONFIRMED” below means confirmed by source trace, not by running the application.

1. **C1 | blocker | CONFIRMED: the cloud path can leave and close the wizard during a download.**

   Where: [OnboardingWizard.tsx:730](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:730), also lines 631–634 and 862–867.

   Choose a cloud provider, enable local transcription as a backup, and start downloading. The checkbox remains enabled. Unchecking it exposes **Skip, next**, which has no `settingUp` guard. Clicking it unmounts the local step; its cleanup calls `onRunning(false)`, unlocking Escape, outside click, and **Skip for now** while the backend download continues. Closing then loses the unsaved wizard choices.

   Fix: disable the checkbox during setup and guard every route out of the step against an active setup. Verify this exact cloud-backup path, including closing from Workspace after attempting to skip.

2. **C2 | blocker | CONFIRMED: 409 recovery can label an undownloaded model “ready.”**

   Where: [OnboardingWizard.tsx:687](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:687), also lines 656–660 and 975–978. Backend definition: [local_setup.py:328](~/labs/projects/anyscribe-wt/wave1/src/anyscribe/core/local_setup.py:328).

   Select Turbo in the wizard, then start Small from another tab before pressing Download. The wizard receives 409 and watches Small, but retains Turbo in `form.localModel`. When Small finishes, `s.set_up` becomes true because it means **any model is runnable**. The wizard advances and its summary says **Turbo · ready**, although Turbo was never downloaded. Finish can then start that missing download synchronously through the save endpoint.

   Fix: explicitly reconcile the selected model with `setup_last_model` when adopting another setup. Before advancing or saying “ready,” verify the particular model being summarized is runnable.

3. **C3 | should-fix | CONFIRMED: an old key’s successful check can advance a newly edited key.**

   Where: [OnboardingWizard.tsx:466](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:466), also lines 444–463 and 488–491.

   Press Next with key A, then edit the input to key B while the request waits. The input remains editable. When A is accepted, the pending `handleNext` calls `onNext()` without checking whether A is still the current value. B proceeds unchecked. The `check.key === value` comparison protects the displayed result, but does not protect this automatic navigation. Back is also active while the request waits, allowing a late response to navigate after leaving the step.

   Fix: discard obsolete responses before updating state or navigating. Bind requests to the provider, key, and current step, or disable editing and navigation while checking.

4. **C4 | should-fix | CONFIRMED: Windows can still print “ready” after losing ffmpeg from PATH.**

   Where: [install.ps1:364](~/labs/projects/anyscribe-wt/wave1/install.ps1:364). Trace also passes through lines 119–129, 289, and 46–50.

   Start PowerShell with ffmpeg and ffprobe available through a session-only PATH entry. `Test-Ffmpeg` records `$script:FfmpegOk = $true`. Later, `Install-Anyscribe` unconditionally calls `Refresh-Path`, replacing PATH with the registry values and dropping that entry. The final banner uses the cached boolean without checking again. Desktop setup can succeed without checking ffmpeg, so the banner can say **anyscribe is ready!** while transcription cannot find it.

   Fix: recheck both binaries after the final PATH change and before launching desktop mode and reporting readiness. The existing isolated `Test-Ffmpeg`/`Write-Result` proof does not exercise this intervening PATH replacement.

5. **C5 | nit | CONFIRMED: source links containing parentheses are truncated.**

   Where: [TranscriptBody.tsx:16](~/labs/projects/anyscribe-wt/wave1/ui/src/components/TranscriptBody.tsx:16).

   `writer.py` preserves the original URL. For `[source](https://example.com/audio_(final).mp3)`, the renderer stops the URL at the first `)`, creating a broken link and leaving `.mp3)` as visible text. This limitation is acknowledged in the builder’s proof; it is not a security bypass.

   Fix: parse balanced parentheses in link destinations. The separate Source button retains the full URL, which limits the impact.

The scope and instrument are appropriate for the owner’s approved request. No architectural replacement or new dependency is needed. The lead’s **“Not checked yet”** correction is accurate: Sarvam’s key is saved only at Finish.

By inspection, ordinary 429s remain retryable, no-credit errors bypass retry, the revised key checks use fixed provider HTTPS endpoints, and the renderer constructs React elements with HTTP(S)-only links. I found no changed-code path that persists the typed key before Finish. Tailnet code, Host-check middleware, version files, release script, and `.github/` have no changes in this diff. The settled declined finding was not reopened.

**Pending owner checks:** none that only the owner can confirm. Native Mac and Windows verification remains engineering work, not an assignment to him.

**Verification limits and inspection:** I read the complete packet, declined list, lead-made commit, changed source and documentation diff, relevant callers, `vault/writer.py`, mutation outputs, installer log evidence, server logs, and all supplied screenshots. Generated bundles and generated documentation were reviewed through their sources, as instructed.

I ran these permitted checks successfully:

```text
bash -n ~/labs/projects/anyscribe-wt/wave1/install.sh
git -C ~/labs/projects/anyscribe-wt/wave1 diff --check 7ab1539..8d63221
```

The brief prohibited runtime checks, so I did not independently run:

```text
cd ~/labs/projects/anyscribe-wt/wave1 && pytest -q
cd ~/labs/projects/anyscribe-wt/wave1 && ruff check src tests scripts
cd ~/labs/projects/anyscribe-wt/wave1/ui && npm run lint && npm run build
cd ~/labs/projects/anyscribe-wt/wave1 && python scripts/build-docs.py && python scripts/check-docs.py
gh pr checks 26 --repo rishmadaan/anyscribe
```

Exact-SHA CI, native macOS installation, Windows PowerShell 5.1, registry PATH refresh, and a real desktop installation remain unverified here. The saved `app-ffmpeg-after-setup-1440.png` shows an empty modal panel, so it does not visually substantiate that particular recovery state. The Sarvam screenshots predate the lead’s wording correction.
~~~~

## Round 1: report-opus-fit-r1.md

~~~~
FIT REVIEW, onboarding wave 1, round 1. Target: feat/onboarding-wave1 at 8d63221 (diff 7ab1539..8d63221). Checkout confirmed on that branch, clean tree.

1. VERDICT: CONDITIONAL on three things. (a) The owner decides when the PyPI release happens, because merging puts the website docs live but customers keep getting the old dashboard (F1). (b) The blank "after setup" screenshot is retaken, or the proof says the check was seen in the page code only (F3). (c) CI is green on 8d63221 (I could not check it). F2 is a should-fix that the lead can fix now or log for later with the owner's OK.

This is the job he asked for. All eight wave 1 items are built and match the ask, and I found nothing from wave 2 or 3 built by accident. The extras are small and in the spirit of the ask: the History "Source" button now opens only http(s) links, the Linux ffmpeg command follows the detected package manager, the website commands wrap below 1100 px, and web-ui-spec.md gained one line. Read as a non-technical customer would read them, the new sentences are plain, short, free of em dashes, and match the fixed strings. The screenshots show what the proofs claim, except the one in F3.

2. FINDINGS

F1. should-fix. CONFIRMED (traced, not run).
Where: landing/docs/getting-started.html and landing/docs/troubleshooting.html (sources docs/user/getting-started.md:114-120 and docs/user/troubleshooting.md:296-363), vercel.json ("outputDirectory": "landing"), install.sh:25 (INSTALL_METHOD="pip", i.e. PyPI), install.ps1:278.
What goes wrong: on merge, Vercel publishes the new docs straight away. Both installers keep installing anyscribe from PyPI, which is still v0.19.0. A customer who installs the day after merge pastes a Groq key and the old dashboard says "API key is set for groq" in green. Meanwhile the website tells them Next asks the provider, and describes "One more thing: ffmpeg", "Not checked yet", "Read transcript" and the no-credit message. They cannot find any of these. Five of the eight items (W3 wizard half, W4, W5, W6, W8) reach customers only with a release. The CHANGELOG says so honestly; the getting-started and troubleshooting pages do not.
The owner would object to hearing "wave 1 is done" at merge when most of the dashboard half is invisible to his customers.
Fix: ask him at merge time whether to release to PyPI the same day, and merge and release together. If he says not yet, add one line to the two doc pages saying the dashboard parts arrive with the next version.

F2. should-fix. PLAUSIBLE (no real Mac run).
Where: install.sh:145-156. The installer activates Homebrew for its own run only (eval brew shellenv) and never saves it to ~/.zprofile.
What goes wrong: on an Apple Silicon Mac with no Homebrew, the fresh Homebrew lands in /opt/homebrew/bin, and new Terminal windows do not look there. Desktop mode, the default, is fine, because the tray's own search path adds /opt/homebrew/bin (core/service.py:59-73). The trouble is the terminal route: --no-desktop, or a desktop step that failed. There the box says "Open a new terminal window, then type: anyscribe ui". In that window anyscribe is found (pipx), but ffmpeg and Deno are not, because the dependency check only searches the window's path (core/deps.py:289). The wizard then shows "One more thing: ffmpeg" with `brew install ffmpeg`, which answers "command not found: brew". That is a dead end.
This is not new code, but W1 makes the path reachable for the first time: before, the installer died at the Homebrew step. The new troubleshooting entry already tells people who installed Homebrew by hand to run Homebrew's "Next steps" lines, so the repo knows about the gap.
Fix (one line): after a successful fresh Homebrew install, append the same `eval "$(/opt/homebrew/bin/brew shellenv)"` line that Homebrew's "Next steps" prints to ~/.zprofile. Or log it under wave 3 "terminal fixes".
To settle it: run an Apple Silicon Mac with no Homebrew, `curl ... | bash -s -- --no-desktop`, then a new Terminal and `anyscribe ui`.

F3. should-fix. CONFIRMED.
Where: ~/.review-runs/2026-11-20-onboarding-wave1/screens/app-ffmpeg-after-setup-1440.png, cited in proof-app.md section a.
What goes wrong: the screenshot is an empty dialog. It is the only picture of the "setup ended, ffmpeg missing" state, which is the actual fix for the silent loop the audit found (one of the must-never-happen items). So the proof claims more than its evidence. The walk is described in text, so the code is probably right, but nobody has seen the screen.
Fix: retake the screenshot. If that cannot be done, reword proof-app.md to say the check was made in the page code only, as it already does for Settings.

F4. nit. CONFIRMED.
Where: BACKLOG.md:668.
What goes wrong: it still says Sarvam returns "Saved, not checked". proof.md says the lead's rewording to "Not checked yet" was applied everywhere ("10 files"), so this one was missed.
Fix: change the words in that line.

F5. nit. PLAUSIBLE.
Where: core/errors.py:106-113 (no_credit_message), used for any provider's 402 or 429 insufficient_quota.
What goes wrong: for Groq, Deepgram or ElevenLabs the message says "{Provider} is prepaid", which is not true of every provider's billing. The APP builder flagged this, and no lead verdict is recorded.
Fix: say "is prepaid" only for OpenAI and OpenRouter. For the others, say "add credit or check your plan".

F6. nit. CONFIRMED.
Where: install.sh:681. On a desktop-mode install that used pipx, the line printed under the box reads "If 'anyscribe' is not found when you type it...".
What goes wrong: the box has just told the person to click the app and has not asked them to type anything, so the line reads as noise. It exists only because tests/test_install_sh.py:342 requires "pipx ensurepath" to appear.
Fix: reword it to "If you type anyscribe in a terminal later and it isn't found, open a new window; if it still isn't, run: pipx ensurepath".

F7. nit. PLAUSIBLE.
Where: install.sh:628-633, the Mac S7a box.
What goes wrong: "click the anyscribe app (in the Applications folder inside your home folder)" is accurate (desktop mode installs to ~/Applications), but a non-technical Mac user will not find that folder. Finder's sidebar "Applications" is /Applications.
Fix: "press ⌘ Space, type anyscribe, press Return". That is the same motion the website just taught for Terminal, and Spotlight indexes ~/Applications.

F8. nit. PLAUSIBLE.
Where: install.ps1:349-367, for -NoDesktop or a failed desktop step, when ffmpeg is missing.
What goes wrong: the box says "winget install Gyan.FFmpeg, then open anyscribe again" and "Type: anyscribe ui" in the same window. That window's PATH predates winget's change, so the dashboard may still not find ffmpeg. The wizard's Windows-only sentence talks about quitting from the tray, which this route does not have.
Fix: on this route, say "then open a new PowerShell window and type: anyscribe ui".
To settle it: a real Windows run with -NoDesktop and no ffmpeg.

F9. nit. CONFIRMED.
Where: ui/src/components/OnboardingWizard.tsx:466-473 (handleNext).
What goes wrong: for Sarvam, where nothing can be checked, the first press of Next only shows the amber note and a second press is needed. A first-time user will wonder whether the press worked.
Simpler: show the "Not checked yet" note on the Sarvam key step from the start, and let the first press go on.

F10. nit. CONFIRMED.
Where: the missingPart() sentences in OnboardingWizard.tsx:883-890.
What goes wrong: "the local engine (faster-whisper)" and "Open the install log below" are jargon on a rare branch.
Fix: plain words, for example "a part anyscribe needs didn't install".

3. ANSWERS AND ADVICE
- The right instrument? Yes. The ask's eight items match the spec's W1 to W8 one for one, and the consent scope holds: the two installers, the website, the wizard and Done screen, the error and key-check code, with no new dependencies.
- The lead-made change ("Saved, not checked" became "Not checked yet") is right. It removes a false "Saved" on the wizard step, where nothing is saved until Finish, and keeps the settled substance: amber, not a fake success, not a failure. One file was missed (F4).
- Three gaps that builders flagged have no home in BACKLOG.md: the Settings local-setup window still ends silently when ffmpeg is missing (LocalSetupModal.tsx), the "prepaid" wording (F5), and F2 if deferred. Add them as wave 2 or 3 lines so they are not lost.
- Optional polish, not a finding: the History page shows duration and word count twice, once in the strip at the top and again in the body lines. The hero lists Mac first. For a mostly Windows audience, consider Windows first or picking by the visitor's OS in a later wave.

4. PENDING OWNER CHECKS
- Release timing (F1): does he approve a PyPI release right after merge? His approval says "if it's mergeable, we'll merge it". Confirm whether he merges or the lead does, since merging publishes the installers and the website.
- Whether he accepts the reworded Sarvam string. It is listed under "decisions already made" in the spec.
- A real Mac run (Homebrew branch, desktop box) and a real Windows PowerShell 5.1 run (winget, keeping the window open on failure). No one has done either.

5. COULD NOT CHECK, AND WHAT I INSPECTED
- CI on 8d63221: not run (not allowed by the brief). Command: `gh pr checks 26 --repo rishmadaan/anyscribe`
- No tests, builds, servers or installers were run (read-only brief). `bash -n install.sh`: ok.
- Not checked on real hardware: everything Mac or Windows. I took the builders' Docker and PowerShell 7 evidence as described.
- Inspected: the whole packet (ask.md, spec.md, target.md, lens.md, proof.md, proof-install.md, proof-app.md, review-log.md, declined.md); commit 8d63221 in full; the source diffs of install.sh, install.ps1, landing/index.html, docs/user/{getting-started,troubleshooting,commands}.md, CHANGELOG.md, BACKLOG.md, the journal entry, core/errors.py, web/routes/config.py, cli/onboard.py, OnboardingWizard.tsx, FfmpegNotice.tsx, SetupBanner.tsx, ResultCard.tsx, TranscriptBody.tsx, TranscriptView.tsx, TranscribePage.tsx, SettingsPage.tsx, transcript.ts, types.ts, tests/test_onboard_agent_cli.py, and the relevant parts of tests/test_install_sh.py.
- Also read: vault/writer.py (the shapes the renderer must handle), core/local_setup.py check_status, core/service.py service_path, core/deps.py's PATH lookup, vercel.json.
- Screenshots viewed: install-hero 1440 and 390; app-ffmpeg-notice 1440 and 390; app-key-refused, app-key-notchecked, app-openai-prepaid, app-download-after-reload, app-ffmpeg-after-setup (blank), app-done 1440 and 390, app-history-clean 1440, app-history-timestamped 390.
- Not reviewed: code correctness, which is the other reviewer's role.

Skipped: did not open the raw logs under install-logs/ and logs/. I relied on the proof excerpts.
Risk: F1 is what the owner feels first. Merging without a release decision puts website docs live that describe a dashboard his new customers will not have.

~~~~

## Round 2: report-gpt-6-astra-r2.md

~~~~
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
~~~~

## Round 2: report-opus-fit-r2.md

~~~~
FIT REVIEW, onboarding wave 1, round 2. Target: feat/onboarding-wave1 at 248ee2b (diff 7ab1539..248ee2b). I confirmed the checkout is on that branch and commit with a clean tree. `bash -n install.sh`: ok.

1. VERDICT: CONDITIONAL on two things. (a) The owner decides when the PyPI release happens. This is round 1's F1, still open by design: merging puts the website's docs live, but customers keep getting the v0.19.0 dashboard until a release. (b) CI is green on 248ee2b. I could not check it; the command is in section 5.
No blocker and no should-fix is left from fit. The four new findings below are nits. The lead can fix them now in one small round or send them to wave 2.

This is still the job he asked for. Wave 1's eight items match W1 to W8 one for one. The fix round added nothing from wave 2 or 3: the one BACKLOG line it added was asked for, and hiding Test key for Sarvam is part of F9. Read as a first-time customer would read it, every new sentence in the fix round is plain and short and has no em dash. The fix1 screenshots show what proof.md claims.

2. FINDINGS (new in round 2)

F1. nit. CONFIRMED (traced in code, not run on Windows).
Where: ui/src/components/FfmpegNotice.tsx:80 (the Windows sentence, spec string S4) and install.ps1:368 (the desktop-route yellow box).
What goes wrong: a Windows customer reads "Install it with the command below, then click Check again." They run `winget install Gyan.FFmpeg` and click Check again, and get "Still not found." This happens every time, not only now and then. The running anyscribe looks up ffmpeg with `shutil.which` on its own PATH (core/deps.py:289, core/preflight.py:38) and never re-reads the registry. install.ps1:367 says so in its own comment: "The running tray keeps the PATH it started with." The same goes for the installer box's "then open anyscribe again": clicking the Start menu app while the tray runs can't help either. Only the fallback sentence ("If it still isn't found... quit anyscribe from the tray") works. So on Windows the first instruction is a dead click, and the step that works is worded as if it were rare. On Mac and Linux, Check again does work: the tray's PATH includes /opt/homebrew/bin, and apt installs to /usr/bin.
The spec's S4 is slightly wrong here, so this is a spec fix, not a builder miss.
Fix: on Windows only, say the working step directly. Wizard: "After installing, quit anyscribe from the tray (the icon near the clock) and open it again from the Start menu; Check again can't see ffmpeg before that." Box: "...winget install Gyan.FFmpeg, then quit anyscribe from the tray (the icon near the clock) and open it again."

F2. nit. CONFIRMED (screenshots).
Where: OnboardingWizard.tsx:859, the progress line ("Downloading Whisper Base… 8.9%"). It sits below the picker, which starts at line 810.
What goes wrong: while a download runs, and above all after a reload, the dialog opens on the language question and the model cards. The progress line is below the fold at 1440 px, and further down at 390. The running model's card says "incomplete: the download resumes" (an existing string), which reads as paused. Only the small grey header line "Skip is off until the download finishes" says anything is happening. Someone who reloaded will think it started over. W6 asks the wizard to "show the running download's progress". It does, but it is out of sight. Seen in fix1-c2-after-reload-1440.png, fix1-c1-locked-during-download-1440.png and app-download-after-reload-1440.png.
Fix: while `settingUp`, render the progress block above the picker, or scroll it into view when a running setup is adopted.

F3. nit. CONFIRMED.
Where: OnboardingWizard.tsx:242, :792 and :933.
What goes wrong: during a download, one screen says "until the download finishes" three times: in the header ("Skip is off..."), in the checkbox label ("stays on...") and under the buttons ("Back is off..."). It reads as nervous rather than clear. It also says "download" while the first phase is "Installing the local engines".
Fix (simpler): keep one line, for example in the header: "Skip, Back and this checkbox are off until setup finishes". Drop the other two.

F4. nit. PLAUSIBLE (traced; proof.md says this sentence was never seen on screen).
Where: OnboardingWizard.tsx:943 (the restart case of missingPart), together with :829 (RestartBanner) and the button label "Try again" (:900).
What goes wrong: when setup ends needing a restart, the customer sees two restart messages, a red one and an amber one. The red one ends "then continue", but the only button says "Try again". After a restart the wizard starts again from Welcome, so "continue" names nothing they can find.
Fix: in the restart case, show only the RestartBanner (no red alert), or end the sentence "then open the setup wizard again; the download is kept."
To settle it: walk a setup whose engines need a restart (restart_needed true, faster_whisper_installed false).

3. ROUND 1 FIT FINDINGS: STATUS
- F1 (website docs live before the dashboard release): DECLINED-OK as code. It went to the owner as a release decision. The docs still describe the unreleased dashboard, so it stays a pending owner check.
- F2 (Homebrew PATH): DECLINED-OK. REFUTED and settled in docs/reviews/declined.md. Not reopened.
- F3 (blank screenshot): FIXED. I opened fix1-f3-ffmpeg-after-setup-1440.png. It shows "One more thing: ffmpeg", the S4 body, `sudo apt install ffmpeg` and Check again. The bottom shot shows the continue button dimmed.
- F4 (BACKLOG wording): FIXED. BACKLOG.md:668 says "Not checked yet". `git grep -i "saved, not checked"` outside docs/reviews finds nothing.
- F5 ("is prepaid" for every provider): FIXED. core/errors.py:105-122 keeps "is prepaid" for openai and openrouter only; the others get "Add credit or check your plan". The docs and the skill reference match.
- F6 (pipx line after the click-the-app box): FIXED. install.sh:677 has the agreed sentence.
- F7 (Mac "Applications folder inside your home folder"): FIXED. install.sh:673 says "press Cmd and Space, type anyscribe, press Return". Not yet seen on a real Mac.
- F8 (Windows without desktop mode, ffmpeg missing): FIXED. install.ps1:370-372 says to "open a new PowerShell window and type: anyscribe ui", with a matching fallback header at :381.
- F9 (Sarvam needs two presses of Next): FIXED. OnboardingWizard.tsx:468 and :493 show the amber note from the start and go on at the first press; Test key is hidden. Screenshot fix1-f9-sarvam-key-1440.png.
- F10 (jargon in missingPart): FIXED for the words: no package names, no "install log". One leftover in the restart case, now F4 above. The engine and restart sentences were never seen on screen.

4. ANSWERS AND ADVICE
- Right job, right instrument: yes. The consent scope holds (the two installers, the website, the wizard and Done screen, the error and key-check code, no new dependencies). The round 1 fixes stayed inside the items.
- One thing the owner may object to later (advice, not a finding): W6's lock has no exit. No cancel endpoint exists (web/routes/local.py), and Back, Skip and Escape are all off. A customer on a slow or stalled connection is held in the wizard until the download ends or fails. Someone who picked a cloud service and ticked "also local" as a backup can wait about 27 minutes for Turbo's 1.6 GB at 1 MB/s. The spec chose the lock, so it is not a defect. Make sure wave 2's "download MB count, time and stall warning" item includes a way out (cancel, or "keep downloading in the background").
- Reload mid-download switches the wizard to "On this computer". Someone who picked Groq plus a local backup and then reloaded finds All set saying "On this computer". This is honest, since the typed key could not be kept before Finish. Worth one line in wave 2's notes.
- The S5 box tells a Windows user without winget to run `winget install Gyan.FFmpeg`. This is rare, and it is the spec's own string. Leave it.

5. PENDING OWNER CHECKS
- Release timing (round 1 F1): does he approve a PyPI release right after merge, and who merges? Merging publishes both installers and the website at once.
- A real Mac run: Homebrew asks for the password, the Spotlight wording works, and Check again finds a fresh `brew install ffmpeg`.
- A real Windows (PowerShell 5.1) run: the window stays open on failure, winget's PATH refresh works, and F1 above. Nobody has run either.

6. COULD NOT CHECK, AND WHAT I INSPECTED
- CI on 248ee2b. The brief's allow-list doesn't cover `gh`, so I did not run it. Command: `gh pr checks 26 --repo rishmadaan/anyscribe`
- Nothing was run beyond `bash -n install.sh`. No tests, builds, servers or installers.
- Inspected: the whole packet (ask.md, spec.md, target.md, lens.md, proof.md including the round 1 fix section, review-log.md, fix-plan-r1.md, report-opus-fit-r1.md, declined.md); `git log 7ab1539..248ee2b`; the full fix-round diff 37f066c..248ee2b for install.sh, install.ps1, core/errors.py, OnboardingWizard.tsx, TranscriptBody.tsx, BACKLOG.md, CHANGELOG.md, docs/user/getting-started.md, docs/user/troubleshooting.md, the skill's troubleshooting reference and the journal; the current OnboardingWizard.tsx (wizard mount, header, StepApiKey, StepOfflineOptIn, missingPart); FfmpegNotice.tsx; web/routes/local.py (status, background setup, no cancel); web/routes/config.py (Sarvam and the unreachable results); install.ps1's Write-Result and its ffmpeg step; core/deps.py and core/preflight.py (ffmpeg lookup); LocalModelPicker.tsx:85.
- Screenshots viewed: fix1-c1-locked-during-download, fix1-c2-after-reload, fix1-c2-all-set, fix1-f3-ffmpeg-after-setup (top and bottom), fix1-f9-sarvam-key, app-download-after-reload, install-hero-1440 (all at 1440 px).
- Not re-read this round: the Done screen, TranscriptView and ResultCard (no change since round 1, which reviewed them); the raw logs; code correctness, which is the other reviewer's role.

What I skipped: the raw run logs and the round 0 screenshots I had already covered in round 1. The risk the owner must know: round 1's F1, the release timing, is still the first thing customers will feel after merge.

~~~~

## Round 3: report-gpt-6.1-sol-r3.md

~~~~
**NOT YET.** The seven original round 2 findings are repaired on their reported paths, but the new handoff can let a customer leave a confirmed running download without the required confirmation. A further request-ordering risk remains untested.

Reviewed `feat/onboarding-wave1` at `c07a65cf74c9cd3dbe2d2a4184b32a715d6e8013`, against `248ee2b`. The work still matches the approved wave 1 scope. CONFIRMED below means established by source trace or existing recorded evidence; runtime execution was prohibited.

**Round 2 findings**

Locations below are within `~/labs/projects/anyscribe-wt/wave1/`.

| Finding | Status | Evidence |
|---|---|---|
| R2C1 | **FIXED** | `OnboardingWizard.tsx:795` sends only the start request; subsequent status failures no longer enter its refusal handler. Recorded T1, T1_500 and T2 support this. |
| R2C2 | **FIXED** | The wizard no longer writes a running lock from its opening read. T5 and T5_late show the original true-then-false handoff no longer leaves a stale lock. |
| R2C3 | **FIXED** | The watcher bounds requests, retries sequentially, handles log failure separately, and exposes the unreachable notice and confirmation. T7, T8 and T9 support these paths. |
| R2F1 | **FIXED** | `FfmpegNotice.tsx:76` and `install.ps1:368` directly instruct Windows users to quit from the tray and reopen. Native Windows operation remains unverified. |
| R2F2 | **FIXED** | `OnboardingWizard.tsx:901` places progress above the picker. Both supplied desktop and mobile screenshots show it near the top. |
| R2F3 | **FIXED** | Only the header retains the lock explanation, now “Skip and Back are off until setup finishes.” |
| R2F4 | **FIXED** | `missingPart()` returns null for the specified restart case; the single RestartBanner includes the route back to the wizard. Recorded F4 and its screenshot support this. |

**New findings**

1. **R3C1 | should-fix | CONFIRMED: the running-download handoff starts unlocked, and Back can bypass the unreachable confirmation.**

   Where: [OnboardingWizard.tsx:162](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:162), especially lines 696, 712, 715 and 953.

   Concrete sequence:

   - Reopen the wizard during a real download.
   - The wizard’s opening read returns `setup_running: true` and routes to Local transcription.
   - The local step initializes `watching` and `starting` to false. It receives neither the running state nor the opening response.
   - Its next status read hangs or fails.

   Until that step receives a successful running response, it reports `idle`. Skip is available, Escape closes immediately, and Back is enabled. This discards the already confirmed running state before the two failures required for the approved exit.

   There is also a persistent bypass after the unreachable notice appears: Back remains enabled because `busy` is still false. Clicking Back unmounts the step, whose cleanup reports `idle`; Escape or Skip can then close without S11.

   The final-bundle evidence already exposes part of this defect: [lead-final.json:476](~/.review-runs/2026-11-20-onboarding-wave1/logs/fix2-instruments/results/lead-final.json:476), T6’s `afterTwoFails`, records `"back": "enabled"`. T6 checks the notice and eventual recovery, but never attempts Back or an early close.

   Fix: transfer the opening read’s running knowledge into the single owner, retaining it until a qualifying stopped response. Keep navigation guarded during reconciliation. Test Escape, Skip and Back both before the second read settles and after S12 appears.

2. **R3C2 | should-fix | PLAUSIBLE: a status response can start and finish watching before the start request settles.**

   Where: [OnboardingWizard.tsx:723](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:723), particularly lines 750–765, 782 and 795–804.

   Rule 6 requires the ending status request to have been sent after the start request settled. The implementation achieves that in the ordinary path by switching `watching` after the POST, but does not enforce it generally.

   On returning to the local step with a previous selection, Download is enabled while the first status read is pending. If that read reports another running setup while a new start request remains pending, it sets `watching=true`. The watcher can then consume a stopped response and advance to Workspace before the pending POST settles. With requests reordered across connections, that pending request could subsequently start work after the step has been left.

   The existing T11 delays a stopped response and gives the POST an immediate answer. It does not cover an earlier running response combined with a delayed POST.

   What would settle it: extend T11 with an initial running response arriving during a delayed start request, followed by stopped-and-runnable status. Assert that completion cannot occur before the start settles, and that only a subsequently sent read can end watching.

   Fix: explicitly track the start request’s lifetime and invalidate earlier status reads. Do not rely solely on `watching` changing to establish request ordering.

3. **R3C3 | nit | CONFIRMED: recovery documentation promises continuation that a server restart does not guarantee.**

   Where: [CHANGELOG.md:60](~/labs/projects/anyscribe-wt/wave1/CHANGELOG.md:60) and [troubleshooting.md:571](~/labs/projects/anyscribe-wt/wave1/docs/user/troubleshooting.md:571), also generated `landing/docs/troubleshooting.html`.

   The changelog says the download carries on after describing an unreachable server, including quitting it. Troubleshooting says reopening makes progress come back.

   Setup runs inside the server process, and its tracking state is in memory. After termination or a crash, reopening can instead produce the Try again state. The journal and recorded restart walk correctly describe that outcome.

   Fix: say the download continues **if anyscribe remains running**. After reopening, the page reconnects and may ask the customer to retry setup.

**The 14 binding rules**

| Rule | Assessment |
|---|---|
| 1. One owner | **MET structurally:** one reporting effect and no wizard poll. The handoff loses information, as R3C1 explains. |
| 2. Lock and confirmed unreachable exit | **PARTLY:** correct after watching starts; adoption has an unlocked interval and Back bypass. The implemented two-failure threshold follows rules 1 and 11, as the proof discloses. |
| 3. S11 and buttons | **MET** on paths reaching it. Close setup uses `dismiss(false)`. |
| 4. Start/adopt watching | **PARTLY:** local running reads and POST outcomes work; the wizard’s confirmed running response is not inherited. |
| 5. Explicit refusals | **MET:** non-409 HTTP failures show the plain refusal sentence without their body. |
| 6. Qualified ending read | **PARTLY:** failures never end watching, but the post-start ordering is implicit and has the R3C2 gap. |
| 7. Exactly once | **MET within a watcher:** `stop` and cleanup discard replaced or unmounted results. The premature-completion concern is rule 6. |
| 8. Status separate from log | **MET:** failed logs no longer discard status. A hanging log can still delay applying it by the bounded log wait. |
| 9. Bounded and sequential | **MET for the polling loop.** This is not a global single-request guarantee: the wizard opening read and manual Check again can overlap step reads. |
| 10. First-status recovery | **MET:** reads continue until status arrives, with S12 after repeated failures. |
| 11. Unreachable notice | **MET in the loop:** two failures show it; a good loop response clears it; percentages disappear while unreachable. |
| 12. No raw text | **PARTLY:** fetch-layer errors are suppressed, but `setup_error` still renders verbatim at line 886. This is pre-existing behavior explicitly disclosed in the proof, not a new regression. |
| 13. Previous guards | **PARTLY:** checkbox, Back, picker and start are disabled while busy; adoption is not initially busy. Selected-model runnable checks and key-check guards remain. |
| 14. Progress and one explanation | **MET:** progress precedes the picker and only one lock explanation remains. |

**Ordering and test assessment**

The diagnosis’s section 2 contains **ten numbered orderings, not twelve**. There are no rows 11 and 12 to assess.

| Cases | Assessment from source and recorded evidence |
|---|---|
| Orderings 1–2; T1–T2 | Accepted start or 409 followed by a failed read retains watching and hides raw errors. |
| Ordering 3; T3 | Stopped-and-runnable status advances without showing 409. |
| T4 and variants | Network failure, timeout and explicit refusal are distinguished. Final T4v2 covers the lead’s start-time lock. |
| Ordering 4; T5 | Original stale lock is removed, including the delayed opening response. |
| Ordering 5; T6 | Recovery eventually works, but early closing and Back expose R3C1. |
| Ordering 6; T7, T9 | Established watchers expose server loss; hung reads abort and retry. |
| Ordering 7; T8 | Log failure no longer blocks successful completion. |
| Ordering 8; T10 | Sequential polling and cleanup prevent the reported duplicate completion path. |
| Ordering 9; T11 | The recorded fast-POST ordering works; the delayed-POST variant remains R3C2. |
| Ordering 10; T12 | A non-runnable selected model produces Try again rather than ready after restart. |
| T13 | Established watching supports the intended reachable lock, unreachable confirmation and reopening path. It does not exercise R3C1’s initial handoff. |

The mutation records demonstrate failures for M1, M6 with HTTP 500, M6b, M8 and M9, followed by restored passes. The final lead run’s old T4_hang failure is explained by its obsolete expectations; the replacement T4v2 checks the actual request timeout.

**Integration, bundle and retained behavior**

- `onRunning` has one code call site, inside the local step’s reporting effect. Settings, LocalSetupModal and App do not consume that callback.
- `fetchJSON` itself is unchanged. The three API wrappers gained optional signals; existing callers omit them and retain their previous behavior. The 10-second limit lives in the wizard’s `limited()` helper, not globally in the API client.
- Settings and LocalSetupModal retain their existing polling behavior and receive no new timeout or unreachable exit. Their known limitations are recorded in BACKLOG.
- RestartBanner’s optional children leave its other callers’ content unchanged.
- Static `index.html` references `index-2r9Aqod2.js`. Inspection of that bundle confirms the final `busy` lock expression, timeout helper and revised header text. **I found no inspected mismatch, but did not independently establish exact build equivalence.**
- The delta does not change provider error classification, transcript rendering, key-check endpoints, dependencies, tailnet code or Host/security middleware. The retained key input and navigation guards remain present.
- The records describe the chosen hard lock with an unreachable exit, rather than design B. Their unconditional lock claims overstate the implementation because of R3C1.

**Pending owner checks**

Only release timing remains an owner decision: whether and when to release the dashboard changes to PyPI alongside merge-time installer and website publication. Native-platform verification and the findings above are engineering work, not actions assigned to the owner.

**Inspection and verification limits**

I read the named packet, earlier findings and verdicts, both fix plans, diagnosis, declined list, lead-made changes, source delta and relevant callers. I inspected the harness, cases, mutations, saved result records, walk log and all seven `fix2` screenshots. The settled Homebrew finding was not reopened.

These permitted checks passed:

```text
git -C ~/labs/projects/anyscribe-wt/wave1 diff --check 248ee2b..c07a65c
bash -n ~/labs/projects/anyscribe-wt/wave1/install.sh
git -C ~/labs/projects/anyscribe-wt/wave1 diff --exit-code c07a65c -- ui/src src/anyscribe/web/static install.sh install.ps1 docs/user
```

The brief prohibited running these checks:

```text
cd ~/labs/projects/anyscribe-wt/wave1 && .venv/bin/python -m pytest -q
cd ~/labs/projects/anyscribe-wt/wave1 && .venv/bin/ruff check src tests scripts
cd ~/labs/projects/anyscribe-wt/wave1/ui && npm run lint && npm run build
cd ~/labs/projects/anyscribe-wt/wave1 && python3 scripts/build-docs.py && python3 scripts/check-docs.py
gh pr checks 26 --repo rishmadaan/anyscribe
```

I ran no tests, builds, servers, installers or provider calls, and wrote nothing. Exact-SHA CI, runtime reproduction of the new sequences, native macOS and Windows behavior, screen-reader behavior, and timeout suitability during a real installation remain unverified. The round 3 walk used simulated setup state over real status requests; it did not perform a real download.
~~~~

## Round 3: report-opus-fit-r3.md

~~~~
FIT REVIEW, onboarding wave 1, round 3 (final). Target: feat/onboarding-wave1 at c07a65c, checked with `git rev-parse HEAD`. The change is 7ab1539..c07a65c. I read the round 3 part, ae8f460..c07a65c, line by line.

1. VERDICT: CONDITIONAL on three things.
(a) F3-1 below is fixed. It is wording only (the S12 notice, one troubleshooting paragraph and one CHANGELOG clause), so the lead can do it at the cap and prove it by diff.
(b) CI is green on c07a65c. I could not run it; the command is in section 5.
(c) The owner decides when the PyPI release happens. This is round 1's F1, still open by design.

No blocker. Nothing on the must-never list is broken by round 3:
- No screen says ready.
- The lock has one writer, and the committed bundle index-2r9Aqod2.js carries the new lock line.
- tailnet.py, app.py, the version files, .github and release.sh have an empty diff against main.

It is still the job he asked for. Round 3 stayed inside W6, plus the four fit nits, plus the records. The one new behaviour is a way to close the wizard when anyscribe can't be reached, behind one confirmation. That is the lead's spec amendment, not something the owner approved, so it is listed under owner checks.

2. FINDINGS (new in round 3)

F3-1. should-fix. CONFIRMED (the builder's own real walk and its screenshot, plus code).
Where:
- ui/src/components/OnboardingWizard.tsx:866, S12: "If you quit it, open it again; this page picks the download back up."
- docs/user/troubleshooting.md:572-574: "...as soon as anyscribe answers the message goes away and the progress comes back."
- CHANGELOG.md:61: "...can be closed after one question; the download carries on."

What goes wrong: the download runs inside the anyscribe process. Setup state lives in memory in the app (web/routes/local.py:46-58), and the thread is started at :144. So quitting anyscribe kills the download. A customer who does exactly what S12 says (quit, then reopen) does not get the download back. The restarted server says "not running, no error". The step ends watching and shows, in red, "A part anyscribe needs to transcribe on this computer didn't install. Click Try again; if it fails again, untick local transcription and go on."
- This is the builder's real walk: proof.md, the "real walk" bullets, and screens/fix2-after-restart-try-again-1440.png.
- If the engines had already installed, the red line would instead read "Setup finished, but Whisper Base can't run yet", and "finished" is false.
- So the notice promises a resume, and what follows reads as an install failure the customer caused. It even suggests giving up on local.
- Try again does work, because the model download resumes (providers/local_models.py:17 and :528, traced from the docstrings, not run). Nothing tells the customer that.

The fix is wording, the S12 shape the lead already owns:
- S12: "Can't reach anyscribe right now. If you quit it, open it again: this page then shows the download again, or a Try again button that carries on from where it stopped."
- troubleshooting.md:574: the same two outcomes.
- CHANGELOG:61: "...can be closed after one question." Drop "the download carries on", or say "if anyscribe is still running".

Optional, and code: when the ending read has `setup_outcome` null (the server restarted mid-setup), say "The setup stopped before it finished (anyscribe was closed). Click Try again; it carries on from where it stopped." instead of the missingPart sentences. That fact is knowable from the payload (local.py:81).

F3-2. nit. CONFIRMED (screenshot).
Where: OnboardingWizard.tsx:892. The "missing" alert, moved above the picker by R2F2's commit 6a375b3, while the Try again button stays at the bottom (around :960).
What goes wrong: the red "Click Try again; ..." sits at the top of the dialog, and the button it names is below five model cards, out of sight at 1440 px (fix2-after-restart-try-again-1440.png). A first-time customer reads "Click Try again", sees no such button and hesitates. R2F2 asked for the progress block to move up. The setup-error and missing alerts went along with it.
Fix: move only the `missing` (and `setupError`) block back below the picker, just above the button row, and keep the progress block on top.

F3-3. nit. CONFIRMED (screenshot fix2-f4-restart-banner-1440.png).
Where: OnboardingWizard.tsx:875-878, the RestartBanner children.
What goes wrong: one box says restart twice in a row. First "...Quit anyscribe from its menu-bar or tray icon, then open it again. Until then, local transcription may fail..." and then "Restart anyscribe, then open the setup wizard again...". It reads as two separate instructions.
Fix: children text "Then open the setup wizard again (Settings, then Run setup wizard); the download is kept."

F3-4. nit. PLAUSIBLE.
Where: OnboardingWizard.tsx:275 (the S11 box renders at the top of the dialog) and Modal.tsx:118 (the dialog scrolls inside itself, overflow-y-auto).
What goes wrong: a customer who has scrolled down to the model cards or the Back button and presses Escape while S12 shows gets the "Close setup?" box at the top, out of view. On their screen nothing happens. Focus also stays where it was, so a keyboard or screen-reader user isn't taken to the choice.
To settle it: at 390 px, while unreachable, scroll to the bottom and press Escape.
Fix: `autoFocus` on the "Keep waiting" button. One attribute: it scrolls the box into view and gives keyboard users the choice.

3. ROUND 2 FIT FINDINGS: STATUS
- R2F1 (Windows Check again can't see winget): FIXED.
  - FfmpegNotice.tsx:199-202 says to quit from the tray and reopen from the Start menu.
  - install.ps1:367-368 says the same in the box.
  - The hint under the buttons dropped "then click Check again", and troubleshooting.md has a Windows bullet.
  - Not run on Windows.
- R2F2 (progress below the fold): FIXED. fix2-lock-progress-above-picker-390.png shows "Downloading Whisper Base… 37%" at the top, above Help me choose. The side effect is F3-2.
- R2F3 (three "until the download finishes" lines): FIXED. Only one remains, OnboardingWizard.tsx:260, "Skip and Back are off until setup finishes." It is in the committed bundle. The checkbox suffix and the Back line are gone.
- R2F4 (two restart messages in the restart case): FIXED. missingPart returns null when a restart is needed (:759-760), and only the RestartBanner shows, ending with the way back to the wizard. A wording leftover is F3-3.

4. ANSWERS AND ADVICE
- Right job, right instrument: yes.
  - The fix plan's choice (keep the owner's hard lock, add an exit only while anyscribe can't be reached) is the smallest step that keeps what he approved.
  - The confirm-to-close question is correctly parked in BACKLOG wave 2 (BACKLOG.md:686) rather than built.
- Simplest thing: yes, given the lock.
  - One writer, one loop, a 10 s limit, and a three-value report to the wizard.
  - The lead's `busy` change (locked from the click) removes the fixer's gap without a new state.
  - I'd not add more.
- What he would object to:
  - F3-1 first: the one sentence written for "something went wrong" is the one that misleads.
  - Second, a customer is still held in the wizard for the whole download while anyscribe answers. For Turbo's 1.6 GB on a slow line that is a long wait, with Back and Skip off. This is his approved design, but he should hear it plainly when the wave 2 question goes to him.
- Read as a first-time customer:
  - S11, S12, S13 and the Windows ffmpeg sentence are short and plain, with no jargon and no em dashes in the new strings.
  - S11's "Close setup" is the bright button and "Keep waiting" the quiet one. That is fine for an exit someone asked for by pressing Escape or Skip.

5. PENDING OWNER CHECKS
- Release timing (round 1 F1): merging puts both installers and the website docs live at once. The dashboard changes, including everything in round 3, reach customers only with a PyPI release.
- The W6 amendment: he approved "lock the wizard during download". The lead added "closable, after one question, when anyscribe can't be reached". He should confirm, and answer the wave 2 question (confirm-to-close, or download in the background).
- A real Mac run and a real Windows (PowerShell 5.1) run, including the Windows "quit from the tray" wording. Nobody has run either.
- After quitting and reopening the desktop app, does it come back on the same port, so the old tab reconnects? If not, S12 waits forever in the old tab. Not checked; see section 5.

6. COULD NOT CHECK, AND WHAT I INSPECTED
Not checked:
- CI on c07a65c. The brief's allow-list does not cover `gh`. Command: `gh pr checks 26 --repo rishmadaan/anyscribe`
- Whether a killed download resumes on Try again (traced from local_models.py docstrings only), and whether the reopened app keeps its port. Both need a real run: a real local setup, quit the tray mid-download, reopen, click Try again.
- Nothing was run beyond `bash -n install.sh` (ok) and read-only git and grep. No tests, builds, servers or installers.

Inspected:
- The packet: ask.md, spec.md (including the W6 amendment), target.md, lens.md, declined.md, fix-plan-r2.md, review-log.md, my round 2 report, and proof.md's round 3 fixer and lead sections.
- `git log 7ab1539..c07a65c`.
- The full source diff ae8f460..c07a65c: OnboardingWizard.tsx, FfmpegNotice.tsx, LocalSetupNotes.tsx, api/client.ts, install.ps1, BACKLOG.md, CHANGELOG.md, docs/user/troubleshooting.md and the journal.
- c07a65c's own diff.
- web/routes/local.py: state, status and the setup thread.
- Modal.tsx's scroll container.
- A grep of the committed bundle for the S13 and S12 strings.
- An empty-diff check on tailnet.py, app.py, the version files, .github and release.sh.

Screenshots viewed:
- fix2-s12-unreachable-1440
- fix2-s11-confirmation-1440
- fix2-after-restart-try-again-1440
- fix2-lock-progress-above-picker-390
- fix2-f4-restart-banner-1440

Not re-read this round:
- The installers apart from install.ps1's one changed box.
- W1 to W5, W7 and W8 code unchanged since round 2.
- findings.md and diagnosis-r2.md in full (I read the fix plan that binds them).
- The harness logs.

What I skipped: the raw harness logs and the unchanged items. The risk the owner must know: S12 tells a customer that quitting and reopening resumes the download, but it actually ends in a red failure line until they click Try again.

~~~~
