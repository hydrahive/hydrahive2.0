"""#150 B1: generate_speech Tool (TTS via OpenRouter gpt-audio).

Live verifiziert 2026-05-31 (3.23): gpt-audio über OpenRouter braucht
stream:true + audio:{voice, format:"pcm16"} (mp3 wird beim Streaming
abgelehnt). Liefert raw PCM16 (24kHz mono 16-bit) in delta.audio.data —
wird in einen WAV-Container gewrappt und im Workspace gespeichert.
"""
from __future__ import annotations

import base64
import io
import json
import wave
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(session_id="s1", agent_id="a1", user_id="u1", workspace=tmp_path)


def _sse_body(b64_chunks: list[str], *, done: bool = True) -> bytes:
    lines = ["data: " + json.dumps({"choices": [{"delta": {"audio": {"data": c}}}]})
             for c in b64_chunks]
    if done:
        lines.append("data: [DONE]")
    return ("\n\n".join(lines) + "\n\n").encode()


class _FakeStream:
    def __init__(self, body: bytes, status=200, chunk_size=48):
        self._body = body
        self.status_code = status
        self._cs = chunk_size

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def aiter_bytes(self):
        for i in range(0, len(self._body), self._cs):
            yield self._body[i:i + self._cs]

    async def aread(self):
        return b'{"error":{"message":"boom"}}'


def _client_with(stream):
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.stream = MagicMock(return_value=stream)
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


# ---------------------------------------------------------------- pcm16 → wav

def test_pcm16_to_wav_header_und_params():
    from hydrahive.tools.generate_speech import _pcm16_to_wav
    pcm = b"\x01\x02" * 100
    raw = _pcm16_to_wav(pcm, sample_rate=24000)
    assert raw[:4] == b"RIFF"
    assert raw[8:12] == b"WAVE"
    with wave.open(io.BytesIO(raw), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 24000
        assert w.readframes(w.getnframes()) == pcm


# ---------------------------------------------------------------- _execute

@pytest.mark.asyncio
async def test_payload_pcm16_voice_und_stream(ctx):
    from hydrahive.tools import generate_speech

    pcm = b"\x00\x01" * 50
    b64 = base64.b64encode(pcm).decode()
    client = _client_with(_FakeStream(_sse_body([b64])))
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
    ):
        await generate_speech._execute({"text": "Hallo", "voice": "echo"}, ctx)

    payload = client.stream.call_args.kwargs["json"]
    assert payload["modalities"] == ["text", "audio"]
    assert payload["audio"] == {"voice": "echo", "format": "pcm16"}
    assert payload["stream"] is True


@pytest.mark.asyncio
async def test_voice_default_alloy(ctx):
    from hydrahive.tools import generate_speech
    pcm = b"\x00\x01" * 50
    b64 = base64.b64encode(pcm).decode()
    client = _client_with(_FakeStream(_sse_body([b64])))
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
    ):
        await generate_speech._execute({"text": "Hallo"}, ctx)
    assert client.stream.call_args.kwargs["json"]["audio"]["voice"] == "alloy"


@pytest.mark.asyncio
async def test_zentrales_modell_aus_media_models(ctx):
    from hydrahive.tools import generate_speech
    pcm = b"\x00\x01" * 50
    b64 = base64.b64encode(pcm).decode()
    client = _client_with(_FakeStream(_sse_body([b64])))
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
        patch("hydrahive.tools.generate_speech.get_media_model", return_value="openai/gpt-audio"),
    ):
        await generate_speech._execute({"text": "x"}, ctx)
    assert client.stream.call_args.kwargs["json"]["model"] == "openai/gpt-audio"


@pytest.mark.asyncio
async def test_execute_speichert_wav(ctx, tmp_path):
    from hydrahive.tools import generate_speech

    pcm = b"\x07\x08" * 500
    b64 = base64.b64encode(pcm).decode()
    half = len(b64) // 2
    stream = _FakeStream(_sse_body([b64[:half], b64[half:]]))
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=_client_with(stream)),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_speech._execute({"text": "Hallo Till"}, ctx)

    assert result.success
    files = list((tmp_path / "generated").glob("*.wav"))
    assert len(files) == 1
    with wave.open(str(files[0]), "rb") as w:
        assert w.readframes(w.getnframes()) == pcm


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
async def test_kein_audio_aber_done(ctx):
    from hydrahive.tools import generate_speech
    stream = _FakeStream(_sse_body([], done=True))
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=_client_with(stream)),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_speech._execute({"text": "x"}, ctx)
    assert not result.success
    assert "erneut" in result.error.lower()


@pytest.mark.asyncio
async def test_stream_vorzeitig_beendet(ctx):
    from hydrahive.tools import generate_speech
    pcm = b"\x01\x02" * 20
    b64 = base64.b64encode(pcm).decode()
    stream = _FakeStream(_sse_body([b64], done=False))
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=_client_with(stream)),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_speech._execute({"text": "x"}, ctx)
    assert not result.success
    assert "vorzeitig" in result.error.lower() or "beendet" in result.error.lower()


@pytest.mark.asyncio
async def test_http_fehler(ctx):
    from hydrahive.tools import generate_speech
    stream = _FakeStream(b"", status=400)
    with (
        patch("hydrahive.tools.generate_speech.httpx.AsyncClient", return_value=_client_with(stream)),
        patch("hydrahive.tools.generate_speech.openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_speech._execute({"text": "x"}, ctx)
    assert not result.success
