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


async def _send(writer: asyncio.StreamWriter, etype: str,
                data: dict | None = None, payload: bytes = b"") -> None:
    """Wyoming wire format: header-JSON\n [data-JSON] [binary]."""
    header: dict = {"type": etype}
    data_bytes = b""
    if data:
        data_bytes = json.dumps(data, separators=(",", ":")).encode()
        header["data_length"] = len(data_bytes)
    if payload:
        header["payload_length"] = len(payload)
    writer.write(json.dumps(header, separators=(",", ":")).encode() + b"\n")
    if data_bytes:
        writer.write(data_bytes)
    if payload:
        writer.write(payload)
    await writer.drain()


async def _recv(reader: asyncio.StreamReader) -> tuple[str, dict, bytes]:
    """Liest ein Wyoming-Event: header → optionaler data-Block → optionaler payload."""
    line = await asyncio.wait_for(reader.readline(), timeout=60.0)
    if not line:
        raise ConnectionError("Wyoming-Verbindung unerwartet geschlossen")
    header = json.loads(line.decode())
    data: dict = {}
    if header.get("data_length", 0) > 0:
        raw = await asyncio.wait_for(reader.readexactly(header["data_length"]), timeout=10.0)
        data = json.loads(raw)
    payload = b""
    if header.get("payload_length", 0) > 0:
        payload = await asyncio.wait_for(reader.readexactly(header["payload_length"]), timeout=30.0)
    return header.get("type", ""), data, payload


async def _wyoming_transcribe(pcm: bytes, rate: int = 16000,
                               width: int = 2, channels: int = 1) -> str:
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(STT_HOST, STT_PORT), timeout=10.0
    )
    try:
        fmt = {"rate": rate, "width": width, "channels": channels}
        await _send(writer, "transcribe", {"language": "de"})
        await _send(writer, "audio-start", fmt)
        chunk_size = rate * width * channels  # 1 Sekunde pro Chunk
        for i in range(0, len(pcm), chunk_size):
            await _send(writer, "audio-chunk", fmt, pcm[i:i + chunk_size])
        await _send(writer, "audio-stop")

        while True:
            etype, data, _ = await _recv(reader)
            if etype == "transcript":
                return data.get("text", "").strip()
            if etype == "error":
                raise RuntimeError(data.get("text", "STT-Fehler"))
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
            "-ar", "16000", "-ac", "1", "-f", "s16le", str(pcm_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=30.0)
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg fehlgeschlagen")
        return pcm_path.read_bytes()
    finally:
        src_path.unlink(missing_ok=True)
        pcm_path.unlink(missing_ok=True)


_MIME_EXT = {
    "audio/webm": ".webm", "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",  "audio/mp4": ".m4a",
    "audio/wav": ".wav",   "audio/x-wav": ".wav",
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
                    message="STT nicht erreichbar — Wyoming faster-whisper läuft?")
    except asyncio.TimeoutError:
        raise coded(status.HTTP_504_GATEWAY_TIMEOUT, "validation_error",
                    message="STT-Timeout — Service überlastet?")

    return JSONResponse({"text": text})
