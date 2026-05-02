"""Text-to-Speech via mmx-CLI (MiniMax).

Public API:
- `synthesize_mp3(text, voice)` — rohes MP3 wie mmx liefert (für Web-TTS)
- `synthesize_to_ogg(text, voice)` — VoiceClip mit OGG/Opus + Sekunden +
  Waveform für WhatsApp-Voice-Notes
- `list_voices(language)` — verfügbare Stimmen vom mmx CLI

`voice/tts.py` ist die einzige Stelle die `mmx` als Subprocess startet —
api/routes/tts.py ist nur ein dünner HTTP-Wrapper.
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from hydrahive.voice._audio_utils import probe_seconds, waveform_from_audio

logger = logging.getLogger(__name__)


@dataclass
class VoiceClip:
    ogg_bytes: bytes
    seconds: int             # gerundet, ≥1
    waveform: bytes          # 64 Bytes, jeweils 0-100


def is_available() -> bool:
    return shutil.which("mmx") is not None and shutil.which("ffmpeg") is not None


def _mmx_key() -> str:
    """MiniMax-API-Key aus llm.json — einzige Key-Quelle."""
    try:
        from hydrahive.llm import client as llm_client
        cfg = llm_client._load_config()
        return llm_client._get_minimax_key(cfg)
    except Exception as e:
        logger.debug("MiniMax-Key aus llm.json nicht lesbar: %s", e)
    return ""


async def synthesize_mp3(text: str, voice: str = "German_FriendlyMan") -> bytes:
    """Roh-MP3-Bytes von mmx — für /api/tts ohne weitere Konvertierung."""
    if not text.strip():
        raise RuntimeError("leerer Text")
    if shutil.which("mmx") is None:
        raise RuntimeError("mmx-CLI fehlt — npm install -g mmx-cli")
    key = _mmx_key()
    if not key:
        raise RuntimeError("MiniMax-API-Key fehlt — Provider 'minimax' in der LLM-Config setzen")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.mp3"
        proc = await asyncio.create_subprocess_exec(
            "mmx", "speech", "synthesize",
            "--api-key", key,
            "--text", text, "--voice", voice,
            "--out", str(out), "--quiet",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, err = await asyncio.wait_for(proc.communicate(), timeout=60.0)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError("mmx-Timeout")
        if proc.returncode != 0 or not out.exists():
            raise RuntimeError(f"mmx fehlgeschlagen: {err.decode(errors='replace')[:200]}")
        return out.read_bytes()


async def list_voices(language: str = "german") -> list[dict]:
    """Verfügbare Voices vom mmx-CLI als JSON-Liste."""
    if shutil.which("mmx") is None:
        raise RuntimeError("mmx-CLI fehlt")
    key = _mmx_key()
    if not key:
        raise RuntimeError("MiniMax-API-Key fehlt")
    proc = await asyncio.create_subprocess_exec(
        "mmx", "speech", "voices",
        "--api-key", key,
        "--language", language, "--output", "json", "--quiet",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=15.0)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError("mmx Voices-Abruf Timeout")
    if proc.returncode != 0:
        raise RuntimeError(f"mmx voices fehlgeschlagen: {err.decode(errors='replace')[:200]}")
    try:
        return json.loads(out.decode())
    except json.JSONDecodeError:
        return []


async def synthesize_to_ogg(text: str, voice: str = "German_FriendlyMan") -> VoiceClip:
    """Text → VoiceClip(ogg_bytes, seconds, waveform) für WhatsApp-Voice-Notes."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg fehlt")
    mp3_bytes = await synthesize_mp3(text, voice)

    with tempfile.TemporaryDirectory() as tmp:
        mp3 = Path(tmp) / "out.mp3"
        ogg = Path(tmp) / "out.ogg"
        mp3.write_bytes(mp3_bytes)

        # MP3 → OGG/Opus 16kHz mono — Standard für WhatsApp ptt
        proc2 = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(mp3),
            "-c:a", "libopus", "-ar", "16000", "-ac", "1",
            "-b:a", "32k", str(ogg),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, err2 = await asyncio.wait_for(proc2.communicate(), timeout=30.0)
        except asyncio.TimeoutError:
            proc2.kill()
            raise RuntimeError("ffmpeg-Timeout bei MP3→OGG")
        if proc2.returncode != 0 or not ogg.exists():
            tail = err2.decode(errors="replace")[-500:] if err2 else ""
            logger.warning("ffmpeg MP3→OGG fehlgeschlagen: %s", tail)
            raise RuntimeError(f"ffmpeg-Konvertierung fehlgeschlagen: {tail[:200]}")

        ogg_bytes = ogg.read_bytes()
        seconds = await probe_seconds(ogg)
        waveform = await waveform_from_audio(ogg)
        return VoiceClip(ogg_bytes=ogg_bytes, seconds=seconds, waveform=waveform)


