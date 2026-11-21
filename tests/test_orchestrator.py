"""Integration test for core/orchestrator.py — process() wiring + dedup."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from anyscribe.config.settings import Settings
from anyscribe.downloaders.base import DownloadResult
from anyscribe.providers.base import TranscriptResult

URL = "https://www.youtube.com/watch?v=abc123"


class FakeDownloader:
    def __init__(self):
        self.calls = 0

    def download(self, url: str, output_dir: Path) -> DownloadResult:
        self.calls += 1
        audio = output_dir / "audio.mp3"
        audio.write_bytes(b"fake audio")
        return DownloadResult(
            audio_path=audio,
            title="Test Video",
            duration=60.0,
            platform="youtube",
            original_url=url,
        )


class FakeProvider:
    name = "fake"

    def transcribe(self, audio_path, language="auto", diarize=False):
        return TranscriptResult(text="hello world from the fake provider", language="en")


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated workspace + stubbed download/transcribe/migrations/preflight."""
    from anyscribe.core import dedup, migrate, orchestrator, preflight
    from anyscribe.vault import index, writer

    ws = tmp_path / "workspace"
    for mod in (dedup, writer, index):
        monkeypatch.setattr(mod, "get_workspace_dir", lambda: ws)
    monkeypatch.setattr(orchestrator, "TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(orchestrator, "RECOVERY_DIR", tmp_path / "recovery")
    monkeypatch.setattr(migrate, "maybe_migrate_workspace", lambda: None)
    monkeypatch.setattr(migrate, "maybe_migrate_media_to_downloads", lambda: None)
    monkeypatch.setattr(migrate, "maybe_flatten_date_folders", lambda: 0)
    monkeypatch.setattr(preflight, "preflight_check", lambda settings, url: None)

    downloader = FakeDownloader()
    monkeypatch.setattr(orchestrator, "get_downloader", lambda url: downloader)
    monkeypatch.setattr(orchestrator, "get_provider", lambda name, model=None: FakeProvider())
    return ws, downloader


def test_process_dedup_and_force(env):
    from anyscribe.core.orchestrator import process

    ws, downloader = env
    settings = Settings()

    # 1. Happy path: file written + index updated
    r1 = process(URL, settings, quiet=True)
    assert r1.cached is False
    assert r1.file_path == ws / "sources" / "youtube" / "test-video.md"
    assert r1.file_path.exists()
    assert f"source: {URL}" in r1.file_path.read_text()
    assert r1.word_count == 6
    assert "test-video" in (ws / "_index.md").read_text()
    assert downloader.calls == 1

    # 2. Same URL again: cached, no download
    r2 = process(URL, settings, quiet=True)
    assert r2.cached is True
    assert r2.file_path == r1.file_path
    assert r2.title == "Test Video"
    assert r2.word_count == 6
    assert downloader.calls == 1

    # 3. force=True: re-transcribes
    r3 = process(URL, settings, quiet=True, force=True)
    assert r3.cached is False
    assert downloader.calls == 2


# ── GET /api/jobs: the list the Mac app's menu bar reads ─────


@pytest.fixture
def jobs(monkeypatch):
    """A fresh job manager behind the API, so other tests' jobs never show."""
    from fastapi.testclient import TestClient

    from anyscribe.web.app import create_app
    from anyscribe.web.jobs import JobManager
    from anyscribe.web.routes import transcribe

    manager = JobManager()
    monkeypatch.setattr(transcribe, "job_manager", manager)
    return manager, TestClient(create_app())


def _run(manager, url, settings):
    import asyncio

    from anyscribe.web.jobs import Job

    job = Job(id=f"job{len(manager._jobs)}", url=url)
    manager._jobs[job.id] = job
    loop = asyncio.new_event_loop()
    try:
        manager._run_job(job, settings, loop)
    finally:
        loop.close()
    return job


def test_job_list_shows_the_title_while_running_and_the_file_when_done(env, jobs, monkeypatch):
    from anyscribe.core import orchestrator

    ws, _ = env
    manager, client = jobs
    seen_mid_job = []

    class TitleWatchingProvider(FakeProvider):
        def transcribe(self, audio_path, language="auto", diarize=False):
            seen_mid_job.append(client.get("/api/jobs").json()[0])
            return super().transcribe(audio_path, language, diarize)

    monkeypatch.setattr(orchestrator, "get_provider", lambda n, model=None: TitleWatchingProvider())
    _run(manager, URL, Settings())

    # Known from the "download completed" event, before the transcript exists.
    assert seen_mid_job[0]["title"] == "Test Video"
    assert seen_mid_job[0]["status"] == "running" and seen_mid_job[0]["stage"] == "transcribe"
    assert seen_mid_job[0]["file_path"] is None and seen_mid_job[0]["completed_at"] is None

    (done,) = client.get("/api/jobs").json()
    assert set(done) == {
        "job_id", "url", "status", "stage", "title", "error",
        "file_path", "created_at", "completed_at",
    }  # fmt: skip
    assert done["job_id"] == "job0" and done["url"] == URL
    assert done["status"] == "completed" and done["stage"] == "index"
    assert done["title"] == "Test Video" and done["error"] is None
    assert done["file_path"] == str(ws / "sources" / "youtube" / "test-video.md")
    assert done["completed_at"] >= done["created_at"]


def test_a_failed_job_keeps_its_title_and_shows_the_error(env, jobs, monkeypatch):
    from anyscribe.core import orchestrator

    manager, client = jobs

    class Broken(FakeProvider):
        def transcribe(self, *a, **k):
            raise RuntimeError("provider down")

    monkeypatch.setattr(orchestrator, "get_provider", lambda n, model=None: Broken())
    _run(manager, URL, Settings())
    (failed,) = client.get("/api/jobs").json()
    assert failed["status"] == "failed" and failed["stage"] == "transcribe"
    assert failed["title"] == "Test Video" and failed["error"] == "provider down"
    assert failed["file_path"] is None


def test_job_title_is_never_parsed_from_the_message_text(jobs, monkeypatch):
    from anyscribe.core import orchestrator

    manager, client = jobs

    def no_data(url, settings, quiet, on_progress, force, model):
        on_progress("download", "completed", "Downloaded: Looks Like A Title")
        raise RuntimeError("stopped")

    monkeypatch.setattr(orchestrator, "process", no_data)
    _run(manager, URL, Settings())
    (job,) = client.get("/api/jobs").json()
    assert job["stage"] == "download" and job["title"] is None


def _finished(manager, n, start=0, done_at=None):
    from anyscribe.web.jobs import Job, JobStatus

    for i in range(start, start + n):
        manager._jobs[f"j{i}"] = Job(
            id=f"j{i}", url=f"u{i}", status=JobStatus.COMPLETED, completed_at=done_at or time.time()
        )


def test_job_list_is_newest_first_and_at_most_50_finished(jobs):
    manager, client = jobs
    _finished(manager, 60)
    listed = client.get("/api/jobs").json()
    assert [j["job_id"] for j in listed] == [f"j{i}" for i in range(59, 9, -1)]
    assert listed[0]["stage"] is None and listed[0]["title"] is None


def test_a_running_job_behind_50_finished_ones_is_still_listed(jobs):
    """Review C2: two workers, one long job, fifty short ones finishing beside it."""
    from anyscribe.web.jobs import Job, JobStatus

    manager, client = jobs
    manager._jobs["long"] = Job(id="long", url="u-long", status=JobStatus.RUNNING)
    _finished(manager, 50)
    manager._jobs["queued"] = Job(id="queued", url="u-q", status=JobStatus.PENDING)
    ids = [j["job_id"] for j in client.get("/api/jobs").json()]
    assert "long" in ids and "queued" in ids
    assert ids[0] == "queued" and ids[-1] == "long"  # still newest first
    assert len(ids) == 50  # 2 active + the newest 48 finished


def test_every_active_job_is_listed_even_past_50(jobs):
    from anyscribe.web.jobs import Job, JobStatus

    manager, client = jobs
    for i in range(55):
        manager._jobs[f"r{i}"] = Job(id=f"r{i}", url="u", status=JobStatus.RUNNING)
    _finished(manager, 3)
    ids = [j["job_id"] for j in client.get("/api/jobs").json()]
    assert ids == [f"r{i}" for i in range(54, -1, -1)]  # all 55 running, no finished room


@pytest.mark.parametrize("app,listed", [("1", True), (None, False)])
def test_finished_jobs_expire_after_an_hour_except_in_the_app(jobs, monkeypatch, app, listed):
    """Review F1: the app's menu keeps "finished while the window was closed" rows."""
    manager, client = jobs
    if app:
        monkeypatch.setenv("ANYSCRIBE_APP", app)
    else:
        monkeypatch.delenv("ANYSCRIBE_APP", raising=False)
    _finished(manager, 1, done_at=time.time() - 3601)
    ids = [j["job_id"] for j in client.get("/api/jobs").json()]
    assert ids == (["j0"] if listed else [])


def test_the_memory_cap_evicts_the_oldest_finished_jobs_never_an_active_one(jobs, monkeypatch):
    from anyscribe.web import jobs as jobs_mod
    from anyscribe.web.jobs import Job, JobStatus

    manager, _ = jobs
    monkeypatch.setattr(jobs_mod, "MAX_JOBS", 3)
    manager._jobs["oldest-running"] = Job(id="oldest-running", url="u", status=JobStatus.RUNNING)
    _finished(manager, 4)
    manager._jobs["pending"] = Job(id="pending", url="u", status=JobStatus.PENDING)
    manager._cleanup_stale()
    assert list(manager._jobs) == ["oldest-running", "j3", "pending"]
