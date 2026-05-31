"""#147 generate_image Tool.

Smoke-Tests mit gemocktem OpenRouter-Response.
Echter API-Call = Till testet im Browser nach Deploy.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hydrahive.tools.base import ToolContext, ToolResult


@pytest.fixture
def ctx():
    return ToolContext(
        session_id="s1", agent_id="a1", user_id="u1",
        workspace=Path("/tmp"),
    )


def _fake_openrouter_response(image_url: str):
    """Minimal OpenRouter chat/completions Response mit Bild-URL."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "choices": [{
            "message": {
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        }]
    }
    return resp


def test_generate_image_in_registry():
    from hydrahive.tools import REGISTRY
    assert "generate_image" in REGISTRY


def test_generate_image_schema_felder():
    from hydrahive.tools import REGISTRY
    schema = REGISTRY["generate_image"].schema
    props = schema["properties"]
    assert "prompt" in props
    assert "model" in props
    assert "width" in props
    assert "height" in props
    assert schema["required"] == ["prompt"]


@pytest.mark.asyncio
async def test_generate_image_gibt_image_url_zurueck(ctx):
    from hydrahive.tools.generate_image import _execute

    fake_url = "https://cdn.openrouter.ai/generated/abc123.png"

    mock_resp = _fake_openrouter_response(fake_url)
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with (
        patch("hydrahive.tools.generate_image.httpx.AsyncClient", return_value=mock_client),
        patch("hydrahive.tools.generate_image._get_openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await _execute({"prompt": "ein roter Würfel"}, ctx)

    assert result.success
    assert result.result_type == "image_url"
    assert result.output == fake_url


@pytest.mark.asyncio
async def test_generate_image_kein_key_gibt_fehler(ctx):
    from hydrahive.tools.generate_image import _execute

    with patch("hydrahive.tools.generate_image._get_openrouter_key", return_value=""):
        result = await _execute({"prompt": "test"}, ctx)

    assert not result.success
    assert "openrouter" in result.error.lower()


@pytest.mark.asyncio
async def test_generate_image_api_fehler_gibt_fehler(ctx):
    import httpx
    from hydrahive.tools.generate_image import _execute

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.HTTPError("500"))

    with (
        patch("hydrahive.tools.generate_image.httpx.AsyncClient", return_value=mock_client),
        patch("hydrahive.tools.generate_image._get_openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await _execute({"prompt": "test"}, ctx)

    assert not result.success


@pytest.mark.asyncio
async def test_generate_image_leere_prompt_fehler(ctx):
    from hydrahive.tools.generate_image import _execute

    with patch("hydrahive.tools.generate_image._get_openrouter_key", return_value="sk-or-v1-test"):
        result = await _execute({"prompt": ""}, ctx)

    assert not result.success
