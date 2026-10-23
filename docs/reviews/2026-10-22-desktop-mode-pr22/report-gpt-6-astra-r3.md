**NOT YET.** Reviewed frozen commit `240766b454338925bb0e987de20135ec73965dca`. I would not merge it yet: W/F8 still fails by deterministic Windows code trace. The claimed skip is absent. The remaining round-2 fixes are present, and I found no additional confirmed production defect introduced by this fix wave.

This is the right instrument for the owner’s request: native launchers and login startup around the existing browser dashboard, with no new runtime dependency or signing cost. CLI and MCP operation remain independent of the desktop app.

| Round-2 finding | Status | Evidence |
|---|---|---|
| W/F8 | **NOT FIXED** | `tests/test_desktop.py:342` avoids the missing constant but still expects a signal that Windows never sends. |
| C1/F12 | **FIXED** | `core/tray.py:133–170` checks the command form and requested role. Literal probes reject interpreter-path and wrong-role cases and accept the required aliases and quoted Windows command. |
| C2/F10 | **FIXED** | `core/desktop.py:216–219` refuses a different installed port before signalling or stopping the tray. An equal port passes this guard. |
| C3/F9 | **FIXED** | `core/desktop.py:191,229` separates exit zero from failure and waits for the winning tray without spawning bare `ui`. |
| C4 | **FIXED** | `core/tray.py:64` gives an explicit `app` field precedence and requires typed legacy fields. Synthetic response probes passed. |
| C5/F14 | **FIXED** | `cli/tray_cmd.py:126–211` uses the same lifecycle lock for startup, restart and teardown, plus `closing` checks. Tests distinguish both races and the starting-server case. |
| C6 | **FIXED** | Cancellation copy, `--no-launch` explanation, installation order, supervision and security wording match the implementation and qualified evidence. |
| F11 | **FIXED** | User and skill troubleshooting distinguish the lifetime OS lock from the PID record. |
| F13 | **FIXED** | Configuration documentation inventories the desktop manifest, assets and lock. |
| F15 | **FIXED** | Duplicate changelog/troubleshooting prose is removed; generated documentation changes reflect the corrected source. |

“FIXED” here means confirmed by source inspection and the permitted probes. It does not mean I independently reran the test suite.

**C1 · should-fix · CONFIRMED: the Windows test correction still fails.**

Location: [tests/test_desktop.py:342](<repo>/tests/test_desktop.py:342), with the production branch at [core/desktop.py:169](<repo>/src/anyscribe/core/desktop.py:169).

The test runs two parameter values, `"posix"` and `"nt"`. It changes `desktop.os.name` only for `"nt"`.

On a real Windows runner, the `"posix"` parameter therefore leaves `desktop.os.name == "nt"`. `_signal_restart()` immediately returns `False`, so `kills` remains empty. The assertion nevertheless expects:

```python
[(4242, None)]
```

Replacing `signal.SIGUSR1` with `getattr(..., None)` changes the failure from `AttributeError` to `AssertionError`. It does not fix the test. The nearby Windows skip belongs to a different test.

The smallest correction is to skip this parameter on actual Windows while retaining its Windows case:

```python
if os_name == "posix" and sys.platform == "win32":
    pytest.skip("SIGUSR1 is POSIX only")
```

Then run on Windows:

```powershell
python -m pytest "tests/test_desktop.py::test_open_falls_back_to_stop_and_start_when_restart_fails[posix]" -q
python -m pytest tests/test_desktop.py tests/test_launcher.py tests/test_tray.py tests/test_autostart_route.py -v
```

The first should skip; the complete desktop job must pass on the corrected commit. No CI result for `240766b` was supplied during this review, so the brief’s claim that this finding is fixed exceeds the evidence.

**New defects introduced by the fixes:** none confirmed beyond this incomplete correction.

The concrete cases requested in the brief resolve as follows:

- **Process identity:** literal regex probes rejected a `python -c` command under an `anyscribe` path and an `anyscribe https://…` command when checking for a tray. `scribe tray`, `ascli tray`, quoted Windows executable paths and Windows uppercase spelling matched. I inspected the real-child tests but did not execute them.
- **Health identity:** synthetic HTTP responses containing `app: "ANYSCRIBE"`, `app: ""`, an explicit foreign app, list-valued dependencies or null legacy fields were rejected. The accepted pre-0.18 string-version/dictionary-dependencies shape still passed.
- **Port handling and duplicate startup:** equal installed ports pass the mismatch check. Exit-zero duplicates wait for health; exit-one failures retain the intended direct-server fallback. These lifecycle paths were traced, not executed.
- **Quit during restart:** teardown marks the state closing before waiting for the shared lock. It stops a child created by an already-running restart; a queued restart sees closing and creates nothing. The tests assert the identities of stopped/surviving children. I inspected the builder’s mutation-failure evidence without independently reproducing it.
- **Failed reinstall after manifest deletion:** the operation is not transactional. A launcher or login item can remain, and Windows/Linux may already have a running tray when service installation fails. `status()` reports “Partly installed” and does not claim a healthy installation. Without the manifest, its reported port falls back to 8457, so it is not a complete inventory of a partial custom-port installation. The identified tray/server records remain available for cleanup or retry.
- **Windows stale `server.pid`:** shutdown reads it with the `ui` role requirement. A PID naming an unrelated process is rejected before termination. This respects the explicitly accepted command-line identity boundary.
- **Finder and `pythonw`:** launcher rendering preserved paths containing spaces and apostrophes. Minimal-PATH rendering included the documented dependency directories. I traced detached-child redirection and missing-stream handling; native Finder and Windows click-through were not performed.

No additional owner decision is needed to fix C1. The developer should correct the test and provide green CI for the resulting SHA. Windows click-through remains owner-deferred, and the Linux stranger test remains blocked by the offline machine; neither is an additional blocker imposed by this review.

I read all sources named in the brief: both reviewers’ round-1 and round-2 reports, the fix brief and builder report, design, the twelve named Python implementation files, both installers, CI workflow, all six named test files, and every listed README, changelog, backlog, user, skill, architecture and journal document. Supporting inspection included fixtures, paths, file utilities, the referenced implementation plan, generated-document changes, the seven-commit fix diff and relevant whole-PR changes.

The permitted local health request returned curl exit 7, and the launchctl query returned no matching row in this restricted session. Those results do not independently verify the lead’s host-side 14/14 report, nor establish that the host installation is broken.

The brief prohibited execution of the following relevant checks, so I did not run them:

```bash
python -m pytest tests/test_desktop.py tests/test_launcher.py tests/test_tray.py tests/test_autostart_route.py tests/test_install_sh.py tests/test_web.py -q
anyscribe desktop open --port 8457
anyscribe desktop open --port 9000
anyscribe desktop install --port 9000 --yes
anyscribe desktop status --json
anyscribe desktop uninstall --yes
```

Not checked independently: pytest, mutation runs, native lifecycle actions or platform click-through; no files were changed.  
Remaining risk: the Windows CI test is still incorrect at this SHA. Fix it and verify the resulting CI before merging.