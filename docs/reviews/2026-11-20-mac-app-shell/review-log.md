# Review log: anyscribe Mac app, phase 2b shell
Size: L
Sized because: security boundary (the window's navigation rules and the preload bridge decide what web content can make the app do) plus process control (spawning and stopping the engine)
Cap: 5 (security: the window's navigation rules and the bridge decide what web content can make the app do)
Packet: v1

| Round | Role | Model, effort | Lane | Target (sha/version) | Verdict | Raised | Upheld | Minutes | Fixer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | correctness | gpt-6.1-sol, high | Codex | 880ed2c | NOT YET | 9 | 8 | 7 | opus (Agent tool, the builder) |
| 1 | fit | claude-opus-5-5, high | Claude (Agent tool; ran with this session's instruction files and hooks) | 880ed2c | CONDITIONAL | 12 | 12 | 5 | opus (Agent tool, the builder) |
| 2 | correctness (re-check, the one Astra pass) | gpt-6-astra, high | Codex | 04986cc | NOT YET | 4 | 4 | 5 | opus (Agent tool, the builder) |
| 2 | fit (rejoined: fixes change what the owner sees) | claude-opus-5-5, high | Claude (Agent tool; ran with this session's instruction files and hooks) | 04986cc | CONDITIONAL | 6 | 6 | 4 | opus (Agent tool, the builder) |
| 3 | correctness (re-check after diagnosis) | gpt-6.1-sol, high | Codex | 2383f26 | NOT YET | 1 | 1 | 5 | opus (Agent tool, the builder) |
| 3 | fit (rejoined: menu and quit question changed) | claude-opus-5-5, high | Claude (Agent tool; ran with this session's instruction files and hooks) | 2383f26 | CONDITIONAL | 4 | 4 | 3 | opus (Agent tool, the builder) |
| 4 | correctness (re-check after the third diagnosis) | gpt-6.1-sol, high | Codex | 787bfa1 | GOOD TO GO | 1 | 1 | 4 | none |
| 4 | fit (rejoined: quit and menu wording changed) | claude-opus-5-5, high | Claude (Agent tool; ran with this session's instruction files and hooks) | 787bfa1 | GOOD TO GO | 2 | 2 | 3 | none |

| Id | Round | Reviewer | Severity | Lead verdict | Evidence | Also raised by |
|---|---|---|---|---|---|---|
| C1 | 1 | sol | blocker | UPHELD | engine.js:321 jobs() returns [] on timeout, 500, bad JSON; main.js quit and restart treat that as idle; malformed bodies throw | F2 |
| F2 | 1 | opus | should-fix | UPHELD | same trace as C1 | C1 |
| C4 | 1 | sol | should-fix (lead lowered from blocker: needs two lifecycle calls overlapping; fix is a serialized lifecycle) | UPHELD | engine.js:303 restart claims nothing before its await; stop() clears this.child unconditionally | F3 |
| F3 | 1 | opus | should-fix | UPHELD | engine.js:188-224 _exitedEarly and _crashed relaunch after stop() began | C4 |
| F1 | 1 | opus | should-fix | UPHELD | main.js:285-289 before-quit always prevented, so an idle logout is cancelled | |
| C2 | 1 | sol | should-fix (lead lowered from blocker: needs another anyscribe server to bind the same port inside the start-up second; fix is cheap: the engine reports its pid in /api/health and the shell requires it to match its child) | UPHELD | engine.js _healthy accepts any anyscribe; stop() posts /api/shutdown to whoever answers | |
| C3 | 1 | sol | should-fix (lead lowered from blocker: no bridge escape, the IPC sender check holds; the dashboard is first-party code) | UPHELD | main.js:315 guards will-navigate and window.open only; no will-frame-navigate or will-redirect | |
| C6 | 1 | sol | should-fix | UPHELD | README's ../.venv path resolved against cwd home | |
| C7 | 1 | sol | should-fix | UPHELD | main.js:306 replaces the menu source each poll; engine caps finished rows at 50 | |
| C8 | 1 | sol | should-fix | UPHELD | e2e.js:187 prints GAP and passes even when the flag is present | |
| C9 | 1 | sol | should-fix | UPHELD | main.js:27, engine.js:41 and 162 sync fs calls can throw outside the failure screen | |
| F4 | 1 | opus | should-fix | UPHELD | openAsHidden is not in Electron 44's LoginItemSettings; settings.json duplicates the system's login state | |
| F5 | 1 | opus | should-fix | UPHELD | hiddenInset with no drag region in today's dashboard | |
| C5 | 1 | sol | blocker | REFUTED | the only submitter to this engine is its own window (CLI, MCP and Claude Code run their own process); a submission and a menu-bar quit cannot both be made by one person in the same instant; declined in docs/reviews/declined.md | |
| F6 | 1 | opus | nit | UPHELD | separators and header style vs mockup section 6 | |
| F7 | 1 | opus | nit | UPHELD | e2e "login launch" is a --hidden launch | |
| F8 | 1 | opus | nit | UPHELD | version in desktop/package.json and pyproject.toml; deferred to phase 3 packaging, recorded in the journal | |
| F9 | 1 | opus | nit | UPHELD | remove the no-flag fallback; the shell merges after 2a | |
| F10 | 1 | opus | nit | UPHELD | dev creates ~/.anyscribe/runtime/lib/python3.13 in the real home | |
| F11 | 1 | opus | nit | UPHELD | quit question has no parent and may open behind | |
| F12 | 1 | opus | nit | UPHELD | default Electron app menu; deferred to phase 3, recorded in the journal | |
| A1 | 2 | astra | should-fix | UPHELD | engine.js _waitReady accepts readiness after the child's exit was recorded; reproduced read-only | |
| A2 | 2 | astra | should-fix | UPHELD | engine.js _stopNow posts /api/shutdown to whoever holds the port after verification; PLAUSIBLE timing, design gap | |
| A3 | 2 | astra | should-fix | UPHELD | AppLog: appendability never checked before spawn; error latched; reproduced read-only | G6 |
| G6 | 2 | opus | nit | UPHELD | engine.js:52-60 error never cleared; Try again cannot succeed | A3 |
| A4 | 2 | astra | should-fix | UPHELD | restart() adopts the stop's new generation; reproduced read-only | |
| G1 | 2 | opus | should-fix | UPHELD | logic.js:152-157 the 5-row cap can hide the failed job; reproduced with a node one-liner | |
| G2 | 2 | opus | nit | UPHELD | any question during logout cancels it; undisclosed | |
| G3 | 2 | opus | nit | UPHELD | waiting and quitting rows uncapped | |
| G4 | 2 | opus | nit | UPHELD | the unknown-list box lacks Quit When Done; the menu keeps a stale list with no word that the engine is not answering | |
| G5 | 2 | opus | nit | UPHELD | journal names decideQuit and roll-forward | |
| S3-A1 | 3 | sol | should-fix | UPHELD | engine.js _cancel leaves restartRequested set, so stop() during a restart's termination wait relaunches; reproduced read-only. Reachable only through stop(), which main.js never calls (stopForQuit is protected) | |
| G7 | 3 | opus | should-fix | UPHELD | main.js:288-291 cancels one job at a time with 2 s timeouts and no visible change; about 18 s with 8 jobs and an unanswering engine | |
| G8 | 3 | opus | nit | UPHELD | two bare "and N more" lines read as more failures | |
| G9 | 3 | opus | nit | UPHELD | "Ready · not answering" contradicts itself | |
| G10 | 3 | opus | nit | UPHELD | main.js:300 dead branch since G4 | |
| S4-A1 | 4 | sol | nit | UPHELD | desktop/README.md:103 says the idle header reads Not answering even when a finished summary shows | |
| G11 | 4 | opus | nit | UPHELD | engine.js:438-439 two blank lines | |
| G12 | 4 | opus | nit | UPHELD | a stopped-overtaken restart reports "The engine didn't start."; unreachable today (no production stop() caller); a 2c note | |

Round 2 plan: correctness re-check (the one Astra pass) and fit rejoins (fresh Opus) because the fixes change what the owner sees.

Cap corrected from 3 to 5 (independent-review step 1: L reviews in the security class cap at 5). Round 2 not clean (A1 to A4, G1 UPHELD should-fix). At L, round 3 starts with a diagnosis read; the lead's choice goes into spec.md.

Round 3 plan: correctness re-check after the diagnosis (Sol, high) and fit rejoins (fresh Opus) because G1, G3 and G4 change the menu and the quit question.

Round 3 not clean (S3-A1, G7). Round 4 starts with a diagnosis read (cap 5, security class).

Round 4 plan: correctness re-check after the third diagnosis (Sol, high) and fit rejoins (fresh Opus): Stop and Quit and the menu wording change what the owner sees.

Round 4 clean: S3-A1 and G7 to G10 FIXED; only nits raised. Review closed at 787bfa1 (code); review files after it.

Residue for Rishabh to pick (nits, none blocking): S4-A1 README wording; G11 a stray blank line; G12 a restart-reason wording for slice 2c; an engine backlog item from the round 4 fit report (interrupted downloads stay in ~/.anyscribe/tmp because a SIGKILL skips the per-job cleanup; sweep the folder at engine start). Also: the 39 ms Stop and Quit figure measures app exit against the fake engine, not the end of real transcription work (the engine's own grace is up to 10 s).

Relay note: the fit seats were Claude-lane reviewers (claude-opus-5-5) that ran with this session's instruction files and hooks loaded; correctness seats were GPT (Sol rounds 1, 3, 4; Astra round 2). Diagnoses: claude-fable-5-2 before rounds 3 and 4.

Pending checks on a real Mac (builder or lead first, then Rishabh judges): idle logout and shutdown complete; a launch at login opens no window; Login Items approval state; the quit question with real jobs (all three choices); window dragging with the default title bar; the three Dock modes; native menu header style; tray dots in light and dark.

## Cost (phlinux, 2026-11-20 18:20)

| Round | Codex runs | Codex tokens used | Codex minutes | Claude agents | Claude fresh+out tokens | Claude minutes |
|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0.0 | 1 | 3,006,756 | 262.4 |
| 1 | 1 | 163,808 | 6.8 | 1 | 179,216 | 4.9 |
| 2 | 1 | 147,712 | 4.7 | 1 | 184,481 | 4.4 |
| 3 | 1 | 192,282 | 4.7 | 2 | 317,653 | 6.1 |
| 4 | 1 | 147,473 | 3.9 | 2 | 252,006 | 4.0 |

A round run on the other machine is added by running this there. Claude usage counted once per message id; Codex tokens are the last figure Codex prints. A duration shown as ? could not be measured (no rollout file or no timestamps): unknown, not zero. Codex children in T3 and anything on the other machine are not counted here. The lead's own tokens are not separable and are not counted.
