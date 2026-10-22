# Fit review, round 2 (Claude Fable 5.1, Agent tool), target 273be39

Saved by the lead from the reviewer's final message (verbatim; the full text is in this session's transcript and summarised below for the record).

VERDICT: NOT YET.

Earlier findings: F1/C6, F2, F3, F4, F6, F7, C1, C2, C4, C5, C7, C8, C9, C10 FIXED (file:line evidence given for each; live Mac state consistent: healthy, tray 40242 launchd-owned runs=1, server 40243 its child, plist ThrottleInterval 10 / ProcessType Interactive, health app=anyscribe, ffmpeg true); F5 DECLINED-OK; C3 FIXED for two-trays, PARTLY for the server-start race (see F9).

New findings:
- F8 should-fix CONFIRMED (CI log): tests/test_desktop.py:320-339 `test_open_falls_back_to_stop_and_start_when_restart_fails[posix]` evaluates `signal.SIGUSR1` on Windows → AttributeError; fix: skip the posix param on win32 (or getattr). Everything else the Windows job proves passed (real lock, real `anyscribe tray` with the lock held, real sleeper not signalled, pythonw stream probe, shortcut, _pid_alive).
- F9 should-fix CONFIRMED by trace: on spawn-path platforms a double-click spawns tray A and tray B; B loses the lock and exits 0; click 2's `_await_health(B)` says "exited" before A's server is up → the headless fallback spawns a bare `anyscribe ui --port 8457 --no-open` → one tray plus one server nobody owns (ui rolls one of them to 8458). Fix: a spawned tray exiting 0 means wait for the winner; keep the `ui` fallback for non-zero exits.
- F10 should-fix PLAUSIBLE (traced): `desktop open --port 9000` with the installed tray on 8457 → orphan branch → SIGUSR1 no-op → 15 s → `stop_tray(9000)` kills the 8457 tray and its server → spawn on 9000 outside launchd. Fix: in `open_cmd`, if a manifest exists and `port != m["port"]`, refuse with exit 1: "anyscribe is installed on port {m['port']}. Run `anyscribe desktop open` (no --port) to open it, or `anyscribe desktop install --port {port}` to move it."
- F11 should-fix (skill docs) CONFIRMED: skill references/troubleshooting.md:355-359, references/commands.md:363, docs/user/troubleshooting.md:521-525 still explain "already running" via the pidfile; it is the OS lock on tray.lock now (exact replacement wording supplied).
- F12 nit CONFIRMED by probe: `scribe tray` / `ascli tray` command lines contain no "anyscribe" → invisible to read_pidfile; fix: match the aliases (regex) or document.
- F13 nit: docs/user/configuration.md:28 and :420 inventory lacks tray.lock, server.pid, desktop.json, desktop/ (row wording supplied).
- F14 nit (test gap): `test_tray_restart_lock_is_idempotent` cannot fail if the `starting` guard is removed; add a sibling with `poll()` None and health False.
- F15 nit (prose): CHANGELOG.md:21-26 and docs/user/troubleshooting.md:597-601 now say "nothing is downloaded" twice and address the Windows user with "click-through remains unverified"; replacement troubleshooting paragraph supplied.

Answers: right job, right instrument; settled list respected; lead's "two simultaneous opens, one tray" evidence covers the kickstart path only (not the spawn path). Pending owner checks: double-click on a Windows/Linux machine after F9; whether `open --port N` should refuse (recommended) or move. Could not run: pytest, any lifecycle command (forbidden); F9/F10 are traces with exact commands for the lead. Inspected: both round-1 reports, fix briefs and builder reports, the fix-wave diff (29 files), all core/cli/web files named, tests, user docs, skill files, live read-only state and pure-function probes.
