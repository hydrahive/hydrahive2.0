"""Hub: ``catalog_read`` beantworten (docs/specs/federation-shared-tasks.md §Volltext nachladen
für Clients). Client C fragt den Volltext eines Eintrags von Ursprung O.

Prüfung (Schritt 1 = Signatur, Frische, Typ, ``msg_id`` erledigt die Route mit verify_incoming):
2. ``msg_id`` neu (Replay im Speicher, wie catalog_fetch), Rate-Limit 30/min je Client
3. Verteilregel: Hub ``shared``, C ``catalog_accept`` + ``active`` + meldet ``shared``
   (``catalog_pull.check`` ohne seq), O sichtbar (Bedingung 2) bzw. O ist der Hub selbst,
   C ≠ O, ``owner`` steht in den ``pull_users`` von C
4. Eintrag existiert im Katalog (bzw. in der eigenen Quelle) und gehört ``owner``

Jeder Fehler → nach außen 404 (``Unavailable``), Grund nur ins Audit. Danach lädt der Hub
über das bestehende catalog_fetch beim Ursprung nach (Timeout 8 s, aktualisiert den
Snapshot) bzw. liest eigene Einträge über ``get_full``. Ist O offline, antwortet er mit dem
Snapshot und ``origin_offline: true``, ``snapshot_at``, ``last_seen``.
"""
from __future__ import annotations

import asyncio
import json
import threading
import time

from hydrahive.db import federation_catalog as catalog_db
from hydrahive.db import federation_catalog_pull as pull_db
from hydrahive.db.connection import db
from hydrahive.federation import catalog_detail, peer_identity as ident
from hydrahive.federation import peer_protocol as proto
from hydrahive.federation.catalog_origin import Unavailable
from hydrahive.federation.catalog_pull_own import own_fp

READ_TIMEOUT = 8.0           # catalog_fetch beim Ursprung; die Gesamtantwort bleibt unter 10 s
_RATE_MAX, _RATE_WINDOW = 30, 60.0
_lock = threading.Lock()
_seen: dict[str, float] = {}             # gleiche Single-Worker-Annahme wie catalog_origin
_rate: dict[str, list[float]] = {}


def _remember(msg_id: str) -> bool:
    now = time.monotonic()
    with _lock:
        for key in [k for k, until in _seen.items() if until <= now]:
            del _seen[key]
        if msg_id in _seen:
            return False
        _seen[msg_id] = now + proto.MAX_AGE_SECONDS + proto.MAX_SKEW_SECONDS
        return True


def _rate_ok(peer_id: str) -> bool:
    now = time.monotonic()
    with _lock:
        hits = [t for t in _rate.get(peer_id, []) if now - t < _RATE_WINDOW]
        ok = len(hits) < _RATE_MAX
        _rate[peer_id] = hits + ([now] if ok else [])
        return ok


def _fields(payload: dict) -> tuple[str, str, str, str]:
    values = tuple(payload.get(k) for k in ("origin_fp", "item_kind", "item_id", "owner"))
    if not all(isinstance(v, str) and 0 < len(v) <= 128 for v in values) or values[1] not in ("task", "idea"):
        raise Unavailable("payload_invalid")
    return values  # type: ignore[return-value]


def _client_ok(peer: dict, owner: str) -> None:
    if not peer.get("catalog_accept"):
        raise Unavailable("peer_catalog_not_accepted")
    if not catalog_db.get_settings().get("shared") or not pull_db.client_shared(peer["id"]):
        raise Unavailable("peer_catalog_not_shared")
    with db() as conn:
        row = conn.execute("SELECT pull_users FROM federation_catalog_sources WHERE peer_id = ?",
                           (peer["id"],)).fetchone()
    try:
        users = json.loads(row["pull_users"]) if row and row["pull_users"] else []
    except ValueError:
        users = []
    if owner not in users:
        raise Unavailable("user_not_pulled")


def _origin_peer(origin_fp: str, client: dict) -> dict:
    """Partner O, sichtbar nach Bedingung 2 und ≠ C."""
    with db() as conn:
        row = conn.execute(
            "SELECT p.* FROM federation_peers p LEFT JOIN federation_catalog_sources s ON s.peer_id = p.id "
            "WHERE replace(p.fingerprint, ' ', '') = ? AND p.catalog_accept = 1 AND p.status = 'active' "
            "AND COALESCE(s.shared, 0) = 1", (origin_fp.replace(" ", ""),),
        ).fetchone()
    if row is None or row["id"] == client["id"]:
        raise Unavailable("origin_not_visible")
    return dict(row)


def _check(peer: dict, payload: dict) -> tuple[str, str, str, str]:
    if not _remember(payload["msg_id"]):
        raise Unavailable("peer_replay")
    if not _rate_ok(peer["id"]):
        raise Unavailable("peer_rate_limited")
    fields = _fields(payload)
    _client_ok(peer, fields[3])
    return fields


async def answer_read(peer: dict, payload: dict) -> tuple[dict, dict[str, str]]:
    """Geprüfte Anfrage beantworten: (signierte Antwort, Header). Wirft Unavailable (→ 404)."""
    origin_fp, kind, item_id, owner = await asyncio.to_thread(_check, peer, payload)
    if origin_fp.replace(" ", "") == own_fp().replace(" ", ""):
        result = await asyncio.to_thread(_own, kind, item_id, owner)
    else:
        origin = await asyncio.to_thread(_origin_peer, origin_fp, peer)
        result = await _remote(origin, kind, item_id, owner)
    item = {**result["item"], "origin_fp": origin_fp}
    body = {"item": item, "content": result["content"], "source": result["source"],
            "origin_offline": not result["origin"]["online"] or result["source"] != "live",
            "snapshot_at": result.get("snapshot_at"), "last_seen": result["origin"].get("last_seen")}
    reply = proto.new_catalog_item(payload["msg_id"], body)
    return reply, {proto.HEADER_SIGNATURE: ident.sign(reply)}


def _own(kind: str, item_id: str, owner: str) -> dict:
    from hydrahive.db import federation_catalog as cfg_db
    if owner not in cfg_db.list_selected_users():
        raise Unavailable("user_not_selected")
    try:
        result = catalog_detail.open_local(kind, item_id, owner, owner, is_admin=False)
    except catalog_detail.NotVisible:
        raise Unavailable("unknown") from None
    if result["item"].get("project_id") in set(cfg_db.list_excluded_projects()):
        raise Unavailable("project_excluded")
    return result


async def _remote(origin: dict, kind: str, item_id: str, owner: str) -> dict:
    row = await asyncio.to_thread(catalog_detail.view_db.get_row, origin["id"], kind, item_id)
    if row is None or row["owner"] != owner:
        raise Unavailable("unknown")
    try:
        return await catalog_detail.open_remote(origin["id"], kind, item_id, owner, is_admin=False,
                                                timeout=READ_TIMEOUT)
    except catalog_detail.NotVisible:
        raise Unavailable("unknown") from None


def _reset_for_tests() -> None:
    with _lock:
        _seen.clear()
        _rate.clear()
