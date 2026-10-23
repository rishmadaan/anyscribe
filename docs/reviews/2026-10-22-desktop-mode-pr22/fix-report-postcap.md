# Fix wave: stranger-test (Linux headless) + round-4 C1 and nits

Branch feat/desktop-mode, from 0382449. Brief: ~/.review-runs/2026-10-22-desktop-mode-pr22/fix-brief-stranger.md.
Status: DONE, all seven items, one commit each, not pushed.

| Item | Commit | What |
|---|---|---|
| 6 port guard | 4eceb1a | `open_dashboard` compares `installed_port()` first, before the external wait and the health shortcut. Test `test_open_other_port_refuses_even_when_that_port_is_healthy`. |
| 1 one-line tray failure | a023ffc | `tray()` catches any non-ImportError from the pystray/PIL import and any exception from `_run_tray` (Icon build + `icon.run`; its finally still tears down) and calls `_cannot_start`: the exact line to stderr, plus tray.log when stderr is not already tray.log (`os.path.samestat`; the Linux autostart entry has no redirect), exit 1. Tests: parametrized import/run case (exact stderr, exact log content, no "Traceback"); `_is_tray_log` true for the log, false for StringIO. |
| 2 install/status honesty | ed780a3 | `desktop.running_without_tray(port)` + `NO_TRAY_REASON`. `status()`: healthy unchanged, reason set when healthy and no tray. CLI install prints the Tray icon line after "Dashboard:" (not with --no-launch, not in JSON). Human `status` now shows the reason next to "Healthy: yes". `test_status_healthy` now fakes a tray pid. |
| 3 tray.lock | 4655cbb | `uninstall()` takes the instance lock after the stop; only if it gets it (no tray alive, including one still starting before its pidfile) it closes and unlinks `tray.LOCKFILE`. |
| 4 categories | dca8675 | `Categories=AudioVideo;Audio;`; launcher test asserts the line. |
| 7 nits | 0459ee3 | Journal line 144 reworded; `uninstall()`/`status()` use `installed_port() or tray.DEFAULT_PORT`. Two tests (no manifest, plist 9100). |
| 5 docs | 4a0b060 | troubleshooting.md new SSH/no-desktop entry (installer skip claim verified in install.sh:528); skill troubleshooting mirror; commands.md uninstall row adds tray.lock; status row + JSON reason line in both commands.md files updated (they said `reason` is null when healthy, now false). landing/docs regenerated, check-docs exit 0. |

## Mutation evidence (each guard removed, test run, restored)

- 6 (guard moved back inside the not-healthy branch): `E Failed: DID NOT RAISE <class 'anyscribe.core.desktop.PortMismatch'>` / `FAILED ...test_open_other_port_refuses_even_when_that_port_is_healthy`
- 1 (both wraps removed): both cases `E assert (1 == 1 and '' == 'The tray cou...ical login.\n'` with `<Result RuntimeError('Bad display name ""\nsecond line')>`; note the exit code is 1 either way under CliRunner, the stderr assertion is what fails.
- 2a (reason branch dropped): `E AssertionError: assert None == 'Running without its tray icon (no graphical session or tray support). The dashboard works; ...'`
- 2b (CLI line disabled): `FAILED ...test_cli_install_says_when_the_tray_is_not_running[None]`
- 3 (unlink made unconditional): `E AssertionError: assert False` where False = `tray.lock`.exists() (the held-lock case); with the unlink removed: `E AssertionError: assert not True`.
- 7 (old `m["port"] if m else` rule restored): `E assert 8457 == 9100` and `E assert [8457] == [9100]`.

## Gates

Final: `pytest -q` 662 passed, 3 skipped; `ruff check src tests scripts` clean; `build-docs.py` + `check-docs.py` clean. Each commit was gated.

## Deviations and concerns

- Item 7 wording: the brief said "the addendum below", but the addendum (line 126) sits above the correction (line 144). Wrote "described in the addendum above".
- Item 1: a pystray ImportError raised because every backend failed ("this platform is not supported") is still shown as the missing-extra message (exit 1, fallback still runs). It only happens when python-xlib/gi are themselves missing; the headless-display case is a DisplayNameError, which is covered. Not changed, to keep the settled missing-extra path.
- Item 2 wording on macOS: a dashboard hand-started (`anyscribe ui`) after the tray was quit would also read "no graphical session or tray support". Brief wording kept.
- `ruff format --check` reports 5 files that were already unformatted at 0382449 (main.py, migrate_cmd.py, test_desktop.py, test_migrate_cmd.py, test_ui_port.py); format is not a gate, left as is.
- Not checked: a real headless Linux run of the new code (no Linux box used); nothing run against the real ~/.anyscribe.
