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
