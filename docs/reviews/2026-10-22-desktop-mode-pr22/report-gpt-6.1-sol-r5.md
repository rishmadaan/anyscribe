**Verdict: NOT YET.**

Reviewed `0382449..c2ae046` only, with surrounding code used to trace callers. The port refusal and headless reporting fixes are real. The new lock cleanup introduces one concurrency defect.

| Item | Verdict | Evidence |
|---|---|---|
| **1. Healthy second-port refusal** | **FIXED** | [desktop.py:217](<repo>/src/anyscribe/core/desktop.py:217) checks the installed port before health, waiting, spawning or browser opening. Evaluating the actual guard confirms 8457 → 9000 refuses, equal ports pass, and no installed port passes. Bare `open` selects the installed port. Reinstall deletes the old manifest before its own open; macOS writes the new plist first. |
| **2. Headless tray failure and reporting** | **FIXED** | [tray_cmd.py:154](<repo>/src/anyscribe/cli/tray_cmd.py:154) preserves the missing-extra `ImportError` message, then handles other import and backend failures through `_cannot_start`, which prints one line and exits 1. The existing nonzero-exit path still starts bare `ui`. [desktop_cmd.py:94](<repo>/src/anyscribe/cli/desktop_cmd.py:94) prints the tray explanation only for a launched, answering dashboard without a live tray, excluding JSON and `--no-launch`. [desktop.py:344](<repo>/src/anyscribe/core/desktop.py:344) preserves “Installed but not running” when both processes are absent. Evaluating those decision statements confirmed all four server/tray combinations. |
| **3. Remove unheld `tray.lock`** | **PARTLY** | [desktop.py:317](<repo>/src/anyscribe/core/desktop.py:317) checks the actual lock, rather than the pidfile, and preserves an already-held lock. However, releasing it before unlinking creates C1 below. |
| **4. Desktop categories** | **FIXED** | [launcher.py:84](<repo>/src/anyscribe/core/launcher.py:84) renders `Categories=AudioVideo;Audio;`. The launcher test asserts that exact line. |
| **5. Journal and installed-port consistency** | **FIXED** | [journal:144](<repo>/docs/building/journal/2026-10-22-desktop-mode.md:144) names the orphan-recovery fix. [desktop.py:307](<repo>/src/anyscribe/core/desktop.py:307) and line 326 use `installed_port() or DEFAULT_PORT` for uninstall and status. |
| **6. Documentation and mirrors** | **FIXED** | The [SSH troubleshooting entry](<repo>/docs/user/troubleshooting.md:595), skill mirror, both command references and generated HTML contain the requested changes. The installer’s headless-Linux skip is present at [install.sh:528](<repo>/install.sh:528). Lock-removal wording will need adjustment if C1 is resolved by retaining the file. |

**C1. should-fix · CONFIRMED by source trace: lock cleanup can allow two trays.**

Where: [desktop.py:319](<repo>/src/anyscribe/core/desktop.py:319), with [tray.py:40](<repo>/src/anyscribe/core/tray.py:40) and [tray_cmd.py:148](<repo>/src/anyscribe/cli/tray_cmd.py:148).

A concrete POSIX interleaving:

1. Uninstall acquires the lock, then closes it.
2. Tray A starts and acquires that same file.
3. Uninstall unlinks the file that A now holds.
4. Tray B starts, creates a replacement `tray.lock`, and acquires it successfully.

The two trays hold locks on different underlying files. Neither sees the other’s lock, and tray startup has no additional duplicate-instance check. Two tray processes can therefore survive.

I traced the actual close/unlink order and demonstrated this schedule in a pure in-memory model. I did not run competing processes.

**Smallest fix:** retain the zero-byte lockfile and update the cleanup promise. Its presence does not mean it is locked. If deletion is mandatory, cleanup and every startup need coordination through a separate stable lock. Merely moving unlink before close does not cover starters that already opened the old file.

The [new cleanup test](<repo>/tests/test_desktop.py:660) checks a lock held before cleanup begins and a sequential unlocked cleanup. It misses acquisition between close and unlink. The other new tests have meaningful failure assertions; mutation results were supplied by the builder and were not independently rerun.

No other new defects confirmed.

Inspected the fix diff, affected functions and callers, new tests and isolation fixtures, documentation mirrors, round-4 reports and post-cap evidence. The reviewed source files match `c2ae046`. New fixtures redirect their files away from the real `~/.anyscribe`.

Not checked: pytest, mutation runs, live lifecycle commands or graphical login, as prohibited by the brief. No files or processes were changed.  
Remaining risk: concurrent tray startup during uninstall can defeat the one-tray guarantee.