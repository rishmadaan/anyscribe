# Spec: the setup wizard's opening read reaches the local step in order (review L1)

## The defect (L1, from `docs/reviews/2026-11-20-onboarding-wave1-lock/report-gpt-6.1-sol-r1.md`)

When the wizard opens, it reads `/api/local/status` once (`OnboardingWizard.tsx`, the effect commented "A download already running..."). If the reply says `setup_running`, it sets the form to local, sets `adopt`, and routes to the local step (`offline_opt_in`). The local step starts `watching` from `useState(adopt)`, so only the value at mount counts.

Two orderings go wrong:

- **A. Late reply, mounted step, failing reads.** The opening read is slow; the person reaches the local step before it answers; the step mounts with `adopt=false`; the step's own status reads fail. The opening reply then says running, but watching stays false. Escape and backdrop close at once, Skip closes at once and sets `scribe_onboarding_dismissed`, and Back stays enabled, while a download really runs.
- **B. Stale reply after a newer setup.** The opening reply ("running", sent before anything else) lands after the person started a newer setup on the local step, it finished quickly and the wizard moved on to Workspace or All set. The handler routes back to the local step with `adopt=true`, and the step watches from a reply older than the start.

Read Sol's L1 section in full, and the lead's verdict line for L1 in that packet's `review-log.md`.

## Decisions already made (the lead's; build these)

1. **Where the wizard is when the reply lands decides what the reply may do.** On a reply with `setup_running: true`:
   - **The local step has never been shown in this wizard** (still on Welcome, Provider or API key): exactly as today. Set the form (local, enabled, the running model), hand the reply to the step, and route to `offline_opt_in`.
   - **The local step is showing now:** hand the reply to the mounted step. The wizard shell changes neither the form nor the route; the step decides (rule 2).
   - **The local step was shown and has since been left:** drop the reply. The step's own reads, and any start it sent, are newer than the reply.

   "Has been shown" is known when the reply lands, so read it from a ref or equivalent, never from a closure captured when the read was sent.
2. **The step accepts a handed reply only if nothing newer has spoken.** Nothing newer means no accepted status read of its own yet (`status` is still null) and no start request sent in this mount (`startGenRef.current === 0`). On accepting, it does what its own running read does: turn local on, select `setup_last_model` when it is set, and start watching. Otherwise it ignores the reply. A reply present when the step mounts is accepted at mount, as today: watching starts true on the first render, with no render where closing doesn't ask.
   - *Lead decision, 2026-11-21 (round 0):* the "no start sent" half is dropped. It was an equivalent mutant (Mii_start): a start needs a pick, and the pick comes only from the step's own accepted read, so `status` is already set. The check is `status === null` alone.
3. **The step remains the one writer of `watched`.** The `onRunning` effect, its single call site and the start-generation counter stay as they are. Don't add a second path that sets `watched` or `confirmClose` from the shell.
4. **Keep what exists.** Design B's behaviour, the S11, S12, S13 and S14 copy, the bounded sequential reads, Back and Skip, `goWorkspace` and Back clearing the handed reply, and the Mac app's `offerTerminal` path all stay as they are.

The prop's shape is the builder's call: the reply itself, or the model plus a flag. Choose whatever makes rule 2 smallest. The form must not be written for a reply the step then ignores.

## Out of scope (settled; leave it)

- Before the opening reply lands on Welcome, closing closes at once (accepted in the lock review, fit edge i).
- A failed opening read is still silently dropped.
- R2L1 (the install log can miss the `[error]` line): it stays in BACKLOG for wave 2.
- Any server, installer, website or Mac app change. No new copy.

## Records

- `BACKLOG.md`: tick the "Before the next PyPI release" L1 line (around line 691) and add the PR's short form.
- `docs/building/journal/2026-11-20-onboarding-wave1.md`: add a short "Follow-up 2" section: what L1 was, the rule chosen and why, and the proof.
- `CHANGELOG.md` "Unreleased": none needed, since the feature itself hasn't been released. If a line in the W6 entry now overclaims, fix that line only.
- Rebuild the committed bundle (`src/anyscribe/web/static`) so CI's bundle check passes.

## Proof bar (in proof.md)

- Both of Sol's variants as harness cases, each failing on the old build (5fb5d1e) and passing on the new one. Assert identities, not counts: which step shows; whether "Close setup?" opened on Escape, on backdrop and on Skip; whether `scribe_onboarding_dismissed` is unset; whether Back is disabled; which model card is selected.
  - **A:** delayed opening "running", the step reached first, the step's reads failing, then the reply lands. Closing must now ask first.
  - **B:** delayed opening "running", a newer setup started on the step and finished, the wizard on Workspace. The reply must not route back, and nothing must flip on Workspace.
- **Variant C:** the step had an accepted "not running" read, then the late opening "running" lands. It is ignored: not watching, and the pick is unchanged.
- **Regressions:** the existing cases still pass, including T5, T5_late, R3C1, R3C2, T4v2 and the S11 and S13 cases. Name any you changed and why.
- **Mutation:** remove each new guard in turn and show a named case failing:
  - (i) the "left the local step: drop" check;
  - (ii) the step's "nothing newer" check;
  - (iii) the hand-off to a mounted step.
  If a mutant survives, trace whether the test is weak or the guard is equivalent, and say which.
- `npm run lint` and `npm run build` in `ui/`; `scripts/check-ui-bundle` or whatever CI runs for the bundle (read `.github/workflows`); `pytest -q` (no Python change is expected, so it is a smoke run).
- One real run against a real server on a throwaway HOME (no fakes for the status endpoint): reload mid-setup and confirm the wizard still opens on the running download, and that Escape asks first. If a real local-engine download is too heavy, say what you ran instead.
