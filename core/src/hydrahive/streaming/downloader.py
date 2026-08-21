"""yt-dlp Download-Runner für Bunny-CDN-Videos."""
from __future__ import annotations

import asyncio
import logging
import re
import sqlite3
from pathlib import Path

from hydrahive.db import streaming as db
from hydrahive.streaming import _download_process as process

_DOWNLOAD_TIMEOUT = 7200
_STATUS_RETRIES = 3
_STATUS_RETRY_DELAY = 0.1
_PROGRESS_DB_TIMEOUT = 0.05
_CRITICAL_DB_TIMEOUT = 0.5
_EMBED_BASE = "https://iframe.mediadelivery.net/embed"

logger = logging.getLogger(__name__)
_download_lock = asyncio.Lock()


async def _update_status(
    job_id: str,
    status: str,
    progress: int = 0,
    error: str | None = None,
    *,
    best_effort: bool = False,
    expected_statuses: tuple[str, ...] | None = None,
) -> bool:
    """Schreibt einen Jobstatus, ohne SQLite-Wartezeit im Event-Loop."""
    attempts = 1 if best_effort else _STATUS_RETRIES
    timeout = _PROGRESS_DB_TIMEOUT if best_effort else _CRITICAL_DB_TIMEOUT
    for attempt in range(attempts):
        try:
            return await asyncio.to_thread(
                db.update_job_status,
                job_id,
                status,
                progress,
                error,
                timeout=timeout,
                expected_statuses=expected_statuses,
            )
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            if best_effort:
                logger.debug("Fortschritt wegen SQLite-Lock übersprungen: job=%s", job_id)
                return False
            if attempt + 1 == attempts:
                raise
            await asyncio.sleep(_STATUS_RETRY_DELAY * (attempt + 1))
    return False


async def _get_job(job_id: str) -> dict | None:
    return await asyncio.to_thread(db.get_job, job_id)


async def cancel_job(job_id: str) -> bool:
    """Bricht einen laufenden oder wartenden Job kontrolliert ab."""
    await process.cancel(job_id)
    await _update_status(
        job_id,
        "error",
        error="Abgebrochen",
        expected_statuses=("pending", "downloading"),
    )
    return True


def _remove_partial_output(out: Path) -> None:
    if not out.exists():
        return
    try:
        out.unlink()
    except OSError:
        logger.warning("Unvollständige Ausgabedatei konnte nicht entfernt werden: %s", out)


async def _record_failure(job_id: str, out: Path, error: str) -> None:
    await _update_status(
        job_id,
        "error",
        error=error,
        expected_statuses=("downloading",),
    )
    _remove_partial_output(out)


async def run_job(job_id: str) -> None:
    """Führt einen Download-Job aus. Blockiert bis fertig oder fehlgeschlagen."""
    job = await _get_job(job_id)
    if not job or job["status"] == "error":
        process.discard_cancel(job_id)
        return

    out = Path(job["output_path"])
    if out.exists():
        await _update_status(
            job_id, "skipped", progress=100, expected_statuses=("pending",)
        )
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    embed_url = f"{_EMBED_BASE}/{job['bunny_library_id']}/{job['bunny_video_id']}"

    async with _download_lock:
        current = await _get_job(job_id)
        if not current or current["status"] == "error" or process.is_cancelled(job_id):
            process.discard_cancel(job_id)
            return
        started = await _update_status(
            job_id, "downloading", progress=0, expected_statuses=("pending",)
        )
        if not started:
            process.discard_cancel(job_id)
            return
        try:
            await asyncio.wait_for(
                _ytdlp(job_id, embed_url, str(out)), timeout=_DOWNLOAD_TIMEOUT
            )
        except process.DownloadCancelled:
            await _record_failure(job_id, out, "Abgebrochen")
        except asyncio.TimeoutError:
            logger.error("Download-Timeout job=%s (>%ds)", job_id, _DOWNLOAD_TIMEOUT)
            await _record_failure(
                job_id, out, f"Timeout nach {_DOWNLOAD_TIMEOUT // 3600}h"
            )
        except asyncio.CancelledError:
            await asyncio.shield(_record_failure(job_id, out, "Abgebrochen"))
            raise
        except Exception as exc:
            logger.error("Download fehlgeschlagen job=%s: %s", job_id, exc)
            await _record_failure(job_id, out, str(exc))
        else:
            # Der Download ist vollständig. Ein DB-Fehler an dieser Stelle darf
            # die fertige Mediendatei keinesfalls als Teil-Download löschen.
            await _update_status(
                job_id, "done", progress=100, expected_statuses=("downloading",)
            )
        finally:
            process.discard_cancel(job_id)


async def _ytdlp(job_id: str, url: str, output: str) -> None:
    async def on_progress(progress: int) -> None:
        await _update_status(
            job_id,
            "downloading",
            progress=progress,
            best_effort=True,
            expected_statuses=("downloading",),
        )

    await process.run(job_id, url, output, on_progress)


def build_output_path(plex_path: str, series_title: str, season: int, episode: int) -> str:
    safe_title = re.sub(r'[<>:"/\\|?*]', "", series_title).strip()
    return str(
        Path(plex_path)
        / safe_title
        / f"Staffel {season}"
        / f"{safe_title} - S{season:02d}E{episode:02d}.mkv"
    )
