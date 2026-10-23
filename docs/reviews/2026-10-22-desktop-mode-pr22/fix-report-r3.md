# Review fix r3 report (feat/desktop-mode, base 240766b)

Status: DONE, all four items.

## Commits
1. Linux identity: 6f31fcf `fix(tray): read the whole command line on Linux (/proc) and BSD (ps -ww)`
2. Windows test: 672d060 `test(desktop): skip the SIGUSR1 fallback case on Windows instead of masking it`
3. Port check ungated: e6772bc `fix(desktop): open --port refuses another port whenever desktop mode is installed`
4. Doc nits: 0382449 `docs(building): ThrottleInterval correction note; stop_tray also stops server.pid`

## Gates (after 0382449)
- `pytest -q`: 652 passed, 3 skipped
- `ruff check src tests scripts`: All checks passed!
- `build-docs.py && check-docs.py`: exit 0; landing/docs/commands.html committed in e6772bc

## Item 1
- `pid_is_anyscribe`: Linux reads `/proc/<pid>/cmdline` (NUL -> space, OSError -> False); other POSIX `ps -ww -o command= -p`; Windows unchanged.
- New tests (tests/test_tray.py): `test_linux_reads_the_untruncated_proc_cmdline` (sys.platform=linux, Path.read_bytes patched, 147-byte NUL line ending `/x/bin/scribe\0tray\0--port\08457`, asserts True for tray, False for ui, and that exactly `/proc/4242/cmdline` was read), `test_linux_missing_proc_entry_is_not_anyscribe`, `test_long_command_line_is_read_in_full` (real child, >200-char `-c` script). `test_alias_tray_is_recognised_and_keeps_its_login_item_job` unchanged, passes on macOS with `-ww`.
- Mutation A (Linux branch disabled, `if False:`):
  ```
  tests/test_tray.py:681: AssertionError
  FAILED tests/test_tray.py::test_linux_reads_the_untruncated_proc_cmdline - As...
  1 failed, 3 passed, 71 deselected in 0.16s
  ```
- Mutation B (drop `-ww`): could NOT be made to fail on macOS. Measured: BSD ps does not truncate when stdout is not a terminal, and ignores COLUMNS:
  `ps -o command=` -> 397 chars; `COLUMNS=80 ps -o command=` -> 397; `COLUMNS=80 ps -ww` -> 397 (397-char line).
  With `-ww` removed: `2 passed, 73 deselected` (long_command, alias_tray). `-ww` is belt-and-braces on macOS/BSD; the real protection against the CI failure is the /proc branch, which Linux CI exercises with real children (the alias test and the new >200-char test) and which mutation A shows is load-bearing. Linux CI must be re-run to confirm.

## Item 2
- Parametrized `[pytest.param("posix", marks=skipif(win32)), "nt"]`, expected list back to `signal.SIGUSR1`, getattr and comment removed. Both params pass on macOS.
- Grep: only other evaluation of `signal.SIGUSR1` in tests is test_desktop.py:317 (already skipif win32) and test_tray.py:1004 (skipif os.name == "nt"); test_tray.py:891 is a docstring.

## Item 3
- `open_dashboard`: `installed = installed_port()` unconditionally, PortMismatch raised before read_pidfile/signal/stop/spawn (still after the "foreign program on the port" check, inside the not-healthy branch; a healthy anyscribe already on the asked port is just opened).
- `open_cmd`: no `--port` -> `desktop.installed_port() or tray.DEFAULT_PORT` (manifest, else login-item plist).
- `install()` unaffected: it unlinks the old manifest before its own open; macOS writes the new plist before `open_dashboard(port, expect_external=True)`, so `installed_port()` returns the new port; Windows/Linux have no plist (`_login_item_port` -> None). Full suite incl. install tests green.
- Tests: `test_open_other_port_refuses_even_with_no_tray` (no pidfile, manifest 8457, open 9000 -> PortMismatch, no spawn, no browser), plus `test_open_without_port_uses_the_login_item_port` (no manifest, plist on 9100, bare `desktop open` -> open_dashboard(9100)).
- Mutation C (re-gate: `installed_port() if tray.read_pidfile() is not None else None`):
  ```
  E   Failed: started a tray
  tests/test_desktop.py:382: Failed
  FAILED tests/test_desktop.py::test_open_other_port_refuses_even_with_no_tray
  1 failed, 51 deselected in 0.11s
  ```
- Mutation D (open_cmd back to manifest-only default):
  ```
  tests/test_desktop.py:394: AssertionError
  FAILED tests/test_desktop.py::test_open_without_port_uses_the_login_item_port
  1 failed, 51 deselected in 0.12s
  ```
- Docs: docs/user/commands.md:933 "is installed on one port"; skill references/commands.md:418 "is installed on port A".

## Item 4
- Journal: one dated line appended at the end (after the addendum) correcting ThrottleInterval 60 -> 10 and "every minute" -> "every 10 s"; no earlier text edited.
- architecture.md:62: stop_tray "SIGTERMs the pidfile pid and the recorded server pid (`server.pid`), and removes both files."

## Concerns
- `-ww` mutation is not demonstrable on macOS (above); relies on Linux CI for the end-to-end proof of item 1.
- `ruff format --check` reports 5 files (incl. tests/test_desktop.py) that were already unformatted at 240766b; CI runs `ruff check` only, so left alone.
- Nothing pushed; docs/reviews/ untouched; no real tray/launchctl/signals used.
