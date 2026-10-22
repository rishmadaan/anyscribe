# Fix brief: Linux headless findings from the stranger test (after round 4; small)

Repo <repo>, branch feat/desktop-mode, from 0382449.
Evidence: docs/reviews/2026-10-22-desktop-mode-pr22/stranger-test-linux-r1.md.

1. **Tray cannot start: one honest line, not a traceback.** `cli/tray_cmd.py::tray()`:
   wrap the pystray/PIL import AND the backend start (`icon.run`) so any exception that is
   not the missing-extra ImportError prints exactly one line to stderr and the log:
   `The tray could not start ({type(e).__name__}: {first line of str(e)}). The dashboard
   runs without it; the tray will try again at your next graphical login.` and exits 1
   (so `desktop open`'s existing non-zero-exit fallback starts the bare dashboard). No
   Rich traceback in tray.log. Test: monkeypatch the pystray import to raise
   `RuntimeError("Bad display name \"\"")` → exit 1, that one line in stderr, no "Traceback"
   in output. Mutation: remove the wrap → the test fails.
2. **`desktop install` and `status` say so.** `core/desktop.py`: after `install()` has
   waited for health, if the dashboard answers but `tray.read_pidfile()` is None (fallback
   mode), the CLI prints after the usual lines: `Tray icon: not running (no graphical
   session or tray support here). The dashboard works without it; the tray will start at
   your next graphical login.` `status()`: when `installed` and `server_running` and not
   `tray_running`, `healthy` stays true (the dashboard answers) and `reason` becomes
   `Running without its tray icon (no graphical session or tray support). The dashboard
   works; the tray will start at your next graphical login.` Tests for both (JSON reason
   asserted exactly). Mutation: drop the reason branch → test fails.
3. **`uninstall` removes `tray.lock`** (`APP_HOME / "tray.lock"`) after stopping; a lock
   held by a still-running tray cannot be unlinked meaningfully on Windows, so only remove
   it when no tray is alive; test asserts the file is gone.
4. **`.desktop` categories**: `Categories=AudioVideo;Audio;` (one main category plus an
   additional one) in `core/launcher.py::render_desktop_entry`; update its test.
5. **Docs**: `docs/user/troubleshooting.md` new entry "I installed over SSH / on a machine
   with no desktop and the tray isn't there": what happens (dashboard runs, tray starts at
   the next graphical login), how to check (`anyscribe desktop status`), and that the
   one-line installer already skips desktop mode on a headless box. Mirror one sentence in
   `src/anyscribe/skill/references/troubleshooting.md`. `docs/user/commands.md` uninstall
   list adds `tray.lock`. Regenerate `landing/docs`.
Gates: `.venv/bin/python -m pytest -q && .venv/bin/ruff check src tests scripts`;
`scripts/build-docs.py && scripts/check-docs.py`. One commit per item, trailer
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Do not run `anyscribe tray`,
`desktop install/uninstall/open`, `launchctl` or signals against the real `~/.anyscribe`.
Report to `.superpowers/sdd/2026-10-22-desktop-mode/review-fix-stranger-report.md`.

6. **Port guard before the health shortcut (round-4 correctness C1).** In
   `core/desktop.py::open_dashboard`, the `installed_port()` comparison currently sits
   inside `if not health_is_anyscribe(port)`, so `desktop open --port 9000` with a healthy
   hand-started `anyscribe ui --port 9000` opens it instead of refusing as the docs promise.
   Move the comparison before the health check (first thing in the function). Test
   `test_open_other_port_refuses_even_when_that_port_is_healthy` (manifest 8457, health on
   9000 True → PortMismatch, no browser, no lifecycle action). Mutation: move it back → fails.

7. **Round-4 fit nits.** `docs/building/journal/2026-10-22-desktop-mode.md` (~144): replace
   "since the r1b fix" with "since the orphan-recovery fix described in the addendum below".
   `core/desktop.py::uninstall()` and `status()`: take the port from `installed_port() or
   tray.DEFAULT_PORT` (same rule as `open`); one test each (manifest absent, plist says 9100
   → status reports port 9100).
