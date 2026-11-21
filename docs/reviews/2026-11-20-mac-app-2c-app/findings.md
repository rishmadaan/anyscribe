# Findings (verbatim reports)

Note: home-folder paths rewritten to `~`; originals in ~/.review-runs/2026-11-20-mac-app-2c-app/. The fit report is a close summary by the lead of the Agent-tool reviewer's hand-back, marked as such.


# Round 1


## report-sol-r1.md

~~~~
**NOT YET.** The work fits the approved app scope, but launcher removal can stop the app’s own engine. There are also failures in file delivery, skill status and recovery reporting.

Reviewed `df94f5b..867e61a` in `~/labs/projects/anyscribe-wt/mac-2c-app`, against engine `b22df16`. Later commits contain review records only; the reviewed code is unchanged.

**Findings**

**C1. blocker | CONFIRMED by trace | `desktop/src/old-launcher.js:83`; engine `core/desktop.py:304`, `core/tray.py:267`**

Removing a partial old installation can shut down the app’s engine.

Concrete case: `desktop.json` is missing, the old plist records port 8470, and a valid old tray remains alive while its server is down. The app chooses 8470 because it checks only the manifest. Removal invokes `desktop uninstall`, which obtains 8470 from the plist and calls `stop_tray(8470)`. That sends `/api/shutdown` to any answering anyscribe server, including the app’s engine. The supervisor subsequently treats its exit as a crash; a transcription can be interrupted.

The builder identified the risk, but the explanation needs correction: the engine’s fallback port is **8457**, and a pidfile must identify a live, matching tray. A stale or unrelated pid alone does not trigger this path.

Fix: protect the app’s engine identity throughout the removal operation. As an immediate guard, refuse removal when the resolved old port overlaps the app’s port. An engine-side fix must protect both HTTP shutdown and PID-based termination. Add an integration regression that verifies the app engine’s identity and running job survive removal.

**C2. should-fix | CONFIRMED by trace | `desktop/src/preload.js:42`; `desktop/src/main.js:436`; `desktop/src/logic.js:354`**

A held file can disappear during subscription cleanup.

With a file queued, the renderer can execute:

```js
const off = window.anyscribeDesktop.onOpenFile(callback);
off();
```

The listener is removed immediately, but the subscribe and unsubscribe requests travel asynchronously. Main processes subscribe first, sends the held file and removes it from the queue. The renderer now has no listener, so the event is discarded. A later subscriber receives nothing.

The existing test substitutes a synchronous delivery callback. Production delivery returns success immediately after `webContents.send`, which does not establish that a callback received the file.

Fix: retain each event until the current renderer subscription acknowledges receipt, using event and subscription identities to prevent loss or duplicate handling. Test immediate cleanup, resubscription and reload during delivery.

**C3. should-fix | CONFIRMED by trace | `desktop/src/terminal.js:187`, `:205`, `:277`**

A failed skill update can be reported as successfully installed.

If an older `SKILL.md` exists and `install-skill --force` fails before replacing it, `installSkill` records the error. However, `skillState` reports “installed” solely because that file exists, and `status` includes the error only when the skill is “missing”. `turnOn` consequently returns `ok: true`, `skill: "installed"` and no installation-failure reason.

The failure test starts without an existing skill, so it misses this case.

Fix: make a failed installation visible regardless of whether an older file remains. Verify the current installation before clearing the failure, and add a regression with an existing skill plus a failed update.

**C4. should-fix | CONFIRMED by trace | `desktop/src/terminal.js:260`, `:267`, `:273`**

A failed command refresh can invalidate ownership of the unchanged command.

Suppose the app already owns the command, then refreshes it with a different Python path or version. The new hash is recorded before the replacement file is written. If creating or renaming the temporary file fails, the old command remains but its recorded hash has changed. The catch path does not restore the old record.

Turning off subsequently treats the untouched command as foreign. It either leaves the app command installed or asks whether it was changed, instead of performing the normal restore.

Fix: preserve the previous ownership record until replacement succeeds, with rollback and recoverable handling of interrupted transitions. Test a changed script followed by a write or rename failure, then verify normal turn-off still restores the original command.

**C5. should-fix | CONFIRMED by trace | `desktop/src/old-launcher.js:92`; `desktop/src/main.js:102`**

Start-at-login carry-over is reported before it is verified.

Removal calls `setStartAtLogin(true)` and unconditionally returns `startAtLoginCarriedOver: true`. Electron’s installed API explicitly permits `requires-approval`, `not-registered` and `not-found` results. The existing `startsAtLogin()` correctly distinguishes these states, but removal never reads it back.

The result can therefore support “This app now starts at login” while macOS still requires approval.

Fix: read the system state after registration. Report successful carry-over only when enabled, and return a clear pending or failure reason otherwise. Test the approval-required case.

**C6. should-fix | CONFIRMED by trace | `desktop/src/old-launcher.js:73`**

A remaining old tray can be excluded from “installed”.

On macOS, `installed` considers only the launcher and plist. If both are absent but the old tray remains running, status returns `installed: false` alongside `menuBarIcon: "running"`. A screen using `installed` to offer cleanup can hide the removal action precisely when one piece remains.

Fix: include the live old tray in the macOS cleanup predicate. Test the tray-only partial installation.

**Answers to the builder’s spec corrections**

1. **`install-skill`: correct.** Registration at engine `cli/main.py:224` confirms the command name. The additional `--force` behavior needs preservation testing against an existing customized skill; the supplied tests do not establish that.
2. **Answering `needsChoice`: sound correction.** The added choices provide the missing mechanism. Update `bridge-v2.md` itself, which still documents the old signature, and verify the combined UI calls the amended form.
3. **Bash profile shadowing: sound correction.** Refusing to create a file that would hide existing startup configuration is appropriate.
4. **Carry-over timing: sound refinement**, subject to C5’s verification requirement.
5. **Engine shutdown risk: real and release-blocking.** Being outside this slice’s file scope does not satisfy the invariant. Correct the port and pidfile details as described in C1.
6. **Reasons accompanying `ok: true`: reasonable.** A completed command installation can coexist with a skill failure or unknown shell state.

The “unknown shell means on” interpretation needs careful contract wording. A read-only reproduction returned `"on"` for `{ours: true, shellKnown: false}`. That proves the command is installed, not that Terminal can run it. The combined UI must show the uncertainty and must not claim “ready in Terminal”.

**Pending owner checks**

Only the visual and wording judgment needs Rishabh: whether the combined sidebar, traffic lights, drag area and resulting messages feel right on his Mac. Native launcher removal, login approval, shell behavior and Finder/Dock delivery are technical checks for the lead or builder first.

**Checks, limits and inspected material**

I read the packet, settled declined findings, binding mockup sections, changed source/tests/docs, relevant shell review records, and all five named engine files at `b22df16`. I also checked Electron’s installed type definitions for navigation events and login-item states.

Read-only module probes confirmed the port choices, unknown-shell state and basic queue behavior. `git diff --check` passed. The worktree remained unchanged.

I did **not** independently reproduce the claimed 85 passing tests, 15 e2e steps or mutation runs. The brief expressly prohibited test runners, builds, Electron launches and writes. The existing e2e covers successful subscription, not C2’s cleanup race; launcher tests substitute the uninstaller and cannot establish engine isolation.

After adding the regressions, run from the worktree’s `desktop/` directory:

```sh
npm test
```

For e2e, first set `ANYSCRIBE_DEV_PYTHON` to the builder’s existing wrapper for engine `b22df16`, then run:

```sh
env -i HOME="$HOME" PATH=/usr/bin:/bin \
  ANYSCRIBE_DEV_PYTHON="$ANYSCRIBE_DEV_PYTHON" node test/e2e.js
```

The wrapper’s absolute path is missing from `proof.md`, so that run is not fully reproducible from the packet alone. Real macOS removal, approval states, login-shell behavior and Finder/Dock events remain unverified.
~~~~


## report-opus-r1.md

~~~~
Fit review, round 1, 2c-app (df94f5b..867e61a), claude-opus-5-5. Close summary by the lead of the fit reviewer's hand-back (every finding, location, severity, fix and answer kept; wording condensed). Not verbatim.

VERDICT: CONDITIONAL on F1 (one machine-readable status field so the screens know when Switch will work), F2 and F3 (known gaps recorded where later work will see them, not only in proof.md), F4 (2c-app merges together with 2c-ui, never alone). Scope and proportion are right; the builder's extras (bash .profile guard, timestamped backups, turnOff({choice}), install-skill --force) each fix a real hole.

F1 should-fix CONFIRMED (terminal.js:180-185, 242-248; test/terminal.test.js:196): "other copy" cannot tell the screens whether "Switch to this app's copy" will do anything. (a) another copy first on PATH elsewhere (pyenv, conda, pip elsewhere): turnOn({replace:true}) writes ours, runs install-skill --force over that copy's skill, returns ok true with state other-copy and no reason; the click changes nothing visible. (b) a uv copy at ~/.local/bin/anyscribe with ~/.local/bin not on Terminal's PATH: status says off, Turn on returns ok false with only prose (OTHER_AT_PATH). Fix: status() adds occupant {path, via, version} | null for whatever sits at ~/.local/bin/anyscribe when not ours; 2c-ui offers Switch only when occupant is set; when ours is written but another copy comes first, status adds a reason naming that copy's path ("Terminal finds another anyscribe at X first"). One unit test per case.

F2 should-fix CONFIRMED (engine b22df16 core/desktop.py:304-312, core/tray.py:260-273; desktop logic.choosePort): a partial old install (no desktop.json, live tray and login item on 8470) makes the app also pick 8470; desktop uninstall posts /api/shutdown to 8470, reaching the app's engine; a running job dies and is recorded as a crash. Only proof.md records it. Fix: decide now and record it: an engine change (skip HTTP shutdown for the app's port) or a desktop-side refusal in oldLauncher.remove() when the uninstall's target port equals engine.port.

F3 should-fix CONFIRMED (engine cli/main.py:156-197; terminal.js header): the skill never updates when the app updates (ANYSCRIBE_APP=1 skips auto-update; only Turn on or Try again writes it), and moving the app breaks the command (it embeds the Python path). Fix: add both to the journal's "Not done here" list or the phase 3 plan.

F4 should-fix (merge condition) PLAUSIBLE (main.js titleBarStyle hiddenInset): until 2c-ui ships the drag strip and top padding, the Mac window cannot be dragged and the sidebar's top row sits under the traffic lights. Make merging 2c-app and 2c-ui together a hard rule.

F5 nit PLAUSIBLE: after the old launcher is removed, desktop.json is gone and choosePort moves the app from 8471 to 8470 on the next launch; the dashboard's local storage is per port (scribe_onboarding_dismissed, App.tsx:24, plus anything 2c-ui stores). Fix: save the first-used port in the app's userData settings, or document the move.

F6 nit CONFIRMED (terminal.js:353-356): if the PATH line is already in ~/.zprofile but .zshrc resets PATH, addToPath returns ok true, status stays path-missing, and the card comes back with no explanation. Fix: addToPath re-asks the shell and adds a reason, or 2c-ui re-reads status and says the line has no effect.

Builder's points: install-skill --force agree (after Off restores the uv copy, its own auto-update rewrites the skill on its next run); turnOff({choice}) needed, 2c-ui must use it, bridge-v2.md still shows the old form, the README is now the contract; bash .profile guard agree; carry-over timing agree; uninstall stopping the app's engine is real, disagree with leaving it only in proof.md (F2); reason with ok true agree. Interpretations: state "on" when the shell could not be asked is acceptable only if 2c-ui shows the reason and never renders "Terminal runs this app's anyscribe" when uses is null; an alias counting as another copy is fine; --version on the other copy is safe (eager callback exits before the skill auto-update); no skill install at app start is correct.

Pending owner checks: on his Mac (old launcher, uv copy, zsh, Claude Code): first launch, Remove, Switch, Off; the uv command comes back, the skill stays, Start at login is on. Whether a lagging skill (F3) is acceptable until phase 3. Whether the one-time port move (F5) is acceptable. Traffic lights against the real sidebar once 2c-ui lands. Dock drop needs phase 3 file associations.

Not run (forbidden): npm test, the e2e. Not checked (Mac only): login-shell PATH under path_helper, ps -ww, real LaunchAgent and tray removal, open-file from Finder, the hiddenInset look. Inspected: the brief, the packet (ask, spec, target, proof, lens, bridge-v2), declined.md, the full desktop/src diff (terminal.js, old-launcher.js, run.js, main.js, preload.js, logic.js, engine.js), README, architecture.md, _index.md, the journal entry, other-copy test names, mockup sections 3, 4, 5, 9, "Skipped on purpose", "For the build" (sha bcf26037), engine b22df16 desktop.uninstall, installed_port, tray.stop_tray, the CLI skill auto-update and install-skill registration, ui/src local storage use.
~~~~

# Round 2

## report-astra-r2.md

~~~~
**NOT YET.** The work fits the approved Mac app scope, and most round 1 fixes are sound. Launcher removal can still stop the app’s engine through two unchecked paths. Command replacement also retains an ownership failure and an unsafe temporary-file write.

Reviewed **98ea8ac**, against engine **b22df16**. Current HEAD adds only review records.

**Round 1 findings**

| ID | Status | Evidence |
|---|---|---|
| C1 | **PARTLY** | The original XML-plist collision is prevented, but PID-based termination and binary plists bypass the protection. See A1 and A2. |
| C2 | **FIXED** | Files remain held until acknowledged; the preload suppresses repeat delivery within a page. The original immediate-unsubscribe race is addressed. |
| C3 | **FIXED** | A recorded installation failure overrides an older `SKILL.md`; status retains the reason. |
| C4 | **PARTLY** | Failure before command replacement preserves ownership. Failure saving the record afterward still invalidates it. See A4. |
| C5 | **FIXED** | Carry-over reads the system state and reports approval-required separately. |
| C6 | **FIXED** | A live old tray alone now counts as installed on macOS. |
| F1 | **FIXED** | `occupant` identifies the replaceable command; status names another copy found first. Combined UI consumption remains a separate check. |
| F2 | **PARTLY** | The decision is documented, but the claimed complete engine protection is false. See A1 and A2. |
| F3 | **FIXED** | Both update and moved-app limitations are recorded in the journal and architecture document, as requested. The functionality remains deferred. |
| F4 | **FIXED** | Both documents explicitly require 2c-app and 2c-ui to merge together. This is a merge condition, not native UI proof. |
| F5 | **FIXED** | Successful startup saves the port; subsequent selection retains it unless excluded. A taken saved port still refuses startup. |
| F6 | **FIXED** | `addToPath` rechecks the login shell and explains when later configuration removes the directory. |

**New and residual findings**

**A1. blocker | CONFIRMED by trace | The port guard does not protect against PID-based termination.**

Where: old-launcher.js:129 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:129`), engine desktop.py:310 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/core/desktop.py:310`), tray.py:269 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/core/tray.py:269`).

Concrete case: the old manifest records 8457. After a crash or reboot, its stale `server.pid` number is reused by the app’s engine, running on 8470. Removal passes the new port guard. The manifest makes `desktop.uninstall()` call `stop_tray(8457)`, which separately reads `server.pid` and terminates that process.

The PID validation checks that the process is alive and runs `anyscribe ui`. The app’s engine satisfies both checks. It does not establish that the process belongs to the old launcher or serves 8457.

**Fix:** protect the app’s engine identity on both HTTP and PID termination paths. At minimum, refuse removal when the old server PID identifies the current app engine. Prefer enforcing the exclusion inside the uninstaller immediately before signalling. Add a regression that asserts the app engine’s identity and active job survive removal, including this stale-PID case.

**A2. blocker | CONFIRMED by trace | A valid binary plist bypasses both port protections.**

Where: old-launcher.js:38 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:38`), engine desktop.py:134 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/core/desktop.py:134`).

Concrete case: `desktop.json` is absent, the old LaunchAgent is a binary plist recording 8470, and a matching old tray remains alive while its server is down.

The app’s XML regular expression reads no port, so initial selection can choose 8470 and the removal guard resolves the old target to 8457. Python’s `plistlib.loads` reads the binary plist correctly, resolves 8470, and the uninstaller posts shutdown to the app’s engine.

The builder explicitly records this shortcut. It contradicts the binding requirement to resolve ports as the engine does. The architecture claim that the refusal covers every app-reachable case is therefore too strong.

**Fix:** use a resolver supporting the same plist formats as the engine, and distinguish an absent plist from an existing one that cannot be interpreted safely. Test the binary-plist partial installation and assert that uninstall is never invoked against the app’s port.

**A3. should-fix | CONFIRMED by trace | The temporary command path can overwrite an unrelated file.**

Where: terminal.js:276 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/terminal.js:276`).

Every `turnOn` now writes to the fixed path `~/.local/bin/anyscribe.anyscribe-tmp` using ordinary `writeFileSync`, then changes its permissions. There is no exclusive creation or ownership check.

If that path already contains a file, it is truncated. If it is a symlink to, for example, `~/.zprofile`, the write follows it and overwrites the profile. The later cleanup also assumes the temporary path belongs to this attempt. The command’s foreign-file guard does not protect this second path.

**Fix:** create a unique temporary file exclusively in the destination directory, retain its ownership for cleanup, and leave pre-existing entries untouched. Apply the same discipline to the fixed `terminal.json.tmp` path. Regression assertions should compare the exact surviving contents and symlink targets.

**A4. should-fix | CONFIRMED by trace | A record-write failure after refresh leaves the command unowned.**

Where: terminal.js:289 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/terminal.js:289`), terminal.js:297 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/terminal.js:297`).

Start with an owned command, then refresh with a different Python path or version while `~/.local/bin` is writable and `~/.anyscribe/runtime` is not.

The rename installs the new command. Saving its hash fails. The catch block rolls back only the newly linked installation path; it does not restore an overwritten owned command. The old record remains, so the new command reads as foreign. Turning off then asks about a supposed external change or leaves the app command behind.

The builder acknowledges this gap but understates its prerequisite: the runtime folder can be unwritable **before the operation starts**. No permission change between writes is necessary. The added test makes the command directory unwritable, so it fails before reaching this transition.

**Fix:** preserve a recoverable previous command and ownership record until the complete replacement commits, with rollback or restart recovery if saving the record fails. Test failure at that specific write, followed by normal turn-off restoring the original command.

**Answers to the builder’s spec corrections**

1. **`install-skill` is correct.** The engine registration confirms it. `--force` updates the bundled skill files, but does overwrite their existing contents; preservation of customized skills has not been demonstrated.
2. **`turnOff({choice})` is a necessary correction.** The contract amendments now describe both answers.
3. **The bash profile refusal is sound.** Creating `.bash_profile` would otherwise hide an existing `.bash_login` or `.profile`.
4. **Carry-over after confirmed removal is sound**, and C5 now verifies the resulting system state.
5. **The shutdown risk remains real.** The fallback is 8457. A manifest alone can enter `stop_tray`; without a manifest, a valid live tray can do so. Port separation alone does not protect the PID termination path.
6. **`reason` alongside `ok: true` is appropriate.** Successful command installation can coexist with a missing skill or unknown shell state.

The deferred skill refresh and moved-app repair are accurately documented. They must remain explicit phase 3 work, not be presented as already working.

**Pending owner checks**

Only Rishabh’s judgment of the combined Mac experience remains owner-specific: whether the traffic lights, drag area, Terminal messages and launcher-removal flow look and read correctly.

Native removal, Login Items approval, shell behavior, file delivery and recovery testing are technical work for the lead or builder, not repair tasks for Rishabh.

**Checks, limits and inspected material**

I read the review packet, round 1 reports and verdicts, binding fix plan, complete change set, approved mockup sections, settled declined findings, relevant shell review records, changed implementation and regression bodies, bridge contract and building documentation. I traced all five named engine files at `b22df16`, plus the skill installer.

Read-only module probes confirmed retained-file delivery before acknowledgement, repeated/unknown acknowledgement behavior, and saved-port selection. The source/building-documentation delta passes `git diff --check`.

I did **not** independently reproduce the claimed 94 passing tests, 15 e2e steps or mutation results. The brief prohibits test runners, Electron launches and writes. In particular:

- Launcher tests substitute the uninstaller, so they do not establish engine isolation.
- The reload-during-delivery test simulates queue unsubscribe/resubscribe; it is not a real renderer reload at the acknowledgement boundary.
- Saving 8470 in e2e does not distinguish persistence from choosing the default again. A full restart retaining 8471 needs coverage.
- Real macOS launcher removal, approval states, `path_helper`, `ps -ww`, Finder/Dock delivery and combined window layout remain unchecked.

After adding the regressions above, run:

```sh
cd ~/labs/projects/anyscribe-wt/mac-2c-app/desktop
npm test
```

The supplied engine wrapper exists and matches the recorded contents. The exact e2e command is:

```sh
cd ~/labs/projects/anyscribe-wt/mac-2c-app/desktop
env -i HOME="$HOME" PATH=/usr/bin:/bin \
  ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python \
  node test/e2e.js
```

No files were written, no application or server was launched, and no processes were signalled.
~~~~

# Round 3

## report-sol-r3.md

~~~~
**NOT YET.** The original shutdown and command-ownership defects are addressed, but cancellation releases the restart guard before removal finishes. The work otherwise fits the approved app scope.

Reviewed `59c4e3d`, against engine `b22df16`. Later commits change review records only.

| Finding | Status | Evidence |
|---|---|---|
| A1 | FIXED | The stale-PID case now runs uninstall after the old engine exits and before its replacement starts. |
| A2 | FIXED | Binary-plist parsing no longer controls removal safety. The same pause surrounds uninstall. |
| A3 | FIXED | Both temporary files use random names and exclusive creation; existing entries are neither followed nor cleaned up. |
| A4 | FIXED | A failed record write precedes command replacement, leaving its bytes and ownership unchanged. |
| C1 | FIXED | The original port-collision path is addressed within an uninterrupted removal. Lifecycle gaps below remain. |
| C4 | FIXED | Recording both new and previous hashes preserves ownership across the refresh transition. |
| F2 | FIXED | The current architecture documents engine pausing and removes the earlier claim that port checks provide complete protection. |

**New findings**

**B1. should-fix | CONFIRMED by trace | Cancellation releases exclusion while uninstall remains active.**

Where: engine.js:382 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/engine.js:382`), engine.js:440 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/engine.js:440`), old-launcher.js:181 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:181`).

Concrete sequence:

1. Removal reaches its pending uninstall step.
2. `stop()` cancels the childless replacement run, clears `this.run` and settles its promise immediately.
3. `restart()` returns and clears `restartPending`.
4. The uninstall is still running: only `removePausingEngine()` separately awaits it.
5. Another `restart()` is accepted. `start()` can also proceed because it checks neither removal activity nor `restartPending`.

A new engine can therefore start while the old uninstaller still has authority to shut it down. The existing stop tests release the uninstall and check for an automatic relaunch; they never request another start before releasing it.

There is currently no production caller of plain `stop()`, so this is an internal supervisor-contract defect, not a demonstrated normal click path. `stopForQuit()` still prevents the same Engine instance from spawning again.

**Fix:** retain the operation’s exclusion until the uninstall actually finishes, and have every start path respect it. Add a regression that holds uninstall pending, stops, requests both restart and start, and verifies neither launches during that interval.

**B2. should-fix | PLAUSIBLE | Quitting can leave an uninstaller that reaches the next app instance.**

Where: run.js:31 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/run.js:31`), main.js:334 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/main.js:334`), engine.js:371 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/engine.js:371`).

The uninstaller is a detached process. Quitting cancels the waiting engine run, but does not cancel or await that helper. Its timeout also belongs to the exiting app process.

If someone quits during a slow uninstall and reopens anyscribe, the new instance has no removal reservation. With the binary-plist collision, a delayed old uninstaller could subsequently send shutdown to the new engine on 8470.

The detached-helper lifecycle is confirmed by trace; the shutdown across two real app instances was not reproduced.

**Fix:** ensure removal cannot outlive its protection against engine startup. For ordinary quit, terminate and reap the helper or finish removal before releasing that protection. Settle this with a held-uninstaller, quit, reopen integration test asserting the new engine’s PID survives and its crash count stays zero.

**B3. nit | CONFIRMED by trace | The new removal test expects Linux behavior unconditionally.**

Where: removal.e2e.js:128 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/test/removal.e2e.js:128`).

A2 always expects `pieces.loginItem === "still there"`. On macOS the real uninstaller removes that plist, so successful native cleanup fails this assertion.

**Fix:** make the expectation platform-specific. On macOS assert the plist was removed and check the complete removal result.

**Answers to the builder’s spec corrections**

- `install-skill` is the correct command. `--force` addresses stale bundled skills, but preservation of customized skill contents remains unproved.
- `turnOff({choice})` correctly supplies the missing answer mechanism.
- Refusing to create a bash profile that would hide existing startup configuration is sound.
- Carry-over only after the old login item disappears, followed by system read-back, is sound.
- The original shutdown explanation understated the paths involved. The engine’s fallback is **8457**; both port and server-PID termination matter. Pausing addresses the original cases.
- A reason accompanying `ok: true` is appropriate for partial outcomes or uncertainty.
- Awaiting the uninstall step was necessary, but awaiting it outside `restart()` does not preserve restart exclusion.
- The existing gate cancels the original replacement run correctly. That does not prove protection against a subsequent start.
- Keeping real-engine tests separate from `npm test` is reasonable.

**Pending owner checks**

Only Rishabh’s judgment of the combined Mac experience: traffic lights, dragging, wording, and whether the removal/reload flow feels understandable.

Native removal, helper cleanup, Login Items approval behavior, shell behavior and file delivery are technical checks for the lead or builder, not tasks to hand to Rishabh.

**Checks, limits and inspected material**

I inspected the complete packet, diagnosis, earlier findings and verdicts, bridge amendments, approved mockup, round 3 code/test changes, relevant shell review records, current bridge wiring, and all five named engine files at `b22df16`. The source and building-documentation delta passes `git diff --check`; the worktree remains clean.

The brief prohibited test runners, Electron, servers, writes and process control. Consequently I did not independently reproduce the reported 104 passing tests, 15 e2e steps, two removal tests or mutation failures. The new real-engine tests materially improve coverage, but neither exercises another start after cancellation or quitting and reopening during removal.

After adding the lifecycle regressions, run:

```sh
cd ~/labs/projects/anyscribe-wt/mac-2c-app/desktop
npm test
env -i HOME="$HOME" PATH=/usr/bin:/bin \
  ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python \
  node test/e2e.js
env -i HOME="$HOME" PATH=/usr/bin:/bin \
  ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python \
  node --test test/removal.e2e.js
```

After correcting B3, run from the Mac checkout’s `desktop` directory:

```sh
ANYSCRIBE_DEV_PYTHON="$(pwd)/../.venv/bin/python" \
  node --test test/removal.e2e.js
```

Real macOS cleanup, dashboard reload/result recovery, Finder/Dock delivery and the combined window layout remain unverified here.
~~~~

# Round 4

## report-sol-r4.md

~~~~
**NOT YET.** B1 and B3 are fixed. B2 terminates the uninstaller, but a previously running old tray can continue its own shutdown work after a normal quit and reach the reopened app’s engine.

Reviewed `1f2e27f`, especially `59c4e3d..1f2e27f`, against engine `b22df16`. Later commits and the working tree contain no additional implementation changes. The work fits the approved app scope.

- **B1: FIXED.** `stepRunning` survives cancellation of the run, blocks both `start()` and `restart()`, and clears in `finally`. `removePausingEngine()` still awaits the removal step.
- **B2: PARTLY.** Opted-in helper groups are killed from `will-quit`. This addresses the orphaned uninstaller, but excludes the existing tray’s independent teardown. See D1.
- **B3: FIXED.** A2 now expects the login item to be removed and `result.ok === true` on macOS, while retaining the Linux expectation elsewhere. The native branch remains unexecuted here.

**D1. should-fix | CONFIRMED by trace | Normal quit can leave the old tray’s shutdown request active.**

Where:

- run.js:14 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/run.js:14`)
- main.js:337 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/main.js:337`)
- Engine `b22df16`: `core/tray.py:268`; `cli/tray_cmd.py:72`, `:115`, `:127`.
- removal.e2e.js:117 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/test/removal.e2e.js:117`)

Concrete sequence:

1. The binary-plist collision leaves a live old tray whose server has died, alongside the app engine on 8470.
2. Removal pauses the app engine. The real uninstaller sends SIGTERM to the old tray.
3. The old tray handles SIGTERM through its watcher thread. Its teardown calls `_shutdown_server()`, which calls `_post_shutdown(port)` even when its remembered server process has already exited.
4. The person quits before that teardown finishes. `killHelpers()` kills the uninstaller’s group. The pre-existing tray belongs to another group and survives this cancellation.
5. The app reopens on 8470 before the tray’s request runs. `_post_shutdown()` checks only that the answering server identifies as anyscribe, then shuts down the new engine.

The shutdown path is confirmed by source trace; I did not reproduce the timing. This concerns **normal quit**, outside the accepted force-quit exception.

The integration fixture misses it: its “tray” is a Node interval process with matching command-line text. It exits on SIGTERM without running the real tray’s teardown. Holding the uninstaller before execution proves cancellation of that helper, not cancellation of work it has already triggered.

**Fix:** include the verified old tray’s remaining teardown in removal cancellation, or prevent that teardown from targeting the app engine. Add a deterministic regression that holds the real tray teardown after SIGTERM, performs normal quit and reopen, then releases it. Assert that the new engine’s PID survives and its crash history stays empty. Mutation-test the protection.

**Answers to the builder’s spec corrections**

- `install-skill` is the correct command. `--force` replaces existing bundled skill files; preservation of customized contents remains unproved.
- `turnOff({choice})` supplies the necessary answer mechanism.
- Refusing to create a bash profile that hides existing startup configuration is sound.
- Carry-over after confirmed login-item removal, with system read-back, is sound.
- The original shutdown explanation understated both port and PID paths. Pausing addresses uninterrupted removal; D1 concerns cancellation after signalling another process.
- A reason alongside `ok: true` correctly represents partial outcomes and uncertainty.
- Awaiting the step and keeping real-engine tests separate from `npm test` are justified.
- The accepted force-quit limitation is documented in both required documents. I have not reopened that decision.

**Pending owner checks**

Only Rishabh’s judgment of the combined Mac experience: traffic lights, dragging, wording and the removal/reload flow. Native lifecycle, shell, Login Items and file-delivery verification remain technical work for the lead or builder.

**Inspection and verification limits**

I read the packet, delta, earlier findings and verdicts, diagnosis, approved mockup sections, bridge amendments, relevant shell review record, implementation, changed regression bodies, README and building documentation. I traced all five named engine files, plus the skill installer and the tray’s actual signal/teardown implementation.

`git diff --check 59c4e3d..1f2e27f -- desktop docs/building` passed.

The brief prohibited test runners, Electron, servers, writes and process control. I therefore did not independently reproduce the reported 107 unit passes, 15 e2e steps, three removal passes or mutation failures. Native macOS cleanup and actual Electron `will-quit` integration remain unchecked.

After adding D1’s regression, run:

```sh
cd ~/labs/projects/anyscribe-wt/mac-2c-app/desktop
npm test

env -i HOME="$HOME" PATH=/usr/bin:/bin \
  ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python \
  node test/e2e.js

env -i HOME="$HOME" PATH=/usr/bin:/bin \
  ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python \
  node --test test/removal.e2e.js
```

No files were written, applications launched or processes signalled.
~~~~

# Round 5

## report-sol-r5.md

~~~~
**NOT YET.** The ordinary port cases are addressed, but the new parser can still choose the live old tray’s port. The work otherwise fits the approved app scope.

Reviewed **5634e13**, focusing on `1f2e27f..5634e13`, against engine **b22df16**. Later commits contain review records only.

- **D1: PARTLY.** Binary plists and single `--port N`, `--port=N`, or `-p N` options are covered. Other valid arguments bypass the protection below.
- **B2: PARTLY.** Normal quit kills the uninstaller’s group. The independent tray teardown can still reach a reopened engine when its port is misread.

**E1. should-fix | CONFIRMED by reproduction and trace | The tray parser disagrees with the engine’s argument parser.**

Where: old-launcher.js:84 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:84`), feeding engine.js:99 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/engine.js:99`).

The regular expression takes the **first** port option and misses the attached short form. The engine uses Typer/Click, which accepts `-p8470` and uses the **last** repeated option.

Read-only module probes, with an in-memory PID-file reader and supplied command lines, produced:

| Existing tray’s arguments | Tray’s actual port, traced through Click | App’s chosen port |
|---|---:|---:|
| `--port 8470` | 8470 | 8471 |
| `--port 8457 --port 8470` | 8470 | **8470** |
| `-p8470` | 8470 | **8470** |

The saved-port path also incorrectly retains 8470 in the latter two cases.

Concrete scenario: an old tray already runs with either argument form, its server has died, and its launcher records are absent. The app can start on 8470. Removal pauses that engine and signals the old tray. A normal quit kills the uninstaller but leaves the tray’s independent teardown. Reopening can again choose 8470, where that teardown can send `/api/shutdown`. The tray retains its former child reference, so `_shutdown_server()` still calls `_post_shutdown(port)`.

I reproduced the wrong port selection and traced the shutdown path; I did not reproduce the timing across real app instances. This tray predates the app, so it is outside the settled “tray started later” exception.

**Fix:** match the engine’s accepted argument forms and repeated-option behavior, or conservatively avoid every supplied port candidate. Add regressions for both cases, including saved-port reuse. A held real-tray teardown should then verify normal quit/reopen preserves the new engine’s PID and empty crash history. The current fixture at removal.e2e.js:116 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/test/removal.e2e.js:116`) is a Node interval process, so it cannot exercise that teardown.

No other new finding.

**Answers to the builder’s spec corrections**

- `install-skill` is correct. `--force` refreshes bundled files, but overwrites existing contents; customized-skill preservation is not established.
- `turnOff({choice})`, the bash-profile shadowing refusal, and reasons accompanying `ok: true` are sound corrections.
- Carry-over after confirmed login-item removal, followed by system read-back, is sound.
- The original shutdown explanation was incomplete: the fallback is **8457**, and server-PID termination matters too. Pausing protects uninterrupted removal.
- Awaiting the removal step and keeping real-engine tests separate from `npm test` are justified.
- Round 5’s direction is sound, but “never chooses a port the old launcher records or serves” exceeds the implementation’s evidence because of E1.

Both settled limits are documented in the journal and architecture document. I have not reopened them. The approximate force-quit window remains supplied documentation, not independently measured evidence.

**Pending owner checks**

Only Rishabh’s judgment of the combined Mac experience: traffic lights, dragging, wording, and the removal/reload flow. Native process cleanup, shell behavior, Login Items, and file delivery remain technical checks for the lead or builder.

**Verification and limits**

I inspected the packet, delta, diagnosis, prior findings and verdicts, settled declined list, approved mockup sections, bridge amendments, relevant shell review records, implementation and regression bodies, README and building documentation. I read all five named engine files plus the actual tray teardown, skill installer, and installed Typer/Click argument handling.

The source/documentation delta passes `git diff --check`; the worktree remains clean. No files were written or processes started or stopped.

The brief prohibited test runners and app launches. Therefore **113 unit passes, 15 e2e steps, three removal passes, and mutation failures remain supplied evidence**. After adding E1’s regressions, run:

```sh
cd ~/labs/projects/anyscribe-wt/mac-2c-app/desktop
npm test

env -i HOME="$HOME" PATH=/usr/bin:/bin \
  ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python \
  node test/e2e.js

env -i HOME="$HOME" PATH=/usr/bin:/bin \
  ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python \
  node --test test/removal.e2e.js
```

Native macOS `plutil`, `ps -ww`, actual Electron `will-quit`, real tray teardown, LaunchAgent removal, Finder/Dock delivery, and combined window behavior remain unverified here. The exact native plist read is:

```sh
/usr/bin/plutil -extract ProgramArguments json -o - \
  "$HOME/Library/LaunchAgents/com.anyscribe.tray.plist"
```
~~~~
