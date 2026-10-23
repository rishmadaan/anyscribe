**NOT YET.** Reviewed frozen commit `0382449cb7614057aefdc3f85fd857f435f66e79`. The Linux identity and Windows test fixes are real. F3 still has one exception that contradicts the required behavior and the updated documentation. I would fix that before merging.

| Round-3 item | Status | Evidence |
|---|---|---|
| F1 | **FIXED** | `core/tray.py:152–164` reads Linux `/proc` and uses `ps -ww` elsewhere. Synthetic probes accepted the long command and rejected empty, unreadable, disappeared and wrong-role entries. |
| F2/W | **FIXED** | `tests/test_desktop.py:321–350` skips the POSIX parameter on Windows. The Windows expectation avoids evaluating `SIGUSR1`. Other test references are protected by POSIX skips. |
| F3 | **PARTLY** | The no-tray mismatch now refuses before startup, and bare `open` uses `installed_port()`. However, a healthy AnyScribe server on another requested port bypasses the mismatch check entirely. |
| F4 | **FIXED** | The journal’s dated correction at line 144 explicitly supersedes both obsolete throttle statements. |
| F6 | **FIXED** | `architecture.md:62` now includes termination of the recorded server and removal of both PID files. |
| F5 | **DECLINED-OK** | The accepted command-line matching boundary remains unchanged. |

**C1 · should-fix · CONFIRMED: an already healthy second port bypasses the installed-port refusal.**

Where: [desktop.py:211](<repo>/src/anyscribe/core/desktop.py:211), [user commands:933](<repo>/docs/user/commands.md:933), [skill commands:418](<repo>/src/anyscribe/skill/references/commands.md:418).

Concrete scenario:

1. Desktop mode is installed on 8457.
2. A separately started `anyscribe ui --port 9000` is healthy.
3. `anyscribe desktop open --port 9000` opens 9000 successfully.

The installed-port check sits inside `if not health_is_anyscribe(port)`. When 9000 is healthy, execution skips that entire block and opens its browser URL. I evaluated the actual source condition with these inputs; the block containing `PortMismatch` was not entered.

Nothing is stopped in this case. The defect is the unmet refusal contract: both updated references promise exit 1 whenever desktop mode is installed on another port.

**Fix:** move the installed-port comparison before the health shortcut. Add a test with manifest port 8457 and requested port 9000 already healthy; assert `PortMismatch`, no browser opening and no lifecycle action.

**New defects introduced by these four commits:** none otherwise confirmed. C1 is a remaining gap preserved by the F3 fix.

The requested edge cases resolve as follows:

- **Linux empty/unreadable/disappearing process:** synthetic probes returned `False` without exceptions. Through `_read_pid`, these results become an absent PID rather than a termination target.
- **macOS process already exited:** a synthetic empty `ps` result returned `False`; the constructed command includes `-ww`.
- **Equal installed/requested port, no tray:** source trace reaches `_start_tray`; equality does not refuse.
- **No manifest or plist:** the real `installed_port()` logic, with missing-file inputs supplied in memory, returned `None`; the mismatch guard permits startup.
- **Windows/Linux manifest without plist:** the manifest supplies the port directly.
- **Reinstall 8457 to 9000:** the old manifest is deleted before the installer’s own `open`. macOS writes the new plist first; Windows/Linux proceed without an old manifest or plist blocking them.
- **Test isolation:** the suite redirects HOME before importing AnyScribe. The reviewed desktop fixtures also replace manifest, PID, log and plist paths and suppress real launchctl calls.

This is the right instrument for the requested job: an app launcher and login startup around the existing dashboard, using the existing Python installation and tray extra. These fixes add no runtime dependency. Desktop startup remains separate from CLI/MCP operation.

**Pending owner checks:** real Windows click-through remains explicitly deferred. The separate Linux stranger-test result is outside this checkout. Neither adds an owner decision or blocks this verdict; C1 is developer work.

I read every source named directly by the round-4 brief, the complete four-commit diff, and supporting launcher, service, tray-command, fixture, configuration, packaging, README, design and CI files. `git diff --check 240766b..0382449` passed.

I did not run the prohibited checks:

```bash
python -m pytest tests/test_desktop.py tests/test_tray.py -q
anyscribe desktop open
anyscribe desktop open --port 9000
anyscribe desktop install --port 9000 --yes
```

Native inspection was restricted: `ps -ww -o command= -p 66259` failed with “Operation not permitted”; `curl -s http://127.0.0.1:8457/api/health` exited 7; `launchctl list | grep anyscribe` returned no row. These results do not establish that the host installation is broken. CI success is reported by the brief, not independently verified here.

Not checked independently: pytest, mutation runs, real lifecycle actions or platform click-through. No files were changed.  
Remaining risk: F3 still opens a healthy second port despite the promised refusal.