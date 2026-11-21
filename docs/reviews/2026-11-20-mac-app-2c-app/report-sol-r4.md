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
