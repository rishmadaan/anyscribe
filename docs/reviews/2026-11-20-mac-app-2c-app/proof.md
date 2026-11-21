# Proof: phase 2c-app (desktop/), round 0

Worktree `~/labs/projects/anyscribe-wt/mac-2c-app`, branch `feat/mac-app-2c-app`, based on df94f5b (checked before editing). Code head: 3d1b6e0; docs head c882b27; this file is committed after it.

Engine for every e2e run: `feat/mac-app-engine` at **b22df16**, exported read-only (`git archive b22df16 src`, files made read-only) into the session scratch folder and run through a wrapper that execs `~/labs/projects/anyscribe/.venv/bin/python` with `PYTHONPATH=<scratch>/engine/src`. The e2e was run as `env -i HOME=$HOME PATH=/usr/bin:/bin ANYSCRIBE_DEV_PYTHON=<wrapper> node test/e2e.js` (headless Electron, throwaway HOME under `desktop/test/.tmp`, no window on the owner's display).

## Commits

| Commit | What |
|---|---|
| da06400 | Packet committed first |
| b7e0c10 | 2b residue: G12, G11, S4-A1 |
| 86f1ef8 | `terminal.js`, `run.js`, Terminal tests |
| 7150c5a | `old-launcher.js` and its tests |
| da99e86 | `install-skill` (not `skill install`), caught by the e2e; error lines skip rich box borders |
| 3d1b6e0 | Bridge v2 wired in `main.js` and `preload.js`; first-launch flags; opened files; hiddenInset; logic tests; e2e steps |
| c882b27 | Docs: `desktop/README.md`, `architecture.md`, journal entry, `_index.md` row |

## Spec sections

| Section | Built | Where | How it was checked |
|---|---|---|---|
| 1. Terminal command (`terminal.*`) | Yes | `src/terminal.js`, `src/run.js`, `main.js` handlers, `preload.js` | `test/terminal.test.js` (24 tests); e2e step 1b against the real engine |
| 2. Old launcher (`oldLauncher.*`) | Yes | `src/old-launcher.js`, `main.js`, `preload.js` | `test/old-launcher.test.js` (8 tests); e2e step 1b (status on Linux) |
| 3. First-launch flags (`firstLaunch.*`) | Yes | `logic.parseSettings`, `main.js` (userData `settings.json`) | `test/logic.test.js`; e2e step 1b reads the file back |
| 4. Opened files (`onOpenFile`) | Yes | `logic.OpenFiles`, `logic.openedFiles`, `main.js` (`open-file` before ready, `second-instance`), `preload.js` | `test/logic.test.js`; e2e step 3b |
| 5. Title bar | Yes | `main.js`: macOS `titleBarStyle: 'hiddenInset'`, `trafficLightPosition: {x: 16, y: 16}` (the mockup's sidebar padding 14 + 2 down, 12 + 4 in); other platforms unchanged | Code read only: not visible on Linux |
| 6. Residue S4-A1, G11, G12 | Yes | README sentence; blank line removed; `restart()` says "The engine was stopped." when a stop overtook it | S3-A1 test gained the G12 assertion |
| Docs | Yes | `desktop/README.md` (bridge v2 table, command, title bar, opened files), `docs/building/architecture.md`, `docs/building/journal/2026-11-20-mac-app-2c-app.md`, `docs/building/_index.md` | |

### How each Terminal state in mockup section 4 is reached

| Mockup state | Result that produces it |
|---|---|
| The offer | `status()` → `state: "off"` |
| Turned on | `turnOn()` → `ok: true, state: "on"` (`uses.via: "app"`, `uses.version` = app version) |
| Another anyscribe is already installed | `status()` → `state: "other-copy"`, `uses: {path, version, via: "uv"}`; `turnOn({replace: false})` with a file at `~/.local/bin/anyscribe` → `ok: false`, nothing touched |
| Terminal can't see the command yet | `turnOn()` → `state: "path-missing"`; `addToPath()` → `{ok, file, line}`; `status()` → `on` |
| Terminal is ready, the skill isn't | `turnOn()` → `ok: true, skill: "missing", reason: "Couldn't write to ~/.claude/skills (permission denied)."`; `retrySkill()` |
| Off puts things back / asks first | `turnOff()` → restored, or `{ok: false, needsChoice: "keep-current-or-restore"}`; answered with `turnOff({choice})` |

## Results

- `npm test` at c882b27: **85 tests, 85 pass, 0 fail** (50 before this slice; 35 new).
- e2e at c882b27 against b22df16: **15 of 15 steps pass** (12 before plus 3 new):
  - PASS firstLaunch and oldLauncher answer; a marked question is saved in the app's settings
  - PASS Terminal: turned on (real skill install), Terminal can't see it, added to PATH, on, turned off (anyscribe v0.19.0; `<e2e HOME>/.zprofile`)
  - PASS opened files are held until the dashboard subscribes, then delivered in order (open-file and a second launch) (talk.m4a, second launch.mp4)
  - and all 12 earlier steps, including "Stop and Quit quits at once" (33 ms).
- The e2e's first run failed twice, both real bugs, both fixed: `getSettings()` had started returning the first-launch flags (fixed to keep the v1 shape `{dockMode, startAtLogin}`), and the real engine rejected `skill install` (see "Spec problems").
- No process of this run was left afterwards. Four `anyscribe ui --port <random> --no-open` processes seen during the check belong to the 2c-ui slice's check script (cwd `mac-2c-ui/.../checks`, HOME `/tmp/anyscribe-2c-ui-*`); not touched.
- The owner's real files were checked after the runs: `~/.local/bin/anyscribe` and `~/.claude/skills/anyscribe` not modified since the packet commit; no `~/.zprofile`, `~/.bash_profile`, `~/.anyscribe/runtime`, `~/Applications` or `~/.config/anyscribe` exists.

## Mutation tests

Each mutant was applied to committed code, the named test run in a fresh `node --test` process, the file restored with `git checkout`, and the same test run again. All 15 failed as mutants and passed restored.

| Guard (spec name) | Mutant | Failing assertion | Restored |
|---|---|---|---|
| Foreign-file guard | `turnOn` without the `other && !replace` refusal | `✖ guard: turnOn never overwrites a file that is not ours without replace` / `AssertionError: refused` / actual `true`, expected `false` | pass |
| Still-ours check before turnOff | `const ours = lexists(f.command)` in `turnOff` | `✖ guard: turnOff refuses when ours was changed and something can be put back; then each choice` / actual `true`, expected `false`; and the "left as it is" test (the edited file was deleted: `The "string" argument must be of type string. Received ... null`) | pass |
| Restore only if unchanged | the needsChoice question removed (`if (false)`) | `✖ guard: turnOff refuses when ours was changed ...` / actual `true`, expected `false` | pass |
| No duplicate PATH line | the "already there" check removed | `✖ guard: addToPath writes one line ... never twice` / `AssertionError: once, on its own line` (the line appeared twice) | pass |
| Skill-removal condition (another copy left) | `if (sh.ok)` | `✖ guard: turnOff removes the skill only when Terminal is left with no anyscribe` / `AssertionError: kept: another anyscribe is left` | pass |
| Skill-removal condition (shell unknown) | `if (!sh.found)` | same test / `AssertionError: kept: unknown is not none` | pass |
| Ownership by hash | hash comparison removed from `isOurs` | `✖ ownership is the marker and the recorded hash ...` / `AssertionError: edited: hash differs` | pass |
| Launcher piece check | `launcher: 'absent'` | `✖ guard: remove checks the launcher itself; ok only when all three are gone` / actual `true`, expected `false` | pass |
| Login item piece check | `loginItem: 'absent'` | `✖ guard: remove checks the loginItem itself ...` / actual `true`, expected `false` | pass |
| Menu bar icon piece check | `menuBarIcon: 'not running'` | `✖ guard: remove checks the menuBarIcon itself ...` / actual `true`, expected `false` | pass |
| Tray command-line check | `trayRunning` returns true for any live pid | `✖ guard: the menu bar icon is running only when tray.pid names a live anyscribe tray` / `AssertionError: a reused pid is not a tray` | pass |
| Carry-over of Start at login | carried over whenever the login item is absent after | `✖ Start at login is carried over only when the old login item was there and is now gone` / actual `true`, expected `false` | pass |
| Open files held until subscribe | `add()` delivers only to a current subscriber | `✖ guard: files opened before the dashboard subscribes are held, then delivered in order` / `AssertionError: held ones, in order, on subscribe` (actual `[]`) | pass |
| Bash profile shadowing (added, see below) | the `.profile` refusal removed | `✖ addToPath: bash reading ~/.profile ...` / actual `true`, expected `false` | pass |
| G12 | the old reason line | `✖ guard: an explicit stop during a restart cancels its relaunch (S3-A1)` / `AssertionError: G12: it says the engine was stopped, not that it failed` / actual `"The engine didn't start."`, expected `'The engine was stopped.'` | pass |

## Spec problems (said, then built as noted)

1. **`skill install` does not exist.** The engine's command is `anyscribe install-skill` (`cli/main.py:224` at b22df16); `skill install` exits 2 with "Got unexpected extra argument(s) (install)". Built with `install-skill --force`. `--force` is my addition: without it an existing skill (an older one left by a uv copy) is reported "already installed" and stays stale after switching.
2. **`needsChoice` had no way to answer it.** The bridge's `turnOff()` takes no argument, but 2c-ui's spec draws "Keep current command" and "Restore previous command". Added `turnOff({choice: "keep-current" | "restore"})`. **2c-ui must call this form; the lead should reconcile the two slices.** When ours was changed and there is nothing to put back, the changed file is left alone with `ok: true` and a reason, instead of asking a question with one possible answer.
3. **Creating `~/.bash_profile` can break a bash user's setup.** bash reads only the first of `~/.bash_profile`, `~/.bash_login`, `~/.profile`; creating the first hides the others. `addToPath` refuses for bash when `~/.bash_profile` is missing and one of the others exists, and returns the line to add by hand.
4. **Carry-over timing.** The spec says "if the login item existed before removal"; built as "existed before and is gone after", so a failed removal never leaves both login items on.
5. **`desktop uninstall` can stop the app's own engine in one edge case** (not built around: `src/` is out of scope). `core/desktop.uninstall` posts `/api/shutdown` to the old launcher's port (the manifest's, else the login item's, else 8470) whenever `tray.pid` exists. The app picks 8471 only when `desktop.json` records 8470. With the manifest gone but the login item or `tray.pid` left (a partial install), both can be 8470, and the app's engine gets the shutdown (the supervisor then restarts it as a crash; a running job would be lost). Fix belongs in the engine (skip the HTTP shutdown when `ANYSCRIBE_APP=1`, or let the app pass the port to leave alone).
6. **Status reasons with `ok: true`.** The contract says reason "when not ok"; the spec also wants the status to say why (shell unknown, skill missing). Built: `reason` may accompany `ok: true`; documented in the README.

## Interpretations worth a look

- `state` when ours is written but the login shell could not be asked: `"on"`, with `uses: null` and a reason. The enum has no "unknown".
- An alias or shell function named anyscribe counts as another copy: `uses: {path: null, version: null, via: "unknown"}`.
- `uses.version` for another copy comes from running it with `--version` (5 s limit); null if that fails.
- The skill is installed only by `turnOn` and `retrySkill`, never at app start ("No surprise skill"; the engine itself skips it under `ANYSCRIBE_APP=1`). Nothing updates the skill when the app updates; that is phase 3's.
- The command embeds the Python path. If the app is moved, the command breaks until turned on again (not handled; phase 3).
- A second launch's file arguments: `argv` minus the binary, flags, relative paths and anything that is not a file.

## Not checked (Mac-only, or not visible here)

- The traffic lights' position against the real sidebar and 2c-ui's drag strip.
- `open-file` from a real Dock drop or Finder "Open With" (the e2e emits the event in the main process and uses a real second launch with a file argument on Linux).
- `desktop uninstall --json` removing a real LaunchAgent, `.app` and tray on macOS (unit tests use a stand-in; the real command was not run, to keep the owner's machine untouched).
- The login shell on macOS: `/etc/zprofile`'s `path_helper`, a GUI app's `SHELL`, Gatekeeper's first-run delay of the packaged Python against the 5 s `--version` limit.
- `ps -ww` command-line reading on macOS (Linux reads `/proc`).
- fish and other shells: `addToPath` refuses them; reading their PATH is best effort (fish prints a list, not a colon string).

## Round 1 fixes (one entry per finding)

Branch started at 09cdc11; code head 96d996b. Every mutant was applied to committed code, the named test was run in a fresh `node --test` process (or a fresh e2e run), the file was restored with `git checkout`, and the test was run again. Every mutant failed, and every restored run passed. The mutation logs are in the session scratch folder (`mutants-r1.log`, `e2e-mutant1.log`, `e2e-mutant2b.log`).

**How the e2e was run.** Wrapper: `<lead scratch folder>/engine-python`. It contains:
```sh
#!/bin/sh
PYTHONPATH=<lead scratch folder>/engine/src exec ~/labs/projects/anyscribe/.venv/bin/python "$@"
```
`engine/src` comes from `git -C ~/labs/projects/anyscribe archive b22df16 src | tar -x -C <scratch>/engine`, made read-only with `chmod -R a-w`. The command, from `~/labs/projects/anyscribe-wt/mac-2c-app/desktop`:
```sh
env -i HOME=$HOME PATH=/usr/bin:/bin ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python node test/e2e.js
```

**Results at 96d996b.** `npm test`: 94 tests, all 94 pass (85 before). e2e: 15 of 15 steps pass; step 3b now also covers the C2 races. No process was left afterwards. The owner's `~/.local/bin/anyscribe` and `~/.claude/skills/anyscribe` were not modified. There is still no `~/.zprofile`, `~/.bash_profile`, `~/.anyscribe/runtime`, `~/Applications` or `~/.config/anyscribe`.

| Id | Change | Ran | Saw (mutants: failing assertion, then restored) |
|---|---|---|---|
| C1 (with F2; blocker) | 2a5e322. `old-launcher.js`: `uninstallTarget(home)` follows the engine's rule (the manifest's port, an empty manifest counting as none as in Python, else the login item's last ProgramArguments entry, else 8457); `recordedPorts(home)` lists all three. `remove()` gets `enginePort` and refuses, running nothing, when the target equals it, with the plan's reason. `engine.js` `pickPort(home, saved)` avoids every recorded port. Journal and architecture.md say the engine-side protection is not built, and why. | `old-launcher.test.js` "uninstall target: the manifest port, else the login item port, else 8457" and "guard: remove refuses, running nothing, when the uninstall would target this app's port (C1)". The second sets up the reviewer's partial install: no manifest, the login item on 8470, a live tray, engine on 8470. `engine.test.js` pickPort with that plist. `logic.test.js` port test. | The refusal leaves the tray running and the uninstall never called; with another engine port, removal goes ahead. Refusal removed: `AssertionError: desktop uninstall was never run` (actual `true`). Ports not avoided (`avoid: []`): pickPort `+ port: 8470 / - port: 8471`. A saved port kept even though the old launcher now records it: `never a port the old launcher now records` (actual 8470, expected 8471). |
| C2 | 882f096, d04f408, 5c518bb, 96d996b. `logic.OpenFiles` keeps `{id, file}` items until `ack(id)`; a subscriber gets every item not yet acknowledged; an unknown or repeated ack does nothing. `main.js` adds `openFile:ack` (dashboard window only). The preload acknowledges only after the page's callbacks ran, sends no ack when no callback is subscribed, and hands a given id over once per page. I first removed that seen-id set as untestable (2354f11). That claim was wrong: subscribe, unsubscribe and subscribe again in one tick makes the app send the file twice. I reverted the removal (d04f408) and the e2e now covers that case. | `logic.test.js` "guard: a file is kept until the dashboard acknowledges it (C2)": subscribe then unsubscribe, a reload during delivery, double and unknown acks, no resend after an ack. e2e step 3b: (a) subscribe and unsubscribe at once, wait; (b) in one tick subscribe, unsubscribe, subscribe again, then check the file was handed over exactly once; then a second launch with a named file. | Unit mutant (held items dropped once sent): `AssertionError: the next subscriber still gets it` (actual `[]`). e2e mutant 1 (ack sent with no callback subscribed): `FAIL Error: timed out waiting for the held file on subscribe`. e2e mutant 2 (seen-id check removed): `FAIL AssertionError: handed over once, though sent twice` (talk.m4a twice). Restored: e2e 15/15. |
| C3 | c632497. `skillState(f, rec)` reads "missing" while the latest install recorded an error, whatever files remain. `installSkill` also counts it a failure when exit 0 left no SKILL.md written since the attempt began (2 s of slack). | `terminal.test.js` "guard: a failed update over an older skill reads missing, with the reason, until an install succeeds (C3)". It covers an older SKILL.md (mtime an hour old) plus a permission failure, then an exit 0 that wrote nothing, then a real success. | Error check removed: `the older SKILL.md does not make it installed` (`+ 'installed' - 'missing'`). The "written this time" check removed: the exit-0 step reads `+ 'installed' - 'missing'`. |
| C4 | 0ddaf89. `turnOn` writes the new command to a temp file, then renames it over ours or hard-links it into an empty spot (fails if something appeared). It records the new hash only after that. On failure the temp file is removed, an unrecorded link is taken back out, and a moved-aside copy is put back. The previous record stays. | `terminal.test.js` "guard: a refresh that cannot be written keeps ours ours, and turnOff still restores the original (C4)". It turns on over a uv symlink, makes `~/.local/bin` read-only, and refreshes with another Python path and version. | The refresh fails with EACCES, the command and its record are unchanged, and turnOff puts the uv symlink back. Record written first again: `AssertionError: and still recorded as ours` (the two hashes differ). |
| C5 | 2a19fe1. `remove()` gets `loginItemState()` (main.js: `getLoginItemSettings().status`, else `openAtLogin`). After `setStartAtLogin(true)`, `startAtLoginCarriedOver` is true only when the state reads `enabled`. `requires-approval` gives the reason "This app is set to start at login, but macOS needs your approval: System Settings, General, Login Items." Any other state is named in the reason. `startsAtLogin()` now reads through the same helper. | `old-launcher.test.js` "guard: Start at login counts as carried over only when the system reads it back enabled (C5)" | Approval-required case: `ok: true`, carried over false, the approval reason. Read-back replaced by `'enabled'`: actual `true`, expected `false`. |
| C6 | 3f72b35. `installed` on macOS counts any piece left, including a running old tray alone. | `old-launcher.test.js` "guard: a live old tray alone still counts as installed on a Mac (C6)" | Tray term removed: `+ installed: false / - installed: true`. |
| F1 | f91fd47. `terminal.status()` adds `occupant: {path, via, version} | null` for a file at `~/.local/bin/anyscribe` that is not ours (it reuses `uses` when that is the same file). When ours is written but another copy comes first, the reason is "Terminal finds another anyscribe at <path> first." (an alias or function gets its own sentence). README updated; this packet's bridge-v2.md already carries the lead's amendment. | `terminal.test.js` (a) "ours is written but another anyscribe comes first on PATH: other-copy" (reason, `occupant: null`); (b) "F1: a uv copy at ~/.local/bin while Terminal does not look there: off, and the occupant is named"; and the uv other-copy test (occupant set). | Occupant removed: (b) `+ null - {`. Reason removed: `F1: says which copy wins` (actual null). |
| F2 | With C1 (same defect). | | |
| F3 | ccb08bd. Journal "Not done here" and architecture.md "Open items (phase 3)": the skill is not refreshed when the app updates; the command embeds the Python path. | Read the diff. | Docs only; no guard. |
| F4 | ccb08bd. Journal and architecture.md: 2c-app and 2c-ui merge together, never alone. | Read the diff. | Record only; no code. |
| F5 | 2a5e322 (part of C1). `settings.json` keeps `port`; `parseSettings` accepts only an integer from 1024 to 65535. The Engine gets `savedPort`, and `main.js` saves the port when the engine first runs on it. `choosePort({saved, avoid})` keeps the saved port unless the old launcher now records it. A taken saved port still shows "Couldn't start" and never moves. e2e step 1b now reads `port: 8470` back from `settings.json`. | `logic.test.js` port and settings tests; `engine.test.js` pickPort ("F5: the saved port is kept"; taken: couldn't start, never a move). | Saved-port line removed: `AssertionError: kept after the old launcher is removed` (actual 8470, expected 8471). |
| F6 | 83c15d1. `addToPath` is async. After writing (or finding) the line it asks the login shell again. If `~/.local/bin` is still not on PATH: `ok: true` with "The line is in ~/.zprofile, but your shell setup removes it again later (check ~/.zshrc)." (`~/.bashrc` for bash). | `terminal.test.js` "guard: addToPath says when the line has no effect because a later rc file resets PATH (F6)" (a `.zshrc` that resets PATH) | Re-check removed: actual `undefined`, expected the reason. |

Docs for round 1: ccb08bd (README rows for C1, C2, C3, C4, C5, C6 and F6; the port bullet; journal "Round 1 review fixes" and "Not done here"; architecture.md).

**Plan notes.**
- I followed the plan as written. One gap: a refresh whose record write fails *after* the rename leaves the new command unrecorded, so it reads as foreign. The old content is gone by then, so it cannot be restored. It needs the runtime folder to become unwritable between two writes; not handled.
- Login-item ports are read from the XML plist the engine writes. A binary plist reads as no port (marked `shortcut:` in the code).

## Round 3 fixes

Built to spec.md "Round 3 design" and bridge-v2.md "Amendment 2". Branch started at b825cf8; the last code commit is b2e7459; docs b151404. Every mutant was applied to committed code and run in a fresh process, then restored with `git checkout` and run again. Each restored run passed.

**How it was run.** The engine export and wrapper are the same as in round 1. Wrapper: `<lead scratch folder>/engine-python` (PYTHONPATH set to the read-only `git archive b22df16 src` export, then exec of `~/labs/projects/anyscribe/.venv/bin/python`). From `~/labs/projects/anyscribe-wt/mac-2c-app/desktop`:
```sh
npm test
env -i HOME=$HOME PATH=/usr/bin:/bin ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python node test/e2e.js
env -i HOME=$HOME PATH=/usr/bin:/bin ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python node --test test/removal.e2e.js   # new: npm run e2e:removal
```

**Results at b151404:**
- `npm test`: 104 tests, 104 pass (94 before).
- e2e: 15 of 15 steps pass. Step 1b now also checks `oldLauncher.status().lastRemoval === null` and that `remove()` refuses off a Mac.
- `test/removal.e2e.js` (real engine, real `desktop uninstall`): 2 of 2 pass.
- No process was left afterwards. The owner's `~/.local/bin/anyscribe` and `~/.claude/skills/anyscribe` were not modified. None of `~/.zprofile`, `~/.bash_profile`, `~/.anyscribe/runtime`, `~/.anyscribe/server.pid`, `~/Applications` or `~/.config/anyscribe` exists.

| Id | Change | Ran | Saw (mutants: failing assertion, then restored) |
|---|---|---|---|
| A1 (blocker) | 58e18c8, 02bb427, b2e7459. **Removal pauses the engine.** `Engine.restart({between})` stores the step on the old run (`relaunchBefore`). When the old child exits, the step goes to the next `_launch` as `before`. `_start(run)` awaits it before anything else, while the new run is current with no child and the state is "restarting". So a stop or quit during the step cancels that run, and the existing gate after the port check spawns nothing. `old-launcher.removePausingEngine(engine, ctx, onResult)` calls `restart` with the uninstall step and waits for that step even when a stop ends the restart early. A refused restart returns its reason with `pieces: null` and runs nothing. If the relaunch fails, the result's reason says so. `main.js` keeps `lastRemoval` (set before the engine comes back), `oldLauncher.status()` returns it, and a failed relaunch's start window adds "The old launcher's removal ran first: …" (`logic.failureMessage(failure, removal)`). The same-port refusal and its test are removed. Port avoidance stays, as tidiness. | **Real engine and real uninstaller** (`test/removal.e2e.js` A1): a manifest on 8457 and the app engine on 8470, with `server.pid` holding the app engine's pid (alive, `-m anyscribe ui`); then `removePausingEngine` with the real `python -m anyscribe desktop uninstall --json`. **Seam engine** (`engine.test.js`): the step runs after the old child exited and before any spawn, never "stopped"; an explicit stop during the step and a quit during the step; a second restart during the step. **Fake engine process**: jobs running, waiting or unknown. **logic**: the start window wording. | Real: while the uninstall ran, the old engine pid was already gone. Afterwards there is a new engine whose `/api/health` pid matches, `crashes.exits` is `[]`, `lastExit` is null, and the manifest and `server.pid` are gone (the real uninstall ran). **Mutant, the uninstaller run with the engine up** (in `restart()`, `if (between) await between();` before the cancel), run again at HEAD: `✖ A1 … AssertionError: the engine never stopped unexpectedly` (actual `[ <time> ]`: the real uninstall killed the app engine through `server.pid`). Jobs refusal removed: `✖ … refused while transcriptions are running` (actual `ok: true, pieces: {…}`). A `_set('stopped')` put into the gap: `states: restarting, stopped, restarting, running`. The gate after the port check removed: `✖ an explicit stop / a quit during the uninstall step … AssertionError: no engine spawned after it` (actual 2, expected 1). `await step` removed: the stop test fails with actual `'The engine was stopped.'` and no removal result. `restartPending` removed: actual `'The engine is already starting.'`, expected `'A restart is already under way.'`. The restart is still refused, by the state check, so this second guard overlaps; it is the 2b guard and was kept. Wording removed: the start window message lacks "The old launcher's removal ran first: it was removed." The 2b test "an explicit stop during a restart cancels its relaunch (S3-A1)" still passes. |
| A2 (blocker) | Same design. Nothing reads the plist for safety now; the XML shortcut comment stays (port choice only). | **Real engine and real uninstaller** (`test/removal.e2e.js` A2): a binary LaunchAgent plist (`bplist00`, written by `plistlib`) on 8470, no manifest, and a live process with a tray's command line named in `tray.pid`. The engine's own `installed_port()` gives 8470, while the app's reading gives 8457, so the app engine runs on 8470: the reviewer's collision. | Afterwards: `crashes.exits` is `[]`, a new engine with a matching pid, the real uninstall printed `"stopped": true`, and the old tray is gone. **The same mutant**: `✖ A2 … AssertionError: the engine never stopped unexpectedly` (the uninstall's `/api/shutdown` to 8470 reached the app engine). On Linux the engine's uninstall removes the XDG login item, not this plist, so `pieces.loginItem` stays "still there". Removing a real LaunchAgent is Mac-only. |
| A3 | 56efb79. `writeTemp(target)` opens `.<name>.<random>.tmp` beside the target with `'wx'` and removes it only if this call created it and the write failed. It is used for the command and for `terminal.json`, and the fixed `anyscribe.anyscribe-tmp` and `terminal.json.tmp` names are gone. `terminal.naming.tempTag` is a test seam for planting at the name. | `terminal.test.js` "guard: temp files are created exclusively; a planted symlink and the profile it points at are left as they were (A3)". It plants a symlink to `~/.zprofile` at the record's temp name, then also at the command's. | Both turnOns fail with EEXIST. The profile's bytes are unchanged, both planted links still point at it, and no command or temp of ours is left. **Mutant `'wx'` → `'w'`**: actual `true`, expected `false` (the write went through the link). |
| A4 | 56efb79. The record commits the write. Order: the command's temp; then the record `{sha256: new, previousSha256: <hash of the current file when ours>, replaced, …}`; then a foreign file is moved aside; then the command is renamed (or hard-linked into an empty spot). `isOurs` accepts either hash. | `terminal.test.js` "guard: a record that cannot be saved leaves the command untouched and ours (A4)": the runtime folder is read-only from the start of the refresh, which uses another Python and version; then turnOff. "guard: in the crash window the record names the new hash and still accepts the old one": a hand-written record with a new hash plus `previousSha256` over the old command. | A4: the refresh fails with EACCES, the command's bytes are identical, it is still ours, and turnOff puts the uv link back. **Mutant, command before record**: `AssertionError: the command's bytes are identical` (0.20.1 against 0.20.0). Crash window: still ours, and turnOff restores. **Mutant, `previousSha256` dropped from `isOurs`**: `the old command is still ours` (actual `false`). The round 1 C4 test (the command folder read-only) still passes. |

**Where the design was adjusted, with evidence.**
- **The step had to be awaited.** `restart()` resolves when the run settles, and a stop during the step settles it before the step ends. Without `await step`, `removePausingEngine` returned with no result. The seam test showed this, and the mutant above confirms it.
- **The design's "one-gate check also covers this new window" holds through the existing gate.** A second gate right after the step was an equivalent mutant: with it removed, the stop and quit tests still passed, because the gate after the port check stops the cancelled run. So it was not kept (b2e7459). The gate after the port check is the one mutated above.
- **The real-engine tests are not in `npm test`.** They need the engine and port 8470. They run as `npm run e2e:removal` (`node --test test/removal.e2e.js`) and skip without `ANYSCRIBE_DEV_PYTHON`.
- **A mutation-runner mistake, caught and fixed.** The runner restores with `git checkout`, so a run started on an uncommitted edit reverted that edit. I re-applied it, committed it, and re-ran every mutant on committed code. One mutant run hung without a test timeout; I stopped it by its pid and re-ran it with `--test-timeout`.

**Not checked (Mac-only).** The real uninstall removing a LaunchAgent and `.app` on macOS, `launchctl unload`, and the dashboard reload and result card after a real removal. `lastRemoval` with a real removal can only be seen on a Mac, because `remove()` refuses elsewhere; on Linux it is checked as null.

## Round 4 fixes

Built to spec.md "Round 4 design". Branch started at 4977acb; the last code commit is 64e03b9; docs 7bb9c23. Every mutant was applied to committed code and run in a fresh process (`--test-timeout` on unit runs), then restored with `git checkout` and run again. Each restored run passed.

**How it was run** (same wrapper `<lead scratch folder>/engine-python` as rounds 1 and 3), from `~/labs/projects/anyscribe-wt/mac-2c-app/desktop`:
```sh
npm test
env -i HOME=$HOME PATH=/usr/bin:/bin ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python node test/e2e.js
env -i HOME=$HOME PATH=/usr/bin:/bin ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python node --test test/removal.e2e.js
```

**Results at 7bb9c23:**
- `npm test`: 107 tests, 107 pass (104 before).
- e2e: 15 of 15 steps pass.
- `removal.e2e.js`: 3 of 3 pass (A1, A2 and the new B2).
- No process was left afterwards. The owner's `~/.local/bin/anyscribe` and `~/.claude/skills/anyscribe` were not modified. None of `~/.zprofile`, `~/.bash_profile`, `~/.anyscribe/runtime`, `~/.anyscribe/server.pid`, `~/Applications` or `~/.config/anyscribe` exists.

| Id | Change | Ran | Saw (mutants: failing assertion, then restored) |
|---|---|---|---|
| B1 | b4c1d91. `Engine.stepRunning` is set before `await run.before()` and cleared in `finally`, so it lasts as long as the step, not the run. While it is set, `start()` returns false and `restart()` refuses with "The old launcher is still being removed." That check comes after the `restartPending` one, so a second restart during a normal removal still says "A restart is already under way." `stop()` is unchanged, and `await step` stays in removePausingEngine. | `engine.test.js` "guard: no start or restart while the removal step runs, even after a stop (B1)": step held, `restart({between})`, `stop()`, `start()` resolves false, `restart()` gives the reason, only the first pid spawned; release; nothing spawned; `start()` then works. Also "a step that throws still releases the hold: start() works afterwards (B1)". | Check dropped from `start()`: `AssertionError: start refused while the step runs` (actual `true`). Check dropped from `restart()`: `+ ok: true, + reason: null` against the reason. Hold released after the await instead of in `finally`: `AssertionError: start works` (actual `false`) after a throwing step. |
| B2 | f203086, 440f9df, f249dce, 64e03b9. `run.js` keeps the process group of each helper that passes `helper: true` (only `desktop uninstall` in `old-launcher.remove` does) and drops it when the helper finishes. `killHelpers()` SIGKILLs every such group synchronously and does not wait. `main.js` `will-quit` now calls `engine.stopForQuit()` then `killHelpers()`. Known limit (force quit, crash or power loss, then reopening within about 25 s) documented in the journal and architecture.md. | Unit (`test/run.test.js`): an opted-in `sh` helper with a `sleep` grandchild and a helper that did not opt in; `killHelpers()`. Integration (`removal.e2e.js` B2): the binary-plist fixture (old launcher on 8470, live tray, app engine on 8470). The **real** uninstaller is held by a wrapper that waits for a go-file (at most 20 s). Once the removal step runs: `stopForQuit()` plus `killHelpers()` (what will-quit does), then at once a second `Engine` on the same home starts on 8470. Then go, and wait 6 s. | Unit: the opted-in helper ends with SIGKILL and its grandchild is gone; the other helper and its grandchild are alive (then killed by the test, by their group). Integration: the new engine's health pid matches, `crashes.exits` is `[]`, state is running. **Mutant, empty `killHelpers()`**: unit `AssertionError: the helper was killed` (actual `null`); integration `AssertionError: the new engine never stopped unexpectedly` (actual `[ <time> ]`: the orphaned real uninstall stopped the new engine). **Mutant, will-quit without `killHelpers()`** (the call left out of the test): the same integration failure. My first version slept 3 s inside the helper and awaited the removal before reopening. The second mutant survived it, because the new engine was not yet up when the uninstaller ran; the go-file gate makes the failure happen every time (64e03b9). |
| B3 | 440f9df. `removal.e2e.js` A2: on macOS it expects `pieces.loginItem === 'removed'` and `result.ok === true`; elsewhere `'still there'`. The fixture is shared with B2 (`binaryPlistFixture`). | A2 on Linux. | Mac branch forced on Linux (`if (true)`): `actual: 'still there', expected: 'removed'`. The macOS branch itself was not run here. |

**Not checked.**
- `will-quit` calling `killHelpers()` in the real Electron app. On Linux `remove()` refuses, so the e2e cannot reach a running uninstall. The integration test makes the same two calls `will-quit` makes.
- The macOS expectation in A2.
- The force-quit window, which is accepted, not built.

## Round 5 fixes

Built to spec.md "Round 5 design". Branch started at 1de3404; the last code commit is abac1bb; docs bce749b. Every mutant was applied to committed code and run in a fresh process, then restored with `git checkout` and run again. Each restored run passed.

**How it was run** (same wrapper `<lead scratch folder>/engine-python`), from `~/labs/projects/anyscribe-wt/mac-2c-app/desktop`:
```sh
npm test
env -i HOME=$HOME PATH=/usr/bin:/bin ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python node test/e2e.js
env -i HOME=$HOME PATH=/usr/bin:/bin ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python node --test test/removal.e2e.js
```

**Results at bce749b:**
- `npm test`: 113 tests, 113 pass (107 before).
- e2e: 15 of 15 steps pass.
- `removal.e2e.js`: 3 of 3 pass.
- No process was left afterwards. The owner's `~/.local/bin/anyscribe` and `~/.claude/skills/anyscribe` were not modified. None of `~/.zprofile`, `~/.bash_profile`, `~/.anyscribe/runtime`, `~/.anyscribe/server.pid`, `~/Applications` or `~/.config/anyscribe` exists.

| Id | Change | Ran | Saw (mutants: failing assertion, then restored) |
|---|---|---|---|
| D1 | 5abef99. `old-launcher.js`. **Exact plist read:** `programArguments(file)` asks `readers.plutil(file)`, a seam whose real form on macOS is `/usr/bin/plutil -extract ProgramArguments json -o - <plist>` (5 s limit) and null elsewhere; then the XML read; then unknown. `loginItemPort` and `uninstallTarget` use it. **The live tray's own port:** `liveTrayCommand(home)` (the old `trayRunning` check, now returning the command line) and `trayPort(home)` take `--port N`, `--port=N` or `-p N` after `tray`, else 8457. An unparseable value gives `{port: 8457, readable: false}`. `recordedPorts(home, {note})` is now async and returns the manifest's port, the login item's, 8457 and the tray's own. It notes an unreadable tray port, and `engine.pickPort` writes that note to the app log; the start goes ahead. | `old-launcher.test.js`: "guard: a binary plist is read exactly through plutil: 8470, so the app picks 8471" (fake plutil JSON over a `bplist00` file; also `uninstallTarget` 8470, and plutil asked about the login item). "plutil failing: the XML read, then unknown". "guard: no files, a live old tray started with `--port 8470` / `-p 8470` / `--port=8470`: the app picks 8471" (three tests, a real process with that command line). "a live tray whose port can't be read: 8457 avoided, a note, and the start goes ahead". | **plutil call dropped:** actual `null`, expected 8470. **XML fallback dropped:** `AssertionError: the XML read` (actual `null`). **Tray's own port dropped from the avoid list:** actual 8470, expected 8471 in all three tray tests, and against the real engine `removal.e2e.js` A2 fails with `AssertionError: the app's engine avoids the old launcher's port` (actual 8470). **Note dropped:** the note check fails (actual `undefined`). |
| D1 (removal.e2e.js) | abac1bb. A2's fixture tray now runs `tray --port 8470`, as desktop mode starts it. The test no longer asserts the XML shortcut's miss; it asserts the app's engine avoids 8470 (port 8471), then the same removal checks: the engine survives, the real uninstall stopped the tray, and `loginItem` per platform. B2 keeps the collision on purpose, since it tests quitting, not ports: its tray names no port, and `readers.plutil` is set to null for that test (restored in `t.after`), so the engine still lands on 8470. | `removal.e2e.js` with the real engine b22df16. | All three pass. The tray-port mutant above fails A2. |
| Docs | bce749b. The journal "Round 5", architecture.md and desktop/README.md describe the avoided ports and the exact read. They record the known limit: an old tray started after the app, on the app's own port, can still reach the app's engine during its own teardown. | Read the diff. | |

**Not checked (Mac-only).** The real `/usr/bin/plutil -extract ProgramArguments json -o -` call runs only on macOS; on Linux the seam returns null and the XML read is used. Every test here goes through a stand-in for plutil, so the real call is to be checked in the Mac walk, as are `ps -ww` reading the tray's command line on macOS and a real old tray's teardown.

## Round 5 leftover fix (E1, not re-reviewed)

Commit 53afdbe, on top of 87a6d3d. Diff stat: `desktop/src/old-launcher.js | 19 +++++++++++--------`, `desktop/test/old-launcher.test.js | 33 +++++++++++++++++++++++++++++++--` (2 files, 42 insertions, 10 deletions).

- **Change.** `trayPort()` now returns `{ports, readable}`. It collects every port the old tray's command line names after `tray`, in every form Click accepts: `--port N`, `--port=N`, `-p N`, `-pN`, repeated. It adds 8457 when none is named, or when a named one does not parse (`readable: false`, noted as before). `recordedPorts()` adds them all to the avoid list, which applies to both the first choice and a saved port. This is conservative on purpose rather than a copy of Click's last-one-wins rule.
- **Ran.** `old-launcher.test.js`: "guard: a repeated --port avoids every port named, and a saved one among them is not reused (E1)" (`--port 8457 --port 8470`: picks 8471, and a saved 8470 also gives 8471); "guard: the attached short form -p8470 avoids 8470, saved or not (E1)"; `-p8470` added to the round 5 tray-form tests. Then `npm test`, and `env -i HOME=$HOME PATH=/usr/bin:/bin ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python node --test test/removal.e2e.js` from `desktop/`.
- **Saw.**
  - `npm test`: 116 tests, 116 pass.
  - `removal.e2e.js`: 3 of 3 pass (A1, A2, B2) against the real engine b22df16.
  - No process was left afterwards.
  - **Mutant, back to the first-match parse** (the round 5 regex): `✖ … repeated --port … AssertionError: avoid: 8457,8457` (8470 missed), and `✖ … -p8470 … actual: 8470, expected: 8471`. Restored: both pass.

## Integration with 2c-ui (the lead, 2026-11-21)

- **Change.** `desktop/test/e2e.js` step 3b assumed a dashboard that never subscribes to opened files. 2c-ui's dashboard subscribes as it loads and takes the file at once, so the step's own subscriber timed out ("timed out waiting for the held file on subscribe"). That is a test assumption, not an app fault. The step now shows the engine's `/api/health` page in the window (same origin; the preload still gives the bridge, and no dashboard code subscribes), runs its checks unchanged, then loads the dashboard again.
- **Ran**, on the combined engine, shell, 2c-app and 2c-ui tree: `node test/e2e.js` 15 of 15 steps; `node --test test/removal.e2e.js` 3 of 3; `npm test` 116 of 116.
- **Mutant.** Removing the preload's `if (!openFileCallbacks.size) return;` (a file with no subscriber is acknowledged and lost) makes the step fail with that same timeout. With `src/preload.js` restored byte for byte, the step passes.
