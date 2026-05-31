"""#150 B1 (rework): generate_speech via dediziertem /audio/speech-Endpoint.

Live verifiziert 2026-05-31 (3.23): POST /api/v1/audio/speech mit
{model, input, voice, response_format:"mp3"} liefert rohe MP3-Bytes (verbatim,
kein Streaming, kein Konversations-Modell). voice ist Pflicht; Default =
erste supported_voice des Modells. gpt-audio (chat) war der falsche Weg.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(session_id="s1", agent_id="a1", user_id="u1", workspace=tmp_path)


def _client(content=b"\xff\xf3mp3-bytes", status=200, text='{"error":{"message":"boom"}}'):
    resp = MagicMock()
    resp.status_code = status
    resp.content = content
    resp.text = text
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.post = AsyncMock(return_value=resp)
    return client


# ---------------------------------------------------------------- Registry/Schema

def test_in_registry():
    from hydrahive.tools import REGISTRY
    assert "generate_speech" in REGISTRY


def test_schema():
    from hydrahive.tools import REGISTRY
    schema = REGISTRY["generate_speech"].schema
    assert "text" in schema["properties"]
    assert "voice" in schema["properties"]
    assert "model" in schema["properties"]
    assert schema["required"] == ["text"]


# ---------------------------------------------------------------- _execute

@pytest.mark.asyncio
async def test_payload_audio_speech_format(ctx):
    from hydrahive.tools import generate_speech
    client = _client()
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
    ):
        await generate_speech._execute({"text": "Hallo", "voice": "af_bella", "model": "hexgrad/kokoro-82m"}, ctx)

    args, kwargs = client.post.call_args
    assert args[0].endswith("/audio/speech")
    body = kwargs["json"]
    assert body["model"] == "hexgrad/kokoro-82m"
    assert body["input"] == "Hallo"
    assert body["voice"] == "af_bella"
    assert body["response_format"] == "mp3"
    # KEIN chat-Streaming-Kram
    assert "modalities" not in body and "stream" not in body


@pytest.mark.asyncio
async def test_voice_default_aus_first_voice(ctx):
    from hydrahive.tools import generate_speech
    client = _client()
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="hexgrad/kokoro-82m"),
        patch("hydrahive.tools.generate_speech.first_voice", AsyncMock(return_value="af_bella")),
    ):
        await generate_speech._execute({"text": "Hallo"}, ctx)
    assert client.post.call_args.kwargs["json"]["voice"] == "af_bella"


@pytest.mark.asyncio
async def test_fehlt_voice_und_keine_default(ctx):
    from hydrahive.tools import generate_speech
    with (
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="hexgrad/kokoro-82m"),
        patch("hydrahive.tools.generate_speech.first_voice", AsyncMock(return_value=None)),
    ):
        result = await generate_speech._execute({"text": "Hallo"}, ctx)
    assert not result.success
    assert "voice" in result.error.lower() or "stimme" in result.error.lower()


@pytest.mark.asyncio
async def test_zentrales_modell_aus_media_models(ctx):
    from hydrahive.tools import generate_speech
    client = _client()
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="openai/gpt-4o-mini-tts-2025-12-15"),
        patch("hydrahive.tools.generate_speech.first_voice", AsyncMock(return_value="alloy")),
    ):
        await generate_speech._execute({"text": "x"}, ctx)
    assert client.post.call_args.kwargs["json"]["model"] == "openai/gpt-4o-mini-tts-2025-12-15"


@pytest.mark.asyncio
async def test_speichert_mp3(ctx, tmp_path):
    from hydrahive.tools import generate_speech
    raw = b"\xff\xf3" + b"songbytes" * 10
    client = _client(content=raw)
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.first_voice", AsyncMock(return_value="af_bella")),
    ):
        result = await generate_speech._execute({"text": "Hallo Till"}, ctx)
    assert result.success
    files = list((tmp_path / "generated").glob("*.mp3"))
    assert len(files) == 1
    assert files[0].read_bytes() == raw


@pytest.mark.asyncio
async def test_leerer_text(ctx):
    from hydrahive.tools import generate_speech
    with patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"):
        result = await generate_speech._execute({"text": "  "}, ctx)
    assert not result.success


@pytest.mark.asyncio
async def test_kein_key(ctx):
    from hydrahive.tools import generate_speech
    with patch("hydrahive.tools.generate_speech.openrouter_key", return_value=""):
        result = await generate_speech._execute({"text": "x"}, ctx)
    assert not result.success
    assert "openrouter" in result.error.lower()


@pytest.mark.asyncio
async def test_http_fehler(ctx):
    from hydrahive.tools import generate_speech
    client = _client(content=b"", status=400, text='{"error":{"message":"nope"}}')
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.first_voice", AsyncMock(return_value="af_bella")),
    ):
        result = await generate_speech._execute({"text": "x"}, ctx)
    assert not result.success


@pytest.mark.asyncio
async def test_leere_audio_antwort(ctx):
    from hydrahive.tools import generate_speech
    client = _client(content=b"", status=200)
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.first_voice", AsyncMock(return_value="af_bella")),
    ):
        result = await generate_speech._execute({"text": "x"}, ctx)
    assert not result.success
