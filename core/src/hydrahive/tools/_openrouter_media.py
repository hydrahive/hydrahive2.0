"""Geteilte Helfer für OpenRouter-Media-Tools (Bild, Musik, Audio …).

Key-Lookup + base64→Datei-Speicherung an EINER Stelle — kein Duplikat über die
einzelnen Tool-Module. Die Datei muss in einem servable-Verzeichnis landen
(Aufrufer übergibt ctx.workspace/… → von /api/files ausgeliefert).
"""
from __future__ import annotations

import io
import json
import logging
import uuid
import wave
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_AUDIO_SPEECH_URL = "https://openrouter.ai/api/v1/audio/speech"


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


async def synthesize_speech(
    text: str, voice: str, model: str, *, key: str
) -> tuple[bytes, str, str, str | None]:
    """Sprache über OpenRouter /audio/speech. Geteilt von generate_speech-Tool + Vorlese-TTS.

    Löst die Voice gegen die Modell-Voices auf (unbekannt → Modell-Default + note;
    leer → Default). `response_format:"pcm"` ist universell — die Sample-Rate steht
    im content-type-Header → WAV-Wrap. Liefert ein Modell mp3, wird es durchgereicht.

    Returns (data, ext, voice_used, note). Raises RuntimeError bei API-/Netzfehler
    oder wenn keine Voice ermittelbar ist.
    """
    from hydrahive.llm.media_models import voices_for

    voices = await voices_for(model)
    note: str | None = None
    requested = (voice or "").strip()
    if requested:
        if voices and requested not in voices:
            used = voices[0]
            note = f"Stimme '{requested}' gibt es bei {model} nicht — '{used}' verwendet"
        else:
            used = requested
    else:
        used = voices[0] if voices else ""
    if not used:
        raise RuntimeError(f"Keine Voice für '{model}' ermittelbar — voice angeben")

    payload = {"model": model, "input": text, "voice": used, "response_format": "pcm"}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                _AUDIO_SPEECH_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"OpenRouter API-Fehler {resp.status_code}: {resp.text[:400]}")
            raw = resp.content
            content_type = resp.headers.get("content-type", "")
    except httpx.HTTPError as e:
        raise RuntimeError(f"Netzwerk-Fehler: {e}") from e

    if not raw:
        raise RuntimeError("Keine Audio-Daten in OpenRouter-Antwort — bitte erneut versuchen")
    if "mpeg" in content_type or "mp3" in content_type:
        return raw, "mp3", used, note
    rate, channels = parse_pcm_content_type(content_type)
    return pcm16_to_wav(raw, sample_rate=rate, channels=channels), "wav", used, note
