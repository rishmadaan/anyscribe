Note: home-folder paths rewritten to `~`.

~~~~
**NOT YET.** The Electron shell fits the approved job and the scope of this development slice. Its current safety checks do not establish the six invariants, particularly around quitting, engine ownership, and navigation.

Reviewed `7ab1539..880ed2c` in `~/labs/projects/anyscribe-wt/mac-shell`. The implementation still matches that target; `e97ef9d` adds only review material.

**Findings, most severe first**

**C1. blocker | CONFIRMED | Failed job reads permit silent interruption.**  
Where: engine.js:321 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:321`), main.js:271 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/main.js:271`), main.js:305 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/main.js:305`).

A two-second timeout, HTTP 500, invalid JSON, or missing endpoint becomes `[]`. Consequently:

- Quit proceeds without asking.
- Quit When Done immediately stops the engine.
- Restart engine passes its active-job guard.

An unresponsive HTTP endpoint does not establish that its worker threads stopped transcribing. The builder’s explanation to the contrary is wrong.

Malformed successful responses also escape validation. `{"jobs":{}}` reaches array operations; `[null]` reaches `job.status`. Read-only Node calls reproduced `jobs.filter is not a function` and `Cannot read properties of null`.

**Fix:** distinguish a validated job list from unknown status. Unknown status must prevent automatic quitting and restarting, preserve the last known information, and offer an explicit stop decision. Validate the array and its entries. Treat the pre-2a compatibility path as lacking this protection.

**C2. blocker | CONFIRMED | The readiness check does not prove ownership of the server.**  
Where: engine.js:188 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:188`), engine.js:257 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:257`), engine.js:287 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:287`).

Trace: the port precheck succeeds; another anyscribe instance takes the port while Python starts; its health response arrives before this child’s announcement or exit. `_healthy()` accepts only the public string `app: "anyscribe"`. `_waitReady()` can therefore mark this child ready while the responding server belongs to someone else. No announcement is required, and the announcement is checked before the awaited health request, not after it.

The window can load the other server, and `stop()` can POST `/api/shutdown` to it. Killing the child by its own pid does not make that HTTP shutdown safe.

The roll-forward fixture prints its alternative-port announcement immediately and serves the original port from the same fake process. It does not test delayed announcements or an independently owned listener.

**Fix:** establish per-launch server identity and authenticate control requests, or use an exclusively owned communication channel. Add strict-port behavior in the engine. Waiting for a startup sentence alone is insufficient because it precedes the actual bind.

**C3. blocker | CONFIRMED | Navigation confinement excludes subframes and redirects.**  
Where: main.js:315 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/main.js:315`).

Only `will-navigate` and initial `window.open` requests are filtered. Electron’s installed API declarations explicitly distinguish:

- `will-navigate`: main-frame navigation.
- `will-frame-navigate`: main-frame and subframe navigation.
- `will-redirect`: server redirects.

There is no handler for the latter two. The dashboard has no frame restriction in its HTML or server response setup. A dashboard script can therefore embed an outside-origin iframe; an allowed local navigation can also redirect outside the allowed origin.

This confirms a confinement defect. I have **not** demonstrated a bridge privilege escape: the IPC URL check would reject an outside-origin sender.

**Fix:** enforce the origin policy for frames and redirects, restrict frame content, and ensure permitted child windows receive the complete policy. Test direct navigation, redirects, iframes, and popups separately.

**C4. blocker | CONFIRMED | Concurrent restarts can lose ownership of a live child.**  
Where: engine.js:303 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:303`), engine.js:277 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:277`).

Two `restartEngine()` calls can both pass the initial state check and wait for `/api/jobs`. Neither marks the restart in progress before that wait.

Both can then stop the same old child. One stop can finish and start a replacement before the other stop finishes. The second stop unconditionally sets `this.child = null`, discarding the replacement’s ownership record. Overlapping port checks and launches can also create two children. A displaced readiness loop returns on the identity mismatch without stopping its displaced child.

**Fix:** serialize start, stop, and restart through one lifecycle operation; claim the operation before the first await. Use an operation identifier to invalidate stale continuations, and never clear or abandon another operation’s child. Add concurrent-restart and restart-versus-quit tests asserting individual child identities.

**C5. blocker | CONFIRMED | A valid empty job snapshot does not reserve an idle engine.**  
Where: main.js:271 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/main.js:271`), engine.js:307 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:307`).

Even with successful HTTP responses, checking jobs and stopping are separate operations. A transcription submission can arrive after the empty list was produced and before shutdown begins. The engine still accepts submissions during that interval. The newly accepted job receives no quit question and can be interrupted by quit or restart.

This also affects the final empty poll for Quit When Done.

**Fix:** coordinate with the engine: atomically stop accepting submissions and establish whether active jobs remain before committing to shutdown or restart. If work remains, retain it and obtain the appropriate decision. Test a submission deliberately interleaved between the idle check and shutdown.

**C6. should-fix | CONFIRMED | The documented development commands resolve Python from the wrong directory.**  
Where: README.md:14 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/README.md:14`), logic.js:23 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/logic.js:23`), engine.js:165 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:165`).

The README supplies `../.venv/bin/python`. `resolvePython()` returns it unchanged, but spawning uses `cwd: home`.

For this machine, the documented relative path therefore resolves to `/home/.venv/bin/python`, rather than the repository’s interpreter. The same problem affects the documented e2e command, whose engine uses a throwaway home. I reproduced the path calculations with Node.

**Fix:** resolve the development interpreter to an absolute path before changing directories, or require and document an absolute path.

**C7. should-fix | CONFIRMED | Finished jobs are not retained until the window opens.**  
Where: main.js:306 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/main.js:306`), logic.js:136 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/logic.js:136`).

Each poll replaces the entire menu source list. The integration engine at the proof’s `54f0d0b` returns every active job but limits the total summary to 50 when possible. Older completed jobs fall out of that response.

For example, after one hidden-window failure followed by 50 successful completions, the failure can disappear and its red indicator clear without the window being shown. Active jobs reduce the available finished-job slots further.

**Fix:** retain unseen completions by job identity in the shell, combined with an engine retrieval/acknowledgment contract that prevents missed completions between polls. Alternatively, explicitly revise the retention promise and show the limitation.

**C8. should-fix | CONFIRMED | The force-kill test can pass when its required safeguard fails.**  
Where: e2e.js:187 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/test/e2e.js:187`).

If the engine survives the killed app, the test prints `GAP`, kills the engine itself, and continues successfully. It does this even when `withFlag` is true.

Thus an actual regression in the integrated `--watch-stdin` path can still produce a successful test exit. The reported successful run is evidence for that particular run, but this test does not enforce the invariant.

**Fix:** assert that the engine follows whenever watchdog support is expected. Allow the historical compatibility gap only through an explicit test mode, and retain cleanup in `finally`.

**C9. should-fix | CONFIRMED | Shell filesystem errors bypass the startup failure screen.**  
Where: main.js:27 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/main.js:27`), engine.js:41 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:41`), engine.js:162 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/src/engine.js:162`).

An unwritable log directory can throw before any window exists. A failed runtime-directory creation, or later synchronous log write, can reject an unawaited start operation or throw from a child-output callback. These errors do not become the advertised Couldn't start state.

**Fix:** catch shell initialization and logging failures, present a usable failure state, and retain control of any child already spawned. Error presentation must work when the normal log file itself is unavailable.

**Answers to the builder’s open points**

The proof contains **eight** points, although the brief says seven.

1. **`stoppedRestarting`: agree.** The banner needs this distinction. Keep the addition documented; a structured stop reason could replace it later.
2. **Busy-port roll-forward: agree with the diagnosis, reject the claimed completeness of the workaround.** Strict-port behavior is appropriate, but server ownership and control-request identity still need C2.
3. **`hiddenInset`: agree that dashboard adaptation belongs to 2c.** Until drag behavior and traffic-light clearance are verified on Mac, do not describe the assembled interface as ready.
4. **Dashboard Shutdown: agree that 2c must replace or hide it.** Currently a deliberate shutdown is treated as a crash and restarted. That is a disclosed integration limitation.
5. **Development user-site behavior: reasonable, with limits.** The hardcoded Python 3.13 directory is a bundled-runtime assumption. Starting successfully in a development venv does not prove packaged add-on installation.
6. **Menu layout and extra wording: reasonable adaptation.** The text rows preserve the stage information. Native rendering and keyboard behavior still need verification.
7. **Raw startup error details: acceptable.** A truthful general sentence plus actual stderr is preferable to invented paraphrasing. C9 remains uncovered.
8. **Unreachable means no jobs: reject.** HTTP availability and transcription-worker activity are separate facts. This is C1.

The old-engine fallback also needs an integration gate beyond the disclosed orphan-process gap. At base `7ab1539`, CLI startup invokes the automatic skill updater without honoring `ANYSCRIBE_APP`. Running that engine against the real home can touch Claude skill files. Slice 2a supplies the guard. A throwaway-home run cannot establish the approved “No surprise skill” promise for the old engine.

**Pending owner checks**

No code correction above requires an owner decision. After the builder verifies the native paths, the owner should confirm that the actual Mac menu, Dock modes, startup screen, and quit choices feel usable in his workflow. Packaging and Finder installation remain phase 3.

**Verification limits and inspected material**

This was strictly read-only. I ran no tests, build, Electron instance, server, or process-control command, and wrote no files.

I read the complete review packet and settled declined list; the approved mockup sections 2, 6, 7, 9 and “For the build”; all desktop JavaScript, HTML, package files, tests and icon-generation code; the changed building documentation and `.gitignore` diff. I traced the integration engine’s relevant startup, health, job-list, cancellation and shutdown paths, including the proof’s `54f0d0b`, and checked relevant behavior against the installed Electron declarations. Binary icons were not visually verified.

`git diff --check 7ab1539..880ed2c` passed. The read-only Node checks reproduced the path-resolution mismatch and malformed-job exceptions.

Existing checks for the lead to run:

```sh
cd ~/labs/projects/anyscribe-wt/mac-shell/desktop && npm test
```

```sh
cd ~/labs/projects/anyscribe-wt/mac-shell/desktop && env -i HOME="$HOME" PATH=/usr/bin:/bin ANYSCRIBE_DEV_PYTHON=~/labs/projects/anyscribe/.venv/bin/python node test/e2e.js
```

The latter reproduces the main-engine compatibility run, not the integrated 2a run. The proof does not name the wrapper file used for that integration run, so its exact invocation is not reproducible from the packet alone.

The new race, failure-response, navigation and filesystem regression cases above have no existing test commands. Mac login, logout, Dock behavior, native dialogs, tray rendering and Finder launch could not be verified on this Linux host.
~~~~
