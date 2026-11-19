"""Local transcription provisioning endpoints.

``GET /api/local/status`` is cheap and safe to poll; the setup/teardown POSTs
kick off background tasks and return immediately. The front-end polls
``status`` to watch ``setup_running`` flip. ``POST /api/local/choose`` makes a
model the default once it can run (see ``routes.models.choose``).

We keep setup state on ``app.state`` rather than in a module global so a
single running server can own a single in-flight setup at a time; a concurrent
POST while another is running returns 409.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from anyscribe.core.local_setup import (
    check_status,
    run_setup,
    run_teardown,
)
from anyscribe.core.local_recommend import LANGUAGE_ANSWERS, recommend
from anyscribe.providers.local_models import (
    BENCHMARK_CAPTION,
    MODEL_SIZES,
    MODEL_SPECS,
    RECOMMENDED_MODEL,
    faster_whisper_importable,
    featured_models,
    list_cached_models,
    runnable,
)
from anyscribe.web.models import LocalSetupRequest

router = APIRouter(prefix="/api/local", tags=["local"])


# Max lines the setup log keeps per run. Enough to diagnose pip/HF issues
# without blowing up memory if something goes pathological.
LOG_RING_LIMIT = 500


def _setup_state(app) -> dict[str, Any]:
    state = getattr(app.state, "local_setup", None)
    if state is None:
        state = {
            "running": False,
            "phase": None,
            "error": None,
            "last_model": None,
            "also": [],
            "outcome": None,  # last run's status: set_up | superseded | failed
            "log": [],
            "progress": None,
        }
        app.state.local_setup = state
    return state


def _append_log(state: dict, line: str) -> None:
    """Append a single line to the ring buffer, trimming from the head."""
    log = state["log"]
    log.append(line)
    if len(log) > LOG_RING_LIMIT:
        del log[: len(log) - LOG_RING_LIMIT]


@router.get("/status")
async def local_status(request: Request) -> dict:
    state = _setup_state(request.app)
    status = check_status(web=True)
    status["setup_running"] = bool(state["running"])
    status["setup_phase"] = state["phase"]
    status["setup_error"] = state["error"]
    status["setup_last_model"] = state["last_model"]
    status["setup_progress"] = state["progress"]
    status["setup_also"] = state.get("also", [])
    status["setup_outcome"] = state.get("outcome")
    status["recommended_model"] = RECOMMENDED_MODEL
    status["choices"] = list(MODEL_SIZES)
    status["featured"] = featured_models()
    status["language_answers"] = LANGUAGE_ANSWERS
    status["benchmark_caption"] = BENCHMARK_CAPTION

    # Merge the Models-panel download queue state so the Settings table (which
    # polls only this endpoint) can render downloading/queued/percent per row.
    dq = getattr(request.app.state, "download_queue", None)
    status["pending_default"] = None
    if dq is not None:
        with dq["lock"]:
            queue = list(dq["queue"])
            progress = dict(dq["progress"])
            results = dict(dq["results"])
            pending = dq.get("pending")
            status["pending_default"] = dict(pending) if pending else None
        if pending:  # a chosen model is on its way, or its switch just failed: no tip
            status["suggestion"] = None
        for m in status["models"]:
            size = m["size"]
            pos = queue.index(size) if size in queue else -1
            m["downloading"] = pos == 0
            m["queued"] = pos > 0
            m["queue_position"] = pos
            m["progress"] = progress.get(size)
            m["last_error"] = (results.get(size) or {}).get("error")

    return status


@router.get("/registry")
async def local_registry() -> dict:
    """The model registry alone: no disk scan, no engine import, so a first
    screen can show sizes and times without waiting on ``/status``."""
    return {
        "recommended_model": RECOMMENDED_MODEL,
        "featured": featured_models(),
        "specs": MODEL_SPECS,
        "benchmark_caption": BENCHMARK_CAPTION,
    }


@router.get("/setup/log")
async def local_setup_log(request: Request, since: int = 0) -> dict:
    """Return lines appended to the setup log since index ``since``.

    Used by the UI to stream pip/install output into a collapsible panel
    inside LocalSetupModal. Lightweight polling, not WebSocket.
    """
    state = _setup_state(request.app)
    log = state["log"]
    total = len(log)
    since = max(0, min(since, total))
    return {
        "lines": log[since:],
        "total": total,
        "running": bool(state["running"]),
    }


def _background_setup(app, model: str, also: list[str] | None = None, activate=None) -> None:
    """Run run_setup synchronously in a thread — faster-whisper/HF calls block."""
    state = _setup_state(app)
    # Fresh run = fresh log.
    state["log"].clear()
    state["progress"] = None

    def on_progress(ev: dict) -> None:
        name = ev.get("event")
        # Byte-level download progress is high-frequency; update the progress
        # field but don't spam the log or churn the phase name.
        if name == "download_progress":
            total = int(ev.get("total") or 0)
            downloaded = int(ev.get("downloaded") or 0)
            state["progress"] = {
                "downloaded": downloaded,
                "total": total,
                "percent": round(downloaded / total * 100, 1) if total > 0 else None,
            }
            return
        state["phase"] = name
        # Mirror phase transitions into the log so the UI panel tells a story
        # even before the install subprocess starts emitting output.
        if name == "installing_package":
            method = ev.get("method", "?")
            cmd = ev.get("command") or []
            _append_log(state, f"[phase] installing faster-whisper + onnx-asr via {method}")
            if cmd:
                _append_log(state, f"[cmd] {' '.join(cmd)}")
        elif name == "package_installed":
            _append_log(state, "[phase] engines installed")
        elif name == "downloading_model":
            _append_log(state, f"[phase] downloading model: {ev.get('size', '?')}")
        elif name == "model_downloaded":
            mb = int(ev.get("bytes", 0)) // (1024 * 1024)
            _append_log(state, f"[phase] model downloaded ({mb} MB)")
            state["progress"] = None
        elif name == "done":
            _append_log(state, "[phase] done")
        elif name == "superseded":
            _append_log(state, "[phase] a newer choice was made meanwhile; default left as it is")

    try:
        result = run_setup(model, on_progress=on_progress, activate=activate)
        state["outcome"] = result.get("status")
        if result.get("status") == "superseded":
            state["error"] = None
            state["also"] = []  # extras belonged to the older choice
        elif result.get("status") == "failed":
            phase = result.get("phase")
            install = result.get("install") or {}
            install_stderr = (install.get("stderr") or "").strip()
            error_msg = result.get("error") or install_stderr or f"setup failed in {phase}"
            state["error"] = error_msg
            if install_stderr:
                for line in install_stderr.splitlines():
                    _append_log(state, f"[stderr] {line}")
            _append_log(state, f"[error] {error_msg}")
        else:
            state["error"] = None
            # extras (Turbo for a mix) download after setup, even if the page closed
            from anyscribe.web.routes.models import enqueue_pull

            for extra in also or []:
                if not runnable(extra):
                    enqueue_pull(app, extra)
    except Exception as e:
        state["error"] = str(e)
        state["outcome"] = "failed"
        _append_log(state, f"[error] {e}")
    finally:
        state["running"] = False
        state["phase"] = "done"


def _check_models(ids: list[str]) -> None:
    for m in ids:
        if m not in MODEL_SIZES:
            raise HTTPException(
                status_code=400,
                detail=f"unknown model '{m}'. Choices: {', '.join(MODEL_SIZES)}",
            )


@router.post("/setup")
async def local_setup_endpoint(req: LocalSetupRequest, request: Request) -> dict:
    _check_models([req.model, *req.also])
    also = [m for m in dict.fromkeys(req.also) if m != req.model]

    state = _setup_state(request.app)
    if state["running"]:
        raise HTTPException(status_code=409, detail="setup already in progress")

    state["running"] = True
    state["phase"] = "starting"
    state["error"] = None
    state["last_model"] = req.model
    state["also"] = also
    state["outcome"] = None
    from anyscribe.web.routes.models import setup_activation

    activate = setup_activation(request.app)  # this setup is now the newest choice

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _background_setup, request.app, req.model, also, activate)

    return {"status": "started", "model": req.model, "also": also}


@router.post("/choose")
async def local_choose_endpoint(req: LocalSetupRequest, request: Request) -> dict:
    """Make ``model`` the default once it can run (now, if it already can);
    download it, its helpers and each ``also`` model. Settings' one commit."""
    from anyscribe.web.routes.models import choose

    _check_models([req.model, *req.also])
    if not faster_whisper_importable():
        raise HTTPException(
            status_code=409,
            detail="local transcription not set up — call POST /api/local/setup first",
        )
    return await asyncio.get_event_loop().run_in_executor(
        None, choose, request.app, req.model, list(dict.fromkeys(req.also))
    )


@router.get("/recommend")
async def local_recommend(answer: str) -> dict:
    """The guided "help me choose" pick for one answer to "What language is
    most of your audio?" (keys of ``language_answers`` in /status)."""
    if answer not in LANGUAGE_ANSWERS:
        raise HTTPException(
            status_code=400,
            detail=f"unknown answer '{answer}'. Choices: {', '.join(LANGUAGE_ANSWERS)}",
        )
    cached = {m["size"] for m in list_cached_models() if m["cached"]}
    return recommend(answer, cached=cached)


@router.post("/teardown")
async def local_teardown_endpoint(request: Request) -> dict:
    state = _setup_state(request.app)
    if state["running"]:
        raise HTTPException(status_code=409, detail="setup in progress")

    # Teardown is fast enough to run synchronously; keeps the UI simple.
    result = await asyncio.get_event_loop().run_in_executor(None, run_teardown)
    return result
