"""#152 generate_music Tool (Lyria 3 via OpenRouter).

Echtes Format (live verifiziert 2026-05-31 auf 3.23, abgeglichen mit der
kanonischen OpenClaw-Implementierung PR #82789):
  modalities:["text","audio"] + audio:{format:"mp3"} + stream:true (alle Pflicht).
  Audio kommt gestreamt in delta.audio.data (base64). Der eigentliche Audio-
  Chunk ist EINE riesige SSE-Zeile (mehrere MB) — der Parser muss über
  rohe Bytes puffern (aiter_lines zerlegt die Zeile nicht-deterministisch).
  Ohne audio:{format} liefert Lyria mal Audio, mal nur Struktur-Marker.
"""
from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(session_id="s1", agent_id="a1", user_id="u1", workspace=tmp_path)


def _audio_event(audio_b64: str) -> str:
    return "data: " + json.dumps({"choices": [{"delta": {"audio": {"data": audio_b64}}}]})


def _sse_body(b64_chunks: list[str], *, done: bool = True) -> bytes:
    """Baut den rohen SSE-Byte-Stream wie OpenRouter ihn schickt."""
    lines = [_audio_event(ch) for ch in b64_chunks]
    if done:
        lines.append("data: [DONE]")
    return ("\n\n".join(lines) + "\n\n").encode("utf-8")


# ---------------------------------------------------------------- Registry/Schema

def test_in_registry():
    from hydrahive.tools import REGISTRY
    assert "generate_music" in REGISTRY


def test_schema():
    from hydrahive.tools import REGISTRY
    schema = REGISTRY["generate_music"].schema
    assert "prompt" in schema["properties"]
    assert "model" in schema["properties"]
    assert schema["required"] == ["prompt"]


# ---------------------------------------------------------------- SSE-Parser (pur)

def test_audio_chunk_aus_sse_zeile():
    from hydrahive.tools.generate_music import _audio_chunk_from_sse_line
    line = 'data: {"choices":[{"delta":{"audio":{"data":"QUJD"}}}]}'
    assert _audio_chunk_from_sse_line(line) == "QUJD"


def test_audio_chunk_ignoriert_done_und_text():
    from hydrahive.tools.generate_music import _audio_chunk_from_sse_line
    assert _audio_chunk_from_sse_line("data: [DONE]") is None
    assert _audio_chunk_from_sse_line(": comment") is None
    assert _audio_chunk_from_sse_line('data: {"choices":[{"delta":{"content":"hi"}}]}') is None


def test_done_line_erkannt():
    from hydrahive.tools.generate_music import _is_done_line
    assert _is_done_line("data: [DONE]") is True
    assert _is_done_line("data:[DONE]") is True
    assert _is_done_line('data: {"choices":[]}') is False
    assert _is_done_line(": comment") is False


# ---------------------------------------------------------------- _execute (gemockt)

class _FakeStream:
    """Simuliert resp aus client.stream(...) mit aiter_bytes() in kleinen Häppchen."""

    def __init__(self, body: bytes, status=200, chunk_size=48):
        self._body = body
        self.status_code = status
        self._chunk_size = chunk_size

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def aiter_bytes(self):
        for i in range(0, len(self._body), self._chunk_size):
            yield self._body[i:i + self._chunk_size]

    async def aread(self):
        return b'{"error":{"message":"boom"}}'


def _client_with(stream):
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.stream = MagicMock(return_value=stream)
    return client


@pytest.mark.asyncio
async def test_payload_enthaelt_audio_format_und_stream(ctx):
    from hydrahive.tools import generate_music

    raw = b"ID3\x03audio"
    b64 = base64.b64encode(raw).decode()
    client = _client_with(_FakeStream(_sse_body([b64])))

    with (
        patch("hydrahive.tools.generate_music.httpx.AsyncClient", return_value=client),
        patch("hydrahive.tools.generate_music.openrouter_key", return_value="sk-or-v1-test"),
    ):
        await generate_music._execute({"prompt": "upbeat jazz"}, ctx)

    payload = client.stream.call_args.kwargs["json"]
    assert payload["modalities"] == ["text", "audio"]
    assert payload["audio"] == {"format": "mp3"}
    assert payload["stream"] is True


@pytest.mark.asyncio
async def test_execute_speichert_mp3_im_workspace(ctx, tmp_path):
    from hydrahive.tools import generate_music

    raw = b"ID3\x03audio-bytes-hier"
    b64 = base64.b64encode(raw).decode()
    stream = _FakeStream(_sse_body([b64]))

    with (
        patch("hydrahive.tools.generate_music.httpx.AsyncClient", return_value=_client_with(stream)),
        patch("hydrahive.tools.generate_music.openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_music._execute({"prompt": "upbeat jazz"}, ctx)

    assert result.success
    assert str(tmp_path) in str(result.output)
    files = list((tmp_path / "generated").glob("*.mp3"))
    assert len(files) == 1
    assert files[0].read_bytes() == raw


@pytest.mark.asyncio
async def test_execute_grosse_einzelzeile_ueber_byte_haeppchen(ctx, tmp_path):
    """Regression: der Audio-Chunk ist EINE riesige SSE-Zeile. Über mehrere
    Byte-Häppchen verteilt muss er deterministisch zusammengesetzt werden
    (aiter_lines war hier nicht-deterministisch)."""
    from hydrahive.tools import generate_music

    raw = b"ID3\x03" + b"x" * 5000
    b64 = base64.b64encode(raw).decode()
    # winzige Häppchen erzwingen Split MITTEN in der data:-Zeile
    stream = _FakeStream(_sse_body([b64]), chunk_size=17)

    with (
        patch("hydrahive.tools.generate_music.httpx.AsyncClient", return_value=_client_with(stream)),
        patch("hydrahive.tools.generate_music.openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_music._execute({"prompt": "x"}, ctx)

    assert result.success
    files = list((tmp_path / "generated").glob("*.mp3"))
    assert files[0].read_bytes() == raw


@pytest.mark.asyncio
async def test_execute_kein_key_fehler(ctx):
    from hydrahive.tools import generate_music
    with patch("hydrahive.tools.generate_music.openrouter_key", return_value=""):
        result = await generate_music._execute({"prompt": "x"}, ctx)
    assert not result.success
    assert "openrouter" in result.error.lower()


@pytest.mark.asyncio
async def test_execute_leerer_prompt(ctx):
    from hydrahive.tools import generate_music
    with patch("hydrahive.tools.generate_music.openrouter_key", return_value="sk-or-v1-test"):
        result = await generate_music._execute({"prompt": "   "}, ctx)
    assert not result.success


@pytest.mark.asyncio
async def test_execute_kein_audio_aber_done(ctx):
    """[DONE] gesehen, aber kein Audio (nur Marker) → klare 'erneut versuchen'-Meldung."""
    from hydrahive.tools import generate_music
    stream = _FakeStream(_sse_body([], done=True))
    with (
        patch("hydrahive.tools.generate_music.httpx.AsyncClient", return_value=_client_with(stream)),
        patch("hydrahive.tools.generate_music.openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_music._execute({"prompt": "x"}, ctx)
    assert not result.success
    assert "erneut" in result.error.lower()


@pytest.mark.asyncio
async def test_execute_stream_vorzeitig_beendet(ctx):
    """Audio-Chunks kamen, aber kein [DONE] → Abbruch-Meldung (nicht 'kein Audio')."""
    from hydrahive.tools import generate_music
    raw = b"ID3\x03teil"
    b64 = base64.b64encode(raw).decode()
    stream = _FakeStream(_sse_body([b64], done=False))
    with (
        patch("hydrahive.tools.generate_music.httpx.AsyncClient", return_value=_client_with(stream)),
        patch("hydrahive.tools.generate_music.openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_music._execute({"prompt": "x"}, ctx)
    assert not result.success
    assert "vorzeitig" in result.error.lower() or "beendet" in result.error.lower()


@pytest.mark.asyncio
async def test_execute_http_fehler(ctx):
    from hydrahive.tools import generate_music
    stream = _FakeStream(b"", status=400)
    with (
        patch("hydrahive.tools.generate_music.httpx.AsyncClient", return_value=_client_with(stream)),
        patch("hydrahive.tools.generate_music.openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_music._execute({"prompt": "x"}, ctx)
    assert not result.success
