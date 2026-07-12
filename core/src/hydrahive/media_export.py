from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from hydrahive import media_assets, media_projects, media_timeline_assembly, media_workspace

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


def _has_audio_stream(path: Path) -> bool:
    """Prüft via ffprobe, ob die Datei eine Audiospur hat (für Video-O-Ton)."""
    if shutil.which("ffprobe") is None:
        return False
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "json", str(path)],
            capture_output=True, timeout=30, check=False,
        )
        if result.returncode != 0:
            return False
        return bool(json.loads(result.stdout or "{}").get("streams"))
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return False


def _enable_expr(segments: list[tuple[float, float]]) -> str:
    """FFmpeg-overlay enable-Ausdruck aus der Vereinigung der on-air-Intervalle."""
    return "+".join(f"between(t,{a},{b})" for a, b in segments)


def export(project_id: str, media_slug: str) -> dict:
    if shutil.which("ffmpeg") is None:
        raise MediaExportError("ffmpeg fehlt")
    timeline = media_workspace.timeline(project_id, media_slug)
    assets = _asset_paths(project_id, media_slug)

    # WYSIWYG-Assemblierung: welcher Video-Clip ist wann sichtbar (entlang Schnittpunkte).
    onair = media_timeline_assembly.video_onair_segments(timeline)

    # Clip-Metadaten je ID (aus den Video-Spuren).
    video_clips: dict[str, dict] = {}
    for track in timeline["tracks"]:
        if track.get("kind") == "video" and not track.get("muted"):
            for clip in track["clips"]:
                video_clips[clip["id"]] = clip

    # Audio-Clips (music/fx/voice) wie bisher.
    audio_clips = [
        (track, clip)
        for track in timeline["tracks"]
        if track.get("kind") != "video" and not track.get("muted")
        for clip in track["clips"]
    ]

    # Fehlende Assets prüfen (nur was tatsächlich gerendert wird).
    missing = {video_clips[cid]["asset_id"] for cid in onair if video_clips[cid]["asset_id"] not in assets}
    missing |= {clip["asset_id"] for _, clip in audio_clips if clip["asset_id"] not in assets}
    if missing:
        raise MediaExportError(f"Assets fehlen: {', '.join(sorted(missing))}")
    if not onair and not audio_clips:
        raise MediaExportError("Timeline ist leer")

    duration = _timeline_duration(timeline)
    root = media_projects._dir(project_id, media_slug)
    output = root / "exports" / "timeline.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)

    args = ["ffmpeg", "-y", "-f", "lavfi", "-i",
            f"color=c=black:s={timeline['width']}x{timeline['height']}:r={timeline['fps']}:d={duration}"]

    # Inputs sammeln (Video-Clips mit on-air-Segmenten + Audio-Clips).
    inputs: list[tuple[str, dict, Path, list[tuple[float, float]] | None]] = []
    for clip_id, segments in onair.items():
        clip = video_clips[clip_id]
        path = assets[clip["asset_id"]]
        if path.suffix.lower() not in VIDEO_EXTS:
            continue
        args.extend(["-i", str(path)])
        inputs.append(("video", clip, path, segments))
    for track, clip in audio_clips:
        path = assets[clip["asset_id"]]
        if path.suffix.lower() not in AUDIO_EXTS | VIDEO_EXTS:
            continue
        args.extend(["-i", str(path)])
        inputs.append(("audio", clip, path, None))

    filters = ["[0:v]setpts=PTS-STARTPTS[base0]"]
    base = "base0"
    audio_labels: list[str] = []
    idx = 0
    w, h = timeline["width"], timeline["height"]
    for kind, clip, path, segments in inputs:
        idx += 1
        start, length, source_in = clip["start"], clip["duration"], clip.get("source_in", 0)
        if kind == "video":
            assert segments is not None
            vlabel = f"v{idx}"
            out = f"base{idx}"
            filters.append(
                f"[{idx}:v]trim=start={source_in}:duration={length},setpts=PTS-STARTPTS+{start}/TB,"
                f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[{vlabel}]"
            )
            filters.append(f"[{base}][{vlabel}]overlay=enable='{_enable_expr(segments)}'[{out}]")
            base = out
            # Video-O-Ton nur für die on-air-Segmente (falls Audiospur vorhanden).
            if _has_audio_stream(path):
                alabel = f"a{idx}"
                delay = round(start * 1000)
                vol = clip.get("volume", 1)
                filters.append(
                    f"[{idx}:a]atrim=start={source_in}:duration={length},asetpts=PTS-STARTPTS,"
                    f"adelay={delay}|{delay},volume={vol}[{alabel}]"
                )
                audio_labels.append(alabel)
        else:
            alabel = f"a{idx}"
            delay = round(start * 1000)
            vol = clip.get("volume", 1)
            filters.append(
                f"[{idx}:a]atrim=start={source_in}:duration={length},asetpts=PTS-STARTPTS,"
                f"adelay={delay}|{delay},volume={vol}[{alabel}]"
            )
            audio_labels.append(alabel)

    if audio_labels:
        filters.append("".join(f"[{a}]" for a in audio_labels) + f"amix=inputs={len(audio_labels)}:duration=longest[aout]")

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


def _timeline_duration(timeline: dict) -> float:
    end = 0.0
    for track in timeline.get("tracks", []):
        if track.get("muted"):
            continue
        for clip in track.get("clips", []):
            end = max(end, clip["start"] + clip["duration"])
    return end
