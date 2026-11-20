# Proof: onboarding wave 1, integration branch feat/onboarding-wave1, 2026-11-20

Two builders worked in parallel on disjoint files; their full proofs are beside this file and are part of this proof:

- `proof-install.md`: builder INSTALL (Claude Opus 5.5, Agent tool, lead-made worktree; W1, W2, W3 installer half, W7, docs and records). Branch `feat/onboarding-wave1-install`, tip `1b21839`.
- `proof-app.md`: builder APP (Claude Opus 5.5, Agent tool, lead-made worktree; W3 wizard half, W4, W5, W6, W8). Branch `feat/onboarding-wave1-app`, tip `9bd08b7`.

Lane note: the T3 child lane could not run (registering the code repo as a T3 project was refused: "Changing projects or environment settings needs a live full-access/default calling thread"), so the lead made the worktrees with `git worktree add` and ran the builders through the Agent tool, the lane this repo used on 2026-11-19.

## Integration (lead)

- Merged INSTALL (`d92be63`) then APP (`53356fd`) into `feat/onboarding-wave1`; no conflicts (disjoint files).
- Lead-made change (wording only, both builders flagged it): S3e said "Saved, not checked" while the wizard saves the key only at Finish. Reworded to "Not checked yet: Sarvam has no way to check a key in advance. It will be checked on your first transcript." in `web/routes/config.py`, its test, `docs/user/troubleshooting.md`, `docs/user/getting-started.md`, the skill's troubleshooting reference, CHANGELOG, the journal entry and `_index.md`; `landing/docs` regenerated. 10 files, 10 lines each way.

## What was run on the integrated tree (after the lead change)

- `ruff check src tests scripts`: All checks passed!
- `pytest -q`: 926 passed, 6 skipped (the APP builder's 927/5 included one local-engine test its venv could run; this fresh venv has no local engines).
- `cd ui && npm ci && npm run lint && npm run build`: lint clean; build emits `index-HNoFjoKn.js`, identical to the committed bundle; `git status` shows no change under `src/anyscribe/web/static`.
- `python scripts/build-docs.py` then `python scripts/check-docs.py`: exit 0.
- `bash -n install.sh`: ok.

## Not proven anywhere in this round

- A real Mac (W1 was proven with Homebrew's Linux installer, which has the same non-interactive check) and real Windows / PowerShell 5.1 (W3 and W7 Windows parts were run in Linux PowerShell 7 only; winget and the registry PATH refresh could not run there).
- The desktop-mode "click the app" box after a real desktop install (shown with `--dry-run` only; containers have no display).

## Round 1 fixes (one entry per finding)

Fixer: Claude Opus 5.5, Agent tool, branch `feat/onboarding-wave1-fix1` from `37f066c`. Raw logs and test instruments are in `~/.review-runs/2026-11-20-onboarding-wave1/logs/` (`fix1-*`, `fix1-instruments/`), screenshots in `screens/fix1-*.png`. Walks ran on a dashboard from this worktree (`HOME=<throwaway> .venv/bin/python -m anyscribe ui --port 8493 --no-open --local-only`, PATH = the venv plus a folder holding ffmpeg, ffprobe, uv, python3, node) in my own T3 preview tab.

Instruments, named once so each entry can point at them:
- **Slow connection.** The first real setup (engines plus Whisper Base) finished in about 10 s, too fast to walk. For every later real download the server also had `HTTPS_PROXY=http://127.0.0.1:8499` (`slowproxy.py`, a CONNECT proxy at about 1 MB/s) and `HF_HUB_DISABLE_XET=1`, and Base was deleted from the throwaway cache before each run. The server code is untouched; the download is real, just slower.
- **Tab harness** (`harness.js`, `c1-scenario.js`). For the mutation runs, the tab's `fetch` is wrapped to fake a few answers: a delayed "accepted" key check, `POST /api/local/setup` as started or 409, `/api/local/status` with `setup_running`, `setup_last_model` and per-model `runnable` overridden, and Finish recorded without being sent. Everything else is the real server.
- **Clicks.** `preview_act` clicks on the local checkbox timed out even when it was enabled (mutant M1 below), so a timeout is never cited as proof that a control is disabled. State is read from the DOM (`disabled`, `checked`), and mutation runs use DOM `.click()`. Escape and the backdrop click are real `preview_act` input.
- The machine's load average was about 41 during the walks. `/api/local/status` took about 1 s.

### C1: the download lock (blocker)

Changed (`ui/src/components/OnboardingWizard.tsx`):
- The `enable-local` checkbox is disabled while a setup runs. Its label adds "(stays on until the download finishes)".
- A line under the buttons reads "Back is off until the download finishes."; Back was already disabled.
- "Skip, next" shows only while local is off, and local cannot be turned off during a setup, so it never shows then. I gave it no `disabled` of its own: that guard could not be reached, so it was an equivalent mutant.
- The lock now follows the server. The step only ever turns `onRunning` on, and turns it off when its poll sees `setup_running: false` (or when its own start failed). The unmount cleanup that unlocked the wizard is gone. While the local step is not showing, the wizard polls `/api/local/status` itself and unlocks only on `setup_running: false`. A wizard opened on a running setup locks at once.
- On mount the step turns local on for a setup that is already running, so the person sees what is locking them.
- The first draft polled status from both the step and the wizard. Under this machine's load that queued the tab's requests, so the committed version polls once.

Ran:
- The real walk on the final code (`fix1-c1-walk.txt`, "FINAL BUILD real walk R1"). Cloud provider (sargam), local turned on as a backup, Whisper Base download started.
- Three seconds in: checkbox `{"checked":true,"disabled":true}`; buttons `["Back [disabled]","Setting up… [disabled]"]`; header "Skip is off until the download finishes".
- A click on the checkbox changed nothing. "Skip, next" and "Skip for now" were both absent.
- Escape, then a click at (110, 450) on the backdrop (`role=presentation`): the dialog stayed open at 8.9%.
- Workspace cannot be reached during the download. After the download the wizard moved on by itself, and Escape on Workspace closed it.
- Screenshot `fix1-c1-locked-during-download-1440.png`, from the same walk on the commit candidate before the polling rework.

Mutation tests (`fix1-c1-walk.txt`, harness faking a running Whisper Small setup):
- **Guarded:** after a checkbox click it stays `{"checked":true,"disabled":true}`, with no Skip of either kind. Escape leaves the dialog open on Local transcription.
- **M1, checkbox guard removed:** the click unticks local and the download panel vanishes. "Skip, next" leads to Workspace while the server still runs; this is the reviewer's route. The server-following lock still holds there: the header reads "Skip is off…", Escape 3 s later leaves the dialog open, and "Skip for now" returns only after the fake server stops.
- **M1 + M3, also the round-0 lock** (`onRunning(settingUp)` with cleanup `onRunning(false)`, no wizard poll): Workspace shows "Skip for now" while `setup_running` is true. Clicking it gives `{"dialogOpen":false}` with the server still running. C1 reproduced.
- **Restored:** identical to the guarded run.

### C2: adopting a running setup's model (blocker)

Changed (`OnboardingWizard.tsx`):
- **Adoption.** When the step finds a running setup on mount, or gets a 409, it sets the wizard's `localModel` to `setup_last_model` through a stable `selectSize` callback. The picker then marks that card, and the progress line already names it.
- **The runnable check.** The step moves on only if `s.set_up` holds and the model being summarised (`selected`, which is the wizard's `localModel`) is `runnable` in `s.models`. Otherwise it says which model cannot run (F10's wording).
- **Why All set needs no check of its own.** With local on, the only way forward from the local step is this poll: the setup button leads into it, and "Skip, next" needs local off. So All set can show "· ready" only for a model that passed the check.

Ran, the real walk on the final code (`fix1-c2-walk.txt`):
- On this computer: the default pick was Parakeet v3. I picked Whisper Base and clicked Download.
- 5 s in, I reloaded. The wizard reopened on Local transcription with Whisper Base selected, "Downloading Whisper Base… 8.9%", Back and the setup button disabled, Skip off, and no "409" or "already in progress" anywhere.
- When the download finished it moved on by itself. All set read "Model: Whisper Base · ready".
- After Finish: `setup_running` false, nothing downloading or queued, `pending_default` null, and the setup log unchanged at 3 lines, so no new setup or download ran. `config.yaml` has `provider: local`, `local_model: base`.
- Screenshots `fix1-c2-after-reload-1440.png` and `fix1-c2-all-set-1440.png`.

Mutation tests (`fix1-c2-mutants.txt`). I picked Whisper Small, then "another tab" started Base and the wizard's Download got a 409. Scenario A: Base is runnable at the end. Scenario B: Base is not, and Tiny is.
- **Guarded A:** the selection switches to Whisper Base. All set reads "Whisper Base · ready", and Finish sends `local_model: base`.
- **MA, adoption removed, scenario A:** the selection stays Whisper Small. The runnable check stops it with "Setup finished, but Whisper Small can't run yet. …"; no All set.
- **MB, runnable check removed, scenario B:** All set reads "Whisper Base · ready" while only Tiny can run.
- **MA + MB, the round-0 code, scenario A:** All set reads "Whisper Small · ready", and Finish sends `local_model: small`, a model never downloaded. C2 reproduced.
- **Restored:** A gives "Whisper Base · ready" and `local_model: base`. B stays on the step with "Setup finished, but Whisper Base can't run yet. Click Try again; if it fails again, choose a cloud service instead."

### C3: a key check's late answer (should-fix)

Changed: the lead's simplest form. While a check runs, the key field is `readOnly` (it keeps focus, dimmed), and Back and "Use this key anyway" are disabled. Next and Test key were already disabled.

Mutation test (`fix1-c3-walk.txt`). Groq, key A, Next; the harness answers "accepted" after 9 s.
- **Guarded:** field `readOnly` and Back disabled. Typing "_EDITED_B" was refused ("requires an editable selector"). After the answer the wizard went on with the key that was checked (`keysSent ["gsk_fake_KEY_A_0000"]`, carried key the same).
- **Mutant (both removed):** "_EDITED_B" was typed. The answer for A moved the wizard on carrying `gsk_fake_KEY_A_0000_EDITED_B`, which was never sent to the check. In a second run, Back during the check went to the provider step, and the late answer pulled the wizard forward to Local transcription.
- **Restored:** the guarded results again. A click on Back during the check left the title unchanged.

### C4: install.ps1 re-checks ffmpeg (should-fix)

Changed: `$null = Test-FfmpegFound` runs right after `Install-Anyscribe`, whose `Refresh-Path` and `Fix-Path` are the last PATH changes. It runs before desktop mode and `Write-Result`, so the box uses what is true then.

Ran: the official `mcr.microsoft.com/powershell:latest` image, pulled for this and removed afterwards by ID (`810c4f1e0c9d`); log `fix1-c4-f8-ps.log`, harness `fix1-instruments/ps-main.ps1`.
- The harness runs the installer's real main `try` block and every real function it calls. Only Python, the JS runtime, yt-dlp and the registry are stood in for.
- ffmpeg is found at first in a session-only PATH entry. `Refresh-Path` then reloads a "registry" PATH without it, as Windows would.
- CI's parser check: 0 errors.

Results:
- **Fixed:** "anyscribe is installed, but can't transcribe yet", and `FfmpegOk at the end = False`.
- **Mutant (re-check removed):** "anyscribe is ready!", and `FfmpegOk = True`.
- **Neighbour, the registry PATH has ffmpeg:** "anyscribe is ready!".
- **Limit:** on Linux, the real `Refresh-Path` sets `$env:Path`, which Linux treats as a different variable from `PATH`, so the stub sets `PATH`. Windows itself and PowerShell 5.1 were not run.

### C5: parentheses in link URLs (nit)

Changed (`TranscriptBody.tsx`): a link destination is now `((?:[^()\s]|\([^()\s]*\))+)`, which allows one level of balanced parentheses. The http(s)-only check and React-only rendering are unchanged. The shortcut comment now names the remaining limit (deeper nesting is not a link).

Ran: the round-0 renderer self-check, with six C5 assertions added (`fix1-instruments/render-c5-assertions.mjs`), compiled with the repo's `tsc`.
- `audio_(final).mp3` is one link with no stray `.mp3)`.
- A Wikipedia-style URL followed by text works, two links sit on one line, and `(see [a](…))` keeps its outer ")".
- An unbalanced `a_(b` stays plain text.
- `javascript:alert(1)` shows its label only.

Results:
- Mutant (the old `([^)\s]+)`): fails with `href="https://example.com/audio_(final"` followed by the text `.mp3)`.
- Restored: "render self-check: all assertions passed". The 20 round-0 assertions pass too (`fix1-c5-render.txt`).

### F3: screenshot retakes (should-fix)

Retaken on the final code, in the C1 real walk:
- I removed the ffmpeg and ffprobe links from the server's PATH at 8.9% of the Base download. When it ended, the server said `set_up: False, setup_error: None, setup_outcome: set_up`.
- The step showed "One more thing: ffmpeg", the S4 body, `sudo apt install ffmpeg` and Check again. "Installed — continue" was disabled, with "Install ffmpeg first (see above), then click Check again."
- Screenshots `fix1-f3-ffmpeg-after-setup-1440.png` (the notice; I opened it and it is not blank) and `fix1-f3-ffmpeg-after-setup-bottom-1440.png` (the bottom of the dialog).
- After I restored the links, Check again cleared the notice, and "Installed — continue" went on to Workspace.
- The Sarvam key step, with the new wording and F9's early note: `fix1-f9-sarvam-key-1440.png`.

### F4: BACKLOG wording (nit)

Changed: BACKLOG.md's W5 line says "Not checked yet". I also added the lead's wave 2 line: "Settings' Set up local transcription window ends silently when ffmpeg is missing (LocalSetupModal.tsx); give it the wizard's ffmpeg notice."

Checked: `git grep -i "saved, not checked"` outside `docs/reviews` finds nothing.

### F5: "is prepaid" only where true (nit)

Changed: `no_credit_message` keeps "{Provider} is prepaid: add credit[ at <billing>] and try again" for OpenAI and OpenRouter. Every other provider gets "Your {Provider} account has no credit. Add credit or check your plan, then try again, or use the free option instead (…)".

Docs updated:
- `docs/user/troubleshooting.md`: the full texts, and its fix line now says "Add credit, or check your plan".
- The skill's troubleshooting reference.
- `landing/docs` regenerated.

Tests: the Groq test now asserts the full new text, and a new parametrized test covers Groq, Deepgram, ElevenLabs and Sarvam (no "prepaid").

Mutation (`fix1-f5-mutant.txt`):
- Split removed, so every provider is prepaid: 5 failed. The Groq text and the four providers.
- Only OpenAI prepaid: 1 failed, the OpenRouter text.
- Restored: 19 passed.

Siblings: `git grep -i "is prepaid"`. The remaining hits are the OpenAI key-step note, docs about OpenAI, and the tests.

### F6: the pipx line (nit)

Changed: `install.sh` now prints "If you type anyscribe in a terminal later and it isn't found, open a new window; if it still isn't, run: pipx ensurepath". It still contains the substring `test_install_sh.py` requires.

Ran: a dry run with OS=linux and OS=macos, pipx and desktop mode (`fix1-f6-f7-box.txt`). The line shows under the box. `tests/test_install_sh.py`: 31 passed.

### F7: the Mac click-the-app line (nit)

Changed: on a Mac the box reads "Open anyscribe: press Cmd and Space, type anyscribe, press Return. Your dashboard should already be open in your browser." Linux keeps "(in your app menu)", and install.ps1 keeps "(in your Start menu)". `app_place()` had no other caller, so I removed it.

Docs: CHANGELOG, getting-started and the journal's decision line now say this.

New test `test_mac_box_says_spotlight_and_stays_aligned`: the Mac box holds the sentence and every line of the box is one width.

Mutants (`fix1-f7-mutant.txt`):
- "press ⌘ and Space" fails on the text.
- The right words plus a ⌘ glyph fail on width, `{58, 60}`: printf pads by bytes.
- Restored: passes.

### F8: Windows without desktop mode, ffmpeg missing (nit)

Changed: on the non-desktop route (`-NoDesktop` or a failed desktop step), the yellow box reads "ffmpeg, a free audio tool, is missing. Install it with: winget install Gyan.FFmpeg, then open a new PowerShell window and type: anyscribe ui". The box no longer carries the "Type: anyscribe ui" paragraph meant for this window.
- In the rare case where `anyscribe` isn't found in this window either, the fallback line underneath gets the header "If anyscribe isn't found in the new window, type:". Without it the line would have lost the paragraph that explained it.
- The desktop route is unchanged.
- troubleshooting.md's Windows bullet says the same.

Ran: the same container (`fix1-c4-f8-ps.log`, cases 4, 4b and 5) shows the new box. The neighbour case (ffmpeg kept, no desktop) still shows "anyscribe is installed!".

### F9: Sarvam's key step (nit)

Changed: with Sarvam picked, the key step shows the amber note "Not checked yet: Sarvam has no way to check a key in advance. It will be checked on your first transcript." from the start. Next goes straight on without a check, and Test key is hidden (it could only repeat the note). Docs updated (getting-started, troubleshooting, CHANGELOG), and `landing/docs` regenerated.

Walked (`fix1-c3-walk.txt`, F9 section):
- Before typing, the note was there (class `text-amber`), Test key was absent, and Next was disabled with the field empty.
- After a fake key, one press of Next went to Local transcription, and no key was sent to the test endpoint.
- Screenshot `fix1-f9-sarvam-key-1440.png`.

### F10: plain words when setup ends but the model can't run (nit)

Changed: `missingPart()` now says one of three things:
- Restart case: "Setup finished, but anyscribe needs a restart before it can transcribe on this computer. Quit anyscribe and open it again, then continue."
- Engine missing: "A part anyscribe needs to transcribe on this computer didn't install. Click Try again; if it fails again, choose a cloud service instead."
- Model missing: "Setup finished, but {model} can't run yet. Click Try again; …".
- On the cloud path the ending is "untick local transcription and go on".
- The setup button reads "Try again" while such a message shows, so the words match a button.
- No package names and no "install log". No doc quoted the old sentences (grep).

Seen: the model sentence in C2's restored scenario B, with buttons `["Back","Try again"]`. The engine and restart sentences were not seen on screen. They need an engine that fails to install or load.

### Not proven, and instrument limits

- **Not proven:** Windows itself (C4, F8 ran in PowerShell 7 on Linux), and a real Mac (F7's box was shown by dry run). F10's engine and restart sentences were not seen. C2's 409 path ran through the harness; its reload path ran for real.
- **Instrument limit:** the walks used a slow proxy and, for mutations, a tab harness (above). The two C1 and C2 real walks used neither override: the download, status and Finish were real.

### Final checks (tip of the fix branch, engines uninstalled again)

- `.venv/bin/ruff check src tests scripts`: All checks passed!
- `.venv/bin/python -m pytest -q`: 931 passed, 6 skipped. That is the 926 / 6 baseline plus 5 new tests: 4 parametrized no-credit cases and the Mac box test.
- `cd ui && npm run lint && npm run build`: lint clean. The build emits `index-gtgg6_kN.js`, the bundle already committed with F10, so nothing changed under `src/anyscribe/web/static`.
- `python3 scripts/build-docs.py && python3 scripts/check-docs.py`: exit 0, and `landing/docs` is unchanged against the commits.
- `bash -n install.sh`: ok.
- Cleanup:
  - The walk's local setup had installed 9 packages into `.venv`: av, ctranslate2, faster-whisper, flatbuffers, numpy, onnx-asr, onnxruntime, protobuf, tokenizers. I uninstalled them with `uv pip uninstall`, and `uv pip check` reports all compatible.
  - Deleted: the throwaway home (with the Base model and the uv cache, 679 MB), the PATH folder, and the PowerShell image (by ID).
  - Stopped my server (8493) and proxy (8499) by pid, after reading their command lines, and closed my preview tab.
