"""B2: OpenRouter als Vorlese-Provider (voice/tts.synthesize_openrouter + /api/tts).

Der OpenRouter-Pfad braucht KEIN mmx — /api/tts darf für provider=openrouter
nicht auf is_available() (mmx) gaten.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------- voice/tts.synthesize_openrouter

@pytest.mark.asyncio
async def test_synthesize_openrouter_gibt_bytes_und_media_type():
    from hydrahive.voice import tts
    with (
        patch("hydrahive.llm._config.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.llm.media_models.get_media_model", return_value="hexgrad/kokoro-82m"),
        patch("hydrahive.tools._openrouter_media.synthesize_speech",
              AsyncMock(return_value=(b"WAVDATA", "wav", "af_bella", None))),
    ):
        data, media_type = await tts.synthesize_openrouter("Hallo", "af_bella")
    assert data == b"WAVDATA"
    assert media_type == "audio/wav"


@pytest.mark.asyncio
async def test_synthesize_openrouter_mp3_media_type():
    from hydrahive.voice import tts
    with (
        patch("hydrahive.llm._config.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.llm.media_models.get_media_model", return_value="openai/gpt-4o-mini-tts"),
        patch("hydrahive.tools._openrouter_media.synthesize_speech",
              AsyncMock(return_value=(b"mp3", "mp3", "alloy", None))),
    ):
        _, media_type = await tts.synthesize_openrouter("Hallo", "alloy")
    assert media_type == "audio/mpeg"


@pytest.mark.asyncio
async def test_synthesize_openrouter_ohne_key_raises():
    from hydrahive.voice import tts
    with patch("hydrahive.llm._config.openrouter_key", return_value=""):
        with pytest.raises(RuntimeError):
            await tts.synthesize_openrouter("Hallo", "af_bella")


# ---------------------------------------------------------------- /api/tts Route (provider=openrouter)

def test_tts_route_openrouter_ohne_mmx(client, auth_headers):
    """Kern-Regression: provider=openrouter darf NICHT auf fehlendes mmx 503en."""
    with (
        patch("hydrahive.voice.tts.is_available", return_value=False),  # mmx fehlt
        patch("hydrahive.voice.tts.synthesize_openrouter",
              AsyncMock(return_value=(b"AUDIO", "audio/wav"))),
    ):
        r = client.post("/api/tts", json={"text": "Hallo", "voice": "af_bella",
                                          "provider": "openrouter"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/wav")
    assert r.content == b"AUDIO"


def test_tts_route_minimax_ohne_mmx_503(client, auth_headers):
    with patch("hydrahive.voice.tts.is_available", return_value=False):
        r = client.post("/api/tts", json={"text": "Hallo", "voice": "x",
                                          "provider": "minimax"}, headers=auth_headers)
    assert r.status_code == 503


def test_tts_voices_openrouter(client, auth_headers):
    with (
        patch("hydrahive.llm.media_models.get_media_model", return_value="hexgrad/kokoro-82m"),
        patch("hydrahive.llm.media_models.voices_for", AsyncMock(return_value=["af_bella", "am_adam"])),
    ):
        r = client.get("/api/tts/voices?provider=openrouter", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["model"] == "hexgrad/kokoro-82m"
    assert [v["voice_id"] for v in data["voices"]] == ["af_bella", "am_adam"]
