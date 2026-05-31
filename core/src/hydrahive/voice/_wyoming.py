"""Wyoming-Protokoll-Wire-Framing — geteilt von STT (faster-whisper) und TTS (Piper).

Wyoming-Event = JSON-Header-Zeile (+ data_length/payload_length) gefolgt von
optionalem data-JSON und Binär-Payload. Eine Stelle für beide Voice-Clients.
"""
from __future__ import annotations

import asyncio
import json


async def send_event(writer, etype: str, data: dict | None = None, payload: bytes = b"") -> None:
    header: dict = {"type": etype}
    data_bytes = b""
    if data:
        data_bytes = json.dumps(data, separators=(",", ":")).encode()
        header["data_length"] = len(data_bytes)
    if payload:
        header["payload_length"] = len(payload)
    writer.write(json.dumps(header, separators=(",", ":")).encode() + b"\n")
    if data_bytes:
        writer.write(data_bytes)
    if payload:
        writer.write(payload)
    await writer.drain()


async def recv_event(reader) -> tuple[str, dict, bytes]:
    line = await asyncio.wait_for(reader.readline(), timeout=60.0)
    if not line:
        raise ConnectionError("Wyoming-Verbindung unerwartet geschlossen")
    header = json.loads(line.decode())
    data: dict = {}
    if header.get("data_length", 0) > 0:
        raw = await asyncio.wait_for(reader.readexactly(header["data_length"]), timeout=10.0)
        data = json.loads(raw)
    payload = b""
    if header.get("payload_length", 0) > 0:
        payload = await asyncio.wait_for(reader.readexactly(header["payload_length"]), timeout=30.0)
    return header.get("type", ""), data, payload
