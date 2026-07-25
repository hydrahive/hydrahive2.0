"""ffmpeg-Konvertierung: ComfyUI-Video-Outputs (animiertes WebP) → MP4.

ComfyUI-Video-Workflows liefern typischerweise ein animiertes WebP
(SaveAnimatedWEBP) — für die Galerie/Timeline brauchen wir MP4 (H.264/AAC).
Sichere Argument-Liste ohne Shell (kein Injection-Risiko), wie in media_export.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def to_mp4(inputs: list[Path], dest_dir: Path) -> Path:
    """Konvertiert die ComfyUI-Outputs zu einer MP4-Datei in dest_dir.

    - Ein animiertes WebP (häufigster Fall) → direkte Transkodierung.
    - Mehrere Einzel-Frames (png/webp) → als Sequenz zu Video (24fps).
    Raises RuntimeError, wenn ffmpeg fehlt oder die Konvertierung scheitert.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg nicht installiert — Video-Konvertierung nicht möglich")
    if not inputs:
        raise RuntimeError("Keine Eingabedateien für ffmpeg-Konvertierung")

    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"{uuid.uuid4().hex}.mp4"

    if len(inputs) == 1:
        # animiertes WebP (oder einzelnes Video) direkt transkodieren
        args = [
            "ffmpeg", "-y",
            "-i", str(inputs[0]),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out),
        ]
    else:
        # Frame-Sequenz: nach Namen sortiert als 24fps-Video
        # (ffmpeg concat via image2 pattern ist heikel bei uneinheitlichen Namen,
        # deshalb via concat-demuxer über eine Liste)
        listfile = dest_dir / f"{uuid.uuid4().hex}.txt"
        listfile.write_text("".join(f"file '{p.name}'\n" for p in sorted(inputs, key=lambda x: x.name)))
        args = [
            "ffmpeg", "-y", "-r", "24",
            "-f", "concat", "-safe", "0", "-i", str(listfile),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out),
        ]

    try:
        res = subprocess.run(args, capture_output=True, timeout=300, cwd=str(dest_dir))
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("ffmpeg-Konvertierung Timeout (>300s)") from e
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg-Fehler: {res.stderr.decode('utf-8', 'replace')[:400]}")
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError("ffmpeg lieferte keine gültige MP4-Datei")
    logger.info("ComfyUI-Output → MP4: %s (%d bytes)", out, out.stat().st_size)
    return out
