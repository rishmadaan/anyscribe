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
