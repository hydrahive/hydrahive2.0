"""Wyoming-Wire-Framing (voice/_wyoming.py), geteilt von STT + TTS."""
from __future__ import annotations

import asyncio
import json

import pytest


class _FakeWriter:
    def __init__(self):
        self.buf = bytearray()

    def write(self, b):
        self.buf.extend(b)

    async def drain(self):
        pass


@pytest.mark.asyncio
async def test_send_event_header_data_payload():
    from hydrahive.voice._wyoming import send_event
    w = _FakeWriter()
    await send_event(w, "synthesize", {"text": "Hi"}, b"\x01\x02")
    line, rest = bytes(w.buf).split(b"\n", 1)
    hdr = json.loads(line)
    assert hdr["type"] == "synthesize"
    assert hdr["data_length"] > 0
    assert hdr["payload_length"] == 2
    data = json.loads(rest[: hdr["data_length"]])
    assert data == {"text": "Hi"}
    assert rest[hdr["data_length"]:] == b"\x01\x02"


@pytest.mark.asyncio
async def test_send_event_nur_typ():
    from hydrahive.voice._wyoming import send_event
    w = _FakeWriter()
    await send_event(w, "audio-stop")
    line = bytes(w.buf).rstrip(b"\n")
    hdr = json.loads(line)
    assert hdr == {"type": "audio-stop"}


@pytest.mark.asyncio
async def test_recv_event_round_trip():
    from hydrahive.voice._wyoming import recv_event, send_event
    # send in einen Buffer, dann über StreamReader zurücklesen
    w = _FakeWriter()
    await send_event(w, "audio-start", {"rate": 22050, "width": 2, "channels": 1})
    await send_event(w, "audio-chunk", None, b"PCMDATA")
    reader = asyncio.StreamReader()
    reader.feed_data(bytes(w.buf))
    reader.feed_eof()
    et, data, payload = await recv_event(reader)
    assert et == "audio-start" and data["rate"] == 22050
    et2, _, payload2 = await recv_event(reader)
    assert et2 == "audio-chunk" and payload2 == b"PCMDATA"
