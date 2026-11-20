Size: M
Sized because: a code PR with no gate: dashboard-only behaviour that reaches customers only with a later PyPI release (the owner gates that), plus copy in the docs; no secrets, money, data loss or unattended automation.
Cap: 2
Packet: v1

| Round | Role | Model, effort | Lane | Target (sha/version) | Verdict | Raised | Upheld | Minutes | Fixer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | correctness | gpt-6.1-sol, high | Codex CLI read-only | bc144d4 | NOT YET | 3 | 3 | 6 | Claude Opus fixer, Agent tool |
| 1 | fit | Opus 5.5, high | Agent tool (read-only by instruction; snapshot unchanged) | bc144d4 | CONDITIONAL | 5 | 5 | 3 | Claude Opus fixer, Agent tool |

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

Round 1 minutes from timestamps: correctness 17:41:19 to 17:46:55; fit 197 s (Agent tool).
