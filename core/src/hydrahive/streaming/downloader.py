"""yt-dlp Download-Runner für Bunny-CDN-Videos."""
from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from pathlib import Path

# Maximale Download-Dauer pro Job: 2 Stunden
_DOWNLOAD_TIMEOUT = 7200

from hydrahive.db import streaming as db

logger = logging.getLogger(__name__)

_PROGRESS_RE = re.compile(r'(\d+\.?\d*)%')
_EMBED_BASE = "https://iframe.mediadelivery.net/embed"
# Binary im gleichen venv-bin wie der laufende Python-Interpreter
_YTDLP_BIN = str(Path(sys.executable).parent / "yt-dlp")

# Max 1 concurrent download process-wide (jobs queue naturally via asyncio tasks)
_download_lock = asyncio.Lock()
_running_tasks: dict[str, asyncio.Task] = {}  # job_id → laufender Task


def cancel_job(job_id: str) -> bool:
    """Bricht einen laufenden oder wartenden Job ab. Gibt True zurück wenn gefunden."""
    task = _running_tasks.get(job_id)
    if task and not task.done():
        task.cancel()
    db.update_job_status(job_id, "error", error="Abgebrochen")
    return True


async def run_job(job_id: str) -> None:
    """Führt einen Download-Job aus. Blockiert bis fertig oder fehlgeschlagen."""
    job = db.get_job(job_id)
    if not job:
        return
    if job["status"] == "error":  # wurde bereits abgebrochen
        return

    out = Path(job["output_path"])
    if out.exists():
        db.update_job_status(job_id, "skipped", progress=100)
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    embed_url = f"{_EMBED_BASE}/{job['bunny_library_id']}/{job['bunny_video_id']}"

    task = asyncio.current_task()
    if task:
        _running_tasks[job_id] = task

    async with _download_lock:
        if db.get_job(job_id)["status"] == "error":  # abgebrochen während er wartete
            _running_tasks.pop(job_id, None)
            return
        db.update_job_status(job_id, "downloading", progress=0)
        try:
            await asyncio.wait_for(_ytdlp(job_id, embed_url, str(out)), timeout=_DOWNLOAD_TIMEOUT)
            db.update_job_status(job_id, "done", progress=100)
        except asyncio.TimeoutError:
            logger.error("Download-Timeout job=%s (>%ds)", job_id, _DOWNLOAD_TIMEOUT)
            db.update_job_status(job_id, "error", error=f"Timeout nach {_DOWNLOAD_TIMEOUT // 3600}h")
            if out.exists():
                try:
                    out.unlink()
                except OSError:
                    pass
        except Exception as exc:
            logger.error("Download fehlgeschlagen job=%s: %s", job_id, exc)
            db.update_job_status(job_id, "error", error=str(exc))
            if out.exists():
                try:
                    out.unlink()
                except OSError:
                    pass
        finally:
            _running_tasks.pop(job_id, None)


async def _ytdlp(job_id: str, url: str, output: str) -> None:
    # create_subprocess_exec — keine Shell, kein Injection-Risiko.
    # url und output kommen aus der DB (UUID-Werte + sanitized Path).
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
    )
    assert proc.stdout is not None

    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        m = _PROGRESS_RE.search(line.decode("utf-8", errors="replace"))
        if m:
            pct = min(99, int(float(m.group(1))))
            db.update_job_status(job_id, "downloading", progress=pct)

    await proc.wait()
    if proc.returncode not in (0, None):
        raise RuntimeError(f"yt-dlp exited with code {proc.returncode}")


def build_output_path(plex_path: str, series_title: str, season: int, episode: int) -> str:
    safe_title = re.sub(r'[<>:"/\\|?*]', "", series_title).strip()
    return str(
        Path(plex_path)
        / safe_title
        / f"Staffel {season}"
        / f"{safe_title} - S{season:02d}E{episode:02d}.mkv"
    )
