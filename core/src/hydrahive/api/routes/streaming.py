"""Streaming-Downloader API."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_auth
from hydrahive.credentials._crypto import decrypt, encrypt
from hydrahive.db import streaming as db
from hydrahive.settings import settings
from hydrahive.streaming import downloader, scraper

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/streaming", tags=["streaming"])

Auth = Annotated[tuple[str, str], Depends(require_auth)]


# ── Credentials ──────────────────────────────────────────────────────────────

class CredentialsIn(BaseModel):
    username: str
    password: str = ""
    plex_path: str = "/media/plex"


class CredentialsOut(BaseModel):
    username: str
    plex_path: str
    has_password: bool


@router.get("/credentials", response_model=CredentialsOut | None)
def get_credentials(auth: Auth) -> CredentialsOut | None:
    user_id, _ = auth
    row = db.get_credentials(user_id)
    if not row:
        return None
    return CredentialsOut(
        username=row["username"],
        plex_path=row["plex_path"],
        has_password=bool(row["password_enc"]),
    )


@router.put("/credentials", status_code=status.HTTP_204_NO_CONTENT)
def save_credentials(body: CredentialsIn, auth: Auth) -> None:
    user_id, _ = auth
    if body.password:
        enc = encrypt(body.password, settings.data_dir)
    else:
        existing = db.get_credentials(user_id)
        enc = existing["password_enc"] if existing else ""
    db.upsert_credentials(user_id, body.username, enc, body.plex_path)


# ── Scrape ────────────────────────────────────────────────────────────────────

class ScrapeIn(BaseModel):
    url: str


@router.post("/scrape")
async def scrape(body: ScrapeIn, auth: Auth) -> dict:
    user_id, _ = auth
    creds = db.get_credentials(user_id)
    if not creds:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Keine Ghostflix-Credentials gespeichert")
    password = decrypt(creds["password_enc"], settings.data_dir)
    try:
        result = await scraper.scrape_series(body.url, creds["username"], password)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    return result


# ── Download starten ─────────────────────────────────────────────────────────

class JobIn(BaseModel):
    episode_key: str
    episode: int
    bunny_video_id: str
    bunny_library_id: str


class StartDownloadIn(BaseModel):
    series_title: str
    series_url: str
    season: int
    plex_path: str
    jobs: list[JobIn]


@router.post("/download/start", status_code=status.HTTP_202_ACCEPTED)
async def start_download(
    body: StartDownloadIn,
    auth: Auth,
    bg: BackgroundTasks,
) -> dict:
    user_id, _ = auth

    if not body.jobs:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Keine Episoden ausgewählt")

    created_ids = []
    for j in body.jobs:
        out = downloader.build_output_path(
            body.plex_path, body.series_title, body.season, j.episode
        )
        job = db.create_job(
            user_id=user_id,
            series_title=body.series_title,
            series_url=body.series_url,
            season=body.season,
            episode=j.episode,
            episode_key=j.episode_key,
            bunny_video_id=j.bunny_video_id,
            bunny_library_id=j.bunny_library_id,
            output_path=out,
        )
        created_ids.append(job["id"])

    async def _run_all(ids: list[str]) -> None:
        for jid in ids:
            await downloader.run_job(jid)

    bg.add_task(_run_all, created_ids)
    return {"job_ids": created_ids}


# ── Jobs list + delete ────────────────────────────────────────────────────────

@router.get("/jobs")
def list_jobs(auth: Auth) -> list[dict]:
    user_id, _ = auth
    return db.list_jobs(user_id)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str, auth: Auth) -> None:
    user_id, _ = auth
    if not db.delete_job(job_id, user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job nicht gefunden")


@router.post("/jobs/{job_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_job(job_id: str, auth: Auth) -> None:
    user_id, _ = auth
    job = db.get_job(job_id)
    if not job or job["user_id"] != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job nicht gefunden")
    downloader.cancel_job(job_id)
