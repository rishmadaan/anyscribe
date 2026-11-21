(Home-folder links in this copy are written as ~ paths; the byte-exact original is in the run folder.)

~~~~~~
**NOT YET.** The fix restores confirmation after Back and return, but a running reply held while another screen is showing still permits closing without warning.

Reviewed `fix/wizard-opening-read` at `4b7232eaf6f3de65d97901c0b3790b28c01b0da1`. Findings below are established by source trace and inspected evidence. Runtime execution was prohibited.

| Round 1 finding | Status | Evidence |
|---|---|---|
| C1 | **PARTLY** | `heardRef` preserves eligible replies across visits. L1E passes, but closing before returning remains unprotected: R2C1 below. |
| C2 | **FIXED** | Opening-effect cleanup aborts the request through the API client. Saved SM1/SM2 results show older requests aborted; removing cleanup makes both fail. Final-code L1X also passes. |
| C3 | **FIXED** | `git diff --check 5fb5d1e..4b7232e` passes. |
| F1 | **PARTLY** | L1F proves adoption after returning from Provider, but never tests closing while the reply is held on Provider. |
| F2 | **FIXED** | The recorded real walk uses shipping bundle `index-CDPOZTVX.js`. Its screenshots show the running Tiny download and confirmation. Only review records changed after that walk’s commit. |
| F3 | **FIXED** | BACKLOG and journal describe the “heard” rule; the cloud-provider observation is recorded. Literal `#PR` remains as explicitly instructed, pending PR creation. |

**R2C1. should-fix | CONFIRMED: holding running knowledge outside Local transcription does not protect closing.**

Where: [OnboardingWizard.tsx:197](~/labs/projects/anyscribe-wt/wizard-l1/ui/src/components/OnboardingWizard.tsx:197), close decision at [line 224](~/labs/projects/anyscribe-wt/wizard-l1/ui/src/components/OnboardingWizard.tsx:224), and watch-state cleanup at [line 788](~/labs/projects/anyscribe-wt/wizard-l1/ui/src/components/OnboardingWizard.tsx:788).

Concrete sequence, within the opening request’s ten-second limit:

1. The opening status request is delayed.
2. Enter Local transcription. Its own reads fail.
3. Press Back to Provider.
4. The opening reply arrives with `setup_running: true`.
5. **Without returning to Local transcription**, press Escape, click outside, or press Skip.

The handler accepts and stores the reply in `adopt`, because `localShownRef` is true and `heardRef` is false. However, leaving the local step has reported `watched=false`. No mounted step consumes the held reply, and `askOrClose` checks only `watched`.

Consequently, Escape and backdrop close immediately. Skip closes immediately **and writes `scribe_onboarding_dismissed=1`**. Nothing newer contradicted the running reply.

The same gap is reachable on every screen the brief singled out:

| Screen | Reachable sequence before the delayed reply lands |
|---|---|
| Provider | Local step with failed reads, then Back. |
| API key | Cloud path, optional local step with failed reads, then Back. |
| Workspace | Cloud path, leave optional local disabled, press “Skip, next” before any successful local read. |
| All set | The preceding Workspace sequence, then Next. Escape and backdrop remain available; this screen has no Skip button. |

These screens remain unchanged when the reply lands, which correctly avoids rerouting. Their closing behavior nevertheless violates the required warning invariant.

The new [L1F case](~/.review-runs/2026-11-21-wizard-opening-read/instruments/l1-cases.js:222) checks that Provider remains visible, immediately returns to Local transcription, and only then exercises closing. Its passing result therefore does not cover this interval.

**Fix:** make an eligible, unsuperseded held running reply participate in the close-confirmation decision immediately, independently of the visible screen. Preserve the current route and form, retain one owner of watch state, and retire that knowledge when a newer accepted status supersedes it. Do not treat every non-null `adopt` as current indefinitely.

Add separate closing checks on Provider, API key, Workspace and All set **before returning**. Assert confirmation, unchanged route/provider/model, and an unset dismissal flag. Retain the existing newer-read and same-batch rejection cases.

This is the remaining C1/F1 defect exposed by the new held-reply state, not an unrelated regression. The implementation follows the fix plan’s holding rule; that plan does not fully satisfy the brief’s stronger closing invariant. L1 should not yet be recorded as complete.

The other ordering checks support the repair:

- Accepted step reads set `heardRef` synchronously, preserving rejection across remounts and later starts.
- Removing the start’s separate `onHeard()` remains justified: a usable selection requires a prior accepted read, or adoption that keeps starting disabled until such a read occurs.
- The step’s `status === null` guard remains necessary. Saved L1S passes on final code and fails when that guard is removed.
- Closing remains disabled only during Finish saving. `Close setup` still calls `dismiss(false)`.
- The source diff preserves S11–S14, bounded polling, start-generation handling, Back/Skip controls and `offerTerminal`. The settled never-shown API-key reroute was not reopened.

**Pending owner checks:** none needed to establish or resolve this defect. Fixing it, adding coverage and checking exact-SHA CI are engineering work. A PyPI release remains a separate owner decision.

I inspected the named packet, both round 1 reports and verdicts, binding fix plan, declined list, prior L1 report and design specification; the full wizard, Modal, API client/types and local server route; source and record diffs; harness, cases and mutation instruments; final result summaries and relevant snapshots/request traces; and the shipping-bundle real-walk screenshots and logs.

HEAD matches the target, inspected files have no working-tree delta from it, and whitespace validation passes. The final saved result contains 37 passing cases; that does not cover R2C1. F2’s post-“Keep setting up” screenshot is visibly incomplete, as disclosed; that interaction rests on the builder’s recorded DOM observations.

I did not independently run browser cases, rebuild, run tests, verify native platforms or inspect remote CI. The brief prohibited those operations. Relevant unrun checks are:

```sh
npm --prefix ~/labs/projects/anyscribe-wt/wizard-l1/ui run lint
npm --prefix ~/labs/projects/anyscribe-wt/wizard-l1/ui run build
git -C ~/labs/projects/anyscribe-wt/wizard-l1 diff --exit-code -- src/anyscribe/web/static
gh run list --repo rishmadaan/anyscribe --commit 4b7232eaf6f3de65d97901c0b3790b28c01b0da1
```

Existing browser entry points `window.__run("L1F")`, `window.__run("L1S")`, `window.__run("SM1")` and `window.__run("SM2")` were inspected, not executed. No existing case exercises R2C1’s closing actions while the reply is held elsewhere.

No files or processes were changed.
~~~~~~
