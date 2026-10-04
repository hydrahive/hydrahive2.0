"""Signierte Nachrichten zwischen gekoppelten HydraHive-Servern.

docs/specs/server-peering.md §Ablauf. Jede Nachricht ist ein JSON-Objekt, das
der Absender mit seinem Ed25519-Schlüssel signiert. Der Empfänger prüft
Absender, Signatur, Frische und Einmaligkeit, bevor er irgendetwas tut.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from hydrahive.db import federation_peers as peers_db
from hydrahive.federation import peer_identity as ident

#: Wie alt eine Nachricht höchstens sein darf (Uhren dürfen leicht abweichen).
MAX_AGE_SECONDS = 300
MAX_SKEW_SECONDS = 60
MAX_TEXT = 200_000

HEADER_PEER = "X-HH-Peer"
HEADER_SIGNATURE = "X-HH-Signature"


class PeerRejected(Exception):
    """Nachricht abgelehnt. ``code`` geht als Fehlercode an den Absender,
    Details bleiben im eigenen Log."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code


@dataclass(frozen=True, slots=True)
class Verified:
    peer: dict
    payload: dict


def new_task(target_agent: str, task: str, task_type: str, profile: str) -> dict:
    now = int(time.time())
    return {
        "kind": "task",
        "task_id": str(uuid.uuid4()),
        "from": ident.fingerprint(ident.public_key_b64()),
        "target_agent": target_agent,
        "task": task[:MAX_TEXT],
        "task_type": task_type,
        "profile": profile,
        "issued_at": now,
    }


def new_reply(task_id: str, status: str, output: str) -> dict:
    return {
        "kind": "reply",
        "task_id": task_id,
        "from": ident.fingerprint(ident.public_key_b64()),
        "status": status,
        "output": output[:MAX_TEXT],
        "issued_at": int(time.time()),
    }


def signed_headers(payload: dict) -> dict[str, str]:
    return {
        HEADER_PEER: ident.fingerprint(ident.public_key_b64()).replace(" ", ""),
        HEADER_SIGNATURE: ident.sign(payload),
        "Content-Type": "application/json",
    }


def _peer_by_header(peer_header: str) -> dict | None:
    wanted = "".join((peer_header or "").split()).lower()
    if not wanted:
        return None
    for peer in peers_db.list_peers():
        if "".join(peer["fingerprint"].split()).lower() == wanted:
            return peer
    return None


def verify_incoming(peer_header: str, signature: str, payload: dict, kind: str) -> Verified:
    """Prüfreihenfolge laut Spec. Wirft PeerRejected, sonst Absender + Inhalt."""
    peer = _peer_by_header(peer_header)
    if not peer or peer["status"] != "active":
        raise PeerRejected("peer_unknown", f"Absender {peer_header!r} nicht gekoppelt/aktiv")
    if not ident.verify(peer["public_key"], payload, signature or ""):
        raise PeerRejected("peer_signature_invalid", f"Signatur von {peer['name']} ungültig")
    if payload.get("kind") != kind:
        raise PeerRejected("peer_payload_invalid", "falscher Nachrichtentyp")
    issued = payload.get("issued_at")
    now = time.time()
    if not isinstance(issued, int) or issued < now - MAX_AGE_SECONDS or issued > now + MAX_SKEW_SECONDS:
        raise PeerRejected("peer_expired", f"Nachricht von {peer['name']} abgelaufen")
    task_id = payload.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        raise PeerRejected("peer_payload_invalid", "task_id fehlt")
    return Verified(peer=peer, payload=payload)
