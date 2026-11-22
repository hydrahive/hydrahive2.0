"""Hub: ``catalog_pull`` beantworten (docs/specs/federation-shared-tasks.md
§Nachricht catalog_pull, §Schalter Bedingungen 1–5).

Prüfreihenfolge (Schritt 1 erledigt die Route mit ``verify_incoming``):
1. Absender gekoppelt + ``active``, Signatur gültig, ``issued_at`` frisch
2. ``catalog_accept = 1`` für C, sonst ``peer_catalog_not_accepted``
3. ``seq`` > ``last_seq`` (DERSELBE Zähler wie beim Push), sonst ``peer_replay``
4. Rate-Limit (gemeinsamer Zähler mit dem Push, 30/min)
5. Hub ``shared`` (Bedingung 1) und C meldet ``shared`` (Bedingung 3), sonst
   ``peer_catalog_not_shared``
6. Felder einzeln

Eine Seite enthält höchstens ``limit`` (≤ 500) Einträge und Löschungen zusammen,
bei ``full`` zusätzlich höchstens 5000 Schlüssel. Ist ``after_rev`` älter als das
aufgeräumte Löschprotokoll (``min_partial_rev``) und fragt C ohne ``full``, bekommt C
automatisch einen vollen Abgleich (``full: true`` in der Antwort, ab ``rev`` 0). Mit
``full`` blättert C normal weiter; fehlende Löschungen erledigt die Schlüsselliste.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from hydrahive.db import federation_catalog as catalog_db
from hydrahive.db import federation_catalog_hub as hub_db
from hydrahive.db import federation_catalog_pull as pull_db
from hydrahive.db import federation_catalog_revs as revs
from hydrahive.db import federation_peers as peers_db
from hydrahive.db._utils import now_iso
from hydrahive.federation import catalog_pull_own as own
from hydrahive.federation import peer_identity as ident
from hydrahive.federation import peer_protocol as proto
from hydrahive.federation.catalog_hub import CatalogReplay, _rate_ok, audit
from hydrahive.federation.catalog_plan import KINDS

MAX_LIMIT = 500
MAX_KEYS = 5000
# Seitenbudget nach Bytes (F2, Security-Review #742): Einträge, Löschungen und Schlüssel
# zusammen bleiben unter der Lesegrenze des Clients (peer_outbound.MAX_REPLY_BYTES), auch
# bei langen Titeln. 64 KB Reserve für Umschlag und ``instances``. Bei ``full`` bekommen
# Einträge höchstens die Hälfte, die Schlüsselliste den Rest.
PAGE_BYTES = 4 * proto.MAX_TEXT
MAX_USERS = 200
MAX_NAME = 64
DEFAULT_INTERVAL = 300
_ITEM_FIELDS = ("origin_fp", "origin_name", "kind", "item_id", "owner", "title", "status",
                "priority", "project_id", "project_name", "created_at", "updated_at")


def _int(value: Any, name: str, *, low: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < low or value > proto.MAX_INT:
        raise proto.PeerRejected("peer_payload_invalid", f"{name} ungültig")
    return value


def _users(raw: Any) -> list[str]:
    if not isinstance(raw, list) or len(raw) > MAX_USERS:
        raise proto.PeerRejected("peer_payload_invalid", "users ungültig")
    if not all(isinstance(u, str) and 0 < len(u) <= MAX_NAME for u in raw):
        raise proto.PeerRejected("peer_payload_invalid", "users ungültig")
    return sorted(set(raw))


def _cursor(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list) and len(raw) == 2 and all(isinstance(x, str) and len(x) <= 128 for x in raw):
        return raw
    raise proto.PeerRejected("peer_payload_invalid", "Cursor ungültig")


def _local_after(raw: Any) -> dict:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise proto.PeerRejected("peer_payload_invalid", "local_after ungültig")
    return {k: _cursor(raw.get(k)) for k in KINDS}


def _keys_after(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list) and len(raw) == 3 and all(isinstance(x, str) and len(x) <= 128 for x in raw):
        return raw
    raise proto.PeerRejected("peer_payload_invalid", "keys_after ungültig")


def check(peer: dict, payload: dict) -> int:
    """Schritte 2–5. Rückgabe ``seq``. Wirft PeerRejected (an C)."""
    if not peer.get("catalog_accept"):
        raise proto.PeerRejected("peer_catalog_not_accepted", "Katalog-Annahme für diesen Partner aus")
    seq = _int(payload.get("seq"), "seq", low=1)
    current = hub_db.last_seq(peer["id"])
    if seq <= current:
        raise CatalogReplay(current)
    if not _rate_ok(peer["id"]):
        raise proto.PeerRejected("peer_rate_limited", "mehr als 30 Katalog-Nachrichten/Minute")
    if not catalog_db.get_settings().get("shared"):
        raise proto.PeerRejected("peer_catalog_not_shared", "Gemeinsame Taskpflege auf dem Hub aus")
    if not pull_db.client_shared(peer["id"]):
        raise proto.PeerRejected("peer_catalog_not_shared", "Gemeinsame Taskpflege beim Client aus")
    return seq


def _instances(peer: dict, now: datetime) -> list[dict]:
    out = [{"origin_fp": own.own_fp(), "origin_name": None, "last_seen": now_iso(), "stale": False}]
    for r in pull_db.instances(peer["id"]):
        last = _parse(r["last_push_at"])
        interval = r["interval_seconds"] or DEFAULT_INTERVAL
        out.append({
            "origin_fp": r["origin_fp"], "origin_name": r["origin_name"], "last_seen": r["last_seen"],
            "stale": last is None or (now - last).total_seconds() > 2 * interval,
        })
    return out


def _parse(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def size(value: Any) -> int:
    """Bytes in der Antwort (wie JSONResponse: kompakt, UTF-8 ohne ASCII-Escape) plus Komma."""
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) + 1


def _public_entry(tag: str, r: dict) -> dict:
    if tag == "d":
        return {"origin_fp": r["origin_fp"], "kind": r["kind"], "item_id": r["item_id"]}
    return {f: r.get(f) for f in _ITEM_FIELDS}


def _page(peer: dict, users: list[str], after_rev: int, local_after: dict, limit: int, budget: int) -> dict:
    """Partner-Einträge und Löschungen nach ``rev``, dann eigene Einträge im Rest.
    Höchstens ``limit`` Stück und ``budget`` Bytes (mindestens ein Eintrag, damit es weitergeht)."""
    upto = pull_db.current_rev()
    found = pull_db.items_after(peer["id"], users, after_rev, upto, limit + 1)
    dels = pull_db.deletions_after(peer["fingerprint"], users, after_rev, upto, limit + 1)
    merged = sorted([("i", r) for r in found] + [("d", r) for r in dels], key=lambda e: e[1]["rev"])
    more = len(merged) > limit
    merged = merged[:limit]
    used, kept = 0, []
    for tag, r in merged:
        entry = _public_entry(tag, r)
        n = size(entry)
        if kept and used + n > budget:
            more = True
            break
        kept.append((tag, r["rev"], entry))
        used += n
    next_rev = kept[-1][1] if more else max(upto, after_rev)
    items = [e for t, _, e in kept if t == "i"]
    deleted = [e for t, _, e in kept if t == "d"]
    own_items, local_next, own_more = own.changes(users, local_after, limit - len(kept),
                                                  max(0, budget - used), size=size)
    items += [{f: r.get(f) for f in _ITEM_FIELDS} for r in own_items]
    used += sum(size({f: r.get(f) for f in _ITEM_FIELDS}) for r in own_items)
    return {"items": items, "deleted": deleted, "next_rev": next_rev, "local_next": local_next,
            "more": more or own_more, "_partner_changes": bool(kept), "_bytes": used}


def _full_keys(peer: dict, users: list[str], keys_after: list[str] | None,
               budget: int) -> tuple[list, list | None]:
    """Eine Seite der vollständigen Schlüsselliste (≤ 5000 Stück, ≤ ``budget`` Bytes) und der
    Cursor der nächsten."""
    try:
        mine = own.keys(users)
    except Exception as e:  # unvollständige Liste würde beim Client Einträge löschen
        raise proto.PeerRejected("peer_local_failed", f"Katalog-Quelle fehlgeschlagen: {e}") from e
    keys = sorted(pull_db.visible_keys(peer["id"], users) + mine)
    if keys_after is not None:
        keys = [k for k in keys if k[:3] > keys_after]
    page: list = []
    used = 0
    for k in keys[:MAX_KEYS]:
        n = size(k)
        if page and used + n > budget:
            break
        page.append(k)
        used += n
    return page, (page[-1][:3] if len(keys) > len(page) else None)


def accept_pull(peer: dict, payload: dict) -> tuple[dict, dict[str, str]]:
    """Geprüfte Anfrage beantworten. Rückgabe: (signierte Antwort, Header). Wirft PeerRejected."""
    seq = check(peer, payload)
    users = _users(payload.get("users"))
    after_rev = _int(payload.get("after_rev", 0), "after_rev")
    local_after = _local_after(payload.get("local_after"))
    full = payload.get("full") is True
    limit = min(_int(payload.get("limit", MAX_LIMIT), "limit", low=1), MAX_LIMIT)
    keys_after = _keys_after(payload.get("keys_after"))
    if after_rev and after_rev < revs.min_partial_rev() and not full:
        # Löschprotokoll schon aufgeräumt: voller Abgleich ab 0. Nur wenn der Client noch
        # keinen vollen Abgleich fährt. Folgeseiten kommen mit full=true und eigenem after_rev,
        # sonst stünde jede Folgeseite wieder bei 0 (Endlosschleife, Review #742).
        after_rev, full = 0, True
    body = _page(peer, users, after_rev, local_after, limit, PAGE_BYTES // 2 if full else PAGE_BYTES)
    keys_next = None
    body["full_keys"] = None
    used = body.pop("_bytes")
    if full:
        body["full_keys"], keys_next = _full_keys(peer, users, keys_after, PAGE_BYTES - used)
        body["more"] = body["more"] or keys_next is not None
    try:
        reset = pull_db.record_pull(peer["id"], seq, users, now_iso(),
                                    local_empty=not any(local_after.values()))
    except hub_db.SeqReplay as e:  # gleichzeitige Nachricht mit derselben seq
        raise CatalogReplay(e.last_seq) from e
    peers_db.touch(peer["id"])
    body.update(full=full, keys_next=keys_next, reset_local=reset,
                instances=_instances(peer, datetime.now(timezone.utc)), ack_seq=seq)
    if body.pop("_partner_changes") or full:   # eigene Einträge wiederholen die letzte Zeitstufe
        audit(peer["name"], f"Abholen seq {seq}: {len(body['items'])} Einträge, "
                            f"{len(body['deleted'])} Löschungen{' (voll)' if full else ''}")
    reply = proto.new_catalog_items(payload["msg_id"], body)
    return reply, {proto.HEADER_SIGNATURE: ident.sign(reply)}
