**NOT YET.** The requested screens are present and largely within scope, but recovery across the real app’s reload is incomplete. A supported removal-error result can also crash rendering. The recorded 173 passing checks do not cover these failures.

**Findings**

**C1. blocker, CONFIRMED: the recovery message disappears during the real engine restart.**  
Where: [EngineBanner.tsx:24](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/EngineBanner.tsx:24), [main.js:345](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/main.js:345).

Scenario: a transcription is being watched when the engine stops. The banner remembers its name only in the current page’s memory. When the engine reports `running`, the real app immediately loads `/` again. The new page has neither the remembered job nor the outage, so “Running again”, the unfinished-job warning and Open History disappear.

I reproduced the banner’s state transitions in memory using its actual handler: before document replacement, the remembered job was `"Weekly sync"`; after a fresh page received `running`, it was `null`. The banner check emits status changes without reproducing the app’s reload.

Fix: preserve the outage and watched job across document replacement, consume them after recovery, and clear them on Dismiss. Test the real reload path.

**C2. blocker, CONFIRMED: a persisted removal error without pieces crashes the dashboard.**  
Where: [MacCards.tsx:94](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/MacCards.tsx:94), [App.tsx:85](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/App.tsx:85), [old-launcher.js:218](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:218).

Scenario: removal throws, the app catches it and saves `{ok:false, pieces:null, reason:…}`, then the engine returns and the dashboard reloads. `claimRemoval()` accepts that saved result. `RemovalAfterReload` passes it directly to `RemovalResult`, which assumes `pieces` exists.

Rendering the actual component with this supported result produced:

```text
Cannot read properties of null (reading 'launcher')
```

Fix: handle no-pieces results inside `RemovalResult`, including persisted results. Show the returned reason with Retry and Close. Allow `pieces: null` in the TypeScript type.

**C3. should-fix, CONFIRMED: queued Dock files are forgotten across an engine reload.**  
Where: [Layout.tsx:23](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/Layout.tsx:23), [preload.js:12](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/preload.js:12).

Scenario: job A runs, then file B arrives through the Dock and waits in “Up next”. The preload acknowledges B after the callback merely adds its path to React state. If the engine crashes before B starts, the dashboard reload destroys that queue, while the app has already acknowledged delivery and will not resend B.

The original file remains intact, but the requested transcription silently disappears.

Fix: persist pending paths before acknowledging delivery and restore them after reload, or retain app ownership until submission is acknowledged. Test the identity of B after recovery, not just the queue length.

**C4. should-fix, CONFIRMED: the restore choice becomes inaccessible after reopening Settings.**  
Where: [ThisMac.tsx:150](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/ThisMac.tsx:150), [ThisMac.tsx:202](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/ThisMac.tsx:202), [terminal.js:341](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/terminal.js:341).

Scenario: Switch replaced an existing command, then another program or the person changes the app’s command. On reopening Settings, the real bridge returns `command:null`, so the switch already appears Off. Clicking it takes the Turn on/Switch path. There is no action that reaches `turnOff()` and its Keep current command / Restore previous command question.

I reproduced the real Terminal module against an in-memory filesystem: status returned `command:null`, while a direct `turnOff()` returned `needsChoice:"keep-current-or-restore"`. The existing check starts with stale “On” status, which hides this problem.

Fix: expose outstanding restoration state through the bridge and provide an explicit way to resolve it after a fresh status read.

**C5. should-fix, CONFIRMED: unknown Terminal availability is presented as success.**  
Where: [MacCards.tsx:219](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/MacCards.tsx:219), [MacCards.tsx:343](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/components/MacCards.tsx:343), [terminal.js:204](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/terminal.js:204).

Scenario: writing the command succeeds, but asking the login shell fails. The real bridge legitimately returns `state:"on"`, `uses:null` and an explanatory reason. The card still displays a green “anyscribe is ready in Terminal”. With a missing skill, it instead claims “Terminal is ready” in the warning heading and Settings row.

I reproduced the ready heading with `uses:null`. The check at `check_ui.py:860` explicitly expects that unsupported success claim.

Fix: gate readiness on confirmed command resolution. For the unknown state, use:

> **Command added; Terminal availability could not be checked.**

Show the bridge’s reason underneath.

**C6. should-fix, CONFIRMED: the once-only question guarantee is incomplete.**  
Where: [App.tsx:62](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/App.tsx:62), [App.tsx:91](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/App.tsx:91), [main.js:451](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/main.js:451).

Two cases:

- Escape or a backdrop click updates only React state, so the question returns next launch. The builder deliberately implemented and tested this exception, but the supplied spec says each question is asked once.
- The real `firstLaunch.mark()` can resolve with `{ok:false, reason}` when saving fails. Callers ignore that result and proceed as though persistence succeeded. The stub always succeeds and returns no result, so this contract difference is untested.

Fix: resolve the dismissal policy explicitly against the once-only requirement. Handle the real mark result and explain persistence failures instead of silently claiming completion. The consent question must remain separate from permission to perform removal or Terminal changes.

**C7. should-fix, PLAUSIBLE: removal can lose its post-reload result through a settlement race.**  
Where: [desktop.ts:164](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/desktop.ts:164), [main.js:354](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/main.js:354), [stub.js:88](~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/stub.js:88).

Scenario: the real removal promise settles after navigation starts but before the old document is destroyed. Its `finally` deletes the recovery note. The replacement page then cannot claim `lastRemoval`.

The stub prevents this ordering by returning a promise that never settles on its reload path. I reproduced the helper’s loss when settlement precedes document replacement: `claimRemoval()` returned `null`.

Fix: retain the recovery token until the result is explicitly consumed or dismissed. A real Electron integration run with a delayed replacement-page response would settle whether this ordering occurs in practice.

**Answers to the builder’s five “spec is wrong” points**

1. **Dragged filename and size:** agree for the renderer path implemented here. The recorded Chromium probe supports the generic overlay. It does not establish that every possible native Electron approach is unavailable. Avoid adding native machinery solely for this detail.
2. **Copy details including the log:** agree that the current dashboard bridge cannot supply the log. The replacement wording is truthful, but the approved diagnostic feature remains reduced until that change is accepted.
3. **Knowing the shell profile beforehand:** agree. Status does not expose the shell or target profile. Naming both supported profiles is reasonable. After a refusal, replace the stale promise with: “anyscribe could not add the line automatically. Add it by hand as described below.”
4. **The watched transcription keeps spinning after restart:** partly correct for a page that survives. It misses the real app’s document reload, which loses the watched job and warning entirely. C1 is the required app recovery fix; changing browser behavior is not necessary to address it.
5. **Restart when the job list is unknown:** reasonable. An enabled button that delegates the decision to the real bridge is preferable to inventing certainty. Keep showing its refusal reason. This is distinct from the confirmed busy-list case, where the button is disabled.

**Pending owner checks**

No owner-only technical action is needed to resolve these findings. After the builder supplies a working Mac integration, Rishabh’s remaining check is whether the native window and approved screens look and read as intended. The reduced drag-overlay and log-copy behavior should be presented as explicit design deviations.

**Inspection and limits**

I inspected the packet, declined findings, specified mockup sections and build promises, the source and documentation diff, all supplied check scripts and recorded outputs, and the five named real bridge files. The app checkout is at `70e911f`. UI source matches the requested target; later commits change review files only. `git diff --check` passed.

I ran only read-only inspections and in-memory reproductions. Nothing was edited, built, started or stopped. I did not independently rerun the recorded 173 checks, lint, build, mutation suite or Mac interactions. Native picker behavior, traffic-light clearance, Finder dragging, actual reload timing and the local-download wizard path remain unverified.

After adding the missing regression cases, the relevant existing checker command is:

```bash
/usr/bin/python3 ~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py --no-shots --only banner,open_file,settings,first_launch,wizard
```

That remains a stub-based check. It must be supplemented with the combined app and engine running on a Mac.