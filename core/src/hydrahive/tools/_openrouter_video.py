"""Geteilte Helfer für OpenRouter-Video-Jobs (asynchrone Jobs-API).

OpenRouter Video läuft NICHT über chat/completions — eigene asynchrone Jobs-API:
  POST   /api/v1/videos          → submit → job_id
  GET    /api/v1/videos/{job_id} → poll   → status + output.url
  GET    /api/v1/videos/models   → Modell-Liste

Das ist fundamental anders als Bild/Musik (synchron): submit gibt sofort eine
job_id zurück, der Caller muss pollen bis status="completed"|"failed".
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_VIDEOS_BASE = "https://openrouter.ai/api/v1/videos"


def openrouter_key() -> str:
    from hydrahive.llm._config import openrouter_key as _key
    return _key()


async def submit_video_job(
    prompt: str,
    model: str,
    *,
    key: str,
    width: int = 1280,
    height: int = 720,
    duration: int = 5,
    aspect_ratio: str = "16:9",
) -> str:
    """Startet einen Video-Generierungs-Job. Gibt job_id zurück.

    Raises RuntimeError bei API- oder Netzwerk-Fehler.
    """
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "width": width,
        "height": height,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _VIDEOS_BASE,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"OpenRouter Video-Submit Fehler {resp.status_code}: {resp.text[:400]}"
                )
            data = resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"Netzwerk-Fehler beim Video-Submit: {e}") from e

    job_id = data.get("id") or data.get("job_id") or ""
    if not job_id:
        raise RuntimeError(f"Kein job_id in OpenRouter-Antwort: {str(data)[:200]}")
    logger.info("video job submitted: id=%s model=%s", job_id, model)
    return str(job_id)


async def poll_video_job(job_id: str, *, key: str) -> dict:
    """Fragt den Status eines Video-Jobs ab.

    Gibt {"status": str, "url": str|None, "error": str|None} zurück.
    status: "pending" | "processing" | "completed" | "failed"

    Raises RuntimeError bei Netzwerk-Fehler oder 4xx/5xx.
    """
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{_VIDEOS_BASE}/{job_id}",
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"OpenRouter Video-Poll Fehler {resp.status_code}: {resp.text[:400]}"
                )
            data = resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"Netzwerk-Fehler beim Video-Poll: {e}") from e

    status = (data.get("status") or "pending").lower()
    url = (data.get("output") or {}).get("url") or data.get("url") or None
    error = data.get("error") or (data.get("output") or {}).get("error") or None
    logger.debug("video poll: id=%s status=%s", job_id, status)
    return {"status": status, "url": url, "error": error}


async def download_video(url: str, dest_dir: Path, *, key: str) -> Path:
    """Lädt ein fertig generiertes Video herunter und speichert es in dest_dir.

    Dateiname: <uuid>.mp4. Gibt den Pfad zurück.
    Raises RuntimeError bei Fehler.
    """
    import uuid
    from hydrahive.tools._openrouter_media import save_bytes

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {key}"},
                follow_redirects=True,
            )
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Video-Download Fehler {resp.status_code}: {resp.text[:200]}"
                )
            raw = resp.content
    except httpx.HTTPError as e:
        raise RuntimeError(f"Netzwerk-Fehler beim Video-Download: {e}") from e

    if not raw:
        raise RuntimeError("Video-Download lieferte leere Daten")

    path = save_bytes(raw, dest_dir, "mp4")
    logger.info("video downloaded: %s bytes → %s", len(raw), path)
    return path
