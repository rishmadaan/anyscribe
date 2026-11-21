---
type: decision
tags: [desktop, electron, mac-app, terminal, claude-code-skill, desktop-mode]
tldr: "Slice 2c-app gives the Mac app's new screens their mechanics: bridge v2 (terminal.*, oldLauncher.*, firstLaunch.*, onOpenFile) and the hiddenInset title bar. The Terminal command at ~/.local/bin/anyscribe is ours only by marker and recorded hash; a foreign one is moved aside, never overwritten or deleted, and put back on turn-off only while ours is untouched. What Terminal runs comes from the login shell itself. The spec's `skill install` is really `install-skill`: the e2e against the real engine caught it."
---

# Mac app, slice 2c-app: Terminal, old launcher, first launch, opened files

## What was built

Bridge v2 in `desktop/` (contract in `desktop/README.md`), behind the approved
mockup's sections 3 (old launcher), 4 (Terminal and Claude Code), 5 (drop on
the Dock icon) and 9 (the Settings rows these feed). The screens themselves
are slice 2c-ui, built in parallel against the same contract.

- `src/terminal.js`: the Terminal command, what Terminal runs, the skill.
- `src/old-launcher.js`: the old browser launcher's pieces and their removal.
- `src/run.js`: one helper that runs a short command in its own process group
  with a timeout, used for the login shell, `--version`, `install-skill` and
  `desktop uninstall`.
- `main.js`: the new IPC handlers (Terminal and launcher calls one at a time),
  first-launch flags in the app's `settings.json`, `open-file` and second-launch
  files held until the dashboard subscribes, `hiddenInset` on macOS.
- 2b residue: a restart overtaken by a stop says "The engine was stopped."
  (G12), a stray blank line (G11), the README's Not-answering sentence (S4-A1).

## Decisions

- **Ownership is marker plus recorded hash.** A file with our marker that was
  edited, or one we never recorded, is not ours. That is what lets turn-off
  refuse to delete or overwrite anything the person changed.
- **Ask the login shell, never parse profiles.** `$SHELL -lic` with a fixed
  starting PATH (what a new Terminal window starts from), random begin and end
  markers so rc-file noise cannot be mistaken for the answer, and a 5 s limit.
  The shell runs in its own process group and the group is killed afterwards,
  so a noisy rc file cannot leave anything running. When the shell cannot be
  asked, PATH is unknown, the status says so, and an unknown is never read as
  "no anyscribe" (the skill is kept).
- **Nothing is deleted.** A replaced command goes to
  `~/.anyscribe/runtime/replaced/anyscribe`; an older backup there is renamed
  with a timestamp, not overwritten; restoring over an edited command first
  moves the edited one aside.
- **Bash `~/.profile` users are left to do it by hand.** Creating
  `~/.bash_profile` would stop bash reading `~/.bash_login` or `~/.profile`, so
  `addToPath` refuses in that case and gives the line.
- **`install-skill --force`.** The engine's command is `install-skill` (the
  spec said `skill install`; the unit tests' stand-in Python accepted the wrong
  form, the e2e against the real engine did not). `--force` so the skill
  matches the copy Terminal now runs; without it an older skill left by another
  copy stays.
- **turnOff answers its own question.** The contract's `needsChoice` had no
  way to answer it; `turnOff({choice: "keep-current" | "restore"})` is the
  additive answer the Settings buttons need. With nothing to put back, a
  changed command is simply left alone (no question with one answer).
- **Carry-over of Start at login** happens when the old login item was there
  before and is gone after, so a failed removal never leaves two login items.

## Tests

`npm test`: 85 tests, including the Terminal rules against throwaway homes and
the real zsh and bash with noisy profiles, a hanging shell, uv/pip/symlink
copies, and the old launcher's pieces with a real process carrying a tray's
command line. The e2e (15 steps) adds bridge v2 through the real app: Terminal
turned on with the real engine's `install-skill` into a throwaway `~/.claude`,
"Terminal can't see it", Add to PATH, on, off; and opened files (an
`open-file` emitted in the main process while the window is hidden, then a
second launch naming a file). Every guard was mutation-tested; see the
review packet's `proof.md`.

## Not checked here (needs a Mac)

The traffic-light position against the real sidebar, `open-file` from a real
Dock drop, `desktop uninstall` removing a real LaunchAgent and tray, and the
login shell on macOS (`/etc/zprofile` and `path_helper`).

## Round 1 review fixes

- **The uninstall must never reach the app's engine (C1, F2, F5).** `desktop
  uninstall` stops whatever anyscribe answers on the old launcher's port, read
  as the engine reads it: the manifest's port, else the login item's last
  argument, else 8457. A partial install (no manifest, a login item and a live
  tray on 8470) made the app pick 8470 too. Now the app avoids every port the
  old launcher records, keeps the port it last ran on in its own settings (so
  the dashboard's per-port browser storage does not reset when the old
  launcher goes), and `oldLauncher.remove()` refuses, running nothing, when
  the uninstall's target is its engine's port. Not built: the engine-side
  protection (an uninstall that never signals the app's port). The app starts
  the uninstall itself and knows its port, so the refusal covers every path
  the app can reach; a person running `anyscribe desktop uninstall` by hand in
  Terminal while the app runs on the old port is the remaining case.
- **Opened files need a receipt (C2).** `webContents.send` is not delivery:
  a subscribe followed at once by an unsubscribe lost a held file. Each file
  now carries an id and is kept until the page acknowledges it after its
  callbacks ran.
- **The status tells the truth after failures (C3, C4, C5, C6, F1, F6).** A
  failed skill install reads "missing" even over an older skill folder; a
  refreshed command's hash is recorded only after the file is in place; Start
  at login counts as carried over only when macOS reads it back enabled; a live
  old tray alone counts as the old launcher installed; `terminal.status()`
  names the `occupant` that "Switch" would replace and which copy Terminal
  finds first; `addToPath` says when a later rc file undoes its line.

## Not done here

- **The skill is not refreshed when the app updates.** The app's command
  runs with `ANYSCRIBE_APP=1`, which skips the engine's skill auto-update; only
  Turn on and Try again write it. Phase 3 re-copies it after each update while
  the switch is on.
- **The command embeds the Python path.** Moving the app breaks the Terminal
  command until the switch is turned on again. Phase 3: rewrite the command at
  launch when the path changed.
- **2c-app and 2c-ui merge together, never alone (F4).** The `hiddenInset`
  title bar needs the dashboard's drag strip and top padding from 2c-ui; on its
  own the Mac window cannot be dragged and the sidebar's top row sits under the
  traffic lights.

## Round 3: remove the target, commit by the record

Round 2 found two more ways the uninstall reached the app's engine: a stale
`server.pid` reused by the engine's pid (the uninstall kills it by pid, not by
port), and a binary LaunchAgent plist the app's XML reading could not parse
(Python's `plistlib` can). The diagnosis: each fix guarded a model of the
uninstaller, and every launcher test swapped the uninstaller for a stand-in, so
the tests proved the model agrees with itself. The fix removes the target
instead: removal runs inside `Engine.restart()`, between the old engine's exit
and the relaunch, so there is no engine for any of the uninstall's three kill
paths to reach. The same-port refusal is gone. Two tests now run the real
`desktop uninstall` from the engine against the real engine (stale `server.pid`;
binary plist with a live tray); with the uninstaller run while the engine is
up, both record an unexpected engine exit.

Command writes had two files and no single commit point. Now the record
commits: fresh temp names created exclusively, the record first (new hash,
previous hash still accepted), then the file moves.

A gate right after the removal step turned out to be an equivalent mutant: the
existing gate after the port check already stops a cancelled run, so it was
not kept.

## Round 4: the pause lives as long as the uninstaller

Round 3's pause belonged to the run object, which a stop or quit discards while
the uninstaller process lives on. Two fixes tie it to the step and the helper
instead:

- **No start while the step runs (B1).** The engine holds `stepRunning` from
  before the step to its `finally`; `start()` returns false and `restart()`
  says "The old launcher is still being removed." A stop keeps its contract.
- **Quitting ends the uninstaller (B2).** `run.js` keeps the process groups of
  helpers that opt in (only `desktop uninstall`), and `will-quit` calls
  `engine.stopForQuit()` then `killHelpers()`, which SIGKILLs them without
  waiting, so quit and logout stay instant. An interrupted removal leaves
  pieces; the next launch reads them and offers removal again (`lastRemoval`
  is memory only).

**Known limit, accepted:** a force quit, crash or power loss during the
uninstall skips `will-quit`. If anyscribe is reopened within about 25 seconds,
the orphaned uninstaller can stop the new engine once (by its port or
`server.pid`); the crash supervisor restarts it. A durable reservation across
app instances would be a hand-made lock-file protocol, so it is not built.

The integration test holds the real uninstaller until the new engine answers;
without `killHelpers()` it stops that engine every time.

## Round 5: the old tray's own port

The uninstall's SIGTERM starts the real old tray's teardown, which posts a
shutdown to the port in the tray's own command line. That request lives in the
tray's process group, so quitting (which kills only the uninstaller's group)
does not stop it, and a reopened app on that port could be shut down (D1, a
normal quit, not the accepted force-quit case). Files and the live tray can
disagree (an edited or deleted plist, a reinstall with another `--port`, a tray
started by hand), so the app now avoids the live tray's own port too (`--port
N`, `--port=N` or `-p N`, else 8457; unreadable: avoid 8457, log it, start
anyway), and reads the login item exactly with `/usr/bin/plutil -extract
ProgramArguments json -o -` on macOS (a reader seam in tests), falling back to
the XML read, then unknown. The real plutil call runs only on a Mac; it is
checked in the Mac walk.

**Known limit, accepted:** an old tray started after the app, on the app's own
port, can still reach the app's engine during its own teardown.
