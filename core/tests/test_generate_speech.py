"""#150 B1 (rework): generate_speech via dediziertem /audio/speech-Endpoint.

Live verifiziert 2026-05-31 (3.23): POST /api/v1/audio/speech mit
{model, input, voice, response_format:"pcm"} liefert rohe PCM16-Bytes —
universell unterstützt (Gemini-TTS will NUR pcm, andere können's auch). Die
Sample-Rate steht im content-type-Header (audio/pcm;rate=24000;channels=1) →
zuverlässig zu WAV gewrappt, kein Raten. voice Pflicht; Default = first_voice.
"""
from __future__ import annotations

import io
import wave
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(session_id="s1", agent_id="a1", user_id="u1", workspace=tmp_path)


def _client(content=b"\x01\x02" * 100, status=200, text='{"error":{"message":"boom"}}',
            content_type="audio/pcm;rate=24000;channels=1"):
    resp = MagicMock()
    resp.status_code = status
    resp.content = content
    resp.text = text
    resp.headers = {"content-type": content_type}
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
    # pcm: universell (auch Gemini), Rate kommt aus dem Header
    assert body["response_format"] == "pcm"
    assert "modalities" not in body and "stream" not in body


def _voices(*v):
    return AsyncMock(return_value=list(v))


@pytest.mark.asyncio
async def test_voice_default_erste_modell_voice(ctx):
    from hydrahive.tools import generate_speech
    client = _client()
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="hexgrad/kokoro-82m"),
        patch("hydrahive.tools.generate_speech.voices_for", _voices("af_bella", "am_adam")),
    ):
        await generate_speech._execute({"text": "Hallo"}, ctx)
    assert client.post.call_args.kwargs["json"]["voice"] == "af_bella"


@pytest.mark.asyncio
async def test_gueltige_voice_wird_genutzt(ctx):
    from hydrahive.tools import generate_speech
    client = _client()
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="hexgrad/kokoro-82m"),
        patch("hydrahive.tools.generate_speech.voices_for", _voices("af_bella", "am_adam")),
    ):
        await generate_speech._execute({"text": "x", "voice": "am_adam"}, ctx)
    assert client.post.call_args.kwargs["json"]["voice"] == "am_adam"


@pytest.mark.asyncio
async def test_unbekannte_voice_faellt_auf_modell_default(ctx):
    """onyx an kokoro → statt 400 die Standard-Stimme + Hinweis (kein Crash)."""
    from hydrahive.tools import generate_speech
    client = _client()
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="hexgrad/kokoro-82m"),
        patch("hydrahive.tools.generate_speech.voices_for", _voices("af_bella", "am_adam")),
    ):
        result = await generate_speech._execute({"text": "x", "voice": "onyx"}, ctx)
    assert result.success
    assert client.post.call_args.kwargs["json"]["voice"] == "af_bella"
    assert "onyx" in result.output and "af_bella" in result.output  # Hinweis im Ergebnis


@pytest.mark.asyncio
async def test_voice_durchgereicht_wenn_modell_voices_unbekannt(ctx):
    """Provider down → voices_for leer → angeforderte Voice wird durchgereicht (API entscheidet)."""
    from hydrahive.tools import generate_speech
    client = _client()
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="x/unknown"),
        patch("hydrahive.tools.generate_speech.voices_for", _voices()),
    ):
        await generate_speech._execute({"text": "x", "voice": "onyx"}, ctx)
    assert client.post.call_args.kwargs["json"]["voice"] == "onyx"


@pytest.mark.asyncio
async def test_keine_voice_und_keine_modell_voices(ctx):
    from hydrahive.tools import generate_speech
    with (
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="x/unknown"),
        patch("hydrahive.tools.generate_speech.voices_for", _voices()),
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
        patch("hydrahive.tools.generate_speech.voices_for", _voices("alloy")),
    ):
        await generate_speech._execute({"text": "x"}, ctx)
    assert client.post.call_args.kwargs["json"]["model"] == "openai/gpt-4o-mini-tts-2025-12-15"


@pytest.mark.asyncio
async def test_pcm_wird_als_wav_mit_header_rate_gespeichert(ctx, tmp_path):
    from hydrahive.tools import generate_speech
    pcm = b"\x07\x08" * 500
    client = _client(content=pcm, content_type="audio/pcm;rate=24000;channels=1")
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.voices_for", _voices("af_bella")),
    ):
        result = await generate_speech._execute({"text": "Hallo Till"}, ctx)
    assert result.success
    files = list((tmp_path / "generated").glob("*.wav"))
    assert len(files) == 1
    with wave.open(str(files[0]), "rb") as w:
        assert w.getframerate() == 24000
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.readframes(w.getnframes()) == pcm


@pytest.mark.asyncio
async def test_rate_aus_header_geparst(ctx, tmp_path):
    from hydrahive.tools import generate_speech
    pcm = b"\x01\x02" * 200
    client = _client(content=pcm, content_type="audio/pcm;rate=48000;channels=1")
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.voices_for", _voices("af_bella")),
    ):
        await generate_speech._execute({"text": "x"}, ctx)
    f = list((tmp_path / "generated").glob("*.wav"))[0]
    with wave.open(str(f), "rb") as w:
        assert w.getframerate() == 48000


@pytest.mark.asyncio
async def test_mp3_antwort_wird_als_mp3_gespeichert(ctx, tmp_path):
    """Falls ein Modell doch mp3 liefert (content-type audio/mpeg) → direkt speichern."""
    from hydrahive.tools import generate_speech
    raw = b"\xff\xf3mp3"
    client = _client(content=raw, content_type="audio/mpeg")
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.voices_for", _voices("af_bella")),
    ):
        result = await generate_speech._execute({"text": "x"}, ctx)
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
        patch("hydrahive.tools.generate_speech.voices_for", _voices("af_bella")),
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
        patch("hydrahive.tools.generate_speech.voices_for", _voices("af_bella")),
    ):
        result = await generate_speech._execute({"text": "x"}, ctx)
    assert not result.success
