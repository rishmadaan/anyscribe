"""Model-cache endpoints for the Web UI's Models panel.

Single-worker FIFO queue for downloads — clicking Download on a second model
while another is in flight enqueues instead of erroring. Reinstall is a
convenience composite (delete + pull) exposed as one endpoint.

The queue also owns "choose a local model" (``choose``): it remembers one
pending default, and the worker switches the default only once that model can
run, so no browser sequencing is involved.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from anyscribe.config.settings import load_config
from anyscribe.core.config_set import set_value
from anyscribe.core.local_setup import ensure_runtime
from anyscribe.providers.local_models import (
    MODEL_SIZES,
    delete_model,
    engine_importable,
    faster_whisper_importable,
    is_cached,
    list_cached_models,
    pull_model,
    runnable,
)

router = APIRouter(prefix="/api/models", tags=["models"])


def _download_state(app) -> dict[str, Any]:
    """FIFO queue state stashed on app.state.

    Shape:
      - ``queue``: list[str] — sizes waiting, head = currently running
      - ``lock``: threading.Lock for queue mutations (worker runs in executor)
      - ``worker_running``: bool — whether the worker task is alive
      - ``results``: dict[size, {status, error?}] — last terminal state per size
      - ``pending``: the chosen default still downloading, ``{model, also,
        state, error}`` (state "downloading" or "failed"), or None. In memory
        only: a restart forgets it and the default stays as it was.
      - ``generation``: the newest choice's number. Every accepted choose and
        every web setup takes the next one; only the newest may switch the
        default (see ``setup_activation``).
    """
    state = getattr(app.state, "download_queue", None)
    if state is None:
        state = {
            "queue": [],
            "lock": threading.Lock(),
            "worker_running": False,
            "results": {},
            "progress": {},  # size -> {downloaded, total, percent}
            "pending": None,
            "generation": 0,
        }
        app.state.download_queue = state
    return state


def _worker_loop(app) -> None:
    """Single consumer: pop from queue head, pull the model, repeat until empty."""
    state = _download_state(app)
    while True:
        with state["lock"]:
            if not state["queue"]:
                state["worker_running"] = False
                return
            size = state["queue"][0]  # running = head

        def _progress(downloaded: int, total: int) -> None:
            with state["lock"]:
                state["progress"][size] = {
                    "downloaded": downloaded,
                    "total": total,
                    "percent": round(downloaded / total * 100, 1) if total > 0 else None,
                }

        try:
            if not engine_importable(size):
                # an install from before Parakeet: add onnx-asr on first pick
                failed = ensure_runtime()
                if failed:
                    raise RuntimeError(
                        f"engine install failed: {failed.get('stderr') or failed['command']}"
                    )
            pull_model(size, progress_cb=_progress)
            with state["lock"]:
                state["results"][size] = {"status": "completed"}
                _settle_pending(state, size, None)
        except Exception as e:
            with state["lock"]:
                state["results"][size] = {"status": "failed", "error": str(e)}
                _settle_pending(state, size, str(e))
        finally:
            with state["lock"]:
                if state["queue"] and state["queue"][0] == size:
                    state["queue"].pop(0)
                state["progress"].pop(size, None)


def _settle_pending(state: dict, size: str, error: str | None) -> None:
    """After ``size``'s download ends (caller holds the lock): if it is the
    pending default, switch to it when it can run, else record why not. The
    old default is never touched on failure."""
    pending = state["pending"]
    if not pending or pending["model"] != size or pending["state"] != "downloading":
        return
    if error is None:
        outcome = set_value("local_model", size)  # refuses a model that still can't run
        if outcome.ok:
            state["pending"] = None
            return
        error = outcome.error
    pending.update(state="failed", error=error)


def choose(app, model: str, also: list[str]) -> dict:
    """Make ``model`` the local default once it can run, downloading what it
    needs, and download each ``also`` model. A later call replaces the pending
    choice; a model that can already run becomes the default at once."""
    state = _download_state(app)
    extras = [m for m in also if m != model and not runnable(m)]
    if runnable(model):
        with state["lock"]:
            state["generation"] += 1
            state["pending"] = None
            outcome = set_value("local_model", model)
        if not outcome.ok:
            raise HTTPException(status_code=422, detail=outcome.error)
        queued = [enqueue_pull(app, m)["size"] for m in extras]
        return {"status": "switched", "default": model, "queued": queued}
    with state["lock"]:
        state["generation"] += 1
        state["pending"] = {"model": model, "also": extras, "state": "downloading", "error": None}
        # the reply describes this request's choice; the worker or a later
        # choose may clear the shared pending before we answer
        accepted = dict(state["pending"])
    queued = [enqueue_pull(app, m)["size"] for m in [model, *extras]]
    return {"status": "pending", "pending": accepted, "queued": queued}


def setup_activation(app):
    """A web setup starting now becomes the newest choice: it takes the next
    number and drops any pending choice (older, so it must never switch). The
    returned ``activate(model)`` switches the default only if no choose came
    after the setup started; otherwise it returns None (superseded)."""
    state = _download_state(app)
    with state["lock"]:
        state["generation"] += 1
        mine = state["generation"]
        state["pending"] = None

    def activate(model: str):
        with state["lock"]:
            if state["generation"] != mine:
                return None
            return set_value("local_model", model)

    return activate


def _kick_worker(app) -> None:
    """Start the worker loop if not already running (a plain thread, so a
    background setup thread can queue downloads too)."""
    state = _download_state(app)
    with state["lock"]:
        if state["worker_running"]:
            return
        state["worker_running"] = True
    threading.Thread(target=_worker_loop, args=(app,), daemon=True).start()


@router.get("/local")
async def list_local_models(request: Request) -> dict:
    settings = load_config()
    models = list_cached_models()
    state = _download_state(request.app)
    total_bytes = sum(int(m["bytes"]) for m in models)

    with state["lock"]:
        queue = list(state["queue"])
        results = dict(state["results"])
        progress = dict(state["progress"])

    def _entry(m):
        size = m["size"]
        pos = queue.index(size) if size in queue else -1
        return {
            "size": size,
            "cached": m["cached"],
            "partial": m["partial"],
            "runnable": m["runnable"],
            "bytes": m["bytes"],
            "repo": m["repo"],
            "spec": m["spec"],
            "downloading": pos == 0,
            "queued": pos > 0,
            "queue_position": pos,
            "progress": progress.get(size),
            "last_error": (results.get(size) or {}).get("error"),
        }

    return {
        "default": settings.local_model,
        "faster_whisper_installed": faster_whisper_importable(),
        "total_disk_bytes": total_bytes,
        "models": [_entry(m) for m in models],
        "queue": queue,
    }


@router.post("/local/{size}/pull")
async def pull_local_model(size: str, request: Request) -> dict:
    if size not in MODEL_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown size '{size}'. Choices: {', '.join(MODEL_SIZES)}",
        )
    if not faster_whisper_importable():
        raise HTTPException(
            status_code=409,
            detail="local transcription not set up — call POST /api/local/setup first",
        )

    # A partial download, or a Parakeet missing its helpers, is queued and resumes.
    if runnable(size):
        return {"status": "already_present", "size": size}
    return enqueue_pull(request.app, size)


def enqueue_pull(app, size: str) -> dict:
    """Add ``size`` to the download queue (no-op if already there) and start
    the worker."""
    state = _download_state(app)
    with state["lock"]:
        if size in state["queue"]:
            pos = state["queue"].index(size)
            return {"status": "already_in_queue", "size": size, "position": pos}
        state["queue"].append(size)
        state["results"].pop(size, None)  # a retry starts with no old error
        position = len(state["queue"]) - 1

    _kick_worker(app)

    return {
        "status": "started" if position == 0 else "queued",
        "size": size,
        "position": position,
    }


@router.post("/local/{size}/reinstall")
async def reinstall_local_model(size: str, request: Request) -> dict:
    """Delete + download in one call. Useful for corrupted weights.

    Runs synchronously — reinstall is rare and a progress spinner is fine.
    """
    if size not in MODEL_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown size '{size}'. Choices: {', '.join(MODEL_SIZES)}",
        )
    if not faster_whisper_importable():
        raise HTTPException(
            status_code=409,
            detail="local transcription not set up",
        )

    state = _download_state(request.app)
    with state["lock"]:
        if state["queue"] and state["queue"][0] == size:
            raise HTTPException(status_code=409, detail=f"{size} is currently downloading")

    loop = asyncio.get_event_loop()

    bytes_freed = 0
    if await loop.run_in_executor(None, is_cached, size):
        del_result = await loop.run_in_executor(None, delete_model, size)
        bytes_freed = int(del_result.get("bytes_freed", 0))

    try:
        pull_result = await loop.run_in_executor(None, pull_model, size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"reinstall failed: {e}")

    return {
        "status": "reinstalled" if bytes_freed > 0 else "downloaded_only",
        "size": size,
        "bytes_freed": bytes_freed,
        "bytes_downloaded": int(pull_result.get("bytes", 0)),
    }


@router.delete("/local/{size}")
async def delete_local_model(size: str, request: Request) -> dict:
    if size not in MODEL_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown size '{size}'. Choices: {', '.join(MODEL_SIZES)}",
        )
    state = _download_state(request.app)
    with state["lock"]:
        if state["queue"] and state["queue"][0] == size:
            raise HTTPException(status_code=409, detail=f"{size} is currently downloading")
        if size in state["queue"]:
            state["queue"].remove(size)
            return {"status": "cancelled", "size": size, "bytes_freed": 0}

    result = await asyncio.get_event_loop().run_in_executor(None, delete_model, size)
    return result
