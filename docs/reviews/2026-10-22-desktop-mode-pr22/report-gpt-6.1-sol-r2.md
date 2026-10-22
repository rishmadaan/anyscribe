**NOT YET.** Reviewed `273be39c2933371e8dfb43c6c64c838b1f6cb5df`, including the seven-commit fix wave.

The approach fits the owner’s request: native launchers around the existing browser dashboard, with no new runtime dependency or desktop requirement for CLI/MCP transcription. Most fixes are real. Process ownership remains unsafe, and the fixes introduce additional lifecycle failures. Green CI would not resolve these findings.

**Earlier findings**

Paths below are relative to `<repo>/`. “FIXED” means supported by source inspection; runtime limits follow.

| Finding | Result | Evidence |
|---|---|---|
| F1 | FIXED | `core/desktop.py:197` requests SIGUSR1 recovery, then replaces the tray only if recovery fails. |
| F2 | FIXED | `core/desktop.py:225` stops a running tray without requiring a manifest; `core/service.py:139` captures launchctl output. Ownership caveat remains below. |
| F3 | FIXED | `docs/user/getting-started.md:97` tells installer users to skip `anyscribe ui`. |
| F4 | FIXED | `core/desktop.py:113` uses plain kickstart for the matching installed port. |
| F5 | DECLINED-OK | `core/service.py:66` retains the installing shell’s PATH, as accepted. |
| F6 | FIXED | `cli/desktop_cmd.py:89` prints “Starts at login: yes”; Settings caption is platform-neutral. |
| F7 | FIXED | `install.sh`, `run_post_install`, skips desktop setup when Linux has neither display variable. |
| C1 | PARTLY | Non-positive PIDs and ordinary unrelated sleepers are rejected, but `core/tray.py:143` still accepts any command containing “anyscribe”. |
| C2 | PARTLY | Version-only responses are rejected and attach/open/shutdown share the parser, but `core/tray.py:77` has an overly broad legacy bypass. |
| C3 | FIXED | `core/tray.py:30` provides a lifetime OS lock, acquired before publishing the tray PID. A new server-start race remains below. |
| C4 | FIXED | `cli/tray_cmd.py:139` supplies missing streams; server Popen explicitly redirects all streams; `web/app.py:66` repairs streams before Uvicorn configuration. |
| C5 | FIXED | `core/tray.py:243` also terminates the recorded server. The test checks signal delivery, not a real transcription’s inability to write afterward. |
| C6 | FIXED | Same recovery mechanism as F1. |
| C7 | PARTLY | Automatic-resume wording is gone, but “long jobs reuse” still overstates local-provider behavior. |
| C8 | FIXED | `core/desktop.py:296` requires an identified answering dashboard; documentation now defines that narrower meaning. |
| C9 | PARTLY | Help and flag tables are corrected; `docs/user/commands.md:944` still says “without starting it now”. |
| C10 | PARTLY | The three requested passages were changed, but `docs/building/architecture.md:239` still guarantees no Gatekeeper or SmartScreen prompt. |

**Round-two findings, most severe first**

**C1. blocker · CONFIRMED by trace · Command-line substring matching still permits signalling unrelated processes.**

Where: [core/tray.py:126](<repo>/src/anyscribe/core/tray.py:126), [core/tray.py:207](<repo>/src/anyscribe/core/tray.py:207), [core/service.py:191](<repo>/src/anyscribe/core/service.py:191).

Concrete cases:

- A stale `tray.pid` or `server.pid` points to `<repo>/.venv/bin/python -c "..."`. This unrelated Python process passes because its interpreter path contains “anyscribe”. Uninstall can terminate it.
- A stale tray PID points to an AnyScribe transcription command rather than a tray. `desktop open` can send that transcription SIGUSR1.
- `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 /usr/local/bin/scribe tray` contains no “anyscribe”. The supported alias is therefore rejected. On macOS, `uninstall-service` can consequently call `launchctl unload` despite a live tray, violating the toggle’s keep-running guarantee when that tray is launchd-owned.

Identity is also checked only when reading the PID, before waits and later escalation.

Fix: validate the exact command and expected role, including aliases, and record/check process creation identity before signalling or escalating. Add unrelated-interpreter-path, wrong-role, alias and PID-reuse regressions. The current real-child test deliberately uses a command containing no “anyscribe”, so it misses this defect.

**C2. should-fix · CONFIRMED by trace · Opening another port can stop the working installed dashboard. NEW.**

Where: [core/desktop.py:194](<repo>/src/anyscribe/core/desktop.py:194).

With the installed tray serving 8457, run `desktop open --port 9000`:

1. Port 9000 is free, but the global pidfile identifies the 8457 tray.
2. SIGUSR1 asks that tray to recover its own 8457 server.
3. Health on 9000 never appears.
4. The fallback calls `stop_tray(9000)`, which nevertheless kills the globally recorded tray and server serving 8457.
5. A detached tray starts on 9000, while the manifest and launcher still point to 8457.

This can interrupt an active transcription. Checking the plist’s port inside `_kickstart` happens too late to prevent it.

Fix: reject a conflicting port before signalling or stopping the existing instance. Suggested message:

> Desktop mode is installed on port 8457. To change it, run: anyscribe desktop install --port 9000

Test the complete open path with a live instance recorded for another port, not only `_kickstart`’s argv selection.

**C3. should-fix · CONFIRMED by traced interleaving · A duplicate tray’s successful exit can create an extra unmanaged server. NEW interaction.**

Where: [core/desktop.py:203](<repo>/src/anyscribe/core/desktop.py:203), [cli/tray_cmd.py:142](<repo>/src/anyscribe/cli/tray_cmd.py:142), [cli/main.py:250](<repo>/src/anyscribe/cli/main.py:250).

On Windows/Linux, two app clicks within 50 ms can both observe no published PID and spawn trays. The lock correctly excludes one tray, which exits **0**. If the winning tray’s server has not bound yet, `_await_health` reports `"exited"` for the loser. `open_dashboard` treats every exit as a missing-backend failure and launches bare `ui`.

There are then two server starters. The existing UI port scan can put one server on 8458. The fallback server is not recorded in `server.pid`, so desktop uninstall need not stop it.

Fix: distinguish successful duplicate exit from backend failure. On duplicate exit, wait for the winning instance; do not launch bare UI. Cover the complete concurrent-open path and assert the identities of all surviving server processes. The lock-only tests do not exercise this fallback.

**C4. should-fix · CONFIRMED by trace · Legacy compatibility overrides an explicit foreign identity. NEW.**

Where: [core/tray.py:74](<repo>/src/anyscribe/core/tray.py:74).

A 200 response containing:

```json
{"app":"another-program","version":"1","dependencies":{}}
```

passes identification. So does:

```json
{"version":null,"dependencies":null}
```

The fallback checks only that two keys exist. Consequently the shared parser can authorize opening, attaching to, or posting shutdown to a foreign program.

Fix: an explicit `app` field must take precedence and reject other applications. Apply legacy matching only when that field is absent, and validate the known legacy structure and value types. Retain the genuine pre-0.18 compatibility test and add both counterexamples. Describe legacy matching as a compatibility heuristic, not guaranteed identity.

**C5. should-fix · PLAUSIBLE · The restart lock excludes neither initial startup nor teardown. NEW concurrency exposure.**

Where: [cli/tray_cmd.py:126](<repo>/src/anyscribe/cli/tray_cmd.py:126), [cli/tray_cmd.py:194](<repo>/src/anyscribe/cli/tray_cmd.py:194), [cli/tray_cmd.py:235](<repo>/src/anyscribe/cli/tray_cmd.py:235).

The signal thread and menu restart share `restart_lock`, but initial `_start_server()` and both teardown calls bypass it.

A signal restart can pop the old process and pause before spawning. Quit and the final teardown can both observe no process. The restart can then publish a new child after the last teardown, leaving a server behind as the tray exits. Similarly, initial startup and a signal restart can overlap their check-before-spawn operations.

Fix: put startup, restart and teardown under the same lifecycle protection, with a shutdown flag that prevents spawning once Quit begins. Use barriers to test these interleavings. The existing idempotency test invokes callbacks sequentially after its fake icon loop has already finished.

**C6. nit · CONFIRMED · Some documentation still contradicts the implementation or evidence.**

- [cli/desktop_cmd.py:29](<repo>/src/anyscribe/cli/desktop_cmd.py:29): “long jobs reuse” excludes long local-provider jobs, which keep accumulated segments only in memory at [providers/local.py:106](<repo>/src/anyscribe/providers/local.py:106). Replace the uninstall copy consistently with:

  > Stopped anyscribe. If a transcription was running, run it again. Saved chunks may be reused; unfinished work may run again.

- [docs/user/commands.md:944](<repo>/docs/user/commands.md:944): replace the example comment with `# Set up desktop mode without opening the dashboard now`.
- [docs/building/architecture.md:239](<repo>/docs/building/architecture.md:239): replace the universal security-prompt claim with:

  > The launcher is generated locally and needs no separately signed app download. It avoided Gatekeeper prompts in our Mac test; Windows click-through remains unverified.

- The architecture’s supervision paragraph at line 62 still describes TCP-only attachment and pidfile-based exclusion. Replace those mechanisms with “health-response identification” and “a lifetime operating-system lock”. Its install-order summary at line 155 also needs the macOS-specific ordering already described above it.
- The skill reference’s claim that SIGTERM always runs teardown is false on Windows. Say: “Menu Quit performs teardown. POSIX SIGTERM/SIGINT do too; Windows desktop uninstall separately terminates the recorded server.”

Regenerate the corresponding published documentation after corrections.

**Answers and evidence limits**

The chosen instrument remains appropriate. No native app framework, signing purchase or new runtime is needed for the agreed job. CLI and MCP paths call the pipeline directly and do not require the desktop server.

The builder deviations are reasonable: capturing launchctl stderr even on exit 0, omitting `-k`, preserving working streams, and avoiding a restart while the owned server is still starting. However:

- The “alive but not answering” guard exists, but its dedicated behavior is not exercised by the idempotency test: that test’s `poll()` always returns an exited status.
- Quit followed by a click inside ten seconds and kickstart on an already-running job remain dependent on the lead’s live evidence.
- `tray.lock` remaining on disk after a crash is harmless because ownership is the OS lock, not file existence.
- Stale server PID safety remains subject to C1.
- Windows worker termination has improved structurally, but the recorded-server test cannot establish that a real job cannot write after uninstall.

The inspected mutation-test reports contain meaningful failing assertions, including survivor identity. I did not rerun those mutations.

**Checks performed and not performed**

Pure rendering probes passed: plist XML preserved spaces, apostrophes and ampersands; port 9000, PATH, Interactive process type, `SuccessfulExit=false` and throttle 10 were present. Linux quoting, percent escaping, PowerShell curly-apostrophe escaping and PATH de-duplication matched the implementation.

The installed manifest, launcher script and plist agree on port 8457 and Python 3.13. The installed plist contains the new settings.

`curl -s http://127.0.0.1:8457/api/health` returned exit 7; `launchctl list | grep anyscribe` returned no row; the permitted health helper returned false. These sandbox results do **not** establish that the host installation is down. Fetching [CI run 39808100206](https://github.com/rishmadaan/anyscribe/actions/runs/39808100206) failed, so its result remains unverified.

I read every explicitly named source, report, test and documentation file, and followed relevant references into the implementation plan, path configuration, file utilities, job manager, CLI/MCP calls and provider checkpoint paths. I also inspected both diff scopes and searched the package for signals, child spawning and port probes.

The brief forbids running the suite or lifecycle reproductions. Exact commands still requiring an authorized execution environment include:

```bash
cd <repo>
.venv/bin/python -m pytest tests/test_desktop.py tests/test_launcher.py tests/test_tray.py tests/test_autostart_route.py tests/test_install_sh.py tests/test_web.py -q
anyscribe desktop open
anyscribe desktop open --port 9000
anyscribe desktop install --yes
anyscribe desktop uninstall --yes
```

Run lifecycle commands only in disposable test state. I also skipped `anyscribe desktop status --json`: its CLI callback can refresh/delete Claude skill files before reaching status, conflicting with this review’s no-write instruction.

**Pending owner checks**

No owner action is needed to fix these findings. Native Windows click-through remains deferred, and Linux desktop execution awaits an available machine. Optional Mac acceptance remains Spotlight → type `anyscribe` → Enter, after Quit and while already running.

Skipped: tests, signals, lifecycle mutations and native Windows/Linux execution, as required. Remaining release risks are unsafe process identification, interruption of the wrong instance, and unmanaged servers during races.