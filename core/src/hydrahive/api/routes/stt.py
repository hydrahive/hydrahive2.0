"""Speech-to-Text Endpoint — Groq Whisper."""
from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.llm.client import _load_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stt", tags=["stt"])

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # Groq limit: 25 MB


def _get_groq_key() -> str:
    cfg = _load_config()
    for p in cfg.get("providers", []):
        if p.get("id") == "groq":
            return p.get("api_key", "")
    return ""


@router.post("")
async def transcribe(
    audio: Annotated[UploadFile, File()],
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> JSONResponse:
    key = _get_groq_key()
    if not key:
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "validation_error",
                    message="Kein Groq-API-Key konfiguriert")

    data = await audio.read()
    if len(data) > MAX_AUDIO_BYTES:
        raise coded(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "validation_error",
                    message="Audio zu groß (max 25 MB)")

    filename = audio.filename or "audio.webm"
    mime = audio.content_type or "audio/webm"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            GROQ_STT_URL,
            headers={"Authorization": f"Bearer {key}"},
            files={"file": (filename, data, mime)},
            data={"model": "whisper-large-v3-turbo", "response_format": "json"},
        )

    if resp.status_code != 200:
        logger.warning("Groq STT Fehler %s: %s", resp.status_code, resp.text[:200])
        raise coded(status.HTTP_502_BAD_GATEWAY, "validation_error",
                    message=f"Groq STT Fehler: {resp.status_code}")

    text = resp.json().get("text", "").strip()
    return JSONResponse({"text": text})
