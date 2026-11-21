# Diagnosis, round 3 (claude-fable-5-2, read-only, Agent tool), summary of its findings

Why the fixes kept missing: the supervisor decides from remembered snapshots instead of from the child process, and each snapshot needs a hand-placed re-check after every await. `gen` has two meanings (user cancellation and launch identity) and `_stopNow()` bumps it, so `restart()` cannot hold a cancellation identity (A4). A child's exit is handled two ways (noted before ready, acted on after), and A1 is the gap at the handover. `verified` and `log.error` are past facts reused later (A2, A3); a port can never be bound to a process for longer than an instant, so A2 cannot be fixed by another check.

What the tests miss: real processes on real ports with sleeps reach only the interleavings timing happens to produce; spawn, fetch and kill cannot be swapped, so no test can hold a reply open and fire an event meanwhile; one test per finding, no command-by-state coverage; assertions on end states, never invariants; a test pokes engine.gen and engine.child directly.

Smaller design: main.js never calls stop(); closing stdin already does what POST /api/shutdown does (and SIGTERM ends the same way), so the HTTP shutdown is redundant and deleting it closes A2. One run record per launch replaces the queue and generations. Recommendation and tests are in spec.md "Round 3 design".
