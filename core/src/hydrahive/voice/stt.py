"""Speech-to-Text via Wyoming faster-whisper (Container Port 10300).

`transcribe_bytes(audio, mime)` ist die Public-API für andere Module
(STT-Route, WhatsApp-Voice-Eingang). Konvertiert beliebiges Audio zu
16kHz Mono raw-PCM via ffmpeg, schickt an Wyoming, liefert Text.
"""
from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

STT_HOST = "127.0.0.1"
STT_PORT = 10300

_MIME_EXT = {
    "audio/webm": ".webm", "audio/ogg": ".ogg", "audio/ogg; codecs=opus": ".ogg",
    "audio/mpeg": ".mp3", "audio/mp4": ".m4a",
    "audio/wav": ".wav", "audio/x-wav": ".wav",
}


async def _send(writer, etype: str, data: dict | None = None, payload: bytes = b"") -> None:
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


async def _recv(reader) -> tuple[str, dict, bytes]:
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


async def _wyoming_transcribe(pcm: bytes, language: str = "de") -> str:
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(STT_HOST, STT_PORT), timeout=10.0
    )
    try:
        fmt = {"rate": 16000, "width": 2, "channels": 1}
        await _send(writer, "transcribe", {"language": language})
        await _send(writer, "audio-start", fmt)
        chunk = 16000 * 2  # 1s pro Chunk
        for i in range(0, len(pcm), chunk):
            await _send(writer, "audio-chunk", fmt, pcm[i:i + chunk])
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


async def _to_pcm(audio: bytes, mime: str) -> bytes:
    suffix = _MIME_EXT.get(mime.lower().strip(), ".bin")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src:
        src.write(audio)
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


async def transcribe_bytes(audio: bytes, mime: str = "audio/ogg",
                           language: str = "de") -> str:
    """Public API: Audio-Bytes → Transkript."""
    pcm = await _to_pcm(audio, mime)
    return await _wyoming_transcribe(pcm, language=language)
