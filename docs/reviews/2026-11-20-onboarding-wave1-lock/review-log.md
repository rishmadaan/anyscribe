Size: M
Sized because: a code PR with no gate: dashboard-only behaviour that reaches customers only with a later PyPI release (the owner gates that), plus copy in the docs; no secrets, money, data loss or unattended automation.
Cap: 2
Packet: v1

| Round | Role | Model, effort | Lane | Target (sha/version) | Verdict | Raised | Upheld | Minutes | Fixer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | correctness | gpt-6.1-sol, high | Codex CLI read-only | bc144d4 | NOT YET | 3 | 3 | 6 | Claude Opus fixer, Agent tool |
| 1 | fit | Opus 5.5, high | Agent tool (read-only by instruction; snapshot unchanged) | bc144d4 | CONDITIONAL | 5 | 5 | 3 | Claude Opus fixer, Agent tool |
| 2 | correctness re-check | gpt-6-astra, high | Codex CLI read-only | 03f6562 | CONDITIONAL | 1 | 1 | 4 | lead (post-cap, unreviewed, lead-verified) |
| 2 | fit (rejoined: fixes changed screens and copy) | Opus 5.5, high | Agent tool (read-only by instruction; snapshot unchanged) | 03f6562 | CONDITIONAL | 4 | 4 | 3 | lead (post-cap, unreviewed, lead-verified) |

| Id | Round | Reviewer | Severity | Lead verdict | Evidence | Also raised by |
|---|---|---|---|---|---|---|
| LF1 | 1 | opus fit | should-fix | UPHELD (lead approves the scope addition: LocalModelPicker.tsx:85 and troubleshooting.md:642-643) | The builder's real restart run: the download restarted from 0%, while the card says "incomplete: the download resumes" | builder flagged |
| L2 | 1 | gpt-6.1-sol | should-fix | UPHELD | T4_notRunning asserts "because anyscribe was closed" where the start never reached the server; the empty state is also the server's initial state | LF fit advice (S14 caveat) |
| L3 | 1 | gpt-6.1-sol | should-fix | UPHELD (pre-existing, but inside this step and against the brief's must-never list) | routes/local.py stores result.error, installer stderr or str(e) as setup_error; the step renders it verbatim and opens the log | builder flagged in PR #26 round 3 |
| L1 | 1 | gpt-6.1-sol | nit (lead downgrade from should-fix: under the owner's confirm-to-close design a wrong belief costs one missing confirmation while the download keeps running, which is design B's stated tolerance; it needs a delayed opening read, a step reached before it answers, and failing step reads; the reroute variant needs a full setup to finish inside the opening read's 10 s window) | UPHELD as nit, not fixed in this PR | Traced: useState(adopt) takes only the initial value; the opening callback has no start-generation guard | fit (edge i) |
| LF2 | 1 | opus fit | nit | UPHELD | S12's "if it is still running" half does not fit a reader who closed anyscribe | |
| LF3 | 1 | opus fit | nit | UPHELD | Modal sends Escape to askOrClose, which reopens the same box | |
| LF4 | 1 | opus fit | nit | UPHELD | CHANGELOG says only Back is off; the checkbox, cards and start button are off too | |
| LF5 | 1 | opus fit | nit | UPHELD | The code comment does not say what the resume check found | |
| R2LF1 | 2 | opus fit | should-fix | UPHELD, lead-fixed after the cap | The new setup-failure sentence offered no way out, unlike its three siblings in the same step | |
| R2LF2 | 2 | opus fit | nit | UPHELD, lead-fixed after the cap | While unreachable the progress line still said a download was running, contradicting S12 | |
| R2LF3 | 2 | opus fit | nit | UPHELD, lead-fixed after the cap | No troubleshooting entry for the setup-failure sentence | |
| R2LF4 | 2 | opus fit | nit | UPHELD, lead-fixed after the cap | cli/models_cmd.py printed "Resume the download" (same disproven claim) | |
| R2L1 | 2 | gpt-6-astra | nit | UPHELD as residue (BACKLOG wave 2) | The failure's [error] line can miss the browser's install log if the last log read fails or the log is past its 500-line cap | |

Round 1 minutes from timestamps: correctness 17:41:19 to 17:46:55; fit 197 s (Agent tool).

Round 2 minutes from timestamps: correctness 18:10:28 to 18:14:36; fit 173 s (Agent tool). CI on 03f6562: all 9 checks pass.
Cap reached (round 2 of 2 at M) with one UPHELD should-fix (R2LF1, a display-only sentence on a repeated-failure path) and three nits. Per the review skill step 7 at M, the lead fixed them after the cap and reports these last changes as UNREVIEWED, lead-verified: a new browser check failed on the old build and passes on the new one (proof.md, "Lead-made changes after the round 2 re-check"). L1 is now marked "Before the next PyPI release" in BACKLOG, honouring the owner's promise that the lock's leftovers never reach a customer.

## Cost (phlinux, 2026-11-20 18:26)

| Round | Codex runs | Codex tokens used | Codex minutes | Claude agents | Claude fresh+out tokens | Claude minutes |
|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0.0 | 1 | 530,322 | 35.8 |
| 1 | 1 | 178,838 | 5.3 | 2 | 427,016 | 24.3 |
| 2 | 1 | 152,487 | 3.8 | 1 | 126,478 | 2.9 |

A round run on the other machine is added by running this there. Claude usage counted once per message id; Codex tokens are the last figure Codex prints. A duration shown as ? could not be measured (no rollout file or no timestamps): unknown, not zero. Codex children in T3 and anything on the other machine are not counted here. The lead's own tokens are not separable and are not counted.
