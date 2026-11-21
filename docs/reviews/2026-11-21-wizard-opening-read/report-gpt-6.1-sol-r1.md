(Home-folder links in this copy are written as ~ paths; the byte-exact original is in the run folder.)

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
