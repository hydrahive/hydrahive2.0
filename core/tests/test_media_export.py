import shutil
import subprocess

import pytest

from hydrahive import media_assets, media_export, media_projects, media_workspace
from hydrahive.projects import config as project_config
from hydrahive.projects._paths import workspace_path


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg fehlt")
def test_export_renders_video_and_audio(tmp_path):
    project = project_config.create(name="Export", members=["testuser"], llm_model="test", created_by="admin")
    media_projects.create(project["id"], "film", "Film")
    root = workspace_path(project["id"])
    video = root / "source.mp4"
    audio = root / "music.wav"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=160x90:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)], check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(audio)], check=True, capture_output=True)
    media_assets.create(project["id"], "film", "video", "video", project["id"], "source.mp4", "Video")
    media_assets.create(project["id"], "film", "music", "audio", project["id"], "music.wav", "Music")
    media_workspace.save_timeline(project["id"], "film", {"fps": 25, "width": 160, "height": 90, "tracks": [{"id": "v", "name": "Video", "kind": "video", "muted": False, "clips": [{"id": "vc", "asset_id": "video", "start": 0, "duration": 1, "source_in": 0, "volume": 1}]}, {"id": "a", "name": "Audio", "kind": "music", "muted": False, "clips": [{"id": "ac", "asset_id": "music", "start": 0, "duration": 1, "source_in": 0, "volume": 1}]}]})
    result = media_export.export(project["id"], "film")
    assert result["status"] == "completed"
    assert (workspace_path(project["id"]) / "media" / "film" / result["rel_path"]).stat().st_size > 1000


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg fehlt")
def test_export_assembles_along_cut_points(tmp_path):
    project = project_config.create(name="ExportCut", members=["testuser"], llm_model="test", created_by="admin")
    media_projects.create(project["id"], "film", "Film")
    root = workspace_path(project["id"])
    v1 = root / "a.mp4"
    v2 = root / "b.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=160x90:d=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(v1)], check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=green:s=160x90:d=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(v2)], check=True, capture_output=True)
    media_assets.create(project["id"], "film", "va", "video", project["id"], "a.mp4", "A")
    media_assets.create(project["id"], "film", "vb", "video", project["id"], "b.mp4", "B")
    media_workspace.save_timeline(project["id"], "film", {
        "fps": 25, "width": 160, "height": 90,
        "tracks": [
            {"id": "vid1", "name": "V1", "kind": "video", "muted": False, "clips": [{"id": "ca", "asset_id": "va", "start": 0, "duration": 4, "source_in": 0, "volume": 1}]},
            {"id": "vid2", "name": "V2", "kind": "video", "muted": False, "clips": [{"id": "cb", "asset_id": "vb", "start": 0, "duration": 4, "source_in": 0, "volume": 1}]},
        ],
        "cut_points": [{"id": "cut1", "time": 2, "effect": "cut", "duration": 0}],
    })
    result = media_export.export(project["id"], "film")
    assert result["status"] == "completed"
    assert (workspace_path(project["id"]) / "media" / "film" / result["rel_path"]).stat().st_size > 1000


def _sample_center(video_path, t):
    """RGB-Pixel in der Bildmitte zum Zeitpunkt t (via ffmpeg + PIL)."""
    import tempfile
    from pathlib import Path

    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        frame = Path(tmp) / "f.png"
        subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", str(video_path), "-frames:v", "1", str(frame)], check=True, capture_output=True)
        im = Image.open(frame).convert("RGB")
        return im.getpixel((im.size[0] // 2, im.size[1] // 2))


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg fehlt")
def test_export_crossfade_blends_midpoint(tmp_path):
    project = project_config.create(name="ExportXf", members=["testuser"], llm_model="test", created_by="admin")
    media_projects.create(project["id"], "film", "Film")
    root = workspace_path(project["id"])
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=160x90:d=8", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(root / "a.mp4")], check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=green:s=160x90:d=8", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(root / "b.mp4")], check=True, capture_output=True)
    media_assets.create(project["id"], "film", "va", "video", project["id"], "a.mp4", "A")
    media_assets.create(project["id"], "film", "vb", "video", project["id"], "b.mp4", "B")
    media_workspace.save_timeline(project["id"], "film", {
        "fps": 25, "width": 160, "height": 90,
        "tracks": [
            {"id": "vid1", "name": "V1", "kind": "video", "muted": False, "clips": [{"id": "ca", "asset_id": "va", "start": 0, "duration": 8, "source_in": 0, "volume": 1}]},
            {"id": "vid2", "name": "V2", "kind": "video", "muted": False, "clips": [{"id": "cb", "asset_id": "vb", "start": 0, "duration": 8, "source_in": 0, "volume": 1}]},
        ],
        "cut_points": [{"id": "cut1", "time": 4, "effect": "crossfade", "duration": 2}],
    })
    result = media_export.export(project["id"], "film")
    out = workspace_path(project["id"]) / "media" / "film" / result["rel_path"]
    r1, g1, b1 = _sample_center(out, 1)   # vor Übergang → rot
    rm, gm, bm = _sample_center(out, 4)   # Mitte Übergang → Mischung
    r3, g3, b3 = _sample_center(out, 7)   # nach Übergang → grün
    assert r1 > 150 and g1 < 80           # rot
    assert r3 < 80 and g3 > 80            # grün
    assert rm > 30 and gm > 30           # beide Kanäle präsent → Überblendung


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg fehlt")
def test_export_rejects_missing_asset():
    project = project_config.create(name="Missing", members=["testuser"], llm_model="test", created_by="admin")
    media_projects.create(project["id"], "film", "Film")
    media_workspace.save_timeline(project["id"], "film", {"tracks": [{"id": "v", "kind": "video", "clips": [{"id": "c", "asset_id": "missing", "start": 0, "duration": 1}]}]})
    with pytest.raises(media_export.MediaExportError, match="Assets fehlen"):
        media_export.export(project["id"], "film")
