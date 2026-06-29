"""#149 generate_video Tool + #148 Async Job Layer.

Alles gemockt — kein echter OpenRouter-Call in Unit-Tests.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(
        session_id="s1", agent_id="a1", user_id="u1",
        workspace=tmp_path,
    )


# ---------------------------------------------------------------- Registry/Schema

def test_generate_video_in_registry():
    from hydrahive.tools import REGISTRY
    assert "generate_video" in REGISTRY


def test_generate_video_schema_felder():
    from hydrahive.tools import REGISTRY
    schema = REGISTRY["generate_video"].schema
    props = schema["properties"]
    assert {"prompt", "model", "width", "height", "duration", "aspect_ratio"} <= set(props)
    assert schema["required"] == ["prompt"]


# ---------------------------------------------------------------- _openrouter_video Helfer

@pytest.mark.asyncio
async def test_submit_video_job_gibt_job_id():
    from hydrahive.tools._openrouter_video import submit_video_job

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "job-abc-123"}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("hydrahive.tools._openrouter_video.httpx.AsyncClient", return_value=mock_client):
        job_id = await submit_video_job("a dog running", "kling/v2", key="sk-test")

    assert job_id == "job-abc-123"


@pytest.mark.asyncio
async def test_submit_video_job_startframe_als_frame_images():
    """Startbild MUSS als frame_images/first_frame gehen — flaches image_url
    ignoriert die API (→ Text-to-Video, Bild verworfen)."""
    from hydrahive.tools._openrouter_video import submit_video_job

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "job-x"}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("hydrahive.tools._openrouter_video.httpx.AsyncClient", return_value=mock_client):
        await submit_video_job(
            "zoom in", "minimax/hailuo-2.3", key="sk-test",
            image_url="data:image/png;base64,AAAA",
        )

    payload = mock_client.post.call_args.kwargs["json"]
    assert "image_url" not in payload  # NICHT flach
    assert payload["frame_images"][0]["frame_type"] == "first_frame"
    assert payload["frame_images"][0]["image_url"]["url"] == "data:image/png;base64,AAAA"


@pytest.mark.asyncio
async def test_submit_video_job_api_fehler():
    from hydrahive.tools._openrouter_video import submit_video_job

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "bad request"
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("hydrahive.tools._openrouter_video.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="400"):
            await submit_video_job("test", "model", key="sk-test")


@pytest.mark.asyncio
async def test_poll_video_job_completed():
    from hydrahive.tools._openrouter_video import poll_video_job

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    # Echtes OpenRouter-Format: unsigned_urls (Doku: openrouter.ai/.../create-videos)
    mock_resp.json.return_value = {
        "id": "job-123",
        "status": "completed",
        "unsigned_urls": ["https://cdn.test/video.mp4"],
        "usage": {"cost": 0.1, "is_byok": False},
    }
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("hydrahive.tools._openrouter_video.httpx.AsyncClient", return_value=mock_client):
        result = await poll_video_job("job-123", key="sk-test")

    assert result["status"] == "completed"
    assert result["url"] == "https://cdn.test/video.mp4"


@pytest.mark.asyncio
async def test_poll_video_job_failed():
    from hydrahive.tools._openrouter_video import poll_video_job

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "failed", "error": "out of quota"}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("hydrahive.tools._openrouter_video.httpx.AsyncClient", return_value=mock_client):
        result = await poll_video_job("job-123", key="sk-test")

    assert result["status"] == "failed"
    assert "quota" in result["error"]


# ---------------------------------------------------------------- _execute (E2E gemockt)

@pytest.mark.asyncio
async def test_execute_completed_speichert_datei(ctx, tmp_path):
    from hydrahive.tools import generate_video

    with (
        patch("hydrahive.tools.generate_video.openrouter_key", return_value="sk-test"),
        patch("hydrahive.tools.generate_video.submit_video_job", new_callable=AsyncMock, return_value="job-1"),
        patch("hydrahive.tools.generate_video.poll_video_job", new_callable=AsyncMock,
              return_value={"status": "completed", "url": "https://cdn.test/v.mp4", "error": None}),
        patch("hydrahive.tools.generate_video.download_video", new_callable=AsyncMock,
              return_value=tmp_path / "generated" / "abc.mp4"),
        patch("hydrahive.tools.generate_video.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await generate_video._execute({"prompt": "ein Sonnenuntergang"}, ctx)

    assert result.success
    assert "abc.mp4" in str(result.output)


@pytest.mark.asyncio
async def test_execute_job_failed_gibt_fehler(ctx):
    from hydrahive.tools import generate_video

    with (
        patch("hydrahive.tools.generate_video.openrouter_key", return_value="sk-test"),
        patch("hydrahive.tools.generate_video.submit_video_job", new_callable=AsyncMock, return_value="job-1"),
        patch("hydrahive.tools.generate_video.poll_video_job", new_callable=AsyncMock,
              return_value={"status": "failed", "url": None, "error": "Modell nicht verfügbar"}),
        patch("hydrahive.tools.generate_video.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await generate_video._execute({"prompt": "test"}, ctx)

    assert not result.success
    assert "Modell nicht verfügbar" in (result.error or result.output)


@pytest.mark.asyncio
async def test_execute_timeout(ctx):
    """Poll läuft bis _POLL_TIMEOUT — dann Timeout-Fehler."""
    from hydrahive.tools import generate_video

    # Immer "processing" zurückgeben → Timeout
    with (
        patch("hydrahive.tools.generate_video.openrouter_key", return_value="sk-test"),
        patch("hydrahive.tools.generate_video.submit_video_job", new_callable=AsyncMock, return_value="job-1"),
        patch("hydrahive.tools.generate_video.poll_video_job", new_callable=AsyncMock,
              return_value={"status": "processing", "url": None, "error": None}),
        patch("hydrahive.tools.generate_video.asyncio.sleep", new_callable=AsyncMock),
        patch("hydrahive.tools.generate_video._POLL_TIMEOUT", 0.001),  # sofort Timeout
    ):
        result = await generate_video._execute({"prompt": "test"}, ctx)

    assert not result.success
    assert "Timeout" in (result.error or result.output)


@pytest.mark.asyncio
async def test_execute_kein_key(ctx):
    from hydrahive.tools import generate_video
    with patch("hydrahive.tools.generate_video.openrouter_key", return_value=""):
        result = await generate_video._execute({"prompt": "test"}, ctx)
    assert not result.success
    assert "openrouter" in (result.error or result.output).lower()


@pytest.mark.asyncio
async def test_execute_leerer_prompt(ctx):
    from hydrahive.tools import generate_video
    with patch("hydrahive.tools.generate_video.openrouter_key", return_value="sk-test"):
        result = await generate_video._execute({"prompt": ""}, ctx)
    assert not result.success
