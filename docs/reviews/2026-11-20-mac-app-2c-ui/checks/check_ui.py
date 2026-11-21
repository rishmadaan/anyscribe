"""Click-through check for the 2c-ui Mac screens (run with /usr/bin/python3, which has Playwright).

Starts real engines from the main checkout's .venv with throwaway HOMEs and free ports:
  A  this worktree's bundle, setup finished (fake key)   - app states and browser mode
  B  this worktree's bundle, fresh HOME (setup not done) - the wizard's last step
  C  the main checkout's bundle (6dc70b2), same state as A - browser-mode pixel baseline
Injects stub.js (window.anyscribeDesktop) before load, clicks every control in every
state, checks what each called on the stub and what the screen then says, and
screenshots each state at 1440, 1000 and 390 px wide.

  python3 check_ui.py [--only NAME[,NAME]] [--no-shots] [--out DIR]
Exit code 0 only when every check passed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parents[3]
MAIN = Path(os.environ.get("ANYSCRIBE_MAIN_CHECKOUT") or Path.home() / "labs/projects/anyscribe")  # the main checkout: its .venv engine and its bundle
PY = MAIN / ".venv/bin/python"
STUB = (HERE / "stub.js").read_text()
WIDTHS = [(1440, 900), (1000, 760), (390, 844)]
GUIDE = "https://github.com/rishmadaan/anyscribe/blob/main/docs/user/troubleshooting.md"

results: list[dict] = []
current = {"scenario": ""}


def check(cond, what, detail=""):
    results.append({"scenario": current["scenario"], "check": what, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("  PASS " if cond else "  FAIL ") + what + ("" if cond else f"  [{detail}]"))
    return cond


# ── engines ──────────────────────────────────────────


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Engine:
    def __init__(self, name, home: Path, src: Path | None):
        self.name, self.home, self.port = name, home, free_port()
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH",)}
        env["HOME"] = str(home)
        if src:
            env["PYTHONPATH"] = str(src)
        self.log = open(home / f"engine-{name}.log", "w")
        self.proc = subprocess.Popen(
            [str(PY), "-m", "anyscribe", "ui", "--port", str(self.port), "--no-open"],
            env=env, stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        self.url = f"http://127.0.0.1:{self.port}"
        for _ in range(120):
            try:
                urllib.request.urlopen(self.url + "/api/health", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        else:
            raise RuntimeError(f"engine {name} did not start; see {self.log.name}")
        print(f"engine {name}: pid {self.proc.pid} port {self.port} HOME {home}")

    def post(self, path, body):
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=10).read())

    def get(self, path):
        return json.loads(urllib.request.urlopen(self.url + path, timeout=10).read())

    def stop(self):
        os.kill(self.proc.pid, signal.SIGTERM)  # by its pid, never by pattern
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.kill(self.proc.pid, signal.SIGKILL)
        self.log.close()


# ── stub configs ─────────────────────────────────────

ON_OK = {"ok": True, "state": "on", "command": "/Users/test/.local/bin/anyscribe",
         "uses": {"path": "/Users/test/.local/bin/anyscribe", "version": "0.20.0", "via": "app"},
         "occupant": None, "appVersion": "0.20.0", "claudeCode": True, "skill": "installed"}
OFF = {**ON_OK, "state": "off", "command": None, "uses": None, "skill": "missing"}
OTHER = {**ON_OK, "state": "other-copy", "command": None,
         "uses": {"path": "/Users/test/.local/bin/anyscribe", "version": "0.19.0", "via": "uv"},
         "occupant": {"path": "/Users/test/.local/bin/anyscribe", "version": "0.19.0", "via": "uv"}}
# another copy earlier on PATH, nothing at our spot: no Switch (amendment)
OTHER_ELSEWHERE = {**OTHER, "occupant": None, "uses": {"path": "/opt/homebrew/bin/anyscribe", "version": "0.18.2", "via": "pipx"},
                   "reason": "Terminal finds another anyscribe at /opt/homebrew/bin/anyscribe first."}
# the login shell could not be asked: uses is null, the reason says so (amendment)
ON_UNKNOWN = {**ON_OK, "uses": None, "reason": "anyscribe couldn't ask your login shell which anyscribe it runs."}
# amendment 2: remove() refuses like Restart engine, with that reason
REFUSED = {"ok": False, "reason": "Wait for transcriptions to finish before restarting the engine."}
REMOVED_OK = {"ok": True, "pieces": {"launcher": "removed", "loginItem": "removed", "menuBarIcon": "stopped"}, "startAtLoginCarriedOver": True}
REMOVED_NOT_CARRIED = {"ok": True, "pieces": {"launcher": "removed", "loginItem": "removed", "menuBarIcon": "stopped"},
                       "startAtLoginCarriedOver": False, "reason": "This app is set to start at login, but macOS needs your approval: System Settings, General, Login Items."}
SKILL_MISSING = {**ON_OK, "skill": "missing", "reason": "Couldn't write to ~/.claude/skills (permission denied)."}
PATH_MISSING = {**ON_OK, "state": "path-missing", "uses": None}
ON_NO_CC = {**ON_OK, "claudeCode": False, "skill": "not-applicable"}
OTHER_OURS = {**OTHER_ELSEWHERE, "command": "/Users/test/.local/bin/anyscribe"}
NO_LAUNCHER = {"installed": False, "pieces": {"launcher": "absent", "loginItem": "absent", "menuBarIcon": "not running"}}
LAUNCHER = {"installed": True, "pieces": {"launcher": "present", "loginItem": "present", "menuBarIcon": "running"}}
REMOVE_FAIL = {"ok": False, "pieces": {"launcher": "removed", "loginItem": "removed", "menuBarIcon": "still running"},
               "startAtLoginCarriedOver": True, "reason": "Cleanup didn't finish: the old menu bar icon is still running."}
CONFLICT = {"ok": False, "needsChoice": "keep-current-or-restore",
            "reason": "The anyscribe command in ~/.local/bin was changed since this app wrote it."}
SHELL_REASON = "anyscribe couldn't ask your login shell which anyscribe it runs, so this is a best guess."
STD_LINE = 'export PATH="$HOME/.local/bin:$PATH"'
# 2c-app terminal.js addToPath, word for word (F4)
BASH_REASON = "Your bash reads ~/.profile; add this line to it by hand: " + STD_LINE
ZSHRC_REASON = "The line is in ~/.zprofile, but your shell setup removes it again later (check ~/.zshrc)."
RUNNING = {"state": "running", "port": 1, "lastExit": None, "stoppedRestarting": False}


def cfg(**over):
    base = {"version": "0.20.0", "platform": "darwin", "settings": {"dockMode": "menubar", "startAtLogin": False},
            "engine": RUNNING, "terminal": ON_OK, "launcher": NO_LAUNCHER,
            "firstLaunch": {"oldLauncherAsked": True, "terminalAsked": True}, "fileDir": FILE_DIR, "results": {}}
    base.update(over)
    return base


# ── page helpers ─────────────────────────────────────


class Run:
    def __init__(self, pw, out: Path, shots: bool):
        self.browser = pw.chromium.launch(headless=True)
        self.out, self.shots = out, shots

    def open(self, engine: Engine, path="/", stub: dict | None = None, jobs=None, mock_transcribe=False,
             dismissed=True, key_ok=False, block_fonts=False):
        ctx = self.browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=engine.url)
        if dismissed:
            ctx.add_init_script("localStorage.setItem('scribe_onboarding_dismissed','1')")
        if stub is not None:
            ctx.add_init_script(f"window.__STUB_CFG = {json.dumps(stub)};\n{STUB}")
        if block_fonts:  # web fonts arrive over the network at varying times: compare on local fonts
            ctx.route(re.compile(r"https://fonts\.(googleapis|gstatic)\.com/.*"), lambda route: route.abort())
        page = ctx.new_page()
        page.reqs = []  # type: ignore[attr-defined]
        page.tagged = []  # type: ignore[attr-defined]  # (body url, the stub's page number) per POST /api/transcribe

        def on_request(q):
            page.reqs.append((q.method, q.url.replace(engine.url, ""), q.post_data))
            if q.method == "POST" and q.url.endswith("/api/transcribe") and q.post_data:
                page.tagged.append((json.loads(q.post_data).get("url"), q.headers.get("x-stub-page")))
        page.on("request", on_request)
        page.jobs = jobs if jobs is not None else []  # type: ignore[attr-defined]
        if stub is not None:  # the main checkout's engine has no job list: serve one
            page.route("**/api/jobs", lambda route: route.fulfill(json=page.jobs))
        if mock_transcribe:  # a job that stays running (the engine never heard of it)
            page.route("**/api/transcribe", lambda route: route.fulfill(
                json={"job_id": "j-check", "provider": "openai", "model": "gpt-4o-transcribe", "notes": []}))
            page.route("**/api/jobs/j-check", lambda route: route.fulfill(json={"status": "running"}))
            page.route_web_socket("**/api/ws/jobs/**", lambda ws: None)  # open, never answers
        if key_ok:
            page.route("**/api/providers/*/test", lambda route: route.fulfill(json={"success": True, "checked": True, "message": "ok"}))
        page.goto(engine.url + path)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        return page

    def calls(self, page, name=None):
        c = page.evaluate("window.__calls || []")
        return [x for x in c if name is None or x[0] == name]

    def shot(self, page, name, target=None):
        if not self.shots:
            return
        for w, h in WIDTHS:
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(250)
            if target:
                page.locator(target).first.scroll_into_view_if_needed()
            page.screenshot(path=str(self.out / f"{name}@{w}.png"))
        page.set_viewport_size({"width": 1440, "height": 900})
        page.wait_for_timeout(100)


def text(page) -> str:
    return page.inner_text("body")


def transcribe_posts(page):
    return [json.loads(b) for m, u, b in page.reqs if m == "POST" and u == "/api/transcribe" and b]


def uploads(page):
    return [u for m, u, b in page.reqs if u == "/api/upload"]


DRAG_JS = """([name, size, withFile, kind]) => {
  const dt = new DataTransfer();
  if (withFile) dt.items.add(new File([new Uint8Array(size)], name, {type: 'audio/mp4'}));
  else if (kind === 'text') dt.setData('text/plain', 'hello');
  const ev = (type, data) => { const e = new DragEvent(type, {bubbles: true, cancelable: true, dataTransfer: data}); document.querySelector('main').dispatchEvent(e); return e; };
  window.__dt = dt;
  ev('dragenter', dt); ev('dragover', dt);
}"""
DROP_JS = "() => { const e = new DragEvent('drop', {bubbles: true, cancelable: true, dataTransfer: window.__dt}); document.querySelector('main').dispatchEvent(e); return e.defaultPrevented; }"


# ── scenarios ────────────────────────────────────────


def s_browser(r: Run):
    """Browser mode (no bridge): today's dashboard, nothing app-only."""
    p = r.open(A, "/")
    t = text(p)
    check(p.evaluate("!('anyscribeDesktop' in window)"), "no bridge in the page")
    check(p.get_by_role("button", name="Shutdown").count() == 1, "Shutdown button present")
    check(p.locator(".app-drag").count() == 0, "no drag strip")
    check("Drop to transcribe" not in t and "engine" not in t.lower(), "no overlay or engine banner text")
    p.evaluate(DRAG_JS, ["clip.m4a", 1000, True, None])
    p.wait_for_timeout(150)
    check("Drop to transcribe" not in text(p), "dragging a file shows no overlay")
    p.evaluate(DROP_JS)
    p.wait_for_timeout(300)
    check(not transcribe_posts(p), "a drop submits nothing")
    p.set_input_files("input[type=file]", files=[{"name": "clip.m4a", "mimeType": "audio/mp4", "buffer": b"\0" * 64}])
    p.wait_for_timeout(800)
    check(len(uploads(p)) == 1, "Browse uploads the file (today's behaviour)", p.reqs[-5:])
    check(not transcribe_posts(p), "Browse does not submit by itself")
    r.shot(p, "browser-transcribe")
    p.goto(A.url + "/settings")
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(300)
    t = text(p)
    auto = A.get("/api/autostart")
    check(("STARTUP" in t.upper()) == bool(auto.get("supported")), f"Startup section as today (supported={auto.get('supported')})")
    check("THIS MAC" not in t.upper(), "no This Mac section")
    for w in ["Show anyscribe in", "Use from Terminal", "Restart engine", "Old browser launcher", "Removing anyscribe"]:
        check(w not in t, f"no '{w}'")
    r.shot(p, "browser-settings")
    p.context.close()


def s_browser_pixels(r: Run):
    """Browser mode, pixel for pixel against the main checkout's bundle (engine C)."""
    from PIL import Image, ImageChops

    def grab(eng, path, w, h, n):
        p = r.open(eng, path, block_fonts=True)
        p.set_viewport_size({"width": w, "height": h})
        p.evaluate("document.fonts.ready.then(() => document.activeElement && document.activeElement.blur())")
        # the blinking caret and running animations (History's loading line), the same for both bundles
        p.add_style_tag(content="* { caret-color: transparent !important; animation: none !important; transition: none !important; }")
        p.wait_for_timeout(1500)  # entrance animations finish
        f = r.out / f"pixel-{eng.name}{path.replace('/', '_') or '_'}@{w}-{n}.png"
        p.screenshot(path=str(f), full_page=True)
        p.context.close()
        return Image.open(f).convert("RGB")

    def diff(a, b):
        return "size" if a.size != b.size else ImageChops.difference(a, b).getbbox()

    for path in ["/", "/history", "/settings"]:
        for w, h in WIDTHS:
            # Up to three loads each: rendering noise (a sub-pixel, 1-level antialias flicker) can differ
            # between two loads of the same bundle, so identical means some new/old pair matches exactly.
            shots_a, shots_c, tries = [], [], []
            for n in range(3):
                shots_a.append(grab(A, path, w, h, n))
                shots_c.append(grab(C, path, w, h, n))
                tries.append(diff(shots_a[-1], shots_c[-1]))
                if tries[-1] is None:
                    break
            noise = [diff(shots_a[0], x) for x in shots_a[1:]]
            check(tries[-1] is None, f"browser {path} at {w}px identical to main's bundle",
                  f"new vs old per load: {tries}; new vs new: {noise}")
            if len(tries) > 1:
                print(f"    (new vs old per load {tries}; new vs new {noise})")


def s_app_layout(r: Run):
    p = r.open(A, "/", cfg())
    check(p.get_by_role("button", name="Shutdown").count() == 0, "app: no Shutdown button")
    strip = p.locator(".app-drag").first
    check(p.locator(".app-drag").count() == 2, "app on macOS: drag strip and logo row are drag regions")
    region = p.evaluate("getComputedStyle(document.querySelector('.app-drag')).getPropertyValue('-webkit-app-region') || getComputedStyle(document.querySelector('.app-drag')).getPropertyValue('app-region')")
    check(region == "drag", "drag strip computes app-region: drag", region)
    box = strip.bounding_box()
    check(box and box["height"] >= 28, "top strip leaves room for the window buttons", box)
    check("© 2026 Rishabh Madaan" in text(p) and p.locator("img[alt=KraftedX]").count() == 1, "credits and KraftedX mark kept")
    r.shot(p, "app-transcribe")
    p.context.close()
    p = r.open(A, "/", cfg(platform="linux"))
    check(p.locator(".app-drag").count() == 0 and p.get_by_role("button", name="Shutdown").count() == 0,
          "app on another OS: no drag strip, still no Shutdown")
    p.context.close()


def s_drop(r: Run):
    p = r.open(A, "/", cfg())
    p.evaluate(DRAG_JS, ["team-sync-recording.m4a", 48 * 1024 * 1024, True, None])
    p.wait_for_timeout(200)
    t = text(p)
    check("Drop to transcribe" in t and "team-sync-recording.m4a" not in t and " MB" not in t, "F11: the overlay says Drop to transcribe only", t[-200:])
    r.shot(p, "app-drop-overlay")
    prevented = p.evaluate(DROP_JS)
    p.wait_for_timeout(800)
    check(prevented, "the drop is taken by the page (no navigation to the file)")
    posts = transcribe_posts(p)
    check(len(posts) == 1 and posts[0]["url"] == f"{FILE_DIR}/team-sync-recording.m4a", "drop submits the file's path", posts)
    check(not uploads(p), "no upload copy")
    check(r.calls(p, "pathForFile") == [["pathForFile", ["team-sync-recording.m4a"]]], "pathForFile asked once")
    check("Drop to transcribe" not in text(p), "overlay gone after the drop")
    r.shot(p, "app-after-drop")
    p.context.close()
    # Dragging text is not a file: no overlay
    p = r.open(A, "/", cfg())
    p.evaluate(DRAG_JS, ["", 0, False, "text"])
    p.wait_for_timeout(150)
    check("Drop to transcribe" not in text(p), "dragging text shows no overlay")
    p.context.close()


def s_browse(r: Run):
    p = r.open(A, "/", cfg())
    p.set_input_files("input[type=file]", files=[{"name": "interview.mp3", "mimeType": "audio/mpeg", "buffer": b"\0" * 64}])
    p.wait_for_timeout(800)
    path = f"{FILE_DIR}/interview.mp3"
    check(p.input_value("input[type=text]") == path and p.evaluate("document.activeElement === document.querySelector('input[type=text]')"),
          "F7: Browse puts the picked file's path in the box and focuses it", p.input_value("input[type=text]"))
    check(not transcribe_posts(p) and not uploads(p), "F7: nothing submitted and no upload copy until he clicks Transcribe")
    r.shot(p, "app-browse-filled")
    p.get_by_role("button", name="Transcribe").click()
    p.wait_for_timeout(600)
    posts = transcribe_posts(p)
    check(len(posts) == 1 and posts[0]["url"] == path, "F7: Transcribe then submits that path", posts)
    p.context.close()


def s_open_file(r: Run):
    p = r.open(A, "/history", cfg())
    p.evaluate(f"window.__openFile('{FILE_DIR}/dock.m4a')")
    p.wait_for_timeout(900)
    check(p.url.endswith(A.url + "/") or p.url == A.url + "/", "a Dock file opens Transcribe", p.url)
    posts = transcribe_posts(p)
    check(len(posts) == 1 and posts[0]["url"] == f"{FILE_DIR}/dock.m4a", "a Dock file is submitted by path", posts)
    p.context.close()
    # held before the page subscribed
    stub = cfg()
    ctx = r.browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script("localStorage.setItem('scribe_onboarding_dismissed','1')")
    ctx.add_init_script(f"window.__STUB_CFG = {json.dumps(stub)};\n{STUB}\nwindow.__openFile('{FILE_DIR}/early.m4a');")
    p = ctx.new_page()
    p.reqs = []
    p.on("request", lambda q: p.reqs.append((q.method, q.url.replace(A.url, ""), q.post_data)))
    p.route("**/api/jobs", lambda route: route.fulfill(json=[]))
    p.goto(A.url + "/")
    p.wait_for_timeout(1200)
    posts = transcribe_posts(p)
    check(len(posts) == 1 and posts[0]["url"] == f"{FILE_DIR}/early.m4a", "a file opened before load is submitted once", posts)
    ctx.close()
    # while a job runs here, the next file waits and is named
    p = r.open(A, "/", cfg(), mock_transcribe=True)
    p.fill("input[type=text]", "https://www.youtube.com/watch?v=check")
    p.get_by_role("button", name="Transcribe").click()
    p.wait_for_timeout(500)
    p.evaluate(f"window.__openFile('{FILE_DIR}/second.m4a')")
    p.wait_for_timeout(500)
    t = text(p)
    check("Up next: second.m4a. It starts when this one finishes." in t, "a file arriving mid-job waits and is named", t[-300:])
    check(len(transcribe_posts(p)) == 1, "it does not replace the running job")
    r.shot(p, "app-up-next")
    # C3: the engine stops and comes back; the app reloads the page to / after acknowledging B
    p.evaluate("window.__emit({state: 'restarting'})")
    p.wait_for_timeout(150)
    p.evaluate("window.__emit({state: 'running'})")
    after_reload(p, 1200)
    posts = [x["url"] for x in transcribe_posts(p)]
    check(reloads(p) == 1 and posts == ["https://www.youtube.com/watch?v=check", f"{FILE_DIR}/second.m4a"],
          "C3: B survives the reload and is submitted by its path", posts)
    check(p.evaluate("sessionStorage.getItem('anyscribe_incoming')") == "[]", "C3: B leaves the stored queue once the engine accepted it",
          p.evaluate("sessionStorage.getItem('anyscribe_incoming')"))
    p.context.close()


def after_reload(p, ms=900):
    """Wait out the app's reload to / after the engine is back (the stub does it as main.js)."""
    p.wait_for_timeout(ms)
    p.wait_for_load_state("networkidle")
    try:
        p.wait_for_function("document.querySelector('aside') !== null", timeout=8000)  # the new page has rendered
    except Exception:
        pass  # a page that crashed renders nothing: the next check says so
    p.wait_for_timeout(400)


def reloads(p) -> int:
    return int(p.evaluate("sessionStorage.getItem('__stub_reloads') || '0'"))


def s_banner(r: Run):
    p = r.open(A, "/", cfg(), mock_transcribe=True)
    check(p.locator("[role=status]").count() == 0, "no banner while running")
    p.fill("input[type=text]", "https://www.youtube.com/watch?v=weekly")
    p.get_by_role("button", name="Transcribe").click()
    p.wait_for_timeout(400)
    p.evaluate("window.__emit({state: 'restarting'})")
    p.wait_for_timeout(200)
    t = text(p)
    check("anyscribe's engine stopped. Restarting it." in t and "This usually takes a few seconds." in t, "restarting banner")
    r.shot(p, "banner-restarting")
    p.evaluate("window.__emit({state: 'running'})")
    after_reload(p)
    t = text(p)
    check(reloads(p) == 1 and p.url == A.url + "/", "R1: the stub reloaded the page to / when the engine came back", p.url)
    check("Running again" in t and "We couldn't confirm whether this transcription finished: https://www.youtube.com/watch?v=weekly. Check History before starting it again." in t,
          "C1: after the reload, running again names the watched job", t[:400])
    r.shot(p, "banner-running-again-job")
    p.get_by_role("link", name="Open History").click()
    p.wait_for_timeout(300)
    check(p.url.endswith("/history") and "Running again" not in text(p), "Open History goes to History and closes the banner", p.url)
    p.reload()
    p.wait_for_timeout(600)
    check("Running again" not in text(p), "C1: the note is used once (not shown after another reload)")
    p.context.close()

    p = r.open(A, "/", cfg())
    p.evaluate("window.__emit({state: 'restarting'})")
    p.wait_for_timeout(100)
    p.evaluate("window.__emit({state: 'running'})")
    after_reload(p)
    t = text(p)
    check("Running again" in t and "couldn't confirm" not in t and p.get_by_role("link", name="Open History").count() == 0,
          "running again with no job watched: no job wording")
    r.shot(p, "banner-running-again-nojob")
    p.get_by_role("button", name="Dismiss").click()
    p.wait_for_timeout(100)
    check("Running again" not in text(p), "Dismiss closes it")
    p.context.close()

    p = r.open(A, "/", cfg(engine={**RUNNING, "state": "starting"}))
    p.evaluate("window.__emit({state: 'running'})")
    after_reload(p)
    check("Running again" not in text(p), "a normal start never shows Running again")
    p.context.close()

    p = r.open(A, "/", cfg(restartMs=2500, results={"restartEngine": [{"ok": False, "reason": "anyscribe couldn't check for running transcriptions; try again in a moment"}, {"ok": True}]}))
    p.evaluate("window.__emit({state: 'stopped', stoppedRestarting: true, lastExit: {code: 1, signal: null, reason: null}})")
    p.wait_for_timeout(200)
    t = text(p)
    check("The engine keeps stopping" in t and "It stopped 3 times in a minute, so anyscribe stopped restarting it. Your transcripts are safe. The engine exited with code 1; the reason wasn't reported." in t,
          "keeps stopping: code, reason not reported", t[:500])
    check("Its log is in" not in t, "F10: no hidden log path in the banner")
    link = p.get_by_role("link", name="Troubleshooting guide")
    check(link.get_attribute("href") == GUIDE and link.get_attribute("target") == "_blank", "Troubleshooting guide link")
    r.shot(p, "banner-keeps-stopping")
    p.locator("[role=status]").get_by_role("button", name="Open log folder").click()
    p.wait_for_timeout(100)
    check(r.calls(p, "openLogFolder") == [["openLogFolder", []]], "F10: Open log folder in the banner calls openLogFolder()")
    p.locator("[role=status]").get_by_role("button", name="Restart engine").click()
    p.wait_for_timeout(200)
    check(len(r.calls(p, "restartEngine")) == 1 and "anyscribe couldn't check for running transcriptions" in text(p), "refused restart shows the bridge's reason")
    r.shot(p, "banner-restart-refused")
    p.locator("[role=status]").get_by_role("button", name="Copy details").click()
    p.wait_for_timeout(200)
    clip = p.evaluate("navigator.clipboard.readText()")
    check("Last exit: code 1" in clip and "app.log" in clip and "Copied" in text(p), "Copy details copies the exit and log location", clip)
    p.locator("[role=status]").get_by_role("button", name="Restart engine").click()
    p.wait_for_timeout(200)
    t = text(p)
    check("Restarting anyscribe's engine." in t and "anyscribe's engine stopped" not in t, "F2: a restart he asked for says so, not the crash words")
    r.shot(p, "banner-restarting-asked")
    after_reload(p, 3000)
    # the engine had stopped by itself before he asked (the outage), so "Running again" reports that one
    check(len(r.calls(p, "restartEngine")) == 2 and "Running again" in text(p) and "keeps stopping" not in text(p),
          "F2: after his restart, the earlier outage (not his restart) is what Running again reports")
    p.context.close()

    p = r.open(A, "/settings", cfg())
    p.wait_for_timeout(300)
    p.locator("#this-mac").get_by_role("button", name="Restart engine").click()
    p.wait_for_timeout(200)
    check("Restarting anyscribe's engine." in text(p), "F2: Restart engine in Settings, the asked-for words")
    after_reload(p)
    check(r.calls(p, "restartEngine") == [["restartEngine", []]] and "Running again" not in text(p), "F2: no Running again after Settings' restart")
    p.context.close()

    p = r.open(A, "/settings", cfg())
    p.evaluate("window.__emit({state: 'stopped', stoppedRestarting: true, lastExit: {code: null, signal: 'SIGKILL', reason: 'Killed by the system (out of memory)'}})")
    p.wait_for_timeout(200)
    t = text(p)
    check("The engine was stopped by SIGKILL: Killed by the system (out of memory)." in t, "keeps stopping: signal and reported reason")
    r.shot(p, "banner-keeps-stopping-signal")
    p.context.close()


def s_settings(r: Run):
    p = r.open(A, "/settings", cfg())
    t = text(p)
    check("THIS MAC" in t.upper() and "STARTUP" not in t.upper(), "This Mac replaces Startup")
    check("When its window is closed, anyscribe stays in the menu bar only. The Dock icon shows while the window is open." in t, "menu bar help")
    check("Off. When on, anyscribe starts in the menu bar when you log in, with no window." in t, "login help, menu bar")
    check("On. Terminal runs this app's anyscribe 0.20.0 from /Users/test/.local/bin/anyscribe. Claude Code skill installed." in t, "terminal on line")
    check("Version 0.20.0." in t, "version line")
    check("Running." in t and "Open log folder" in t, "engine running line")
    check("Old browser launcher" not in t, "no launcher row when not installed")
    ws = A.get("/api/config")["_resolved_workspace"]
    check(f"Your transcripts in {ws} and settings in ~/.anyscribe stay." in " ".join(t.split()), "removal help names the real workspace", ws)
    r.shot(p, "settings-default", "#this-mac")
    p.get_by_role("button", name="Dock", exact=True).click()
    p.wait_for_timeout(200)
    t = text(p)
    check(r.calls(p, "setDockMode") == [["setDockMode", ["dock"]]], "Dock calls setDockMode('dock')")
    check("No menu bar icon. anyscribe stays in the Dock while it runs; click the Dock icon to open it." in t and "starts in the Dock when you log in" in t, "Dock help and login help follow")
    r.shot(p, "settings-dock", "#this-mac")
    p.get_by_role("button", name="Menu bar and Dock").click()
    p.wait_for_timeout(200)
    t = text(p)
    check(r.calls(p, "setDockMode")[-1] == ["setDockMode", ["both"]] and "like a normal app" in t and "starts in the menu bar and the Dock" in t, "both")
    r.shot(p, "settings-both", "#this-mac")
    p.get_by_role("button", name="Menu bar", exact=True).click()
    p.wait_for_timeout(200)
    check(r.calls(p, "setDockMode")[-1] == ["setDockMode", ["menubar"]], "back to menu bar")
    p.get_by_role("switch", name="Start at login").click()
    p.wait_for_timeout(200)
    check(r.calls(p, "setStartAtLogin") == [["setStartAtLogin", [True]]] and "On. anyscribe starts in the menu bar when you log in, with no window." in text(p), "Start at login on")
    r.shot(p, "settings-login-on", "#this-mac")
    p.get_by_role("switch", name="Start at login").click()
    p.wait_for_timeout(200)
    check(r.calls(p, "setStartAtLogin")[-1] == ["setStartAtLogin", [False]] and "Off. When on" in text(p), "Start at login off")
    p.get_by_role("button", name="Open log folder").click()
    p.wait_for_timeout(100)
    check(len(r.calls(p, "openLogFolder")) == 1, "Open log folder")
    p.get_by_role("switch", name="Use from Terminal and Claude Code").click()
    p.wait_for_timeout(300)
    check(r.calls(p, "terminal.turnOff") == [["terminal.turnOff", []]], "switch off calls turnOff()")
    check("Off. anyscribe isn't in Terminal, and its Claude Code skill is removed." in text(p), "F8: right after a turnOff that removed the skill, the off line says so")
    r.shot(p, "settings-terminal-off", "#this-mac")
    p.get_by_role("switch", name="Use from Terminal and Claude Code").click()
    p.wait_for_timeout(300)
    check(r.calls(p, "terminal.turnOn") == [["terminal.turnOn", [{"replace": False}]]] and "On. Terminal runs" in text(p), "switch on calls turnOn({replace:false})")
    p.context.close()

    p = r.open(A, "/settings", cfg(loginNeedsApproval=True))
    p.get_by_role("switch", name="Start at login").click()
    p.wait_for_timeout(200)
    check("macOS hasn't turned it on yet. If it asks, allow anyscribe in System Settings, under Login Items." in text(p), "login waiting for approval")
    r.shot(p, "settings-login-approval", "#this-mac")
    p.context.close()

    p = r.open(A, "/settings", cfg(terminal=OTHER))
    t = text(p)
    check("Off. Terminal uses another anyscribe 0.19.0, installed with uv. Switch to this app's copy" in t, "other copy line")
    r.shot(p, "settings-terminal-other", "#this-mac")
    p.get_by_role("switch", name="Use from Terminal and Claude Code").click()
    p.wait_for_timeout(300)
    check(p.get_by_role("dialog").count() == 1 and not r.calls(p, "terminal.turnOn"), "switch on with another copy asks first (no turnOn)")
    p.keyboard.press("Escape")
    p.wait_for_timeout(200)
    p.get_by_role("button", name="Switch to this app's copy").click()
    p.wait_for_timeout(300)
    t = text(p)
    check("Terminal already has anyscribe" in t and "Terminal uses anyscribe 0.19.0, installed separately with uv at /Users/test/.local/bin/anyscribe." in t, "other copy card")
    check("If you switch, turning this off later puts your uv copy back" in t, "other copy note names uv")
    r.shot(p, "settings-terminal-other-card")
    p.get_by_role("dialog").get_by_role("button", name="Switch to this app's copy").click()
    p.wait_for_timeout(300)
    check(r.calls(p, "terminal.turnOn") == [["terminal.turnOn", [{"replace": True}]]], "Switch calls turnOn({replace:true})")
    check("anyscribe is ready in Terminal" in text(p) and "It runs this app's anyscribe 0.20.0 and updates with the app." in text(p), "ready card")
    r.shot(p, "settings-terminal-ready-card")
    p.get_by_role("button", name="Done").click()
    p.wait_for_timeout(300)
    check(p.get_by_role("dialog").count() == 0 and "On. Terminal runs" in text(p), "Done closes and the row reads On")
    p.context.close()

    p = r.open(A, "/settings", cfg(terminal=SKILL_MISSING, results={"terminal.retrySkill": [{**SKILL_MISSING}, {**ON_OK}]}))
    check("On. Terminal is ready; the Claude Code skill isn't installed." in text(p), "skill missing line")
    r.shot(p, "settings-terminal-skill", "#this-mac")
    p.locator("#this-mac").get_by_role("button", name="Try again").click()
    p.wait_for_timeout(300)
    check(len(r.calls(p, "terminal.retrySkill")) == 1 and "Couldn't write to ~/.claude/skills" in text(p) and "isn't installed" in text(p), "Try again still missing: the row says so, with the reason")
    p.locator("#this-mac").get_by_role("button", name="Try again").click()
    p.wait_for_timeout(300)
    check(len(r.calls(p, "terminal.retrySkill")) == 2 and "Claude Code skill installed." in text(p), "Try again succeeding")
    p.context.close()

    p = r.open(A, "/settings", cfg(terminal=PATH_MISSING, results={"terminal.status": [PATH_MISSING] * 4 + [ON_OK]}))
    check("On. Terminal can't see the command yet: it doesn't look in ~/.local/bin." in text(p), "path missing line")
    r.shot(p, "settings-terminal-path", "#this-mac")
    p.locator("#this-mac").get_by_role("button", name="Add it for me").click()
    p.wait_for_timeout(300)
    check(not r.calls(p, "terminal.addToPath"), "GUARD addToPath: the row's button only asks")
    check("One more step for Terminal" in text(p) and 'export PATH="$HOME/.local/bin:$PATH"' in text(p), "the ask shows the exact line")
    r.shot(p, "settings-terminal-path-ask")
    p.get_by_role("dialog").get_by_role("button", name="I'll do it myself").click()
    p.wait_for_timeout(300)
    check(not r.calls(p, "terminal.addToPath") and p.get_by_role("dialog").count() == 0, "GUARD addToPath: I'll do it myself adds nothing")
    p.locator("#this-mac").get_by_role("button", name="Add it for me").click()
    p.wait_for_timeout(300)
    p.get_by_role("dialog").get_by_role("button", name="Add it for me").click()
    p.wait_for_timeout(400)
    check(len(r.calls(p, "terminal.addToPath")) == 1 and "anyscribe is ready in Terminal" in text(p), "the person's yes adds the line, then ready")
    p.context.close()

    p = r.open(A, "/settings", cfg(results={"terminal.turnOff": [CONFLICT, CONFLICT, {"ok": True}]}))
    p.get_by_role("switch", name="Use from Terminal and Claude Code").click()
    p.wait_for_timeout(300)
    t = text(p)
    check(CONFLICT["reason"] in t and "Keep current command" in t and "Restore previous command" in t, "turnOff conflict asks keep or restore")
    r.shot(p, "settings-terminal-conflict", "#this-mac")
    p.get_by_role("button", name="Keep current command").click()
    p.wait_for_timeout(300)
    p.get_by_role("button", name="Restore previous command").click()
    p.wait_for_timeout(300)
    offs = r.calls(p, "terminal.turnOff")
    check(offs[1:] == [["terminal.turnOff", [{"choice": "keep-current"}]], ["terminal.turnOff", [{"choice": "restore"}]]], "AMEND 1: the two answers reach turnOff({choice})", offs)
    check("Keep current command" not in text(p), "conflict closes once settled")
    p.context.close()

    p = r.open(A, "/settings", cfg(terminal={**ON_OK, "reason": SHELL_REASON}))
    info = p.locator("#this-mac p", has_text=SHELL_REASON)
    check(info.count() == 1 and "text-red" not in (info.get_attribute("class") or ""), "AMEND 2: ok with a reason shows as information, not an error")
    r.shot(p, "settings-terminal-info-reason", "#this-mac")
    p.context.close()

    p = r.open(A, "/settings", cfg(terminal=ON_NO_CC))
    check("Claude Code isn't on this Mac." in text(p), "no Claude Code line")
    p.context.close()
    p = r.open(A, "/settings", cfg(terminal=OTHER_OURS))
    t = text(p)
    check("Terminal finds another anyscribe at /opt/homebrew/bin/anyscribe first." in t and "Terminal runs this app's" not in t, "ours written but another first: the status reason")
    r.shot(p, "settings-terminal-other-first", "#this-mac")
    p.context.close()

    p = r.open(A, "/settings", cfg(terminal=OTHER_ELSEWHERE))
    t = text(p)
    check("Terminal uses another anyscribe 0.18.2, installed with pipx." in t and OTHER_ELSEWHERE["reason"] in t, "AMEND occupant: other copy elsewhere, reason shown")
    check(p.get_by_role("button", name="Switch to this app's copy").count() == 0, "AMEND occupant: no Switch without an occupant")
    r.shot(p, "settings-terminal-other-elsewhere", "#this-mac")
    p.get_by_role("switch", name="Use from Terminal and Claude Code").click()
    p.wait_for_timeout(300)
    check(r.calls(p, "terminal.turnOn") == [["terminal.turnOn", [{"replace": False}]]] and p.get_by_role("dialog").count() == 0, "AMEND occupant: the switch writes ours without replacing anything")
    p.context.close()

    p = r.open(A, "/settings", cfg(terminal=ON_UNKNOWN))
    t = text(p)
    check("Terminal runs this app's" not in t and ON_UNKNOWN["reason"] in t, "AMEND uses: no 'runs this app's' claim when the shell wasn't asked; the reason instead")
    check("On. The command is added; anyscribe couldn't check that Terminal finds it." in t and "Terminal is ready" not in t, "C5: Settings row for a shell not asked")
    r.shot(p, "settings-terminal-unknown", "#this-mac")
    p.context.close()

    p = r.open(A, "/settings", cfg(terminal={**ON_UNKNOWN, "skill": "missing"}))
    t = text(p)
    check("On. The command is added; anyscribe couldn't check that Terminal finds it. The Claude Code skill isn't installed." in t
          and "Terminal is ready" not in t and p.locator("#this-mac").get_by_role("button", name="Try again").count() == 1,
          "C5: shell not asked and skill missing: no 'Terminal is ready', Try again offered")
    p.context.close()

    # F8: off on a Mac where the skill was never installed: no "skill is removed"
    p = r.open(A, "/settings", cfg(terminal=OFF))
    t = text(p)
    check("Off. anyscribe isn't in Terminal." in t and "skill is removed" not in t, "F8: plain off line when nothing was removed here")
    p.context.close()

    # F5: a copy sits at ~/.local/bin/anyscribe that Terminal does not use
    OFF_OCC = {**OFF, "occupant": {"path": "/Users/test/.local/bin/anyscribe", "version": "0.19.0", "via": "uv"}}
    p = r.open(A, "/settings", cfg(terminal=OFF_OCC))
    t = text(p)
    check("Off. Another anyscribe 0.19.0 is already at ~/.local/bin/anyscribe, installed with uv. Switch to this app's copy" in t
          and "Terminal uses" not in t, "F5: Settings row names the copy at our spot and offers Switch")
    r.shot(p, "settings-terminal-occupant", "#this-mac")
    p.get_by_role("switch", name="Use from Terminal and Claude Code").click()
    p.wait_for_timeout(300)
    check(p.get_by_role("dialog").count() == 1 and not r.calls(p, "terminal.turnOn"), "F5: the switch asks first when a copy sits there")
    p.get_by_role("dialog").get_by_role("button", name="Switch to this app's copy").click()
    p.wait_for_timeout(400)
    check(r.calls(p, "terminal.turnOn") == [["terminal.turnOn", [{"replace": True}]]] and "anyscribe is ready in Terminal" in text(p), "F5: Switch replaces it")
    p.context.close()

    p = r.open(A, "/settings", cfg(launcher=LAUNCHER, results={"oldLauncher.remove": [REFUSED]}))
    p.get_by_role("button", name="Remove it").click()
    p.wait_for_timeout(400)
    t = text(p)
    check("Removing the old launcher restarts the engine. " + REFUSED["reason"] in t and "Cleanup didn't finish" not in t and "Still installed" in t, "AMEND launcher/F6: a refusal shows its reason, prefixed, no checklist")
    r.shot(p, "settings-launcher-refused", "#this-mac")
    p.context.close()

    p = r.open(A, "/settings", cfg(launcher=LAUNCHER, results={"oldLauncher.remove": [REMOVED_NOT_CARRIED]}))
    p.get_by_role("button", name="Remove it").click()
    after_reload(p, 1200)
    t = text(p)
    check("Old launcher removed" in t and REMOVED_NOT_CARRIED["reason"] in t and "starts at login instead" not in t, "AMEND carry-over: not confirmed, the reason instead")
    p.context.close()

    p = r.open(A, "/settings", cfg(results={"restartEngine": [{"ok": False, "reason": "Wait for transcriptions to finish before restarting the engine."}]}),
               jobs=[{"status": "running"}, {"status": "pending"}, {"status": "completed"}])
    p.wait_for_timeout(500)
    t = text(p)
    btn = p.locator("#this-mac").get_by_role("button", name="Restart engine")
    check("Running · 2 transcriptions." in t and "Wait for transcriptions to finish before restarting the engine." in t, "engine with jobs line")
    check(btn.is_disabled(), "GUARD restart: disabled while transcriptions run")
    btn.click(force=True)
    p.wait_for_timeout(200)
    check(not r.calls(p, "restartEngine"), "GUARD restart: a click while disabled calls nothing")
    r.shot(p, "settings-engine-busy", "#this-mac")
    p.jobs = [{"status": "completed"}]
    p.wait_for_timeout(3500)
    check(not btn.is_disabled() and "Running." in text(p), "enabled again when the jobs finish")
    btn.click()
    p.wait_for_timeout(300)
    check(len(r.calls(p, "restartEngine")) == 1 and "Wait for transcriptions to finish" in text(p), "a refused restart shows the reason")
    p.context.close()

    p = r.open(A, "/settings", cfg())
    p.evaluate("window.__emit({state: 'stopped', stoppedRestarting: true, lastExit: {code: 1, signal: null, reason: null}})")
    p.wait_for_timeout(300)
    t = text(p)
    check("Stopped. It stopped 3 times in a minute, so anyscribe stopped restarting it. What happened" in t and "The engine keeps stopping" in t, "engine stopped row and banner")
    check(not p.locator("#this-mac").get_by_role("button", name="Restart engine").is_disabled(), "Restart engine available when stopped")
    r.shot(p, "settings-engine-stopped", "#this-mac")
    p.get_by_role("button", name="What happened").click()
    p.wait_for_timeout(600)
    check(p.evaluate("document.querySelector('main').scrollTop") == 0, "What happened scrolls to the banner")
    p.locator("#this-mac").get_by_role("button", name="Restart engine").click()
    p.wait_for_timeout(200)
    check(len(r.calls(p, "restartEngine")) == 1, "row Restart engine calls restartEngine")
    p.context.close()

    p = r.open(A, "/settings", cfg())
    p.evaluate("window.__emit({state: 'restarting'})")
    p.wait_for_timeout(300)
    check("Restarting." in text(p), "engine restarting row")
    r.shot(p, "settings-engine-restarting", "#this-mac")
    p.context.close()

    p = r.open(A, "/settings", cfg(launcher=LAUNCHER))
    check("Still installed in ~/Applications, with its login item. Your transcripts and settings are not affected." in text(p), "launcher row")
    r.shot(p, "settings-launcher", "#this-mac")
    p.get_by_role("button", name="Remove it").click()
    after_reload(p, 1200)
    t = text(p)
    check(len(r.calls(p, "oldLauncher.remove")) == 1 and "Old launcher removed" in t and "This app now starts at login instead" in t, "Remove it, removed (after the app's reload)")
    p.get_by_role("button", name="OK").click()
    p.goto(A.url + "/settings")
    p.wait_for_timeout(800)
    check(p.get_by_role("button", name="Remove it").count() == 0 and "Old browser launcher" not in text(p), "no Remove button once gone")
    r.shot(p, "settings-launcher-removed", "#this-mac")
    p.context.close()

    p = r.open(A, "/settings", cfg(launcher=LAUNCHER, componentNoReload=True, results={"oldLauncher.remove": [REMOVE_FAIL, REMOVE_FAIL]}))
    p.get_by_role("button", name="Remove it").click()
    p.wait_for_timeout(600)
    t = text(p)
    check("Cleanup didn't finish" in t and "Old menu bar icon: still running" in t and "Launcher: removed" in t and "Log out and back in to stop it, or try again." in t, "[component] per-piece result in the Settings row")
    r.shot(p, "settings-launcher-failed", "#this-mac")
    p.locator("#this-mac").get_by_role("button", name="Try again").click()
    p.wait_for_timeout(600)
    check(len(r.calls(p, "oldLauncher.remove")) == 2, "[component] Try again removes again")
    p.locator("#this-mac").get_by_role("button", name="Copy details").click()
    p.wait_for_timeout(200)
    clip = p.evaluate("navigator.clipboard.readText()")
    check("Old menu bar icon: still running" in clip, "Copy details copies the checklist", clip)
    p.context.close()


def s_first_launch(r: Run):
    unasked_l = {"oldLauncherAsked": False, "terminalAsked": True}
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=unasked_l))
    t = text(p)
    check("Replace the old anyscribe launcher?" in t and "and a login item that starts it" in t and "This app will start at login in its place." in t and "Your transcripts, settings and API keys stay where they are." in t, "launcher question")
    check("Keeping both shows two anyscribe icons in the menu bar." in t, "launcher note")
    r.shot(p, "first-launcher-question")
    p.get_by_role("button", name="Keep both").click()
    p.wait_for_timeout(300)
    check(r.calls(p, "firstLaunch.mark") == [["firstLaunch.mark", ["oldLauncherAsked"]]] and not r.calls(p, "oldLauncher.remove"), "Keep both marks and removes nothing")
    check(p.get_by_role("dialog").count() == 0, "question closes")
    p.reload()
    p.wait_for_timeout(800)
    check(p.get_by_role("dialog").count() == 0 and "Replace the old" not in text(p), "GUARD repeat: not asked again after reload")
    p.context.close()

    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=unasked_l))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 1200)
    t = text(p)
    check(r.calls(p, "firstLaunch.mark") == [["firstLaunch.mark", ["oldLauncherAsked"]]] and len(r.calls(p, "oldLauncher.remove")) == 1, "Remove marks and removes")
    check("Old launcher removed" in t and "Removed the old launcher, its login item and its menu bar icon. This app now starts at login instead; change it in Settings." in t, "removed card")
    r.shot(p, "first-launcher-removed")
    p.get_by_role("button", name="OK").click()
    p.wait_for_timeout(200)
    check(p.get_by_role("dialog").count() == 0, "OK closes")
    p.context.close()

    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=unasked_l, results={"oldLauncher.remove": [REMOVE_FAIL, {"ok": True, "pieces": {"launcher": "removed", "loginItem": "removed", "menuBarIcon": "stopped"}, "startAtLoginCarriedOver": False}]}))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 1200)
    t = text(p)
    check("Cleanup didn't finish" in t and "Old menu bar icon: still running" in t, "cleanup checklist")
    r.shot(p, "first-launcher-failed")
    p.get_by_role("dialog").get_by_role("button", name="Try again").click()
    after_reload(p, 1200)
    t = text(p)
    check(len(r.calls(p, "oldLauncher.remove")) == 2 and "Old launcher removed" in t and "starts at login instead" not in t, "Try again, removed, no carry-over sentence")
    p.context.close()

    p = r.open(A, "/", cfg(launcher={**LAUNCHER, "pieces": {**LAUNCHER["pieces"], "loginItem": "absent"}}, firstLaunch=unasked_l))
    t = text(p)
    check("login item" not in t and "in its place" not in t, "no login item: no login words")
    p.context.close()

    both = {"oldLauncherAsked": False, "terminalAsked": False}
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=both, terminal=OFF))
    check("Replace the old anyscribe launcher?" in text(p) and "Use anyscribe from Terminal" not in text(p), "launcher first")
    p.get_by_role("button", name="Keep both").click()
    p.wait_for_timeout(500)
    t = text(p)
    check("ONE MORE OPTION" in t.upper() and "Use anyscribe from Terminal and Claude Code" in t and "Adds one small file: ~/.local/bin/anyscribe" in t, "then the Terminal card, One more option")
    r.shot(p, "first-terminal-offer")
    p.get_by_role("button", name="Turn on").click()
    p.wait_for_timeout(400)
    t = text(p)
    check(r.calls(p, "terminal.turnOn") == [["terminal.turnOn", [{"replace": False}]]] and "anyscribe is ready in Terminal" in t, "Turn on, ready")
    check("In Claude Code, ask it to transcribe a link." in t and "If Claude Code isn't on this Mac yet" not in t, "F12: with Claude Code, its sentence only")
    r.shot(p, "first-terminal-ready")
    p.get_by_role("button", name="Done").click()
    p.wait_for_timeout(300)
    check(r.calls(p, "firstLaunch.mark")[-1] == ["firstLaunch.mark", ["terminalAsked"]] and p.get_by_role("dialog").count() == 0, "Done marks Terminal asked")
    p.reload()
    p.wait_for_timeout(800)
    check(p.get_by_role("dialog").count() == 0, "GUARD repeat: neither question again after reload")
    p.context.close()

    tonly = {"oldLauncherAsked": True, "terminalAsked": False}
    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF))
    p.get_by_role("button", name="Skip for now").click()
    p.wait_for_timeout(300)
    check(r.calls(p, "firstLaunch.mark") == [["firstLaunch.mark", ["terminalAsked"]]] and not r.calls(p, "terminal.turnOn"), "Skip for now marks, turns nothing on")
    p.context.close()

    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OTHER))
    t = text(p)
    check("Terminal already has anyscribe" in t and "ONE MORE OPTION" in t.upper() and "Claude Code keeps using that copy and its skill." in t, "other copy card on first launch")
    r.shot(p, "first-terminal-other")
    p.get_by_role("button", name="Keep the one I have").click()
    p.wait_for_timeout(300)
    check(r.calls(p, "firstLaunch.mark") == [["firstLaunch.mark", ["terminalAsked"]]] and not r.calls(p, "terminal.turnOn"), "Keep the one I have changes nothing")
    p.context.close()

    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF, results={"terminal.turnOn": [SKILL_MISSING], "terminal.retrySkill": [ON_OK]}))
    p.get_by_role("button", name="Turn on").click()
    p.wait_for_timeout(400)
    t = text(p)
    check("Terminal is ready, but the Claude Code skill couldn't be installed" in t and "Couldn't write to ~/.claude/skills (permission denied)." in t, "skill card")
    r.shot(p, "first-terminal-skill")
    p.get_by_role("button", name="Try again").click()
    p.wait_for_timeout(400)
    check(len(r.calls(p, "terminal.retrySkill")) == 1 and "anyscribe is ready in Terminal" in text(p), "Try again, ready")
    p.context.close()
    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF, results={"terminal.turnOn": [SKILL_MISSING]}))
    p.get_by_role("button", name="Turn on").click()
    p.wait_for_timeout(400)
    p.get_by_role("button", name="Continue").click()
    p.wait_for_timeout(300)
    check(r.calls(p, "firstLaunch.mark") == [["firstLaunch.mark", ["terminalAsked"]]] and p.get_by_role("dialog").count() == 0, "Continue marks and closes")
    p.context.close()

    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF, results={"terminal.turnOn": [PATH_MISSING], "terminal.status": [OFF, PATH_MISSING]}))
    p.get_by_role("button", name="Turn on").click()
    p.wait_for_timeout(400)
    t = text(p)
    check("One more step for Terminal" in t and "anyscribe can add this line to ~/.zprofile (~/.bash_profile if your Terminal uses bash):" in " ".join(t.split()), "path card after Turn on")
    check(not r.calls(p, "terminal.addToPath"), "GUARD addToPath: not called before the yes")
    r.shot(p, "first-terminal-path")
    p.get_by_role("button", name="Add it for me").click()
    p.wait_for_timeout(400)
    check(len(r.calls(p, "terminal.addToPath")) == 1 and "The line was added, but Terminal still can't see the command." in text(p), "added, still missing")
    r.shot(p, "first-terminal-path-still")
    p.context.close()

    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF, results={"terminal.turnOn": [PATH_MISSING], "terminal.addToPath": [{"ok": False, "reason": "Add ~/.local/bin to your shell's PATH by hand"}]}))
    p.get_by_role("button", name="Turn on").click()
    p.wait_for_timeout(400)
    p.get_by_role("button", name="Add it for me").click()
    p.wait_for_timeout(400)
    check("Add ~/.local/bin to your shell's PATH by hand" in text(p), "addToPath refusal shows its reason")
    r.shot(p, "first-terminal-path-refused")
    p.get_by_role("button", name="I'll do it myself").click()
    p.wait_for_timeout(300)
    check(r.calls(p, "firstLaunch.mark") == [["firstLaunch.mark", ["terminalAsked"]]], "I'll do it myself marks")
    p.context.close()

    for line, extra in [(STD_LINE, False), ("# added for anyscribe\n" + STD_LINE, True)]:
        p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF, results={"terminal.turnOn": [PATH_MISSING], "terminal.addToPath": [{"ok": False, "file": None, "reason": BASH_REASON, "line": line}]}))
        p.get_by_role("button", name="Turn on").click()
        p.wait_for_timeout(400)
        p.get_by_role("button", name="Add it for me").click()
        p.wait_for_timeout(400)
        pres = p.get_by_role("dialog").locator("pre.select-all")
        texts = [pres.nth(i).inner_text() for i in range(pres.count())]
        t = text(p)
        reason_el = p.get_by_role("dialog").locator("p", has_text=BASH_REASON[:30])
        shown_reason = BASH_REASON[: -len(line)].rstrip() if BASH_REASON.endswith(line) else BASH_REASON
        check(shown_reason in t and texts == [line] and (not BASH_REASON.endswith(line) or BASH_REASON not in t),
              f"AMEND 3/F4/G6: bash refusal shows its reason (without a repeated line) and only its line, selectable ({'own line' if extra else 'same line'})", texts)
        check("anyscribe can add this line" not in t and "text-red" not in (reason_el.first.get_attribute("class") or ""),
              "F4: no stale offer to add the line; the reason is guidance, not red")
        check(p.get_by_role("button", name="Add it for me").count() == 0, "AMEND 3: no second Add it for me after a refusal")
        r.shot(p, "first-terminal-bash-refused" + ("-own-line" if extra else ""))
        p.context.close()

    # F3: addToPath ok, with why it has no effect: that reason, not a generic line
    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF, results={"terminal.turnOn": [PATH_MISSING], "terminal.status": [OFF, PATH_MISSING],
                                                                     "terminal.addToPath": [{"ok": True, "file": "/Users/test/.zprofile", "line": STD_LINE, "reason": ZSHRC_REASON}]}))
    p.get_by_role("button", name="Turn on").click()
    p.wait_for_timeout(400)
    p.get_by_role("button", name="Add it for me").click()
    p.wait_for_timeout(400)
    t = text(p)
    check(ZSHRC_REASON in t and "The line was added" not in t, "F3: the app's reason replaces the generic sentence")
    check("Takes effect in new Terminal windows" not in t, "G6: no 'takes effect in new windows' under the finding that it doesn't")
    r.shot(p, "first-terminal-added-reason")
    p.context.close()

    # F5: off, with a copy at ~/.local/bin/anyscribe Terminal does not use: Switch in the offer
    OFF_OCC = {**OFF, "occupant": {"path": "/Users/test/.local/bin/anyscribe", "version": "0.19.0", "via": "uv"}}
    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF_OCC))
    t = text(p)
    check("Another anyscribe 0.19.0 is already at ~/.local/bin/anyscribe, installed with uv." in t and "Adds one small file" not in t
          and p.get_by_role("button", name="Switch to this app's copy").count() == 1 and p.get_by_role("button", name="Turn on").count() == 0,
          "F5: the offer names the copy and offers Switch instead of Turn on")
    r.shot(p, "first-terminal-occupant")
    p.get_by_role("button", name="Switch to this app's copy").click()
    p.wait_for_timeout(400)
    check(r.calls(p, "terminal.turnOn") == [["terminal.turnOn", [{"replace": True}]]] and "anyscribe is ready in Terminal" in text(p), "F5: Switch calls turnOn({replace:true})")
    p.context.close()

    # F12: without Claude Code: the "turn it off and on again" note, not the Claude Code sentence
    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal={**OFF, "claudeCode": False, "skill": "not-applicable"}))
    p.get_by_role("button", name="Turn on").click()
    p.wait_for_timeout(400)
    t = text(p)
    check("If Claude Code isn't on this Mac yet" in t and "In Claude Code, ask it" not in t, "F12: without Claude Code, its note only")
    p.context.close()

    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF, results={"terminal.turnOn": [{**ON_OK, "reason": SHELL_REASON}]}))
    p.get_by_role("button", name="Turn on").click()
    p.wait_for_timeout(400)
    check("anyscribe is ready in Terminal" in text(p) and SHELL_REASON in text(p), "AMEND 2: Turn on ok with a reason: ready card carries the reason")
    r.shot(p, "first-terminal-ready-reason")
    p.context.close()

    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF, results={"terminal.turnOn": [{**OFF, "ok": False, "reason": "anyscribe couldn't write ~/.local/bin/anyscribe (permission denied)."}]}))
    p.get_by_role("button", name="Turn on").click()
    p.wait_for_timeout(400)
    check("couldn't write ~/.local/bin/anyscribe" in text(p) and "Use anyscribe from Terminal" in text(p), "Turn on refused stays on the offer with the reason")
    r.shot(p, "first-terminal-refused")
    p.context.close()

    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OTHER_ELSEWHERE))
    t = text(p)
    check("Terminal already has anyscribe" in t and OTHER_ELSEWHERE["reason"] in t and p.get_by_role("button", name="Switch to this app's copy").count() == 0,
          "AMEND occupant: first-launch card without Switch, with the reason")
    check(p.get_by_role("button", name="OK").count() == 1 and p.get_by_role("button", name="Keep the one I have").count() == 0, "F16: its only button reads OK")
    r.shot(p, "first-terminal-other-elsewhere")
    p.context.close()

    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF, results={"terminal.turnOn": [ON_UNKNOWN]}))
    p.get_by_role("button", name="Turn on").click()
    p.wait_for_timeout(400)
    t = text(p)
    check("The anyscribe command is added" in t and "ready in Terminal" not in t and "It runs this app's" not in t and ON_UNKNOWN["reason"] in t
          and "Open a new Terminal window and type anyscribe --help to check." in t, "C5: shell not asked: 'The anyscribe command is added', the reason, how to check")
    r.shot(p, "first-terminal-added-unknown")
    p.context.close()

    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF, results={"terminal.turnOn": [{**ON_UNKNOWN, "skill": "missing"}]}))
    p.get_by_role("button", name="Turn on").click()
    p.wait_for_timeout(400)
    check("The anyscribe command is added, but the Claude Code skill couldn't be installed" in text(p) and "Terminal is ready" not in text(p),
          "C5: the skill card's title when the shell wasn't asked")
    p.context.close()

    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch={"oldLauncherAsked": False, "terminalAsked": True}, results={"oldLauncher.remove": [REFUSED]}))
    p.get_by_role("button", name="Remove the old launcher").click()
    p.wait_for_timeout(400)
    t = text(p)
    check("Removing the old launcher restarts the engine. " + REFUSED["reason"] in t and "Replace the old anyscribe launcher?" in t and "Cleanup didn't finish" not in t, "AMEND launcher/F6: first-launch refusal shows its reason, prefixed, on the question")
    r.shot(p, "first-launcher-refused")
    p.context.close()

    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch={"oldLauncherAsked": False, "terminalAsked": True}, results={"oldLauncher.remove": [REMOVED_NOT_CARRIED]}))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 1200)
    t = text(p)
    check("Old launcher removed" in t and REMOVED_NOT_CARRIED["reason"] in t and "starts at login instead" not in t, "AMEND carry-over: first-launch card shows the reason")
    r.shot(p, "first-launcher-removed-not-carried")
    p.context.close()

    # amendment 2: removal restarts the engine, the page reloads mid-call, the result comes from lastRemoval
    unasked_l = {"oldLauncherAsked": False, "terminalAsked": True}
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=unasked_l, restartMs=2500))
    p.get_by_role("button", name="Remove the old launcher").click()
    p.wait_for_timeout(250)
    check("Restarting anyscribe's engine." in text(p), "AMEND2/F2: the restarting banner covers the gap, in the asked-for words")
    r.shot(p, "first-launcher-removing")
    after_reload(p, 3000)
    t = text(p)
    check(reloads(p) == 1 and p.url == A.url + "/", "AMEND2: the app reloaded the page to / during remove()", p.url)
    check("Old launcher removed" in t and "This app now starts at login instead" in t and "Replace the old" not in t, "AMEND2: after the reload the result card comes from lastRemoval")
    check(r.calls(p, "oldLauncher.remove") == [["oldLauncher.remove", []]] and r.calls(p, "firstLaunch.mark") == [["firstLaunch.mark", ["oldLauncherAsked"]]], "AMEND2: one removal, one mark")
    r.shot(p, "first-launcher-removed-after-reload")
    p.get_by_role("button", name="OK").click()
    p.wait_for_timeout(200)
    p.reload()
    p.wait_for_timeout(900)
    check(p.get_by_role("dialog").count() == 0, "AMEND2: the result never repeats after another reload")
    p.context.close()

    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=unasked_l,
                           results={"oldLauncher.remove": [REMOVE_FAIL, REMOVED_OK]}))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 1500)
    t = text(p)
    check("Cleanup didn't finish" in t and "Old menu bar icon: still running" in t, "AMEND2: the checklist after the reload")
    r.shot(p, "first-launcher-failed-after-reload")
    p.get_by_role("dialog").get_by_role("button", name="Try again").click()
    after_reload(p, 1500)
    t = text(p)
    check(len(r.calls(p, "oldLauncher.remove")) == 2 and "Old launcher removed" in t and "Cleanup didn't finish" not in t, "AMEND2: Try again reloads again and shows Removed")
    p.context.close()

    p = r.open(A, "/", cfg(launcher=LAUNCHER, lastRemoval={**REMOVED_OK, "at": 1000}, removingNote=True))
    check(p.get_by_role("dialog").count() == 0, "AMEND2: an older lastRemoval is never shown")
    p.context.close()

    p = r.open(A, "/settings", cfg(launcher=LAUNCHER))
    p.get_by_role("button", name="Remove it").click()
    after_reload(p, 1500)
    t = text(p)
    check("Old launcher removed" in t and p.get_by_role("dialog").count() == 1 and "Still installed" not in t, "AMEND2: Settings Remove it, result after the reload")
    r.shot(p, "settings-launcher-removed-after-reload")
    p.context.close()

    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=unasked_l, results={"oldLauncher.remove": [REFUSED]}))
    p.get_by_role("button", name="Remove the old launcher").click()
    p.wait_for_timeout(1200)
    check("Removing the old launcher restarts the engine. " + REFUSED["reason"] in text(p) and reloads(p) == 0,
          "AMEND2/F6: a refusal answers at once, says the removal restarts the engine, no reload")
    check(p.evaluate("localStorage.getItem('anyscribe_launcher_removing')") is None, "C7: a refusal clears the note at once")
    p.context.close()

    # C6: each question is asked once; Escape and a click outside are the quiet answer
    p = r.open(A, "/", cfg(firstLaunch=tonly, terminal=OFF))
    p.keyboard.press("Escape")
    p.wait_for_timeout(300)
    check(p.get_by_role("dialog").count() == 0 and r.calls(p, "firstLaunch.mark") == [["firstLaunch.mark", ["terminalAsked"]]] and not r.calls(p, "terminal.turnOn"),
          "C6: Escape on the Terminal card is Skip for now (marked, nothing turned on)")
    p.reload()
    p.wait_for_timeout(800)
    check(p.get_by_role("dialog").count() == 0, "C6: and it is not asked again")
    p.context.close()

    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch={"oldLauncherAsked": False, "terminalAsked": True}))
    p.mouse.click(5, 5)  # outside the card
    p.wait_for_timeout(300)
    check(p.get_by_role("dialog").count() == 0 and r.calls(p, "firstLaunch.mark") == [["firstLaunch.mark", ["oldLauncherAsked"]]] and not r.calls(p, "oldLauncher.remove"),
          "C6: a click outside the launcher question is Keep both (marked, nothing removed)")
    p.context.close()

    # C6: the app couldn't save the answer: the choice still goes ahead, and he is told why it may come back
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch={"oldLauncherAsked": False, "terminalAsked": True}, markFails=True))
    p.get_by_role("button", name="Keep both").click()
    p.wait_for_timeout(400)
    t = text(p)
    check("anyscribe couldn't save your answer" in t and "EACCES" in t and "The old launcher question may come back the next time anyscribe starts." in t,
          "C6: a failed save is shown with its reason, naming the question (G5)")
    r.shot(p, "first-mark-failed")
    p.get_by_role("button", name="OK").click()
    p.wait_for_timeout(200)
    check(p.get_by_role("dialog").count() == 0, "C6: OK closes the notice")
    p.context.close()

    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch={"oldLauncherAsked": False, "terminalAsked": True}, markFails=True,
                           results={}))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 1500)
    check(r.calls(p, "oldLauncher.remove") == [["oldLauncher.remove", []]] and "Old launcher removed" in text(p),
          "C6: with the save failing, the removal still runs and its result shows")
    p.get_by_role("button", name="OK").click()
    p.wait_for_timeout(300)
    check("anyscribe couldn't save your answer" in text(p), "C6: then the failed save is explained (kept across the reload)")
    p.context.close()

    # G5: both questions' saves failed: the card says both may come back
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch={"oldLauncherAsked": False, "terminalAsked": False}, terminal=OFF, markFails=True))
    p.get_by_role("button", name="Keep both").click()
    p.wait_for_timeout(500)
    p.get_by_role("button", name="Skip for now").click()
    p.wait_for_timeout(500)
    t = text(p)
    check("These questions may come back the next time anyscribe starts." in t, "G5: both questions named when both saves failed", t[-300:])
    # stub self-check: a failed mark is the app's memory only (asked), not its disk
    check(p.evaluate("JSON.parse(sessionStorage.getItem('__stub_marks_mem')||'{}').oldLauncherAsked === true && !JSON.parse(localStorage.getItem('__stub_marks')||'{}').oldLauncherAsked"),
          "stub self-check: a failed mark is held in memory, not written to disk")
    p.get_by_role("button", name="OK").click()
    p.wait_for_timeout(200)
    p.reload()
    p.wait_for_timeout(800)
    check(p.get_by_role("dialog").count() == 0, "stub self-check: while the app runs, a failed mark still reads asked")
    p.evaluate("sessionStorage.clear()")  # as the app quitting: its memory goes, the disk stays
    p.reload()
    p.wait_for_timeout(900)
    check("Replace the old anyscribe launcher?" in text(p), "stub self-check: after the app's memory is gone, the unsaved question comes back")
    p.context.close()



def s_removal_reload(r: Run):
    """Round 1: the removal's result across the app's reload (C7, C2, F9), on its own so a failure
    in first_launch cannot hide these."""
    unasked_l = {"oldLauncherAsked": False, "terminalAsked": True}
    # C7: remove() settles just before the old page is replaced; the kept note still finds the result
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=unasked_l, results={}))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 1500)
    t = text(p)
    check(reloads(p) == 1 and "Old launcher removed" in t and p.get_by_role("dialog").count() == 1,
          "C7: settled before the reload, the reloaded page still shows the result", t[:300])
    check(p.evaluate("localStorage.getItem('anyscribe_launcher_removing')") is None, "C7: claimed, the note is gone")
    p.keyboard.press("Escape")  # closed without OK: the claim itself must have used the note up
    p.wait_for_timeout(200)
    p.reload()
    p.wait_for_timeout(900)
    check(p.get_by_role("dialog").count() == 0, "C7: closed with Escape, not shown again after another reload")
    p.context.close()

    # C7: settled with no reload (the card shows it); the note stays until the card is closed
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=unasked_l, componentNoReload=True))
    p.get_by_role("button", name="Remove the old launcher").click()
    p.wait_for_timeout(600)
    kept = p.evaluate("localStorage.getItem('anyscribe_launcher_removing')")
    p.get_by_role("button", name="OK").click()
    p.wait_for_timeout(200)
    check(kept is not None and p.evaluate("localStorage.getItem('anyscribe_launcher_removing')") is None,
          "[component] C7: the note is kept while the result card is open, gone once it is closed", kept)
    p.context.close()

    # C2: the removal threw; the app kept {ok: false, pieces: null, reason}; the reloaded page shows it
    THREW = {"ok": False, "pieces": None, "startAtLoginCarriedOver": False, "reason": "The removal failed: spawn python ENOENT"}
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=unasked_l, removalThrew=True,
                           results={"oldLauncher.remove": [THREW, REMOVED_OK]}))
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 1500)
    t = text(p)
    check(not errors and "Cleanup didn't finish" in t and THREW["reason"] in t and p.get_by_role("dialog").get_by_role("button", name="Try again").count() == 1
          and p.get_by_role("dialog").get_by_role("button", name="Close").count() == 1,
          "C2: a kept result with no pieces shows its reason, Try again and Close (no crash)", errors or t[:300])
    r.shot(p, "first-launcher-threw-after-reload")
    p.get_by_role("dialog").get_by_role("button", name="Close").click()
    p.wait_for_timeout(200)
    check(p.get_by_role("dialog").count() == 0 and p.evaluate("localStorage.getItem('anyscribe_launcher_removing')") is None, "C2: Close consumes it")
    p.context.close()

    # F9: no login item and no running menu bar icon before: the Removed card names only the launcher
    p = r.open(A, "/", cfg(launcher={"installed": True, "pieces": {"launcher": "present", "loginItem": "absent", "menuBarIcon": "running"}},
                           firstLaunch=unasked_l, results={"oldLauncher.remove": [{**REMOVED_OK, "startAtLoginCarriedOver": False}]}))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 1200)
    t = text(p)
    check("Removed the old launcher and its menu bar icon." in t and "login item" not in t, "F9: names only what was there (no login item)")
    p.context.close()



def route_transcribe(p, refuse):
    """POST /api/transcribe: refused (500) for paths in the set `refuse`, else accepted as a job that
    stays running (the engine never heard of it)."""
    def handle(route):
        body = json.loads(route.request.post_data or "{}")
        if body.get("url") in refuse:
            route.fulfill(status=500, body='{"detail": "the engine refused this one"}', content_type="application/json")
        else:
            route.fulfill(json={"job_id": "j-check", "provider": "openai", "model": "gpt-4o-transcribe", "notes": []})
    p.route("**/api/transcribe", handle)
    p.route("**/api/jobs/j-check", lambda route: route.fulfill(json={"status": "running"}))
    p.route_web_socket("**/api/ws/jobs/**", lambda ws: None)


def queue(p):
    return json.loads(p.evaluate("sessionStorage.getItem('anyscribe_incoming') || '[]'"))


def s_r2_facts(r: Run):
    """Round 2: every decision from a fact (accepted, running, the app's saved lastRemoval)."""
    A_ = f"{FILE_DIR}/a.m4a"
    B_ = f"{FILE_DIR}/b.m4a"

    # A1: refused A with B waiting: A stays at the head, B waits, nothing posted for B
    p = r.open(A, "/", cfg())
    refuse = {A_}
    route_transcribe(p, refuse)
    p.evaluate(f"window.__openFile('{A_}'); window.__openFile('{B_}')")
    p.wait_for_timeout(1200)
    posts = [x["url"] for x in transcribe_posts(p)]
    check(queue(p) == [A_, B_] and posts == [A_] and "Transcription failed" in text(p),
          "A1: refused A, B waiting: the stored queue is exactly [A, B] and only A was posted", (queue(p), posts))
    check("Up next: b.m4a." in text(p) and "Up next: a.m4a" not in text(p), "A1: Up next names B, not the failed head")
    r.shot(p, "r2-queue-refused-head")
    refuse.clear()
    p.get_by_role("button", name="Try again").click()
    p.wait_for_timeout(800)
    posts = [x["url"] for x in transcribe_posts(p)]
    check(posts == [A_, A_] and queue(p) == [B_], "A1: Try again posts A, then the queue is exactly [B]", (queue(p), posts))
    p.context.close()

    # G1: the engine is down when B arrives: no post and no failure; after the reload, one post with B's path
    p = r.open(A, "/", cfg())
    route_transcribe(p, set())
    p.evaluate("window.__emit({state: 'restarting'})")
    p.wait_for_timeout(200)
    p.evaluate(f"window.__openFile('{B_}')")
    p.wait_for_timeout(1000)
    check(not transcribe_posts(p) and "Transcription failed" not in text(p) and queue(p) == [B_],
          "G1: engine down: nothing posted, no failure, B kept", (queue(p), transcribe_posts(p)))
    p.evaluate("window.__emit({state: 'running'})")
    after_reload(p, 1200)
    posts = [x["url"] for x in transcribe_posts(p)]
    check(posts == [B_] and queue(p) == [], "G1: after the reload, exactly one post, carrying B's path", (posts, queue(p)))
    p.context.close()

    # A1: a failed typed link while B waits, then New: B is not dropped
    L = "https://www.youtube.com/watch?v=typed"
    p = r.open(A, "/", cfg())
    route_transcribe(p, {L, B_})
    p.fill("input[type=text]", L)
    p.get_by_role("button", name="Transcribe").click()
    p.wait_for_timeout(500)
    p.evaluate(f"window.__openFile('{B_}')")
    p.wait_for_timeout(500)
    check(queue(p) == [B_] and [x["url"] for x in transcribe_posts(p)] == [L], "A1: B waits behind the typed link's error, not posted")
    p.get_by_role("button", name="New").click()
    p.wait_for_timeout(900)
    check(queue(p) == [B_] and [x["url"] for x in transcribe_posts(p)] == [L, B_],
          "A1: New after a typed link's failure keeps B (then B is tried, and stays at the head when refused)", (queue(p), transcribe_posts(p)))
    p.context.close()

    # A2: removal pending, a crash during its job check, the refusal, the reload; then a crash while watching J
    J = "https://www.youtube.com/watch?v=jay"
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch={"oldLauncherAsked": False, "terminalAsked": True}, refusalMs=800,
                           results={"oldLauncher.remove": [{"ok": False, "pieces": None, "startAtLoginCarriedOver": False,
                                                             "reason": "The engine was stopped while the restart was being checked."}]}))
    route_transcribe(p, set())
    p.get_by_role("button", name="Remove the old launcher").click()
    p.wait_for_timeout(200)
    p.evaluate("window.__emit({state: 'restarting'})")  # the crash, while the removal's job check is pending
    p.wait_for_timeout(1000)
    p.evaluate("window.__emit({state: 'running'})")
    after_reload(p, 1200)
    check(p.evaluate("localStorage.getItem('anyscribe_launcher_removing')") is None and p.get_by_role("dialog").count() == 0,
          "A2: after the reload, the unmatched note is gone and no result is shown")
    p.fill("input[type=text]", J)
    p.get_by_role("button", name="Transcribe").click()
    p.wait_for_timeout(400)
    p.evaluate("window.__emit({state: 'restarting'})")
    p.wait_for_timeout(200)
    t = text(p)
    check("anyscribe's engine stopped. Restarting it." in t, "A2: a later crash reads as a crash", t[:200])
    p.evaluate("window.__emit({state: 'running'})")
    after_reload(p, 1200)
    t = text(p)
    check("Running again" in t and J in t, "A2: and Running again names J", t[:300])
    p.context.close()

    # A2: a thrown removal settling just before the reload: the reloaded card shows its reason
    THREW = {"ok": False, "pieces": None, "startAtLoginCarriedOver": False, "reason": "The removal failed: spawn python ENOENT"}
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch={"oldLauncherAsked": False, "terminalAsked": True}, removalThrew=True,
                           results={"oldLauncher.remove": [THREW]}))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 1500)
    t = text(p)
    check(reloads(p) == 1 and THREW["reason"] in t and "Cleanup didn't finish" in t,
          "A2: a thrown removal settled just before the reload: the reloaded card shows its reason", t[:300])
    p.context.close()

    # A3/G3/G2: removal ok, carried over, the engine didn't start again: the card says so, and the banner
    X = "anyscribe's engine didn't start again afterwards: another program is using port 8470"  # bare, as engine.js gives it
    OKX = {"ok": True, "pieces": {"launcher": "removed", "loginItem": "removed", "menuBarIcon": "stopped"}, "startAtLoginCarriedOver": True, "reason": X}
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch={"oldLauncherAsked": False, "terminalAsked": True}, removalEngineStops=True,
                           results={"oldLauncher.remove": [OKX], "restartEngine": [{"ok": False, "reason": "Port 8470 is still in use."}, {"ok": True}]}))
    p.get_by_role("button", name="Remove the old launcher").click()
    p.wait_for_timeout(1200)
    t = text(p)
    check("Old launcher removed" in t and "This app now starts at login instead" in t and X in t, "A3/G3: carried over and the engine reason: both shown")
    check("anyscribe's engine stopped" in t and "It couldn't start again. Your transcripts are safe. The engine exited with code 1; the reason wasn't reported." in t,
          "G2: the stopped engine gets its red card", t[:400])
    r.shot(p, "r2-removed-engine-stopped")
    p.keyboard.press("Escape")  # the card closed without OK: its note waits for the running engine
    p.wait_for_timeout(300)
    p.locator("[role=status]").get_by_role("button", name="Restart engine").click()
    p.wait_for_timeout(400)
    check("Port 8470 is still in use." in text(p), "G2: a refused Restart shows its reason under the stopped card")
    p.locator("[role=status]").get_by_role("button", name="Copy details").click()
    p.wait_for_timeout(200)
    check("Engine: stopped, couldn't start again" in p.evaluate("navigator.clipboard.readText()"), "G2: Copy details names the stopped state")
    p.locator("[role=status]").get_by_role("button", name="Restart engine").click()
    after_reload(p, 1500)
    t = text(p)
    check(X + ". It is running again now." in t, "A3, K4: claimed after the reload, the card adds that it is running again now, after a full stop", t[:400])
    p.context.close()

    # A5/G4: the Settings card names only what was there before (no reload: the engine didn't start again)
    ICON_ONLY = {"installed": True, "pieces": {"launcher": "absent", "loginItem": "absent", "menuBarIcon": "running"}}
    p = r.open(A, "/settings", cfg(launcher=ICON_ONLY, removalEngineStops=True,
                                   results={"oldLauncher.remove": [{**REMOVED_OK, "startAtLoginCarriedOver": False, "reason": X}]}))
    p.get_by_role("button", name="Remove it").click()
    p.wait_for_timeout(1200)
    t = text(p)
    check("Stopped the old menu bar icon. The launcher and login item were already gone." in t and "Removed the old launcher" not in t,
          "A5/G4: Settings' card names the icon only, from the pieces read before")
    r.shot(p, "r2-settings-icon-only", "#this-mac")
    p.context.close()

    # A2/G7: a removal note left by an open result card is not "his restart": a crash then reads as one
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch={"oldLauncherAsked": False, "terminalAsked": True}, componentNoReload=True))
    p.get_by_role("button", name="Remove the old launcher").click()
    p.wait_for_timeout(700)
    noted = p.evaluate("localStorage.getItem('anyscribe_launcher_removing')") is not None
    p.evaluate("window.__emit({state: 'restarting'})")
    p.wait_for_timeout(200)
    t = text(p)
    check(noted and "anyscribe's engine stopped. Restarting it." in t and "Restarting anyscribe's engine." not in t,
          "[component] A2/G7: with the removal's card still open (its note kept), a crash reads as a crash", t[:200])
    p.context.close()

    # A5: no snapshot of what was there: the plain sentence
    p = r.open(A, "/", cfg(launcher=NO_LAUNCHER, removingNote=True, lastRemoval={**REMOVED_OK, "at": 9e12}))
    p.wait_for_timeout(900)
    check("Cleanup finished. Nothing of the old launcher is left on this Mac." in text(p), "A5: no snapshot, no guess about pieces")
    p.context.close()

    # stub self-check: after a removal and the reload, the app's memory changed as the real app's does
    p = r.open(A, "/settings", cfg(launcher=LAUNCHER, terminal=OFF))
    p.get_by_role("switch", name="Use from Terminal and Claude Code").click()
    p.wait_for_timeout(400)
    p.get_by_role("button", name="Remove it").click()
    after_reload(p, 1200)
    p.get_by_role("button", name="OK").click()
    p.goto(A.url + "/settings")
    p.wait_for_timeout(900)
    t = text(p)
    check("On. Terminal runs this app's anyscribe" in t and "On. anyscribe starts in the menu bar" in t and "Old browser launcher" not in t,
          "stub self-check: after removal and reload, Start at login on, launcher gone, Terminal kept", t[:600])
    p.context.close()


def s_r3_facts(r: Run):
    """Round 3: a doomed page starts nothing; callbacks act only on the note present at page load."""
    B_ = f"{FILE_DIR}/b.m4a"
    LOGIN = "This app is set to start at login, but macOS needs your approval: System Settings, General, Login Items."
    X = "Cleanup didn't finish: the old menu bar icon is still running. " + LOGIN  # as old-launcher.js builds it
    unasked_l = {"oldLauncherAsked": False, "terminalAsked": True}
    OKX = {"ok": True, "pieces": {"launcher": "removed", "loginItem": "removed", "menuBarIcon": "stopped"},
           "startAtLoginCarriedOver": True, "reason": LOGIN}

    # H1: engine down, B opened, reloadDelay 300: only the reloaded page posts B
    p = r.open(A, "/", cfg(reloadDelay=300))
    route_transcribe(p, set())
    p.evaluate("window.__emit({state: 'restarting'})")
    p.wait_for_timeout(200)
    p.evaluate(f"window.__openFile('{B_}')")
    p.wait_for_timeout(500)
    p.evaluate("window.__emit({state: 'running'})")
    after_reload(p, 1200)
    check(p.tagged == [(B_, "1")] and p.get_by_role("button", name="Stop").count() == 1,
          "H1: exactly one POST, body B, sent by the reloaded page; its progress (Stop) is there", p.tagged)
    p.context.close()

    # H1, first read: the page loads with the engine at restarting (no event), then it comes back
    p = r.open(A, "/", cfg(reloadDelay=300, engine={**RUNNING, "state": "restarting"}, engineDownApi=False))
    route_transcribe(p, set())
    p.evaluate(f"window.__openFile('{B_}')")
    p.wait_for_timeout(500)
    p.evaluate("window.__emit({state: 'running'})")
    after_reload(p, 1200)
    check(p.tagged == [(B_, "1")] and p.get_by_role("button", name="Stop").count() == 1,
          "H1: a page that first read 'restarting' is doomed too: only the reloaded page posts B", p.tagged)
    p.context.close()

    # B1: no note at load; Remove while the engine still reads running (its job check); the reloaded card shows X
    REMX = {"ok": True, "pieces": {"launcher": "removed", "loginItem": "removed", "menuBarIcon": "stopped"},
            "startAtLoginCarriedOver": False, "reason": "B1-X: the removal's own reason."}
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=unasked_l, slowStatus={"0:2": 900}, removeCheckMs=700,
                           results={"oldLauncher.remove": [REMX]}))
    before_click = len(r.calls(p, "oldLauncher.status"))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 2600)
    t = text(p)
    check(before_click == 1 and "B1-X: the removal's own reason." in t and "Old launcher removed" in t,
          "B1: no note at load, no recovery read; the reloaded card shows the removal's reason X", (before_click, t[:300]))
    p.context.close()

    # B1, note at load: Remove from Settings while the recovery read is pending: the click's note survives
    # status calls on Settings: 1 App's question read, 2 the recovery read (slow here), 3 This Mac's row
    # The recovery read answers 4 s after load: after the click (the page is ready in under 2 s), and
    # while the removal's job check (5 s) keeps the engine reading running.
    p = r.open(A, "/settings", cfg(launcher=LAUNCHER, removingNote=True, slowStatus={"0:2": 4000}, removeCheckMs=5000,
                                   results={"oldLauncher.remove": [REMX]}))
    old_at = int(p.evaluate("sessionStorage.getItem('__stub_noted_at')"))
    clicked_ms = p.evaluate("performance.now()")
    p.get_by_role("button", name="Remove it").click()
    p.wait_for_timeout(max(0, 4300 - clicked_ms))  # until just after the recovery read has answered
    stored = p.evaluate("localStorage.getItem('anyscribe_launcher_removing')")
    stored_at = json.loads(stored)["at"] if stored else None
    after_reload(p, 6500)
    t = text(p)
    check(clicked_ms < 4000 and stored_at is not None and stored_at != old_at and "B1-X: the removal's own reason." in t,
          "B1: the stored note is the click's, not the predecessor's; the reloaded card shows X", (old_at, stored_at, t[:200]))
    p.context.close()

    # Doomed recovery: restarting arrives before the recovery read returns
    # The engine leaves running and is back before the read answers; the read answers in the window
    # before the app's reload (reloadDelay 4 s), when the engine reads running on the doomed old page.
    p = r.open(A, "/", cfg(launcher=NO_LAUNCHER, removingNote=True, lastRemoval={**OKX, "reason": "DOOM-X", "at": 9e12},
                           slowStatus={"0:2": 4000}, reloadDelay=4000))
    note0 = p.evaluate("localStorage.getItem('anyscribe_launcher_removing')")
    pending = p.get_by_role("dialog").count() == 0  # the recovery read has not answered yet
    p.evaluate("window.__emit({state: 'restarting'})")
    p.wait_for_timeout(200)
    p.evaluate("window.__oldPage = 1; window.__emit({state: 'running'})")  # the reload follows 4 s later
    p.wait_for_timeout(max(0, 4500 - p.evaluate("performance.now()")))  # the read has answered, the old page is still here
    still_old = p.evaluate("window.__oldPage === 1")
    note1 = p.evaluate("localStorage.getItem('anyscribe_launcher_removing')")
    no_card = p.get_by_role("dialog").count() == 0
    after_reload(p, 4500)
    check(still_old and pending and no_card and note0 == note1 and note0 is not None and "DOOM-X" in text(p),
          "Doomed recovery: no card and the note unchanged on the old page; the reloaded card shows X", (still_old, pending, no_card, note0 == note1))
    p.context.close()

    # H3: both questions unasked, Remove, reload: no Terminal status read until the removal card's OK
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch={"oldLauncherAsked": False, "terminalAsked": False}, terminal=OFF,
                           slowStatus={"2": 800}))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 1800)
    held = r.calls(p, "terminal.status")
    shown = "Old launcher removed" in text(p)
    p.get_by_role("button", name="OK").click()
    p.wait_for_timeout(600)
    check(held == [] and shown and r.calls(p, "terminal.status") == [["terminal.status", []]] and "One more option".upper() in text(p).upper(),
          "H3: terminal.status calls are [] until OK, then exactly one", held)
    p.context.close()

    # B2: partial cleanup with reason X: the card shows X and the checklist
    PART = {"ok": False, "pieces": {"launcher": "removed", "loginItem": "removed", "menuBarIcon": "still running"},
            "startAtLoginCarriedOver": False, "reason": X}  # the approval note comes only with False (old-launcher.js:187)
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=unasked_l, results={"oldLauncher.remove": [PART]}))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 1400)
    t = text(p)
    check(LOGIN in t and "Cleanup didn't finish: the old menu bar icon" not in t and "Old menu bar icon: still running" in t and "Launcher: removed" in t
          and t.index("Log out and back in to stop it, or try again.") < t.index(LOGIN),
          "B2, K1: the checklist card shows what the bridge adds, below the advice, without repeating its opening sentence", t[:400])
    r.shot(p, "r3-partial-reason")
    p.context.close()

    # B3: a normal removal settles after the engine is running again
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch=unasked_l))
    p.get_by_role("button", name="Remove the old launcher").click()
    after_reload(p, 1400)
    check(p.evaluate("sessionStorage.getItem('__stub_remove_settled_engine')") == "running",
          "B3: the engine read 'running' when remove() settled")
    p.context.close()

    # H2: engine stopped; a file dropped in the idle view, and in the completed view: named, not posted
    p = r.open(A, "/", cfg())
    route_transcribe(p, set())
    p.evaluate("window.__emit({state: 'stopped', stoppedRestarting: false, lastExit: {code: 1, signal: null, reason: null}})")
    p.wait_for_timeout(200)
    p.evaluate(f"window.__openFile('{B_}')")
    p.wait_for_timeout(600)
    t = text(p)
    check("Up next: b.m4a. It starts once anyscribe's engine is running again." in t and p.tagged == [],
          "H2: idle view names the waiting file; zero POSTs", p.tagged)
    r.shot(p, "r3-idle-waiting")
    p.context.close()

    DONE = {"step": "done", "status": "completed", "message": "Done",
            "data": {"file_path": "/Users/test/anyscribe/clip.md", "title": "Clip", "platform": "local", "duration": "0:42",
                     "language": "en", "word_count": 120, "provider": "openai", "model": "gpt-4o-transcribe"}}
    p = r.open(A, "/", cfg())
    p.route("**/api/transcribe", lambda route: route.fulfill(json={"job_id": "j-done", "provider": "openai", "model": "gpt-4o-transcribe", "notes": []}))
    p.route_web_socket("**/api/ws/jobs/**", lambda ws: ws.send(json.dumps(DONE)))
    p.fill("input[type=text]", "https://www.youtube.com/watch?v=done")
    p.get_by_role("button", name="Transcribe").click()
    p.wait_for_timeout(800)
    done_view = "Clip" in text(p) and p.get_by_role("button", name="Stop").count() == 0
    p.evaluate("window.__emit({state: 'stopped', stoppedRestarting: false, lastExit: {code: 1, signal: null, reason: null}})")
    p.wait_for_timeout(200)
    p.evaluate(f"window.__openFile('{B_}')")
    p.wait_for_timeout(600)
    t = text(p)
    check(done_view and "Up next: b.m4a. It starts once anyscribe's engine is running again." in t
          and [u for u, _ in p.tagged] == ["https://www.youtube.com/watch?v=done"],
          "H2: completed view names the waiting file; no POST for it", (done_view, p.tagged))
    r.shot(p, "r3-completed-waiting")
    p.context.close()

    # K3 (lead): Up next under a running job, and under an error, while the engine is down
    p = r.open(A, "/", cfg())
    route_transcribe(p, {"https://www.youtube.com/watch?v=bad"})
    p.fill("input[type=text]", "https://www.youtube.com/watch?v=run")
    p.get_by_role("button", name="Transcribe").click()
    p.wait_for_timeout(600)
    p.evaluate(f"window.__openFile('{B_}')")
    p.wait_for_timeout(400)
    up = "Up next: b.m4a. It starts when this one finishes." in text(p)
    p.evaluate("window.__emit({state: 'stopped', stoppedRestarting: false, lastExit: {code: 1, signal: null, reason: null}})")
    p.wait_for_timeout(400)
    t = text(p)
    check(up and p.get_by_role("button", name="Stop").count() == 1 and "Up next: b.m4a. It starts once anyscribe's engine is running again." in t,
          "K3: under a running job, Up next says it waits for the engine while the engine is down", (up, t[:300]))
    r.shot(p, "r4-running-waiting")
    p.context.close()
    p = r.open(A, "/", cfg())
    route_transcribe(p, {"https://www.youtube.com/watch?v=bad"})
    p.fill("input[type=text]", "https://www.youtube.com/watch?v=bad")
    p.get_by_role("button", name="Transcribe").click()
    p.wait_for_timeout(600)
    p.evaluate(f"window.__openFile('{B_}')")
    p.wait_for_timeout(400)
    up = "Up next: b.m4a. It waits until you try this one again or choose New." in text(p)
    p.evaluate("window.__emit({state: 'stopped', stoppedRestarting: false, lastExit: {code: 1, signal: null, reason: null}})")
    p.wait_for_timeout(400)
    t = text(p)
    check(up and "Up next: b.m4a. It starts once anyscribe's engine is running again." in t and [u for u, _ in p.tagged] == ["https://www.youtube.com/watch?v=bad"],
          "K3: under an error, Up next says it waits for the engine while the engine is down; nothing posted for B", (up, p.tagged, t[:300]))
    r.shot(p, "r4-error-waiting")
    p.context.close()

    # E1 (lead, round 5): a failed dropped file stays ahead of B; B is said to start after it, and does not jump it
    A_ = f"{FILE_DIR}/a.m4a"
    p = r.open(A, "/", cfg(reloadDelay=300))
    route_transcribe(p, {A_})
    p.evaluate(f"window.__openFile('{A_}'); window.__openFile('{B_}')")
    p.wait_for_timeout(800)
    p.evaluate("window.__emit({state: 'stopped', stoppedRestarting: false, lastExit: {code: 1, signal: null, reason: null}})")
    p.wait_for_timeout(400)
    down = "Up next: b.m4a. It starts after a.m4a, which is tried again once anyscribe's engine is running again." in text(p)
    r.shot(p, "r5-failed-head-waiting")
    p.evaluate("window.__emit({state: 'running'})")
    after_reload(p, 1500)
    t = text(p)
    check(down and [u for u, _ in p.tagged] == [A_, A_] and queue(p) == [A_, B_]
          and "Up next: b.m4a. It waits until you try this one again or choose New." in t,
          "E1: B is said to start after the failed a.m4a; after recovery a.m4a is tried again first and B still waits", (down, p.tagged, queue(p), t[:300]))
    p.context.close()


def s_first_launch_marked(r: Run):
    p = r.open(A, "/", cfg(launcher=LAUNCHER, firstLaunch={"oldLauncherAsked": True, "terminalAsked": True}, terminal=OFF))
    check(p.get_by_role("dialog").count() == 0, "GUARD repeat: both marked, nothing asked")
    p.context.close()


def s_wizard(r: Run):
    p = r.open(B, "/", cfg(firstLaunch={"oldLauncherAsked": True, "terminalAsked": False}, terminal=OFF), dismissed=False, key_ok=True)
    check("Welcome to anyscribe" in text(p) and "Use anyscribe from Terminal" not in text(p), "new person: the wizard, not the separate card")
    walk_wizard(p)
    t = text(p)
    check("One last thing" in t and "All set" not in t and "LAST STEP · OPTIONAL" in t.upper() and "Use anyscribe from Terminal and Claude Code" in t,
          "Terminal is the wizard's last step, titled One last thing (F13)")
    r.shot(p, "wizard-terminal-step")
    p.get_by_role("dialog").get_by_role("button", name="Skip for now").click()
    p.wait_for_timeout(500)
    check(r.calls(p, "firstLaunch.mark") == [["firstLaunch.mark", ["terminalAsked"]]] and p.get_by_role("dialog").count() == 0, "Skip for now marks and closes the wizard, no second card")
    p.context.close()


def s_wizard_escape(r: Run):
    p = r.open(B3, "/", cfg(firstLaunch={"oldLauncherAsked": True, "terminalAsked": False}, terminal=OFF), dismissed=False, key_ok=True)
    walk_wizard(p)
    p.keyboard.press("Escape")
    p.wait_for_timeout(500)
    check(r.calls(p, "firstLaunch.mark") == [["firstLaunch.mark", ["terminalAsked"]]] and not r.calls(p, "terminal.turnOn") and p.get_by_role("dialog").count() == 0,
          "C6: Escape on the wizard's Terminal step is Skip for now: marked, nothing turned on")
    p.context.close()


def walk_wizard(p):
    p.get_by_role("button", name="Let's go").click()
    p.locator("[data-choice=cloud]").click()
    p.get_by_role("button", name="OpenAI Whisper").click()
    p.get_by_role("dialog").locator("input").first.fill("sk-check-not-a-real-key-1234567890")
    p.get_by_role("button", name="Next").click()
    p.get_by_role("button", name="Skip, next").click()
    p.get_by_role("button", name="Next").click()
    p.get_by_role("button", name="Finish & start transcribing").click()
    p.wait_for_timeout(800)


def s_wizard_browser(r: Run):
    p = r.open(B2, "/", None, dismissed=False, key_ok=True)
    walk_wizard(p)
    check(p.get_by_role("dialog").count() == 0 and "Use anyscribe from Terminal" not in text(p), "browser: Finish closes the wizard (no Terminal step)")
    p.context.close()


SCENARIOS = {f.__name__[2:]: f for f in [s_browser, s_browser_pixels, s_app_layout, s_drop, s_browse, s_open_file,
                                          s_banner, s_settings, s_first_launch, s_removal_reload, s_r2_facts, s_r3_facts, s_first_launch_marked, s_wizard, s_wizard_escape, s_wizard_browser]}


def main():
    global A, B, B2, B3, C, FILE_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--no-shots", action="store_true")
    ap.add_argument("--out", default=str(HERE / "shots"))
    a = ap.parse_args()
    names = [n for n in a.only.split(",") if n] or list(SCENARIOS)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="anyscribe-2c-ui-"))
    engines = []
    try:
        home_a = tmp / "home-a"
        home_a.mkdir()
        FILE_DIR = str(home_a / "Media")
        A = Engine("A", home_a, WORKTREE / "src")
        engines.append(A)
        A.post("/api/onboarding/save", {"provider": "openai", "api_key": "sk-check-not-a-real-key-1234567890"})
        if "browser_pixels" in names:
            C = Engine("C", home_a, None)  # same HOME: only reads, and the paths on screen match
            engines.append(C)
        if "wizard" in names:
            (tmp / "home-b").mkdir()
            B = Engine("B", tmp / "home-b", WORKTREE / "src")
            engines.append(B)
        if "wizard_escape" in names:
            (tmp / "home-b3").mkdir()
            B3 = Engine("B3", tmp / "home-b3", WORKTREE / "src")
            engines.append(B3)
        if "wizard_browser" in names:
            (tmp / "home-b2").mkdir()
            B2 = Engine("B2", tmp / "home-b2", WORKTREE / "src")
            engines.append(B2)
        with sync_playwright() as pw:
            r = Run(pw, out, not a.no_shots)
            for n in names:
                current["scenario"] = n
                print(f"== {n}")
                try:
                    SCENARIOS[n](r)
                except Exception as e:  # a crash is a failed check, never a silent pass
                    check(False, f"scenario ran to the end", f"{type(e).__name__}: {e}")
                    traceback.print_exc()
            r.browser.close()
    finally:
        for e in engines:
            e.stop()
        shutil.rmtree(tmp, ignore_errors=True)
    failed = [x for x in results if not x["ok"]]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    (out / "results.json").write_text(json.dumps(results, indent=1))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
