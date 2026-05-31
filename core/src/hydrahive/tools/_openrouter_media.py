"""Geteilte Helfer für OpenRouter-Media-Tools (Bild, Musik, Audio …).

Key-Lookup + base64→Datei-Speicherung an EINER Stelle — kein Duplikat über die
einzelnen Tool-Module. Die Datei muss in einem servable-Verzeichnis landen
(Aufrufer übergibt ctx.workspace/… → von /api/files ausgeliefert).
"""
from __future__ import annotations

import io
import json
import uuid
import wave
from pathlib import Path
from typing import Any


def openrouter_key() -> str:
    from hydrahive.llm._config import openrouter_key as _key
    return _key()


def is_done_line(line: str) -> bool:
    """True wenn die SSE-Zeile das Stream-Ende markiert (`data: [DONE]`)."""
    if not line.startswith("data:"):
        return False
    return line[len("data:"):].strip() == "[DONE]"


def audio_chunk_from_sse_line(line: str) -> str | None:
    """Extrahiert delta.audio.data (base64) aus einer SSE-Zeile, sonst None."""
    if not line.startswith("data:"):
        return None
    payload = line[len("data:"):].strip()
    if not payload or payload == "[DONE]":
        return None
    try:
        chunk = json.loads(payload)
    except (json.JSONDecodeError, ValueError):
        return None
    delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
    audio = delta.get("audio")
    if isinstance(audio, dict):
        return audio.get("data")
    return None


async def read_audio_sse(resp: Any) -> tuple[list[str], bool]:
    """Liest den OpenRouter-Audio-SSE-Stream über rohe Bytes.

    Puffert und trennt selbst an `\\n` — der Audio-Chunk ist EINE mehrere MB
    große Einzelzeile, die httpx' aiter_lines() nicht-deterministisch zerlegt.
    Gibt (audio_base64_teile, done_gesehen) zurück.
    """
    parts: list[str] = []
    done = False
    buf = b""

    def consume(raw_line: bytes) -> None:
        nonlocal done
        text = raw_line.decode("utf-8", "replace").rstrip("\r")
        if is_done_line(text):
            done = True
            return
        chunk = audio_chunk_from_sse_line(text)
        if chunk:
            parts.append(chunk)

    async for data in resp.aiter_bytes():
        buf += data
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            consume(line)
    if buf:
        consume(buf)
    return parts, done


def save_bytes(raw: bytes, dest_dir: Path, ext: str) -> Path:
    """Schreibt raw bytes als <uuid>.<ext> in dest_dir (wird angelegt)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{uuid.uuid4().hex}.{ext.lstrip('.')}"
    path.write_bytes(raw)
    return path


def pcm16_to_wav(pcm: bytes, sample_rate: int = 24000, channels: int = 1) -> bytes:
    """Wrappt raw PCM16 (signed 16-bit LE) in einen WAV-Container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


def parse_pcm_content_type(content_type: str) -> tuple[int, int]:
    """Liest rate/channels aus `audio/pcm;rate=24000;channels=1`. Defaults 24000/1."""
    rate, channels = 24000, 1
    for part in (content_type or "").split(";"):
        part = part.strip()
        if part.startswith("rate=") and part[5:].isdigit():
            rate = int(part[5:])
        elif part.startswith("channels=") and part[9:].isdigit():
            channels = int(part[9:])
    return rate, channels
