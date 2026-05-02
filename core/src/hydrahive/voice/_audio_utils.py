"""ffmpeg/ffprobe helper functions for TTS audio processing."""
from __future__ import annotations

import asyncio
import logging
import math
import shutil
import struct
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


async def probe_seconds(path: Path) -> int:
    """Duration in seconds via ffprobe — rounded to int, at least 1."""
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
    except (OSError, asyncio.TimeoutError, ValueError):
        return 1


async def waveform_from_audio(path: Path) -> bytes:
    """64-byte waveform (RMS per bucket, 0-100) via ffmpeg PCM decode."""
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
            out[i] = min(100, int(rms / 327.67))
        return bytes(out)
    finally:
        pcm_path.unlink(missing_ok=True)
