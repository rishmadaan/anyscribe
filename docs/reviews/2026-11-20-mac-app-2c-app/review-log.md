# Review log: anyscribe Mac app, phase 2c-app
Size: L
Sized because: writes and moves files the owner owns (~/.local/bin, shell profiles, the Claude Code skill) and removes the old launcher: data loss class; new bridge members widen what web content can ask the app to do
Cap: 5 (data loss and security: owner files and the bridge)
Packet: v1

| Round | Role | Model, effort | Lane | Target (sha/version) | Verdict | Raised | Upheld | Minutes | Fixer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | correctness | gpt-6.1-sol, high | Codex | 867e61a | NOT YET | 6 | 6 | 6 | opus (Agent tool, the builder) |
| 1 | fit | claude-opus-5-5, high | Claude (Agent tool; ran with this session's instruction files and hooks) | 867e61a | CONDITIONAL | 6 | 6 | 6 | opus (Agent tool, the builder) |
| 2 | correctness (re-check, the one Astra pass) | gpt-6-astra, high | Codex | 98ea8ac | NOT YET | 4 | 4 | 6 | opus (Agent tool, the builder) |
| 3 | correctness (re-check after diagnosis) | gpt-6.1-sol, high | Codex | 59c4e3d | NOT YET | 3 | 3 | 6 | opus (Agent tool, the builder) |
| 4 | correctness (re-check after the second diagnosis) | gpt-6.1-sol, high | Codex | 1f2e27f | NOT YET | 1 | 1 | 5 | opus (Agent tool, the builder) |
| 5 | correctness (re-check after the third diagnosis; the cap) | gpt-6.1-sol, high | Codex | 5634e13 | NOT YET | 1 | 1 | 6 | opus (Agent tool, the builder; fix built, not re-reviewed) |

| Id | Round | Reviewer | Severity | Lead verdict | Evidence | Also raised by |
|---|---|---|---|---|---|---|
| C1 | 1 | sol | blocker | UPHELD | partial old install (no desktop.json, login item and live tray on 8470): app picks 8470; desktop uninstall's stop_tray posts /api/shutdown to it | F2 |
| F2 | 1 | opus | blocker (lead raised: same defect as C1) | UPHELD | same trace as C1 | C1 |
| C2 | 1 | sol | should-fix | UPHELD | preload unsubscribe races main's held-file delivery; webContents.send is not a receipt | |
| C3 | 1 | sol | should-fix | UPHELD | skillState reads "installed" from an old SKILL.md after a failed --force install | |
| C4 | 1 | sol | should-fix | UPHELD | the new ownership hash is recorded before the replacement is written; a failed write leaves ours looking foreign | |
| C5 | 1 | sol | should-fix | UPHELD | startAtLoginCarriedOver reported true without reading the system state back (requires-approval) | |
| C6 | 1 | sol | should-fix | UPHELD | installed ignores a live old tray when the launcher and plist are gone | |
| F1 | 1 | opus | should-fix | UPHELD | status cannot say whether Switch will work (copy first elsewhere on PATH; uv copy with ~/.local/bin off PATH) | |
| F3 | 1 | opus | should-fix | UPHELD | skill not refreshed after an app update; the command embeds the Python path; recorded only in proof.md | |
| F4 | 1 | opus | should-fix | UPHELD (as a merge rule) | hiddenInset needs 2c-ui's drag strip and padding | |
| F5 | 1 | opus | nit | UPHELD | the app's port moves after the old launcher is removed; per-port local storage resets | |
| F6 | 1 | opus | nit | UPHELD | addToPath ok true while the line is ineffective | |
| A1 | 2 | astra | blocker | UPHELD | a stale server.pid reused by the app's engine passes the port guard; stop_tray terminates it by pid | |
| A2 | 2 | astra | blocker | UPHELD | a binary LaunchAgent plist: the app's XML read finds no port, plistlib resolves 8470 and the uninstall posts shutdown to the app's engine | |
| A3 | 2 | astra | should-fix | UPHELD | fixed temp paths (anyscribe.anyscribe-tmp, terminal.json.tmp) written without exclusive create; a pre-existing file or symlink is overwritten | |
| A4 | 2 | astra | should-fix | UPHELD | the record save after the command rename can fail (runtime folder unwritable from the start); the new command then reads as foreign | |
| B1 | 3 | sol | should-fix | UPHELD | stop() during the uninstall step settles the run and clears restartPending while the uninstaller still runs; start() checks neither; no production caller of stop() | |
| B2 | 3 | sol | should-fix | UPHELD | the uninstaller is detached and neither killed nor awaited on quit; a quick reopen has no reservation (PLAUSIBLE timing) | |
| B3 | 3 | sol | nit | UPHELD | removal.e2e.js expects the Linux loginItem result on every platform | |
| D1 | 4 | sol | should-fix | UPHELD | the old tray's own SIGTERM teardown posts /api/shutdown to its port; with the binary-plist collision (app and old tray both on 8470) a normal quit and quick reopen can let it reach the new engine; traced, timing not reproduced | |
| E1 | 5 | sol | should-fix | UPHELD | the tray-argument regex takes the first port option and misses -pN; Click takes the last repeated option and accepts -p8470; reproduced: `--port 8457 --port 8470` and `-p8470` both pick 8470 | |

Round 2 plan: correctness re-check (the one Astra pass). Fit does not rejoin: this slice has no screens of its own; its screen-facing contract changes are reviewed with 2c-ui.

Round 2 not clean (A1, A2 blockers; A3, A4 should-fix). Round 3 starts with a diagnosis read.

Round 3 plan: correctness re-check after the diagnosis (Sol, high). Fit does not rejoin (no screens in this slice).

Round 3 not clean (B1, B2 should-fix). Round 4 starts with a diagnosis read.

Round 4 plan: correctness re-check after the second diagnosis (Sol, high). Fit does not rejoin (no screens in this slice).

Round 4 not clean (D1). Round 5 (the cap) starts with a diagnosis read.

Round 5 plan (the cap): correctness re-check after the third diagnosis (Sol, high). Fit does not rejoin (no screens in this slice).

Round 5 is the cap and was not clean (E1, a code leftover). Under step 7 at the cap: E1's fix is built by the fixer and goes to Rishabh once with its exact diff; no further review round without his yes (`over cap: round 6 approved by Rishabh`).

Closed (2026-11-21): the owner chose to accept E1's fix (53afdbe) on the lead's verification instead of an over-cap round 6. Lead-verified: E1's tests pass in `npm test`, the e2e and the removal e2e (proof.md "Round 5 leftover fix (E1, not re-reviewed)"); not re-reviewed. Residue for a Mac: plutil read, real LaunchAgent and tray removal, Login Items approval, Dock drop and Open With.
