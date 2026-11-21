"""The real engine as the Mac app starts it: `python -m anyscribe ui --watch-stdin`, in its own
process with a throwaway HOME and a free port. Requests from other websites are refused
while it keeps running, and closing its stdin (the app dying) stops it.

Tests run in file order against one engine; the last one closes its stdin.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _request(port: int, path: str, method: str = "GET", origin: str | None = None) -> int:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method)
    if origin is not None:
        req.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def _listening(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    home = tmp_path_factory.mktemp("engine-home")
    port = _free_port()
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home), "ANYSCRIBE_APP": "1"}
    log = home / "engine.log"
    with open(log, "wb") as out:
        proc = subprocess.Popen(
            [sys.executable, "-m", "anyscribe", "ui", "--watch-stdin", "--no-open"]
            + ["--port", str(port)],
            stdin=subprocess.PIPE,
            stdout=out,
            stderr=subprocess.STDOUT,
            env=env,
        )
    try:
        deadline = time.monotonic() + 60
        while not _listening(port):
            assert proc.poll() is None, log.read_text()
            assert time.monotonic() < deadline, "engine never started: " + log.read_text()
            time.sleep(0.2)
        yield proc, port, log
    finally:
        if proc.poll() is None:  # stop exactly the process this fixture started
            proc.kill()
            proc.wait()


def test_health_reports_the_engines_own_pid(engine):
    """The Mac app proves the server on its port is the engine it started by this pid."""
    import json

    proc, port, _ = engine
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=30) as r:
        body = json.load(r)
    assert (body["app"], body["pid"]) == ("anyscribe", proc.pid)


@pytest.mark.parametrize("origin", ["https://evil.example", "null"])
def test_another_website_cannot_stop_it_or_read_jobs(engine, origin):
    proc, port, _ = engine
    assert _request(port, "/api/shutdown", "POST", origin) == 403
    assert _request(port, "/api/jobs", origin=origin) == 403
    time.sleep(0.5)
    assert proc.poll() is None and _request(port, "/api/health") == 200  # still running


@pytest.mark.parametrize("origin", [None, "http://localhost:5173", "http://127.0.0.1:8457"])
def test_no_origin_and_local_origins_are_answered(engine, origin):
    _, port, _ = engine
    assert _request(port, "/api/health", origin=origin) == 200
    assert _request(port, "/api/jobs", origin=origin) == 200


def test_closing_stdin_stops_the_engine(engine):
    proc, port, log = engine
    assert proc.poll() is None
    proc.stdin.close()  # what the OS does when the app holding the pipe dies
    try:
        code = proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        pytest.fail("engine still running 20 s after its stdin closed:\n" + log.read_text())
    # The graceful stop runs, then the one exit door: on POSIX the engine kills its own group
    # (itself included), elsewhere os._exit(1).
    assert code == (-signal.SIGKILL if hasattr(os, "killpg") else 1), log.read_text()
    assert not _listening(port)


def _stop_in_process(monkeypatch, close, grace=0.2):
    """Run _stop_when_stdin_closes on a closed stdin with the hard exit recorded, not taken.
    Returns the event log and the monotonic time the hard exit fired (None if it never did)."""
    import io
    import threading

    from anyscribe.web import app as web_app

    order: list[str] = []
    fired: list[float] = []
    done = threading.Event()

    class Server:
        def __setattr__(self, name, value):
            order.append(f"{name}={value}")

    class Share:
        port = 8457

        def close(self):
            order.append("tailnet closed")
            return close()

    def exit_hard():
        fired.append(time.monotonic())
        order.append("exit")
        done.set()

    monkeypatch.setattr(sys, "stdin", type("S", (), {"buffer": io.BytesIO(b"anything\n")})())
    monkeypatch.setattr(web_app, "STDIN_EXIT_GRACE_SECONDS", grace)
    monkeypatch.setattr(web_app, "_exit_hard", exit_hard)
    start = time.monotonic()
    try:
        web_app._stop_when_stdin_closes(Server(), Share())
    except Exception as e:
        order.append(f"raised {type(e).__name__}")
    done.wait(5)
    return order, (fired[0] - start if fired else None)


def test_stdin_end_runs_the_shutdown_path_then_exits_hard(monkeypatch):
    """The tailnet rule is removed before the server is told to stop, and the process exits
    hard if the graceful stop has not finished after the grace period."""
    order, _ = _stop_in_process(monkeypatch, close=lambda: None)
    assert order == ["tailnet closed", "should_exit=True", "exit"]


def test_slow_tailnet_cleanup_cannot_delay_the_hard_exit(monkeypatch):
    """The clock starts at end of input: a Tailscale call slower than the grace still ends
    the process at the deadline, not after the call returns."""

    def slow():
        time.sleep(1.5)

    order, at = _stop_in_process(monkeypatch, close=slow, grace=0.2)
    assert at is not None and at < 1.0, (order, at)


def test_a_failing_print_cannot_skip_the_hard_exit(monkeypatch):
    import builtins

    def broken_print(*a, **k):
        raise OSError("stdout is gone")

    monkeypatch.setattr(builtins, "print", broken_print)
    order, at = _stop_in_process(monkeypatch, close=lambda: "tailscale said no")
    assert order == ["tailnet closed", "should_exit=True", "raised OSError", "exit"]


_WATCHED_ENGINE = """
import asyncio, subprocess, sys, threading

from anyscribe.web import app as web_app

port, grace, held = int(sys.argv[1]), float(sys.argv[2]), sys.argv[3] == "held"
web_app.STDIN_EXIT_GRACE_SECONDS = grace
create_app = web_app.create_app


def create_engine_app():
    app = create_app()

    @app.on_event("startup")
    async def _start_child():  # stands in for pip, yt-dlp or ffmpeg, held by a worker thread
        def hold():
            child = subprocess.Popen(["sleep", "300"])
            print(child.pid, flush=True)
            child.wait()

        threading.Thread(target=hold, daemon=True).start()

    if held:  # a server that cannot finish stopping (a job holding it): only the deadline ends it

        @app.on_event("shutdown")
        async def _hold():
            await asyncio.sleep(300)

    return app


web_app.create_app = create_engine_app
web_app.run(port=port, open_browser=False, watch_stdin=True)
"""


def _group_gone(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    return False


@pytest.mark.skipif(not hasattr(os, "killpg"), reason="process groups are POSIX only")
@pytest.mark.parametrize(
    "stop", ["stdin closes", "SIGTERM", "stdin closes and SIGTERM", "held", "detached, SIGTERM"]
)
def test_the_engine_never_outlives_its_watch_by_any_route(tmp_path, stop):
    """Invariant: when the app's engine ends, by any route, nothing it started is still running.
    The real run(watch_stdin=True), with a `sleep 300` child held by a worker thread, stopped
    as the app stops it: its stdin closing, SIGTERM, both (the app's quit), or with the server
    held past the deadline; and started detached, a session leader, as the app's shell starts
    it. Afterwards the engine's whole process group is gone."""
    port = _free_port()
    grace = "1" if stop == "held" else "5"
    env = {**os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}
    env["ANYSCRIBE_APP"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-c", _WATCHED_ENGINE, str(port), grace, stop],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=env,
        start_new_session=stop.startswith("detached"),
    )
    child = pgid = None
    try:
        child = int(proc.stdout.readline())  # printed once the server started
        pgid = os.getpgid(proc.pid)
        deadline = time.monotonic() + 30
        while not _listening(port):
            assert proc.poll() is None and time.monotonic() < deadline, "engine never listened"
            time.sleep(0.1)
        assert (pgid, os.getpgid(child)) == (proc.pid, proc.pid)  # it leads; its child is in it
        if "stdin" in stop or stop == "held":
            proc.stdin.close()
        if "SIGTERM" in stop:
            proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=20)  # reaped, so the engine is not a zombie still in its group
        gone_by = time.monotonic() + 5
        while not _group_gone(pgid) and time.monotonic() < gone_by:
            time.sleep(0.1)
        assert _group_gone(pgid), f"the engine's group outlived it ({stop}); child {child}"
    finally:  # stop exactly what this test started: the engine, and its child only while it
        # is still in the engine's group (a pid alone may have been reused by then)
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        if child is not None and pgid is not None:
            try:
                if os.getpgid(child) == pgid:
                    os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass


_APP_HOLDING_AN_ENGINE = """
import subprocess, sys, time
# This process stands in for the app; the engine below did not make itself a group leader.
engine = subprocess.run(
    [sys.executable, "-c", "from anyscribe.web import app; app._exit_hard()"]
)
print("app survived", engine.returncode, flush=True)
"""


@pytest.mark.skipif(not hasattr(os, "killpg"), reason="process groups are POSIX only")
def test_the_hard_exit_never_signals_a_group_the_engine_does_not_lead():
    """An engine in the app's group (no group of its own) exits alone; the app lives on.
    Runs in a new session so even a wrong group kill cannot reach pytest."""
    done = subprocess.run(
        [sys.executable, "-c", _APP_HOLDING_AN_ENGINE],
        capture_output=True,
        text=True,
        timeout=60,
        start_new_session=True,
    )
    assert done.stdout.strip() == "app survived 1", (done.returncode, done.stderr)
