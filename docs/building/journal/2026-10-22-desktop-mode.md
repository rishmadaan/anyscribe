---
type: feature
tags: [desktop, tray, installers, launchd, windows, linux]
tldr: "v0.18.0 adds desktop mode: `anyscribe desktop install` writes an app launcher and a login item with each OS's own plain files, starts the tray and opens the dashboard; the one-line installers run it by default. No signed downloadable app: a locally built .app carries no quarantine attribute, so no Gatekeeper or SmartScreen prompt and no certificate. The launchd login item runs as ProcessType Interactive after measuring a plain job throttling /api/health to 5-13 s."
---

# v0.18.0: desktop mode

## The problem

Until now, "anyscribe is always there" meant a user had to know that a web
server exists (`anyscribe ui`), that a tray can supervise it (`anyscribe
tray`), and that a login item can start the tray (`anyscribe install-service`,
macOS only). The tray also crashed on Windows, and a tray started at login on
macOS could not find ffmpeg or Deno. The goal: install once, never learn that
any of those pieces exist.

Design: `docs/superpowers/specs/2026-10-22-desktop-mode-design.md` (approved
by the owner over three rounds, 2026-10-22). Plan:
`docs/superpowers/plans/2026-10-22-desktop-mode.md`.

## Decisions

1. **No signed, downloadable app (for now).** The researched route was a
   Tauri shell around a PyInstaller-frozen Python (read of T3 Code's release
   pipeline and Voicebox's build docs; Microsoft's code-signing options page,
   2026-08-29). It needs an Apple Developer Program membership for
   notarization and a Windows certificate (SignPath Foundation is the free
   route for open source), and a frozen-Python build per OS. Desktop mode
   instead builds the launcher on the user's own machine. **Evidence, a live
   probe on this Mac:** a locally created `.app` launches with no Gatekeeper
   prompt and `xattr` shows no `com.apple.quarantine` attribute on it; nothing
   pip installs carries that attribute either. Quarantine is stamped by the
   app that downloads a file (browsers, mail), so a file written by our own
   Python never gets it. The same holds on Windows: SmartScreen keys off the
   Mark of the Web, which only downloaded files carry. The signed app is
   parked in `BACKLOG.md`.
2. **No money, no new accounts, no new runtime dependencies.** Each OS's own
   plain-file mechanism holds the launcher and the login item (`.app` bundle
   and LaunchAgent plist; `.lnk` shortcuts made through PowerShell's
   `WScript.Shell` COM object; XDG `.desktop` files). Pillow, already in the
   `[tray]` extra, renders icons; macOS's bundled `iconutil` makes the
   `.icns`.
3. **Claude Code is unaffected by whether the app runs.** The skill and the
   MCP server run the pipeline in-process and exit; the dashboard reads
   history from the vault on disk. No code change; the docs say so.
4. **One command owns it:** `anyscribe desktop {install, uninstall, status,
   open}`. `install-service` / `uninstall-service` stay as the login-item-only
   commands, now on all three OSes, and the Settings → Startup toggle calls
   the same `core/service.py`.
5. **Version 0.18.0** (minor): a new install method is a milestone. Release
   (tag + PyPI) is a separate, owner-gated step.

## The launchd measurement: `ProcessType Interactive`

The first macOS login item was a plain LaunchAgent. Started that way, the
dashboard was sluggish: `/api/health` (which spawns ffmpeg and yt-dlp to check
them) took **4.8-12.7 s** from the plain launchd job,
against **0.32-0.35 s** with `ProcessType Interactive` and **0.38-0.48 s**
from a terminal start. `/api/providers`, which spawns nothing, was about 3 ms
either way, which located the cost in child processes: launchd's default
process type throttles a background job's children. Transcriptions are child
processes too, so the key is not cosmetic. The plist now carries
`ProcessType Interactive` alongside `EnvironmentVariables.PATH`,
`KeepAlive {SuccessfulExit: false}`, `ThrottleInterval 60` and a log at
`~/.anyscribe/logs/tray.log`.

## What shipped

- `core/launcher.py`: icons, app launcher per OS (`~/Applications/anyscribe.app`
  with `LSUIElement`; Start-menu `anyscribe.lnk` to `pythonw.exe`;
  `~/.local/share/applications/anyscribe.desktop`), each running
  `<python> -m anyscribe desktop open`.
- `core/service.py`: login item on macOS, Windows (Startup-folder
  `anyscribe tray.lnk`) and Linux (`~/.config/autostart/anyscribe-tray.desktop`
  with `Exec=env PATH=…`). `service_path()` gives login-started processes the
  installing shell's PATH plus the usual install directories (the fix for
  "ffmpeg missing" from a login-started tray). Removing a login item never
  stops a running tray; on macOS it skips `launchctl unload` while a tray is
  alive, so the toggle does not kill the dashboard it sits in.
- `core/desktop.py` + `cli/desktop_cmd.py`: install (icons → launcher → start
  → login item → manifest `~/.anyscribe/desktop.json`), uninstall (stop tray
  and server first, then remove everything; never the vault, config or keys),
  status (`healthy` + `reason`, including "Partly installed" and a vanished
  recorded Python), open (health probe, foreign-port refusal, detached tray
  with a bare-`ui` fallback, URL on stderr when no browser). Exit codes 0 / 1
  refused or failed / 2 unsupported platform; `status` always 0.
  Install-order fix (same day): on macOS the login item now comes before the
  start, and `open_dashboard(expect_external=True)` waits up to 10 s for
  launchd's RunAtLoad tray before spawning one; a tray we spawned sat outside
  launchd, so `launchctl unload` missed it and KeepAlive crash restart only
  applied after the next login. Windows and Linux keep start → login item.
- `core/tray.py`: Windows guards for `pthread_sigmask`, `sigwait` and
  `preexec_fn`; a second tray exits 0 (a non-zero exit under `KeepAlive`
  would relaunch every minute); `stop_tray(port)`.
- Installers: `install.sh` ends with `desktop install --yes` unless
  `--no-desktop` (git-method installs skip it and say why); `install.ps1` has
  `-NoDesktop`, passed through `& ([scriptblock]::Create((irm <url>)))`
  because `irm | iex` cannot take switches. A failed desktop step warns and
  leaves the plain banner.
- Settings → Startup on all three OSes, labelled "Start at login". The
  tray-missing refusal reads the same on every surface: "The tray isn't
  installed. Run: pip install "anyscribe[tray]" first."
- CI: a `desktop-platforms` job runs the desktop, launcher and tray tests on
  macOS and Windows, so the real `iconutil` and `.lnk` creation run.

## Known limits (documented, not fixed)

- GNOME without the AppIndicator extension shows no tray icon; the app-menu
  icon still opens the dashboard.
- Reinstalling Python breaks the recorded interpreter; `desktop status` says
  so and `desktop install` fixes it.
- `desktop open` under `pythonw.exe` has no console; its errors go only to
  `tray.log`.
- On macOS, turning Start at login off while the tray runs leaves launchd's
  job loaded until logout (a crash still relaunches it; turning it back on in
  the same session does not start a second tray).

## Parked

Signed downloadable app (Tauri + SignPath Foundation + Apple Developer
Program), bundling ffmpeg/Deno/yt-dlp, in-app self-update, remote access to the
dashboard, and the tray restarting a crashed server. All in `BACKLOG.md`.
