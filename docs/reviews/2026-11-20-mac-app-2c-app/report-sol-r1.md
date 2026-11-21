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
