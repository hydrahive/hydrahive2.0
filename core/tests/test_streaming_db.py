"""Atomare Statusübergänge für Streaming-Jobs."""
from __future__ import annotations

from hydrahive.db import init_db
from hydrahive.db import streaming as db
from hydrahive.settings import settings


def test_terminal_status_cannot_be_overwritten_by_done(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "streaming.db", raising=False)
    init_db()
    job = db.create_job(
        user_id="user-1",
        series_title="Serie",
        series_url="https://example.invalid/serie",
        season=1,
        episode=1,
        episode_key="episode-1",
        bunny_video_id="video-1",
        bunny_library_id="library-1",
        output_path=str(tmp_path / "episode.mkv"),
    )

    assert db.update_job_status(
        job["id"], "downloading", expected_statuses=("pending",)
    )
    assert db.update_job_status(
        job["id"],
        "error",
        error="Abgebrochen",
        expected_statuses=("pending", "downloading"),
    )
    assert not db.update_job_status(
        job["id"], "done", progress=100, expected_statuses=("downloading",)
    )
    assert db.get_job(job["id"])["status"] == "error"
