# Fit review, round 3 (closing) (Claude Fable 5.1, Agent tool), target 240766b

Saved by the lead from the reviewer's final message (summary; full text in the session transcript).

VERDICT: NOT YET. CI on 240766b red in two jobs (python 3.11: new real-child alias test; windows-latest: the W/F8 test). Everything else in the fix wave is real; live Mac state consistent; docs match code.

Round-2 items: W/F8 NOT FIXED (posix param runs on Windows where os.name is nt; getattr only changed the expected value); C1/F12 PARTLY (regex and role right; Linux identity path unproven: ps truncation); C2/F10 FIXED (residual F3); C3/F9 FIXED; C4 FIXED; C5/F14 FIXED; C6, F11, F13, F15 FIXED.

New findings:
- F1 blocker CONFIRMED (CI) / mechanism PLAUSIBLE: on ubuntu-24.04 `ps -o command=` truncates (procps honours COLUMNS; piped width "undefined"); a pipx/uv path + `-m anyscribe tray --port 8457` is 77-90 chars, right at an 80-column cut → Linux users could have `desktop open` not seeing the tray and uninstall not stopping it. Fix: read `/proc/<pid>/cmdline` on Linux; `ps -ww` on macOS.
- F2 blocker CONFIRMED (CI): skip the posix param on win32 via `pytest.param(..., marks=skipif)`; restore `signal.SIGUSR1` in the expected list.
- F3 should-fix CONFIRMED by trace: desktop.py:216 gates the port check on `pid is not None`; after Quit, `desktop open --port 9000` spawns a 9000 tray outside launchd holding the lock; next app click (8457) eventually `stop_tray`s it (18 s, no message). Fix: compute `installed_port()` unconditionally and refuse on mismatch; `open_cmd` defaults `port` to the installed port; docs "while desktop mode is installed on one port".
- F4 nit: journal says ThrottleInterval 60 / "every minute" in two places; now 10.
- F5 nit: regex matches anywhere on the line (unrealistic for a pidfile; leave or anchor).
- F6 nit: architecture.md:62 stop_tray description lacks the server.pid clause.

Answers: right job, right instrument; settled list respected; docs read right; skill matches CLI. Pending owner checks: Linux click-through with a long interpreter path after F1; Windows double-click on a real PC (deferred). Inspected: full fix diff, all core/cli/web files named, all tests and conftest (no test touches the real ~/.anyscribe), docs, CI logs for 39813117167; live read-only probes on this Mac.
