"""Speech-to-Text Endpoint — Wyoming faster-whisper."""
from __future__ import annotations

import asyncio
import logging
import struct
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


async def _wyoming_transcribe(audio_bytes: bytes) -> str:
    """Schickt WAV-Audio über das Wyoming-Protokoll an faster-whisper."""
    reader, writer = await asyncio.open_connection(STT_HOST, STT_PORT)
    try:
        # Wyoming Transcribe-Request senden
        payload = b'{"type":"transcribe","data":{"language":"de","audio_format":{"type":"pcm","rate":16000,"width":2,"channels":1}}}\n'
        writer.write(payload)
        await writer.drain()

        # Audio-Bytes als Wyoming AudioChunk senden
        header = f'{{"type":"audio-chunk","data":{{"rate":16000,"width":2,"channels":1,"audio":true}}}}\n'.encode()
        writer.write(header)
        writer.write(struct.pack("<I", len(audio_bytes)))
        writer.write(audio_bytes)
        await writer.drain()

        # AudioStop senden
        writer.write(b'{"type":"audio-stop","data":{}}\n')
        await writer.drain()

        # Auf Transcript warten
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=30.0)
            if not line:
                break
            import json
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


async def _convert_to_wav(audio_bytes: bytes, suffix: str) -> bytes:
    """Konvertiert Audio zu 16kHz Mono WAV via ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src:
        src.write(audio_bytes)
        src_path = Path(src.name)
    wav_path = src_path.with_suffix(".wav")
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(src_path),
            "-ar", "16000", "-ac", "1", "-f", "wav", str(wav_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=30.0)
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg Konvertierung fehlgeschlagen")
        return wav_path.read_bytes()
    finally:
        src_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)


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
        wav = await _convert_to_wav(data, suffix)
    except Exception as e:
        logger.warning("Audio-Konvertierung fehlgeschlagen: %s", e)
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error",
                    message="Audio-Konvertierung fehlgeschlagen — ffmpeg installiert?")

    try:
        text = await _wyoming_transcribe(wav)
    except (ConnectionRefusedError, OSError):
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "validation_error",
                    message="STT-Service nicht erreichbar — Wyoming faster-whisper installiert?")
    except asyncio.TimeoutError:
        raise coded(status.HTTP_504_GATEWAY_TIMEOUT, "validation_error",
                    message="STT-Timeout — Service überlastet?")

    return JSONResponse({"text": text})
