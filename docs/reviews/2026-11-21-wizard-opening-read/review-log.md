Size: M
Sized because: a code PR with no gate: a dashboard-only ordering fix that reaches customers only with a later PyPI release (the owner gates that); no secrets, money, data loss or unattended automation.
Cap: 2
Packet: v1

| Round | Role | Model, effort | Lane | Target (sha/version) | Verdict | Raised | Upheld | Minutes | Fixer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | correctness | gpt-6.1-sol, high | Codex CLI read-only | 8d53ebc | NOT YET | 3 | 3 | 5 | Claude Opus fixer, Agent tool |
| 1 | fit | Opus 5.5, high | Agent tool (read-only by instruction; snapshot unchanged) | 8d53ebc | CONDITIONAL | 3 | 3 | 3 | Claude Opus fixer, Agent tool |

| Id | Round | Reviewer | Severity | Lead verdict | Evidence | Also raised by |
|---|---|---|---|---|---|---|
| C1 | 1 | gpt-6.1-sol | should-fix | UPHELD | Traced: Back sets localStepRef to "left" for good, so a late running reply is dropped although the step never accepted a read or sent a start; a second visit with failing reads closes without "Close setup?" and Skip sets the dismissed flag. No case covers Back then return | opus fit (F1) |
| F1 | 1 | opus fit | should-fix | UPHELD (same defect as C1; fixed in code, not accepted as residue: the owner was promised the lock's leftovers never reach a customer, and the fix is small) | Same trace as C1 | gpt-6.1-sol (C1) |
| F2 | 1 | opus fit | should-fix | UPHELD | proof.md: the real-server walk ran on index-Bl10hv_a.js; the bundle under review is index-CJbYAiX1.js, after the render-time change in 1def075 | gpt-6.1-sol (noted, section 3) |
| C2 | 1 | gpt-6.1-sol | nit | UPHELD as nit (development only: production React runs the effect once; the fix is a cleanup on the opening effect, cheap and also covers a wizard closed before the reply) | Traced: the opening effect has no cleanup, so StrictMode's replay sends two reads and the older one can be handed after the newer; the committed bundle does wrap the root in StrictMode, so proof.md's statement that it does not is wrong | |
| F3 | 1 | opus fit | nit | UPHELD | BACKLOG.md:691 still ends "reconcile it through the step's start-ordering guard", which the fix no longer uses; the PR number is pending | |
| C3 | 1 | gpt-6.1-sol | nit | UPHELD; lead-made fix (the lead's own spec.md, a whitespace-only line) | `git diff --check 5fb5d1e..8d53ebc` exits 2 on spec.md:20 | |

Round 1 lead-made change: C3, trailing spaces removed from spec.md line 20 (`git diff --check` now exits 0).
Outside L1, from the fit report's observation (not a finding): a late opening reply on the API key step turns a cloud user into a local user and jumps them to Local transcription; behaviour from before this PR, logged as a wave 2 BACKLOG line in the fix round.
Round 2: the fit reviewer does not rejoin. The fixes change no copy or screen; the one behaviour change ("Close setup?" now also asks after a Back and return) is the code option the fit report itself gave for F1, and F3's records wording is checked by the correctness re-check.
