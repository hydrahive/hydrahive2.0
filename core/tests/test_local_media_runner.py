"""Tests für den gemeinsamen lokalen Media-Job-Lifecycle."""
from pathlib import Path

import pytest

from hydrahive.llm.video_backends import JobRef, JobStatus, VideoParams, run_local_media


class FakeBackend:
    type = "fake"

    def __init__(self, status: JobStatus):
        self.status = status
        self.fetched = False

    async def submit(self, provider, model, params):
        return JobRef("job-1")

    async def poll(self, provider, job):
        return self.status

    async def fetch_output(self, provider, job, dest_dir: Path):
        self.fetched = True
        dest_dir.mkdir(parents=True, exist_ok=True)
        result = dest_dir / "result.bin"
        result.write_bytes(b"media")
        return result


@pytest.mark.asyncio
async def test_runner_fetches_done_result(monkeypatch, tmp_path):
    monkeypatch.setattr("hydrahive.llm.video_backends._runner.asyncio.sleep", lambda _: _done())
    backend = FakeBackend(JobStatus(state="done"))
    result = await run_local_media(backend, {}, "local:x/model", VideoParams("p"), tmp_path)
    assert result.read_bytes() == b"media"
    assert backend.fetched


@pytest.mark.asyncio
async def test_runner_raises_backend_error(monkeypatch, tmp_path):
    monkeypatch.setattr("hydrahive.llm.video_backends._runner.asyncio.sleep", lambda _: _done())
    backend = FakeBackend(JobStatus(state="error", error="worker offline"))
    with pytest.raises(RuntimeError, match="worker offline"):
        await run_local_media(backend, {}, "local:x/model", VideoParams("p"), tmp_path)


async def _done():
    return None
