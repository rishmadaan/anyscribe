Note: home-folder paths rewritten to `~`.

~~~~
FIT REVIEW, round 1: mac app engine hooks, diff 7ab1539..2dd8e64 on feat/mac-app-engine

1. VERDICT

CONDITIONAL on F1, the job list forgetting finished jobs after one hour, which breaks a menu bar promise in the approved mockup. F1 can be fixed in this slice with one line, or in the shell slice. Also wanted: the F2 wording fix in the journal.

This is the job he asked for. It covers the engine side of the approved Mac app and adds nothing beyond it, apart from two small, justified extras: `doctor` showing "Mac app", and the onboarding skill fix the coordinator added by amendment. Each hook matches a promise in the mockup's "For the build" list:
- "No surprise skill": app mode plus the onboarding guard.
- "One job list": GET /api/jobs.
- "Stop with the app": `--watch-stdin`.
- The Origin fix closes a real hole, and the spec approved it.

The code is small and follows the repo's existing patterns: one place reads the variable, the new route reuses `job_manager`, and the Origin check reuses `HostCheck.allowed`. I found no over-engineering.

2. FINDINGS

F1 (should-fix, CONFIRMED by reading both sides): finished jobs drop out of /api/jobs one hour after they finish, so the menu's "Finished while the window was closed" rows disappear unseen.
- Where: src/anyscribe/web/jobs.py:17 (`JOB_TTL_SECONDS = 3600`). `_cleanup_stale()` runs inside `summaries()` at jobs.py:78, and also in `get()` and `submit()`.
- Mockup section 6, direction A: "Jobs that finish while the window is closed stay in the menu as Saved or Failed until the window is opened". The spec says the menu bar, the quit question, Settings and the update restart "will all read this one list". The shell branch (feat/mac-app-shell, desktop/src/logic.js:136-143 `menuModel`) builds those rows only from the current /api/jobs, filtered by `completed_at >= hiddenSince`, and keeps no memory of its own.
- Scenario: he closes the window at 9:00. A job fails at 9:05 and the menu shows "Failed" with a red dot. At 10:10 the engine has dropped the job, so the menu reads "Ready" with no dot. He never learns it failed.
- The docs overclaim in the same way. architecture.md's "Mac app hooks" section and the journal say "every job this engine run knows" and "this run's jobs", but never mention the one-hour expiry.
- Fix, simplest first:
  (a) Engine: skip the time-based expiry in app mode, `if is_app(): skip the TTL part` in `_cleanup_stale`. The MAX_JOBS 500 cap and the 50-row listing still bound memory, and the shell needs no change.
  (b) Shell: it polls every 2 s, so it can remember finished-while-hidden jobs itself.
  Whichever is chosen, state the expiry, or its absence in app mode, in architecture.md's "Mac app hooks" section.

F2 (should-fix, the code path is CONFIRMED; the signing consequence is PLAUSIBLE): the journal understates what happens if the Terminal command does not set ANYSCRIBE_APP=1.
- Where: docs/building/journal/2026-11-20-mac-app-engine-hooks.md, last "Open for the app build" bullet. It says the shim's choice "decides whether `update` there says 'the app updates itself'; that is the shim's choice, not the engine's."
- What actually happens without the variable, traced:
  - `anyscribe update` from Terminal reaches `updater._pip_update()`, which runs `[sys.executable, "-m", "pip", "install", "--upgrade", "anyscribe"]`. `sys.executable` is the Python packed inside the app (the shell spec puts it at `<resources>/python/bin/python3`). A shell started from Terminal has no PIP_USER, so pip writes into the app bundle itself.
  - `anyscribe local install` from Terminal does the same, via `detect_install_method()`, which would no longer return "app".
  - Every Terminal command also runs `_auto_update_skill()`.
- Writing into a signed bundle very likely breaks its signature: PLAUSIBLE. A packaged run in phase 3 would settle it.
- Fix: reword the bullet to a requirement. The `~/.local/bin/anyscribe` shim must export ANYSCRIBE_APP=1, PIP_USER=1 and PYTHONUSERBASE=~/.anyscribe/runtime, the same as the engine environment in the shell spec. Add a companion bullet: in app mode nothing in the engine refreshes the Claude Code skill after an app update, so the app must re-copy it (for example `anyscribe skill install`) after it updates itself whenever the Terminal switch is on. Otherwise the skill stays at the version installed when he turned it on.

F3 (nit, PLAUSIBLE): "Its own port" depends on the shell reading the engine's printed output, not on the engine.
- Where: src/anyscribe/cli/main.py, the `ui` port scan (`PORT_SCAN_SPAN = 10`).
- In app mode the engine still moves to the next port when its port is busy. The shell guards against this by checking the port first, then matching `http://127.0.0.1:(\d+)` in the engine's output and killing the engine if the port moved (desktop/src/engine.js:192-196).
- That holds only while the printed line stays the same. In the race window, an engine that moved could also begin a tailnet share on the wrong port before it is stopped.
- Fix (optional): in app mode, do not move ports; exit non-zero with the existing "already in use" message. That makes the promise the engine's own, and the output matching can go later.

F4 (nit, CONFIRMED): two claims are worded stronger than their evidence.
- tests/test_engine_process.py's docstring says "The real engine as the Mac app starts it", but the fixture's environment does not set ANYSCRIBE_APP=1. Fix: set it in the fixture's env, or reword the docstring.
- The journal and architecture.md say the stdin thread "behaves the same on Windows" and "also works on Windows". Nothing ran on Windows (proof.md says so). Fix: say "meant to work on Windows; not yet run there".

3. ANSWERS (advice, not findings)
- Simplest thing: yes. `_stop_when_stdin_closes` repeats the shutdown route's few lines (close the share, then `should_exit`) rather than calling the route. Since system.py was out of scope, that is acceptable.
- A release note is worth having. The Origin fix changes behaviour: any page or bookmarklet on another site that calls the local API is now refused. When the release writes its CHANGELOG entry, name this as a security fix. The spec's "nothing user-facing" is true for screens, not for this behaviour.
- The hard exit uses code 1. The shell may report code 1 as a crash ("engine exited with code 1") if it ever observes this exit. It normally won't, because the shell kills the engine itself on stop. A distinct exit code would make the log clearer. Optional.

4. PENDING OWNER CHECKS
- None of the decisions here need him. A real Mac run, force-quitting the packaged app and watching the engine stop, belongs to phase 3, not to him.

5. NOT CHECKED, AND WHAT I INSPECTED
- I ran nothing: no tests, as the brief requires. If F1 is fixed engine-side, the lead can run `.venv/bin/python -m pytest -q tests/test_orchestrator.py -k job_list` plus a new test that sets `completed_at` more than 3600 s back under ANYSCRIBE_APP=1 and asserts the job is still listed. Mutation-check it by removing the `is_app()` skip.
- Not traced: the 10-second hard exit landing during a vault write. vault/writer.py:138 uses a plain `write_text`, not `core/fileutil.atomic_write`, so a hard exit at that exact moment could leave a cut-off transcript that a later run finds and reports as "Already transcribed". The window is microseconds. writer.py is out of this slice; a correctness reviewer should take it.
- Inspected: the whole packet (ask, spec, target, proof-bar, proof, lens, declined.md, nothing reopened); the full source diff plus surrounding code (jobs.py, web/app.py HostCheck and run, cli/main.py _auto_update_skill, ui, update, doctor, updater.py _pip_update, local_setup.py install and uninstall paths, onboard_headless.py, the /api/shutdown route, every on_progress caller, the other skill-copy sites); the docs diff (architecture.md, journal, _index.md, CLAUDE.md) and tests/test_engine_process.py; the mockup's job map and sections 2, 6, 7, 8, 9, 10 and "For the build"; the sibling branch feat/mac-app-shell (spec.md, desktop/src/engine.js port and readiness, logic.js menuModel); the onboarding branches (none touch onboard_headless.py, web/app.py or jobs.py).

Skipped: deep attacks on the Origin check and the race and abort cases, which belong to the correctness reviewer. Risk: F1 is invisible in testing unless someone waits an hour with the window closed.
~~~~
