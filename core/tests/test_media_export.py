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
def test_export_rejects_missing_asset():
    project = project_config.create(name="Missing", members=["testuser"], llm_model="test", created_by="admin")
    media_projects.create(project["id"], "film", "Film")
    media_workspace.save_timeline(project["id"], "film", {"tracks": [{"id": "v", "kind": "video", "clips": [{"id": "c", "asset_id": "missing", "start": 0, "duration": 1}]}]})
    with pytest.raises(media_export.MediaExportError, match="Assets fehlen"):
        media_export.export(project["id"], "film")
