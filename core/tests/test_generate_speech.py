"""#150 generate_speech Tool — dünner Wrapper um _openrouter_media.synthesize_speech.

Die Synthese-Details (POST /audio/speech, pcm→WAV, Voice-Auflösung) sind in
test_openrouter_media.py getestet. Hier nur das Wrapping: Datei speichern,
Hinweis anhängen, Fehler durchreichen.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(session_id="s1", agent_id="a1", user_id="u1", workspace=tmp_path)


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


@pytest.mark.asyncio
async def test_speichert_datei_mit_endung_und_voice(ctx, tmp_path):
    from hydrahive.tools import generate_speech
    with (
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="hexgrad/kokoro-82m"),
        patch("hydrahive.tools.generate_speech.synthesize_speech",
              AsyncMock(return_value=(b"WAVDATA", "wav", "af_bella", None))),
    ):
        result = await generate_speech._execute({"text": "Hallo"}, ctx)
    assert result.success
    files = list((tmp_path / "generated").glob("*.wav"))
    assert len(files) == 1 and files[0].read_bytes() == b"WAVDATA"


@pytest.mark.asyncio
async def test_note_wird_an_ergebnis_angehaengt(ctx):
    from hydrahive.tools import generate_speech
    with (
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="hexgrad/kokoro-82m"),
        patch("hydrahive.tools.generate_speech.synthesize_speech",
              AsyncMock(return_value=(b"x", "wav", "af_bella",
                                      "Stimme 'onyx' gibt es bei hexgrad/kokoro-82m nicht — 'af_bella' verwendet"))),
    ):
        result = await generate_speech._execute({"text": "x", "voice": "onyx"}, ctx)
    assert result.success
    assert "onyx" in result.output and "af_bella" in result.output


@pytest.mark.asyncio
async def test_uebergibt_voice_und_modell(ctx):
    from hydrahive.tools import generate_speech
    syn = AsyncMock(return_value=(b"x", "mp3", "alloy", None))
    with (
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="hexgrad/kokoro-82m"),
        patch("hydrahive.tools.generate_speech.synthesize_speech", syn),
    ):
        await generate_speech._execute({"text": "Hallo", "voice": "alloy", "model": "openai/gpt-4o-mini-tts"}, ctx)
    args, kwargs = syn.call_args
    assert args[0] == "Hallo" and args[1] == "alloy" and args[2] == "openai/gpt-4o-mini-tts"


@pytest.mark.asyncio
async def test_zentrales_modell_wenn_kein_param(ctx):
    from hydrahive.tools import generate_speech
    syn = AsyncMock(return_value=(b"x", "wav", "af_bella", None))
    with (
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="hexgrad/kokoro-82m"),
        patch("hydrahive.tools.generate_speech.synthesize_speech", syn),
    ):
        await generate_speech._execute({"text": "x"}, ctx)
    assert syn.call_args.args[2] == "hexgrad/kokoro-82m"


@pytest.mark.asyncio
async def test_fehler_aus_synthese_wird_durchgereicht(ctx):
    from hydrahive.tools import generate_speech
    with (
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="hexgrad/kokoro-82m"),
        patch("hydrahive.tools.generate_speech.synthesize_speech",
              AsyncMock(side_effect=RuntimeError("OpenRouter API-Fehler 400: nope"))),
    ):
        result = await generate_speech._execute({"text": "x"}, ctx)
    assert not result.success
    assert "400" in result.error


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
