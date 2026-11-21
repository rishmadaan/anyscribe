"""In-memory job manager — runs process() in threads, bridges to async."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from anyscribe.core.appmode import is_app
from anyscribe.web.progress import ProgressEvent

# Cleanup constants
JOB_TTL_SECONDS = 3600  # Remove finished jobs after 1 hour (never in the Mac app)
MAX_EVENTS_PER_JOB = 100  # Cap event history per job
MAX_JOBS = 500  # Hard cap on jobs in memory: evicts the oldest finished jobs only
MAX_LISTED_JOBS = 50  # GET /api/jobs: every active job, then the newest finished up to this


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE = (JobStatus.PENDING, JobStatus.RUNNING)


class JobCancelled(Exception):
    """Raised inside the pipeline thread to abort a cancelled job."""


@dataclass
class Job:
    id: str
    url: str
    status: JobStatus = JobStatus.PENDING
    stage: str | None = None  # step of the last pipeline progress event
    title: str | None = None  # from the "download completed" event's data, then the result
    created_at: float = field(default_factory=time.time)
    events: list[ProgressEvent] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    completed_at: float | None = None
    cancel_requested: bool = False
    _subscribers: list[asyncio.Queue] = field(default_factory=list)


class JobManager:
    """Manages transcription jobs with thread-pool execution and async event streaming."""

    def __init__(self, max_workers: int = 2) -> None:
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def _cleanup_stale(self) -> None:
        """Drop finished jobs older than TTL, then the oldest finished jobs past MAX_JOBS.
        A pending or running job is never dropped. In the Mac app finished jobs do not
        expire by age: its menu keeps them until the window is opened."""
        finished = [jid for jid, job in self._jobs.items() if job.status not in ACTIVE]
        if not is_app():
            now = time.time()
            stale = {
                jid
                for jid in finished
                if self._jobs[jid].completed_at
                and (now - self._jobs[jid].completed_at) > JOB_TTL_SECONDS
            }
            for jid in stale:
                del self._jobs[jid]
            finished = [jid for jid in finished if jid not in stale]
        for jid in finished[: max(0, len(self._jobs) - MAX_JOBS)]:
            del self._jobs[jid]

    def get(self, job_id: str) -> Job | None:
        self._cleanup_stale()
        return self._jobs.get(job_id)

    def summaries(self) -> list[dict[str, Any]]:
        """Newest first: every pending and running job, always, then the newest finished jobs
        up to MAX_LISTED_JOBS in all. The quit question must never miss a running job."""
        self._cleanup_stale()
        room = MAX_LISTED_JOBS - sum(j.status in ACTIVE for j in self._jobs.values())
        jobs = []
        for j in reversed(self._jobs.values()):
            if j.status in ACTIVE:
                jobs.append(j)
            elif room > 0:
                jobs.append(j)
                room -= 1
        return [
            {
                "job_id": j.id,
                "url": j.url,
                "status": j.status.value,
                "stage": j.stage,
                "title": j.title,
                "error": j.error,  # set only when the job failed
                "file_path": (j.result or {}).get("file_path"),  # result exists once completed
                "created_at": j.created_at,
                "completed_at": j.completed_at,
            }
            for j in jobs
        ]

    def cancel(self, job_id: str) -> Job | None:
        """Request cooperative cancellation. No-op if the job already finished."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
            job.cancel_requested = True
        return job

    def subscribe(self, job: Job) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        job._subscribers.append(q)
        return q

    def unsubscribe(self, job: Job, queue: asyncio.Queue) -> None:
        try:
            job._subscribers.remove(queue)
        except ValueError:
            pass

    async def submit(
        self,
        url: str,
        settings: Any,
        loop: asyncio.AbstractEventLoop,
        force: bool = False,
        model: str | None = None,
    ) -> str:
        """Submit a new transcription job. Returns job_id immediately."""
        self._cleanup_stale()
        job_id = uuid.uuid4().hex[:8]
        job = Job(id=job_id, url=url)
        self._jobs[job_id] = job
        loop.run_in_executor(self._executor, self._run_job, job, settings, loop, force, model)
        return job_id

    def _run_job(
        self,
        job: Job,
        settings: Any,
        loop: asyncio.AbstractEventLoop,
        force: bool = False,
        model: str | None = None,
    ) -> None:
        """Run process() synchronously in a thread, pushing events to subscribers."""
        from anyscribe.config.settings import load_env
        from anyscribe.core.orchestrator import process

        load_env()
        job.status = JobStatus.RUNNING

        def on_progress(step: str, status: str, message: str, **kwargs: Any) -> None:
            # ponytail: cancellation is cooperative — a sync pipeline can't be
            # interrupted mid-step, so we abort at the next progress event.
            if job.cancel_requested:
                raise JobCancelled()
            job.stage = step
            title = (kwargs.get("data") or {}).get("title")
            if title:
                job.title = title
            event = ProgressEvent(
                step=step,
                status=status,
                message=message,
                percent=kwargs.get("percent"),
                data=kwargs.get("data", {}),
            )
            job.events.append(event)
            # Cap event history to prevent unbounded growth
            if len(job.events) > MAX_EVENTS_PER_JOB:
                job.events = job.events[-MAX_EVENTS_PER_JOB:]
            dead_queues = []
            for q in list(job._subscribers):
                try:
                    loop.call_soon_threadsafe(q.put_nowait, event)
                except Exception:
                    dead_queues.append(q)
            for q in dead_queues:
                try:
                    job._subscribers.remove(q)
                except ValueError:
                    pass

        try:
            result = process(
                url=job.url,
                settings=settings,
                quiet=True,
                on_progress=on_progress,
                force=force,
                model=model,
            )
            job.title = result.title or job.title
            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()
            job.result = {
                "file_path": str(result.file_path),
                "title": result.title,
                "platform": result.platform,
                "duration": result.duration,
                "language": result.language,
                "word_count": result.word_count,
                "provider": result.provider,
                "model": result.model or model,
                "notes": result.notes,
                "cached": result.cached,
            }
            # Send completion event
            done_event = ProgressEvent(
                step="done",
                status="completed",
                message="Transcription complete",
                data=job.result,
            )
            job.events.append(done_event)
            for q in list(job._subscribers):
                try:
                    loop.call_soon_threadsafe(q.put_nowait, done_event)
                except Exception:
                    pass

        except JobCancelled:
            job.status = JobStatus.CANCELLED
            job.completed_at = time.time()
            cancel_event = ProgressEvent(
                step="cancelled",
                status="cancelled",
                message="Transcription cancelled",
            )
            job.events.append(cancel_event)
            for q in list(job._subscribers):
                try:
                    loop.call_soon_threadsafe(q.put_nowait, cancel_event)
                except Exception:
                    pass

        except Exception as e:
            job.status = JobStatus.FAILED
            job.completed_at = time.time()
            job.error = str(e)
            err_event = ProgressEvent(
                step="error",
                status="error",
                message=str(e),
            )
            job.events.append(err_event)
            for q in list(job._subscribers):
                try:
                    loop.call_soon_threadsafe(q.put_nowait, err_event)
                except Exception:
                    pass


# Singleton for the app lifetime
job_manager = JobManager()
