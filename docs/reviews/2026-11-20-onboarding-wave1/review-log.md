Size: L
Sized because: release gate: install.sh and install.ps1 are fetched by every new customer straight from main, and the website deploys on merge, so merging releases them; the key check also sends customers' API keys to new endpoints (secrets).
Cap: 3
Packet: v1

| Round | Role | Model, effort | Lane | Target (sha/version) | Verdict | Raised | Upheld | Minutes | Fixer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | correctness | gpt-6.1-sol, high | Codex CLI read-only | 8d63221 | NOT YET | 5 | 5 | 24 | Claude Opus fixer, Agent tool |
| 1 | fit | Opus 5.5, default effort | Agent tool (Claude lane, read-only by instruction; snapshot unchanged) | 8d63221 | CONDITIONAL | 10 | 9 | 7 | Claude Opus fixer, Agent tool |

Round 1 fit seat ran at the Agent tool's default effort (the tool's effort is set only on explicit instruction); the roster names high.

| Id | Round | Reviewer | Severity | Lead verdict | Evidence | Also raised by |
|---|---|---|---|---|---|---|
| C1 | 1 | gpt-6.1-sol | blocker | UPHELD | Traced: OnboardingWizard.tsx `enable-local` checkbox has no disabled state during setup; unchecking shows "Skip, next" (no settingUp guard); unmount cleanup calls onRunning(false), unlocking Escape, backdrop and Skip | |
| C2 | 1 | gpt-6.1-sol | blocker | UPHELD | Traced: on reload the step calls onPresetSize(recommended_model) and setSettingUp(true) without adopting `setup_last_model` (routes/local.py:78); the 409 branch also keeps the old selection; `set_up` means any model runnable (local_setup.py:328), so All set can say "<recommended> · ready" after a different model downloaded and Finish then starts that download. Hits the W6 reload path, not only a second tab | |
| C3 | 1 | gpt-6.1-sol | should-fix | UPHELD | Traced: handleNext awaits the check and calls onNext() without comparing the key to the current input or step | |
| C4 | 1 | gpt-6.1-sol | should-fix | UPHELD | Traced: Test-Ffmpeg caches $script:FfmpegOk; Install-Anyscribe later calls Refresh-Path; Write-Result reads the cached flag | |
| C5 | 1 | gpt-6.1-sol | nit | UPHELD | Known limit noted in TranscriptBody.tsx; source URLs with parentheses break | |
| F1 | 1 | opus fit | should-fix | UPHELD as an owner decision, no code change | Installers install from PyPI (still 0.19.0) while Vercel publishes landing/docs on merge; dashboard items reach customers only with a release, which needs the owner's yes | |
| F2 | 1 | opus fit | should-fix | REFUTED | Homebrew's current installer writes /etc/paths.d/homebrew when the prefix is /opt/homebrew and it has sudo (Homebrew/install install.sh lines 599-601, 1083-1090, fetched 2026-11-20); macOS's /etc/zprofile runs path_helper, so new Terminal windows find brew. W1 now gives Homebrew sudo. Intel Macs use /usr/local/bin, already on PATH | |
| F3 | 1 | opus fit | should-fix | UPHELD | Opened screens/app-ffmpeg-after-setup-1440.png: empty panel | C (report end) |
| F4 | 1 | opus fit | nit | UPHELD (lead miss) | BACKLOG.md:668 still says "Saved, not checked" | |
| F5 | 1 | opus fit | nit | UPHELD | errors.py no_credit_message says "{Provider} is prepaid" for any 402 | builder APP flagged |
| F6 | 1 | opus fit | nit | UPHELD | install.sh after_box line after the click-the-app box | |
| F7 | 1 | opus fit | nit | UPHELD | Finder's Applications is /Applications; desktop mode uses ~/Applications | |
| F8 | 1 | opus fit | nit | UPHELD | install.ps1 non-desktop route with ffmpeg missing tells them to type in the same window | |
| F9 | 1 | opus fit | nit | UPHELD | Sarvam: first Next only shows the amber note | |
| F10 | 1 | opus fit | nit | UPHELD | missingPart() says "the local engine (faster-whisper)" and "install log" | |
