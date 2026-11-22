"""Aufträge an gekoppelte Server senden und auf die Antwort warten.

Gegenstück zu peer_inbound. ``ask_agent("<agent>@<partner>")`` landet hier,
wenn <partner> ein aktiver gekoppelter HydraHive-Server ist.
"""
from __future__ import annotations

import asyncio
import json
import logging

import httpx

from hydrahive.db import federation_peers as peers_db
from hydrahive.federation import peer_protocol as proto
from hydrahive.federation.peer_inbound import send_signed

logger = logging.getLogger(__name__)

# task_id → (Future, peer_id). Nur der Partner, an den wir geschickt haben,
# darf die Antwort liefern.
_WAITING: dict[str, tuple[asyncio.Future, str]] = {}

_TIMEOUT = {"quick": 240, "standard": 660, "deep": 1_920}


def find_active_peer(name: str) -> dict | None:
    peer = peers_db.get_by_name(name)
    return peer if peer and peer["status"] == "active" else None


async def send_task(peer: dict, target_agent: str, task: str, task_type: str, profile: str) -> dict:
    """Schickt den Auftrag und wartet auf die Antwort. Rückgabe: Antwort-Payload."""
    payload = proto.new_task(target_agent, task, task_type, profile)
    task_id = payload["task_id"]
    peers_db.claim_task(task_id, peer["id"], "out")
    fut: asyncio.Future = asyncio.get_running_loop().create_future()
    _WAITING[task_id] = (fut, peer["id"])
    try:
        await send_signed(peer, "/api/peering/tasks", payload)
        peers_db.set_task_status(task_id, "sent")
        reply = await asyncio.wait_for(fut, timeout=_TIMEOUT.get(profile, _TIMEOUT["standard"]))
        peers_db.set_task_status(task_id, reply.get("status", "error"))
        return reply
    except BaseException:
        peers_db.set_task_status(task_id, "error")
        raise
    finally:
        _WAITING.pop(task_id, None)


def resolve_reply(peer: dict, payload: dict) -> bool:
    """Antwort vom Partner zuordnen. Nur der beauftragte Partner zählt."""
    entry = _WAITING.get(payload["task_id"])
    if not entry:
        return False
    fut, expected_peer = entry
    if expected_peer != peer["id"]:
        logger.warning("Server-Kopplung: Antwort %s von falschem Partner %s verworfen", payload["task_id"], peer["name"])
        return False
    if not fut.done():
        fut.set_result(payload)
    peers_db.touch(peer["id"])
    return True


class ReplyUnavailable(Exception):
    """Partner erreichbar, gibt aber nichts heraus (antwortet 404)."""


# Obergrenze für eine Antwort beim signierten Nachladen (Security-Review #738, MEDIUM):
# Ohne Grenze puffert der Hub eine beliebig große Antwort eines Partners im RAM, bevor
# die Signatur geprüft wird. Gültig sind höchstens MAX_TEXT Zeichen Text; JSONResponse
# schreibt UTF-8 ohne ASCII-Escape, also bis zu 4 Byte je Zeichen, dazu Metadaten.
MAX_REPLY_BYTES = 4 * proto.MAX_TEXT + 65_536
# Fehlerantworten (HTTP ≥ 400) enthalten nur {"detail": {"code", "params"}}: begrenzt
# lesen, damit Aufrufer den Grund (z. B. peer_catalog_not_shared, peer_replay + last_seq)
# bekommen. Ohne Lesen warf response.json() httpx.ResponseNotRead (Live-Befund 22.11.).
MAX_ERROR_BYTES = 65_536


def _too_large() -> proto.PeerRejected:
    return proto.PeerRejected("peer_payload_too_large", f"Antwort größer als {MAX_REPLY_BYTES} Byte")


async def _post(peer: dict, path: str, payload: dict, timeout: float) -> tuple[httpx.Response, bytes]:
    """POST und Antwort begrenzt lesen. Zu groß oder komprimiert → PeerRejected.

    Komprimierung wird abgelehnt (``Accept-Encoding: identity``), damit die Grenze auf
    den echten Bytes gilt und keine gzip-Bombe sie umgeht."""
    headers = {**proto.signed_headers(payload), "Accept-Encoding": "identity"}
    async with httpx.AsyncClient(timeout=timeout, verify=False) as client:  # noqa: S501 - Ed25519 statt TLS
        async with client.stream("POST", peer["url"] + path, json=payload, headers=headers) as response:
            if response.headers.get("content-encoding", "identity").lower() not in ("", "identity"):
                raise proto.PeerRejected("peer_payload_invalid", "komprimierte Antwort")
            if response.status_code >= 400:          # Fehler: nur den Anfang lesen, nie „zu groß“
                return response, await _read_head(response, MAX_ERROR_BYTES)
            length = response.headers.get("content-length", "")
            if length.isdigit() and int(length) > MAX_REPLY_BYTES:
                raise _too_large()
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():   # Komprimierung oben abgelehnt: Bytes = Rohdaten
                size += len(chunk)
                if size > MAX_REPLY_BYTES:
                    raise _too_large()
                chunks.append(chunk)
            return response, b"".join(chunks)


async def _read_head(response: httpx.Response, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        chunks.append(chunk[: limit - size])
        size += len(chunks[-1])
        if size >= limit:
            break
    return b"".join(chunks)


def _status_error(response: httpx.Response, raw: bytes) -> httpx.HTTPStatusError:
    """``HTTPStatusError`` mit LESBARER Antwort (``e.response.json()`` funktioniert)."""
    readable = httpx.Response(
        response.status_code, content=raw, request=response.request,
        headers={"content-type": response.headers.get("content-type", "application/json")},
    )
    return httpx.HTTPStatusError(
        f"HTTP {response.status_code} von {response.request.url}", request=response.request, response=readable,
    )


async def request_signed(peer: dict, path: str, payload: dict, *, reply_kind: str, timeout: float) -> dict:
    """Signiert anfragen UND die signierte Antwort prüfen (Ergänzung zu send_signed,
    das nur die Anfrage signiert). 404 → ReplyUnavailable; andere HTTP-Fehler →
    ``httpx.HTTPStatusError`` mit gelesenem Körper (Code/Parameter); Netz/Timeout → httpx-Fehler;
    ungültige oder zu große Antwort (> MAX_REPLY_BYTES) → PeerRejected. Der Aufrufer
    (catalog_detail) behandelt PeerRejected wie „Ursprung offline“."""
    response, raw = await _post(peer, path, payload, timeout)
    if response.status_code == 404:
        raise ReplyUnavailable(peer["name"])
    if response.status_code >= 400:
        raise _status_error(response, raw)
    try:
        body = json.loads(raw)
    except ValueError as e:
        raise proto.PeerRejected("peer_payload_invalid", "Antwort ist kein JSON") from e
    return proto.verify_reply(
        peer, response.headers.get(proto.HEADER_SIGNATURE, ""), body, reply_kind, payload["msg_id"],
    )
