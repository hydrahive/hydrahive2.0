"""Speech-to-Text Endpoint — Wyoming faster-whisper."""
from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stt", tags=["stt"])

STT_HOST = "127.0.0.1"
STT_PORT = 10300


def _event(evt_type: str, data: dict, payload: bytes = b"") -> bytes:
    """Serialisiert ein Wyoming-Event: JSON-Zeile + optionale Binary-Payload."""
    header = json.dumps({
        "type": evt_type,
        "data": data,
        "data_length": 0,
        "payload_length": len(payload),
    }) + "\n"
    return header.encode() + payload


async def _wyoming_transcribe(pcm_bytes: bytes) -> str:
    """Schickt rohes PCM (16kHz, 16-bit, Mono) ans Wyoming-STT."""
    reader, writer = await asyncio.open_connection(STT_HOST, STT_PORT)
    try:
        writer.write(_event("transcribe", {"language": "de"}))
        writer.write(_event("audio-start", {"rate": 16000, "width": 2, "channels": 1}))

        chunk_size = 4096
        for i in range(0, len(pcm_bytes), chunk_size):
            writer.write(_event(
                "audio-chunk",
                {"rate": 16000, "width": 2, "channels": 1},
                pcm_bytes[i:i + chunk_size],
            ))

        writer.write(_event("audio-stop", {}))
        await writer.drain()

        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=30.0)
            if not line:
                break
            msg = json.loads(line.decode())
            if msg.get("type") == "transcript":
                return msg.get("data", {}).get("text", "").strip()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
    return ""


async def _to_pcm(audio_bytes: bytes, suffix: str) -> bytes:
    """Konvertiert beliebiges Audio zu 16kHz Mono raw-PCM via ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src:
        src.write(audio_bytes)
        src_path = Path(src.name)
    pcm_path = src_path.with_suffix(".pcm")
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(src_path),
            "-ar", "16000", "-ac", "1",
            "-f", "s16le",          # raw signed 16-bit little-endian PCM, kein WAV-Header
            str(pcm_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=30.0)
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg Konvertierung fehlgeschlagen")
        return pcm_path.read_bytes()
    finally:
        src_path.unlink(missing_ok=True)
        pcm_path.unlink(missing_ok=True)


_MIME_EXT = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
}


@router.post("")
async def transcribe(
    audio: Annotated[UploadFile, File()],
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> JSONResponse:
    data = await audio.read()
    if not data:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message="Leere Audio-Datei")

    mime = (audio.content_type or "audio/webm").split(";")[0].strip()
    suffix = _MIME_EXT.get(mime, ".webm")

    try:
        pcm = await _to_pcm(data, suffix)
    except Exception as e:
        logger.warning("Audio-Konvertierung fehlgeschlagen: %s", e)
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error",
                    message="Audio-Konvertierung fehlgeschlagen — ffmpeg installiert?")

    try:
        text = await _wyoming_transcribe(pcm)
    except (ConnectionRefusedError, OSError):
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "validation_error",
                    message="STT-Service nicht erreichbar — Wyoming faster-whisper läuft?")
    except asyncio.TimeoutError:
        raise coded(status.HTTP_504_GATEWAY_TIMEOUT, "validation_error",
                    message="STT-Timeout — Service überlastet?")

    return JSONResponse({"text": text})
