"""DB-Operationen für Streaming-Downloader."""
from __future__ import annotations

import uuid
from typing import Any

from hydrahive.db.connection import db


def _row(r: Any) -> dict:
    return dict(r)


# ── Credentials ──────────────────────────────────────────────────────────────

def get_credentials(user_id: str, provider: str = "ghostflix") -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM streaming_credentials WHERE user_id=? AND provider=?",
            (user_id, provider),
        ).fetchone()
    return _row(row) if row else None


def upsert_credentials(
    user_id: str,
    username: str,
    password_enc: str,
    plex_path: str,
    provider: str = "ghostflix",
) -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO streaming_credentials (id, user_id, provider, username, password_enc, plex_path)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, provider) DO UPDATE SET
                 username=excluded.username,
                 password_enc=excluded.password_enc,
                 plex_path=excluded.plex_path""",
            (str(uuid.uuid4()), user_id, provider, username, password_enc, plex_path),
        )


# ── Jobs ─────────────────────────────────────────────────────────────────────

def create_job(
    user_id: str,
    series_title: str,
    series_url: str,
    season: int,
    episode: int,
    episode_key: str,
    bunny_video_id: str,
    bunny_library_id: str,
    output_path: str,
    provider: str = "ghostflix",
) -> dict:
    job_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            """INSERT INTO streaming_jobs
               (id, user_id, provider, series_title, series_url, season, episode,
                episode_key, bunny_video_id, bunny_library_id, output_path)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (job_id, user_id, provider, series_title, series_url, season, episode,
             episode_key, bunny_video_id, bunny_library_id, output_path),
        )
        row = conn.execute(
            "SELECT * FROM streaming_jobs WHERE id=?", (job_id,)
        ).fetchone()
    return _row(row)


def list_jobs(user_id: str, limit: int = 50) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """SELECT * FROM streaming_jobs WHERE user_id=?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    return [_row(r) for r in rows]


def get_job(job_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM streaming_jobs WHERE id=?", (job_id,)
        ).fetchone()
    return _row(row) if row else None


def update_job_status(
    job_id: str,
    status: str,
    progress: int = 0,
    error: str | None = None,
) -> None:
    with db() as conn:
        conn.execute(
            """UPDATE streaming_jobs SET status=?, progress=?, error=?,
               updated_at=datetime('now') WHERE id=?""",
            (status, progress, error, job_id),
        )


def count_active_jobs(user_id: str) -> int:
    with db() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM streaming_jobs WHERE user_id=? AND status IN ('pending','downloading')",
            (user_id,),
        ).fetchone()[0]
