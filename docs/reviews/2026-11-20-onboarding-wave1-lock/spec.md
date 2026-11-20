# Spec: the setup wizard's download lock becomes "closing asks first"

Follow-up to PR #26 (onboarding wave 1), before any PyPI release. The owner chose (ask.md): during a model download, closing the setup wizard is allowed after a warning, replacing the hard lock. Read `docs/reviews/2026-11-20-onboarding-wave1/diagnosis-r2.md` section 4 (design B) and that review's round 3 reports (`report-gpt-6.1-sol-r3.md`, `report-opus-fit-r3.md`) first: this PR builds design B on top of what PR #26 already has (one owner of the setup status in the local step, bounded sequential status reads, the unreachable notice, the close confirmation) and closes the round 3 leftovers.

Everything here is in `ui/src/components/OnboardingWizard.tsx` (and `LocalSetupNotes.tsx` only for F3-3), plus records. No server change, no new dependency.

## Behaviour (rules a reviewer can check)

1. **Never trapped.** `disableClose` is `saving` only. No download ever switches closing off. "Skip for now" is visible on every step, including during a download.
2. **Asks first while a setup is watched.** While the local step is watching a setup (or its start request is in flight), Escape, a backdrop click and "Skip for now" open the confirmation S11 inside the wizard, and nothing else. When nothing is watched, they act at once, as on every other step.
3. **The confirmation** shows S11 with two buttons: "Keep setting up" (hides it; it gets focus when the confirmation opens, which also scrolls it into view: fixes F3-4) and "Close setup" (closes without setting `scribe_onboarding_dismissed`, so the wizard comes back on the next load while setup is incomplete).
4. **One owner stays.** The local step stays the only writer of the watch state the wizard reads (one `onRunning` call site). Keep the round 3 machinery: one bounded status read at a time (10 s limit), failures never end watching, a good read sent after the start settled ends it, completion runs exactly once, the log is read separately, no raw server text.
5. **R3C1 (adoption).** When the wizard's own opening read says `setup_running: true`, that confirmed knowledge reaches the step so it starts watching at once (adopt `setup_last_model`, local on) instead of waiting for its own first read. Escape during that first moment asks first.
6. **R3C2 (ordering).** Track the start request's lifetime explicitly (for example a generation counter): a status read sent before the current start request settled can neither start nor end watching for it. Add the case the reviewer named: a running read arrives during a delayed start, then a stopped-and-runnable read; completion must not happen before the start settles, and only a read sent afterwards can end watching.
7. **Back during a download** stays disabled (as in PR #26), and S13 says so in one line. Under this design Back is not a way around anything, so no other guard is needed for it.
8. **Unreachable notice (R3C3 / F3-1).** S12 must not promise the download carries on after anyscribe is quit: the setup runs inside the anyscribe process and its state lives in memory (`web/routes/local.py`), so quitting stops it. Use S12 below.
9. **Setup interrupted (F3-1, optional part, build it).** When the ending read is `setup_running: false` with `setup_outcome` null and no `setup_error` (the server was restarted mid-setup), say S14 instead of the `missingPart` sentences, with the existing Try again button.
10. **F3-2.** The red `setupError` / `missing` / S14 block sits just above the button row (below the model picker), so the "Try again" it names is in view; the progress line stays above the picker.
11. **F3-3.** The RestartBanner's added sentence reads S15 (no second "restart").
12. **Resume claim.** S12 and S14 may say that Try again "carries on from where it stopped" only if you prove it: a real partial model download (Whisper Base is enough), the server stopped mid-download, restarted, Try again, and the second download visibly starts from the partial size (bytes on disk before and after, or the progress starting above 0). If you cannot prove it, use the bracketed fallback wording.

## Fixed strings

- **S11** (confirmation): "Close setup? The download keeps going in the background while anyscribe stays open. Your choices on these screens are saved only when you click Finish. To come back: Settings, then Run setup wizard." Buttons: "Keep setting up", "Close setup".
- **S12** (unreachable): "Can't reach anyscribe right now. If you closed it, open it again: this page then shows the download if it is still running, or a Try again button that carries on from where it stopped." [Fallback if resume is not proven: "...or a Try again button to start it again."]
- **S13** (header line while a setup is watched): "Back is off until setup finishes. Skip for now asks first."
- **S14** (setup interrupted): "The setup stopped before it finished, because anyscribe was closed. Click Try again; it carries on from where it stopped." [Fallback: "Click Try again to start it again."]
- **S15** (RestartBanner addition): "Then open the setup wizard again (Settings, then Run setup wizard); the download is kept."

## Records (same PR)

- `CHANGELOG.md` "Unreleased": the W6 entry describes this behaviour (closing asks first; never locked), not the hard lock.
- `BACKLOG.md`: tick the "Before the next PyPI release: finish W6" item and the wave 2 item "A way out of a slow download"; add a wave 2 line: "tests/conftest.py leaves a /tmp/ascli-test-home-* folder per pytest run (about 300 so far, harmless)".
- `docs/user/troubleshooting.md` (and regenerate `landing/docs`): entries keyed on S11, S12 and S14.
- The wave 1 journal (`docs/building/journal/2026-11-20-onboarding-wave1.md`): a dated "Follow-up" section saying why the hard lock was replaced (diagnosis-r2.md, the owner's choice).
- Rebuild `src/anyscribe/web/static`.

## Keep-list

Everything PR #26 shipped outside the download lock; the round 3 machinery in rule 4; C2's model adoption and runnable check; C3's key-check rules; the progress line above the picker; the Windows ffmpeg wording; the KraftedX credit and licence notices.

## Not in this PR

Anything from wave 2 or 3 other than the BACKLOG ticks above; any server change; Settings' LocalSetupModal (a wave 2 item).
