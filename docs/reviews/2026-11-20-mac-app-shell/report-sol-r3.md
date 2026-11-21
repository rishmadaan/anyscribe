Note: home-folder paths rewritten to `~`.

~~~~
**NOT YET.** The rebuild fixes the stale health response, HTTP shutdown, logging and menu findings. A plain `stop()` can still be overridden by a restart already waiting for the old engine to exit.

Reviewed shell **2383f26** against engine **4470a4d**. The shell worktree’s code matches the reviewed commit; later commits change review files only.

| Prior finding | Status | Evidence |
|---|---|---|
| A1 | FIXED | Exit clears the current run before readiness resumes. A delayed health reply produced `starting, stopped`, never `running`. |
| A2 | FIXED | Stop uses stdin and process-group signals, with no HTTP shutdown request. |
| A3 | FIXED | Each launch probes appendability; successful probes and writes clear the error. |
| A4 | PARTLY | Stop during the jobs read is handled. Stop during the subsequent termination wait still permits relaunch. See new A1 below. |
| R2, engine round 3 | FIXED | Every spawned run’s exit handler signals its process group, including exits before readiness. Real helper removal remains supplied test evidence. |
| G1 | FIXED | Failed completions sort first, then newest; reproduced with seven completions. |
| G2 | FIXED | README and journal disclose that any quit question cancels logout. Native behavior remains unchecked. |
| G3 | FIXED | Waiting rows are capped at five plus “and N more”; running rows remain visible, including while quitting. |
| G4 | FIXED | Unknown status offers the approved three choices; the header gains “not answering” after three failed reads. |
| G5 | FIXED | Journal names and descriptions reflect the rebuilt supervisor. |
| G6 | FIXED | A repaired log is probed again successfully; the old error no longer blocks retry. |

**New A1. should-fix | CONFIRMED | Stop does not cancel a restart’s pending relaunch.**

Where: engine.js:357 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:357`), particularly `_cancel()`, `_onExit()` at line 317, and `restart()` at line 419.

Scenario:

1. `restart()` obtains an idle jobs list, sets `restartRequested = true`, and starts terminating the old child.
2. Before that child exits, `stop()` is called.
3. `_cancel()` leaves `restartRequested` true.
4. The child exits. `_onExit()` launches its replacement because that flag remains true and the app is not quitting.

A read-only Node probe exercised the actual supervisor methods with in-memory children, logging, network checks and signal functions. No process or server was started. Its output was:

```text
Before stop:
state: restarting
restartRequested: true

After stop completed:
restartResult: {"ok":true,"reason":null}
state: running
spawnCount: 2
ownedPid: 90000001
```

The new regressions at engine.test.js:457 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/test/engine.test.js:457`) stop while the **jobs read** is suspended. They never reach this later termination phase.

**Fix:** make an explicit stop revoke the pending relaunch, while preserving restart’s own internal termination request. Add a regression that holds the old child alive after restart sends SIGTERM, calls `stop()`, then emits exit. Assert that stop finishes with no replacement child and state `stopped`; mutation-test that protection.

This is a supervisor contract defect. `main.js` currently uses `stopForQuit()`, whose permanent quitting flag prevents this relaunch. I separately reproduced that protection. This finding does **not** establish an engine surviving an actual Electron quit.

**Pending owner checks**

No owner decision is required for the correction. The builder or lead still needs to verify on a Mac:

- Idle logout and shutdown complete.
- Login launch opens no window; Login Items approval and external changes are reflected.
- Quit dialogs appear visibly and all three choices work with real jobs.
- Window dragging, Dock modes, menu headers and light/dark tray indicators work.

After technical verification, Rishabh should judge the actual startup screen, menu and quit flow. Those implementation checks are not his repair tasks.

**Verification limits and inspected material**

I read the named packet, complete round 3 delta, prior reports, verdict ledger, binding plans, diagnosis, proof and declined list. I inspected the supervisor, Electron wiring, logic, preloads, startup page, supervisor and logic tests, fake engine, e2e, icon generator, relevant documentation and approved mockup sections. I traced the exact engine commit’s health, jobs, cancellation, stdin watcher and process-group exit paths. Engine source at the e2e’s **62cba9c** matches **4470a4d**.

Read-only probes confirmed the dispositions described above. The desktop/building-documentation delta passes `git diff --check`. No files were changed.

I did not run test runners, Electron, servers, real signals or mutation tests, as prohibited. The reported **49 passing tests and 11 e2e steps remain supplied evidence**, not independently rerun results. Native rendering, real-job quitting and live helper cleanup were not independently verified.

After adding the missing regression, run:

```sh
cd ~/labs/projects/anyscribe-wt/mac-shell/desktop
npm test
```

Repeat the integrated e2e against the exact engine snapshot. The packet describes an exported engine and interpreter wrapper but does not provide the wrapper’s path or complete invocation, so that integrated command is not reproducible exactly from the supplied proof.
~~~~
