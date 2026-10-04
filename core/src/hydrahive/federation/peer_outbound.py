"""Aufträge an gekoppelte Server senden und auf die Antwort warten.

Gegenstück zu peer_inbound. ``ask_agent("<agent>@<partner>")`` landet hier,
wenn <partner> ein aktiver gekoppelter HydraHive-Server ist.
"""
from __future__ import annotations

import asyncio
import logging

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
