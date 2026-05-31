"""Geteilte OpenRouter-Media-Helfer (Key-Lookup + base64→Datei + SSE-Audio-Stream)."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest


def test_save_bytes_schreibt_datei_mit_endung(tmp_path):
    from hydrahive.tools._openrouter_media import save_bytes
    path = save_bytes(b"\x00\x01\x02", tmp_path / "sub", "mp3")
    assert path.exists()
    assert path.suffix == ".mp3"
    assert path.parent == tmp_path / "sub"
    assert path.read_bytes() == b"\x00\x01\x02"


def test_save_bytes_eindeutige_namen(tmp_path):
    from hydrahive.tools._openrouter_media import save_bytes
    a = save_bytes(b"x", tmp_path, "png")
    b = save_bytes(b"y", tmp_path, "png")
    assert a != b


def test_save_bytes_strippt_punkt_in_endung(tmp_path):
    from hydrahive.tools._openrouter_media import save_bytes
    path = save_bytes(b"x", tmp_path, ".wav")
    assert path.suffix == ".wav"
    assert ".." not in path.name


def test_openrouter_key_liest_aus_config():
    from hydrahive.tools import _openrouter_media
    with patch("hydrahive.llm._config.load_config", return_value={
        "providers": [{"id": "openrouter", "api_key": "sk-or-v1-abc"}]
    }):
        assert _openrouter_media.openrouter_key() == "sk-or-v1-abc"


def test_openrouter_key_leer_wenn_nicht_konfiguriert():
    from hydrahive.tools import _openrouter_media
    with patch("hydrahive.llm._config.load_config", return_value={"providers": []}):
        assert _openrouter_media.openrouter_key() == ""


# ---------------------------------------------------------------- SSE-Parser (pur)

def test_audio_chunk_und_done_line():
    from hydrahive.tools._openrouter_media import audio_chunk_from_sse_line, is_done_line
    line = 'data: {"choices":[{"delta":{"audio":{"data":"QUJD"}}}]}'
    assert audio_chunk_from_sse_line(line) == "QUJD"
    assert audio_chunk_from_sse_line("data: [DONE]") is None
    assert audio_chunk_from_sse_line(": comment") is None
    assert is_done_line("data: [DONE]") is True
    assert is_done_line("data:[DONE]") is True
    assert is_done_line('data: {"x":1}') is False


# ---------------------------------------------------------------- read_audio_sse (Byte-Stream)

class _Resp:
    def __init__(self, body: bytes, chunk_size: int = 32):
        self._body = body
        self._cs = chunk_size

    async def aiter_bytes(self):
        for i in range(0, len(self._body), self._cs):
            yield self._body[i:i + self._cs]


def _sse(chunks: list[str], done: bool = True) -> bytes:
    lines = ["data: " + json.dumps({"choices": [{"delta": {"audio": {"data": c}}}]}) for c in chunks]
    if done:
        lines.append("data: [DONE]")
    return ("\n\n".join(lines) + "\n\n").encode()


@pytest.mark.asyncio
async def test_read_audio_sse_setzt_chunks_zusammen():
    from hydrahive.tools._openrouter_media import read_audio_sse
    parts, done = await read_audio_sse(_Resp(_sse(["QQ==", "Qg=="]), chunk_size=7))
    assert parts == ["QQ==", "Qg=="]
    assert done is True


@pytest.mark.asyncio
async def test_read_audio_sse_done_false_ohne_marker():
    from hydrahive.tools._openrouter_media import read_audio_sse
    parts, done = await read_audio_sse(_Resp(_sse(["QQ=="], done=False)))
    assert parts == ["QQ=="]
    assert done is False


# ---------------------------------------------------------------- PCM → WAV

def test_pcm16_to_wav_round_trip():
    import io
    import wave
    from hydrahive.tools._openrouter_media import pcm16_to_wav
    pcm = b"\x01\x02" * 100
    raw = pcm16_to_wav(pcm, sample_rate=24000, channels=1)
    assert raw[:4] == b"RIFF" and raw[8:12] == b"WAVE"
    with wave.open(io.BytesIO(raw), "rb") as w:
        assert w.getframerate() == 24000
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.readframes(w.getnframes()) == pcm


def test_parse_pcm_content_type():
    from hydrahive.tools._openrouter_media import parse_pcm_content_type
    assert parse_pcm_content_type("audio/pcm;rate=24000;channels=1") == (24000, 1)
    assert parse_pcm_content_type("audio/pcm;rate=48000;channels=2") == (48000, 2)
    # ohne Angaben → Defaults
    assert parse_pcm_content_type("audio/pcm") == (24000, 1)
    assert parse_pcm_content_type("") == (24000, 1)
