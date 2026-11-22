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


def new_catalog_push(
    seq: int,
    interval_seconds: int,
    items: list[dict],
    deleted: list[dict],
    full_versions: dict | None = None,
    *,
    shared: bool = False,
    remote_edits: bool = False,
) -> dict:
    """Katalog-Push an den Hub (docs/specs/federation-catalog.md §Ablauf 3).

    Einmaligkeit über ``seq`` (streng steigend je Partner), ``msg_id`` dient nur
    der Zuordnung im Log.

    ``shared``/``remote_edits`` (docs/specs/federation-shared-tasks.md
    §Schalter): die eigenen Einstellungen, in jedem Push mitgemeldet, damit der
    Hub sie in ``federation_catalog_sources`` ablegen kann. Standard aus.
    """
    return {
        "kind": "catalog_push",
        "msg_id": str(uuid.uuid4()),
        "from": ident.fingerprint(ident.public_key_b64()),
        "seq": int(seq),
        "interval_seconds": int(interval_seconds),
        "issued_at": int(time.time()),
        "items": list(items),
        "deleted": list(deleted),
        "full_versions": full_versions,
        "shared": bool(shared),
        "remote_edits": bool(remote_edits),
    }


def new_catalog_fetch(item_kind: str, item_id: str, owner: str) -> dict:
    """Hub → Ursprung: Volltext eines Katalog-Eintrags anfordern (Spec §Ablauf 4)."""
    return {
        "kind": "catalog_fetch",
        "msg_id": str(uuid.uuid4()),
        "from": ident.fingerprint(ident.public_key_b64()),
        "issued_at": int(time.time()),
        "item_kind": item_kind,
        "item_id": item_id,
        "owner": owner,
    }


def new_catalog_item(in_reply_to: str, item: dict) -> dict:
    """Ursprung → Hub: signierte Antwort auf ``catalog_fetch`` (wiederholt dessen ``msg_id``)."""
    return {
        "kind": "catalog_item",
        "msg_id": str(uuid.uuid4()),
        "in_reply_to": in_reply_to,
        "from": ident.fingerprint(ident.public_key_b64()),
        "issued_at": int(time.time()),
        "item": item,
    }


def verify_reply(peer: dict, signature: str, payload: object, kind: str, in_reply_to: str) -> dict:
    """Signierte Antwort des Partners prüfen: Signatur mit SEINEM Schlüssel,
    Nachrichtentyp, Frische und dass sie sich auf unsere Anfrage bezieht."""
    if not isinstance(payload, dict):
        raise PeerRejected("peer_payload_invalid", "Antwort ist kein Objekt")
    if not ident.verify(peer["public_key"], payload, signature or ""):
        raise PeerRejected("peer_signature_invalid", f"Antwort-Signatur von {peer['name']} ungültig")
    if payload.get("kind") != kind:
        raise PeerRejected("peer_payload_invalid", "falscher Antworttyp")
    issued = payload.get("issued_at")
    now = time.time()
    if not isinstance(issued, int) or issued < now - MAX_AGE_SECONDS or issued > now + MAX_SKEW_SECONDS:
        raise PeerRejected("peer_expired", f"Antwort von {peer['name']} abgelaufen")
    if payload.get("in_reply_to") != in_reply_to:
        raise PeerRejected("peer_payload_invalid", "Antwort gehört nicht zu unserer Anfrage")
    return payload


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


def verify_incoming(
    peer_header: str, signature: str, payload: dict, kind: str, *, id_field: str = "task_id",
) -> Verified:
    """Prüfreihenfolge laut Spec. Wirft PeerRejected, sonst Absender + Inhalt.

    ``id_field``: Pflichtfeld mit der Nachrichten-ID — ``task_id`` für
    Aufträge/Antworten (Standard, unverändert), ``msg_id`` für Katalog-Nachrichten.
    """
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
    message_id = payload.get(id_field)
    if not isinstance(message_id, str) or not message_id:
        raise PeerRejected("peer_payload_invalid", f"{id_field} fehlt")
    return Verified(peer=peer, payload=payload)
