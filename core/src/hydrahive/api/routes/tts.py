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
from hydrahive.voice import _quota as tts_quota

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tts", tags=["tts"])

DEFAULT_VOICE = "German_FriendlyMan"


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    voice: str = Field(default=DEFAULT_VOICE, max_length=80)
    provider: str = Field(default="minimax", max_length=20)


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
    provider: str = "minimax",
) -> JSONResponse:
    if provider == "openrouter":
        from hydrahive.llm import media_models
        model = media_models.get_media_model("tts")
        voices = await media_models.voices_for(model)
        return JSONResponse({"voices": [{"voice_id": v, "voice_name": v} for v in voices],
                             "model": model})
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
    # mmx-Gate NUR für MiniMax — local (Piper) und OpenRouter brauchen kein mmx.
    if body.provider == "minimax" and not voice_tts.is_available():
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "validation_error",
                    message="mmx CLI nicht installiert")
    username, _ = auth
    allowed, used, cap = tts_quota.check_and_increment(username)
    if not allowed:
        raise coded(
            status.HTTP_429_TOO_MANY_REQUESTS, "quota_exceeded",
            message=f"Tägliches TTS-Limit erreicht ({used}/{cap}). "
                    f"Reset um Mitternacht UTC. Override via ENV TTS_DAILY_CAP.",
        )
    try:
        if body.provider == "local":
            data, media_type = await voice_tts.synthesize_local(body.text, body.voice)
        elif body.provider == "openrouter":
            data, media_type = await voice_tts.synthesize_openrouter(body.text, body.voice)
        else:
            data = await voice_tts.synthesize_mp3(body.text, body.voice)
            media_type = "audio/mpeg"
    except RuntimeError as e:
        raise _runtime_to_coded(e)
    except Exception as e:
        # TTS hängt an externen Diensten (Container/Subprozess) — unerwartete
        # Fehler nie als rohes HTTP 500 leaken, sondern als 502 mit Meldung.
        logger.warning("TTS unerwarteter Fehler (provider=%s): %s", body.provider, e)
        raise coded(status.HTTP_502_BAD_GATEWAY, "validation_error", message=str(e) or type(e).__name__)
    logger.info("TTS-Quota %s: %d/%d (provider=%s)", username, used, cap, body.provider)
    return Response(content=data, media_type=media_type)
