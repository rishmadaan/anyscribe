# Findings, verbatim

(Home-folder links in this copy are written as ~ paths; the byte-exact original is in the run folder.)

## report-gpt-6.1-sol-r1.md (round 1)

~~~~~~
**NOT YET.** The main L1 cases are fixed, but leaving and returning to the local step still permits closing without warning after an otherwise valid running reply arrives.

Reviewed `fix/wizard-opening-read` at `8d53ebc7ca857db3439196da68ea5c4a0e633999`, against `5fb5d1e`. CONFIRMED below means established by source trace or inspected evidence. Runtime execution was prohibited.

**1. Findings**

**C1. should-fix | CONFIRMED: “left stays left” discards running knowledge that nothing newer superseded.**

Where: [OnboardingWizard.tsx:111](~/labs/projects/anyscribe-wt/wizard-l1/ui/src/components/OnboardingWizard.tsx:111), opening-reply rejection at line 189, closing at line 217.

Concrete sequence, within the opening request’s ten-second window:

1. The opening status request is delayed.
2. The customer enters Local transcription. Every step status read fails, so `status` remains null and watching remains false.
3. They press Back, then select On this computer again.
4. The second visit’s reads also fail.
5. The opening reply arrives with `setup_running: true`.

Back permanently changed `localStepRef` to `"left"`. Returning does not change it, so line 189 drops the reply. Escape and backdrop close immediately. Skip closes immediately **and writes `scribe_onboarding_dismissed=1`**.

No accepted newer status or start superseded this reply. Visiting a screen is being treated as evidence that the screen learned something. The same loss occurs if the reply arrives while the customer is still on Provider after pressing Back.

The proof acknowledges this residue, but its consequence violates the brief’s explicit closing invariant. None of L1A to L1D exercises it.

**Fix:** track actual supersession by accepted status reads and starts across visits. Preserve eligible running knowledge across Back and remount, while retaining one watch-state owner and preventing rerouting from Workspace or All set. Add the sequence above, asserting all three closing methods and the dismissal flag. Simply changing `"left"` back to `"showing"` is insufficient because a remount loses its previous status and start-generation state.

**C2. nit | CONFIRMED: StrictMode’s duplicate opening requests can apply older knowledge after newer knowledge.**

Where: [OnboardingWizard.tsx:185](~/labs/projects/anyscribe-wt/wizard-l1/ui/src/components/OnboardingWizard.tsx:185), handoff acceptance at line 785 and model selection at line 793.

Under development StrictMode effect replay, the opening effect issues two requests without cleanup or request identity:

- Older request A captures running Whisper Small and is delayed.
- Newer request B reports running Whisper Base and arrives first, mounting the step with Base selected.
- All step reads fail.
- A arrives. The shell hands it over, and `status === null` permits acceptance. Small replaces Base.

The payloads need not match. The server reads mutable setup state at [local.py:75](~/labs/projects/anyscribe-wt/wizard-l1/src/anyscribe/web/routes/local.py:75).

This is a development replay defect, not evidence that production doubles effects. However, the committed bundle **does** wrap the root in `StrictMode`; the proof’s statement that it contains no StrictMode is inaccurate.

**Fix:** give the opening effect cleanup that invalidates its callback and aborts its request. Verify opposite reply orders with different payloads, including a newer stopped reply followed by an older running reply.

**C3. nit | CONFIRMED: the submitted diff fails whitespace validation.**

Where: [spec.md:20](~/labs/projects/anyscribe-wt/wizard-l1/docs/reviews/2026-11-21-wizard-opening-read/spec.md:20).

`git diff --check 5fb5d1e..8d53ebc` exits 2 for trailing whitespace. Remove the spaces on that blank line.

**2. Answers to the brief’s questions**

**Is “left stays left” right?** Only where something newer actually superseded the opening reply. It correctly prevents the completed-setup reroute, but is too broad when all first-visit reads failed. C1 is the counterexample.

**Was removing “no start sent” justified?** Yes, for this exact implementation. On the first visit eligible for late handoff, starting requires a selection obtained through an accepted status read, or adoption that already disables starting. Therefore the status check rejects the reply before the start-generation check could matter.

That reasoning is deliberately narrow. On a second visit, selection survives in the parent while the step’s status resets to null. T11 and R3C2 exercise starts in that state. Today `"left"` prevents handoff there. Revisit this equivalence when fixing C1.

**3. Rules and evidence**

- **Rule 1:** the first-visit and Workspace paths work; the permanent-left interpretation has C1.
- **Rule 2:** the recorded late handoff, newer-status rejection and refused-start cases work. StrictMode has C2.
- **Rule 3:** preserved. There remains one `onRunning` call site.
- **Rule 4:** the source diff preserves S11 to S14, Back and Skip controls, bounded polling, start-generation handling, and `offerTerminal`. No server, installer, website or desktop source changed.

The saved final results contain 31 passing cases. I checked their assertions, snapshots and request traces. The final mutations fail as claimed: Mi under L1B, Mii_status under L1C/L1D/T5_late, and Miii under L1A. These establish the exercised orderings, not the missing Back/remount or StrictMode cases.

The two real-run screenshots support a running Tiny download and a visible confirmation with Keep setting up focused. That walk used the earlier bundle, as the proof’s final section discloses. It was not repeated after the render-time handoff change.

**4. Pending owner checks**

None needed to resolve these findings. Reproduction, fixes, exact-SHA CI and the final real-server walk are engineering work. A PyPI release remains a separate owner decision.

**5. Inspection and limits**

I read the complete named packet and declined list, prior L1 report and verdict, prior design specification, complete wizard, Modal, API client and types, server route, current harness and cases, mutation/build instruments, all fourteen current result files, supplied logs and both screenshots. I inspected the source/record diff and relevant generated bundle logic.

HEAD and branch match the target. Inspected source and static files have no working-tree delta from that target. The static entry references `index-CJbYAiX1.js`.

I did not independently execute browser cases, builds, tests, native-platform checks or CI. The brief prohibited them. Relevant unrun commands include:

```sh
cd ~/labs/projects/anyscribe-wt/wizard-l1/ui
npm run lint
npm run build

cd ~/labs/projects/anyscribe-wt/wizard-l1
git diff --exit-code -- src/anyscribe/web/static
uvx "ruff>=0.4,<0.16" check src tests scripts
python3 scripts/build-docs.py
python3 scripts/check-docs.py
```

The recorded pytest command was also not rerun:

```sh
HOME=<new-empty-review-home> \
PYTHONPATH=~/labs/projects/anyscribe-wt/wizard-l1/src \
uv run --no-project \
  --python ~/labs/projects/anyscribe/.venv/bin/python \
  --with "pytest>=8.0" --with "huggingface-hub>=0.21" \
  python -m pytest -q
```

Existing browser entry points, including `window.__run("L1A")`, `window.__run("L1B")`, `window.__run("R3C1")` and `window.__run("R3C2")`, were inspected, not executed. C1 and C2 require additional cases. No files or processes were changed.
~~~~~~

## report-opus-fit-r1.md (round 1)

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
