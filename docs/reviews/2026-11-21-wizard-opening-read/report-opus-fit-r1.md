(Home-folder links in this copy are written as ~ paths; the byte-exact original is in the run folder.)

~~~~~~
FIT REVIEW, round 1: fix/wizard-opening-read @ 8d53ebc (diff 5fb5d1e..8d53ebc)

1. VERDICT: CONDITIONAL on three things. (a) The second-visit residue (F1) is written down where the owner and the next session will see it, and he accepts it, or it gets closed. (b) One real reload walk on the bundle that actually ships, index-CJbYAiX1.js (F2). (c) CI is green on the PR's SHA.

The job fits the ask. It changes only L1: OnboardingWizard.tsx, the rebuilt bundle, BACKLOG, the journal and the packet. There is no release, no server change and no copy change. Design B, Back, Skip, S11 to S14, the bounded reads and the Mac app's offerTerminal path are unchanged. `disableClose={saving}` is still the only lock. Neither "Close setup" nor a stale reply can set the dismissed flag: `dismiss(false)` is unchanged, and the hand-off never calls dismiss. The fix is about as small as it can be: one 3-state ref in the shell, the reply passed down as the prop, and one render-time guard plus one effect in the step.

2. FINDINGS

F1. should-fix, CONFIRMED (traced). Location: OnboardingWizard.tsx:111-117 (the `localStepRef` "left stays left" rule) and :188-191. The records are BACKLOG.md:691 and journal Follow-up 2.
- Scenario:
  1. The opening read is slow.
  2. The person reaches Local transcription, and every one of the step's reads fails. Back is enabled because the step is not busy.
  3. They click Back to Provider, and the ref becomes "left".
  4. The opening reply ("running") lands and is dropped.
  5. They pick "On this computer" again. The step mounts with adopt=null, and its reads keep failing.
  6. Escape, a click outside or Skip now closes at once while a download runs. Skip also sets `scribe_onboarding_dismissed`.
- Nothing newer than the reply ever spoke. The first visit accepted no read, and it could not send a start because a start needs a pick, and the pick needs a read. So this is variant A again, one Back later, and it breaks this brief's own must-never bullet 2 word for word.
- proof.md (choices to review, item 2) names this as residue accepted by the lead. But it is not in BACKLOG, which ticks L1 as "Done", and the journal says only "so a second visit does not take a reply older than the first". The owner was promised that the lock's leftovers never reach a customer. A known leftover that ships needs his informed yes, not a lead-only acceptance buried in proof.md.
- Cost to a customer: one missing "Close setup?" while the download keeps running in the background. It needs a slow server plus failing reads plus a Back, the same odds the lead already graded as a nit for L1.
- Fix, minimum (records):
  - Add an unticked BACKLOG line under the L1 line: "- [ ] Setup wizard: if every status read on the first visit to Local transcription failed and the person went Back, a late opening reply that says a setup is running is dropped, so a second visit can close without "Close setup?" while the download runs (residue of review L1, 2026-11-21)."
  - Add one matching sentence to journal Follow-up 2.
  - Put the decision to the owner in plain words.
- Fix, alternative (code, about 5 lines): the shell keeps a "the step has heard" ref, set through a new callback when the step first accepts a read. It drops a "left" reply only when that ref is set, and otherwise holds the reply for the next mount. If you take this route, restore the "no start sent" half (see answer 2).

F2. should-fix, CONFIRMED (from proof.md). The only real-server walk (proof.md "The real run") ran on index-Bl10hv_a.js. The shipped bundle is index-CJbYAiX1.js (c1d9be0), which came after the hand-off moved from an effect to a render-time setState (1def075). proof.md says this itself ("Not re-run after this change").
- The lens and the house rule both want at least one hook-free walk of the build that ships. The harness fakes the status endpoint, so the shipped reload path has only been seen through fakes.
- My reading of the diff f03d02d..1def075 is that the reload (never-shown) path is logically the same. That is reasoning, not a walk.
- Fix: re-run the real reload-mid-setup walk once on c1d9be0 or later: reload, the wizard opens on the running download, and Escape asks first. This is about 5 minutes with the Tiny model.

F3. nit, CONFIRMED. BACKLOG.md:691 keeps the old plan text "reconcile it through the step's start-ordering guard". The fix does not use that guard: its half was removed as an equivalent mutant. Suggested wording for the end of the line: "Done in #NN: where the wizard is when the reply lands decides what it may do; the step takes it only before its own first accepted read." Also, spec.md asked for the PR's short form. The branch name stands in for it until the lead fills it in, so this is pending before merge.

3. ANSWERS TO THE BRIEF'S QUESTIONS (advice)

Q1, "left stays left": right in most cases, but it drops one reply that should count.
- It is correct whenever the first visit had an accepted read. That read is newer than the reply, and a second-visit mount (status null again) could otherwise take a stale "running" and end in a false S14.
- It is wrong in exactly one case: the first visit accepted nothing, which also means it sent no start. Then the dropped reply is the newest knowledge the wizard has. That is F1.
- The case is rare and costs little. The rule is defensible only if it is recorded and accepted, not silently closed under a ticked "Done".

Q2, the Mii_start equivalence trace: sound in production, under today's rule 1.
- I checked that `handleStartSetup` returns early when `!selected`, and the start button is disabled on `!selected || busy`.
- On a first visit marked "showing", `form.localModel` gets a value only from the step's own accepted read: `onPresetSize`, a card click or the recommendation, each of which needs `status`. The only other source is the never-shown branch. That branch mounts the step already watching, so the button stays disabled until an accepted read ends watching, and that read sets status. Nothing resets `status` to null: the only `setStatus` calls, at :826 and :904, are given a real reply.
- StrictMode's second opening reply is handled the same way.
- One caveat. The equivalence depends on "left stays left". On a second visit `selected` survives from the first visit, so a second-visit mount with failing reads can show "Install now" and send a start with `status === null`. If F1 is fixed in code by handing replies to a second visit, the "no start sent" half stops being equivalent and must come back.

Observation outside L1 (not a finding; rule 1 settled it, and this PR must not change it). The never-shown branch still writes `provider: "local"`. If the late opening reply lands while a cloud user is on the API key step, the wizard turns them into a local user and jumps them to Local transcription. Their key stays in the form but is not saved at Finish. This is behaviour from before this PR, under the same slow-server odds. Worth its own BACKLOG line for wave 2.

4. PENDING OWNER CHECKS
- Does he accept shipping F1's residue (one missing warning, only after a Back with every read failing), or does he want it closed before the PyPI release? His original promise covered "the leftovers".
- The release itself still waits for his yes. This PR does not release.

5. WHAT I COULD NOT CHECK, AND WHAT I INSPECTED
- Not run (read-only brief): the harness, the builds, lint, CI and the real walk. The commands to run:
  - `cd ~/labs/projects/anyscribe-wt/wizard-l1/ui && npm run lint && npm run build && git -C .. diff --exit-code -- src/anyscribe/web/static`
  - the real reload walk on c1d9be0 or later (F2)
  - CI on the PR's SHA
- I did not look at the screenshots (they show the earlier bundle). I did not read the other reviewer's report in the run folder, to stay independent.
- Inspected:
  - the packet (ask.md, spec.md, target.md, proof.md, lens.md, review-log.md) and declined.md
  - Sol's L1 entry and the lead's L1 verdict line in docs/reviews/2026-11-20-onboarding-wave1-lock/
  - the full source and records diff 5fb5d1e..8d53ebc
  - the f03d02d..1def075 diff
  - OnboardingWizard.tsx: the shell at lines 85-420 and StepOfflineOptIn at 720-1075
  - the `setup_running` and `setup_last_model` fields in types.ts:115-118 and local.py:75-78
  - the CHANGELOG W6 lines 57-62: no overclaim
  - the result files: r0b-final-all.json has 31 passes and 0 fails; old-l1.json has 3 fails; r0b-Mi, r0b-Mii_status and r0b-Miii each have at least one fail, matching the proof's tables. The result files do not record which bundle they ran on.

Skipped: Modal.tsx and client.ts beyond what the wizard's calls show. Risk: F1 is a lock leftover the owner has not been told about.

~~~~~~
