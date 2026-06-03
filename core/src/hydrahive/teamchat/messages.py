"""teamchat/messages.py — Matrix-Nachrichten senden und lesen.

send_message: Sendet eine Plaintext-Nachricht in einen Raum.
history:      Gibt die letzten N Nachrichten chronologisch zurück.

Schicht-1: nur m.text, kein HTML/formatted_body.
"""
from __future__ import annotations

import logging

import nio

from hydrahive.teamchat.client import build_client
from hydrahive.teamchat.identity import ensure_identity

logger = logging.getLogger(__name__)


class MessageError(Exception):
    """Wird geworfen wenn ein Matrix-Send- oder History-Aufruf fehlschlägt."""


async def send_message(room_id: str, sender_user_id: str, text: str) -> dict:
    """Sendet eine Plaintext-Nachricht in *room_id* als *sender_user_id*.

    Returns:
        {"event_id": str, "sender": MXID, "text": str}

    Raises:
        MessageError: Wenn room_send eine Fehler-Response zurückgibt.
    """
    from hydrahive.settings import settings

    s = await ensure_identity(sender_user_id)
    client = build_client(settings.matrix_homeserver_url, s.user_id, s.access_token, s.device_id)
    try:
        resp = await client.room_send(
            room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": text},
        )
        if isinstance(resp, nio.RoomSendResponse):
            logger.debug(
                "send_message: event_id=%s room=%s sender=%s",
                resp.event_id, room_id, s.user_id,
            )
            return {"event_id": resp.event_id, "sender": s.user_id, "text": text}
        raise MessageError(
            f"room_send fehlgeschlagen in room={room_id!r}: {resp!r}"
        )
    finally:
        await client.close()


async def history(
    room_id: str,
    requester_user_id: str,
    limit: int = 50,
) -> list[dict]:
    """Gibt die letzten *limit* Textnachrichten in *room_id* zurück.

    Liefert die Nachrichten in chronologischer Reihenfolge (älteste zuerst).
    Nicht-Text-Events (Bilder, Dateien …) werden herausgefiltert.

    Returns:
        Liste von {"event_id", "sender", "text", "ts"}, älteste zuerst.

    Raises:
        MessageError: Wenn room_messages eine Fehler-Response zurückgibt.
    """
    from hydrahive.settings import settings

    r = await ensure_identity(requester_user_id)
    client = build_client(settings.matrix_homeserver_url, r.user_id, r.access_token, r.device_id)
    try:
        resp = await client.room_messages(
            room_id,
            start="",
            limit=limit,
            direction=nio.MessageDirection.back,
        )
        if isinstance(resp, nio.RoomMessagesResponse):
            # direction=back → neueste zuerst; umkehren für chronologische Reihenfolge
            text_events = [
                {
                    "event_id": ev.event_id,
                    "sender": ev.sender,
                    "text": ev.body,
                    "ts": ev.server_timestamp,
                }
                for ev in resp.chunk
                if isinstance(ev, nio.RoomMessageText)
            ]
            logger.debug(
                "history: room=%s requester=%s total_chunk=%d text_events=%d",
                room_id, r.user_id, len(resp.chunk), len(text_events),
            )
            return list(reversed(text_events))
        raise MessageError(
            f"room_messages fehlgeschlagen in room={room_id!r}: {resp!r}"
        )
    finally:
        await client.close()
