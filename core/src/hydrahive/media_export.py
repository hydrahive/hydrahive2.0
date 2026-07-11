from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from hydrahive import media_assets, media_projects, media_workspace

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"}


class MediaExportError(ValueError):
    pass


def _asset_paths(project_id: str, media_slug: str) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for item in media_assets.list_all(project_id, media_slug):
        if not item["available"]:
            continue
        paths[item["id"]] = media_assets._source(item["source_project_id"], item["rel_path"])
    return paths


def export(project_id: str, media_slug: str) -> dict:
    if shutil.which("ffmpeg") is None:
        raise MediaExportError("ffmpeg fehlt")
    timeline = media_workspace.timeline(project_id, media_slug)
    assets = _asset_paths(project_id, media_slug)
    clips = [(track, clip, assets.get(clip["asset_id"])) for track in timeline["tracks"] if not track.get("muted") for clip in track["clips"]]
    missing = sorted({clip["asset_id"] for _, clip, path in clips if path is None})
    if missing:
        raise MediaExportError(f"Assets fehlen: {', '.join(missing)}")
    if not clips:
        raise MediaExportError("Timeline ist leer")
    duration = max(clip["start"] + clip["duration"] for _, clip, _ in clips)
    root = media_projects._dir(project_id, media_slug)
    output = root / "exports" / "timeline.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)

    args = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={timeline['width']}x{timeline['height']}:r={timeline['fps']}:d={duration}"]
    valid: list[tuple[dict, dict, Path, int]] = []
    for track, clip, path in clips:
        assert path is not None
        suffix = path.suffix.lower()
        if track["kind"] == "video" and suffix not in VIDEO_EXTS:
            continue
        if track["kind"] != "video" and suffix not in AUDIO_EXTS | VIDEO_EXTS:
            continue
        args.extend(["-i", str(path)])
        valid.append((track, clip, path, len(valid) + 1))

    filters = ["[0:v]setpts=PTS-STARTPTS[base0]"]
    base = "base0"
    audio_labels: list[str] = []
    for track, clip, _, index in valid:
        start, length, source_in = clip["start"], clip["duration"], clip.get("source_in", 0)
        if track["kind"] == "video":
            label = f"v{index}"
            out = f"base{index}"
            filters.append(f"[{index}:v]trim=start={source_in}:duration={length},setpts=PTS-STARTPTS+{start}/TB,scale={timeline['width']}:{timeline['height']}:force_original_aspect_ratio=decrease,pad={timeline['width']}:{timeline['height']}:(ow-iw)/2:(oh-ih)/2[{label}]")
            filters.append(f"[{base}][{label}]overlay=enable='between(t,{start},{start + length})'[{out}]")
            base = out
        else:
            label = f"a{index}"
            delay = round(start * 1000)
            volume = clip.get("volume", 1)
            filters.append(f"[{index}:a]atrim=start={source_in}:duration={length},asetpts=PTS-STARTPTS,adelay={delay}|{delay},volume={volume}[{label}]")
            audio_labels.append(label)
    if audio_labels:
        filters.append("".join(f"[{label}]" for label in audio_labels) + f"amix=inputs={len(audio_labels)}:duration=longest[aout]")
    args.extend(["-filter_complex", ";".join(filters), "-map", f"[{base}]"])
    if audio_labels:
        args.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"])
    args.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(duration), "-movflags", "+faststart", str(output)])
    try:
        result = subprocess.run(args, capture_output=True, timeout=1800, check=False)
    except subprocess.TimeoutExpired as exc:
        raise MediaExportError("FFmpeg-Export Timeout") from exc
    if result.returncode != 0 or not output.is_file():
        error = result.stderr.decode(errors="replace")[-500:]
        raise MediaExportError(f"FFmpeg-Export fehlgeschlagen: {error}")
    return {"status": "completed", "rel_path": str(output.relative_to(root)), "path": str(output), "duration": duration}
