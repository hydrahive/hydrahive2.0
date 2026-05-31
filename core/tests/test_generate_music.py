"""#152 generate_music Tool (Lyria 3 via OpenRouter).

Echtes Format (live verifiziert 2026-05-31 auf 3.23):
  modalities:["audio","text"] + stream:true (Pflicht), Audio kommt gestreamt
  in delta.audio.data (base64, mehrere Chunks möglich), Default-Format MP3.
"""
from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(session_id="s1", agent_id="a1", user_id="u1", workspace=tmp_path)


def _sse(b64_chunks: list[str]) -> list[str]:
    """Baut SSE-Zeilen wie OpenRouter sie streamt."""
    lines = []
    for ch in b64_chunks:
        lines.append('data: ' + _json_chunk(ch))
    lines.append("data: [DONE]")
    return lines


def _json_chunk(audio_b64: str) -> str:
    import json
    return json.dumps({"choices": [{"delta": {"audio": {"data": audio_b64}}}]})


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


# ---------------------------------------------------------------- _execute (gemockt)

class _FakeStream:
    def __init__(self, lines, status=200):
        self._lines = lines
        self.status_code = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def aiter_lines(self):
        for ln in self._lines:
            yield ln

    async def aread(self):
        return b'{"error":{"message":"boom"}}'


def _client_with(stream):
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.stream = MagicMock(return_value=stream)
    return client


@pytest.mark.asyncio
async def test_execute_speichert_mp3_im_workspace(ctx, tmp_path):
    from hydrahive.tools import generate_music

    raw = b"ID3\x03audio-bytes-hier"
    b64 = base64.b64encode(raw).decode()
    # in zwei Chunks streamen → muss korrekt zusammengesetzt werden
    half = len(b64) // 2
    stream = _FakeStream(_sse([b64[:half], b64[half:]]))

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
async def test_execute_kein_audio_fehler(ctx):
    from hydrahive.tools import generate_music
    stream = _FakeStream(["data: [DONE]"])
    with (
        patch("hydrahive.tools.generate_music.httpx.AsyncClient", return_value=_client_with(stream)),
        patch("hydrahive.tools.generate_music.openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_music._execute({"prompt": "x"}, ctx)
    assert not result.success


@pytest.mark.asyncio
async def test_execute_http_fehler(ctx):
    from hydrahive.tools import generate_music
    stream = _FakeStream([], status=400)
    with (
        patch("hydrahive.tools.generate_music.httpx.AsyncClient", return_value=_client_with(stream)),
        patch("hydrahive.tools.generate_music.openrouter_key", return_value="sk-or-v1-test"),
    ):
        result = await generate_music._execute({"prompt": "x"}, ctx)
    assert not result.success
