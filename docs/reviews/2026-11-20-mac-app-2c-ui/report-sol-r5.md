**NOT YET.** K3 introduces a false start promise when a failed dropped file remains ahead of “Up next.” No new data-loss defect found.

- **K1 FIXED:** Only the opening cleanup summary is stripped. Uninstall messages, including embedded full stops, login notes and engine notes survive. Copy details retains the original reason.
- **K2 PARTLY:** The replacement words match the bridge, but the partial-cleanup fixture combines an approval note with an impossible carry-over flag.
- **K3 PARTLY:** Correct for the tested typed-link scenario; overpromises when a failed queued file remains at the head.
- **K4 FIXED:** Bare engine reasons receive a full stop before “It is running again now.” Existing terminal punctuation is preserved.

**E1. should-fix. CONFIRMED.**  
Where: [TranscribePage.tsx:440](~/labs/projects/anyscribe-wt/mac-2c-ui/ui/src/pages/TranscribePage.tsx:440), using the helper at line 128.

Drop A and B; A is refused, leaving `[A, B]`. While the engine is down, the error view now says: “Up next: b.m4a. It starts once anyscribe’s engine is running again.”

Recovery reloads the page and retries **A first**. If A is refused again, the error pause blocks B indefinitely until another action. Engine recovery alone therefore does not start B.

I reproduced this using the source’s extracted waiting-list expression and start gate. The new check at [check_ui.py:1546](~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py:1546) uses a failed typed link, so B is the queue head, and closes before recovery.

Fix: when the failed file remains at the queue head, use: **“Still queued behind the failed file, which will be tried again after the engine restarts.”** Extend the check through recovery with `[A, B]` and A refusing again.

**E2. nit. CONFIRMED.**  
Where: [check_ui.py:1477](~/labs/projects/anyscribe-wt/mac-2c-ui/docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py:1477).

`PART` now includes the macOS approval note while setting `startAtLoginCarriedOver: True`. The real bridge sets that flag only for `enabled`; `requires-approval` produces this note with **false** ([old-launcher.js:187](~/labs/projects/anyscribe-wt/mac-2c-app/desktop/src/old-launcher.js:187)).

I executed the bridge’s extracted `remove()` body with simulated inputs and reproduced the same reason with `false`. Set this fixture’s flag to `False`. The mismatch does not invalidate the stripping assertion, but the fixture is not a producible bridge result.

**Verification and limits**

Inspected both deltas, the round-4 report, the specified proof section, both declined lists, both fix plans, production context, bridge reason construction, changed checks, stub, mutation script and recorded output. Production source matches `4abb653`; the bridge is at `70e911f`.

Read-only Node checks passed **520 generated reason cases**. No unintended supplementary reason disappeared or duplicated.

The mutation output records all four targeted failures and a restored **32 passed, 0 failed**. These demonstrate detection of the four reversions, not the retained-head recovery scenario above.

I did not run builds, browsers, servers or mutation scripts. The claimed **249-check** run and new screenshots were not independently verified: the committed full-run log contains **247 passed**, and the proof places the newer artifacts in an unspecified scratch folder. No files were changed.