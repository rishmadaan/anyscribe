You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names. Test folders, leave
them alone: ~/labs/projects/anyscribe-wt/wizard-l1/tests and ~/labs/projects/anyscribe-wt/wizard-l1/desktop.

THE PACKET, read all of it first: ~/labs/projects/anyscribe-wt/wizard-l1/docs/reviews/2026-11-21-wizard-opening-read/
ask.md (the owner's words; the first question is whether this is the job he
asked for), spec.md, target.md, proof.md (what the builder ran and saw: claims
to check, not facts), lens.md; ~/labs/projects/anyscribe-wt/wizard-l1/docs/reviews/declined.md (SETTLED, DO NOT
REOPEN). The finding being fixed: L1 in
~/labs/projects/anyscribe-wt/wizard-l1/docs/reviews/2026-11-20-onboarding-wave1-lock/report-gpt-6.1-sol-r1.md,
and the lead's verdict line for L1 in that folder's review-log.md. That
folder's spec.md is the design (B) this fix must keep.

THE TARGET: checkout ~/labs/projects/anyscribe-wt/wizard-l1, branch fix/wizard-opening-read at 8d53ebc. The change is
`git -C ~/labs/projects/anyscribe-wt/wizard-l1 diff 5fb5d1e..8d53ebc` (5fb5d1e is main; 41ee458 adds the packet
only). Review sources; the static bundle under src/anyscribe/web/static is
generated.

YOUR ROLE: fit. Is this what he asked for (ask.md: L1 only, before the release, so the lock leftovers never reach a customer), is it the simplest thing that closes L1, does anything a customer sees or does change in a way they would notice or object to, and do the records (BACKLOG line, journal Follow-up 2, proof) say only what the code and proof show.

MUST NEVER HAPPEN:
- The setup wizard traps the customer: any state where closing is impossible other than while saving at Finish.
- While anything in this wizard knows a setup is running and nothing newer contradicts it, Escape, a click outside or Skip closes the wizard without "Close setup?" (the opening reply landing before the step mounts, after it mounted, while its reads fail).
- An old status reply moves the person backwards (reroutes from Workspace or All set), changes their pick, or starts or ends watching after something newer spoke (an accepted read of the step's own, a start request).
- "Close setup" or a stale reply sets scribe_onboarding_dismissed.
- Anything outside L1 changes: design B's behaviour, the S11 to S14 copy, Back and Skip, the bounded sequential reads, the Mac app's offerTerminal path.

QUESTIONS FOR YOU:
- Is "left stays left" (spec.md rule 1, the builder's reading for a second visit) right, or does it drop a reply that should count?
- The builder found one half of rule 2's check (no start sent) equivalent and the lead had it removed: is the trace in proof.md sound?

BUDGET: this is round 1 of at most 2; about 30 minutes.

SOURCES beyond the packet: ui/src/components/OnboardingWizard.tsx in full
(the shell and StepOfflineOptIn), ui/src/components/Modal.tsx,
ui/src/api/client.ts and ui/src/api/types.ts
(LocalStatusResponse), src/anyscribe/web/routes/local.py (what
the status payload holds). The builder's harness, cases, results and
screenshots: ~/.review-runs/2026-11-21-wizard-opening-read/ (instruments/,
logs/, screens/; old-src and mut-src are the old build and the mutants).

LEAD-MADE CHANGES: 41ee458 (packet) only; no code.

LENS: the packet's lens.md.

YOU MAY RUN: read-only commands: git log/show/diff on that checkout, grep,
sed -n, cat. YOU MAY NOT: run tests, builds, servers, Docker, package installs,
anything that writes; push, or call any provider API.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Findings, most severe first, numbered F1, F2...: severity
   (blocker / should-fix / nit, only these words); CONFIRMED (you traced it) or
   PLAUSIBLE (say what would settle it); where (file:line); what goes wrong, as a
   concrete scenario; the fix (for copy, the exact replacement wording).
3. Answers to the questions in this brief (advice, not findings).
4. Pending owner checks: things only the owner can confirm.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
