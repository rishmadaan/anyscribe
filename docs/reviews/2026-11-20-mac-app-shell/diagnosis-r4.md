# Diagnosis, round 4 (claude-fable-5-2, read-only, Agent tool), summary

S3-A1: keep stop() (12 test call sites and the afterEach invariant check rely on it; stopForQuit sets a permanent flag and would bypass the gates those tests prove). One-line fix in stop(): an explicit stop revokes a restart's pending relaunch (`if (this.run) this.run.restartRequested = false;`) before `_cancel`; it cannot live in `_cancel()` because restart() sets the flag and then calls `_cancel()` itself. The overtaken restart() returns ok false.

G7: do not cancel at all. Jobs live only in the engine's memory, cancel is cooperative (a flag read at the next progress event), and the engine's stop (stdin plus SIGTERM) ends every job milliseconds later, so the cancels change nothing that survives and only add waiting. stopAndQuit becomes finalQuit(); delete engine.cancelJob, the jobs read before it, and G10's dead line. G8 and G9 wording fixes stand as written.
