"""Subprozess-Lebenszyklus für Streaming-Downloads."""
from __future__ import annotations

import asyncio
import logging
import os
import re
import signal
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

_PROCESS_STOP_TIMEOUT = 5.0
_PROGRESS_RE = re.compile(r"(\d+\.?\d*)%")
_YTDLP_BIN = str(Path(sys.executable).parent / "yt-dlp")

logger = logging.getLogger(__name__)

running_processes: dict[str, asyncio.subprocess.Process] = {}
cancelled_jobs: set[str] = set()


class DownloadCancelled(RuntimeError):
    """Der Benutzer hat den Download kontrolliert abgebrochen."""


def is_cancelled(job_id: str) -> bool:
    return job_id in cancelled_jobs


def discard_cancel(job_id: str) -> None:
    cancelled_jobs.discard(job_id)


async def stop_process(proc: asyncio.subprocess.Process) -> None:
    """Beendet die gesamte yt-dlp/ffmpeg-Prozessgruppe und reapet sie."""
    if proc.returncode is not None:
        await proc.wait()
        return

    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass

    try:
        await asyncio.wait_for(proc.wait(), timeout=_PROCESS_STOP_TIMEOUT)
        return
    except asyncio.TimeoutError:
        pass

    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    await proc.wait()


async def cancel(job_id: str) -> None:
    """Setzt das Cancel-Signal und stoppt einen bereits registrierten Prozess."""
    cancelled_jobs.add(job_id)
    proc = running_processes.get(job_id)
    if proc is not None:
        await stop_process(proc)


async def run(
    job_id: str,
    url: str,
    output: str,
    on_progress: Callable[[int], Awaitable[None]],
) -> None:
    """Startet yt-dlp, meldet Fortschritt und garantiert Prozess-Cleanup."""
    if is_cancelled(job_id):
        raise DownloadCancelled("Abgebrochen")

    cmd = [
        _YTDLP_BIN,
        "--format", "bestvideo+bestaudio/best",
        "--merge-output-format", "mkv",
        "--output", output,
        "--no-playlist",
        "--retries", "5",
        "--fragment-retries", "5",
        "--concurrent-fragments", "4",
        "--newline",
        "--progress",
        url,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
        start_new_session=True,
    )
    running_processes[job_id] = proc
    assert proc.stdout is not None
    last_progress: int | None = None

    try:
        # Cancel kann während create_subprocess_exec eintreffen.
        if is_cancelled(job_id):
            await stop_process(proc)
            raise DownloadCancelled("Abgebrochen")

        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            match = _PROGRESS_RE.search(line.decode("utf-8", errors="replace"))
            if match:
                progress = min(99, int(float(match.group(1))))
                if progress != last_progress:
                    await on_progress(progress)
                    last_progress = progress

        await proc.wait()
        if is_cancelled(job_id):
            raise DownloadCancelled("Abgebrochen")
        if proc.returncode not in (0, None):
            raise RuntimeError(f"yt-dlp exited with code {proc.returncode}")
    except asyncio.CancelledError:
        await asyncio.shield(stop_process(proc))
        raise
    except Exception:
        if proc.returncode is None:
            await asyncio.shield(stop_process(proc))
        raise
    finally:
        if running_processes.get(job_id) is proc:
            running_processes.pop(job_id, None)
