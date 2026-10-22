**NOT YET.** Reviewed commit `24a532220c0ea2e7594e8da8ee0193cd8d5b1780`. CI is green on that exact commit, but the process-ownership, concurrent-start and Windows startup paths still contain blockers.

**Findings, most severe first**

**C1. blocker · CONFIRMED by trace · Uninstall can terminate an unrelated process.**  
Where: [core/tray.py:62](<repo>/src/anyscribe/core/tray.py:62), [core/tray.py:119](<repo>/src/anyscribe/core/tray.py:119).

After a crash or reboot, `tray.pid` can survive and its number can be reused by another program. `read_pidfile()` checks only whether that PID exists. Reinstall or uninstall then sends that unrelated process SIGTERM and potentially SIGKILL. Non-positive PID values are also accepted.

Fix: validate process identity, including creation identity, before signalling. Never treat a live numeric PID alone as ownership. Reject non-positive values. Test that an unrelated process survives unchanged; the present tests deliberately treat any live PID as a tray.

**C2. blocker · CONFIRMED by trace · The foreign-program boundary has two bypasses.**  
Where: [core/desktop.py:88](<repo>/src/anyscribe/core/desktop.py:88), [cli/tray_cmd.py:156](<repo>/src/anyscribe/cli/tray_cmd.py:156).

First, any HTTP 200 response containing a `version` key counts as AnyScribe. An unrelated program returning `{"version":"1"}` from `/api/health` therefore passes, and `desktop open` opens its dashboard.

Second, the login-started tray attaches to **any** listener without checking identity. Its **Open UI** action opens that listener directly. This bypasses the desktop refusal altogether. `stop_tray()` also posts `/api/shutdown` without identifying the recipient.

Fix: use an AnyScribe-specific identity response consistently before attaching, opening or requesting shutdown. Add tests that exercise the real identity parser. The existing foreign-port test replaces that parser with `False`, so it cannot catch this failure.

**C3. blocker · CONFIRMED by traced interleaving · Two simultaneous opens can create two trays.**  
Where: [core/desktop.py:162](<repo>/src/anyscribe/core/desktop.py:162), [cli/tray_cmd.py:139](<repo>/src/anyscribe/cli/tray_cmd.py:139), [core/tray.py:75](<repo>/src/anyscribe/core/tray.py:75).

On Windows or Linux, two clicks can both see no pidfile and spawn trays. Both trays can pass their own check before either writes the file. They then overwrite each other’s PID and both enter their icon loops. Their server starts can also race, with `ui` rolling one server onto another port.

Fix: acquire an operating-system lock before checking or publishing ownership, and hold it throughout the tray’s lifetime. Test simultaneous starts with a barrier. `test_open_does_not_spawn_second_tray` covers an already-published PID, not this race.

**C4. blocker · CONFIRMED by source trace, not native Windows execution · The windowless Windows server path lacks usable output streams.**  
Where: [core/service.py:159](<repo>/src/anyscribe/core/service.py:159), [cli/tray_cmd.py:160](<repo>/src/anyscribe/cli/tray_cmd.py:160), [web/app.py:68](<repo>/src/anyscribe/web/app.py:68).

The Windows shortcuts use `pythonw.exe`. The tray subsequently launches its server using that same interpreter, with no stdin/stdout/stderr redirection. Windowless Python can have `sys.stdout=None`; the inspected Uvicorn default formatter calls `sys.stdout.isatty()` during configuration. That raises before the server starts. `CREATE_NO_WINDOW` does not supply those streams. Python documents the windowless-stream behavior. [Python documentation](https://docs.python.org/3.13/library/sys.html#sys.__stderr__)

Fix: explicitly provide valid streams for the server child, preferably the existing tray log, including the direct login-shortcut path. Verify the actual `pythonw.exe` launch. CI currently creates a shortcut but does not launch the tray through it.

**C5. should-fix · CONFIRMED by trace · Windows uninstall can leave a transcription running after reporting it cancelled.**  
Where: [core/tray.py:118](<repo>/src/anyscribe/core/tray.py:118), [web/jobs.py:107](<repo>/src/anyscribe/web/jobs.py:107).

With a dashboard transcription running, uninstall requests server shutdown and immediately terminates the Windows tray. Windows termination skips the tray’s teardown. The server’s transcription runs in a separate `ThreadPoolExecutor`; stopping HTTP serving neither cancels that worker nor prevents its later vault write. Once the port closes, `stop_tray()` can return while that process continues working.

Fix: stop and verify the owned server process, including its workers, before declaring uninstall complete. Use a controlled long-running job in the regression test and assert that it cannot write after uninstall returns.

**C6. should-fix · CONFIRMED by trace · Clicking the app cannot recover from the dashboard’s Shutdown button.**  
Where: [core/desktop.py:162](<repo>/src/anyscribe/core/desktop.py:162), [system.py:54](<repo>/src/anyscribe/web/routes/system.py:54), [getting-started.md:284](<repo>/docs/user/getting-started.md:284).

Use the installed dashboard, click **Shutdown → Shutdown?**, then click the app again. Shutdown stops only the server; the tray remains alive. `desktop open` sees that tray and waits without starting or restarting anything, then raises `StartFailed`. The guide explicitly promises that clicking the app is the way back after Shutdown.

Fix: make this deliberate shutdown/reopen lifecycle work, either by shutting down the tray cooperatively or by letting an app click request a server restart. This does not require reopening the parked automatic crash-restart feature.

**C7. should-fix · CONFIRMED by trace · The promised checkpoint resume is broader than the pipeline supports.**  
Where: [desktop_cmd.py:29](<repo>/src/anyscribe/cli/desktop_cmd.py:29), [getting-started.md:272](<repo>/docs/user/getting-started.md:272).

The message promises every interrupted transcription “will resume from its checkpoint.” Short OpenAI and Deepgram jobs bypass `_transcribe_chunked()` entirely and create no checkpoint. An interrupted request must run again. Jobs are held in memory and are not automatically requeued on the next app launch.

The plan’s required wording was itself wrong here.

Exact replacement:

> Stopped anyscribe. Re-run interrupted transcriptions manually. Saved chunks may be reused, but unfinished work may run again.

Apply equivalent wording to the user guide and skill reference. Fix C5 before asserting that Windows work has actually stopped.

**C8. should-fix · CONFIRMED · “Healthy” means installation files exist, not that AnyScribe works.**  
Where: [core/desktop.py:239](<repo>/src/anyscribe/core/desktop.py:239), [commands.md:906](<repo>/docs/user/commands.md:906).

`healthy` ignores both process state and the health endpoint’s dependency verdict. With Python, launcher and login-item files present, it remains true even when the server is absent or ffmpeg is missing. The tests explicitly assert this behavior.

My permitted status command returned `server_running:false`, `healthy:true`, `reason:null`. The sandbox’s failed connection does **not** establish that the host server is down; it does demonstrate the meaning of this status field.

Fix: label this **Installation intact**, or separate installation integrity from operational readiness. Exact documentation wording:

> Status checks the recorded Python and installation files separately from the tray and server. Installation integrity does not establish transcription readiness.

**C9. nit · CONFIRMED · Several `--no-launch` descriptions still contradict the accepted macOS behavior.**  
Where: [desktop_cmd.py:63](<repo>/src/anyscribe/cli/desktop_cmd.py:63), [SKILL.md:80](<repo>/src/anyscribe/skill/SKILL.md:80), [commands.md:934](<repo>/docs/user/commands.md:934), [skill commands.md:408](<repo>/src/anyscribe/skill/references/commands.md:408).

These promise not to start the tray, although loading the macOS login item starts it. A correct note elsewhere does not repair misleading command help or the skill’s decision table.

Exact replacement:

> Do not open the dashboard now. On macOS, registering the login item still starts the tray; on Windows and Linux, this also skips starting it now.

**C10. nit · CONFIRMED evidence mismatch · Security-prompt claims exceed the recorded verification.**  
Where: [CHANGELOG.md:24](<repo>/CHANGELOG.md:24), [troubleshooting.md:597](<repo>/docs/user/troubleshooting.md:597), [journal:4](<repo>/docs/building/journal/2026-10-22-desktop-mode.md:4).

The Mac probe supports “no Gatekeeper prompt in this test.” It does not establish a universal absence of security prompts, particularly on Windows, whose click-through is explicitly unverified.

Exact replacement:

> The launcher is generated locally and needs no separately signed app download. It avoided Gatekeeper prompts in our Mac test; Windows click-through remains unverified.

This changes the claim, not the settled signing decision.

**Answers to the brief**

The instrument fits the owner’s job: retain the browser dashboard and existing Python package, adding native launchers and login registration. A native application framework is unnecessary for the agreed scope. The remaining defects are lifecycle and verification problems within that approach.

Checks supported by the code and permitted probes:

- Space/apostrophe shell arguments and plist XML round-tripped correctly. PATH de-duplication, Homebrew/Deno additions, port arguments, `KeepAlive`, throttle and `ProcessType` checks passed.
- Linux special-character and Windows curly-apostrophe renderings matched the intended escaping. This was rendering verification, not native execution.
- `desktop open` without a port reads the installed port from the manifest.
- Missing recorded Python is detected by file existence. That does not prove an existing interpreter still contains a working AnyScribe installation.
- Removing login registration preserves a live tray as intended; the documented macOS until-logout behavior remains accepted.
- Installer opt-out, git-method skip and desktop-failure banner paths are present and covered by the named tests.
- CLI and MCP transcription call the shared pipeline without depending on the desktop server.
- Dashboard binding remains `127.0.0.1`. The existing unauthenticated endpoints remain local; autostart capability expands to Windows and Linux as intended.
- [CI run 39777981708](https://github.com/rishmadaan/anyscribe/actions/runs/39777981708) succeeded for this SHA: Python 3.11/3.12/3.14, frontend, docs, macOS desktop and Windows desktop, including PowerShell parsing.

**Pending owner checks**

None required to resolve these findings. Native Windows and Linux verification remains engineering work under the previously agreed deferrals.

**Inspection and checks not run**

I read every source named in [brief-r1.md](<run folder>/brief-r1.md): design, plan, ledger, journal, the named core/CLI/routes/config files, installers, CI, all five test files, and all named documentation and skill files. I also followed the relevant references into test isolation, web startup/jobs, MCP, checkpoint/provider code, UI shutdown, and installed Uvicorn/CPython process handling.

No tests, installs, uninstalls, toggles, process starts/stops, edits or deletions were performed. The existing suite should be rerun by the lead after fixes:

```bash
cd <repo>
pytest tests/test_desktop.py tests/test_launcher.py tests/test_tray.py tests/test_autostart_route.py tests/test_install_sh.py -q
```

The Uvicorn stream failure can be checked without starting a server:

```bash
python3 -B -c "import sys, uvicorn; sys.stdout = None; uvicorn.Config('anyscribe.web.app:create_app', factory=True)"
```

Repeat these live probes outside the reviewer sandbox:

```bash
anyscribe desktop status --json
curl -s http://127.0.0.1:8457/api/health
launchctl list | grep anyscribe
```

Unverified: native Windows execution, simultaneous-launch reproduction, destructive lifecycle checks, and the lead’s mutation-test logs. The traced ownership and startup failures remain release risks despite green CI.