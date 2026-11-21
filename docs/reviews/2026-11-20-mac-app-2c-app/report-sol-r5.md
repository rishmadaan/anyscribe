~~~~
**NOT YET.** The ordinary port cases are addressed, but the new parser can still choose the live old tray’s port. The work otherwise fits the approved app scope.

Reviewed **5634e13**, focusing on `1f2e27f..5634e13`, against engine **b22df16**. Later commits contain review records only.

- **D1: PARTLY.** Binary plists and single `--port N`, `--port=N`, or `-p N` options are covered. Other valid arguments bypass the protection below.
- **B2: PARTLY.** Normal quit kills the uninstaller’s group. The independent tray teardown can still reach a reopened engine when its port is misread.

**E1. should-fix | CONFIRMED by reproduction and trace | The tray parser disagrees with the engine’s argument parser.**

Where: old-launcher.js:84 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:84`), feeding engine.js:99 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/engine.js:99`).

The regular expression takes the **first** port option and misses the attached short form. The engine uses Typer/Click, which accepts `-p8470` and uses the **last** repeated option.

Read-only module probes, with an in-memory PID-file reader and supplied command lines, produced:

| Existing tray’s arguments | Tray’s actual port, traced through Click | App’s chosen port |
|---|---:|---:|
| `--port 8470` | 8470 | 8471 |
| `--port 8457 --port 8470` | 8470 | **8470** |
| `-p8470` | 8470 | **8470** |

The saved-port path also incorrectly retains 8470 in the latter two cases.

Concrete scenario: an old tray already runs with either argument form, its server has died, and its launcher records are absent. The app can start on 8470. Removal pauses that engine and signals the old tray. A normal quit kills the uninstaller but leaves the tray’s independent teardown. Reopening can again choose 8470, where that teardown can send `/api/shutdown`. The tray retains its former child reference, so `_shutdown_server()` still calls `_post_shutdown(port)`.

I reproduced the wrong port selection and traced the shutdown path; I did not reproduce the timing across real app instances. This tray predates the app, so it is outside the settled “tray started later” exception.

**Fix:** match the engine’s accepted argument forms and repeated-option behavior, or conservatively avoid every supplied port candidate. Add regressions for both cases, including saved-port reuse. A held real-tray teardown should then verify normal quit/reopen preserves the new engine’s PID and empty crash history. The current fixture at removal.e2e.js:116 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/test/removal.e2e.js:116`) is a Node interval process, so it cannot exercise that teardown.

No other new finding.

**Answers to the builder’s spec corrections**

- `install-skill` is correct. `--force` refreshes bundled files, but overwrites existing contents; customized-skill preservation is not established.
- `turnOff({choice})`, the bash-profile shadowing refusal, and reasons accompanying `ok: true` are sound corrections.
- Carry-over after confirmed login-item removal, followed by system read-back, is sound.
- The original shutdown explanation was incomplete: the fallback is **8457**, and server-PID termination matters too. Pausing protects uninterrupted removal.
- Awaiting the removal step and keeping real-engine tests separate from `npm test` are justified.
- Round 5’s direction is sound, but “never chooses a port the old launcher records or serves” exceeds the implementation’s evidence because of E1.

Both settled limits are documented in the journal and architecture document. I have not reopened them. The approximate force-quit window remains supplied documentation, not independently measured evidence.

**Pending owner checks**

Only Rishabh’s judgment of the combined Mac experience: traffic lights, dragging, wording, and the removal/reload flow. Native process cleanup, shell behavior, Login Items, and file delivery remain technical checks for the lead or builder.

**Verification and limits**

I inspected the packet, delta, diagnosis, prior findings and verdicts, settled declined list, approved mockup sections, bridge amendments, relevant shell review records, implementation and regression bodies, README and building documentation. I read all five named engine files plus the actual tray teardown, skill installer, and installed Typer/Click argument handling.

The source/documentation delta passes `git diff --check`; the worktree remains clean. No files were written or processes started or stopped.

The brief prohibited test runners and app launches. Therefore **113 unit passes, 15 e2e steps, three removal passes, and mutation failures remain supplied evidence**. After adding E1’s regressions, run:

```sh
cd ~/labs/projects/anyscribe-wt/mac-2c-app/desktop
npm test

env -i HOME="$HOME" PATH=/usr/bin:/bin \
  ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python \
  node test/e2e.js

env -i HOME="$HOME" PATH=/usr/bin:/bin \
  ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python \
  node --test test/removal.e2e.js
```

Native macOS `plutil`, `ps -ww`, actual Electron `will-quit`, real tray teardown, LaunchAgent removal, Finder/Dock delivery, and combined window behavior remain unverified here. The exact native plist read is:

```sh
/usr/bin/plutil -extract ProgramArguments json -o - \
  "$HOME/Library/LaunchAgents/com.anyscribe.tray.plist"
```
~~~~
