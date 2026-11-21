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
