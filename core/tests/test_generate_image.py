"""#147 generate_image Tool.

Echtes OpenRouter-Format (live verifiziert 2026-05-31):
  message.images[].image_url.url = data:image/png;base64,...  (~3 MB!)
Die data-URI wird NIE ins LLM gegeben — Bild wird lokal gespeichert,
nur der Pfad geht zurück.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(
        session_id="s1", agent_id="a1", user_id="u1",
        workspace=tmp_path,
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
    ):
        result = await generate_image._execute({"prompt": "ein Eisbär"}, ctx)

    assert result.success
    # Pfad im Output, KEIN base64 im LLM-Kontext
    assert str(tmp_path) in str(result.output)
    assert "base64" not in str(result.output)
    # Datei landet im Workspace (= /api/files-servierbar), nicht in data_dir/generated
    files = list((tmp_path / "generated").glob("*.png"))
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


# ---------------------------------------------------------------- Transparenz (Green-Screen)

def _green_data_uri(size=(8, 8)) -> str:
    """Reines Grün als PNG-data-URI — simuliert das Modell auf Green-Screen."""
    buf = io.BytesIO()
    Image.new("RGB", size, (0, 255, 0)).save(buf, "PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"


def _saved_path(output: str) -> Path:
    return Path(output.split(": ", 1)[1].strip())


def test_schema_hat_transparent_default_true():
    from hydrahive.tools import REGISTRY
    props = REGISTRY["generate_image"].schema["properties"]
    assert "transparent" in props
    assert props["transparent"].get("default") is True


@pytest.mark.asyncio
async def test_transparent_fordert_gruen_an_und_keyt_es(ctx):
    from hydrahive.tools import generate_image

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=_fake_response_images(_green_data_uri()))

    with (
        patch("hydrahive.tools.generate_image.httpx.AsyncClient", return_value=mock_client),
        patch("hydrahive.tools.generate_image._get_openrouter_key", return_value="sk-test"),
    ):
        result = await generate_image._execute(
            {"prompt": "a neon hydra", "model": "openai/gpt-5-image"}, ctx
        )

    assert result.success
    # Grüner Hintergrund wird über image_config angefordert (der bisher fehlende Wert)
    posted = mock_client.post.call_args.kwargs["json"]
    assert posted["image_config"]["background_rgb_color"] == [0, 255, 0]
    # Ergebnis ist PNG, Grün rausgekeyt → voll transparent
    path = _saved_path(result.output)
    assert path.suffix == ".png"
    img = Image.open(path).convert("RGBA")
    alphas = [img.getpixel((x, y))[3] for y in range(img.height) for x in range(img.width)]
    assert max(alphas) == 0


@pytest.mark.asyncio
async def test_opak_pfad_keyt_nicht(ctx):
    from hydrahive.tools import generate_image

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=_fake_response_images(_green_data_uri()))

    with (
        patch("hydrahive.tools.generate_image.httpx.AsyncClient", return_value=mock_client),
        patch("hydrahive.tools.generate_image._get_openrouter_key", return_value="sk-test"),
    ):
        result = await generate_image._execute(
            {"prompt": "x", "model": "openai/gpt-5-image", "transparent": False}, ctx
        )

    assert result.success
    posted = mock_client.post.call_args.kwargs["json"]
    assert "background_rgb_color" not in posted.get("image_config", {})
    # Grün bleibt deckend (kein Key)
    img = Image.open(_saved_path(result.output)).convert("RGBA")
    assert img.getpixel((0, 0))[3] == 255
