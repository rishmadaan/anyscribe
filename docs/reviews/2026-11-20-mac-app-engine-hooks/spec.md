# Spec: phase 2a, engine hooks for the Mac app

The Mac app (an Electron shell, built separately in desktop/) starts this engine with `python -m anyscribe ui ...` from a Python packed inside the app, shows the dashboard in its window, and reads the engine's state for its menu bar. This slice adds the engine-side hooks it needs. Small, Python only, testable on Linux.

## 1. App mode: the environment variable ANYSCRIBE_APP=1
Means "this engine belongs to the Mac app". Read it in one place (a tiny helper, for example `core/appmode.py: def is_app() -> bool`), used by:
- `cli/main.py` callback: skip `_auto_update_skill()` in app mode. Mockup rule: starting the engine never installs or updates the Claude Code skill; only the app's Terminal switch does.
- `core/updater.py`: install type "app". `anyscribe update` and `anyscribe update --check` print one line, "This anyscribe came with the Mac app, which updates itself.", and exit 0 without running pip or git.
- `core/local_setup.py`: `detect_install_method()` returns "app" in app mode, checked first. Installing and removing the local engines uses the plain `[sys.executable, "-m", "pip", ...]` command (the app's environment sets PIP_USER=1 and PYTHONUSERBASE so pip writes to the add-ons folder, proven in phase 0). The progress log line names "app".

## 2. `anyscribe ui --watch-stdin` (hidden from --help)
The engine shuts down when its standard input reaches end of file. The app holds the other end of that pipe, so if the app dies, even force-killed, the engine follows (phase 0 found a force-killed app left the engine running). Shut down through the same path as POST /api/shutdown (tailnet rule cleanup included); if the process is still alive 10 seconds later, exit hard. Must not break on Windows (a thread reading stdin is fine). Without the flag, nothing changes.

## 3. GET /api/jobs
Every job this engine run knows, newest first, at most 50: `{job_id, url, status, stage, title, error, file_path, created_at, completed_at}`.
- status: the JobStatus value (pending, running, completed, failed, cancelled).
- stage: the step of the job's last progress event (download, transcribe, write, index, cached, ...), null before any.
- title: null until known. The orchestrator passes it as data on the "download completed" event, `on_progress("download", "completed", msg, data={"title": download.title})`; web/jobs.py copies `data["title"]` onto the job. Never parse it out of the message text. Also set it from the result on completion. Grep every on_progress implementer first and keep each one working.
- error and file_path: null unless failed or completed.
The menu bar, the quit question, Settings and the update restart will all read this one list.

## 4. Refuse requests sent by other websites (pre-existing hole, found in planning)
`HostCheck` in web/app.py checks the Host header (DNS rebinding) but not the Origin header, so any web page the user visits can send a no-preflight POST to http://127.0.0.1:8457/api/shutdown or /api/upload. Add: when an Origin header is present (HTTP and WebSocket), its hostname must be one of LOCAL_HOSTS (any port; the Vite dev server at localhost:5173 proxies with the browser's Origin) or the tailnet name this server currently holds; otherwise 403 (WebSocket: close 1008, as for a bad Host). `Origin: null` is refused. No Origin header (curl, the CLI, server-to-server) passes as today.

## 5. Docs (the repo's rules, AGENTS.md and docs/building/COMMIT_CHECKLIST.md)
`docs/building/architecture.md`: a short "Mac app hooks" section (the variable, the flag, /api/jobs, the Origin rule). A journal entry `docs/building/journal/2026-11-20-mac-app-engine-hooks.md` plus its row in `docs/building/_index.md`. No user-doc, skill or CHANGELOG change (nothing user-facing; the release adds the CHANGELOG entry).

## Decisions already made (do not reopen)
One environment variable, not several. Hidden flag for stdin. Title as a data field. Origin: any local hostname passes, any port. Version stays 0.19.0.

## Left to the builder
Names of helpers and tests, where the stdin thread lives, the hard-exit mechanism.

## Round 3 design (the lead's choice after the diagnosis; binding)

Two invariants, tested as such:
1. A transcript's final path only ever holds the whole content (or the previous content), never part of it.
2. When the app's engine (`--watch-stdin`) ends, by any route, nothing it started is still running.

A. `core/fileutil.atomic_write`: create the temporary file in the same folder with `open(tmp, "xb")` on a hidden, unique name (for example `.<name>.<random>.tmp`), so it is created with the user's normal permissions (umask applies, as `write_text` did) instead of mkstemp's 0600; write the bytes through that buffered file object, `flush()`, `os.fsync()`, close, then `os.replace(tmp, path)`; on any exception, unlink the temp and re-raise. Keep the `encoding` parameter. No hand-written write loop, never `buffering=0`.

B. Engine, `--watch-stdin` only (CLI, MCP and Claude Code paths unchanged): one exit door. `_exit_hard()` kills the engine's own process group when the engine leads it (else `os._exit`). Install SIGTERM and SIGINT handlers that let uvicorn's graceful shutdown run (so the tailnet rule is still removed) and end in `_exit_hard()`; wrap `server.run()` in `try/finally: _exit_hard()`; the stdin timer stays. Make the engine a group leader only if it is not one already (the shell will start it as a session leader, where `os.setpgrp()` raises): `if os.getpgid(0) != os.getpid(): os.setpgrp()`, guarded.
Decision on jobs: in app mode a stop is final. The app asks before quitting while jobs run; once it stops the engine, running jobs end with it. Write this down in architecture.md.

C. Shell (slice 2b): spawn the engine with `detached: true` (its own group from birth) and stop it by killing the group (`process.kill(-pid, ...)`), falling back to the pid. Built in the shell's branch.

Tests (real behaviour, not mirrors of the patch):
- A: in a subprocess, set `RLIMIT_FSIZE` to 64 KB and `atomic_write` 1 MB over a file holding "old": it raises, the file still reads exactly "old", no temp remains (skip where RLIMIT_FSIZE is unavailable). Also: a transcript written through it has the same permission bits a plain `write_text` gets under the same umask.
- B: the real `run(watch_stdin=True)` in a subprocess with a `sleep 300` child held by a daemon thread, parametrized over stdin close, SIGTERM, both together (the shell's quit), and a server held past the deadline; each asserts the engine's group is gone (`os.killpg(pgid, 0)` raises ProcessLookupError) and stops anything left by its own pid. Mutations: drop the signal handler (SIGTERM case fails); drop the finally (stdin case fails); drop the group kill.
- Replace the old raise-midway write test and update the stop test that expected exit code 0.

## Round 4 design (the lead's choice after the second diagnosis; binding)

atomic_write's contract, as one list:
1. The final path only ever holds the whole new content or the whole old content.
2. The temporary file is never more readable than the final file at any moment: created with its final mode in os.open itself.
3. An existing file keeps its exact permission bits.
4. A new file is created private (0600) by default, exactly as mkstemp made every caller's new files before this branch. The transcript writer alone asks for the platform default (`new_mode=0o666`, narrowed by the umask), exactly as Path.write_text gave transcripts before. So every caller's permissions match the baseline.
5. Buffered write, flush, fsync, then os.replace; the temp is removed on any failure; the open stays outside the try.

Shape: `mode = existing bits, else new_mode` (parameter `new_mode: int = 0o600`); `fd = os.open(tmp, O_WRONLY | O_CREAT | O_EXCL | getattr(os, "O_BINARY", 0), mode)`; for an existing file `os.chmod(tmp, mode)` straight after creation, before any byte (undoes umask narrowing, never wider than the target); then `os.fdopen(fd, "wb")`, write, flush, fsync, close, `os.replace`. Keep the hidden `.name.hex.tmp` name and the `encoding` parameter. Never call os.umask.

Tests (mutation-tested): the temp's mode observed at fdopen and at fsync is 0600 for an existing 0600 target under umask 022 (mutants: open "xb" at the umask default; create wide then chmod); a new file through the default is 0600; a new transcript is 0644 under umask 022 and 0664 under 002; an existing 0664 file under umask 022 stays 0664; the RLIMIT short-write test and temp removal still pass.
