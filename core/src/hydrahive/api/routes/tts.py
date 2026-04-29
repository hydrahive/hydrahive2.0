"""Text-to-Speech Endpoint — MiniMax via mmx CLI."""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tts", tags=["tts"])

DEFAULT_VOICE = "German_FriendlyMan"


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    voice: str = Field(default=DEFAULT_VOICE, max_length=80)


def _mmx_available() -> bool:
    return shutil.which("mmx") is not None


@router.get("/voices")
async def list_voices(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    language: str = "german",
) -> JSONResponse:
    if not _mmx_available():
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "validation_error",
                    message="mmx CLI nicht installiert")
    proc = await asyncio.create_subprocess_exec(
        "mmx", "speech", "voices", "--language", language, "--output", "json", "--quiet",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15.0)
    except asyncio.TimeoutError:
        proc.kill()
        raise coded(status.HTTP_504_GATEWAY_TIMEOUT, "validation_error",
                    message="mmx Voices-Abruf Timeout")
    if proc.returncode != 0:
        raise coded(status.HTTP_502_BAD_GATEWAY, "validation_error",
                    message="mmx voices fehlgeschlagen")
    try:
        voices = json.loads(stdout.decode())
    except json.JSONDecodeError:
        voices = []
    return JSONResponse({"voices": voices})


@router.post("")
async def synthesize(
    body: SpeakIn,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> Response:
    if not _mmx_available():
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "validation_error",
                    message="mmx CLI nicht installiert")

    out_path = Path(tempfile.mkstemp(suffix=".mp3", prefix="hh-tts-")[1])
    try:
        proc = await asyncio.create_subprocess_exec(
            "mmx", "speech", "synthesize",
            "--text", body.text,
            "--voice", body.voice,
            "--out", str(out_path),
            "--quiet",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
        except asyncio.TimeoutError:
            proc.kill()
            raise coded(status.HTTP_504_GATEWAY_TIMEOUT, "validation_error",
                        message="mmx TTS-Timeout")
        if proc.returncode != 0:
            err = stderr.decode(errors="replace")[:300] if stderr else ""
            logger.warning("mmx synthesize fehlgeschlagen: %s", err)
            raise coded(status.HTTP_502_BAD_GATEWAY, "validation_error",
                        message=f"mmx TTS-Fehler: {err or 'unbekannt'}")
        audio = out_path.read_bytes()
        return Response(content=audio, media_type="audio/mpeg")
    finally:
        out_path.unlink(missing_ok=True)
