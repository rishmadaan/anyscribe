# Fix plan, round 1 (the lead's choices; they bind the fixer)

Fix every UPHELD finding in review-log.md except C3, which the lead already fixed. The reports are verbatim in findings.md.

## C1 and F1 (should-fix, both reviewers): drop a reply only when something newer spoke, not because the step was left

Close it in code. Do not record it as residue. Replace "left: drop" with "heard: drop":

1. **The shell keeps `heardRef`.** It turns true, and stays true for the rest of this wizard, once the local step has accepted a status read of its own or sent a start request, on any visit. The step reports this through one new stable callback, for example `onHeard()`. Call it in three places:
   - where the step accepts a status (the tick's accepted branch, and `checkFfmpeg`'s `setStatus`);
   - in `handleStartSetup`, before the request is sent.

   It never touches `watched` or `confirmClose`. The step stays the one writer of those (spec rule 3).
2. **The opening reply, when it says `setup_running`:**
   - **heard:** drop it.
   - **The local step has never been shown:** as today. Write the form, hand over the reply, route to `offline_opt_in`.
   - **Otherwise** (showing now, or shown and left): `setAdopt(reply)` only, with neither the form nor the route touched. A mounted step takes it now. If the person is elsewhere, the reply is held, and their next visit to the step takes it at mount.

   The three-state ref can shrink to "ever shown" if nothing else needs it.
3. **The step keeps its `status === null` guard.** It covers a different ordering from `heardRef`: the hand-off and the step's own newer read being accepted in the same render batch. Mutation-test it. If no harness ordering can tell it apart (try both replies resolving at the same moment), trace whether it is equivalent and report it. Do not remove it: the lead decides.
4. **The "no start sent" half stays out of the step.** `heardRef` now covers starts on every visit. Show by trace why a start cannot come between a hand-off and its take within one mount.
5. **Keep everything else in spec rules 3 and 4.** Back and `goWorkspace` still clear the reply. A held reply that the step later takes turns local on and picks its model, exactly as the step's own running read does.

**Cases to add**, each failing on 8d53ebc and passing after the fix. Assert identities: Escape, backdrop and Skip each ask, the dismissed flag is null, Back is disabled, the selected card.
- **C1's sequence:** delayed opening read; the person reaches the local step with failing reads; Back, then return; the second visit's reads also fail; the reply lands. Closing must ask first.
- **The reply lands while the person is on Provider after a Back;** they return. The step watches from mount.
- **Heard on the first visit (an accepted "not running" read), Back, return with failing reads, reply lands:** dropped. Not watching, pick unchanged.
- **A refused start on the first visit, Back, return, reply lands:** dropped.

Update spec.md: add one line under rule 1 recording this round 1 lead decision.

## F2 (should-fix): a real walk on the bundle that ships

After the fix and the final rebuild, rerun the hook-free walk on a real server with a throwaway HOME, using the smallest model:
- A reload mid-setup opens on the running download.
- Escape asks first.
- "Keep setting up" keeps it.

Name the bundle file in proof.md. Clean up as before, and report `df -h ~`.

## C2 (nit): the opening read gets a cleanup

Give the opening effect an AbortController passed to `limited`, and a live flag that its `.then` checks. The cleanup aborts the request and clears the flag. Under StrictMode's replay, the first request is then cancelled, and a wizard closed before the reply lands writes nothing. Correct proof.md's statement about StrictMode: the committed bundle does wrap the root in StrictMode, and production runs each effect once. Prove it with a harness case or a trace, and say which.

## F3 (nit) and the records

- **BACKLOG.md, the L1 line:** replace "reconcile it through the step's start-ordering guard. Done in the L1 follow-up (branch ...)..." with "Done in #PR: a late reply is dropped only once the local step has heard something newer (an accepted read or a start); otherwise the step takes it." Keep the literal `#PR`; the lead puts the number in when the PR opens.
- **BACKLOG.md:** add the fit report's observation as an unticked wave 2 line, under the R2L1 line: "- [ ] Setup wizard: a late opening reply that says a setup is running, landing while a cloud user is on the API key step, turns them into a local user and jumps them to Local transcription; their key stays in the form but is not saved at Finish (seen in the L1 review, 2026-11-21)."
- **The journal's Follow-up 2:** describe the "heard" rule in place of "left stays left", and mention round 1 in one sentence.
- **proof.md:** a "Round 1 fixes" section with one entry per finding (C1/F1, F2, C2, F3), plus the full harness on the final bundle and every mutant with the case that killed it.

## Checks before handing back

Run lint, the build and the static diff check on the final commit. pytest is not needed (no Python change); say so.
