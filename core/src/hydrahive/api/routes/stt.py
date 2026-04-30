"""Speech-to-Text Endpoint — delegiert an hydrahive.voice.stt."""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.voice.stt import transcribe_bytes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stt", tags=["stt"])


@router.post("")
async def transcribe(
    audio: Annotated[UploadFile, File()],
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> JSONResponse:
    data = await audio.read()
    if not data:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error",
                    message="Leere Audio-Datei")

    mime = (audio.content_type or "audio/webm").split(";")[0].strip()
    try:
        text = await transcribe_bytes(data, mime=mime)
    except (ConnectionRefusedError, OSError):
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "validation_error",
                    message="STT nicht erreichbar — Wyoming faster-whisper läuft?")
    except asyncio.TimeoutError:
        raise coded(status.HTTP_504_GATEWAY_TIMEOUT, "validation_error",
                    message="STT-Timeout — Service überlastet?")
    except RuntimeError as e:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error",
                    message=str(e))
    return JSONResponse({"text": text})
