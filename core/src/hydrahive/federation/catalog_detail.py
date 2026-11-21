"""Hub: einen Katalog-Eintrag öffnen (docs/specs/federation-catalog.md §Ablauf 4).

Fremder Eintrag: Volltext live und signiert vom Ursprung holen (höchstens
``FETCH_TIMEOUT`` = 10 s), Metadaten nachziehen und als Snapshot speichern. Ist
der Ursprung nicht erreichbar, kommen Metadaten + letzter Snapshot („Stand vom“,
„veraltet“) + „zuletzt gesehen am“. Einen Fehlertext als Inhalt gibt es nie.
Antwortet der Ursprung 404, bleibt der Snapshot: Der Ursprung antwortet laut
Spec in JEDEM Fehlerfall gleich (auch Rate-Limit, Uhrabweichung, Sync aus), der
Hub kann also nicht unterscheiden. Gelöschte oder ausgeschlossene Einträge
verschwinden samt Snapshot mit der Katalog-Zeile beim Abgleich (Spec).

Gelöschte Anmerkungen (Task f3eeec36): Der Snapshot wird bei jedem erfolgreichen
Nachladen GANZ ersetzt, nie ergänzt, und jedes Öffnen versucht zuerst live. Er
wird nur angezeigt, wenn der Ursprung offline ist — dann immer mit „Stand vom“.
Eigener Eintrag des Hubs: direkt aus der lokalen Quelle, kein Snapshot.
"""
from __future__ import annotations

import asyncio
import json
import logging

import httpx

from hydrahive.db import federation_catalog_view as view_db
from hydrahive.db import federation_peers as peers_db
from hydrahive.db._utils import now_iso
from hydrahive.federation import peer_protocol as proto
from hydrahive.federation.catalog_hub import _item as _valid_meta
from hydrahive.federation.catalog_hub import audit
from hydrahive.federation.catalog_view import LOCAL, _public
from hydrahive.federation.peer_outbound import ReplyUnavailable, request_signed
from hydrahive.modules import catalog_sources

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = 10.0
FETCH_PATH = "/api/peering/catalog/fetch"
TEXT_FIELD = {"task": "description", "idea": "body"}
NOTE_FIELDS = ("author", "agent_name", "body", "created_at")


class NotVisible(Exception):
    """Unbekannt oder nicht sichtbar → Route antwortet 404 (gleich, damit nichts verrät)."""


def _content(kind: str, raw: dict) -> dict:
    """Nur der Volltext-Teil: Beschreibung bzw. Ideentext (+ Anmerkungen)."""
    field = TEXT_FIELD[kind]
    content: dict = {field: str(raw.get(field) or "")[:proto.MAX_TEXT]}
    if kind == "idea":
        content["notes"] = [
            {f: n.get(f) for f in NOTE_FIELDS} for n in (raw.get("notes") or []) if isinstance(n, dict)
        ]
    return content


def _snapshot(row: dict) -> dict | None:
    try:
        data = json.loads(row.get("snapshot_body") or "")
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _result(row: dict, *, source: str, content: dict | None, peer: dict | None, online: bool) -> dict:
    item = _public({**row, "instance": row.get("peer_name"), "local": False})
    return {
        "item": item,
        "source": source,                       # live · snapshot · none
        "content": content,
        "snapshot_at": row.get("snapshot_at") if source == "snapshot" else None,
        "snapshot_stale": bool(row.get("snapshot_stale")) if source == "snapshot" else False,
        "origin": {"name": row.get("peer_name"), "online": online,
                   "last_seen": (peer or {}).get("last_seen")},
    }


def _offline(row: dict, peer: dict | None) -> dict:
    snap = _snapshot(row)
    return _result(row, source="snapshot" if snap else "none", content=snap, peer=peer, online=False)


async def open_remote(peer_id: str, kind: str, item_id: str, viewer: str, *, is_admin: bool) -> dict:
    row = await asyncio.to_thread(view_db.get_row, peer_id, kind, item_id)
    if row is None or (not is_admin and row["owner"] != viewer):
        raise NotVisible()
    peer = await asyncio.to_thread(peers_db.get_peer, peer_id)
    if not peer or peer["status"] != "active":
        return _offline(row, peer)
    payload = proto.new_catalog_fetch(kind, item_id, row["owner"])
    try:
        reply = await asyncio.wait_for(
            request_signed(peer, FETCH_PATH, payload, reply_kind="catalog_item", timeout=FETCH_TIMEOUT),
            timeout=FETCH_TIMEOUT,
        )
    except ReplyUnavailable:
        await asyncio.to_thread(audit, peer["name"], f"Nachladen {kind} {item_id[:8]}: Ursprung gibt nichts heraus")
        result = _offline(row, peer)
        result["origin"]["online"] = True       # erreichbar, gibt aber (gerade) nichts heraus
        return result
    except (asyncio.TimeoutError, httpx.HTTPError, proto.PeerRejected) as e:
        logger.info("Katalog: Nachladen von %s fehlgeschlagen: %s", peer["name"], e)
        return _offline(row, peer)
    item = reply.get("item") if isinstance(reply.get("item"), dict) else {}
    if (item.get("kind"), item.get("item_id"), item.get("owner")) != (kind, item_id, row["owner"]):
        await asyncio.to_thread(audit, peer["name"], f"Nachladen {kind} {item_id[:8]}: falscher Eintrag", severity="warning")
        return _offline(row, peer)
    content = _content(kind, item)
    try:
        meta = _valid_meta(item)       # gleiche Regeln wie beim Push (Status, Titel ≤ 300)
    except ValueError:
        meta = {}                      # ungültige Metadaten: nur den Snapshot speichern
    saved = await asyncio.to_thread(
        view_db.save_fetch, peer_id, kind, item_id, meta, json.dumps(content, ensure_ascii=False), now_iso(),
    )
    await asyncio.to_thread(peers_db.touch, peer_id)
    await asyncio.to_thread(audit, peer["name"], f"Nachladen {kind} {item_id[:8]} durch {viewer}")
    return _result(saved or row, source="live", content=content, peer=peer, online=True)


def open_local(kind: str, item_id: str, owner: str, viewer: str, *, is_admin: bool) -> dict:
    """Eigener Eintrag des Hubs, direkt aus der Modul-Quelle."""
    if not is_admin and owner != viewer:
        raise NotVisible()
    source = catalog_sources.get_source(kind)
    if source is None:
        raise NotVisible()
    try:
        full = source.get_full(owner, item_id)
    except Exception as e:
        logger.warning("Katalog: eigene Quelle %s nicht lesbar: %s", kind, e)
        raise NotVisible() from None
    if not isinstance(full, dict) or full.get("owner", owner) != owner:
        raise NotVisible()
    item = _public({**full, "kind": kind, "item_id": item_id, "owner": owner,
                    "peer_id": None, "instance": None, "local": True})
    return {"item": item, "source": "live", "content": _content(kind, full),
            "snapshot_at": None, "snapshot_stale": False,
            "origin": {"name": None, "online": True, "last_seen": None}}


async def open_item(peer_id: str, kind: str, item_id: str, viewer: str, *, is_admin: bool,
                    owner: str | None = None) -> dict:
    if kind not in TEXT_FIELD:
        raise NotVisible()
    if peer_id == LOCAL:
        return await asyncio.to_thread(open_local, kind, item_id, owner or viewer, viewer, is_admin=is_admin)
    return await open_remote(peer_id, kind, item_id, viewer, is_admin=is_admin)
