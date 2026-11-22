"""Client: Volltext eines fremden Eintrags über den Hub holen (docs/specs/federation-shared-
tasks.md §Volltext nachladen für Clients: catalog_read). Aufgerufen über
``ModuleContext.catalog_foreign_get``.

- Nur Einträge, die in der eigenen Kopie stehen und dem Nutzer gehören (sonst ``None``).
- Signierte Anfrage ``catalog_read`` an den eigenen Hub, ohne ``seq`` und außerhalb der
  gemeinsamen Sperre. Die Antwort wird begrenzt gelesen und mit dem Schlüssel des Hubs
  geprüft (``request_signed``: MAX_REPLY_BYTES, ``catalog_item``, ``in_reply_to``).
- Der Volltext wird NICHT gespeichert, weder in der Kopie noch als Snapshot.
- Hub nicht erreichbar oder Antwort ungültig → Metadaten aus der Kopie mit
  ``source = "metadata"`` und ``hub_unreachable = True``. Hub sagt 404 (nicht mehr
  sichtbar) → ``None``.

``FullItem`` = ``{item, content, source, origin_offline, snapshot_at, last_seen,
hub_unreachable}``; ``item`` hat die Felder eines ForeignItem (ohne ``local_project_id``),
``content`` ist ``{description}`` (Task) bzw. ``{body, notes}`` (Idee) oder ``None``.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from hydrahive.db import federation_catalog_client as client_db
from hydrahive.db import federation_catalog_foreign as foreign_db
from hydrahive.federation import peer_protocol as proto
from hydrahive.federation.catalog_detail import _content
from hydrahive.federation.catalog_foreign import FIELDS, hub_stale
from hydrahive.federation.peer_outbound import ReplyUnavailable, request_signed

logger = logging.getLogger(__name__)

READ_PATH = "/api/peering/catalog/read"
TIMEOUT = 10.0                  # Hub wartet höchstens 8 s auf den Ursprung


def _from_mirror(row: dict, *, hub_unreachable: bool) -> dict:
    item = {**{f: row.get(f) for f in FIELDS}, "foreign": True, "origin_last_seen": row.get("origin_last_seen"),
            "stale": bool(row.get("stale")), "pending_edits": 0}
    return {"item": item, "content": None, "source": "metadata", "origin_offline": True,
            "snapshot_at": None, "last_seen": row.get("origin_last_seen"), "hub_unreachable": hub_unreachable}


def _from_reply(row: dict, reply: dict) -> dict | None:
    item = reply.get("item") if isinstance(reply.get("item"), dict) else {}
    if (item.get("kind"), item.get("item_id"), item.get("owner")) != (row["kind"], row["item_id"], row["owner"]):
        return None                                    # Hub liefert einen anderen Eintrag: verwerfen
    raw = reply.get("content")
    content = _content(row["kind"], raw) if isinstance(raw, dict) else None
    base = _from_mirror(row, hub_unreachable=False)
    base["item"].update({k: item[k] for k in ("title", "status", "priority", "updated_at")
                         if isinstance(item.get(k), str)})
    source = reply.get("source") if reply.get("source") in ("live", "snapshot", "none") else "none"
    return {**base, "content": content, "source": source, "origin_offline": bool(reply.get("origin_offline")),
            "snapshot_at": reply.get("snapshot_at") if isinstance(reply.get("snapshot_at"), str) else None,
            "last_seen": reply.get("last_seen") if isinstance(reply.get("last_seen"), str) else None}


async def foreign_get(kind: str, username: str, origin_fp: str, item_id: str) -> dict | None:
    """Wirft nie. ``None`` = nicht sichtbar (nicht in der Kopie, fremder Nutzer, Hub sagt 404)."""
    try:
        mode = foreign_db.mode()
        if mode == foreign_db.HUB:
            return await _on_hub(kind, username, origin_fp, item_id)
        if mode not in (foreign_db.CLIENT, foreign_db.CLIENT_OFFLINE):
            return None
        row = await asyncio.to_thread(foreign_db.mirror_row, kind, username, origin_fp, item_id)
        if row is None:
            return None
        row = {**row, "stale": bool(row.get("stale")) or await asyncio.to_thread(hub_stale, mode)}
        if mode == foreign_db.CLIENT_OFFLINE:            # Hub gesperrt/entfernt: Kopie mit Hinweis (AK G14)
            return _from_mirror(row, hub_unreachable=True)
        cfg = await asyncio.to_thread(client_db.load_config)
        if not (cfg.active and cfg.shared):
            return _from_mirror(row, hub_unreachable=True)
        payload = proto.new_catalog_read(origin_fp, kind, item_id, username)
        try:
            reply = await asyncio.wait_for(   # Gesamtzeit, nicht nur je httpx-Phase
                request_signed(cfg.hub, READ_PATH, payload, reply_kind="catalog_item", timeout=TIMEOUT),
                timeout=TIMEOUT + 2)
        except ReplyUnavailable:
            return None
        except (httpx.HTTPError, proto.PeerRejected, asyncio.TimeoutError) as e:
            logger.info("catalog_read: Hub nicht erreichbar oder Antwort ungültig: %s", e)
            return _from_mirror(row, hub_unreachable=True)
        return _from_reply(row, reply) or _from_mirror(row, hub_unreachable=True)
    except Exception as e:
        logger.warning("catalog_foreign_get(%s, %s) fehlgeschlagen: %s", kind, item_id, e)
        return None


async def _on_hub(kind: str, username: str, origin_fp: str, item_id: str) -> dict | None:
    """Auf dem Hub direkt beim Ursprung nachladen (Etappe 4, ``catalog_detail``), nur sichtbare
    Partner und nur der eigene Nutzername."""
    from hydrahive.federation import catalog_detail

    rows = await asyncio.to_thread(foreign_db.hub_rows, kind, username, None, None)
    row = next((r for r in rows if r["origin_fp"] == origin_fp and r["item_id"] == item_id), None)
    peer_id = await asyncio.to_thread(foreign_db.peer_id_for, origin_fp) if row else None
    if row is None or peer_id is None:
        return None
    try:
        result = await catalog_detail.open_remote(peer_id, kind, item_id, username, is_admin=False)
    except catalog_detail.NotVisible:
        return None
    reply = {"item": {**result["item"], "owner": username}, "content": result["content"],
             "source": result["source"], "origin_offline": not result["origin"]["online"] or result["source"] != "live",
             "snapshot_at": result.get("snapshot_at"), "last_seen": result["origin"].get("last_seen")}
    return _from_reply({**row, "stale": False}, reply)
