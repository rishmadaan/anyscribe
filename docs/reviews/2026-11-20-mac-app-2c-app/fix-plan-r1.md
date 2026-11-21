# Fix plan, round 1 (the lead's choices; binding where it decides)

**C1 + F2 + F5 (the app's engine must never be the uninstall's target; a stable port).**
- The app keeps its port: the first port it successfully runs on is saved in the app's userData settings and reused on every launch, unless that port is now one the old launcher records (below) or is taken (then the existing "Couldn't start" rule applies). This replaces choosing from desktop.json alone.
- "The ports the old launcher records" means every one the engine's own `desktop uninstall` could target, read the way the engine reads them: the desktop.json manifest's port, the LaunchAgent plist's port, and the engine's default 8457. A first choice avoids all of them.
- `oldLauncher.remove()` computes the port the uninstall would target with the engine's exact rule (manifest port, else the login item's port, else 8457). If it equals the app engine's current port, refuse: run nothing, return `ok: false` with the reason "The old launcher is set to the same port as this app, so removing it now would stop this app's engine. Quit anyscribe, then run `anyscribe desktop uninstall` in Terminal." Test that refusal (uninstall never invoked) and the normal path; mutation-test the refusal.
- Record in the journal and architecture.md that the engine-side protection (an uninstall that never signals the app's port) is not built and why the desktop refusal is enough for now.

**C2 (held files are never lost).** Deliver each held file with an id and keep it until the dashboard acknowledges it (`onOpenFile` callback runs, then the preload sends an ack with that id); an unsubscribe or a page reload before the ack leaves it held for the next subscriber; an ack for an unknown id is ignored, so no file is delivered twice. Tests: subscribe then unsubscribe at once (the file is still delivered to the next subscriber), reload during delivery, double ack.

**C3 (skill truth).** A failed install is visible whatever files remain: status carries `skill: "missing"` with the failure reason until a later install succeeds; "installed" only after the most recent install attempt succeeded (or none was needed). Test with an existing older skill plus a failing install.

**C4 (ownership survives a failed refresh).** Write the new command first (temp file, then rename), and only after the rename succeeds record the new hash; on failure the previous record stays. Test a refresh whose write or rename fails, then a normal turnOff restoring the original.

**C5 (carry-over is verified).** After `setStartAtLogin(true)`, read the system state back; `startAtLoginCarriedOver` is true only when it reads enabled; otherwise return the state ("requires approval in System Settings, Login Items") as the reason. Test the approval-required case.

**C6.** On macOS `installed` is true when any piece remains, including a live old tray alone. Test the tray-only case.

**F1 (Switch only when it can work).** `terminal.status()` adds `occupant: {path, via, version} | null`: whatever sits at ~/.local/bin/anyscribe when it is not ours. When ours is written but the login shell finds another copy first, status carries the reason "Terminal finds another anyscribe at <path> first." and `uses` names it. Update desktop/README.md and both packets' bridge-v2.md (the lead updates 2c-ui's copy). One unit test per case: (a) another copy first elsewhere on PATH, (b) a uv copy at ~/.local/bin with ~/.local/bin off PATH.

**F3.** Add to the journal's "Not done here" and to docs/building/architecture.md's open items: the skill is not refreshed when the app updates (phase 3 re-copies it after each update while the switch is on); the command embeds the Python path, so moving the app breaks it until the switch is turned on again (phase 3: re-write the command on launch when the path changed).

**F4.** No code. Record in the journal: 2c-app and 2c-ui merge together (hiddenInset needs the dashboard's drag strip and padding).

**F6.** After appending, `addToPath` asks the login shell again; if ~/.local/bin is still not on PATH, return `ok: true` with the reason "The line is in <file>, but your shell setup removes it again later (check ~/.zshrc)." Test with an rc file that resets PATH.

## proof.md
Append "## Round 1 fixes (one entry per finding)": C1 to C6, F1 to F6 (F2 with C1, F4 records only): change | ran | saw, with mutation results for every new guard. Run npm test and the e2e (engine b22df16, exported read-only; give the wrapper's absolute path and the full command this time). Commit after each finding.
