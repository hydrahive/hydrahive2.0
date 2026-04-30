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
import math
import shutil
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class VoiceClip:
    ogg_bytes: bytes
    seconds: int             # gerundet, ≥1
    waveform: bytes          # 64 Bytes, jeweils 0-100


def is_available() -> bool:
    return shutil.which("mmx") is not None and shutil.which("ffmpeg") is not None


async def synthesize_mp3(text: str, voice: str = "German_FriendlyMan") -> bytes:
    """Roh-MP3-Bytes von mmx — für /api/tts ohne weitere Konvertierung."""
    if not text.strip():
        raise RuntimeError("leerer Text")
    if shutil.which("mmx") is None:
        raise RuntimeError("mmx-CLI fehlt — npm install -g mmx-cli")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.mp3"
        proc = await asyncio.create_subprocess_exec(
            "mmx", "speech", "synthesize",
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
    proc = await asyncio.create_subprocess_exec(
        "mmx", "speech", "voices",
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
        seconds = await _probe_seconds(ogg)
        waveform = await _waveform_from_audio(ogg)
        return VoiceClip(ogg_bytes=ogg_bytes, seconds=seconds, waveform=waveform)


async def _probe_seconds(path: Path) -> int:
    """Dauer in Sekunden via ffprobe — gerundet auf int, mindestens 1."""
    if shutil.which("ffprobe") is None:
        return 1
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        return max(1, round(float(out.decode().strip())))
    except Exception:
        return 1


async def _waveform_from_audio(path: Path) -> bytes:
    """64 Bytes Waveform (RMS pro Bucket, 0-100). Nutzt PCM-Decode via ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as tmp:
        pcm_path = Path(tmp.name)
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(path),
            "-ar", "8000", "-ac", "1", "-f", "s16le", str(pcm_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, err = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        if proc.returncode != 0:
            logger.debug("waveform-ffmpeg fehlgeschlagen: %s",
                         err.decode(errors="replace")[-500:])
            return bytes(64)
        raw = pcm_path.read_bytes()
        if not raw:
            return bytes(64)
        sample_count = len(raw) // 2
        samples = struct.unpack(f"<{sample_count}h", raw[:sample_count * 2])
        bucket = max(1, sample_count // 64)
        out = bytearray(64)
        for i in range(64):
            seg = samples[i * bucket: (i + 1) * bucket] if i < 63 else samples[i * bucket:]
            if not seg:
                continue
            rms = math.sqrt(sum(s * s for s in seg) / len(seg))
            out[i] = min(100, int(rms / 327.67))   # 32767 / 100
        return bytes(out)
    finally:
        pcm_path.unlink(missing_ok=True)
