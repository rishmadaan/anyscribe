~~~~
**NOT YET.** The work fits the approved Mac app scope, and most round 1 fixes are sound. Launcher removal can still stop the app’s engine through two unchecked paths. Command replacement also retains an ownership failure and an unsafe temporary-file write.

Reviewed **98ea8ac**, against engine **b22df16**. Current HEAD adds only review records.

**Round 1 findings**

| ID | Status | Evidence |
|---|---|---|
| C1 | **PARTLY** | The original XML-plist collision is prevented, but PID-based termination and binary plists bypass the protection. See A1 and A2. |
| C2 | **FIXED** | Files remain held until acknowledged; the preload suppresses repeat delivery within a page. The original immediate-unsubscribe race is addressed. |
| C3 | **FIXED** | A recorded installation failure overrides an older `SKILL.md`; status retains the reason. |
| C4 | **PARTLY** | Failure before command replacement preserves ownership. Failure saving the record afterward still invalidates it. See A4. |
| C5 | **FIXED** | Carry-over reads the system state and reports approval-required separately. |
| C6 | **FIXED** | A live old tray alone now counts as installed on macOS. |
| F1 | **FIXED** | `occupant` identifies the replaceable command; status names another copy found first. Combined UI consumption remains a separate check. |
| F2 | **PARTLY** | The decision is documented, but the claimed complete engine protection is false. See A1 and A2. |
| F3 | **FIXED** | Both update and moved-app limitations are recorded in the journal and architecture document, as requested. The functionality remains deferred. |
| F4 | **FIXED** | Both documents explicitly require 2c-app and 2c-ui to merge together. This is a merge condition, not native UI proof. |
| F5 | **FIXED** | Successful startup saves the port; subsequent selection retains it unless excluded. A taken saved port still refuses startup. |
| F6 | **FIXED** | `addToPath` rechecks the login shell and explains when later configuration removes the directory. |

**New and residual findings**

**A1. blocker | CONFIRMED by trace | The port guard does not protect against PID-based termination.**

Where: old-launcher.js:129 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:129`), engine desktop.py:310 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/core/desktop.py:310`), tray.py:269 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/core/tray.py:269`).

Concrete case: the old manifest records 8457. After a crash or reboot, its stale `server.pid` number is reused by the app’s engine, running on 8470. Removal passes the new port guard. The manifest makes `desktop.uninstall()` call `stop_tray(8457)`, which separately reads `server.pid` and terminates that process.

The PID validation checks that the process is alive and runs `anyscribe ui`. The app’s engine satisfies both checks. It does not establish that the process belongs to the old launcher or serves 8457.

**Fix:** protect the app’s engine identity on both HTTP and PID termination paths. At minimum, refuse removal when the old server PID identifies the current app engine. Prefer enforcing the exclusion inside the uninstaller immediately before signalling. Add a regression that asserts the app engine’s identity and active job survive removal, including this stale-PID case.

**A2. blocker | CONFIRMED by trace | A valid binary plist bypasses both port protections.**

Where: old-launcher.js:38 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:38`), engine desktop.py:134 (`~/labs/projects/anyscribe-wt/mac-engine/src/anyscribe/core/desktop.py:134`).

Concrete case: `desktop.json` is absent, the old LaunchAgent is a binary plist recording 8470, and a matching old tray remains alive while its server is down.

The app’s XML regular expression reads no port, so initial selection can choose 8470 and the removal guard resolves the old target to 8457. Python’s `plistlib.loads` reads the binary plist correctly, resolves 8470, and the uninstaller posts shutdown to the app’s engine.

The builder explicitly records this shortcut. It contradicts the binding requirement to resolve ports as the engine does. The architecture claim that the refusal covers every app-reachable case is therefore too strong.

**Fix:** use a resolver supporting the same plist formats as the engine, and distinguish an absent plist from an existing one that cannot be interpreted safely. Test the binary-plist partial installation and assert that uninstall is never invoked against the app’s port.

**A3. should-fix | CONFIRMED by trace | The temporary command path can overwrite an unrelated file.**

Where: terminal.js:276 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/terminal.js:276`).

Every `turnOn` now writes to the fixed path `~/.local/bin/anyscribe.anyscribe-tmp` using ordinary `writeFileSync`, then changes its permissions. There is no exclusive creation or ownership check.

If that path already contains a file, it is truncated. If it is a symlink to, for example, `~/.zprofile`, the write follows it and overwrites the profile. The later cleanup also assumes the temporary path belongs to this attempt. The command’s foreign-file guard does not protect this second path.

**Fix:** create a unique temporary file exclusively in the destination directory, retain its ownership for cleanup, and leave pre-existing entries untouched. Apply the same discipline to the fixed `terminal.json.tmp` path. Regression assertions should compare the exact surviving contents and symlink targets.

**A4. should-fix | CONFIRMED by trace | A record-write failure after refresh leaves the command unowned.**

Where: terminal.js:289 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/terminal.js:289`), terminal.js:297 (`~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/terminal.js:297`).

Start with an owned command, then refresh with a different Python path or version while `~/.local/bin` is writable and `~/.anyscribe/runtime` is not.

The rename installs the new command. Saving its hash fails. The catch block rolls back only the newly linked installation path; it does not restore an overwritten owned command. The old record remains, so the new command reads as foreign. Turning off then asks about a supposed external change or leaves the app command behind.

The builder acknowledges this gap but understates its prerequisite: the runtime folder can be unwritable **before the operation starts**. No permission change between writes is necessary. The added test makes the command directory unwritable, so it fails before reaching this transition.

**Fix:** preserve a recoverable previous command and ownership record until the complete replacement commits, with rollback or restart recovery if saving the record fails. Test failure at that specific write, followed by normal turn-off restoring the original command.

**Answers to the builder’s spec corrections**

1. **`install-skill` is correct.** The engine registration confirms it. `--force` updates the bundled skill files, but does overwrite their existing contents; preservation of customized skills has not been demonstrated.
2. **`turnOff({choice})` is a necessary correction.** The contract amendments now describe both answers.
3. **The bash profile refusal is sound.** Creating `.bash_profile` would otherwise hide an existing `.bash_login` or `.profile`.
4. **Carry-over after confirmed removal is sound**, and C5 now verifies the resulting system state.
5. **The shutdown risk remains real.** The fallback is 8457. A manifest alone can enter `stop_tray`; without a manifest, a valid live tray can do so. Port separation alone does not protect the PID termination path.
6. **`reason` alongside `ok: true` is appropriate.** Successful command installation can coexist with a missing skill or unknown shell state.

The deferred skill refresh and moved-app repair are accurately documented. They must remain explicit phase 3 work, not be presented as already working.

**Pending owner checks**

Only Rishabh’s judgment of the combined Mac experience remains owner-specific: whether the traffic lights, drag area, Terminal messages and launcher-removal flow look and read correctly.

Native removal, Login Items approval, shell behavior, file delivery and recovery testing are technical work for the lead or builder, not repair tasks for Rishabh.

**Checks, limits and inspected material**

I read the review packet, round 1 reports and verdicts, binding fix plan, complete change set, approved mockup sections, settled declined findings, relevant shell review records, changed implementation and regression bodies, bridge contract and building documentation. I traced all five named engine files at `b22df16`, plus the skill installer.

Read-only module probes confirmed retained-file delivery before acknowledgement, repeated/unknown acknowledgement behavior, and saved-port selection. The source/building-documentation delta passes `git diff --check`.

I did **not** independently reproduce the claimed 94 passing tests, 15 e2e steps or mutation results. The brief prohibits test runners, Electron launches and writes. In particular:

- Launcher tests substitute the uninstaller, so they do not establish engine isolation.
- The reload-during-delivery test simulates queue unsubscribe/resubscribe; it is not a real renderer reload at the acknowledgement boundary.
- Saving 8470 in e2e does not distinguish persistence from choosing the default again. A full restart retaining 8471 needs coverage.
- Real macOS launcher removal, approval states, `path_helper`, `ps -ww`, Finder/Dock delivery and combined window layout remain unchecked.

After adding the regressions above, run:

```sh
cd ~/labs/projects/anyscribe-wt/mac-2c-app/desktop
npm test
```

The supplied engine wrapper exists and matches the recorded contents. The exact e2e command is:

```sh
cd ~/labs/projects/anyscribe-wt/mac-2c-app/desktop
env -i HOME="$HOME" PATH=/usr/bin:/bin \
  ANYSCRIBE_DEV_PYTHON=<lead scratch folder>/engine-python \
  node test/e2e.js
```

No files were written, no application or server was launched, and no processes were signalled.
~~~~
