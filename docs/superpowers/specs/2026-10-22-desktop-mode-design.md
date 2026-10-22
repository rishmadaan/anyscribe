# anyscribe: desktop mode — design

**Date:** 2026-10-22
**Status:** Approved in conversation by Rishabh (three rounds, 2026-10-22); plan
at `docs/superpowers/plans/2026-10-22-desktop-mode.md`.
**Research basis:** read of T3 Code's release pipeline (`release.yml`,
`release-desktop.yml`, `build-desktop-artifact.ts`), Microsoft's code-signing
options page (2026-08-29), Voicebox's Tauri+PyInstaller build docs, and a live
probe on this Mac: a locally created `.app` launches with no Gatekeeper prompt
and carries no quarantine attribute, and nothing pip installs is quarantined.

## Goal

A user installs anyscribe once and never has to know that there is a server, a
tray, a login item, or a terminal. Two install methods:

- **CLI mode**: `pip install anyscribe`. Unchanged.
- **Desktop mode**: the one-line installer (or `pip install "anyscribe[tray]"`
  followed by one command) puts an **anyscribe** app in Applications / the Start
  menu / the app menu, starts the background server at login, starts it now, and
  opens the dashboard. Clicking the app opens the dashboard; closing the window
  leaves it running; Quit in the tray menu stops it.

## Decisions (locked)

1. **No signed, downloadable app.** Not now. Desktop mode builds its launcher on
   the user's own machine, so nothing is quarantined and nothing needs an Apple
   or Windows certificate. The Tauri/PyInstaller downloadable-app route is
   parked in BACKLOG for when the project is worth paying for.
2. **No money, no new accounts, no new runtime dependencies.** Each OS's own
   plain-file mechanism holds the login item and launcher; Pillow (already in
   the `[tray]` extra) renders icons; macOS's bundled `iconutil` makes `.icns`.
3. **Claude Code is unaffected by whether the app is running.** The skill and
   the MCP server run the pipeline in-process and exit; they never talk to the
   web server. The dashboard reads history from the vault on disk, so Claude's
   transcripts appear in it whenever it is next opened. No change needed; the
   docs say so.
4. **One command owns it: `anyscribe desktop {install, uninstall, status, open}`.**
   `install-service` / `uninstall-service` stay as the login-item-only
   commands (now on all three OSes); the Settings → Startup toggle calls the
   same code.
5. **Version 0.18.0.** A new install method is a milestone. Release is a
   separate, Rishabh-gated step (PyPI publish is public).

## 1. What `anyscribe desktop install` does

Refuses (exit 1, clear message) when the `[tray]` extra is missing or the OS is
not macOS / Windows / Linux. Then, in order:

1. **Icons** rendered from `src/anyscribe/assets/app-icon.png` (1024×1024, the
   approved mark) into `~/.anyscribe/desktop/`: `anyscribe.icns` (macOS, via
   Pillow-resized iconset + `iconutil`), `anyscribe.ico` (Windows, Pillow), and
   `anyscribe.png` (Linux, copied to
   `~/.local/share/icons/hicolor/512x512/apps/anyscribe.png`).
2. **App launcher** — clicking it runs `<python> -m anyscribe desktop open`:
   - macOS: `~/Applications/anyscribe.app` (Info.plist with `LSUIElement` so no
     Dock bounce, `Contents/MacOS/anyscribe` shell script, `.icns`).
   - Windows: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\anyscribe.lnk`
     targeting `pythonw.exe` (no console window). Shortcuts are created through
     PowerShell's `WScript.Shell` COM object; no new Python dependency.
   - Linux: `~/.local/share/applications/anyscribe.desktop`
     (`Terminal=false`, `Icon=anyscribe`), then `update-desktop-database` if present.
3. **Login item** — runs `<python> -m anyscribe tray --port <port>` at login:
   - macOS: `~/Library/LaunchAgents/com.anyscribe.tray.plist` with
     `EnvironmentVariables.PATH` (see §3), `KeepAlive {SuccessfulExit: false}`,
     `ThrottleInterval 60`, `ProcessType Interactive`, stdout/stderr to
     `~/.anyscribe/logs/tray.log`. `ProcessType` was added after measurement
     on 2026-10-22: a plain launchd job throttles the server's child processes
     (`/api/health`, which spawns ffmpeg and friends, took 5–13 s; with
     `Interactive` 0.32 s, the same as a terminal start). Transcriptions are
     child processes too.
   - Windows: `...\Start Menu\Programs\Startup\anyscribe tray.lnk` → `pythonw.exe`.
   - Linux: `~/.config/autostart/anyscribe-tray.desktop` with
     `Exec=env PATH=<path> <python> -m anyscribe tray --port <port>`.
4. **Manifest** `~/.anyscribe/desktop.json`:
   `{"version", "python", "port", "launcher", "login_item", "installed_at"}`.
   `status` reads it and reports `healthy: false` with a reason when the
   recorded Python no longer exists (the "I upgraded Python" case) or a file is missing.
5. **Start now and open** — unless `--no-launch`: `desktop open` (§2).

`anyscribe desktop uninstall` stops the tray and its server (POST
`/api/shutdown`, then SIGTERM the pidfile pid), removes launcher, login item,
icons and manifest, and prints that any transcription in progress was
cancelled (checkpoints resume it next run). It never touches `~/anyscribe/`,
config, or keys.

`anyscribe desktop status [--json]` reports platform, launcher path, login-item
path, tray running, server responding, port, healthy + reason.

Flags on `install`: `--port` (default 8457, stored in the manifest and used by
launcher and login item), `--no-launch`, `--yes`, `--json`. On `uninstall`:
`--yes`, `--json`. All four subcommands work without a TTY.

## 2. What `anyscribe desktop open` does

1. If `/api/health` on the manifest port answers as anyscribe → open the browser.
2. Else if something else is listening there → exit 1: "Port N is in use by
   another program. Run: anyscribe desktop install --port <free port>".
3. Else spawn `anyscribe tray --port N` detached (POSIX `start_new_session`;
   Windows `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` under `pythonw.exe`),
   output appended to `~/.anyscribe/logs/tray.log`. Wait up to 15 s for health.
   If the tray process exits during the wait (no tray backend: headless Linux,
   missing display), spawn `anyscribe ui --port N --no-open` detached instead
   and wait again.
4. Open the browser; if `webbrowser.open` returns False (SSH, no GUI), print the URL.

## 3. Fixes to the existing tray that desktop mode depends on

- **PATH for login-started processes.** launchd and Linux autostart give a
  minimal PATH; on this Mac `anyscribe doctor` under that PATH reports ffmpeg
  and Deno missing. `service_path()` = the installing shell's PATH +
  `/opt/homebrew/bin`, `/usr/local/bin`, `~/.deno/bin`, `~/.local/bin`,
  `dirname(sys.executable)`, de-duplicated, order kept. Written into the plist
  and the Linux autostart `Exec`. Windows inherits the user PATH, which the
  installer already fixes.
- **Windows tray is broken today**: `signal.pthread_sigmask`, `signal.sigwait`
  and `Popen(preexec_fn=…)` do not exist on Windows. Guard all three with
  `os.name != "nt"`.
- **A second tray exits 0, not 1**, when the pidfile shows a live tray: with
  `KeepAlive` a non-zero exit would make launchd relaunch it every
  `ThrottleInterval`. The missing-extra exit stays 1 (install refuses without
  the extra, so only a later uninstall of the extra reaches it; ThrottleInterval
  keeps that loop to once a minute and troubleshooting names the fix).
- **`stop_tray(port)`** in `core/tray.py`: POST shutdown, SIGTERM the pidfile
  pid, remove the pidfile. Used by uninstall and by the Windows path, where
  SIGTERM terminates without running the tray's own teardown.

## 4. Surfaces that change

- **Installers.** `install.sh` (pip path only; git-method installs skip the
  extra and say so) and `install.ps1` end with `anyscribe desktop install --yes`
  unless `--no-desktop` / `-NoDesktop`. Finishing banner becomes:
  macOS "anyscribe is in your Applications folder and running in your menu bar";
  Linux "…in your app menu and running in your system tray"; Windows "…in your
  Start menu and running in your system tray". The `anyscribe ui` line stays.
- **Settings → Startup** shows on all three OSes. Toggle label **"Start at
  login"**; caption **"Starts anyscribe in the menu bar (macOS) or system tray
  (Windows, Linux) when you log in."** Rebuild `web/static`.
- **`install-service` / `uninstall-service`** lose the macOS-only refusal.
- **Docs** (same PR): `docs/user/getting-started.md` (two install methods; the
  "Keep it running" section becomes desktop mode), `commands.md` (new
  `anyscribe desktop` section), `troubleshooting.md` (ffmpeg missing from a
  login-started tray; GNOME hides tray icons, use the app-menu icon; Windows
  shows no SmartScreen prompt because nothing is downloaded), `agents.md`
  (Claude works with the app closed), README install section, landing page
  install copy, skill `SKILL.md` + `references/commands.md` +
  `references/troubleshooting.md`, `CHANGELOG.md` 0.18.0, `BACKLOG.md` (0.18.0
  row + parked "signed downloadable app" item), `docs/building/architecture.md`
  (desktop surface), journal entry + `_index.md`, `scripts/build-docs.py` run.
- **CI.** `ci.yml` gains two small jobs: `macos-latest` and `windows-latest`
  running `pytest tests/test_desktop.py tests/test_launcher.py tests/test_tray.py`,
  so the real `iconutil` and the real `.lnk` creation are exercised.

## 5. Out of scope (parked in BACKLOG)

Signed downloadable installers (Tauri shell, SignPath Foundation for Windows,
Apple Developer Program); bundling ffmpeg/Deno/yt-dlp inside the app; in-app
self-update; reaching the dashboard from other devices; tray restarting a
crashed *server* (menu "Restart server" stays manual).

## 6. Known limits (documented, not fixed)

- GNOME without the AppIndicator extension shows no tray icon; the server still
  runs and the app-menu icon opens the dashboard.
- Reinstalling Python breaks the recorded interpreter path; `desktop status`
  says so and `desktop install` fixes it.
- `desktop open` under `pythonw.exe` has no console, so its errors go only to
  `~/.anyscribe/logs/tray.log`.
