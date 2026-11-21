# Spec: phase 2c-app, the app-side mechanics behind the new screens (desktop/)

Build bridge-v2.md's new members in the shell (desktop/src, preload, main), plus the macOS title bar. The screens that call them are slice 2c-ui, built in parallel against the same contract. The approved design is the mockup at the approved mockup (kept privately; its sha256 starts bcf26037) (final, sha bcf26037): sections 3 (old launcher), 4 (Terminal and Claude Code), 5 (drop on the Dock icon), 9 (Settings rows these feed) and its "For the build" list.

## 1. The Terminal command (bridge terminal.*)
- Our command is one small POSIX sh script at ~/.local/bin/anyscribe. First line after the shebang: a marker comment naming it as the Mac app's command with the app version. It sets ANYSCRIBE_APP=1, PIP_USER=1, PYTHONUSERBASE="$HOME/.anyscribe/runtime" (and, packaged, the app's bin folder first on PATH and ANYSCRIBE_ELECTRON), then execs the app's Python with `-m anyscribe "$@"` (in dev, the resolved ANYSCRIBE_DEV_PYTHON). These are the engine review's F2 requirements: without them, `anyscribe update` and local setup would write into the signed app.
- "Ours" means: the file carries the marker and its content hash matches the one the app recorded when it wrote it (recorded in ~/.anyscribe/runtime/terminal.json together with any file it replaced).
- What Terminal runs: ask the person's login shell (`$SHELL -lic`, with clear begin/end markers around the output, a 5 s timeout, and HOME kept) for `command -v anyscribe` and $PATH. Never parse a Terminal profile file to guess. If the login shell cannot be asked (timeout, error), say so in the status reason and treat PATH as unknown.
- turnOn: never overwrite a file that is not ours unless replace is true; with replace, move the other file (or symlink) to ~/.anyscribe/runtime/replaced/anyscribe and record what it was (symlink target or content hash). Then the skill: if ~/.claude exists, run `<python> -m anyscribe skill install` with the engine's environment; the skill is "missing" if that fails (the status says why).
- turnOff: remove ours only if it is still ours (marker and hash); put back what it replaced only if the path now holds exactly our file; otherwise touch nothing and return needsChoice. Remove the Claude Code skill (the folder `skill install` wrote) only when, after the removal, the login shell finds no other anyscribe.
- addToPath: append exactly `export PATH="$HOME/.local/bin:$PATH"` to ~/.zprofile (zsh) or ~/.bash_profile (bash), creating the file if missing, never twice, never another shell's file; any other login shell: return not ok with a reason ("Add ~/.local/bin to your shell's PATH by hand").
- The Terminal states in the mockup (section 4: offer, turned on, other copy, Terminal can't see it yet, skill couldn't be installed) must each be reachable from these results.

## 2. The old browser launcher (bridge oldLauncher.*)
- Pieces: the launcher `~/Applications/anyscribe.app`; the login item `~/Library/LaunchAgents/com.anyscribe.tray.plist`; the old menu bar icon (today's tray process: find how core/tray.py records it, for example its pid file, and check that pid is alive and is an anyscribe tray).
- remove: run `<python> -m anyscribe desktop uninstall --json` with the engine's environment, then check each piece yourself and report each one; ok only when all are gone. If the login item existed before removal, turn on the app's own Start at login (carried over) and report it.
- status works on any OS; remove is only offered on macOS (elsewhere `installed` is false).

## 3. First-launch flags (bridge firstLaunch.*)
In the app's settings (userData JSON, the same store as dockMode): oldLauncherAsked, terminalAsked. Never in ~/.anyscribe.

## 4. Files opened with the app (bridge onOpenFile)
`app.on('open-file')` (macOS; register it before ready) and files passed on a second launch: absolute paths, held until the dashboard subscribes, then delivered in order. File associations for the Dock icon are packaging (phase 3); this slice handles the event.

## 5. The dashboard window's title bar
On macOS the dashboard window uses `titleBarStyle: 'hiddenInset'` again, with the traffic lights placed to clear the sidebar's top strip; 2c-ui adds the drag region and the top padding in the same release. Other platforms keep the default title bar.

## 6. Residue from the 2b review to fold in
S4-A1: desktop/README.md says "Not answering" replaces the header only when it would otherwise read Ready. G11: delete the stray blank line in engine.js. G12: a restart overtaken by stop() reports "The engine was stopped." instead of "The engine didn't start.".

## Done bar
- Unit tests (node --test) for every rule above with a throwaway HOME (never the real ~/.local/bin, ~/.zprofile, ~/Library, ~/.claude): ownership by marker and hash; never overwriting a foreign file; backup and exact restore (symlink and regular file); turnOff refusing when ours was changed; skill removal only when no other anyscribe is left; addToPath idempotent and shell-specific; login-shell output parsing with noisy rc files; the three launcher pieces each checked; carry-over of Start at login; open-file events held until subscribe.
- Mutation-test each guard: the foreign-file guard, the still-ours check before turnOff, the restore-only-if-unchanged check, the no-duplicate PATH line, the skill-removal condition, each launcher piece check.
- npm test and the e2e (run as before, against the engine branch feat/mac-app-engine at b22df16, exported read-only) still pass. Add an e2e step for open-file if Electron allows sending one headless; otherwise say so.
- Docs: desktop/README.md (bridge v2), architecture.md "Mac app shell", the journal entry for 2c-app and its _index row.

## Round 3 design (the lead's choice after the diagnosis; binding)

**Old launcher removal pauses the app's engine.** `oldLauncher.remove()` runs the uninstaller inside `Engine.restart()`, as an optional step between the old child's exit and the relaunch:
- It refuses exactly as Restart engine does (running, waiting or unknown jobs; a restart already pending), with the same reasons, and runs nothing.
- After the app's engine (and its process group) has exited, run `<python> -m anyscribe desktop uninstall --json` with the engine's environment, wait for it (killing it after a timeout), check each piece, then relaunch the engine whether the uninstall succeeded or not. A quit during the gap spawns nothing. The menu reads "Restarting" during the gap, never "Couldn't start".
- The same-port refusal and its reason are removed. Port avoidance when choosing the app's port stays as tidiness; the plist reading is no longer safety-critical (keep its shortcut comment).
- The result is kept in the main process and returned by `oldLauncher.status()` as `lastRemoval: {ok, pieces, startAtLoginCarriedOver, reason, at}` until the next removal, because the dashboard reloads when the engine comes back. `remove()` still returns it when the page survives.
- If anything else holds the port when the engine restarts, the existing "Couldn't start: another program is using port N" applies, and that message also says the old launcher's removal ran (with its result).
- The 2b supervisor's rule holds: the explicit-stop-cancels-relaunch guarantee and the one-gate check also cover this new window (run is null while the state is "restarting").

**Command writes are committed by the record.** Exclusive-create (`wx`) random temp names in the same folder for both the command and the record; clean up only temps this call created. Order: write the command's temp; write the record (via its own temp) as `{sha256: new, previousSha256: old, replaced}`; move a foreign file aside if replacing; rename the command into place. `isOurs` accepts either hash. A failed record write leaves the command untouched; a crash at any point leaves ours ours.

**Tests (each mutation-tested):**
- A1: real engine export, a manifest on 8457, server.pid holding the app engine's pid; during the uninstall step the old engine pid is gone; afterwards a new engine answers with a matching pid and the crash count is zero. Mutation: run the uninstaller with the engine up.
- A2: the same with a binary plist on the app's port and the real uninstaller, where Linux runs that path; otherwise say Mac-only in proof.md.
- Jobs: running, waiting or unknown jobs refuse, the uninstaller never runs, the engine pid is unchanged.
- The gap: the state is never "stopped"; a quit in the gap spawns nothing; a second restart is refused.
- A3: plant a symlink at the temp name pointing at a profile file; its bytes and target are unchanged afterwards. Mutation: `wx` to `w`.
- A4: the runtime folder read-only from the start, then a refresh: the command's bytes are identical, it is still ours, and turnOff restores the uv link. Mutation: command before record.
- Crash window: a hand-written record holding the new and previous hash over the old command reads as ours. Mutation: drop previousSha256.

## Round 4 design (the lead's choice after the second diagnosis; binding)

- B1: the engine holds one flag while the removal step runs (set before `await run.before()`, cleared in `finally`). While it is set, `start()` returns false and `restart()` refuses with "The old launcher is still being removed." `stop()` keeps its contract. Keep `await step` in removePausingEngine.
- B2: run.js tracks the process groups of helpers that opt in (only the uninstaller does) and exports `killHelpers()`, which SIGKILLs each group synchronously. `will-quit` calls `engine.stopForQuit()` then `killHelpers()`. Quit stays instant; an interrupted removal leaves pieces that the next launch offers to remove again.
- Accepted and documented (journal and architecture.md, as a known limit): a force quit, crash or power loss during the uninstall, followed by reopening anyscribe within about 25 seconds, can let the old uninstaller stop the new engine once; the supervisor restarts it. A durable cross-instance reservation is not built.
- B3: removal.e2e.js expects `'removed'` for the login item on macOS (and `result.ok === true`), `'still there'` elsewhere.
- Tests (mutation-tested): B1 with the seams (step held; restart({between}); stop(); start() resolves false; restart() returns the reason; only the first pid spawned; release; start() then works; a throwing step leaves start() working; mutants: drop the check in start(), in restart(), drop the finally). B2 unit: an opted-in helper with a grandchild, killHelpers(), both pids gone, a non-opted helper alive (mutant: empty killHelpers()). B2 integration in removal.e2e.js with the binary-plist fixture: delay the real uninstaller 3 s, stopForQuit() plus killHelpers(), a second Engine on the same home, after 5 s its health pid matches and no crash is recorded (mutant: omit killHelpers()).

## Round 5 design (the lead's choice after the third diagnosis; binding)

- The ports the app avoids (first choice, reuse of a saved port) are: every port the old launcher's files record, read exactly (on macOS `/usr/bin/plutil -extract ProgramArguments json -o - <plist>`; if plutil fails, the XML read; then unknown), the manifest's port, 8457, and the live old tray's own port from its command line (`--port N` or `-p N`, else 8457). A live tray whose port cannot be read: avoid 8457 and log it; never refuse to start for this.
- The uninstaller's target port is read the same exact way (no longer safety-critical after the engine pause, but kept truthful).
- Documented known limit (journal and architecture.md): an old tray started after the app, on the app's own port, can still reach the app's engine during its own teardown.
- Tests (mutation-tested): with a reader seam, a binary plist read through fake plutil JSON gives 8470; plutil failing falls back to the XML read; no files plus a live tray whose command line has `--port 8470` makes the app pick 8471; `-p 8470` likewise. Mutants: drop the plutil call; drop the tray's own port from the avoid list. Update removal.e2e.js's A2 so it no longer asserts the shortcut's miss (the app now avoids 8470 there; keep the A2 removal check itself). Record that the real plutil call is Mac-only and is checked in the Mac walk.
