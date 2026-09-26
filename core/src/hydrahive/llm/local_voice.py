"""Lokale Sprach-Modelle als auswählbare Einträge (Whisper STT, Piper TTS).

Die lokalen Dienste laufen in eigenen Incus-Containern und sind über
Wyoming auf 127.0.0.1 erreichbar (siehe voice/stt.py, voice/tts.py). Sie
stehen in keinem Anbieter-Katalog. Damit sie in der Standard-Auswahl
erscheinen und die Agent-Tools sie nutzen können, bekommen sie feste IDs
mit dem Präfix `local/`.

Angeboten wird ein lokales Modell nur, wenn sein Dienst gerade erreichbar
ist. Eine Auswahl, die ins Leere läuft, wäre schlechter als keine.
"""
from __future__ import annotations

import asyncio
import socket

from hydrahive.voice.stt import STT_HOST, STT_PORT
from hydrahive.voice.tts import PIPER_HOST, PIPER_PORT

LOCAL_PREFIX = "local/"
LOCAL_STT_ID = "local/whisper"
LOCAL_TTS_ID = "local/piper"

_ENTRIES = {
    "stt": (LOCAL_STT_ID, "Whisper (lokal, dieser Server)", STT_HOST, STT_PORT),
    "tts": (LOCAL_TTS_ID, "Piper (lokal, dieser Server)", PIPER_HOST, PIPER_PORT),
}


def is_local(model_id: str) -> bool:
    return (model_id or "").startswith(LOCAL_PREFIX)


def _reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


async def list_local(purpose: str) -> list[dict]:
    """Lokale Modelle für `stt` oder `tts`, nur wenn der Dienst antwortet."""
    entry = _ENTRIES.get(purpose)
    if entry is None:
        return []
    model_id, name, host, port = entry
    if not await asyncio.to_thread(_reachable, host, port):
        return []
    return [{"id": model_id, "name": name}]
