# Architecture

**Last updated:** 2026-10-22 (v0.18.0)

## Overview

anyscribe has three entry surfaces but one shared core. The CLI, the Web UI,
and the Claude Code skill (via MCP) all funnel into the same orchestrator, which
runs a fixed pipeline:

```
   three ways in            ┌─────────┐ ┌────────┐  ┌──────────────┐
                            │   CLI   │ │ Web UI │  │  Claude Code │
                            │anyscribe│ │ React+ │  │   skill/MCP  │
                            │         │ │FastAPI │  │              │
                            └────┬────┘ └───┬────┘  └──────┬───────┘
                                 └──────────┼──────────────┘
                                            ▼
                              ┌───────────────────────────┐
   one shared core            │  core/orchestrator.process │
                              └─────────────┬─────────────┘
                                            ▼
   0. dedup       ┌────────────────────────────────────────────────┐
    (unless       │ scan vault frontmatter for a matching `source:` │
     --force)     │ hit → return existing file, cached=True, stop   │
                  └───────────────────────┬────────────────────────┘
                                          ▼
   1. download    ┌────────────────────────────────────────────────┐
                  │ registry picks downloader (first match wins):   │
                  │   local file → YouTube + Instagram (both yt-dlp) │
                  └───────────────────────┬────────────────────────┘
                                          ▼
   2. prepare     ┌────────────────────────────────────────────────┐
      audio       │ 16 kHz · mono · 64 kbps mp3                     │
                  │ chunk if >25 MB or >30 min (18-min parts, 5s ov)│
                  └───────────────────────┬────────────────────────┘
                                          ▼
   3. transcribe  ┌────────────────────────────────────────────────┐
                  │ one of 7 providers (cloud API or local Whisper) │
                  │ openai · deepgram · elevenlabs · sargam · ...    │
                  └───────────────────────┬────────────────────────┘
                                          ▼
   4. write       ┌────────────────────────────────────────────────┐
                  │ markdown → ~/anyscribe vault                    │
                  │ frontmatter + body (clean/timestamped/diarized) │
                  └───────────────────────┬────────────────────────┘
                                          ▼
   5. index       ┌────────────────────────────────────────────────┐
                  │ update _index.md MOC + daily log                │
                  └────────────────────────────────────────────────┘
```

Downloaded media lands *outside* the vault (in `~/.anyscribe/downloads/`) so
the Obsidian vault at `~/anyscribe/` stays pure markdown.

## Layers

### CLI Layer (`cli/`)
- Typer app with `rich_markup_mode="rich"`, custom `DefaultToTranscribe(TyperGroup)` class for bare-URL routing
- Primary command: `anyscribe` (aliases: `scribe`, `ascli` for backward compat)
- Commands: `onboard`, `transcribe`, `download`, `batch`, `rm`, `logs`, `config`, `providers`, `local`, `model`, `ui`, `tray`, `desktop` (`install`/`uninstall`/`status`/`open`), `install-service`, `uninstall-service`, `update`, `doctor`, `install-skill`, `migrate`
- **Tray supervision model** (`cli/tray_cmd.py` + `core/tray.py`): `anyscribe tray` is a `pystray` menu-bar icon that supervises `anyscribe ui` as a subprocess — attaches only to a listener that identifies itself as anyscribe on `/api/health` (another program on the port is left alone), runs as a single instance by holding a lifetime OS lock on `~/.anyscribe/tray.lock` (not the pidfile, which only records the pid), and tears down via a `signal.pthread_sigmask` + `signal.sigwait` watcher thread rather than a plain `signal.signal` handler (pystray's macOS Cocoa event loop can block Python bytecode from running, so a normal handler can miss SIGTERM/SIGINT). The signal watcher and `preexec_fn` are POSIX-only and skipped on Windows (`os.name != "nt"`); a second tray exits 0 ("already running") so a `KeepAlive` login item does not relaunch-loop. `core/tray.py::stop_tray(port)` POSTs `/api/shutdown`, SIGTERMs the pidfile pid and the recorded server pid (`server.pid`), and removes both files. `core/service.py` writes the login item (`anyscribe install-service`) that runs `{python} -m anyscribe tray --port N` at login on macOS, Windows and Linux; see "Desktop surface" below.
- Bare URL: `anyscribe "url"` auto-routes to transcribe (first arg not a known subcommand → prepend `transcribe`)
- `--json` and `--quiet` available on main commands (transcribe, download, batch, config show, providers list)
- `--json` for AI agent and scripting integration
- `__main__.py` enables `python -m anyscribe` as alternative entry point (Windows PATH fallback)
- On Windows, app callback checks if `anyscribe` is on PATH; if not, prints the exact PowerShell command to fix it (one-time, uses `.path_warned` marker)

### MCP Layer (`mcp/`)
- `MCPServer` (MCP Python SDK v2, protocol revision `2026-07-28`) with the
  `anyscribe-mcp` entry point, stdio transport (`scribe-mcp` is a permanent alias)
- 10 tools: transcribe, batch_transcribe, download, list_transcripts, delete_transcript, get_config, set_config, list_providers, test_provider, doctor
  - `transcribe` / `batch_transcribe` accept `quality` (accuracy|balanced|cost|free) and `force`; `force` bypasses the dedup check
- 3 resources: scribe://config, scribe://providers, scribe://workspace — these are
  addresses, not display names, so the anyscribe rename deliberately left them alone
- Calls core modules directly (orchestrator, settings, providers) — not CLI commands
- All tools return JSON, consistent error format
- Optional dependency: `pip install anyscribe[mcp]` (adds `mcp>=2,<3`). **The upper
  bound is load-bearing.** SDK v2 deleted `mcp.server.fastmcp` outright; the previous
  unbounded `mcp>=1.0` resolved straight onto it and broke every fresh install of the
  extra. Any future major bump gets migrated deliberately, never resolved into.
- CI installs `.[dev,mcp]`, not `.[dev]` — without the extra, `tests/test_mcp_providers.py`
  hits its `importorskip` and this whole layer goes untested

### Web UI Layer (`web/` + `ui/`)
- FastAPI backend serving a built React SPA at `127.0.0.1:8457`
- Launched via `anyscribe ui` — core dependency, not optional
- REST API (`web/routes/*.py`):
  - Config/keys: GET/PUT `/api/config`, GET `/api/providers`, GET `/api/providers/{name}/languages`, POST `/api/providers/{name}/test`, GET `/api/keys/status`, PUT `/api/keys`, DELETE `/api/keys/{provider_name}`
  - Jobs: POST `/api/upload`, POST `/api/transcribe`, GET `/api/jobs` (every active job, then the newest finished, 50 rows in all), GET `/api/jobs/{job_id}`, POST `/api/jobs/{job_id}/cancel`
  - History: GET `/api/transcripts`, GET/DELETE `/api/transcripts/{transcript_id}`, GET `/api/workspace/info`
  - System: GET `/api/health`, GET/PUT `/api/autostart`, GET/PUT `/api/tailnet`, POST `/api/shutdown`
  - Local: GET `/api/local/status`, GET `/api/local/setup/log`, POST `/api/local/setup` (`{model, also}`: the background setup queues `also` itself), POST `/api/local/choose` (`{model, also}`: one server-side pending default; the download queue's worker switches `local_model` only once the model is `runnable()`, a failure keeps the old default; a later call replaces it; reported as `pending_default` in status), POST `/api/local/teardown`. Readiness everywhere is `providers/local_models.runnable()` (engine imports, weights complete, Parakeet's Tiny + VAD too); `cached` means weights only (sizes, disk maths). `config_set.set_value('local_model', X)` refuses a change to a model that isn't runnable: the one guarded switch for CLI, Web and MCP
  - Models: GET `/api/models/local`, POST `/api/models/local/{size}/pull`, POST `/api/models/local/{size}/reinstall`, DELETE `/api/models/local/{size}`
  - Onboarding: GET `/api/onboarding/status`, POST `/api/onboarding/save`
- WebSocket: `/api/ws/jobs/{job_id}` for real-time transcription progress
- JobManager runs `process()` in ThreadPoolExecutor, bridges to async via `asyncio.Queue` + `call_soon_threadsafe`
- Orchestrator's `on_progress` callback emits `ProgressEvent` at each pipeline step (download, transcribe, write, index)
- Frontend: React 19 + TypeScript + Vite + Tailwind CSS v4, builds to `web/static/`
- SPA routing: catch-all `/{full_path:path}` serves `index.html` for non-API paths
- Server stashed on `app.state.server` for graceful `/shutdown` via `server.should_exit = True`
- Busy port: `anyscribe ui` rolls forward up to 10 ports (clamped to 65535) and only errors when all are busy
- Tailnet sharing (optional, `settings.tailnet`, default off; `ui --tailnet` / `--local-only` per run via `core.tailnet.run_override`): the bind stays `127.0.0.1`; `web.app.run` registers a startup handler that starts a short thread: it waits for `server.started` (uvicorn runs startup handlers before it binds, and runs shutdown handlers on a bind failure), then calls `core/tailnet.py` `Share.apply(True)` (runs `tailscale serve --bg --https=<port> http://127.0.0.1:<port>` for the port actually chosen). The shutdown handler calls `Share.close()`, and `/api/shutdown` calls it before setting `should_exit`. Uvicorn runs shutdown handlers on SIGINT and SIGTERM before re-raising the signal, so every clean stop removes the rule; SIGKILL leaves it (documented limit). `run()` also installs `HostCheck`, a pure ASGI middleware that answers only Host `127.0.0.1` / `localhost` / `[::1]` and, only while this server holds a share (`share.held`, set when `start()` succeeds and cleared on switch-off, "removed outside anyscribe" and close; it stays set while the display reads failed because Tailscale is down), the exact host of `share.held` (403 otherwise, setting on or off; blocks DNS rebinding, and keeps a leftover or hand-made serve rule from exposing the page while sharing is off). It also refuses an `Origin` header that names any other host (see Mac app hooks). It is not in `create_app()` so TestClient tests keep their "testserver" Host. The `Share` object lives on `app.state.tailnet`; `PUT /api/tailnet` (and `PUT /api/config` with `tailnet`) saves the setting and applies it live. The tray and desktop mode start the server as `python -m anyscribe ui`, so they inherit this with no extra code
- Web tests: `tests/test_web*.py`, `test_autostart_route.py`, `test_keys_status.py`, `test_ui_port.py`, `test_tailnet.py` (FastAPI TestClient; the tailscale CLI faked)

### Desktop surface (`cli/desktop_cmd.py` + `core/desktop.py`, `core/launcher.py`, `core/service.py`)

Desktop mode makes the Web UI reachable without a terminal, using only the
user's own machine: no downloaded app, no signing, no new runtime
dependency. The chain is **launcher → `desktop open` → tray → ui**:

- The **app launcher** (`core/launcher.py`) runs `<python> -m anyscribe desktop open`:
  `~/Applications/anyscribe.app` (Info.plist with `LSUIElement`, a shell-script
  executable, `.icns` made by Pillow + macOS's bundled `iconutil`), a Start-menu
  `anyscribe.lnk` targeting `pythonw.exe` (created through PowerShell's
  `WScript.Shell` COM object), or `~/.local/share/applications/anyscribe.desktop`.
  Icons render from `assets/app-icon.png` into `~/.anyscribe/desktop/`.
- **`desktop open`** (`core/desktop.py::open_dashboard`) opens the browser if
  `/api/health` on the port answers as anyscribe; refuses (exit 1) if another
  program holds the port; otherwise starts the tray (`launchctl kickstart`, no
  `-k`, when the macOS login item serves the port; else spawns `anyscribe tray
  --port N` detached, output to `~/.anyscribe/logs/tray.log`). A live tray whose
  server is gone (dashboard Shutdown) gets `SIGUSR1`, which the tray's sigwait
  loop turns into a server restart; it is stopped and replaced only if that
  fails, and always on Windows (no signals). Then it falls back to a detached
  `anyscribe ui --no-open` if the tray process dies (no display), waits for
  health, then opens the browser or prints the URL to stderr.
- **`desktop install`** (`core/desktop.py::install`) orders the steps by OS. On
  macOS it writes the login item first (`launchctl load`, whose `RunAtLoad`
  starts the tray launchd supervises, so `KeepAlive` restarts it after a crash),
  then `open_dashboard(expect_external=True)` waits up to 10 s for that tray
  before falling back to spawning one. On Windows and Linux the login item only
  takes effect at the next login, so the tray is spawned detached first and the
  login item written after. A reinstall (manifest present) runs `stop_tray`,
  which waits for the old tray to exit and its port to free, then unloads and
  reloads the login item; on macOS an existing plist with no manifest is also
  unloaded first, since `load` on a still-loaded job is a no-op.
- The **tray** supervises the **ui** server as before.
- The **login item** (`core/service.py`) starts the tray at login: a launchd
  LaunchAgent (`com.anyscribe.tray.plist`: `EnvironmentVariables.PATH` from
  `service_path()`, `KeepAlive {SuccessfulExit: false}`, `ThrottleInterval 10`,
  `ProcessType Interactive`, log to `tray.log`), a Startup-folder
  `anyscribe tray.lnk`, or `~/.config/autostart/anyscribe-tray.desktop` with
  `Exec=env PATH=…`. `service_path()` is the installing shell's PATH plus the
  Homebrew, `/usr/local/bin`, `~/.deno/bin`, `~/.local/bin` and interpreter
  directories, since login-started processes get a minimal PATH. Removing a
  login item never stops a running tray (on macOS it skips `launchctl unload`
  while a tray is alive, because unload would kill the dashboard the Startup
  toggle sits in).
- The **manifest** `~/.anyscribe/desktop.json` (`version`, `python`, `port`,
  `launcher`, `login_item`, `installed_at`) is written last; `desktop status`
  reads it and reports `healthy: false` with a reason (recorded Python gone,
  launcher or login item missing, or a launcher/login item with no manifest:
  "Partly installed").

`desktop install` order: icons → launcher → then on macOS the login item first,
and launchd starts the tray from it (so KeepAlive supervises it); on Windows and
Linux the tray is spawned first (unless `--no-launch`), then the login item →
manifest; a re-install first stops the old tray
and removes the old login item. `desktop uninstall` stops the tray and server,
then removes launcher, login item, icons and manifest; it never touches the
vault, config or keys. The three core modules keep every artifact's text in a
**pure render function** (`render_app_script`, `render_info_plist`,
`render_desktop_entry`, `render_shortcut_script` in `launcher.py`;
`render_plist`, `render_autostart_entry` in `service.py`), so each OS's output
is unit-tested on every OS; `ci.yml`'s `desktop-platforms` job runs the
real-OS tests (`iconutil`, `.lnk` creation) on macOS and Windows. The
installers end with `desktop install --yes` unless `--no-desktop` /
`-NoDesktop`. The skill and MCP server never depend on any of this: they run
the pipeline in-process, and the dashboard reads history from the vault.

### Mac app hooks (`core/appmode.py`, `ui --watch-stdin`, `GET /api/jobs`, the Origin check)

The Mac app (an Electron shell, built separately in `desktop/`) starts this
engine as `python -m anyscribe ui --watch-stdin ...` from a Python packed inside
the app, shows the dashboard in its window and reads the engine's state for its
menu bar. The engine side is four small hooks:

- **`ANYSCRIBE_APP=1`** means "this engine belongs to the Mac app". Only
  `core/appmode.py::is_app()` reads it (exactly `"1"`). In app mode the CLI
  callback skips `_auto_update_skill()`, `run_headless_onboard()` never
  installs the skill whatever `install_skill` says (web wizard and agent path
  alike; `skill_installed` reads false), and the interactive `anyscribe onboard`
  skips it too (`cli/onboard.py::_install_skill_step()`; its summary says "not
  installed"), since only the app's Terminal switch installs it; `core/updater.py` reports install type `app`, and `update` /
  `update --check` print "This anyscribe came with the Mac app, which updates
  itself." and exit 0 without running pip or git; `core/local_setup.py`'s
  `detect_install_method()` returns `app` first and installs or removes the local
  engines with `[sys.executable, "-m", "pip", ...]`, never uv. The app's
  environment sets `PIP_USER=1` and `PYTHONUSERBASE`, so pip writes to the
  add-ons folder, not into the app bundle. `doctor` shows "Install type: Mac app".
  `anyscribe ui --port N` never moves to another port in app mode (the app
  connects to the port it chose): if N is taken it prints "Port N is already in
  use." and exits 1.
- **`anyscribe ui --watch-stdin`** (hidden from `--help`): a daemon thread reads
  stdin until end of file. The app holds the other end of that pipe, so when the
  app dies, even force-killed, the pipe closes and the engine stops the way
  `POST /api/shutdown` does (removes this run's tailnet rule, then
  `server.should_exit = True`). The 10 s clock starts the moment stdin ends,
  before that cleanup, so a slow Tailscale call or a failing print cannot delay
  or skip it. If the process is still alive when it runs out (a running job or
  open socket holding the graceful stop), it exits hard. On POSIX the engine
  leads its own process group (`os.setpgrp()` at startup; when the app starts it
  detached it is already a session leader, the call fails harmlessly and it still
  leads its group), so its children (pip, yt-dlp, ffmpeg) share its group.
  **One exit door.** With `--watch-stdin` every way the engine ends goes through
  `_exit_hard()`: stdin ending, SIGTERM or SIGINT (handlers installed before
  `server.run()`; uvicorn captures the signal while serving, stops gracefully so
  the tailnet rule is removed, then re-raises it into these handlers), the server
  stopping by itself (`try/finally` around `server.run()`), and the deadline.
  `_exit_hard()` SIGKILLs the engine's group, itself included, only when the
  engine leads it (never the app's group); elsewhere it calls `os._exit(1)`. So a
  watched engine always ends by signal 9 (exit 1 where there are no groups).
  Invariant: when the app's engine ends, by any route, nothing it started is
  still running. The one route the engine cannot see is a SIGKILL of its own pid;
  the app covers that by killing the group. The stdin watch is a thread, not a
  signal, so it is meant to work on Windows; not yet run there.
  **Jobs: in app mode a stop is final.** The app asks before quitting while jobs
  run; once it stops the engine, running jobs (a download, a transcription, a pip
  install) end with it, mid-step. A transcript is either written whole or not at
  all (`core/fileutil.atomic_write`), so a stopped job leaves nothing half-done
  for duplicate detection to mistake for finished.
- **`GET /api/jobs`**: newest first, every pending and running job always (even
  past 50), then the newest finished jobs up to 50 rows in all, as `{job_id, url,
  status, stage, title, error, file_path, created_at, completed_at}`. The job
  manager never drops an active job: finished jobs expire one hour after they
  finish (not in app mode, where the menu keeps "finished while the window was
  closed" rows until the window opens), and the 500-job memory cap evicts the
  oldest finished jobs only. `stage` is the step of the last pipeline progress event;
  `title` arrives as data on the orchestrator's "download completed" event
  (`data={"title": ...}`, never parsed from the message) and from the result on
  completion; `error` and `file_path` are null unless failed or completed. The
  menu bar, the quit question, Settings and the update restart read this list.
- **`GET /api/health` carries `pid`**, the engine process's own `os.getpid()`.
  The app checks it matches the engine it spawned before it loads the page on
  its port or sends `/api/shutdown`, so it never trusts or stops another
  process that happens to answer there.
- **The Origin check** in `HostCheck` (see the Web UI layer): an `Origin` header,
  when present, must be exactly one header holding one serialized origin
  (`http` or `https`, a host, an optional port; no userinfo, path or spaces) and
  name a local host (any port; the Vite dev server proxies with the browser's
  Origin) or the tailnet name this server holds; anything else, `Origin: null`
  and two Origin headers included, gets 403 (WebSocket: close 1008). No Origin
  (curl, the CLI, the tray) passes. This closes a hole older than the app: any
  web page the user visited could send a no-preflight POST to `/api/shutdown` or
  `/api/upload`. The app's window must load the dashboard from
  `http://127.0.0.1:<port>`, so its requests carry a local Origin.

Tests: `tests/test_app_mode.py`, `tests/test_engine_process.py` (the real
engine as a subprocess with a throwaway HOME and a free port), the jobs-list
tests in `tests/test_orchestrator.py`, the Origin tests in `tests/test_tailnet.py`.
Journal: `2026-11-20-mac-app-engine-hooks.md`.

### Mac app shell (`desktop/`)

The Mac app (in development; packaging comes later) is an Electron shell that
owns one engine: it starts `python -m anyscribe ui --port N --no-open
--watch-stdin` as its child and shows the dashboard from that server in its own
window. Nothing in `src/` depends on it; the engine only learns it runs inside
the app from `ANYSCRIBE_APP=1`. Plain JavaScript, Electron 44.9.3 pinned, no
other dependencies; `desktop/README.md` has the run instructions and the
bridge contract.

- `src/logic.js`: pure decisions, unit-tested: the port (8470, or 8471 when
  `desktop.json` records 8470, so it never collides with desktop mode), the
  engine environment (built from scratch; packaged PATH is `<resources>/bin`
  plus the system directories, never the caller's), the job list to menu
  mapping (jobs that finished while the window was hidden are kept by id until
  it is shown), the menu layout, the quit decision, the navigation rule, the
  three-exits-in-60-s crash window.
- `src/engine.js`: the supervisor (Node only, tested against
  `test/fake-engine.js`, and through its seams: `spawn`, `health`, `jobs`,
  `killGroup`). It decides from the child process, not remembered facts: one
  current run record (`this.run`), set when a start or restart is accepted and
  cleared only by that child's exit (or a failure before spawn); every late
  continuation passes one gate (`run === this.run && !run.cancelled`); one exit
  handler kills the group and decides what next (failure, stop, restart,
  exited early, crash). Refuses a port something already answers on or holds;
  polls `/api/health` every 100 ms for 60 s and is ready only when its `pid` is
  the spawned child's (anything else is another program on the port, sent
  nothing). The engine is spawned as its own process group; one stop closes
  stdin, sends SIGTERM to the group and SIGKILLs it after 10 s, with no HTTP
  request; at quit the same, without waiting, and never spawning again. A
  second restart while one is pending is refused. `jobs()` returns null when
  the list cannot be read, never an empty list. Output and `[app]` lines go to
  `~/.anyscribe/logs/app.log`, probed before every launch; if it cannot be
  written the start window says so, and Try again probes it again.
- `src/main.js`: windows (a local start window, never served by the engine;
  the dashboard window, which hides on close), single instance, the menu bar
  (polls `GET /api/jobs` every 2 s; a failed read keeps the last list) and
  Dock modes, the login item (read from the system), the quit decision on
  every quit path (made at once from the last poll, so an idle logout goes
  through; an unknown list asks the same three buttons as a known busy one), one navigation rule for
  navigations, frames, redirects and popups (outside pages open in the
  browser, outside frames are blocked), and the preload bridge `window.anyscribeDesktop`
  (contextIsolation, sandbox, no Node; IPC accepted only from the dashboard's
  origin and the start page).
- Tests: `npm test` (unit and supervisor), `npm run e2e` (the real app,
  headless, against a real engine in a throwaway HOME).

### Skill Layer (`skill/`)
- Claude Code skill files bundled in package, auto-installed to `~/.claude/skills/anyscribe/`
- AI-first: auto-installs if `~/.claude/` exists (no opt-in), auto-updates via `.version` marker
- On every CLI invocation (except in the Mac app's engine, `ANYSCRIBE_APP=1`): compare `.version` to `__version__`, re-copy if mismatched
- One-time cleanup of the stale `ascli`/`scribe` skill directories (superseded by `anyscribe`)
- Skill files: SKILL.md (operator guide), references/ (commands, providers, config, troubleshooting)

### Config Layer (`config/`)
- `paths.py`: all path constants via pathlib
- `settings.py`: Settings dataclass, YAML serialization, dotenv loading

### Download Layer (`downloaders/`)
- Abstract base with `download()` and `can_handle()` methods
- YouTube: yt-dlp subprocess with `--extract-audio --audio-format mp3`
- Instagram: yt-dlp subprocess with `--extract-audio`; cookies optional via `--cookies-from-browser` (config field `instagram.browser`). Same pattern as YouTube.
- Registry dispatches URL to correct downloader

### Provider Layer (`providers/`)
- Abstract base with `transcribe(audio_path, language, diarize) -> TranscriptResult`
- `TranscriptSegment` includes optional `speaker` field for diarization
- 7 providers implemented:
  - **OpenAI** (default): `gpt-transcribe`, or `whisper-1` when timestamps are needed, or `gpt-4o-transcribe-diarize` with `--diarize`. `MODEL` class attr so Groq can subclass it.
  - **Deepgram**: Nova-3 (nova-2 also pickable), native diarization, `hi-Latn` support
  - **ElevenLabs**: Scribe v2, 90+ languages; word timings grouped into ~30-word timestamped segments
  - **OpenRouter**: Audio-via-chat (`openai/gpt-audio-mini`), no timestamps, freeform model slugs
  - **Sargam/Sarvam**: Indic languages, `saaras:v3` only, auto-chunks to 28 s (sync REST limit is 30 s, exclusive)
  - **Groq**: `whisper-large-v3-turbo`, OpenAI-compatible — thin subclass of `OpenAIProvider`. Cheapest + fastest.
  - **Local**: Parakeet (onnx-asr) or Whisper (faster-whisper), offline, CPU/GPU, no API key; a Whisper Tiny language guard keeps Parakeet to its 25 languages
- Lazy-import registry — each provider only loaded when requested
- Provider selected via config, overridable per-run with `--provider`
- **One resolution point**: `core/resolve.py::resolve_run(settings, cli_provider=, cli_model=, diarize=)` returns `RunPlan(provider, model, via, notes)` and is the only implementation of the ladder — explicit `--provider` → `--diarize` → `quality` tier → configured provider. All four run surfaces (CLI transcribe, batch, web, MCP) call it; none may reimplement it. `via` explains the choice; `notes` carry every automatic decision (keyless-tier fallback, whisper-1 timestamp switch, hi-Latn, diarize reroute) so no surface can silently swallow one.
- **Quality routing**: `quality` ∈ accuracy/balanced/cost/free (tier → provider, `core/quality.py::QUALITY_TIERS`) or `custom` (use `settings.provider`). Every write that sets a provider also writes `quality="custom"` — see `core/config_set.py::set_value` and `core/onboard_headless.py`.
- **Model resolution**: per-run `--model` (validated) > `settings.provider_models[provider]` > `get_models(provider, settings.extra_models)[0]` > `None` (local only).
- Diarization enabled per-run with `--diarize` flag or `diarize: true` in config

### Vault Layer (`vault/`)
- Scaffold creates Obsidian vault with .obsidian/ config
- Writer generates markdown with YAML frontmatter
- Supports `clean` (default), `timestamped`, and `diarized` output formats
- Diarized format groups consecutive same-speaker segments into blocks: `**Speaker** *[ts]*: text`
- Index maintains _index.md MOC and daily processing logs

### Core Layer (`core/`)
- Orchestrator ties the pipeline together; runs the dedup check (step 0) before any download, skippable with `force=True`
- Dedup (`core/dedup.py`) — `find_existing_transcript(source)` scans `sources/*/*.md` frontmatter for a matching `source:` line; no cache file, the vault is the source of truth
- Audio module handles chunking (18-min for Whisper 25MB limit); the Sarvam provider chunks its own input to 28 s (`providers/sargam.py`)
- Pre-flight (`core/preflight.py`) — prerequisite checks before the pipeline starts
- Checkpoint (`core/checkpoint.py`) — chunk save/resume for partial transcriptions
- Errors (`core/errors.py`) — structured provider errors + retry logic
- File utilities (`core/fileutil.py`) — atomic writes + file locking
- Local setup (`core/local_setup.py`) — local engine install/teardown (faster-whisper, av<19, onnx-asr; uv fallback)
- Local recommendation (`core/local_recommend.py`) — "Help me choose": one language question + detected hardware -> a model pick, shared by CLI, Web UI and MCP
- Config writes (`core/config_set.py`) — the single validated settings write path (CLI, Web UI, MCP)
- Tailnet sharing (`core/tailnet.py`) — finds the tailscale CLI (PATH; macOS app bundle), reads `tailscale status --json` and `tailscale serve status --json`, adds the serve rule only when the port is free (never replaces another rule, never Funnel), removes it only if anyscribe recorded creating it (`~/.anyscribe/tailnet-owned.json`) and it is still exactly ours (a matching hand-made rule is used but left in place), re-checks a held share on every `GET /api/tailnet`, outside the lock with a 3 s timeout (`BackendState` Stopped, NeedsLogin or NeedsMachineAuth: shown failed as stopped; a failed or slow read, or Starting: shown as unconfirmed, other devices may still reach it; both keep the hold; Running and the rule ours: shown live again; Running and the rule gone: released; `GET /api/tailnet` returns `held` beside `active`, and the card's privacy line follows `held`, the field the Host gate uses), and words each failure as one reason + fix (plus `card_fix`, the Settings card's switch wording). With sharing off it starts no Tailscale command (a read already running at switch-off finishes, at most 3 s, and is discarded)
- Dependency checker detects OS (macOS, Linux, Windows), checks/installs yt-dlp, ffmpeg, Python; auto-updates stale yt-dlp (>60 days) before download. Uses module-based detection for pip-installed tools (`python -m module --version`) and `shutil.which` for system binaries
- Updater supports git-based (dev) and pip-based (user) installs, and refuses to update the Mac app's engine (install type `app`), which the app updates
- Migrations run at startup: app home `~/.anyscribecli` → `~/.anyscribe`, workspace path rename, media → downloads, date-folder flattening, stale Sarvam model pin

## Key Technical Decisions

- **Python** over JS/TS: pipeline tools (yt-dlp, whisper) are Python-native
- **yt-dlp via `python -m yt_dlp`** (not bare `yt-dlp` binary): invoked as a Python module via `sys.executable` to avoid PATH issues on Windows. Auto-updated when stale — YouTube changes streaming formats frequently, causing 403s with old extractors. `get_command("yt-dlp")` in `core/deps.py` centralizes invocation for all call sites
- **yt-dlp for Instagram (0.8.3+)**: replaced instaloader to eliminate the rate-limit-prone `test_login()` GraphQL probe and the password-on-disk requirement. Cookies come from the user's existing browser via `--cookies-from-browser`. See `docs/building/journal/2026-04-29-instagram-yt-dlp-migration.md` for the decision record.
- **httpx** over requests: async-capable for batch processing
- **Dataclasses** over pydantic for config/results; pydantic only for web request/response models (`web/models.py`), via FastAPI
- **src/ layout**: prevents accidental imports from project root
- **Audio: 16kHz mono 64kbps**: proven optimal for Whisper from AnyScribe web app
- **Lazy imports**: optional deps (faster-whisper, onnx-asr for the local provider) only imported when needed
- **Three install paths**: install.sh (users), pip from PyPI (recommended), git clone (devs)
- **SemVer**: 0.x for pre-stable, 1.0.0 when all platforms + providers stable
- **Auto-migration**: Startup migrations handle legacy state transparently (app home `~/.anyscribecli` → `~/.anyscribe`, workspace rename, media → downloads, date-folder flattening, stale Sarvam model pin)
- **CI + PyPI automation**: GitHub Actions runs lint, tests, package build, and frontend bundle freshness checks on pushes/PRs. Tag pushes publish to PyPI via trusted publishing; `scripts/release.sh` handles one-command releases. The same workflow also runs `gh release create --generate-notes` after publish, so every tag gets a GitHub Release automatically. CI also runs a fake-HOME migration rehearsal (`scripts/rehearse-migration.sh`) and a docs job (rendered-HTML freshness, version drift, MCP-tool and CHANGELOG gates).
- **Desktop mode built on the user's machine, not downloaded** (0.18.0): the launcher and login item are plain files each OS already understands, written by `anyscribe desktop install`. The launcher is generated locally and needs no separately signed app download. It avoided Gatekeeper prompts in our Mac test; Windows click-through remains unverified. The signed downloadable app (Tauri) is parked in `BACKLOG.md`. Journal: `2026-10-22-desktop-mode.md`.
- **Tailnet sharing through `tailscale serve`, not a wider bind** (2026-11-09): the server keeps binding `127.0.0.1` and Tailscale proxies HTTPS from the tailnet to it, so the server never listens on a network interface and gets a real certificate for free. Off by default for every install; anyscribe only removes a serve rule it recorded creating that still points at itself. Journal: `2026-11-09-tailnet-sharing.md`.
- **Tray as a supervisor, not a rewrite**: `anyscribe tray` spawns/attaches to the existing `anyscribe ui` server rather than embedding a webview or rewriting the UI as a native app — the browser stays the UI surface, the tray only adds discoverability and process supervision.
- **AI-first skill management**: Claude Code skill auto-installs and auto-updates on every CLI invocation. `.version` marker pattern borrowed from gitstow — one file read + string compare, never blocks CLI
- **MCP server**: Thin wrapper around core modules. Both CLI and MCP use same orchestrator/providers/settings — only output format differs (Rich console vs JSON)
- **Web UI as core dependency**: FastAPI/uvicorn ship with `pip install anyscribe` (not optional). One app, one install. Same pattern as gitstow. React SPA builds to `web/static/`, committed to repo — end users don't need Node.js
- **Progress callback over async rewrite**: `on_progress` callback on `process()` avoids rewriting all providers/downloaders as async. ThreadPoolExecutor bridges sync→async cleanly
- **WebSocket over polling**: Real-time transcription progress (download→transcribe→write→index) needs instant feedback, not 30s HTMX polls. Event replay on late-connecting clients prevents missed events

## Configurability surface: tunable vs hard-coded

anyscribe draws a deliberate line: **user-facing behaviour is configurable; the
audio and transcription mechanics are constants in source.** This keeps
`config.yaml` short for a semi-technical audience, at the cost of power-user
tunability. The user-facing version of this boundary is in
`docs/user/configuration.md`; this section is the developer map.

```
   set at runtime (knobs)                fixed in source (constants)
   ┌───────────────────────────┐        ┌────────────────────────────────┐
   │ config/settings.py         │        │ core/audio.py   — chunk sizes  │
   │   → config.yaml            │        │ providers/*.py  — model IDs    │
   │ .env             (secrets) │        │ downloaders/*   — 16k/mono/64k │
   │ CLI flags · Web UI · MCP   │        │ config/paths.py — ~/.anyscribe │
   └───────────────────────────┘        │ web/app.py      — host 127.0.. │
   change anytime, no code              └────────────────────────────────┘
                                        change = edit source + reinstall
```

Hard-coded constants and where they live:

| Constant | Value | Source | Why fixed |
|----------|-------|--------|-----------|
| Audio profile | 16 kHz · mono · 64 kbps mp3 | `downloaders/youtube.py:58`, `instagram.py:105`, `local_file.py:52`, `core/audio.py:97` | Proven optimal for Whisper accuracy-per-byte. Duplicated across 4 files — no shared constant yet. |
| Whisper size trigger | 25 MB (`WHISPER_MAX_BYTES`) | `core/audio.py:9` | OpenAI upload cap |
| Whisper duration trigger | 30 min (`WHISPER_MAX_DURATION_SECONDS`) | `core/audio.py:16` | HTTP timeout ceiling |
| Chunk length / overlap | 18 min / 5 s | `core/audio.py:20,23` | Stays under 25 MB at 64 kbps |
| Sarvam chunk | 28 s (`SARVAM_MAX_DURATION`) | `providers/sargam.py` (`SARVAM_MAX_DURATION`) | Sarvam sync REST cap is 30 s, exclusive |
| Provider model catalogs | `PROVIDER_MODELS` in `providers/__init__.py` (defaults: `gpt-transcribe`, `nova-3`/`nova`, `scribe_v2`, `saaras:v3`, `openai/gpt-audio-mini`, `whisper-large-v3-turbo`); diarize pins `gpt-4o-transcribe-diarize` | `providers/__init__.py` + each `providers/*.py` | Pickable since 0.14.0 via `settings.provider_models` / `--model`; the `quality` tier still picks the provider, the pin rides on top. **Closed catalogs are release-managed** — each entry needs response-parsing code, so users can't extend them. `settings.extra_models` is the one escape hatch and is openrouter-only (0.15.0), because an open-model provider forwards any slug. Read catalogs via `get_models(name, extra_models)`, never `PROVIDER_MODELS` directly |
| App home | `~/.anyscribe` | `config/paths.py:6` | Fixed root for config + state |
| Web bind host | `127.0.0.1` (port is configurable via `--port`) | `web/app.py` `run()` | Localhost-only by design; server has no auth. Remote reach is opt-in through Tailscale's own proxy (`tailnet` setting), never by binding another interface |
| Registries | provider & downloader plugin tables | `providers/__init__.py`, `downloaders/registry.py` | Code-level extension points |

> **Why this split?** Config covers "what do I want out"; the hard-coded layer
> covers "how the transcription sausage gets made." See the
> [2026-06-27 audit](journal/2026-06-27-transcription-landscape-and-config-audit.md)
> for which of these constants are worth promoting to config and which should
> stay fixed.

## CLI ↔ Web UI: shared backend, asymmetric surfaces

### Rule: neither surface shells out to the other

CLI commands (`cli/*.py`) and Web UI routes (`web/routes/*.py`) are both **thin adapters** over the same Python modules:

```
CLI (Typer) ─┐
              ├──→ core/ · providers/ · config/ · vault/ · downloaders/
Web UI ─────┘     (shared backend — single implementation)
(FastAPI)
```

`anyscribe "url"` and `POST /api/transcribe` both call `core/orchestrator.py::process()` directly. No subprocess layer. Add a provider in `providers/` and both surfaces pick it up; fix a bug in the orchestrator and both surfaces are fixed. Same applies to the MCP server (see decision above).

For flows where UX differs meaningfully across surfaces (onboarding being the main one), we extract a shared backend function into `core/` that all surfaces' flow controllers converge on — e.g. `core/onboard_headless.py::run_headless_onboard()` powers the CLI `--yes` path and the Web UI wizard save-phase.

### Feature-coverage matrix

Not every feature lives on every surface. The asymmetry is intentional per-feature; this matrix captures the current state.

| Feature | CLI | Web UI | Notes |
|---------|-----|--------|-------|
| License and source information | `--help` footer | Sidebar links | Static notices, no backend state; `NOTICE` owns the first-party grant and Vite generates bundled JavaScript attribution. |
| Transcribe URL/file | ✓ | ✓ | Same `orchestrator.process()` on both |
| Duplicate detection (`cached`) + `--force` | ✓ (`--force`/`-f`) | ✓ ("Re-transcribe" on cached state) | Enforced in `orchestrator.process()` (dedup step 0), so all surfaces + MCP inherit it |
| Delete transcript | ✓ (`anyscribe rm`) | ✓ (delete in History) | Same `vault/index.py::delete_transcript`; also MCP `delete_transcript` tool |
| Cancel a running job | — | ✓ (`POST /api/jobs/{id}/cancel`, cooperative) | UI-only — a CLI run is cancelled with Ctrl+C |
| Onboard (first-run setup) | ✓ (TUI + `--yes` headless) | ✓ (wizard) | Both call `run_headless_onboard()` |
| Config read/write | ✓ (`anyscribe config`) | ✓ (Settings page) | Same `settings.load_config` / `save_config` |
| Provider test | ✓ (`anyscribe providers test`) | ✓ (Test/Diagnose buttons) | Same `/providers/{name}/test` logic |
| Local model mgmt | ✓ (`anyscribe model`) | ✓ (model cards + More models table) | Same `providers/local_models.py` registry |
| Local model guidance ("Help me choose") | ✓ (`onboard` language question) | ✓ (wizard, setup modal, Settings) | Same `core/local_recommend.py`; MCP gets it through `doctor` (`local.recommendations`) |
| Local setup/teardown | ✓ (`anyscribe local`) | ✓ (Setup modal, Teardown button) | Same `core/local_setup.py` |
| History browse | Obsidian vault directly | ✓ (History page with search) | Web UI has richer UX; CLI leans on Obsidian |
| Progress | Terminal progress | ✓ (WebSocket) | Same `on_progress` callback |
| Batch processing | ✓ (`anyscribe batch`, `--timeout` per URL) | — | CLI-only. Add to UI if users ask |
| Download-only | ✓ (`anyscribe download`) | — | CLI-only |
| View recent activity | ✓ (`anyscribe logs`) | — | Reads workspace `daily/*.md` + recovery dir directly; UI already has richer History browsing |
| Local model download progress | — | ✓ (byte-level bar, `setup_progress`/`progress` on status polls) | UI-only — CLI shows NDJSON phase events, no byte counter |
| System diagnostics | ✓ (`anyscribe doctor`) | ✓ (Settings → System section, lighter) | UI surfaces a subset |
| Self-update | ✓ (`anyscribe update`) | — | CLI-only. Updating a running server is weird |
| Claude Code skill install | ✓ (`anyscribe install-skill`) | — | CLI-only; runs automatically anyway |
| Menu-bar tray | ✓ (`anyscribe tray`) | — | CLI-only by nature — a tray icon isn't a Web UI concept; the tray supervises the Web UI server, it doesn't compete with it |
| Desktop app (launcher + login item + manifest) | ✓ (`anyscribe desktop install/uninstall/status/open`) | — | CLI-only: it installs the thing that starts the Web UI. The installers run it. `core/desktop.py` |
| Tailnet sharing | ✓ (`config set tailnet on` / `off`, `ui --tailnet` / `--local-only`) | ✓ (Settings → Sharing switch, live; sidebar link + copy while shared) | Same `core/tailnet.py` `Share` on both; the UI switch also applies to the running server. One-run flags are CLI-only by nature (they choose how a server starts) |
| Login auto-start | ✓ (`install-service`/`uninstall-service`) | ✓ (Settings → Startup → "Start at login", macOS/Windows/Linux, needs `[tray]` extra) | Same `core/service.py` (`GET/PUT /api/autostart`); the route writes the dashboard's own port |
| Legacy config migration | ✓ (`anyscribe migrate`, `--dry-run`) | — | CLI-only. Automatic app-home migration is guarded once per process and invoked by load_config(), load_env() and ensure_app_dirs(); direct path reads do not trigger it. |
| Drag-and-drop upload | — | ✓ | UI-only |
| API key management | ✓ (`anyscribe config set <prov>_api_key`) | ✓ (inline per-provider with Test) | UI has richer UX |

### When to place a feature on which surface

- **Both surfaces, default for core user-facing actions.** Transcribing, config changes, provider testing, onboarding — anything a human does often enough to want both a click and a script should live on both. The backend is shared; the cost of a second surface is just UX work.
- **CLI-only when it's operational/agentic by nature.** Batch processing, self-update, install scripts, CI-friendly doctor checks. These are things agents run or that belong in shell pipelines.
- **Web-UI-only when it's a visual interaction.** Drag-and-drop, rich history browsing with search/filter, inline masked-key management with visual feedback. CLI equivalents would be clunky.
- **Deliberate gaps are fine.** Not every CLI command needs a UI button; not every UI action needs a CLI equivalent. The rule is that the **primary flow for a given user archetype** (human / agent) should be fully sufficient on its native surface — we don't force humans into the CLI or agents into a browser.

When adding a new feature, decide surface coverage up front and note it in the commit message or PR description. If you're uncertain, default to building backend logic first (in `core/` or wherever fits) and adding the adapter(s) above — that way the other surface can get it later without refactoring.
