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
