# Bridge v2: what the dashboard can ask the app (shared contract for 2c-app and 2c-ui)

`window.anyscribeDesktop` exists only inside the Mac app. The dashboard in a browser has no bridge and must behave exactly as today.

Kept from v1 (desktop/README.md): `version`, `platform`, `getSettings()` gives `{dockMode, startAtLogin}`, `setDockMode(mode)`, `setStartAtLogin(on)`, `engineStatus()` gives `{state, port, lastExit, stoppedRestarting}`, `onEngineStatus(cb)` returns an unsubscribe function, `restartEngine()` gives `{ok, reason}`, `openLogFolder()`, `revealInFinder(path)`, `pathForFile(file)`.

New in v2 (all async unless said; every result carries `ok` and, when not ok, a plain-words `reason`):
- `terminal.status()` gives `{state, command, uses, appVersion, claudeCode, skill}`:
  - `state`: "off" (no command of ours), "on" (Terminal runs this app's copy), "other-copy" (Terminal runs a different anyscribe first), "path-missing" (ours is written but the login shell does not look in ~/.local/bin).
  - `command`: the path of our command when written, else null.
  - `uses`: what Terminal runs first: `{path, version, via: "uv"|"pipx"|"pip"|"app"|"unknown"}` or null.
  - `claudeCode`: whether ~/.claude exists. `skill`: "installed" | "missing" | "not-applicable" (no Claude Code).
- `terminal.turnOn({replace: boolean})`: writes our command; `replace: true` is needed when another anyscribe sits at ~/.local/bin/anyscribe (it is backed up, never deleted). Installs the Claude Code skill when Claude Code is present. Gives the new status.
- `terminal.turnOff()`: removes our command only if it is still ours; puts back a command it replaced, only if nothing has replaced ours since; removes the skill only if no other anyscribe is left for Terminal. If our command was changed since, gives `{ok: false, needsChoice: "keep-current-or-restore", reason}` and changes nothing.
- `terminal.addToPath()`: appends one line to the login shell's profile (`~/.zprofile` for zsh, `~/.bash_profile` for bash) unless the line is already there; gives `{ok, file, line}`. The dashboard asks the person before calling it.
- `terminal.retrySkill()`: tries the skill install again.
- `oldLauncher.status()` gives `{installed, pieces: {launcher, loginItem, menuBarIcon}}`, each piece "present" | "absent" (menuBarIcon "running" | "not running").
- `oldLauncher.remove()`: runs today's `anyscribe desktop uninstall --json`, then checks each piece itself; gives `{ok, pieces: {launcher: "removed"|"still there", loginItem: "removed"|"still there", menuBarIcon: "stopped"|"still running"}, startAtLoginCarriedOver}`. ok only when all three are gone. When the old login item existed, the app's own Start at login is turned on (carried over).
- `firstLaunch.get()` gives `{oldLauncherAsked, terminalAsked}`; `firstLaunch.mark(key)` records one as asked (kept in the app's settings, so each question is asked once).
- `onOpenFile(cb)`: called with an absolute path when a file is dropped on the Dock icon or opened with the app; returns an unsubscribe function. Files that arrive before the dashboard subscribes are held and delivered on subscribe.

## Amendments (2026-11-20, from the 2c-app build and its round 1 review)
- `terminal.turnOff({choice: "keep-current" | "restore"})` answers a `needsChoice: "keep-current-or-restore"` result.
- A result may carry `ok: true` together with a `reason` (shell could not be asked; skill missing; the PATH line is there but has no effect): show it as information, not an error.
- `terminal.status()` adds `occupant: {path, via, version} | null`: what sits at ~/.local/bin/anyscribe when it is not ours. Offer "Switch to this app's copy" only when `occupant` is set. When ours is written but another copy comes first, status carries the reason "Terminal finds another anyscribe at <path> first."
- Never show "Terminal runs this app's anyscribe" unless `uses.via` is "app"; when `uses` is null (the shell could not be asked), show the reason instead.
- For bash, `addToPath` refuses when creating ~/.bash_profile would hide ~/.profile or ~/.bash_login, returning `ok: false` with the line to add by hand.
- `oldLauncher.remove()` can refuse with `ok: false` and a reason when the old launcher is set to this app's port; show the reason; no pieces change.
- `oldLauncher.remove()`'s `startAtLoginCarriedOver` is true only when the system confirms it; otherwise a reason says what macOS needs (approval in System Settings, Login Items).
- The engine's skill command is `install-skill`.

## Amendment 2 (2026-11-20, 2c-app round 3 design)
- `oldLauncher.remove()` pauses the app's engine: it refuses exactly like Restart engine (transcriptions running or waiting, the list unknown, a restart already pending) with that reason; otherwise the engine restarts around the removal, so the dashboard reloads during it. The old same-port refusal is gone.
- `oldLauncher.status()` adds `lastRemoval: {ok, pieces, startAtLoginCarriedOver, reason, at} | null`: the result of the most recent removal, kept by the app across the reload. After a reload, show the result card from `lastRemoval` (only when it is newer than the question being answered).
