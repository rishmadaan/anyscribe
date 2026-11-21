Note: home-folder paths rewritten to `~`.

~~~~
**GOOD TO GO for the round-4 changes in this development slice.** All five requested fixes are present. I found no new runtime defect. Native Mac validation remains pending.

Reviewed shell **787bfa1** against engine **b22df16**. Current shell HEAD **cd71ebf** differs only in review files; the inspected engine source matches its target.

| Finding | Status | Evidence |
|---|---|---|
| S3-A1 | **FIXED** | `stop()` revokes `restartRequested`. My in-memory reproduction finished stopped, with one child ever created and no current run. Omitting the guard in memory reproduced the second launch and successful restart. |
| G7 | **FIXED** | Both Stop and Quit actions call `finalQuit()` directly. `will-quit` calls `stopForQuit()`, which closes stdin, signals the owned process group and permanently prohibits relaunch. No job read or cancel loop remains in either action. |
| G8 | **FIXED** | Probes returned distinct “and 5 more waiting” and “and 2 more finished” rows, including when both appear together. |
| G9 | **FIXED** | Idle failure returned “anyscribe · Not answering”; Transcribing and Quitting retain the suffix. |
| G10 | **FIXED** | The dead `choice === 'quit'` branch is gone. Both question variants expose only the three supported choices. |

New findings:

**A1. nit | CONFIRMED | The README describes the new header too broadly.**

Where: desktop/README.md:103 (`~/labs/projects/anyscribe-wt/mac-shell/desktop/README.md:103`).

It says the header reads “anyscribe · Not answering” when no job is active. With an unseen finished job and three failed reads, the actual result is:

```text
anyscribe · 1 saved · not answering
```

The implementation matches the disclosed round-4 choice to retain the finished summary. Change the README condition to “when otherwise showing Ready.” No runtime correction is needed.

The quit-path evidence supports the design, with a timing limit: the reported **39 ms measures app exit against the fake engine**, not termination of real transcription work. At engine `b22df16`, cancellation is an in-memory flag checked at progress events. Removing those requests therefore removes no persistent cancellation record. The real engine retains its process-group hard exit and stdin watchdog, whose grace period is **10 seconds**. Real-job termination should not be reported as independently measured in milliseconds.

Pending owner checks:

- The builder or lead should verify idle logout/shutdown, login launch without a window, Login Items approval changes, real-job quit choices, window dragging, Dock modes, native menu headers and light/dark tray rendering on Mac.
- Rishabh then judges the actual startup, menu and quit experience. Technical verification and the documentation correction are not his repair tasks.

Verification and limits:

I read every file named directly by the brief, the approved mockup text, the changed source and relevant regression bodies, e2e and fake-engine code, bridges, startup page, README, architecture section and journal. I traced the target engine’s jobs, cancellation, stdin watcher, signal handling and process-group exit paths.

Read-only Node probes reproduced the restart guard’s effect and menu results. The reviewed source/documentation delta passes `git diff --check`.

I ran no test runner, Electron instance, server, real signal or filesystem mutation. **50 passing tests and 12 e2e steps remain supplied evidence.** The suite command is:

```sh
cd ~/labs/projects/anyscribe-wt/mac-shell/desktop
npm test
```

The packet omits the interpreter-wrapper path used for the exact-engine e2e, so its complete invocation cannot be reconstructed from the supplied proof.
~~~~
