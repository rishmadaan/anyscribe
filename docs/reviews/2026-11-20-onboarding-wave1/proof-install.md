# Proof: builder INSTALL, onboarding wave 1, round 0

Branch `feat/onboarding-wave1-install`, base `91bdc2b` (checked before editing).
Logs: `~/.review-runs/2026-11-20-onboarding-wave1/install-logs/`. Screenshots:
`~/.review-runs/2026-11-20-onboarding-wave1/screens/install-hero-{1440,1000,390}.png`.

| Commit | Item |
|---|---|
| `77fe12b` Installer: give Homebrew the keyboard and stop with a clear message if it fails | W1 |
| `9945c47` Website: a copyable Windows install line and how to open a terminal | W2 |
| `153a714` Installers: never say ready when ffmpeg is missing | W3 (installers) |
| `71480bc` Installers: the last box says how to open anyscribe from here | W7 |
| `93114ac` Installers: keep "Next step" and the pipx hint in the last box | W7 follow-up |
| `439f52d` Docs and records for onboarding wave 1 | docs and records |
| `a3ae866` Installer: plain comment for app_place | comment only |

## What was run

### W1, Homebrew (Docker, Ubuntu 24.04, normal user `alice` whose sudo needs a password, nothing cached)

The anyscribe installer only takes the Homebrew branch on macOS, so the harness
is built from the real `install.sh` text (its helpers and
`install_brew_if_needed`, with `OS=macos`) and piped exactly as a customer does:
`cat h.sh | bash`, inside a real pseudo-terminal driven by a script that
presses Enter at `[Y/n]` and types the password. Homebrew's Linux installer has
the same non-interactive check as on a Mac. `/usr/local/bin/brew` is a dangling
link to Linux Homebrew's `bin/brew`, standing in for the Intel-Mac location the
function activates.

- Old line (base `91bdc2b`), `w1-A-old.log`:
  ```
  Warning: Running in non-interactive mode because `stdin` is not a TTY.
  ==> Checking for `sudo` access...
  Insufficient permissions to install Homebrew to "/home/linuxbrew/.linuxbrew".
  pipeline exit: 1
  ```
  No anyscribe message at all: the silent death the audit found.
- New line, `w1-B-new.log`:
  ```
  ==> Checking for `sudo` access (which may request your password)...
  [sudo] password for alice: <<driver typed sudo>>
  Press RETURN/ENTER to continue or any other key to abort: <<driver typed ret>>
  ==> Installation successful!
  /bin/bash: /home/linuxbrew/.linuxbrew/Library/Homebrew/brew.sh: No such file or directory
  MARKER: continued past the Homebrew step; brew is [/usr/local/bin/brew]
  pipeline exit: 0
  ```
  (The `brew.sh` line is `brew shellenv` run through the stand-in link, which
  Homebrew resolves to the wrong prefix on Linux; on a Mac `/usr/local/bin/brew`
  sits inside its own prefix.)
- Same container, after the install (`after-b.sh`): `brew install hello; brew unlink hello; brew install hello`
  ```
  Warning: hello 2.12.3 is already installed, it's just not linked.
  brew install of an installed-but-unlinked formula exit: 0
  hello not on PATH
  ```
  This is the concrete path by which `install.sh` could reach its end with no
  ffmpeg (see W3).
- No terminal at all (`docker run` without `-t`), `w1-E-notty.log`:
  `main: line 23: /dev/tty: No such device or address`, exit 1, at the
  "Install Homebrew now?" prompt. Pre-existing and on the keep-list (prompts
  read `/dev/tty`); not changed.
- `bash -n install.sh`: ok. `shellcheck` (koalaman/shellcheck:stable): 5
  warnings on the new file, the same 5 as on the base (SC2034 `VERBOSE` unused,
  SC1010 bare `done` four times); none added (my one new `== done` is quoted).

### W2, website (served `python3 -m http.server 8483` from `landing/`, T3 preview tab)

- Opened at 1440, 1000 and 390 px wide; clicked both hero copy buttons with
  real clicks. The copy writes to this machine's X clipboard, so each click was
  checked by reading it back with `xclip` and comparing to the exact command
  (the script prints only on a match):
  ```
  clipboard == exact Mac command: [curl -fsSL https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.sh | bash]
  clipboard == exact Windows command: [irm https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.ps1 | iex]
  390px Mac copy: clipboard == [curl -fsSL https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.sh | bash]
  390px Windows copy: clipboard == [irm https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.ps1 | iex]
  ```
  (1440 run: Mac then Windows; 390 run: Mac then Windows, so each click changed
  the clipboard.)
- At 1000 px the Mac line overflowed its box with a horizontal scrollbar (the
  same before this change). Added one rule: below 1100 px the command wraps
  instead (`scrollWidth > clientWidth` false for both boxes afterwards).
- At 390 px: no horizontal page scroll (`scrollWidth` 375 = viewport minus the
  scrollbar), 24 px gutters, buttons 45 px tall.
- No console errors. The section 07 install tabs are untouched (the hero uses
  two stacked blocks, so the page's global tab script is not involved).

### W3 and W7, `install.sh` (Docker, same image, one long-lived container `b95fa4f74b22`)

- Run 1, clean: `cat /w/install.sh | bash` as `alice`, Enter at every prompt
  (`w37-run1-clean.log`): Python, yt-dlp (apt brought ffmpeg along), Deno 2.9,
  then `python3.12 has no pip. Using pipx instead...`, desktop mode skipped
  (no display), and:
  ```
  ┌────────────────────────────────────────────────────────┐
  │  anyscribe is installed!                               │
  │                                                        │
  │  Open a new terminal window, then type: anyscribe ui   │
  └────────────────────────────────────────────────────────┘
      Or, in this window: /home/alice/.local/bin/anyscribe ui
  installer exit: 0
  ```
  Checked the box's claims: the installing window's PATH gives
  `anyscribe: not found`; a new interactive terminal (`bash -i`, reads
  `~/.bashrc`) gives `/home/alice/.local/bin/anyscribe` and `anyscribe v0.19.0`;
  the printed full path prints `anyscribe v0.19.0`.
- Run 2, ffmpeg missing (`w37-run2-ffmpeg-missing.log`): ffmpeg and ffprobe
  moved out of PATH, and a stand-in `sudo` first on PATH that answers
  `apt update -qq` and `apt install -y ffmpeg` with exit 0 and installs nothing
  (the same outcome as `brew install` of an unlinked formula, proven above):
  ```
  [fake sudo] apt install -y ffmpeg -> exit 0, nothing installed
    ! ffmpeg is still not available after installing it.
  ┌────────────────────────────────────────────────────────┐
  │  anyscribe is installed, but can't transcribe yet      │
  │                                                        │
  │  ffmpeg, a free audio tool, is missing. Install it     │
  │  with: sudo apt install ffmpeg, then open anyscribe    │
  │  again.                                                │
  │                                                        │
  │  Open a new terminal window, then type: anyscribe ui   │
  └────────────────────────────────────────────────────────┘
  ```
- Run 5, from a new terminal window whose PATH already has `~/.local/bin`
  (`w37-run5-newwindow.log`): the box gives the type-it line, no new-window
  step.
- Runs 6 and 7, `--dry-run` with a display (desktop mode counts as done in a
  dry run), Linux and then as macOS (`uname -s` answering `Darwin`):
  ```
  ✓ anyscribe is in your app menu and running in your system tray
  │  Open anyscribe: click the anyscribe app (in your      │
  │  app menu). Your dashboard should already be open in   │
  ...
  ✓ anyscribe is in the Applications folder inside your home folder (~/Applications) and running in your menu bar
  │  Open anyscribe: click the anyscribe app (in the       │
  │  Applications folder inside your home folder). Your    │
  │  dashboard should already be open in your browser.     │
  ```
- After the Docker runs the open line was reworded to start with "Next step:"
  (so `tests/test_install_sh.py` passes unchanged) and the desktop + pipx hint
  kept "pipx ensurepath". Final wording, from the real `install.sh` with its
  install steps stubbed (`w7-sh-final-wording.log`):
  ```
  │  Next step: open the dashboard to set up and start     │
  │  transcribing. Type: anyscribe ui                      │
  ...
      If 'anyscribe' is not found when you type it, open a new terminal window first; if it still isn't, run: pipx ensurepath
  ```
- `tests/test_install_sh.py` (pytest in a throwaway venv, the suite's own
  conftest isolating HOME): `30 passed`.

### W3 and W7, `install.ps1` (official `mcr.microsoft.com/powershell:latest`, PowerShell 7.4.2 on Ubuntu 22.04)

- CI's own check: `[scriptblock]::Create((Get-Content -Raw install.ps1))`
  ok; parser errors 0.
- Window survival (`w7-ps-exit.log`). The script text piped into
  `Invoke-Expression`, exactly like `irm … | iex`, then a marker in the same
  session, then our own `exit 7`. Python is absent in the image, so the
  install fails at its first step:
  - new script: `x Installation failed: Python not found`, the manual-install
    list, then `MARKER: session still alive after the installer`, pwsh exit
    code `7`. Nothing after the failure ran (no "Checking ffmpeg...").
  - base script: the same messages, no marker, pwsh exit code `1`: the session
    was killed, which in a real window closes it.
  - `& ([scriptblock]::Create((Get-Content -Raw install.ps1))) -NoDesktop` (the
    documented -NoDesktop form): marker printed.
  - run as a file, `pwsh -File install.ps1`: exit code `1`.
- End result (`w3-ps-guarded.log`, `w7-ps-banner.log`). A small test script
  loads every function from the real `install.ps1` through the PowerShell
  parser without running its main part, then runs the real `Test-Ffmpeg` and
  `Write-Result`. Fake `ffmpeg`/`ffprobe`/`anyscribe` scripts on PATH stand in
  for installed programs. Results:
  - no ffmpeg, desktop done: `FfmpegOk = False`, box "anyscribe is installed,
    but can't transcribe yet" / "Install it with: winget install Gyan.FFmpeg,
    then open anyscribe again. If it still isn't found after installing, quit
    anyscribe from the tray and open it again." / S7a.
  - ffmpeg without ffprobe: same as no ffmpeg.
  - ffmpeg and ffprobe, desktop done: "anyscribe is ready!" / "Open anyscribe:
    click the anyscribe app (in your Start menu). Your dashboard should already
    be open in your browser."
  - no desktop, `anyscribe` found: "Next step: … Type: anyscribe ui".
  - no desktop, not found: "Next step: … with the line below this box." then
    `& "/usr/bin/python3" -m anyscribe ui`.
  - desktop failed: installed box plus the existing "Desktop mode was not set up"
    warning.

### Docs

`python scripts/build-docs.py` then `python scripts/check-docs.py` (exit 0);
only the three edited pages changed in `landing/docs/` (agents, providers and
configuration rendered byte-identical, so the local `markdown` 3.5.2 matches
what was committed). Rendered anchors checked: every in-page link I added
resolves to an `id` in `landing/docs/troubleshooting.html`. Before writing the
dashboard sentences I read APP's commits (`40ebc18`, `9045d27`, `a46d64a`,
`183bdf5`, `00dc861`) read-only, so the docs match the code: the `NoCreditError`
text, the `checked: false` results, the 10 s timeout, Settings' Test checking
the saved key, "Use this key anyway" in the wizard only, "Skip is off until the
download finishes", the `Check again` button.

## Guards mutation-tested

Each guard was removed in a copy and run under the same conditions; the
assertion is the exact text printed.

| Guard | With the guard | Guard removed |
|---|---|---|
| W1 `… </dev/tty \|\| die "$brew_failed"` (Homebrew exits non-zero: "x" pressed at its RETURN prompt), `w1-C-*.log` | `✗ Homebrew didn't finish installing, so anyscribe can't continue. Install Homebrew from https://brew.sh (copy its one line into Terminal), then run this anyscribe installer again.` | nothing printed, `pipeline exit: 1` (the old silent death) |
| W1 `command_exists brew \|\| die "$brew_failed"` (no network: `curl` fails, `bash -c ""` exits 0), `w1-D-*.log` | the same S6 line, exit 1 | `MARKER: continued past the Homebrew step; brew is []`, exit 0 |
| W3 `install.sh` re-check after installing ffmpeg, `w37-run2/run3` | `! ffmpeg is still not available after installing it.` and the yellow "can't transcribe yet" box | green `anyscribe is installed!` box, no mention of ffmpeg |
| W3 `install.ps1` `if (-not $script:FfmpegOk)` in `Write-Result`, `w3-ps-mutant.log` | "anyscribe is installed, but can't transcribe yet" box | `anyscribe is ready!` with `FfmpegOk = False` |
| W3 `install.ps1` ffprobe required in `Test-FfmpegFound` (ffmpeg only on PATH), `w3-ps-mutant-ffprobe.log` | `FfmpegOk = False`, "can't transcribe yet" box | `+ ffmpeg found`, `anyscribe is ready!` |
| W7 `install.sh` check of the person's own PATH (`ORIG_PATH`), `w37-run4-*.log` | `Open a new terminal window, then type: anyscribe ui` plus the full path | `… Type: anyscribe ui` in a window where `anyscribe` is not found |
| W7 `install.ps1` `if ($PSCommandPath) { exit 1 }` | `pwsh -File`: exit code 1; under iex the session survives | line removed: `pwsh -File` exit code 0. Unconditional `exit 1` (the base script): the iex session dies, no marker, exit 1 |

## Customer-use walk

- Linux customer, clean container, normal user, `cat install.sh | bash` with
  Enter everywhere: installs, ends with the open-a-new-window box; a new
  terminal finds `anyscribe` (above).
- Website visitor at 1440, 1000 and 390 px: two labelled options, each full
  command copies exactly, how-to-open line under each (screens saved).
- Windows: the real script text under `irm | iex`-style evaluation in the
  official PowerShell image; failure leaves the session usable.
- Not walked: a real Mac (Homebrew branch, `/opt/homebrew`), real Windows
  (PowerShell 5.1, winget, `Refresh-Path` reading the registry: on Linux the
  Machine/User PATH is empty, so the winget path could not be exercised), and a
  real desktop-mode install (no display in a container; the S7a box was shown
  with `--dry-run`).

## Items

- [x] W1 BUILT: `install.sh`, `</dev/tty` plus two stop guards; password and
  10-20 minute warning kept.
- [x] W2 BUILT: `landing/index.html` hero, two stacked labelled options with
  full commands, copy buttons and S9 lines; Windows teaser line removed from
  the "or" row; wrap rule under 1100 px. `docs/user/getting-started.md`
  "PowerShell / Terminal", Command Prompt dropped, S9 lines.
- [x] W3 installer half BUILT: `install.ps1` tracks `FfmpegOk` (ffmpeg and
  ffprobe) and ends with S5 (Windows); `install.sh` re-checks after install and
  ends with S5 (Mac or Linux form).
- [x] W7 BUILT: `install.sh` end box (S7a, S7b, full path, pipx warning merged);
  `install.ps1` S7a, python `-m` fallback, no `exit` under iex.
- [x] `docs/user/troubleshooting.md` BUILT: S6, S5 + S4 (one entry), S1, each S3
  result, new-terminal note under "command not found", pointer from "Provider
  error".
- [x] `docs/user/getting-started.md` BUILT: S9, S2 (twice), key check, ffmpeg
  notice, download lock, last box, Read transcript.
- [x] `docs/user/commands.md` BUILT (one table cell: Settings Test now asks the
  provider).
- [x] `src/anyscribe/skill/references/troubleshooting.md` BUILT: S1, key-check
  results, rate-limit and 401 entries adjusted. `SKILL.md` SKIPPED: its one
  related fact (`providers test` makes no API call) is still true.
- [x] `landing/docs/` regenerated BUILT.
- [x] `CHANGELOG.md` "Unreleased" BUILT (no version number).
- [x] `BACKLOG.md` "Onboarding audit (2026-11-20)" BUILT: wave 1 checked, waves 2
  and 3 unchecked.
- [x] `docs/building/journal/2026-11-20-onboarding-wave1.md` and the
  `docs/building/_index.md` row BUILT.
- [x] `docs/building/web-ui-spec.md` BUILT (extra, one line: the test
  endpoint's path and `checked` field).
- [ ] `README.md` SKIPPED: nothing in it became false.

## Spec problems found

1. **W3, `install.ps1` premise.** The spec says to refresh `$env:Path` after
   winget or Chocolatey. That already happens (`Refresh-Path` right after both
   installs, base lines 135 and 149). The real bug was that the outcome was
   never recorded, so a failed or declined ffmpeg still ended "ready". Built
   the tracking; the refresh stays as it was.
2. **W3, `install.sh` "can any path reach the end with ffmpeg missing?"** Yes:
   `brew install` of an installed but unlinked formula exits 0 (shown above).
   In that one case S5's `brew install ffmpeg` does not fix it (`brew link
   ffmpeg` does); brew prints that itself, and the troubleshooting entry says
   it. I kept the fixed command.
3. **S5 Linux command.** The fixed string gives `sudo apt install ffmpeg` for
   all Linux. The box uses the detected package manager (`sudo dnf install
   ffmpeg`, `sudo pacman -S ffmpeg`, else apt).
4. **S7a, macOS.** "in your Applications folder" would send a Mac user to
   `/Applications`; desktop mode installs to `~/Applications`
   (`core/launcher.py`). The box says "in the Applications folder inside your
   home folder", matching the existing `desktop_where` line.
5. **S5 on Windows after desktop mode.** "then open anyscribe again" is not
   enough there: the tray already running keeps the PATH it started with, and
   clicking the Start menu entry reopens that same process. In that case the box
   adds S4's Windows sentence ("If it still isn't found after installing, quit
   anyscribe from the tray and open it again.").
6. **W7, `install.ps1` second case.** It does not exist under `irm | iex`: the
   PATH changes happen in the person's own session, so the window that ran the
   installer can run `anyscribe`. The existing python `-m` fallback stays, now
   referred to from the box.
7. **`tests/test_install_sh.py` is APP's file** (target.md gives `tests/**` to
   APP) but encodes installer copy: two tests assert "Next step:" and "pipx
   ensurepath". Rather than edit APP's file, I kept those phrases in the new
   box; all 30 tests pass unchanged. If the lead wants different wording, that
   file changes with it.
8. **S3e in the wizard** says "Saved, not checked" while the wizard has not
   saved anything yet (it saves at Finish). APP's string and a settled
   decision; the docs say the wizard saves it when you finish. Flagged only.

Pre-existing problems noticed and left alone: with no terminal at all the
first `[Y/n]` prompt stops the installer with bash's own error; on the docs
site, the Windows PATH code block inside a list in "command not found" renders
as raw backticks; on phones the hero copy button sits inline after the wrapped
command (existing 760 px design); `install_anyscribe` still prints its own
mid-install pipx line before the box.

## Cleanup

Removed by ID: containers (all `--rm`, plus `b95fa4f74b22`), images
`b10afb0476cf` (my Ubuntu test image), `bb596a0d169b` (shellcheck),
`810c4f1e0c9d` (PowerShell). No prune was run; my one `docker build` reused
existing cache layers and may have left small cache records. The http server
on 8483 (pid read, then killed) and the preview tab are closed; the worktree's
`.venv`, `.pytest_cache` and the throwaway folder under `~/.review-runs/` are
deleted. The clipboard checks overwrote this machine's clipboard (it last held
the Windows install line).
