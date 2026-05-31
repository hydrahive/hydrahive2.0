"""#147 generate_image Tool.

Echtes OpenRouter-Format (live verifiziert 2026-05-31):
  message.images[].image_url.url = data:image/png;base64,...  (~3 MB!)
Die data-URI wird NIE ins LLM gegeben — Bild wird lokal gespeichert,
nur der Pfad geht zurück.
"""
from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx():
    return ToolContext(
        session_id="s1", agent_id="a1", user_id="u1",
        workspace=Path("/tmp"),
    )


# 1x1 PNG, base64
_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
_DATA_URI = f"data:image/png;base64,{_PNG_B64}"


def _fake_response_images(url: str):
    """OpenRouter chat/completions Response mit Bild in message.images."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "images": [{"type": "image_url", "image_url": {"url": url}}],
            }
        }]
    }
    return resp


# ---------------------------------------------------------------- Registry/Schema

def test_generate_image_in_registry():
    from hydrahive.tools import REGISTRY
    assert "generate_image" in REGISTRY


def test_generate_image_schema_felder():
    from hydrahive.tools import REGISTRY
    schema = REGISTRY["generate_image"].schema
    props = schema["properties"]
    assert {"prompt", "model", "width", "height"} <= set(props)
    assert schema["required"] == ["prompt"]


# ---------------------------------------------------------------- Extraktion

def test_extract_aus_images_array():
    from hydrahive.tools.generate_image import _extract_image_url
    data = {"choices": [{"message": {"images": [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,XXX"}}
    ]}}]}
    assert _extract_image_url(data) == "data:image/png;base64,XXX"


def test_extract_aus_content_array_fallback():
    from hydrahive.tools.generate_image import _extract_image_url
    data = {"choices": [{"message": {"content": [
        {"type": "image_url", "image_url": {"url": "https://x.test/a.png"}}
    ]}}]}
    assert _extract_image_url(data) == "https://x.test/a.png"


def test_extract_leer_gibt_none():
    from hydrahive.tools.generate_image import _extract_image_url
    assert _extract_image_url({"choices": [{"message": {"content": None}}]}) is None


# ---------------------------------------------------------------- Speichern

def test_persist_data_uri_schreibt_datei(tmp_path):
    from hydrahive.tools.generate_image import _persist_data_uri
    path, err = _persist_data_uri(_DATA_URI, tmp_path)
    assert err is None
    assert path is not None
    assert path.exists()
    assert path.suffix == ".png"
    assert path.read_bytes() == base64.b64decode(_PNG_B64)


def test_persist_http_url_kein_speichern(tmp_path):
    """Echte URL → kein Speichern, Tool nutzt sie direkt."""
    from hydrahive.tools.generate_image import _persist_data_uri
    path, err = _persist_data_uri("https://x.test/a.png", tmp_path)
    assert path is None
    assert err is None


def test_persist_kaputte_data_uri_gibt_fehler(tmp_path):
    from hydrahive.tools.generate_image import _persist_data_uri
    path, err = _persist_data_uri("data:image/png;base64,!!!nicht-base64!!!", tmp_path)
    assert path is None
    assert err is not None


# ---------------------------------------------------------------- _execute (E2E gemockt)

@pytest.mark.asyncio
async def test_execute_data_uri_speichert_und_gibt_pfad(ctx, tmp_path):
    from hydrahive.tools import generate_image

    mock_resp = _fake_response_images(_DATA_URI)
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with (
        patch("hydrahive.tools.generate_image.httpx.AsyncClient", return_value=mock_client),
        patch("hydrahive.tools.generate_image._get_openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_image._generated_dir", return_value=tmp_path),
    ):
        result = await generate_image._execute({"prompt": "ein Eisbär"}, ctx)

    assert result.success
    # Pfad im Output, KEIN base64 im LLM-Kontext
    assert str(tmp_path) in str(result.output)
    assert "base64" not in str(result.output)
    # Datei existiert wirklich
    files = list(tmp_path.glob("*.png"))
    assert len(files) == 1


@pytest.mark.asyncio
async def test_execute_http_url_gibt_image_url_result(ctx, tmp_path):
    from hydrahive.tools import generate_image

    mock_resp = _fake_response_images("https://cdn.test/generated/abc.png")
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with (
        patch("hydrahive.tools.generate_image.httpx.AsyncClient", return_value=mock_client),
        patch("hydrahive.tools.generate_image._get_openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_image._generated_dir", return_value=tmp_path),
    ):
        result = await generate_image._execute({"prompt": "test"}, ctx)

    assert result.success
    assert result.result_type == "image_url"
    assert result.output == "https://cdn.test/generated/abc.png"


@pytest.mark.asyncio
async def test_execute_kein_key_fehler(ctx):
    from hydrahive.tools import generate_image
    with patch("hydrahive.tools.generate_image._get_openrouter_key", return_value=""):
        result = await generate_image._execute({"prompt": "test"}, ctx)
    assert not result.success
    assert "openrouter" in result.error.lower()


@pytest.mark.asyncio
async def test_execute_leerer_prompt_fehler(ctx):
    from hydrahive.tools import generate_image
    with patch("hydrahive.tools.generate_image._get_openrouter_key", return_value="sk-or-v1-test"):
        result = await generate_image._execute({"prompt": ""}, ctx)
    assert not result.success


@pytest.mark.asyncio
async def test_execute_api_fehler(ctx, tmp_path):
    import httpx
    from hydrahive.tools import generate_image

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.HTTPError("boom"))

    with (
        patch("hydrahive.tools.generate_image.httpx.AsyncClient", return_value=mock_client),
        patch("hydrahive.tools.generate_image._get_openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_image._execute({"prompt": "test"}, ctx)
    assert not result.success


@pytest.mark.asyncio
async def test_execute_keine_bild_url_fehler(ctx, tmp_path):
    from hydrahive.tools import generate_image

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": "nur Text"}}]}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with (
        patch("hydrahive.tools.generate_image.httpx.AsyncClient", return_value=mock_client),
        patch("hydrahive.tools.generate_image._get_openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_image._execute({"prompt": "test"}, ctx)
    assert not result.success
