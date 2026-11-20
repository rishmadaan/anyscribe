# Spec: onboarding wave 1, "let people in"

Who it is for: a non-technical customer (content creator or student, usually on a Mac or Windows laptop, never opened a terminal, no API keys, often Hindi or Hinglish audio). Wave 1 removes the walls that stop them before or during setup, and makes the finished transcript readable. Nothing else: waves 2 and 3 are listed at the end so nobody builds them by accident.

Two builders work in parallel on disjoint files. Builder **INSTALL** owns installers, website, every doc and record file. Builder **APP** owns Python and dashboard code, tests and the rebuilt static bundle. Neither edits the other's files. Copy shared between them is fixed below (section "Fixed strings") so both use the same words.

## Items

### W1. Mac without Homebrew: the installer must not die silently (INSTALL)

Today `install.sh` line 145 runs Homebrew's installer as `/bin/bash -c "$(curl ... Homebrew/install/HEAD/install.sh)"`. Under `curl ... | bash`, stdin is the pipe, so Homebrew goes non-interactive, checks `sudo -n`, refuses ("Insufficient permissions..." / "Need sudo access"), and `set -e` ends the anyscribe installer with no message.

- Connect Homebrew to the keyboard: `... </dev/tty`.
- If Homebrew still fails (non-zero exit, or no `brew` afterwards), stop with string S6, not a bare exit.
- Keep the existing warning about the password and the 10 to 20 minute wait.
- Proof: reproduce in Docker the way the audit did (Homebrew's Linux branch has the same non-interactive check): the old line piped through `curl | bash` refuses; the new line asks for the password and proceeds. Also `bash -n install.sh` and `shellcheck` if available.

### W2. Copyable Windows command, and how to open a terminal (INSTALL)

`landing/index.html` hero install card (around lines 1452 to 1470) is headed `install · macos & linux`, has a copy button only for the `curl` line, and shows Windows as a shortened `irm https://…/install.ps1 | iex` with no copy button. Nothing says how to open Terminal or PowerShell.

- Two clearly labelled options, Mac (and Linux) and Windows, each with the FULL command and its own working copy button. Tabs or two stacked blocks: builder's call, matching the page's existing style. The full Windows line already exists lower on the page (around line 1981) and a copy-button pattern exists there to reuse.
- Under each, one line from S9 on how to open the terminal and paste.
- `docs/user/getting-started.md` (around line 41) says "Command Prompt / PowerShell (Windows)": Command Prompt cannot run `irm`; make it PowerShell / Terminal only, with the same how-to-open line.
- Do NOT redesign the rest of the hero or change other copy on the first screen (that is wave 3), except where it directly contradicts the new lines.
- Proof: open the page in a browser at 1440, about 1000 and 390 px wide; click both copy buttons and show the clipboard holds the full, exact command; screenshot each width.

### W3. ffmpeg missing: say so, never "ready" (INSTALL for installers, APP for the wizard)

INSTALL:
- `install.ps1` ffmpeg step (lines 117 to 160): after a winget or Chocolatey install, refresh `$env:Path` from the Machine and User registry values before testing for ffmpeg (a fresh winget install is otherwise invisible to the current session and reported as a failure). Track whether ffmpeg ended up available. If not, the final banner must not say "anyscribe is ready!": print S5 (Windows form) instead.
- `install.sh`: check whether any path can reach the end with ffmpeg missing; if so, same rule (S5, Mac or Linux form). If none can, say so in proof.

APP:
- The setup wizard's local step (`ui/src/components/OnboardingWizard.tsx`, the polling effect around lines 560 to 585) has no branch for "setup stopped, no error, not set up". `set_up` requires ffmpeg (`core/local_setup.py` around line 328), so a missing ffmpeg leaves a silent loop. Fix both ends:
  - Before download: read `ffmpeg_ok` from `/api/local/status` (already in the payload). When false, show notice S4 with the command for the person's OS (reuse `FFMPEG_COMMANDS` from `SetupBanner.tsx`, moving it to a shared place if needed) and a "Check again" button that re-reads status; the Download button stays disabled with a reason until ffmpeg is found.
  - After setup: when polling ends with neither `setup_error` nor `set_up`, show what is missing (ffmpeg via S4, or otherwise a plain sentence naming the missing part from the status payload) instead of the "Installed, continue" loop.
- Proof: run the dashboard with ffmpeg removed from the server's PATH and walk it (see Proof).

### W4. OpenAI "no credit" (APP; docs by INSTALL)

`core/errors.py` maps every 429 to `RateLimitError` ("Rate limited by openai. Wait a moment and retry..."), which `with_retry` retries. OpenAI returns 429 with `"code": "insufficient_quota"` (also `"type": "insufficient_quota"`) for an account with no credit.

- In `classify_api_error`, a 429 (any provider) whose body contains `insufficient_quota` becomes a NON-retryable error with user message S1 (provider name filled in; the billing URL only for OpenAI). Ordinary 429s stay `RateLimitError` and keep retrying.
- Check how providers raise and whether OpenRouter's out-of-credit answer (HTTP 402) is already handled; if 402 is unhandled, map it to the same no-credit message. Do not change any other error class.
- Web wizard OpenAI key step and the terminal `anyscribe onboard` OpenAI key prompt (`cli/onboard.py` around lines 666 to 674): add S2.
- Proof: unit tests for insufficient_quota (not retried, S1 text) and plain 429 (still RateLimitError, still retried); mutation test the new branch.

### W5. Real key checks (APP; docs by INSTALL)

`web/routes/config.py` `test_provider` (lines 225 to 360): Groq returns `"API key is set for groq"` and Sarvam `"API key is set (no validation endpoint)"` without calling anything; OpenRouter calls `/api/v1/models`, which answers 200 with no key at all, so any text is "valid".

- Groq: a real authenticated call (OpenAI-compatible `https://api.groq.com/openai/v1/models`, Bearer key).
- OpenRouter: an endpoint that requires the key (OpenRouter documents a key-info endpoint, `GET /api/v1/key`; verify the exact path and that it returns 401 without a valid key before relying on it).
- Sarvam: no check exists; return a distinct "not checked" result (for example `success: true, checked: false`) with S3e, and render it in amber, not as a green success.
- All providers: result messages use S3a to S3d (plain words, provider's display name, no em dash, no raw status line as the headline).
- Wizard key step: pressing Next runs the check if it has not run for the current text. Success continues. A refusal stays on the step showing the message, with a quieter "Use this key anyway" action. A network failure or timeout shows S3d and lets them continue.
- Keep: the typed key is tested without being saved (existing behaviour); keys are never logged or echoed.
- Proof: tests with the HTTP calls mocked the way the repo's existing tests mock HTTP (no new test dependency); mutation test the Groq and OpenRouter branches; one live negative check per provider with an obviously fake key, showing the refusal. Never use a real key.

### W6. Lock the wizard during the download (APP)

`OnboardingWizard.tsx` passes `disableClose={saving}` only, so Escape or a click outside closes the wizard mid-download, and "Skip for now" stays visible. After a reload the wizard restarts and Download answers `409: {"detail":"setup already in progress"}`.

- While local setup runs: Escape and outside clicks do not close the wizard, and "Skip for now" is hidden or disabled with a reason.
- On opening, if `/api/local/status` says `setup_running`, show the running download's progress instead of offering Download. A 409 from the setup endpoint is treated the same way (resume watching), never shown raw.
- Proof: walk it (Escape mid-download; reload mid-download).
- **Amended after the round 2 diagnosis (lead choice, 2026-11-20; see diagnosis-r2.md and fix-plan-r2.md):** the hard lock holds only while the page can confirm the download is running. "Is a setup running" has ONE owner (the local step), fed by one bounded, sequential status read. When the page cannot reach the server (two failed or timed-out reads in a row), a plain notice shows and closing is possible again, through one confirmation. The owner approved "lock the wizard during download"; this keeps that lock and adds only the exit the lock lacked when the server is unreachable. Dropping the lock for a confirm-to-close design (the diagnosis's recommendation) is left to the owner as a wave 2 question.

### W7. "Ready!" box and the Windows window closing (INSTALL)

- `install.sh` final box (lines 619 to 652): when desktop mode was set up (`DESKTOP_STATE == done`), the box tells them to click the app (S7a), not to type commands. When it was not, and `anyscribe` is not on PATH in the current shell (the pipx route), the box says to open a NEW terminal window first (S7b) or prints the full path. The existing pipx warning can merge into the box.
- `install.ps1`: the same two cases for the Windows banner, if the same problem exists there (check whether the current session can run `anyscribe` after install).
- `install.ps1` line 394: `exit 1` inside the catch closes the person's whole PowerShell window under `irm | iex`, so the error and recovery steps vanish. Replace with a form that ends the script but leaves the window open (`return` at the right scope, or wrap the body in a function). Nothing after the failure may run. Keep a non-zero signal where possible for anyone running it as a file.
- Proof: Docker run of `install.sh` for the pipx case showing the new box; for PowerShell, the official `mcr.microsoft.com/powershell` image: run the script text through `Invoke-Expression` with a forced failure, then a marker command, and show the session survives and nothing after the catch ran.

### W8. "Read transcript" button and a formatted transcript (APP)

- `ui/src/components/ResultCard.tsx`, the Done screen: add a "Read transcript" link to `/history/<slug>`, as the main action; "New transcription" becomes secondary (house rule: one main button per card). The "already transcribed" branch in `TranscribePage.tsx` (around line 310) builds the slug with `file_path.split("/")`, which breaks on Windows paths; use a helper that handles both `/` and `\` and use it in both places.
- `ui/src/pages/TranscriptView.tsx` (line 107) shows the raw markdown in a `<pre>` code font. Render it formatted instead, with a small renderer for the shapes `vault/writer.py` produces: `#` and `##` headings, `> ` quote lines, `---` rules, paragraphs, and inline `**bold**`, `[text](url)` links (http and https only, open in a new tab with `rel="noopener noreferrer"`), and `` `code` ``. Build React elements; never `dangerouslySetInnerHTML` (titles and text come from the internet). Do not show the title twice (skip a leading `#` heading equal to the page title). Body font, comfortable size, line length about 70 characters. Read `_format_diarized` and the timestamped format in `writer.py` and make sure both read well.
- No new npm dependency.
- Keep "Copy text" as it is (wave 2 decides what it should copy).
- Rebuild `src/anyscribe/web/static` from `ui/` and commit it (CI fails if it is stale).
- Proof: walk a real transcript (see Proof) and screenshot the Done screen and the History view at 1440, about 1000 and 390 px, plus one transcript in timestamped format.

## Fixed strings

Use these words. Fill `{Provider}` with the display name (OpenAI, Groq, OpenRouter, Sarvam, Deepgram, ElevenLabs).

- **S1** (no credit): "Your {Provider} account has no credit. {Provider} is prepaid: add credit and try again, or use the free option instead (in the dashboard: Settings, then Run setup wizard, then On this computer)." For OpenAI insert after "add credit": " at https://platform.openai.com/settings/organization/billing".
- **S2** (OpenAI key step note): "OpenAI is prepaid: add credit to your OpenAI account first, or transcripts will fail."
- **S3a** (key accepted): "{Provider} accepted this key."
- **S3b** (401 or 403): "{Provider} refused this key. Check that you copied all of it, with no extra spaces."
- **S3c** (other error status): "{Provider} answered with an error ({status}). Try again in a minute."
- **S3d** (timeout or network): "Couldn't reach {Provider} to check the key. Check your internet connection, or continue: the key will be checked on your first transcript."
- **S3e** (Sarvam): "Saved, not checked: Sarvam has no way to check a key in advance. It will be checked on your first transcript."
- **S4** (wizard, ffmpeg missing): heading "One more thing: ffmpeg"; body "anyscribe needs ffmpeg, a free audio tool, to read audio and video. Install it with the command below, then click Check again." Windows only, add: "If it still isn't found after installing, quit anyscribe from the tray and open it again."
- **S5** (installer end, ffmpeg missing): box title "anyscribe is installed, but can't transcribe yet"; body "ffmpeg, a free audio tool, is missing. Install it with: {command}, then open anyscribe again." Commands: Windows `winget install Gyan.FFmpeg`, Mac `brew install ffmpeg`, Linux `sudo apt install ffmpeg`.
- **S6** (Homebrew failed): "Homebrew didn't finish installing, so anyscribe can't continue. Install Homebrew from https://brew.sh (copy its one line into Terminal), then run this anyscribe installer again."
- **S7a** (box, desktop mode done): "Open anyscribe: click the anyscribe app (in your Applications folder / app menu / Start menu). Your dashboard should already be open in your browser." (Pick the one place that fits the OS.)
- **S7b** (box, command not on PATH yet): "Open a new terminal window, then type: anyscribe ui"
- **S9** (website, how to open): Mac: "Open Terminal: press ⌘ Space, type Terminal, press Return. Paste the line and press Return. It may ask for your Mac password; nothing shows while you type." Windows: "Open PowerShell: right-click the Start button and choose Terminal (or Windows PowerShell). Paste the line and press Enter."
- **S10**: button label "Read transcript".

Avoid em dashes in new user-facing copy.

## Docs and records (INSTALL owns all of these)

Per the repo's `AGENTS.md` and `docs/building/COMMIT_CHECKLIST.md`:
- `docs/user/troubleshooting.md`: entries for S1 (no credit), the S3 key-check results (including Sarvam "not checked"), the wizard's ffmpeg notice, and the installer's Homebrew failure (S6), each keyed on the exact text.
- `docs/user/getting-started.md`: W2's terminal line; S2's prepaid note where OpenAI keys are described.
- `src/anyscribe/skill/references/troubleshooting.md` (and SKILL.md only if a stated fact changed): S1 and the key-check results.
- Run `python scripts/build-docs.py` and commit the regenerated `landing/docs/`.
- `CHANGELOG.md`: an "Unreleased" section at the top, user-facing, covering W1 to W8 in plain words (do not invent a version number).
- `BACKLOG.md`: a section "Onboarding audit (2026-11-20)" with wave 1 (this PR) checked, and waves 2 and 3 below as unchecked items, copied from "Not in this wave".
- `docs/building/journal/2026-11-20-onboarding-wave1.md` plus a row at the top of `docs/building/_index.md`.

## Keep-list (must survive)

- The installer's prompts reading from `/dev/tty`, Enter meaning Yes, Deno optional and never fatal, desktop-mode failure never failing the install, the pipx fallback.
- The website's existing look, the KraftedX credit and license notices, the demo video.
- The wizard's local-first framing, "Help me choose", the language question and its reasons, download sizes on the button, Back on every step, config written once at Finish.
- `SetupBanner` stays.
- The key test checks the typed key without saving it.
- Tailnet sharing (`core/tailnet.py`) and the web app's Host check are untouched.

## Decisions already made (do not reopen)

- No new dependencies (Python, npm, services, keys).
- Sarvam gets "Saved, not checked", not a fake success and not a hard failure.
- A refused key can still be used ("Use this key anyway"); a provider's check being down never blocks setup.
- "Read transcript" is the main action on the Done screen.
- No version bump and no release in this PR.

## Left to the builder

Exact layout of the website's two install options; where shared constants live; test structure; how the formatted view is styled, within the dashboard's existing look.

## Not in this wave (do not build)

Wave 2: Hinglish answer and no pre-selected model; honest Sarvam label; prices and get-a-key steps on paid cards; plain error messages with a button for every common error; Skip leading to the free option and a banner that offers it; dropping the workspace step; download MB count, time and stall warning; Instagram and YouTube login help; "Open folder"; what "Copy text" copies.
Wave 3: website first screen and default-engine wording; getting-started as one straight line; Claude skill first-run steps; one-command Claude Desktop setup; terminal fixes (zsh quoting, onboard summary after a failed local setup, `doctor`); the 17 polish items in the audit.
