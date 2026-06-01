"""#151 transcribe_audio Tool — Audio-Transkription via OpenRouter Whisper-API."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(session_id="s1", agent_id="a1", user_id="u1", workspace=tmp_path)


@pytest.fixture
def audio_file(tmp_path):
    p = tmp_path / "voice.webm"
    p.write_bytes(b"\x1aE\xdf\xa3")  # minimal webm-Header-Bytes
    return p


# ---------------------------------------------------------------- Registry/Schema

def test_transcribe_audio_in_registry():
    from hydrahive.tools import REGISTRY
    assert "transcribe_audio" in REGISTRY


def test_transcribe_audio_schema_felder():
    from hydrahive.tools import REGISTRY
    schema = REGISTRY["transcribe_audio"].schema
    props = schema["properties"]
    assert {"file", "language", "model"} <= set(props)
    assert schema["required"] == ["file"]


# ---------------------------------------------------------------- _mime_for

def test_mime_for_webm():
    from hydrahive.tools.transcribe_audio import _mime_for
    # mimetypes gibt video/webm oder audio/webm zurück — beide sind gültig
    assert _mime_for(Path("test.webm")) in ("audio/webm", "video/webm")


def test_mime_for_m4a():
    from hydrahive.tools.transcribe_audio import _mime_for
    assert _mime_for(Path("test.m4a")) == "audio/mp4"


def test_mime_for_mp3():
    from hydrahive.tools.transcribe_audio import _mime_for
    mime = _mime_for(Path("test.mp3"))
    assert "mpeg" in mime or "mp3" in mime


def test_mime_for_unbekannt():
    from hydrahive.tools.transcribe_audio import _mime_for
    assert _mime_for(Path("test.xyz")) == "audio/mpeg"


# ---------------------------------------------------------------- _openrouter_transcribe Helfer

@pytest.mark.asyncio
async def test_transcribe_file_gibt_text():
    from hydrahive.tools._openrouter_transcribe import transcribe_file

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"text": "Hallo Welt"}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("hydrahive.tools._openrouter_transcribe.httpx.AsyncClient", return_value=mock_client):
        text = await transcribe_file(b"audio", "test.webm", key="sk-test", model="openai/whisper-1")

    assert text == "Hallo Welt"


@pytest.mark.asyncio
async def test_transcribe_file_api_fehler():
    from hydrahive.tools._openrouter_transcribe import transcribe_file

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "bad request"
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("hydrahive.tools._openrouter_transcribe.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="400"):
            await transcribe_file(b"audio", "test.webm", key="sk-test", model="openai/whisper-1")


# ---------------------------------------------------------------- _execute (E2E gemockt)

@pytest.mark.asyncio
async def test_execute_gibt_transkript(ctx, audio_file):
    from hydrahive.tools import transcribe_audio

    with (
        patch("hydrahive.tools.transcribe_audio.openrouter_key", return_value="sk-test"),
        patch("hydrahive.tools.transcribe_audio.transcribe_file",
              new_callable=AsyncMock, return_value="Das ist ein Test."),
    ):
        result = await transcribe_audio._execute({"file": str(audio_file)}, ctx)

    assert result.success
    assert "Test" in result.output


@pytest.mark.asyncio
async def test_execute_kein_key(ctx, audio_file):
    from hydrahive.tools import transcribe_audio
    with patch("hydrahive.tools.transcribe_audio.openrouter_key", return_value=""):
        result = await transcribe_audio._execute({"file": str(audio_file)}, ctx)
    assert not result.success
    assert "openrouter" in (result.error or result.output).lower()


@pytest.mark.asyncio
async def test_execute_datei_nicht_gefunden(ctx):
    from hydrahive.tools import transcribe_audio
    with patch("hydrahive.tools.transcribe_audio.openrouter_key", return_value="sk-test"):
        result = await transcribe_audio._execute({"file": "/tmp/ghost_audio.webm"}, ctx)
    assert not result.success
    assert "nicht gefunden" in (result.error or result.output)


@pytest.mark.asyncio
async def test_execute_leerer_file_param(ctx):
    from hydrahive.tools import transcribe_audio
    with patch("hydrahive.tools.transcribe_audio.openrouter_key", return_value="sk-test"):
        result = await transcribe_audio._execute({"file": ""}, ctx)
    assert not result.success


@pytest.mark.asyncio
async def test_execute_datei_zu_gross(ctx, tmp_path):
    from hydrahive.tools import transcribe_audio
    from hydrahive.tools.transcribe_audio import _MAX_FILE_BYTES
    big = tmp_path / "big.webm"
    big.write_bytes(b"x" * (_MAX_FILE_BYTES + 1))
    with patch("hydrahive.tools.transcribe_audio.openrouter_key", return_value="sk-test"):
        result = await transcribe_audio._execute({"file": str(big)}, ctx)
    assert not result.success
    assert "groß" in (result.error or result.output)


@pytest.mark.asyncio
async def test_execute_mit_language_param(ctx, audio_file):
    from hydrahive.tools import transcribe_audio

    captured = {}

    async def fake_transcribe(audio, filename, *, key, model, language=None):
        captured["language"] = language
        return "Bonjour"

    with (
        patch("hydrahive.tools.transcribe_audio.openrouter_key", return_value="sk-test"),
        patch("hydrahive.tools.transcribe_audio.transcribe_file", side_effect=fake_transcribe),
    ):
        result = await transcribe_audio._execute(
            {"file": str(audio_file), "language": "fr"}, ctx
        )

    assert result.success
    assert captured["language"] == "fr"


@pytest.mark.asyncio
async def test_execute_api_fehler_gibt_fehlermeldung(ctx, audio_file):
    from hydrahive.tools import transcribe_audio

    with (
        patch("hydrahive.tools.transcribe_audio.openrouter_key", return_value="sk-test"),
        patch("hydrahive.tools.transcribe_audio.transcribe_file",
              new_callable=AsyncMock,
              side_effect=RuntimeError("OpenRouter Transcribe Fehler 503: Service Unavailable")),
    ):
        result = await transcribe_audio._execute({"file": str(audio_file)}, ctx)

    assert not result.success
    assert "503" in (result.error or result.output)
