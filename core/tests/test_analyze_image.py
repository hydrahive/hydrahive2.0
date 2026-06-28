"""#153 analyze_image Tool — Vision-Input."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hydrahive.tools.base import ToolContext

# 1×1 PNG Minimal-Datei (valides PNG, 67 Bytes)
import base64 as _b64
_TINY_PNG = _b64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(session_id="s1", agent_id="a1", user_id="u1", workspace=tmp_path)


@pytest.fixture
def image_file(tmp_path):
    p = tmp_path / "test.png"
    p.write_bytes(_TINY_PNG)
    return p


def _ok_response(text: str = "Das ist ein Testbild."):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": text}}]
    }
    return resp


# ---------------------------------------------------------------- Registry/Schema

def test_analyze_image_in_registry():
    from hydrahive.tools import REGISTRY
    assert "analyze_image" in REGISTRY


def test_analyze_image_schema_felder():
    from hydrahive.tools import REGISTRY
    schema = REGISTRY["analyze_image"].schema
    props = schema["properties"]
    assert {"image", "question", "model"} <= set(props)
    assert set(schema["required"]) == {"image", "question"}


# --------------------------------------------------------------- image_to_content_block
# Die Bild→content-block-Logik wurde nach hydrahive.tools._openrouter_media
# ausgelagert (geteilt von analyze_image + generate_image). Tests folgen dahin.

def test_http_url_wird_als_url_block_gebaut():
    from hydrahive.tools._openrouter_media import image_to_content_block
    block = image_to_content_block("https://example.com/foto.jpg")
    assert isinstance(block, dict)
    assert block["type"] == "image_url"
    assert block["image_url"]["url"] == "https://example.com/foto.jpg"


def test_lokaler_pfad_wird_base64(image_file):
    from hydrahive.tools._openrouter_media import image_to_content_block
    block = image_to_content_block(str(image_file))
    assert isinstance(block, dict)
    assert block["type"] == "image_url"
    assert block["image_url"]["url"].startswith("data:image/png;base64,")


def test_datei_nicht_gefunden_gibt_fehler_string(tmp_path):
    from hydrahive.tools._openrouter_media import image_to_content_block
    result = image_to_content_block(str(tmp_path / "ghost.png"))
    assert isinstance(result, str)
    assert "nicht gefunden" in result


def test_datei_zu_gross_gibt_fehler_string(tmp_path):
    from hydrahive.tools._openrouter_media import image_to_content_block, _MAX_IMAGE_BYTES
    big = tmp_path / "big.png"
    big.write_bytes(b"x" * (_MAX_IMAGE_BYTES + 1))
    result = image_to_content_block(str(big))
    assert isinstance(result, str)
    assert "zu groß" in result


# ---------------------------------------------------------------- _execute (E2E gemockt)

@pytest.mark.asyncio
async def test_execute_url_gibt_textantwort(ctx):
    from hydrahive.tools import analyze_image

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=_ok_response("Ein Hund läuft auf einer Wiese."))

    with (
        patch("hydrahive.tools.analyze_image.httpx.AsyncClient", return_value=mock_client),
        patch("hydrahive.tools.analyze_image.openrouter_key", return_value="sk-test"),
    ):
        result = await analyze_image._execute(
            {"image": "https://example.com/dog.jpg", "question": "Was ist auf dem Bild?"},
            ctx,
        )

    assert result.success
    assert "Hund" in result.output


@pytest.mark.asyncio
async def test_execute_lokaler_pfad(ctx, image_file):
    from hydrahive.tools import analyze_image

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=_ok_response("Ein kleines PNG."))

    with (
        patch("hydrahive.tools.analyze_image.httpx.AsyncClient", return_value=mock_client),
        patch("hydrahive.tools.analyze_image.openrouter_key", return_value="sk-test"),
    ):
        result = await analyze_image._execute(
            {"image": str(image_file), "question": "Beschreibe das Bild."},
            ctx,
        )

    assert result.success
    assert "PNG" in result.output


@pytest.mark.asyncio
async def test_execute_kein_key(ctx):
    from hydrahive.tools import analyze_image
    with patch("hydrahive.tools.analyze_image.openrouter_key", return_value=""):
        result = await analyze_image._execute(
            {"image": "https://x.test/a.jpg", "question": "Was?"},
            ctx,
        )
    assert not result.success
    assert "openrouter" in (result.error or result.output).lower()


@pytest.mark.asyncio
async def test_execute_leeres_image(ctx):
    from hydrahive.tools import analyze_image
    with patch("hydrahive.tools.analyze_image.openrouter_key", return_value="sk-test"):
        result = await analyze_image._execute({"image": "", "question": "Was?"}, ctx)
    assert not result.success


@pytest.mark.asyncio
async def test_execute_leere_frage(ctx, image_file):
    from hydrahive.tools import analyze_image
    with patch("hydrahive.tools.analyze_image.openrouter_key", return_value="sk-test"):
        result = await analyze_image._execute(
            {"image": str(image_file), "question": ""},
            ctx,
        )
    assert not result.success


@pytest.mark.asyncio
async def test_execute_api_fehler(ctx):
    import httpx
    from hydrahive.tools import analyze_image

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.HTTPError("Netzwerk weg"))

    with (
        patch("hydrahive.tools.analyze_image.httpx.AsyncClient", return_value=mock_client),
        patch("hydrahive.tools.analyze_image.openrouter_key", return_value="sk-test"),
    ):
        result = await analyze_image._execute(
            {"image": "https://x.test/a.jpg", "question": "Test"},
            ctx,
        )
    assert not result.success
    assert "Netzwerk" in (result.error or result.output)


@pytest.mark.asyncio
async def test_execute_kein_vision_modell_gibt_hilfreichen_fehler(ctx):
    from hydrahive.tools import analyze_image

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = '{"error": "vision not supported by this model"}'
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with (
        patch("hydrahive.tools.analyze_image.httpx.AsyncClient", return_value=mock_client),
        patch("hydrahive.tools.analyze_image.openrouter_key", return_value="sk-test"),
    ):
        result = await analyze_image._execute(
            {"image": "https://x.test/a.jpg", "question": "Test", "model": "some-text-only-model"},
            ctx,
        )
    assert not result.success
    assert "Vision" in (result.error or result.output) or "vision" in (result.error or result.output).lower()
