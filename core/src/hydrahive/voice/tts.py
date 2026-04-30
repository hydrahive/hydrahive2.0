"""Text-to-Speech via mmx-CLI (MiniMax).

`synthesize_to_ogg(text, voice)` ist die Public-API. Liefert OGG/Opus-Bytes
fertig für WhatsApp-Sprachnachrichten (push-to-talk Format).
mmx liefert MP3 — wir konvertieren danach via ffmpeg zu OGG/Opus.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def is_available() -> bool:
    return shutil.which("mmx") is not None and shutil.which("ffmpeg") is not None


async def synthesize_to_ogg(text: str, voice: str = "German_FriendlyMan") -> bytes:
    """Text → OGG/Opus-Bytes (für WhatsApp ptt). Wirft RuntimeError bei Fehler."""
    if not text.strip():
        raise RuntimeError("leerer Text")
    if shutil.which("mmx") is None:
        raise RuntimeError("mmx-CLI fehlt — npm install -g mmx-cli")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg fehlt")

    with tempfile.TemporaryDirectory() as tmp:
        mp3 = Path(tmp) / "out.mp3"
        ogg = Path(tmp) / "out.ogg"

        proc = await asyncio.create_subprocess_exec(
            "mmx", "speech", "synthesize",
            "--text", text, "--voice", voice,
            "--out", str(mp3), "--quiet",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, err = await asyncio.wait_for(proc.communicate(), timeout=60.0)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError("mmx-Timeout")
        if proc.returncode != 0 or not mp3.exists():
            raise RuntimeError(f"mmx fehlgeschlagen: {err.decode()[:200]}")

        # MP3 → OGG/Opus 16kHz mono — Standard für WhatsApp ptt
        proc2 = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(mp3),
            "-c:a", "libopus", "-ar", "16000", "-ac", "1",
            "-b:a", "32k", str(ogg),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(proc2.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            proc2.kill()
            raise RuntimeError("ffmpeg-Timeout bei MP3→OGG")
        if proc2.returncode != 0 or not ogg.exists():
            raise RuntimeError("ffmpeg-Konvertierung fehlgeschlagen")

        return ogg.read_bytes()
