Size: L
Sized because: code PR with no gate (feature + dependency change; no secrets, money, data loss or unattended automation)
Cap: 3
Packet: v1
resized to L: approved by Rishabh
over cap: round 4 approved by Rishabh
Round 4 is Claude-only (fixer Opus, re-checks Opus): no other-family reviewer in round 4, by his choice to save OpenAI usage.

| Round | Role | Model, effort | Lane | Target (sha/version) | Verdict | Raised | Upheld | Minutes | Fixer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | correctness | gpt-6.1-sol, high | Codex CLI read-only | 87dbd2f | NOT YET | 11 | 10 | 20 | Claude Opus fixer, Agent tool |
| 1 | fit | Opus 5.5, high | Agent tool (Claude lane, read-only by instruction; snapshot unchanged) | 87dbd2f | NOT YET | 10 | 9 | 6 | Claude Opus fixer, Agent tool |
| 2 | correctness re-check | gpt-6-astra, high | Codex CLI read-only | 8c5d10d | NOT YET | 7 | 7 | 25 | Claude Opus fixer, Agent tool (round 1 fixes) |
| 2 | fit (rejoined: fixes changed screens) | Opus 5.5, high | Agent tool (read-only by instruction; snapshot unchanged) | 8c5d10d | CONDITIONAL | 8 | 8 | 5 | Claude Opus fixer, Agent tool (round 1 fixes) |
| 3 | correctness final re-check | gpt-6.1-sol, high | Codex CLI read-only | 5551230 | NOT YET | 3 | 3 | 30 | Claude Opus fixer, Agent tool (round 2 fixes, after Fable diagnosis) |
| 3 | fit (rejoined: Settings and wizard changed) | Opus 5.5, high | Agent tool (read-only by instruction; snapshot unchanged) | 5551230 | CONDITIONAL | 3 | 3 | 5 | Claude Opus fixer, Agent tool (round 2 fixes) |
| 4 | correctness final re-check (over cap, owner-approved, Claude-only) | Opus 5.5, high | Agent tool (read-only by instruction; snapshot unchanged during the round) | 90bc0cf | GOOD TO GO | 4 | 4 | 10 | Claude Opus fixer, Agent tool (round 3 fixes); lead (R4F1, R4F2, R4C2 in 0659c0a) |
| 4 | fit (rejoined, Claude-only) | Opus 5.5, high | Agent tool (read-only by instruction) | 90bc0cf | CONDITIONAL on R4F1 | 3 | 3 | 3 | lead (0659c0a) |

| Id | Round | Reviewer | Severity | Lead verdict | Evidence | Also raised by |
|---|---|---|---|---|---|---|
| C1 | 1 | gpt-6.1-sol | blocker | UPHELD | Traced: TranscribePage keeps stale quality=balanced after wizard; matches builder screenshot result-note-1440 (lead saw the WARNING line) | F1, lead L2 |
| C2 | 1 | gpt-6.1-sol | should-fix (lead downgrade from blocker: the main case, a whole recording in an uncovered language, is guarded and proven; gaps are mid-recording switches, leading silence and the Whisper-only auto regression) | UPHELD in part: 30 s window, leading silence, Whisper-only regression UPHELD; explicit-label bypass DECLINED (see declined.md) | Code read local.py plan(); spec decision 6 chose explicit-language trust | F4 |
| C3 | 1 | gpt-6.1-sol | should-fix (lead downgrade: unpushed branch, precedent on main) | UPHELD, lead-fixed | target.md scratch paths masked; screens/ moved out of repo; branch to be squashed before first push | F10 |
| C4 | 1 | gpt-6.1-sol | blocker (lead upgrade: every Mac user gets a 110 s load and 7x slower runs) | UPHELD | Lead ran on M1 Pro: default providers 110.6 s load / 3.1x; CPU provider 0.9 s / 23.6x | lead L1, F6 |
| C5 | 1 | gpt-6.1-sol | should-fix | UPHELD | Traced cached = any bytes; pull skips on any bytes | builder risk note |
| C6 | 1 | gpt-6.1-sol | should-fix | UPHELD | OnboardingWizard enqueues also-model and advances; proof records Turbo still downloading at All set | F3 |
| C7 | 1 | gpt-6.1-sol | should-fix | UPHELD | Reviewer evaluated recommend() with low disk; reasons not regenerated | |
| C8 | 1 | gpt-6.1-sol | should-fix | UPHELD | Screens show no reference-machine caption; mockup had one | F6, lead L3 |
| C9 | 1 | gpt-6.1-sol | should-fix | UPHELD | Traced orchestrator cached path and human batch print | |
| C10 | 1 | gpt-6.1-sol | should-fix | UPHELD | Python keeps imported av module after on-disk downgrade; standard behaviour | |
| C11 | 1 | gpt-6.1-sol | should-fix | UPHELD | Traced pendingDefault not cleared on later explicit choice | |
| F1 | 1 | opus | blocker | UPHELD | = C1 | C1 |
| F2 | 1 | opus | should-fix | UPHELD | LocalModelPicker applies suggestion only on Use this; spec said pre-select | |
| F3 | 1 | opus | should-fix | UPHELD | = C6 plus size disclosure | C6 |
| F4 | 1 | opus | should-fix | UPHELD | = C2 mid-recording part; lead decides wording + 3-window check, keeps Parakeet for mix | C2 |
| F5 | 1 | opus | should-fix | UPHELD | Read local_recommend.py reasons; other shares Hindi branch | |
| F6 | 1 | opus | should-fix | UPHELD | = C8 | C8 |
| F7 | 1 | opus | should-fix | INCONCLUSIVE | Fixer to settle on a fresh HOME; static fallback either way | |
| F8 | 1 | opus | should-fix | UPHELD | getting-started What you need still cloud-first | |
| F9 | 1 | opus | nit | UPHELD | Screens show step 1 to 3, raw ids, double sizes | |
| F10 | 1 | opus | nit | UPHELD, lead-fixed | = C3 | C3 |
| R2C1 | 2 | gpt-6-astra | should-fix | UPHELD | Traced local.py: uncovered-language branch runs before the all-low-confidence branch; probe [("hi",0.2)] forced hi | |
| R2C2 | 2 | gpt-6-astra | should-fix | UPHELD | Traced LocalModelPicker: every response calls onUse, no staleness guard | R2F1 (same mechanism) |
| R2C3 | 2 | gpt-6-astra | should-fix | UPHELD | Traced: cached ignores helpers; default activation reads cached | |
| R2C4 | 2 | gpt-6-astra | should-fix | UPHELD | Traced: wizard Next bypasses extra-model capture | |
| R2C5 | 2 | gpt-6-astra | should-fix | UPHELD | Traced: onUse only for non-null primary | |
| R2C6 | 2 | gpt-6-astra | should-fix (lead downgrade to nit: a quoted prefix, no session id) | UPHELD, lead-fixed (packet record) | grep finds the quote in findings.md and report-opus-r1.md | R2F6 |
| R2C7 | 2 | gpt-6-astra | nit | UPHELD | Traced onboard.py headless human output | |
| R2F1 | 2 | opus | should-fix | UPHELD | Traced Settings handleRecommendation commits on answer | R2C2 |
| R2F2 | 2 | opus | should-fix | UPHELD | local_recommend sets hi for every indian answer | |
| R2F3 | 2 | opus | should-fix | UPHELD (lead decides in scope: one hint line when no key is set) | Traced resolve/openai messages on an un-onboarded config | |
| R2F4 | 2 | opus | nit | UPHELD | grep "typical" in CHANGELOG and docs | |
| R2F5 | 2 | opus | nit | UPHELD | fx-wizard-4-allset-ready shows ready beside "once it finishes" | |
| R2F6 | 2 | opus | nit | UPHELD, lead-fixed | = R2C6 | R2C6 |
| R2F7 | 2 | opus | nit | UPHELD | LocalSetupNotes terminal-only wording | |
| R2F8 | 2 | opus | nit | UPHELD | Pre-existing amber needs-API-key rows on a local user's Settings | |
| R3C1 | 3 | gpt-6.1-sol | should-fix (lead downgrade from blocker: a lost update needs a foreground save inside the milliseconds of a background save; the same unguarded read-modify-write already existed on main via run_setup; widened, not introduced) | UPHELD | Traced config_set.set_value read-modify-write with no shared lock; reviewer's in-memory interleaving | |
| R3C2 | 3 | gpt-6.1-sol | should-fix | UPHELD | Traced models.py choose builds response from shared pending after starting the worker | |
| R3C3 | 3 | gpt-6.1-sol | should-fix | UPHELD | Traced run_setup writes its model at the end with no check for a newer choose | |
| R3F1 | 3 | opus | should-fix | UPHELD | Traced: local setup never sets provider; hint loops; plain <p> collapses the newline | |
| R3F2 | 3 | opus | nit | UPHELD | Tip shows a CLI command on the web and stays while pending | |
| R3F3 | 3 | opus | nit | UPHELD | Use button offered for the current default | |
| R4C1 | 4 | opus | nit | UPHELD, residue | Fixer's note was false: web wizard Finish posts provider local to onboarding/save, which runs run_setup without the generation; explicit click, pre-existing synchronous call | |
| R4C2 | 4 | opus | nit | UPHELD, lead-fixed in 0659c0a | PlanNotes whitespace-pre-line; resolve appends local_hint only when the fallback is not local; test fails on 90bc0cf | |
| R4C3 | 4 | opus | nit | INCONCLUSIVE, residue | Two-tab superseded setup may say a non-runnable model is ready; not walked | |
| R4C4 | 4 | opus | nit | UPHELD, residue (the onboard --force part lead-fixed with R4F2) | Undo of same key (unreachable today); sargam migration once per install; diarize+free tip | R4F2 |
| R4F1 | 4 | opus | should-fix | UPHELD, lead-fixed in 0659c0a (display-only; lead-verified) | Web setup window now says "default local model" and "New transcripts still go to <provider>. ... pick 'free' ..."; test fails on 90bc0cf | |
| R4F2 | 4 | opus | nit | UPHELD, lead-fixed in 0659c0a | Hint names `anyscribe onboard --force` | R4C4 |
| R4F3 | 4 | opus | nit | PLAUSIBLE, residue | Use button for a model already pending; not walked | |

Closed: lead-verified. Round 4 correctness GOOD TO GO; the fit reviewer's one should-fix (R4F1) and two display nits (R4F2, R4C2) fixed by the lead in 0659c0a under the at-the-cap display-only rule, each with a test seen failing on 90bc0cf and passing after. Residue for the owner: R4C1, R4C3, R4C4 (remaining parts), R4F3. Round 4 had no reviewer from a different model family (owner's choice); rounds 1 to 3 did (gpt-6.1-sol, gpt-6-astra, gpt-6.1-sol).

## Cost (phlinux, 2026-11-19 22:12)

| Round | Codex runs | Codex tokens used | Codex minutes | Claude agents | Claude fresh+out tokens | Claude minutes |
|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0.0 | 1 | 1,091,454 | 61.0 |
| 1 | 1 | 232,062 | 6.2 | 2 | 813,044 | 76.3 |
| 2 | 1 | 207,453 | 6.6 | 3 | 880,133 | 41.7 |
| 3 | 1 | 227,209 | 7.2 | 2 | 566,308 | 37.7 |
| 4 | 0 | 0 | 0.0 | 2 | 345,452 | 11.8 |

A round run on the other machine is added by running this there. Claude usage counted once per message id; Codex tokens are the last figure Codex prints. A duration shown as ? could not be measured (no rollout file or no timestamps): unknown, not zero. Codex children in T3 and anything on the other machine are not counted here. The lead's own tokens are not separable and are not counted.
