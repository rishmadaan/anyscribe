"""Suite-wide isolation: never touch the developer's real ~/.anyscribe.

Every path constant in anyscribe.config.paths binds from Path.home() at
IMPORT time, so redirecting HOME must happen here, at conftest import — pytest
imports conftest before any test module, i.e. before anyscribe is imported.
Anything later (fixtures, monkeypatch.setenv) is too late: the real paths are
already baked into module-level constants.

This exists because three onboarding tests once wrote through to the real
~/.anyscribe — replacing the developer's OPENAI_API_KEY with "sk-test" and
rewriting config.yaml — while the suite stayed green (2026-07-29 audit).
"""

from __future__ import annotations

import os
import sys
import tempfile

assert not any(m.startswith("anyscribe") for m in sys.modules), (
    "anyscribe was imported before tests/conftest.py could isolate HOME — "
    "real user config would be at risk. Import it only inside tests/fixtures."
)

_ISOLATED_HOME = tempfile.mkdtemp(prefix="ascli-test-home-")
os.environ["HOME"] = _ISOLATED_HOME  # macOS / Linux
os.environ["USERPROFILE"] = _ISOLATED_HOME  # Windows


import json  # noqa: E402
import threading  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture
def health_server():
    """A real local HTTP server on a free port answering /api/health with ``body``.

    Yields a controller: ``.port``, ``.body`` (set it before requests), ``.posts``
    (paths of every POST received). Defaults to a foreign program's answer.
    """

    class Ctl:
        body: dict = {"version": "1"}
        posts: list = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            data = json.dumps(Ctl.body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):  # noqa: N802
            Ctl.posts.append(self.path)
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *a):
            pass

    Ctl.posts = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Ctl.port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield Ctl
    server.shutdown()
    server.server_close()
