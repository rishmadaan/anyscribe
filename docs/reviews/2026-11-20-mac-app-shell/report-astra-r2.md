Note: home-folder paths rewritten to `~`.

~~~~
**NOT YET.** The fixes substantially improve the shell, but readiness can now report a dead engine as running, and log failures are not handled as promised. Stop invalidation also misses a restart continuation. Server ownership remains conditional after startup.

Reviewed shell `04986cc` against engine `4d9bb42`. The current worktrees’ relevant code matches those targets. No files were changed, and no Electron instance, server, test runner, or process-control operation was run.

**Round 1 dispositions**

“FIXED” below means the agreed code or documentation change is present. It does not certify the pending Mac checks.

| ID | Status | Evidence |
|---|---|---|
| C1 | FIXED | Failed or malformed job reads return `null`; quit, restart and Quit When Done distinguish unknown from empty. |
| C2 | PARTLY | Readiness checks the child’s PID, but shutdown trusts cached verification. See A2. |
| C3 | FIXED | Frames, redirects and popups share the navigation policy; event properties match installed Electron declarations. |
| C4 | PARTLY | Concurrent restarts are serialized, but a pending restart can continue after stop invalidation. See A4. |
| C5 | DECLINED-OK | Left settled, including the explicitly accepted polling interval limitation. |
| C6 | FIXED | Relative interpreter paths resolve against the app’s original working directory. |
| C7 | FIXED | Observed hidden-window completions persist by job ID; displayed rows are capped without dropping counts or the failure indicator. |
| C8 | FIXED | Engine survival after force-killing the app now fails the e2e instead of printing a passing GAP. |
| C9 | PARTLY | Filesystem exceptions are caught, but first-append failures escape the startup failure state; retry retains the old error. See A3. |
| F1 | FIXED | Known-idle quit is no longer prevented; shutdown occurs in `will-quit`. Native logout remains unverified. |
| F2 | FIXED | Unknown job reads no longer trigger Quit When Done or permit restart. |
| F3 | PARTLY | Automatic-launch and port-check cancellation are guarded; pending manual restart still bypasses stop invalidation. See A4. |
| F4 | FIXED | Removed `openAsHidden` and duplicated login state; system state is authoritative. Actual login launch remains unverified. |
| F5 | FIXED | Dashboard uses the default title bar pending slice 2c. |
| F6 | FIXED | Separator placement and conditional native headers implement the agreed change. |
| F7 | FIXED | Evidence now identifies `--hidden`, rather than claiming a tested macOS login launch. |
| F8 | FIXED | Version stamping is explicitly deferred to phase 3, as agreed. |
| F9 | FIXED | Removed fallback; `--watch-stdin` is unconditional. |
| F10 | FIXED | Add-ons directory creation is restricted to packaged mode. |
| F11 | FIXED | Quit question focuses the app and uses the visible dashboard as parent. Native presentation remains unverified. |
| F12 | FIXED | The application menu is explicitly recorded for phase 3. |

A1 and A4 concern the revised lifecycle code. A2 and A3 are remaining gaps in the C2 and C9 fixes.

**A1. should-fix | CONFIRMED | Readiness can permanently miss an engine exit.**

Where: engine.js:234 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:234`), especially `_waitReady()` at lines 247–260.

Scenario: the child answers health, then exits while `_health()` is still awaiting the response or JSON. The exit listener records `attempt.exit`, but does not call `_onExit()` because `attempt.ready` is still false. `_waitReady()` subsequently accepts `'ours'`, sets `ready = true`, and reports `running`. The exit event has already happened, so no automatic restart follows.

The previous implementation checked `attempt.exit` after the awaited health response. This delta removed that check.

A read-only Node reproduction supplied that interleaving to the actual `_waitReady()` method, with no child process:

```text
started: true
state: running
childExitCode: 1
crashes.exits: []
```

The dashboard can fail to load while the shell continues reporting a running engine. Restart can then be refused because `/api/jobs` is unreachable.

Fix: recheck the attempt’s exit and ownership after health completes, before accepting readiness. Add a regression that delivers a successful health response after the child’s exit event; verify the restored check fails when removed.

**A2. should-fix | PLAUSIBLE | Startup verification does not bind the later shutdown request to that server.**

Where: engine.js:345 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:345`), `_stopNow()`.

`this.verified === child` establishes who answered an earlier health request. It does not establish who receives a later request to the same port. `_stopNow()` closes stdin first, then sends unauthenticated `POST /api/shutdown`, without even rejecting an already-exited child.

Scenario: the verified engine exits during shutdown and another server takes the port before the POST connects. That server can receive the shutdown request despite having a different PID.

An in-memory probe with an already-exited, previously verified child confirmed that `_stopNow()` still issues the POST. I did **not** reproduce a live port takeover or stop another server. The existing C2 tests cover an unverified server during startup, not replacement after verification.

Fix: use the owned stdin/process channel for shutdown, or authenticate the control request with per-launch identity checked by the receiving engine. Another separate health check would still leave a race. Test replacement of the listener after verification.

**A3. should-fix | CONFIRMED | An unwritable log file can still produce a successful startup, and its error cannot be retried.**

Where: engine.js:40 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:40`), `AppLog`, and `_launch()` at lines 203–238.

The constructor creates the directory and checks file size. For an existing small log file, neither operation establishes append permission. `_launch()` checks `log.error` before spawning; the first append happens afterward. An append failure then sets `log.error`, but nothing converts it into the advertised failure state.

A read-only simulation replaced filesystem, network and spawning operations with in-memory stand-ins. The actual startup code returned:

```text
initial log error: null
started: true
spawned: 1
state: running
logError: EACCES: app.log is not writable
failure: null
```

This contradicts the README’s promise that an unwritable log prevents engine startup and displays the reason. The existing test only makes the *directory* invalid, which fails earlier.

Separately, `error` stays latched permanently. After the underlying problem is repaired, Try again checks the same error and fails without attempting to reopen the log.

Fix: establish appendability before spawning, retain the in-memory diagnostic tail, and reopen/revalidate logging on retry. Cover an unwritable existing file, later write failure, and repair followed by Try again.

**A4. should-fix | CONFIRMED at supervisor level | A pending restart adopts the stop’s new generation.**

Where: engine.js:375 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:375`), `restart()`.

Unlike `start()`, `restart()` does not capture its generation when requested or check for invalidation after awaiting `jobs()` and `_stopNow()`. It eventually calls `_launch(..., this.gen)`, adopting whichever generation now exists.

Scenario: restart waits for the job list; a stop invalidates outstanding work; the job response arrives. Restart still stops and launches. With queued `stop()`, this can start an unnecessary replacement and delay completion of the stop through another readiness wait.

An in-memory reproduction suspended `jobs()`, called `stopForQuit()`, then released the response. It recorded:

```text
quitGen: 1
launchGen: 2
currentGen: 2
restart result: { ok: true, reason: null }
```

This proves the invalidation gap. It does **not** prove an engine survives an actual Electron quit; Electron teardown and the stdin watcher may prevent that outcome.

Fix: give the complete restart operation a cancellation identity that its own internal stop cannot overwrite. Check it after each await. Add restart-versus-stop coverage, rather than relying only on concurrent-restart and automatic-crash tests.

**Pending owner checks**

The lead or builder should perform the technical Mac checks: idle logout and shutdown, login launch without a window, Login Items approval/external changes, quit-dialog visibility and choices, Dock modes, and draggable windows. These are not code-repair tasks for Rishabh.

After those pass, Rishabh should confirm the actual menu, light/dark indicators, startup screen and quit flow are usable. Packaging and Finder installation remain phase 3.

**Verification and limits**

I read every file explicitly named by the brief, including the full delta, both prior reports, binding fix plan, proof and declined list. I inspected the affected supervisor, Electron wiring, bridges, startup page, logic, regression tests, e2e, README and building documentation; the relevant approved mockup sections; and the engine’s health, job, cancellation and shutdown integration. Installed Electron declarations support the new frame and redirect handler signatures.

The engine’s own process-group exit path supports the shell’s detached spawning and group signalling. I found no new navigation-policy defect in this pass.

Read-only Node probes reproduced A1, A3 and the supervisor behavior in A4. A2’s live timing remains untested. The production-code/documentation delta passes `git diff --check`. The claimed 43 passing tests and 11 e2e steps remain supplied evidence, not independently rerun results.

After adding the missing regressions, run:

```sh
cd ~/labs/projects/anyscribe-wt/mac-shell/desktop && npm test
```

The integrated e2e also needs repeating against exact engine `4d9bb42`. The packet describes an exported engine and interpreter wrapper but does not give that wrapper’s path or full invocation, so I cannot supply an exact equivalent command from the evidence provided. Native Mac behavior, visual rendering, real-job quitting and live race timing were not checked under this review’s read-only restrictions.
~~~~
