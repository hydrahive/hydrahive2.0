"""Lokale Standardmodelle dürfen nicht durch den Cloud-Keypfad laufen."""
from unittest.mock import AsyncMock, patch

import pytest

from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(session_id="s", agent_id="a", user_id="u", workspace=tmp_path)


@pytest.mark.asyncio
async def test_image_local_default_skips_openrouter_key(ctx):
    from hydrahive.tools import generate_image

    with (
        patch("hydrahive.tools.generate_image.get_media_model", return_value="local:node/image"),
        patch("hydrahive.tools.generate_image._get_openrouter_key", side_effect=AssertionError),
        patch("hydrahive.tools.generate_image._execute_local", new=AsyncMock(return_value="ok")) as local,
    ):
        result = await generate_image._execute({"prompt": "cat"}, ctx)
    local.assert_awaited_once()
    assert result == "ok"


@pytest.mark.asyncio
async def test_video_local_default_skips_openrouter_key(ctx):
    from hydrahive.tools import generate_video

    with (
        patch("hydrahive.tools.generate_video.get_media_model", return_value="local:node/video"),
        patch("hydrahive.tools.generate_video.openrouter_key", side_effect=AssertionError),
        patch("hydrahive.tools.generate_video._execute_local", new=AsyncMock(return_value="ok")) as local,
    ):
        result = await generate_video._execute({"prompt": "cat"}, ctx)
    local.assert_awaited_once()
    assert result == "ok"
