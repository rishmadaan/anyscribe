---
type: feature
tags: [mac-app, desktop, web-ui, security, updater, local-setup]
tldr: "Engine hooks for the Mac app (phase 2a): ANYSCRIBE_APP=1 (read only by core/appmode.is_app) stops skill auto-install (CLI start and onboarding), makes `update` print one line and exit 0, and installs local engines with the app's own pip; hidden `ui --watch-stdin` stops the engine when the app's pipe closes (hard exit after 10 s); GET /api/jobs lists this run's jobs with the title passed as event data; HostCheck now refuses an Origin from any other website, a hole older than the app."
---

# Mac app engine hooks (phase 2a)

## The ask

The owner approved building anyscribe into an installable Mac app (an Electron
shell, web-first like T3 Code), with the CLI kept. Phase 0 proved a test Mac app
can pack Python, yt-dlp and ffmpeg; phase 1's reviewed mockup ("menu bar
direction A") is the binding design. This slice is the engine side only: small,
Python only, testable on Linux. The Electron shell is built separately in
`desktop/`.

## What was built

1. **App mode, one variable.** `ANYSCRIBE_APP=1` means "this engine belongs to
   the Mac app". `core/appmode.py::is_app()` is the only reader, and only the
   exact value `1` counts. Users of it:
   - `cli/main.py`: the callback skips `_auto_update_skill()`. The mockup's rule
     is that starting the engine never installs or updates the Claude Code
     skill; only the app's Terminal switch does.
   - `core/onboard_headless.py`: `run_headless_onboard()` never installs the
     skill, whatever `install_skill` says, so the web wizard and the agent path
     follow the same rule. The response's `skill_installed` reads false.
   - `cli/onboard.py`: the interactive wizard's own skill step
     (`_install_skill_step()`) skips the install too; its summary says "not
     installed (the Mac app's Terminal switch installs it)". (Review round 1.)
   - `core/updater.py`: install type `app`; `update` and `update --check` print
     "This anyscribe came with the Mac app, which updates itself." and exit 0
     without pip or git. `doctor` shows "Install type: Mac app".
   - `core/local_setup.py`: `detect_install_method()` returns `app` first; the
     local engines install and uninstall with `[sys.executable, "-m", "pip",
     ...]`, never the uv fallback. The app sets `PIP_USER=1` and
     `PYTHONUSERBASE`, which phase 0 proved sends pip's writes to the add-ons
     folder instead of the signed app bundle. Progress lines say "via app".
2. **`ui --watch-stdin`** (hidden). Phase 0 found a force-killed app left its
   engine running. The app now holds the engine's stdin; a daemon thread reads
   it to end of file, then does what `POST /api/shutdown` does (removes this
   run's tailnet rule, sets `server.should_exit`), and exits hard if the
   process is still alive 10 s later. The clock starts when stdin ends, before
   the cleanup, so a slow Tailscale call or a failing print cannot hold it (review
   round 1). On POSIX the engine leads its own process group from startup, and
   the hard exit SIGKILLs that group, so pip, yt-dlp or ffmpeg children die with
   it; it never signals a group it does not lead. Elsewhere it calls
   `os._exit(1)`. A thread rather than a signal handler, so it is meant to work
   on Windows; not yet run there. Review round 3 made that hard exit the one
   exit door: SIGTERM and SIGINT handlers (run after uvicorn's graceful stop)
   and a `try/finally` around `server.run()` send every ending through it, so a
   watched engine never leaves pip, yt-dlp or ffmpeg running. In app mode a stop
   is final: running jobs end with the engine. Transcripts are written whole or
   not at all (`core/fileutil.atomic_write`: buffered write, flush, fsync,
   rename), so a stopped job never leaves a cut-off file.
3. **`GET /api/jobs`**: newest first, every pending and running job (even past
   50), then the newest finished jobs up to 50 rows in all, `{job_id, url, status,
   stage, title, error, file_path, created_at, completed_at}`. Clean-up and the
   memory cap never drop an active job, and in app mode finished jobs do not
   expire after an hour (review round 1). The title is passed as
   data on the orchestrator's "download completed" event and copied onto the
   job, and taken from the result on completion; it is never parsed from the
   message text. `web/jobs.py` is the only `on_progress` implementer for
   `process()`, and it already accepted `data=`, so no other caller changed.
   `stage` is the step of the last pipeline event, so a failed job shows where
   it failed (for example `transcribe`).
4. **Origin check.** Planning found that `HostCheck` checked Host (DNS
   rebinding) but not Origin, so any page the user visited could send a
   no-preflight POST to `http://127.0.0.1:8457/api/shutdown` or `/api/upload`.
   Now an Origin header, when present, must name a local host (any port, so the
   Vite dev server at `localhost:5173` still works) or the tailnet name this
   server holds; otherwise 403 (WebSocket close 1008). `Origin: null`, two
   Origin headers and anything but a plain serialized origin (scheme, host,
   optional port; no userinfo or path) are refused (review round 1); requests with no Origin (curl, the CLI, the
   tray's shutdown call) pass as before. The 403 body says "anyscribe does not
   answer requests sent by other websites."

## Decisions (made with the owner's approval of the plan)

- One environment variable, not several.
- The stdin flag is hidden: only the app uses it.
- The title travels as a data field, not text to parse.
- Origin: any local hostname passes, on any port.
- Version stays 0.19.0; the release adds the CHANGELOG entry. Nothing here is
  user-facing, so no user doc or skill change.

## Proof

Each guard was mutation-tested (removed, the test seen failing, restored, seen
passing): the app-mode skill skip, the stdin watch (the real
`python -m anyscribe ui --watch-stdin` subprocess stayed up past 20 s), and the
Origin check (with it removed, a POST carrying `Origin: https://evil.example`
really shut the subprocess engine down). Details in
`docs/reviews/2026-11-20-mac-app-engine-hooks/proof.md`.

## Open for the app build

- (Built in the same slice, after review found it.) The web onboarding wizard
  called `run_headless_onboard()` with its default `install_skill=True`, so
  onboarding inside the app would have installed the skill when `~/.claude`
  existed. The check now sits where the install happens, in
  `run_headless_onboard()`, covering the web wizard and `onboard --yes`; the
  interactive wizard has its own install step, guarded the same way in review
  round 1.
- The app's window must load the dashboard over `http://127.0.0.1:<port>`.
  A `file://` or custom-scheme page would send `Origin: null` or a non-local
  Origin and be refused.
- Requirement: the app's Terminal command (`~/.local/bin/anyscribe`) must
  export `ANYSCRIBE_APP=1`, `PIP_USER=1` and
  `PYTHONUSERBASE=~/.anyscribe/runtime`, the same environment the app gives the
  engine. Without them, `anyscribe update` and the local-engine setup typed in
  Terminal would run pip into the signed app bundle.
- In app mode nothing in the engine refreshes the Claude Code skill after an app
  update (the CLI's own skill update is off there). So the app re-copies the
  skill after each update while the Terminal switch is on.
