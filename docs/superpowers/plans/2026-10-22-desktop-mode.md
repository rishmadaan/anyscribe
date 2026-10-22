# Desktop Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `anyscribe desktop install` (run by the one-line installers) gives a user an anyscribe app icon, a login-started background server and an open dashboard on macOS, Windows and Linux, with no signing, no money and no new dependencies.

**Architecture:** Three small core modules behind one Typer group: `core/service.py` (login item per OS, extended from the macOS-only version), new `core/launcher.py` (app icon + launcher per OS + Windows shortcut helper), new `core/desktop.py` (install / uninstall / status / open + manifest). The existing `anyscribe tray` stays the supervised background process; two bugs that block it on Windows and under launchd are fixed first. Every render function is pure (returns text) so each OS's artifact is unit-tested on every OS; one real-platform integration test per OS runs in CI.

**Tech Stack:** Python 3.11+, Typer, pystray + Pillow (existing `[tray]` extra), launchd plist / `.desktop` files / PowerShell `WScript.Shell` for `.lnk`, pytest, bash + PowerShell installers, GitHub Actions (`ubuntu-latest`, `macos-latest`, `windows-latest`).

**Spec:** `docs/superpowers/specs/2026-10-22-desktop-mode-design.md`

## Global Constraints

- Current version 0.17.1 → this PR bumps to **0.18.0** in `src/anyscribe/__init__.py` and `pyproject.toml` (Task 9) but creates **no tag**; `./scripts/release.sh` is a separate, Rishabh-gated step.
- No new runtime dependency. Pillow and pystray come from the existing `[tray]` extra; every Pillow import is lazy (inside functions) so the base install stays tray-free, as `cli/tray_cmd.py` does today.
- All user-data paths through `config/paths.py`; new constants go there (`DESKTOP_DIR = APP_HOME / "desktop"`, `DESKTOP_MANIFEST = APP_HOME / "desktop.json"`). New per-OS *system* locations (`~/Applications`, `~/.config/autostart`, `%APPDATA%`) live as functions in the module that owns them so tests can monkeypatch them, mirroring `service.launch_agents_dir()`.
- Product name in user-facing files and menus is **anyscribe** (lowercase, as the CLI, docs and tray already spell it). Launcher file names: `anyscribe.app`, `anyscribe.lnk`, `anyscribe.desktop`. launchd label stays `com.anyscribe.tray`.
- Skill files (`src/anyscribe/skill/`) change in the same commit as the CLI behaviour they describe (repo CLAUDE.md). User docs change in Task 9, before the PR opens.
- Every shell-facing path is quoted: `shlex.quote` in the `.app` script and `.desktop` `Exec`; PowerShell single quotes with `'` doubled in shortcut scripts. Tests use a home path containing a space and an apostrophe.
- Any guard that prevents a loop, data loss or a wrong launch is mutation-tested: remove the guard, watch the covering test fail, restore it, and paste the failing run's tail into the task report.
- "If the spec is wrong, say so instead of building it."
- Gates per task: `ruff check src tests scripts && pytest`. Tasks touching `ui/` also run `cd ui && npm run lint && npm run build` and commit `src/anyscribe/web/static`.
- Commit after each green step on the feature branch; messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Reviewers and read-only agents delete nothing; test infrastructure lives in `tests/`, `.venv/`, `ui/node_modules/`.

## Models and effort (from the roster, 2026-10-22)

| Role | Model | Notes |
|---|---|---|
| Implementer, every task | Opus 5.5 (`model: opus`) | Effort `high` for Tasks 3 and 5 (platform branching, most failure classes); default otherwise. Each brief carries the three clauses: mutation-test a guard and report the failing run; say so if the spec is wrong; commit after each green step. |
| Per-task reviewer (subagent-driven-development gate) | Opus 5.5, effort high | Claude lane only, to keep Codex allowance for the final review. |
| Final PR gate | `independent-review` skill, size L | Correctness rounds on `gpt-6.1-sol` high; fit-to-job on Fable (else Opus high); the single `gpt-6-astra` closing pass. |
| Build check the way Rishabh will use it (Task 10) | `gpt-6.1-sol` effort medium writes the checklist script, the lead runs it outside the sandbox on this Mac and repeats a few claims by hand | Roster rule: Opus/lead owns the verdict. |
| Stranger test of the new getting-started text (Task 10) | Sonnet 5.5 (`model: sonnet`) | Follows the doc word for word on phantom-linux. |

## Review Focus

Failure modes the spec implies and no happy-path test covers; each has a pinned test in the owning task.

1. **Home path with a space or apostrophe** (`/Users/Rish O'Brien`): launcher script, plist, `.desktop` `Exec` and PowerShell shortcut script must still launch. → Task 3 (`test_renders_quote_paths_with_space_and_apostrophe`), Task 4 (`test_linux_autostart_exec_quotes_path`).
2. **Another program already on the port**: `desktop open` must not open the browser onto a stranger's server nor let the tray "attach" to it. → Task 5 (`test_open_refuses_foreign_listener`).
3. **Python reinstalled after install**: the recorded interpreter is gone; `status` must say so instead of "installed". → Task 5 (`test_status_unhealthy_when_python_missing`).
4. **Second tray under launchd KeepAlive**: a non-zero exit would relaunch every ThrottleInterval forever. → Task 2 (`test_tray_exits_zero_when_already_running`), Task 1 (`test_plist_has_throttle_interval`).
5. **Uninstall while a transcription runs**: the server is stopped on purpose; the user must be told the job was cancelled and that it resumes. → Task 5 (`test_uninstall_stops_tray_and_warns_about_running_job`).

---

### Task 0: App icon approval (lead + Rishabh, no subagent)

**Files:**
- Create (scratch, not committed): `outputs/2026-10-22-anyscribe-app-icon/option-a.png`, `option-b.png`, `preview.html`

- [ ] **Step 1:** Render two 1024×1024 options with Pillow from the existing brand: the landing favicon's dark rounded tile `#0E0D0B` with (A) the tray waveform glyph in amber `#F5A524`, (B) the amber dot from the favicon. Compose `preview.html` showing both at 16, 32, 128 and 512 px beside a mock Dock and Start menu row.
- [ ] **Step 2:** Show Rishabh; record the chosen option in the task report. **Gate: Task 3 Step 1 copies the approved file.** (Global CLAUDE.md: approval of the build does not approve an unseen mark.)

---

### Task 1: Login item survives launchd's minimal PATH and a crash

**Files:**
- Modify: `src/anyscribe/core/service.py`
- Modify: `src/anyscribe/core/tray.py` (add `TRAY_LOG`)
- Modify: `src/anyscribe/config/paths.py` (nothing new here yet; `LOGS_DIR` exists)
- Test: `tests/test_tray.py`

**Interfaces:**
- Produces: `service.service_path(environ: Mapping[str, str] | None = None, home: Path | None = None) -> str` — the installing shell's PATH followed by `/opt/homebrew/bin`, `/usr/local/bin`, `<home>/.deno/bin`, `<home>/.local/bin`, `dirname(sys.executable)`, de-duplicated, order kept, joined with `os.pathsep`.
- Produces: `service.render_plist(python: str | None = None, label: str = LABEL, port: int = 8457, path_env: str | None = None, log: Path | None = None) -> str`.
- Produces: `tray.TRAY_LOG: Path = LOGS_DIR / "tray.log"`.

- [ ] **Step 1: Write the failing tests** in `tests/test_tray.py`:

```python
def test_service_path_appends_known_dirs_once(tmp_path):
    env = {"PATH": f"/opt/homebrew/bin{os.pathsep}/usr/bin"}
    parts = service.service_path(env, home=tmp_path).split(os.pathsep)
    assert parts[:2] == ["/opt/homebrew/bin", "/usr/bin"]
    assert parts.count("/opt/homebrew/bin") == 1
    assert str(tmp_path / ".deno" / "bin") in parts
    assert str(Path(sys.executable).parent) in parts

def test_render_plist_carries_path_log_keepalive_and_port():
    xml = service.render_plist(python="/usr/bin/python3", port=9000,
                               path_env="/a:/b", log=Path("/tmp/t.log"))
    assert "<key>PATH</key>" in xml and "<string>/a:/b</string>" in xml
    assert "<string>--port</string>" in xml and "<string>9000</string>" in xml
    assert "<key>SuccessfulExit</key>" in xml and "<false/>" in xml
    assert "<string>/tmp/t.log</string>" in xml

def test_plist_has_throttle_interval():
    xml = service.render_plist(python="/usr/bin/python3")
    assert "<key>ThrottleInterval</key>" in xml and "<integer>60</integer>" in xml
```

- [ ] **Step 2: Run** `pytest tests/test_tray.py -k "service_path or render_plist or throttle" -v` → FAIL (unexpected keyword / AttributeError).
- [ ] **Step 3: Implement** `service_path` and extend `render_plist` (keys: `EnvironmentVariables.PATH`, `KeepAlive` dict `SuccessfulExit false`, `ThrottleInterval 60`, `StandardOutPath` and `StandardErrorPath` = `log`). `install_service()` passes `service_path()` and `tray.TRAY_LOG` and creates `TRAY_LOG.parent`. Keep `test_render_plist_contents` passing.
- [ ] **Step 4: Run** `pytest tests/test_tray.py -v` → PASS.
- [ ] **Step 5: Mutation.** Delete the de-dup in `service_path`; `test_service_path_appends_known_dirs_once` must fail; restore. Paste the failing tail in the report.
- [ ] **Step 6: Live check on this Mac** (read-only): `python -c "from anyscribe.core import service; print(service.render_plist())"` and confirm `/opt/homebrew/bin` appears.
- [ ] **Step 7: Commit** `fix(service): launchd tray gets a full PATH, crash restart and a log`.

---

### Task 2: Tray runs on Windows; a second tray exits 0; `stop_tray`

**Files:**
- Modify: `src/anyscribe/cli/tray_cmd.py`
- Modify: `src/anyscribe/core/tray.py`
- Test: `tests/test_tray.py`

**Interfaces:**
- Produces: `tray.stop_tray(port: int) -> bool` — POST `http://127.0.0.1:{port}/api/shutdown` (httpx, timeout 2, errors ignored), `os.kill(pid, SIGTERM)` for a live pidfile pid, `remove_pidfile()`; returns True if a pid was signalled.
- Produces: `tray_cmd._watch_signals_in_thread(state: dict, port: int) -> None` — on `os.name == "nt"` returns without touching `signal`; else today's block+sigwait thread.
- Produces: `tray_cmd._child_kwargs() -> dict` — `{"preexec_fn": …}` on POSIX, `{"creationflags": subprocess.CREATE_NO_WINDOW}` on Windows.

- [ ] **Step 1: Write the failing tests:**

```python
def test_tray_exits_zero_when_already_running(monkeypatch):
    monkeypatch.setattr(tray_cmd.core, "read_pidfile", lambda: 4242)
    monkeypatch.setitem(sys.modules, "pystray", types.ModuleType("pystray"))
    monkeypatch.setitem(sys.modules, "PIL", types.ModuleType("PIL")); sys.modules["PIL"].Image = object
    result = CliRunner().invoke(app, ["tray"])
    assert result.exit_code == 0
    assert "already running" in result.output

def test_signal_watch_is_skipped_on_windows(monkeypatch):
    monkeypatch.setattr(tray_cmd.os, "name", "nt")
    monkeypatch.setattr(tray_cmd.signal, "pthread_sigmask",
                        lambda *a: pytest.fail("pthread_sigmask called on nt"), raising=False)
    tray_cmd._watch_signals_in_thread({"proc": None}, 8457)

def test_stop_tray_shuts_down_and_kills(monkeypatch, tmp_path):
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid"); tray.PIDFILE.write_text("777")
    monkeypatch.setattr(tray, "_pid_alive", lambda pid: True)
    killed, posted = [], []
    monkeypatch.setattr(tray.os, "kill", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(tray, "_post_shutdown", lambda port: posted.append(port))
    assert tray.stop_tray(8457) is True
    assert killed == [(777, signal.SIGTERM)] and posted == [8457]
    assert not tray.PIDFILE.exists()
```

- [ ] **Step 2: Run** `pytest tests/test_tray.py -k "already_running or windows or stop_tray" -v` → FAIL.
- [ ] **Step 3: Implement.** In `tray_cmd.tray`: already-running → print and `raise typer.Exit(code=0)`. Extract the signal block into `_watch_signals_in_thread`; extract Popen kwargs into `_child_kwargs`. In `tray.py`: `_post_shutdown(port)` (httpx import lazy) and `stop_tray`.
- [ ] **Step 4: Run** `pytest tests/test_tray.py -v` → PASS. Update `test_tray_missing_extra` only if its assertion changed (it should not: missing extra stays exit 1).
- [ ] **Step 5: Mutation.** Change the already-running exit back to 1; `test_tray_exits_zero_when_already_running` must fail; restore.
- [ ] **Step 6: Skill.** In `src/anyscribe/skill/references/commands.md` § `anyscribe tray`: "a second `anyscribe tray` prints *already running* and exits 0" and "works on Windows and Linux too".
- [ ] **Step 7: Commit** `fix(tray): run on Windows, exit 0 when already running, add stop_tray`.

---

### Task 3: `core/launcher.py` — icons and the app launcher on each OS

**Files:**
- Create: `src/anyscribe/assets/app-icon.png` (approved in Task 0, 1024×1024 RGBA)
- Create: `src/anyscribe/core/launcher.py`
- Modify: `src/anyscribe/config/paths.py` (add `DESKTOP_DIR = APP_HOME / "desktop"`)
- Test: `tests/test_launcher.py`

**Interfaces:**
- Produces (pure renderers):
  - `render_app_script(python: str, port: int) -> str` — `#!/bin/sh\nexec <q python> -m anyscribe desktop open --port <port>\n`
  - `render_info_plist(icon_file: str = "anyscribe") -> str` — `CFBundleName anyscribe`, `CFBundleIdentifier com.anyscribe.app`, `CFBundleExecutable anyscribe`, `CFBundleIconFile`, `CFBundlePackageType APPL`, `LSUIElement true`.
  - `render_desktop_entry(python: str, port: int, icon: str = "anyscribe") -> str` — `[Desktop Entry]`, `Type=Application`, `Name=anyscribe`, `Exec=<q python> -m anyscribe desktop open --port <port>`, `Icon=`, `Terminal=false`, `Categories=AudioVideo;Utility;`.
  - `render_shortcut_script(lnk: Path, target: str, arguments: str, icon: Path | None, description: str) -> str` — PowerShell using `New-Object -ComObject WScript.Shell`, single-quoted with `'` doubled.
- Produces (effects):
  - `pythonw() -> str` — `sys.executable` with `pythonw.exe` beside it on Windows, else `sys.executable`.
  - `create_shortcut(lnk: Path, target: str, arguments: str, icon: Path | None, description: str) -> None` — runs `powershell -NoProfile -NonInteractive -Command <script>`; raises `RuntimeError` on non-zero exit.
  - `render_icons(dest_dir: Path) -> dict[str, Path]` — writes `anyscribe.png` (512), `anyscribe.ico` (Pillow, sizes 16–256), and on macOS `anyscribe.icns` via an iconset + `iconutil -c icns`; returns the written paths keyed `png`/`ico`/`icns`.
  - `applications_dir() -> Path` (`~/Applications`), `start_menu_dir() -> Path` (`%APPDATA%/Microsoft/Windows/Start Menu/Programs`), `xdg_applications_dir() -> Path` (`~/.local/share/applications`), `xdg_icon_path() -> Path` (`~/.local/share/icons/hicolor/512x512/apps/anyscribe.png`).
  - `install_launcher(python: str, port: int, icons: dict[str, Path]) -> Path` — dispatch on `sys.platform`; returns the launcher path. macOS: writes the `.app` tree and `chmod 0o755` the script. Linux: writes `.desktop`, copies the png to `xdg_icon_path()`, runs `update-desktop-database <dir>` if on PATH (failure ignored). Windows: `create_shortcut(...)` to `start_menu_dir()/anyscribe.lnk` targeting `pythonw()`.
  - `uninstall_launcher() -> bool`, `launcher_path() -> Path`.

- [ ] **Step 1:** Copy the approved icon to `src/anyscribe/assets/app-icon.png`; confirm `python -c "from importlib.resources import files; print(len(files('anyscribe').joinpath('assets/app-icon.png').read_bytes()))"` > 0 (hatch ships the whole package dir; `tray-icon.png` already proves it).
- [ ] **Step 2: Write the failing tests** in `tests/test_launcher.py` (helper `home = tmp_path / "Rish O'Brien"`; monkeypatch `Path.home` → `home`, and `sys.platform` per test):

```python
def test_renders_quote_paths_with_space_and_apostrophe(home):
    py = str(home / "py env" / "python3")
    assert shlex.quote(py) in launcher.render_app_script(py, 8457)
    assert shlex.quote(py) in launcher.render_desktop_entry(py, 8457)
    ps = launcher.render_shortcut_script(home / "a.lnk", py, "-m anyscribe tray", None, "anyscribe")
    assert "Rish O''Brien" in ps and "$s.Save()" in ps

def test_info_plist_is_background_launcher():
    xml = launcher.render_info_plist()
    assert "<key>LSUIElement</key>" in xml and "<string>com.anyscribe.app</string>" in xml

def test_desktop_entry_fields():
    txt = launcher.render_desktop_entry("/usr/bin/python3", 8457)
    assert "Terminal=false" in txt and "Icon=anyscribe" in txt and "--port 8457" in txt

def test_install_launcher_macos_writes_app_tree(home, monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher, "applications_dir", lambda: home / "Applications")
    app = launcher.install_launcher("/usr/bin/python3", 8457, {"icns": home / "i.icns"})
    assert (app / "Contents" / "MacOS" / "anyscribe").stat().st_mode & 0o111
    assert (app / "Contents" / "Info.plist").exists()
    assert launcher.uninstall_launcher() is True and not app.exists()

def test_install_launcher_linux_writes_desktop_and_icon(home, monkeypatch): ...  # asserts .desktop + icon copy, update-desktop-database call captured via monkeypatched subprocess.run

def test_install_launcher_windows_calls_create_shortcut(home, monkeypatch): ...  # monkeypatch launcher.create_shortcut, assert lnk path and pythonw target

@pytest.mark.skipif(sys.platform != "darwin", reason="iconutil")
def test_render_icons_real_icns(tmp_path):
    out = launcher.render_icons(tmp_path)
    assert out["icns"].stat().st_size > 1000

@pytest.mark.skipif(sys.platform != "win32", reason="WScript.Shell")
def test_create_shortcut_real_lnk(tmp_path):
    lnk = tmp_path / "anyscribe.lnk"
    launcher.create_shortcut(lnk, sys.executable, "-m anyscribe --version", None, "test")
    assert lnk.exists()

def test_render_icons_png_and_ico(tmp_path):
    pytest.importorskip("PIL")
    out = launcher.render_icons(tmp_path)
    assert out["png"].exists() and out["ico"].exists()
```

- [ ] **Step 3: Run** `pytest tests/test_launcher.py -v` → FAIL (module missing).
- [ ] **Step 4: Implement** `launcher.py` per the Interfaces block. `render_icons` skips `.icns` when `shutil.which("iconutil")` is None.
- [ ] **Step 5: Run** `pytest tests/test_launcher.py -v` → PASS on this Mac (the win32 test skips).
- [ ] **Step 6: Mutation.** Remove the `'` doubling in `render_shortcut_script`; `test_renders_quote_paths_with_space_and_apostrophe` must fail; restore.
- [ ] **Step 7: Commit** `feat(launcher): app icon and launcher for macOS, Windows, Linux`.

---

### Task 4: Login item on Windows and Linux; Settings toggle on all three

**Files:**
- Modify: `src/anyscribe/core/service.py`
- Modify: `src/anyscribe/cli/service_cmd.py` (`_require_macos` → `_require_supported`)
- Modify: `src/anyscribe/web/routes/system.py`
- Test: `tests/test_tray.py`, `tests/test_autostart_route.py`

**Interfaces:**
- Consumes: `launcher.create_shortcut`, `launcher.pythonw`, `launcher.render_shortcut_script`, `service.service_path`, `tray.TRAY_LOG`.
- Produces: `service.SUPPORTED: frozenset = {"darwin", "win32", "linux"}`, `service.supported() -> bool`, `service.login_item_path() -> Path` (plist / `startup_dir()/anyscribe tray.lnk` / `autostart_dir()/anyscribe-tray.desktop`), `service.startup_dir() -> Path`, `service.autostart_dir() -> Path`, `service.render_autostart_entry(python: str, port: int, path_env: str) -> str`, `service.install_service(port: int = 8457) -> Path`, `service.uninstall_service() -> bool`, `service.is_installed() -> bool`.

- [ ] **Step 1: Write the failing tests:**

```python
def test_linux_autostart_exec_quotes_path(tmp_path):
    txt = service.render_autostart_entry(str(tmp_path / "py env" / "python3"), 8457, "/a:/b c")
    assert "Exec=env PATH='/a:/b c' " in txt and shlex.quote(str(tmp_path / "py env" / "python3")) in txt
    assert "X-GNOME-Autostart-enabled=true" in txt

def test_install_service_linux_writes_autostart(monkeypatch, tmp_path):
    monkeypatch.setattr(service.sys, "platform", "linux")
    monkeypatch.setattr(service, "autostart_dir", lambda: tmp_path / "autostart")
    path = service.install_service(port=9000)
    assert path.name == "anyscribe-tray.desktop" and "--port 9000" in path.read_text()
    assert service.uninstall_service() is True and not path.exists()

def test_install_service_windows_creates_startup_shortcut(monkeypatch, tmp_path):
    monkeypatch.setattr(service.sys, "platform", "win32")
    monkeypatch.setattr(service, "startup_dir", lambda: tmp_path / "Startup")
    calls = []
    monkeypatch.setattr(service.launcher, "create_shortcut", lambda *a, **k: calls.append((a, k)))
    service.install_service()
    assert calls[0][0][0] == tmp_path / "Startup" / "anyscribe tray.lnk"
    assert "-m anyscribe tray --port 8457" in calls[0][0][2]
```

  In `tests/test_autostart_route.py` replace `test_autostart_rejected_off_macos` with `test_autostart_supported_on_linux_and_windows` (GET reports `supported: True` for `linux` and `win32`) and `test_autostart_rejected_on_unknown_platform` (`sys.platform = "freebsd"` → 400).

- [ ] **Step 2: Run** `pytest tests/test_tray.py tests/test_autostart_route.py -v` → FAIL.
- [ ] **Step 3: Implement.** Dispatch on `sys.platform` inside `install_service` / `uninstall_service` / `login_item_path`; macOS path unchanged from Task 1. `system.py`: `supported = sys.platform in service.SUPPORTED`; `enabled = supported and service.is_installed()`; the pystray refusal stays. `service_cmd.py`: `_require_supported` with message `Autostart is not supported on {platform.system()}.`; docstrings drop "(macOS)".
- [ ] **Step 4: Run** `pytest -v` → PASS.
- [ ] **Step 5: Skill.** `SKILL.md` rows 81–82 and `references/commands.md` § install-service: drop "macOS only"; name the three file locations.
- [ ] **Step 6: Commit** `feat(service): start-at-login on Windows and Linux; Settings toggle everywhere`.

---

### Task 5: `anyscribe desktop {install, uninstall, status, open}`

**Files:**
- Create: `src/anyscribe/core/desktop.py`
- Create: `src/anyscribe/cli/desktop_cmd.py`
- Modify: `src/anyscribe/cli/main.py:210-227` (`app.add_typer(desktop_app, name="desktop")`)
- Modify: `src/anyscribe/config/paths.py` (`DESKTOP_MANIFEST = APP_HOME / "desktop.json"`)
- Modify: `src/anyscribe/skill/SKILL.md`, `src/anyscribe/skill/references/commands.md`, `src/anyscribe/skill/references/troubleshooting.md`
- Test: `tests/test_desktop.py`

**Interfaces:**
- Consumes: `launcher.render_icons / install_launcher / uninstall_launcher / launcher_path / pythonw`, `service.install_service(port) / uninstall_service / login_item_path / supported`, `tray.port_responding / read_pidfile / stop_tray / TRAY_LOG`.
- Produces (`core/desktop.py`):
  - `Manifest` TypedDict `{version: str, python: str, port: int, launcher: str, login_item: str, installed_at: str}`; `read_manifest() -> Manifest | None`, `write_manifest(m: Manifest) -> None` (via `fileutil.atomic_write`).
  - `tray_available() -> bool` (`find_spec("pystray") and find_spec("PIL")`).
  - `health_is_anyscribe(port: int) -> bool` — GET `/api/health`, True iff 200 and JSON has `"version"` (`web/routes/health.py` returns `{"ok", "version", "dependencies"}` today; verified 2026-10-22).
  - `spawn_detached(args: list[str], log: Path) -> subprocess.Popen` — stdin DEVNULL, stdout/stderr appended to `log`; POSIX `start_new_session=True`; Windows `creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`.
  - `open_dashboard(port: int, timeout: float = 15.0) -> str` — spec §2; returns the URL opened/printed; raises `PortInUseError(port)` for a foreign listener; `StartFailed` after the fallback also fails.
  - `install(port: int = 8457, launch: bool = True) -> Manifest` — raises `TrayMissing` when `tray_available()` is False.
  - `uninstall() -> dict` — `{"stopped": bool, "launcher": bool, "login_item": bool}`.
  - `status() -> dict` — `{"platform", "supported", "installed", "launcher", "login_item", "python", "port", "tray_running", "server_running", "healthy", "reason"}`.
- Produces (`cli/desktop_cmd.py`): Typer app `desktop_app` with `install(--port, --no-launch, --yes, --json)`, `uninstall(--yes, --json)`, `status(--json)`, `open(--port)`. JSON envelope `{"success", "data", "error"}` like `service_cmd.py`. Exit codes: 0 ok; 1 refused/failed; 2 unsupported platform.

- [ ] **Step 1: Write the failing tests** in `tests/test_desktop.py` (fixtures monkeypatch `desktop.launcher.*`, `desktop.service.*`, `desktop.tray.*`, `paths.DESKTOP_MANIFEST` → tmp):

```python
def test_install_writes_manifest_and_launches(fake_platform_darwin, calls):
    m = desktop.install(port=9000, launch=True)
    assert m["port"] == 9000 and Path(m["launcher"]).name == "anyscribe.app"
    assert calls["install_launcher"] == [("python", 9000)] and calls["install_service"] == [9000]
    assert calls["open_dashboard"] == [9000]

def test_install_refuses_without_tray(monkeypatch):
    monkeypatch.setattr(desktop, "tray_available", lambda: False)
    with pytest.raises(desktop.TrayMissing): desktop.install()

def test_open_refuses_foreign_listener(monkeypatch):
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: True)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: False)
    monkeypatch.setattr(desktop, "spawn_detached", lambda *a, **k: pytest.fail("must not spawn"))
    with pytest.raises(desktop.PortInUseError): desktop.open_dashboard(8457)

def test_open_starts_tray_then_opens(monkeypatch, fake_spawn, fake_browser):
    health = iter([False, False, True])
    monkeypatch.setattr(desktop.tray, "port_responding", lambda port, **k: False)
    monkeypatch.setattr(desktop, "health_is_anyscribe", lambda port: next(health))
    url = desktop.open_dashboard(8457, timeout=1)
    assert fake_spawn.args[0][-4:] == ["tray", "--port", "8457"] or "tray" in fake_spawn.args[0]
    assert url == "http://127.0.0.1:8457" and fake_browser.opened == [url]

def test_open_falls_back_to_ui_when_tray_dies(monkeypatch, fake_spawn_dying_then_ok, fake_browser):
    ...  # first Popen.poll() returns 1 → second spawn args contain ["ui", "--port", "8457", "--no-open"]

def test_status_unhealthy_when_python_missing(tmp_manifest):
    tmp_manifest(python="/nonexistent/python3")
    s = desktop.status()
    assert s["installed"] is True and s["healthy"] is False and "python" in s["reason"].lower()

def test_uninstall_stops_tray_and_warns_about_running_job(monkeypatch, tmp_manifest, calls):
    tmp_manifest()
    monkeypatch.setattr(desktop.tray, "stop_tray", lambda port: calls["stop"].append(port) or True)
    r = CliRunner().invoke(app, ["desktop", "uninstall", "--yes"])
    assert r.exit_code == 0 and calls["stop"] == [8457]
    assert "transcription in progress" in r.output and "resume" in r.output

def test_cli_status_json_envelope(tmp_manifest):
    r = CliRunner().invoke(app, ["desktop", "status", "--json"])
    data = json.loads(r.output); assert data["success"] is True and "healthy" in data["data"]

def test_cli_install_unsupported_platform_exit_2(monkeypatch):
    monkeypatch.setattr(desktop.service.sys, "platform", "freebsd")
    assert CliRunner().invoke(app, ["desktop", "install", "--yes"]).exit_code == 2
```

- [ ] **Step 2: Run** `pytest tests/test_desktop.py -v` → FAIL (module missing).
- [ ] **Step 3: Implement** `core/desktop.py` then `cli/desktop_cmd.py`; register in `main.py`. Uninstall copy (exact): `Stopped anyscribe. Any transcription in progress was cancelled; it will resume from its checkpoint the next time you run it.` Foreign-port copy (exact): `Port {port} is in use by another program. Run: anyscribe desktop install --port <free port>`.
- [ ] **Step 4: Run** `pytest -v && ruff check src tests scripts` → PASS.
- [ ] **Step 5: Mutation.** Remove the `health_is_anyscribe` check in `open_dashboard`; `test_open_refuses_foreign_listener` must fail; restore.
- [ ] **Step 6: Skill.** `SKILL.md` command table: add `anyscribe desktop install --yes --json`, `desktop status --json`, `desktop uninstall --yes --json`; rewrite rows 80–82 to point at `desktop` first. `references/commands.md`: new `## anyscribe desktop` section (what each subcommand does, flags, JSON shapes, exit codes). `references/troubleshooting.md`: "ffmpeg not found but only from the app" → `anyscribe desktop install` again (rewrites the login item with the current PATH); "no tray icon on GNOME" → use the app-menu icon. Add the sentence "The skill and the MCP server never need the desktop app running."
- [ ] **Step 7: Live smoke on this Mac**: `python -m anyscribe desktop status --json` (not installed), `python -m anyscribe desktop install --yes --no-launch`, `status` again (healthy true), `ls ~/Applications/anyscribe.app ~/Library/LaunchAgents/com.anyscribe.tray.plist`, `launchctl list | grep anyscribe`, then `desktop uninstall --yes`, confirm all three gone. Paste outputs in the report.
- [ ] **Step 8: Commit** `feat(desktop): anyscribe desktop install/uninstall/status/open`.

---

### Task 6: Settings → Startup copy on all platforms (UI rebuild)

**Files:**
- Modify: `ui/src/pages/SettingsPage.tsx:329-346`
- Rebuild: `src/anyscribe/web/static/`

- [ ] **Step 1:** Change the comment to `{/* Startup — hidden only where the API says unsupported. */}`, label to `Start at login`, caption to `Starts anyscribe in the menu bar (macOS) or system tray (Windows, Linux) when you log in.`
- [ ] **Step 2:** `cd ui && npm ci && npm run lint && npm run build`; `git status` shows only `web/static` changes plus the tsx.
- [ ] **Step 3:** `grep -l "Start at login" src/anyscribe/web/static/assets/*.js` → one hit.
- [ ] **Step 4: Commit** `feat(ui): Startup toggle copy covers Windows and Linux`.

---

### Task 7: Installers finish with desktop mode

**Files:**
- Modify: `install.sh` (flags block ~L60–90, `run_post_install` ~L510–550, banners ~L560–590, header comment L9–16)
- Modify: `install.ps1` (param block, `Install-Anyscribe`, banner ~L335–345, header L11–13)
- Test: `tests/test_install_sh.py`

- [ ] **Step 1: Write the failing tests** (the file already runs `install.sh` with `--dry-run` through fake commands; follow `test_skipped_pipx_launch_does_not_claim_ready`):

```python
def test_dry_run_installs_desktop_by_default(tmp_path):
    out = run_installer_dry(tmp_path)
    assert "desktop install --yes" in out

def test_no_desktop_flag_skips_it(tmp_path):
    out = run_installer_dry(tmp_path, "--no-desktop")
    assert "desktop install" not in out and "anyscribe ui" in out

def test_git_method_skips_desktop_and_says_why(tmp_path):
    out = run_installer_dry(tmp_path, "--method", "git")
    assert "desktop install" not in out and "[tray]" in out

def test_ps1_has_nodesktop_switch_and_desktop_step():
    txt = Path("install.ps1").read_text()
    assert "[switch]$NoDesktop" in txt and "desktop install --yes" in txt
```

- [ ] **Step 2: Run** `pytest tests/test_install_sh.py -v` → FAIL.
- [ ] **Step 3: Implement.** bash: `--no-desktop` sets `RUN_DESKTOP=false` (default true); in `run_post_install`, when `RUN_DESKTOP` and the pip path was used: `"${cmd[@]}" desktop install --yes` (dry-run echoes). Banner per OS from spec §4; keep the `anyscribe ui` line. PowerShell: `param([switch]$NoDesktop)`; after `Install-Anyscribe`: `& $script:PythonCmd -m anyscribe desktop install --yes` unless `$NoDesktop`; Windows banner text.
- [ ] **Step 4: Run** `bash -n install.sh && pytest tests/test_install_sh.py -v` → PASS. If `pwsh` is installed here, `pwsh -NoProfile -Command "[scriptblock]::Create((Get-Content -Raw install.ps1)) | Out-Null"` parses; else note it is parsed by the Windows CI job (Task 8).
- [ ] **Step 5: Commit** `feat(installers): finish with anyscribe desktop install; --no-desktop opts out`.

---

### Task 8: CI runs the real-platform tests

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1:** Add job `desktop-platforms` with `strategy.matrix.os: [macos-latest, windows-latest]`, `runs-on: ${{ matrix.os }}`, Python 3.12, `pip install -e ".[dev,tray]"`, `pytest tests/test_desktop.py tests/test_launcher.py tests/test_tray.py tests/test_autostart_route.py -v`, plus on Windows `pwsh -NoProfile -Command "$null = [scriptblock]::Create((Get-Content -Raw install.ps1))"`.
- [ ] **Step 2:** `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` → no error.
- [ ] **Step 3: Commit** `ci: run desktop-mode tests on macOS and Windows`. Push the branch; the lead confirms the job is green on GitHub before Task 9 closes.

---

### Task 9: Docs, changelog, version 0.18.0 (no tag)

**Files:**
- Modify: `docs/user/getting-started.md`, `docs/user/commands.md`, `docs/user/troubleshooting.md`, `docs/user/agents.md`, `README.md`, `landing/index.html` (install copy only), `CHANGELOG.md`, `BACKLOG.md`, `docs/building/architecture.md`, `docs/building/_index.md`, `src/anyscribe/__init__.py`, `pyproject.toml`
- Create: `docs/building/journal/2026-10-22-desktop-mode.md`
- Regenerate: `landing/docs/*.html` via `python scripts/build-docs.py`

- [ ] **Step 1: getting-started.** New section "Two ways to install" right after the installers: **CLI mode** (pip, terminal, Claude Code) and **Desktop mode** (what the installer set up: the app, the login item, the dashboard; how to open it: *Spotlight → anyscribe* / *Start menu → anyscribe* / *app menu → anyscribe*; how to stop it: tray menu → Quit; how to remove it: `anyscribe desktop uninstall`). Replace "Keep it running" with a pointer to it; keep `anyscribe ui` as the CLI-mode way in. Blockquote: "Claude Code does not need the app open."
- [ ] **Step 2: commands.md.** New `## anyscribe desktop` (overview table row + section with the four subcommands, flags, JSON, exit codes). Update `install-service` / `uninstall-service` sections (all OSes; "prefer `anyscribe desktop install`"). Update `tray` (Windows/Linux; exit 0 when already running).
- [ ] **Step 3: troubleshooting.md.** Three entries from spec §4 plus "Startup toggle says the tray isn't installed" (`pip install "anyscribe[tray]"`).
- [ ] **Step 4: agents.md.** Row "Menu-bar tray" → "Desktop app"; paragraph: agents can run `anyscribe desktop install --yes --json`; the skill and MCP never need it running.
- [ ] **Step 5: README + landing.** Install section: the one-liner now sets up desktop mode; `--no-desktop` for CLI-only. `grep -n "install-service\|Keep it running\|anyscribe ui" README.md landing/index.html` and fix each hit.
- [ ] **Step 6: Building docs.** `architecture.md`: new "Desktop surface" paragraph (launcher → `desktop open` → tray → ui; login item; manifest; the three pure-render modules). Journal entry (type: feature; tags: desktop, tray, installers; tldr) covering the decisions in the spec §Decisions and the Gatekeeper probe. `_index.md` row at the top. `BACKLOG.md`: 0.18.0 row + section; parked item "Signed downloadable app (Tauri + SignPath Foundation + Apple Developer Program)".
- [ ] **Step 7: CHANGELOG 0.18.0** — **Added**: desktop mode (`anyscribe desktop …`, installers, Start at login everywhere); **Fixed**: login-started tray now finds ffmpeg/Deno; tray runs on Windows; **Changed**: `install-service` on all OSes. Upgrade note: run `anyscribe desktop install` once after `pip install --upgrade`.
- [ ] **Step 8: Version.** Set `0.18.0` in both files; `grep -rn "0\.17\.1" --include="*.md" --include="*.py" --include="*.toml" --include="*.html" . | grep -v CHANGELOG | grep -v BACKLOG | grep -v journal` → zero hits or each marked `<!-- version-pin-ok -->`.
- [ ] **Step 9:** `python scripts/build-docs.py && python scripts/check-docs.py && ruff check src tests scripts && pytest` → all PASS; `git status` includes `landing/docs/*.html`.
- [ ] **Step 10: Commit** `docs: desktop mode; bump to 0.18.0`.

---

### Task 10: Use it the way Rishabh will (lead, with helpers)

- [ ] **Step 1 (Mac, lead):** On this Mac, from the branch's editable install: `anyscribe desktop install --yes`. Confirm: `~/Applications/anyscribe.app` opens the dashboard from Spotlight; menu-bar icon present; `launchctl list | grep com.anyscribe.tray` shows a pid; `curl -s 127.0.0.1:8457/api/health`. Then `launchctl unload` + `load` the plist (stands in for logout/login) and transcribe a short local audio file **from the dashboard** — this proves the launchd-started server finds ffmpeg. Quit from the tray menu; confirm the server stopped and launchd did not relaunch it (`launchctl list` shows exit 0, no new pid after 70 s).
- [ ] **Step 2 (Mac, Sol build check):** `gpt-6.1-sol` effort medium writes a checklist script covering every control named in the docs (install, status, open, Settings toggle off/on, uninstall) and one planted bug (e.g. `health_is_anyscribe` forced False); the lead runs it outside the sandbox and repeats three of its claims by hand.
- [ ] **Step 3 (Linux, stranger test):** Sonnet 5.5 follows `docs/user/getting-started.md` word for word over SSH on phantom-linux (`--no-desktop` is *not* passed), then reports: did `desktop install` succeed, does `~/.local/share/applications/anyscribe.desktop` exist, does `desktop status` say healthy, does `desktop open` print the URL (no browser over SSH). The lead checks the autostart file's `Exec` by eye.
- [ ] **Step 4:** Windows: CI (Task 8) is the only check for now; the click-through waits for a Windows PC (Rishabh, 2026-10-22). Say so in the PR.
- [ ] **Step 5:** Open the PR; run the `independent-review` skill at size L; fix or answer every finding; re-check the last fix round; then hand to Rishabh for the release decision.
