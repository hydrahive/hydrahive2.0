"""Gemeinsamer Lebenszyklus für lokale Bild- und Videojobs."""
from __future__ import annotations

import asyncio
from pathlib import Path

from hydrahive.llm.video_backends._base import JobRef, JobStatus, VideoBackend, VideoParams

_POLL_TIMEOUT = 300.0
_POLL_START = 1.0
_POLL_MAX = 20.0


async def run_local_media(
    backend: VideoBackend,
    provider: dict,
    model: str,
    params: VideoParams,
    dest_dir: Path,
    *,
    timeout: float = _POLL_TIMEOUT,
) -> Path:
    """Submit, poll and fetch one local media job.

    The backend remains responsible for transport and output conversion. This
    runner deliberately has no cloud fallback: an unavailable local backend is
    an explicit generation error.
    """
    job = await backend.submit(provider, model, params)
    elapsed = 0.0
    interval = _POLL_START
    while elapsed < timeout:
        await asyncio.sleep(interval)
        elapsed += interval
        status: JobStatus = await backend.poll(provider, job)
        if status.state == "done":
            if status.url:
                job = JobRef(native_id=job.native_id, extra={**job.extra, "url": status.url})
            return await backend.fetch_output(provider, job, dest_dir)
        if status.state == "error":
            raise RuntimeError(status.error or "Lokales Media-Backend meldet einen Fehler")
        interval = min(interval * 2, _POLL_MAX)
    raise TimeoutError(f"Lokaler Media-Job nach {timeout:.0f}s nicht fertig")
