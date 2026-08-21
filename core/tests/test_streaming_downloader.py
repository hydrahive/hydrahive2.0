"""Regressionstests für DB-Locks und Prozess-Cleanup im Streaming-Downloader."""
from __future__ import annotations

import asyncio
import sqlite3

import pytest

from hydrahive.streaming import _download_process as download_process
from hydrahive.streaming import downloader


class _Stdout:
    def __init__(self, lines: list[bytes] | None = None) -> None:
        self._lines = iter(lines or [])

    async def readline(self) -> bytes:
        return next(self._lines, b"")


class _BlockingStdout:
    async def readline(self) -> bytes:
        await asyncio.Event().wait()
        return b""


class _Process:
    def __init__(self, stdout: object, *, pid: int = 4242) -> None:
        self.stdout = stdout
        self.pid = pid
        self.returncode: int | None = None
        self.wait_calls = 0

    async def wait(self) -> int:
        self.wait_calls += 1
        while self.returncode is None:
            await asyncio.sleep(0)
        return self.returncode


@pytest.mark.asyncio
async def test_progress_lock_is_best_effort_and_does_not_escape(monkeypatch):
    def locked(*args, **kwargs) -> None:
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(downloader.db, "update_job_status", locked)

    written = await downloader._update_status(
        "job-1", "downloading", progress=12, best_effort=True
    )

    assert written is False


@pytest.mark.asyncio
async def test_critical_status_retries_transient_database_lock(monkeypatch):
    calls = 0

    def eventually_writes(*args, **kwargs) -> None:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise sqlite3.OperationalError("database is locked")
        return True

    monkeypatch.setattr(downloader.db, "update_job_status", eventually_writes)
    monkeypatch.setattr(downloader, "_STATUS_RETRY_DELAY", 0)

    written = await downloader._update_status("job-1", "done", progress=100)

    assert written is True
    assert calls == 3


@pytest.mark.asyncio
async def test_ytdlp_writes_each_progress_percentage_only_once(monkeypatch):
    proc = _Process(_Stdout([b"[download] 1.0%\n", b"[download] 1.4%\n", b"[download] 2.0%\n"]))
    proc.returncode = 0
    updates: list[int] = []

    async def create_process(*args, **kwargs):
        return proc

    async def update_status(job_id: str, status: str, **kwargs) -> bool:
        updates.append(kwargs["progress"])
        return True

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)
    monkeypatch.setattr(downloader, "_update_status", update_status)

    await downloader._ytdlp("job-1", "https://example.invalid/video", "/tmp/out.mkv")

    assert updates == [1, 2]


@pytest.mark.asyncio
async def test_cancel_stops_process_and_records_aborted_status(monkeypatch):
    proc = _Process(_Stdout())
    statuses: list[tuple[str, str, str | None]] = []

    def signal_process(pid: int, signal: int) -> None:
        assert pid == proc.pid
        proc.returncode = -signal

    async def update_status(job_id: str, status: str, **kwargs) -> bool:
        statuses.append((job_id, status, kwargs.get("error")))
        return True

    download_process.running_processes["job-1"] = proc
    monkeypatch.setattr(download_process.os, "killpg", signal_process)
    monkeypatch.setattr(downloader, "_update_status", update_status)

    try:
        found = await downloader.cancel_job("job-1")
    finally:
        download_process.running_processes.clear()
        download_process.cancelled_jobs.clear()

    assert found is True
    assert proc.wait_calls == 1
    assert statuses == [("job-1", "error", "Abgebrochen")]


@pytest.mark.asyncio
async def test_coroutine_cancellation_reaps_ytdlp_process(monkeypatch):
    proc = _Process(_BlockingStdout())

    async def create_process(*args, **kwargs):
        return proc

    def signal_process(pid: int, signal: int) -> None:
        proc.returncode = -signal

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)
    monkeypatch.setattr(download_process.os, "killpg", signal_process)

    task = asyncio.create_task(
        downloader._ytdlp("job-1", "https://example.invalid/video", "/tmp/out.mkv")
    )
    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert proc.wait_calls == 1
    assert "job-1" not in download_process.running_processes


@pytest.mark.asyncio
async def test_cancel_before_process_creation_prevents_spawn(monkeypatch):
    async def unexpected_process(*args, **kwargs):
        raise AssertionError("yt-dlp darf nach Cancel nicht mehr starten")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", unexpected_process)
    download_process.cancelled_jobs.add("job-1")
    try:
        with pytest.raises(download_process.DownloadCancelled):
            await downloader._ytdlp(
                "job-1", "https://example.invalid/video", "/tmp/out.mkv"
            )
    finally:
        download_process.cancelled_jobs.clear()


@pytest.mark.asyncio
async def test_cancel_during_process_creation_stops_new_process(monkeypatch):
    proc = _Process(_Stdout())

    async def create_process(*args, **kwargs):
        download_process.cancelled_jobs.add("job-1")
        return proc

    def signal_process(pid: int, signal: int) -> None:
        proc.returncode = -signal

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)
    monkeypatch.setattr(download_process.os, "killpg", signal_process)

    try:
        with pytest.raises(download_process.DownloadCancelled):
            await downloader._ytdlp(
                "job-1", "https://example.invalid/video", "/tmp/out.mkv"
            )
    finally:
        download_process.running_processes.clear()
        download_process.cancelled_jobs.clear()

    assert proc.wait_calls == 1


@pytest.mark.asyncio
async def test_progress_write_error_stops_and_reaps_process(monkeypatch):
    proc = _Process(_Stdout([b"[download] 12.0%\n"]))

    async def create_process(*args, **kwargs):
        return proc

    async def broken_update(*args, **kwargs) -> bool:
        raise RuntimeError("write failed")

    def signal_process(pid: int, signal: int) -> None:
        proc.returncode = -signal

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)
    monkeypatch.setattr(downloader, "_update_status", broken_update)
    monkeypatch.setattr(download_process.os, "killpg", signal_process)

    with pytest.raises(RuntimeError, match="write failed"):
        await downloader._ytdlp(
            "job-1", "https://example.invalid/video", "/tmp/out.mkv"
        )

    assert proc.wait_calls == 1
    assert "job-1" not in download_process.running_processes


@pytest.mark.asyncio
async def test_rejected_pending_to_downloading_transition_does_not_spawn(
    monkeypatch, tmp_path
):
    job = {
        "status": "pending",
        "output_path": str(tmp_path / "episode.mkv"),
        "bunny_library_id": "library",
        "bunny_video_id": "video",
    }
    spawned = False

    async def get_job(job_id: str) -> dict:
        return job

    async def reject_transition(*args, **kwargs) -> bool:
        return False

    async def ytdlp(*args, **kwargs) -> None:
        nonlocal spawned
        spawned = True

    monkeypatch.setattr(downloader, "_get_job", get_job)
    monkeypatch.setattr(downloader, "_update_status", reject_transition)
    monkeypatch.setattr(downloader, "_ytdlp", ytdlp)

    await downloader.run_job("job-1")

    assert spawned is False


@pytest.mark.asyncio
async def test_done_status_db_error_does_not_delete_completed_file(
    monkeypatch, tmp_path
):
    output = tmp_path / "episode.mkv"
    job = {
        "status": "pending",
        "output_path": str(output),
        "bunny_library_id": "library",
        "bunny_video_id": "video",
    }

    async def get_job(job_id: str) -> dict:
        return job

    async def update_status(job_id: str, status: str, **kwargs) -> bool:
        if status == "done":
            raise sqlite3.OperationalError("database is locked")
        return True

    async def ytdlp(job_id: str, url: str, path: str) -> None:
        output.write_bytes(b"complete video")

    monkeypatch.setattr(downloader, "_get_job", get_job)
    monkeypatch.setattr(downloader, "_update_status", update_status)
    monkeypatch.setattr(downloader, "_ytdlp", ytdlp)

    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        await downloader.run_job("job-1")

    assert output.read_bytes() == b"complete video"
