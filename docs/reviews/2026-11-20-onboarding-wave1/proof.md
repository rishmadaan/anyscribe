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

## Round 2 fixes, built in round 3 (one entry per finding)

Fixer: Claude Opus 5.5, Agent tool, branch `feat/onboarding-wave1-fix2` from `ae8f460`. Built to fix-plan-r2.md's rules (design A: hard lock, one owner, an exit only while anyscribe can't be reached). Raw evidence is outside the repo in `~/.review-runs/2026-11-20-onboarding-wave1/`:
- `logs/fix2-instruments/`: `harness.js` (the tab harness), `cases.js` (T1 to T13 and the two finding cases), `mutate.py` (the mutants), `serve.py` (serves those files to my tab and saves results), `results/*.json` (every run, saved by the page itself).
- `logs/fix2-results.txt`: every case and mutant, check by check. `logs/fix2-walk.txt`: the real walk.
- `screens/fix2-*.png`: each one opened and checked for content before it is cited here.

**Instruments.**
- Server: `HOME=~/.review-runs/2026-11-20-onboarding-wave1/fix2-home-a .venv/bin/python -m anyscribe ui --port 8494 --no-open --local-only`, in my own T3 preview tab. No engines were installed and nothing was downloaded.
- Harness: wraps the tab's `fetch` for four endpoints. Each has a queue of outcomes: real, real with fields overridden, fail (a network error), hang (until the page aborts it), a set HTTP answer, or any of these after a delay that honours the abort signal. The setup POST never reaches the server, and Finish is recorded but not sent. It logs every request: what was sent, when, how it settled, and how many status reads were in flight at once.
- Cases: each reloads the page, opens a fresh wizard through `window.openOnboarding()` (so the wizard's own mount read goes through the harness), drives it with DOM clicks, and asserts what is on screen. The checks cover the header line, Skip for now, S11, S12, the progress line, red alerts, Back, the start button, the checkbox, the picked card, any raw text (`409`, `Failed to fetch`, `"detail"`, `AbortError`) and the dismissed flag. Each case also checks the identity of the requests it sent. The real walk used real key presses and clicks.

**Final run, all on the committed bundle `index-6SAVCIl_.js`: 20 of 20 cases pass** (`results/final-all.json`).

### R2C1: a failed status read after the start unlocked a live download (should-fix)

Changed (`OnboardingWizard.tsx`, `client.ts`; commit `21f3178`):
- `handleStartSetup` sends only the start request, with the same 10 s limit as the status reads. It never reads status itself.
- Its catch sorts the outcomes. An HTTP answer other than 409 means the setup did not start: the step shows "anyscribe couldn't start the setup. Click Try again; if it fails again, {choose a cloud service instead | untick local transcription and go on}." and never the body.
- A 2xx, a 409, or no answer at all (network error, timeout) starts watching (rule 4).
- Watching ends in one place only: the status loop, on a good read that says `setup_running: false`. A failed or timed-out read only counts toward "unreachable" (rule 6).

Seen (each case is in `fix2-results.txt`):
- **T1** (start 200, the next status read fails, then running). 0.6 s after the click, with one failed read: the lock line, no Skip, no S12, Back disabled, "Setting up… [disabled]", and the checkbox `{checked: true, disabled: true}`. There is no red alert and no raw text. Then "Downloading Whisper Base… 25%". Escape and a backdrop click leave the dialog open, with no S11. Requests: `setup → answered 200`, `status → TypeError`, `status → answered 200`, and so on.
- **T1_500:** the same case with the failed read answered by HTTP 500. Same result.
- **T2** (409, then a failed read): locked at once, and no "409" anywhere. When the reads succeed, it adopts the other tab's model: the Whisper Small card is picked and the line reads "Downloading Whisper Small… 40%".
- **T3** (409, then not running and the model can run): moves on to Workspace, with no 409. Requests: `setup → answered 409`, then one status read `answered 200` that ended watching.
- **T4** (no answer, then running): watching and locked.
- **T4_hang** (the start hangs): for 3 s the controls are off and the button reads "Setting up…", with no lock line. The start is aborted at 10000 ms (`AbortError`), and then watching starts.
- **T4_notRunning** (no answer, then not running): the plain Try again sentence, unlocked.
- **T4_refused** (start 500): "anyscribe couldn't start the setup. Click Try again; …", with no "500" and no body. Not watching, and no status read follows.

Mutation (rule 6, `mutate.py M6`, the lead's form: a status read put back inside the start's `try`):
- **T1_500 fails.** One read answered 500 after an accepted start gives "anyscribe couldn't start the setup", Skip for now, and the checkbox enabled. Escape closes the dialog (`{"dialogOpen":false}`). This is R2C1 again.
- **T1 with a network failure survives M6.** The mutant's own read takes the failure, and the catch treats "no answer" as "may have started" (rule 4), so watching starts anyway. The lead's T1, as written, does not kill this mutant.
- A second mutant, M6b, puts the guard in the loop: a failed read ends watching. **T1 (network) fails**: the lock line is gone, Skip for now shows, the checkbox is enabled, the Download button is back, and Escape closes the dialog.
- **Restored** (`results/restored.json`): T1 and T1_500 pass again.

### R2C2: the stale lock after a reload near the end (should-fix)

Changed (commit `21f3178`):
- The wizard's own poll is deleted, and so is the lock its mount read used to set. That read now only routes to the local step: it sets the provider to local, turns local on, picks `setup_last_model` and opens the step. It is bounded too.
- The step is the lock's one writer, in one effect: `const report = (w) => onRunning(w); report(watch); return () => report("idle")`. Here `watch` is "unknown" while unreachable, "running" while watching, and "idle" otherwise. The wizard locks only on "running".
- `git grep -n "onRunning("` in the code: exactly one line, `ui/src/components/OnboardingWizard.tsx:714`. Every other hit is in `docs/reviews`.
- The step reads status until it has a first one (rule 10), and after that only while watching. A first read that says "not running" leaves it idle.

Seen:
- **T5** (the wizard's read says running, the step's says not running): no lock line, Skip for now shown, no progress line, Back enabled. Escape closes the dialog at once, with the flag unset. Requests: exactly two status reads (running, then not running), then none.
- **T5_late**: the same, with the wizard's read delayed 3 s so that it lands after the step's read. Same result.

Mutation (rule 1, `M1`: the wizard's mount read writes the lock again):
- **T5_late fails.** The lock line shows, there is no Skip, and Escape leaves the dialog open, while Back is enabled and "Download Whisper Base (140 MB)" is offered. That is a stale lock with nothing running.
- **T5 survives M1**, because the step reports its own state when it mounts, in the same commit, and so overwrites the wizard's write. Only the late ordering exposes a second writer.
- **Restored:** both pass.

### R2C3: silent and locked when reads fail; the log read coupled to the status read (should-fix)

Changed (commit `21f3178`):
- **One loop, one read at a time.** One effect runs one loop: a status read, then the log read only while watching, then `setTimeout(1500)` for the next tick. The next read is scheduled only after the previous one settles (rule 9).
- **Time limits.** Every status read, the start request, and the wizard's mount read go through `limited()`: `AbortController` with `setTimeout`, 10 s. The loop's cleanup aborts the read in flight and drops its answer.
- **Separate reads.** The log read is awaited separately and its failure is ignored, so a failed log read changes only the log panel (rule 8).
- **The unreachable state.** Two failed reads in a row set `unreachable`. S12 shows, and the step reports "unknown": the lock lifts, the lock line goes, and Skip for now returns. Reads continue, and the next good read clears it (rule 11).
- **Closing while unreachable.** Escape, a backdrop click or Skip for now opens S11 inside the wizard (rule 2). "Keep waiting" hides it. "Close setup" calls `dismiss(false)`, so the flag is not set (rule 3). S11 also hides by itself when the step leaves "unknown".
- **The progress line while unreachable** shows "Installing the local engines and downloading the model…", never a percent.
- **Exactly once (rule 7).** The read that ends watching sets `stop` and runs the completion branch once. Answers that land after a loop is replaced, or after the step unmounts, are dropped.

Seen:
- **T6** (the wizard's read says running, then the step's reads fail three times): after the second failure, S12 and Skip for now, with no lock line. Then it adopts: locked, S12 gone, "Downloading Whisper Base… 30%".
- **T7** (watching, then 30 s of failures):
  - S12, Skip for now, no lock line, and the progress line without a percent. Back stays disabled.
  - 20 reads were sent in the 30 s, one at a time (`maxInflight` 1 from the start on).
  - Escape opens S11. "Keep waiting" hides it.
  - When reads return, S12 clears and the lock and "60%" come back.
  - Unreachable again: Skip for now opens S11, and "Close setup" closes with the flag `null`.
- **T8** (stopped and runnable, every log read fails): moves on to Workspace. Every log request ended in a `TypeError`.
- **T9** (one read hangs, then one fails): still locked while it hangs.
  - The hung read ends `AbortError` after 10001 ms, and counts as a failure. With the next failure, S12 shows.
  - The next good read clears it and the wizard is locked again.
  - Never more than one status read in flight.
- **T10** (the ending read, then Next on Workspace): stays on All set 5 s later. No status read was sent after the ending read.
- **T11** (a read sent before Download is delayed 3 s and carries `setup_error: "OLD ERROR…"`): that read ends `AbortError` 102 ms later, when the start settled and the loop was replaced. The setup then shows as watched and locked, with no old error on screen.
- **T12** (a restarted server: not running, no error, no outcome; only Tiny can run): "Setup finished, but Whisper Base can't run yet. Click Try again; …", the button "Try again", unlocked, never All set.
- **T13**:
  - Escape while reachable: nothing happens.
  - Unreachable: Escape opens S11, "Keep waiting" hides it, and a backdrop click opens it again.
  - "Close setup" closes with the flag unset.
  - Then Settings, then Run setup wizard: the wizard reopens on Local transcription, locked, with "Downloading Whisper Base… 50%".

Mutations:
- **Rule 8** (`M8`, `Promise.all` back): T8 fails. The status said stopped and runnable, but every tick was thrown away with the failed log read. The step stays on "Setting up…" and shows S12 after two such ticks.
- **Rule 9** (`M9`, no time limit): T9 fails. The hung read stays `pending`, no further status read is ever sent, and the screen stays locked and silent on "Downloading Whisper Base… 20%". This is R2C3 again.
- **Restored:** T8 and T9 pass (`results/restored.json`), and `npm run build` gives back the same bundle name, `index-6SAVCIl_.js`.

**The real walk** (`logs/fix2-walk.txt`), on the cloud path with local ticked:
- The harness made the setup and the "running at 37%" state, on top of the real server's status answers.
- I stopped my server by its pid (after reading its command line). Two real `ERR_CONNECTION_REFUSED` status reads, and S12 showed (`fix2-s12-unreachable-1440.png`).
- A real Escape key press opened S11 (`fix2-s11-confirmation-1440.png`). A real click on "Keep waiting" hid it.
- I restarted the server on the same port. The next good read cleared S12 and restored the lock line and "37%" (`fix2-after-restart-locked-1440.png`).
- With the override off, the restarted server's own answer ended watching: running False, error None, outcome None, engines not installed. The step showed the Try again sentence, never "ready" (`fix2-after-restart-try-again-1440.png`).

### R2F2: progress below the fold (nit)

Changed (commit `6a375b3`, a pure move, 21 lines each way): the restart banner, the setup error, the "missing" alert and the progress/log block now render above the model picker.

Seen:
- `fix2-lock-progress-above-picker-1440.png`: the header lock line, the checkbox, then "Downloading Whisper Base… 37%", then Help me choose and the cards.
- `fix2-lock-progress-above-picker-390.png`: the same order at 390 px. The progress line is at y 261 of 844.

### R2F3: three "until the download finishes" lines (nit)

Changed:
- The header line is S13, "Skip, Back and the local checkbox are off until setup finishes." It landed in `21f3178`, because that line is the lock's own.
- Commit `d8619d0` removes the checkbox label's "(stays on until the download finishes)" and the "Back is off until the download finishes." line.

Seen: `git grep -n "until the download finishes\|until setup finishes" -- ui/src` gives one hit, the header. On screen, T1 reads the header equal to S13.

### R2F1: Windows "Check again" can't see a winget install (nit)

Changed (commit `36abf46`):
- **`FfmpegNotice.tsx`, Windows:** "anyscribe needs ffmpeg, a free audio tool, to read audio and video. Install it with the command below. Then quit anyscribe from the tray (the icon near the clock) and open it again from the Start menu: Check again can't see a new install before that." The separate Windows "If it still isn't found…" line is gone. Mac and Linux keep "…then click Check again."
- **`install.ps1`, desktop route:** "…Install it with: winget install Gyan.FFmpeg, then quit anyscribe from the tray (the icon near the clock) and open it again." The route without desktop mode is unchanged (it opens a new PowerShell window).
- **Sibling:** the wizard's hint under the buttons, "Install ffmpeg first (see above), then click Check again.", repeated the dead instruction on Windows. It is now "Install ffmpeg first (see above)." on every OS.
- **Docs:** `docs/user/troubleshooting.md` now says "On a Mac or Linux… click Check again". Its Windows bullet comes first: Check again can't see a new install, so quit from the tray and reopen. `landing/docs` regenerated.

Seen (case **F1**, with the user agent stubbed in the tab):
- Windows: the notice holds the new text and `winget install Gyan.FFmpeg`, without "then click Check again" or "If it still isn't found".
- The hint reads "Install ffmpeg first (see above)."
- Linux, with the real agent: "Install it with the command below, then click Check again." and `sudo apt install ffmpeg`, with no "tray".

Sibling grep: `git grep -n "then click Check again\|click \*\*Check again\*\*"` outside docs/reviews and the generated files finds two lines, both Mac and Linux only: `FfmpegNotice.tsx:78` (the non-Windows branch) and `troubleshooting.md:114` ("On a Mac or Linux, … then click **Check again**"). The installer's strings have no test (`tests/` has no match for "open anyscribe again" or "quit anyscribe"). Not run on Windows.

### R2F4: the restart case showed two restart messages (nit)

Changed (commit `f2435d7`):
- `missingPart` returns `null` in the restart case, so there is no red alert and the setup button does not read "Try again".
- `RestartBanner` takes optional `children`. The wizard passes "Restart anyscribe, then open the setup wizard again (Settings, then Run setup wizard); the download is kept."
- Settings and LocalSetupModal render it without children, so they are unchanged.

Seen:
- **Case F4** (setup ends with `restart_needed` true and the engine not loadable): no red alert, the banner text plus that sentence, no "then continue", and the button not "Try again".
- Screenshot `fix2-f4-restart-banner-1440.png`.

### Records (fix-plan-r2.md "Tests and proof")

Commit `5527913`:
- CHANGELOG's W6 bullet adds the unreachable exit.
- BACKLOG: the W6 line describes the one owner, the 10 s limit and the confirmation. Three wave 2 lines, in the lead's words: the way out of a slow download, LocalSetupModal's same lock shape, and the `beforeunload` guard.
- The journal: a paragraph on why the lock took three rounds and the shape that holds, plus two decision lines (the hard lock kept, and the Windows ffmpeg wording).
- `docs/user/troubleshooting.md`: a new entry keyed on S12.
- `landing/docs` regenerated.

### Choices I made where the rules left room, and where I read a rule differently

- **Rule 2 against rules 1 and 11.** Rule 2 says the wizard is locked only while "the last status read succeeded". Rules 1 and 11 make the lock `watching && !unreachable`, with unreachable after two failures. I built rules 1 and 11, so the wizard stays locked after one failed read; T1 checks exactly that. Unlocking on every single failed read would make the exit flicker on any slow tick.
- **`onRunning` carries three values, not a boolean.** It reports idle, running or unknown, because the wizard must know "unknown" to send Escape, the backdrop and Skip to S11. "running" is exactly `watching && !unreachable`.
- **While the start request is in flight** (normally under a second; at most 10 s if it hangs), watching has not started (rule 4), so the wizard is not locked. The step's controls are disabled ("Setting up…"), so the step cannot be left. Escape during that moment closes the wizard, with the download maybe starting in the background. That is the same outcome as S11's "Close setup". Locking during the start too would be one more term (`starting`) in the report. I left it out to follow rule 1 literally.
- **`setup_error`**, the server's own description of a failed setup, still shows in red with the log opened, unchanged since round 0. I read rule 12 as covering the fetch-layer text (the 409 body, "Failed to fetch"), which can no longer reach the screen (no case found any). A plain message for every setup error is wave 2's "plain error messages" item.
- **The wizard's single mount read** can be in flight at the same time as the step's first read (T5_late's requests show both). The step's own reads never overlap.
- **S13 names "the local checkbox"** on the "On this computer" path too, where there is no checkbox. It is a fixed string, so I kept it.

### Not proven

- Windows and Mac themselves. R2F1's wording was seen with a stubbed user agent, and install.ps1's box only by reading it; PowerShell was not run this round.
- A real download. No engines and no model were installed: disk was 1.8 GB free. The running state came from the harness on top of real status answers, and the stop and restart were real.
- How long a status read takes on a slow laptop during pip install. Here real reads took 0.24 to 0.44 s. If two reads in a row ever pass 10 s, S12 shows and the wizard can close; it does not unlock silently.
- Screen-reader behaviour of the S11 `alertdialog` and the S12 `status`.

### Final checks (tip of this branch)

- `.venv/bin/ruff check src tests scripts`: All checks passed!
- `.venv/bin/python -m pytest -q`: 931 passed, 6 skipped.
- `cd ui && npm run lint && npm run build`: lint clean, and the build emits `index-6SAVCIl_.js`, the bundle committed in `18613cb`.
- `python3 scripts/build-docs.py && python3 scripts/check-docs.py`: exit 0.
- `bash -n install.sh`: ok.
- `git grep -n "onRunning("`: one code hit, `ui/src/components/OnboardingWizard.tsx:714`; the rest are in `docs/reviews`.

## Lead-made changes before the round 3 re-check (2 lines of source, both flagged by the round 3 fixer)

- **Lock from the click.** `OnboardingWizard.tsx`: the lock value uses `busy` (`watching || starting`) instead of `watching`, so Escape, a backdrop click and Skip cannot close the wizard while the start request is in flight (the fixer's "short gap before the lock"; up to the 10 s limit if the request hangs).
  - New case TG (`~/.review-runs/2026-11-20-onboarding-wave1/logs/fix2-instruments/lead-gap.js`): the start answers after 3 s; Escape and a backdrop click at 0.8 s. Guarded: PASS (dialog open on Local transcription, no Skip; locked line after the answer). Mutant (back to `watching`): FAIL, `{"dialogOpen":false}` during the slow start. Restored: PASS.
  - Regression: the fixer's 17 cases on the final bundle (`index-2r9Aqod2.js`, results `results/lead-final.json`): 16 PASS. T4_hang FAILS only on its old expectations: "no lock line yet" while the start hangs (now intended), and it waited for the lock line as its signal that the start had been aborted, which now appears at the click. Replaced by T4v2 (same file): locked while the start hangs, Escape and backdrop do nothing, the start is aborted at the limit (AbortError, about 10 s), then watching with progress, still locked: PASS (`results/lead-T4v2-TG.json`).
- **Lock line wording (S13).** "Skip, Back and the local checkbox are off until setup finishes." named a checkbox that does not exist on the "On this computer" path; now "Skip and Back are off until setup finishes." (`git grep` finds no other copy outside docs/reviews and the packet's fix plan).
- `cd ui && npm run lint && npm run build`: lint clean; bundle `index-2r9Aqod2.js` committed.
