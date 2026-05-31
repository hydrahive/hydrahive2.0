"""B-local: voice/tts.synthesize_local — Wyoming-Piper-Client (Port 10200).

Live verifiziert (3.23, incus-Piper de_DE-thorsten-medium): synthesize{text} →
audio-start{rate:22050,width:2,channels:1} → audio-chunk(PCM)* → audio-stop.
PCM wird zu WAV gewrappt (Rate aus audio-start).
"""
from __future__ import annotations

import asyncio
import io
import wave
from unittest.mock import patch

import pytest

from hydrahive.voice._wyoming import send_event


class _FakeWriter:
    def __init__(self):
        self.buf = bytearray()
        self.closed = False

    def write(self, b):
        self.buf.extend(b)

    async def drain(self):
        pass

    def close(self):
        self.closed = True

    async def wait_closed(self):
        pass


async def _piper_reply(events) -> asyncio.StreamReader:
    """Baut einen StreamReader, der die gegebenen Wyoming-Events liefert."""
    w = _FakeWriter()
    for etype, data, payload in events:
        await send_event(w, etype, data, payload)
    reader = asyncio.StreamReader()
    reader.feed_data(bytes(w.buf))
    reader.feed_eof()
    return reader


def _open_connection_returning(reader):
    async def _fake(host, port):
        return reader, _FakeWriter()
    return _fake


@pytest.mark.asyncio
async def test_synthesize_local_pcm_zu_wav():
    from hydrahive.voice import tts
    pcm = b"\x07\x08" * 200
    reader = await _piper_reply([
        ("audio-start", {"rate": 22050, "width": 2, "channels": 1}, b""),
        ("audio-chunk", None, pcm[:200]),
        ("audio-chunk", None, pcm[200:]),
        ("audio-stop", None, b""),
    ])
    with patch("hydrahive.voice.tts.asyncio.open_connection", _open_connection_returning(reader)):
        data, media_type = await tts.synthesize_local("Hallo Till")
    assert media_type == "audio/wav"
    with wave.open(io.BytesIO(data), "rb") as wv:
        assert wv.getframerate() == 22050
        assert wv.getnchannels() == 1
        assert wv.readframes(wv.getnframes()) == pcm


@pytest.mark.asyncio
async def test_synthesize_local_leerer_text():
    from hydrahive.voice import tts
    with pytest.raises(RuntimeError):
        await tts.synthesize_local("   ")


@pytest.mark.asyncio
async def test_synthesize_local_error_event():
    from hydrahive.voice import tts
    reader = await _piper_reply([("error", {"text": "boom"}, b"")])
    with patch("hydrahive.voice.tts.asyncio.open_connection", _open_connection_returning(reader)):
        with pytest.raises(RuntimeError):
            await tts.synthesize_local("Hallo")


@pytest.mark.asyncio
async def test_synthesize_local_channels_error_freundlich():
    """Piper '# channels not specified' (kein Audio, z.B. nur Satzzeichen) →
    verständliche Meldung statt kryptischem Piper-Text."""
    from hydrahive.voice import tts
    reader = await _piper_reply([("error", {"text": "# channels not specified"}, b"")])
    with patch("hydrahive.voice.tts.asyncio.open_connection", _open_connection_returning(reader)):
        with pytest.raises(RuntimeError, match="Vorlesbares"):
            await tts.synthesize_local("...")


@pytest.mark.asyncio
async def test_synthesize_local_kein_audio():
    from hydrahive.voice import tts
    reader = await _piper_reply([
        ("audio-start", {"rate": 22050, "width": 2, "channels": 1}, b""),
        ("audio-stop", None, b""),
    ])
    with patch("hydrahive.voice.tts.asyncio.open_connection", _open_connection_returning(reader)):
        with pytest.raises(RuntimeError):
            await tts.synthesize_local("Hallo")


def test_tts_route_local_ohne_mmx(client, auth_headers):
    """provider=local darf NICHT auf fehlendes mmx 503en (Piper braucht kein mmx)."""
    from unittest.mock import AsyncMock
    with (
        patch("hydrahive.voice.tts.is_available", return_value=False),
        patch("hydrahive.voice.tts.synthesize_local",
              AsyncMock(return_value=(b"WAVDATA", "audio/wav"))),
    ):
        r = client.post("/api/tts", json={"text": "Hallo", "provider": "local"},
                        headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/wav")
    assert r.content == b"WAVDATA"


@pytest.mark.asyncio
async def test_synthesize_local_sendet_voice_wenn_gesetzt():
    from hydrahive.voice import tts
    captured = _FakeWriter()
    reader = await _piper_reply([
        ("audio-start", {"rate": 22050, "width": 2, "channels": 1}, b""),
        ("audio-chunk", None, b"\x01\x02"),
        ("audio-stop", None, b""),
    ])

    async def _fake(host, port):
        return reader, captured

    with patch("hydrahive.voice.tts.asyncio.open_connection", _fake):
        await tts.synthesize_local("Hallo", voice="de_DE-kerstin-low")
    # erstes Event ist synthesize mit voice.name
    first_line = bytes(captured.buf).split(b"\n", 1)[0]
    assert b"synthesize" in first_line
    assert b"de_DE-kerstin-low" in bytes(captured.buf)


@pytest.mark.asyncio
async def test_synthesize_local_ignoriert_fremd_voice():
    """German_FriendlyMan (MiniMax) ist keine Piper-Voice → NICHT weiterreichen
    (sonst Piper-502). Container-Default wird genutzt."""
    from hydrahive.voice import tts
    captured = _FakeWriter()
    reader = await _piper_reply([
        ("audio-start", {"rate": 22050, "width": 2, "channels": 1}, b""),
        ("audio-chunk", None, b"\x01\x02"),
        ("audio-stop", None, b""),
    ])

    async def _fake(host, port):
        return reader, captured

    with patch("hydrahive.voice.tts.asyncio.open_connection", _fake):
        data, _ = await tts.synthesize_local("Hallo", voice="German_FriendlyMan")
    assert b"German_FriendlyMan" not in bytes(captured.buf)
    assert b"voice" not in bytes(captured.buf)  # gar keine voice gesetzt
