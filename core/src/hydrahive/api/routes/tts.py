"""Text-to-Speech Endpoint — dünner HTTP-Wrapper um voice/tts.py."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.voice import tts as voice_tts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tts", tags=["tts"])

DEFAULT_VOICE = "German_FriendlyMan"


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    voice: str = Field(default=DEFAULT_VOICE, max_length=80)


def _runtime_to_coded(e: RuntimeError):
    msg = str(e).lower()
    if "timeout" in msg:
        return coded(status.HTTP_504_GATEWAY_TIMEOUT, "validation_error", message=str(e))
    if "fehlt" in msg:
        return coded(status.HTTP_503_SERVICE_UNAVAILABLE, "validation_error", message=str(e))
    return coded(status.HTTP_502_BAD_GATEWAY, "validation_error", message=str(e))


@router.get("/voices")
async def list_voices(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    language: str = "german",
) -> JSONResponse:
    if not voice_tts.is_available():
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "validation_error",
                    message="mmx CLI nicht installiert")
    try:
        voices = await voice_tts.list_voices(language=language)
    except RuntimeError as e:
        raise _runtime_to_coded(e)
    return JSONResponse({"voices": voices})


@router.post("")
async def synthesize(
    body: SpeakIn,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> Response:
    if not voice_tts.is_available():
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "validation_error",
                    message="mmx CLI nicht installiert")
    try:
        mp3 = await voice_tts.synthesize_mp3(body.text, body.voice)
    except RuntimeError as e:
        raise _runtime_to_coded(e)
    return Response(content=mp3, media_type="audio/mpeg")
