"""Hub: ``catalog_push`` annehmen (docs/specs/federation-catalog.md §Ablauf 3).

Prüfreihenfolge (Schritt 1 erledigt die Route mit ``verify_incoming``):
1. Absender gekoppelt + ``active``, Signatur gültig, ``issued_at`` frisch
2. ``catalog_accept = 1`` für diesen Partner, sonst ``peer_catalog_not_accepted``
3. ``seq`` > ``last_seq``, sonst ``peer_replay`` (mit ``last_seq``)
4. Rate-Limit (eigener Zähler, 30/min) und Größe (≤ 500 Einträge/Löschungen)
5. Felder einzeln: ungültige Einträge werden verworfen und gezählt

Audit (``errors_log``, Quelle ``federation.catalog``): jede Ablehnung mit Grund;
angenommene Pushes nur als Zahlen ohne Titel und nur, wenn sich etwas geändert
hat (leere Lebenszeichen alle 5 min würden das Log sonst fluten).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from hydrahive.db import errors_log
from hydrahive.db import federation_catalog_hub as hub_db
from hydrahive.db import federation_peers as peers_db
from hydrahive.db._utils import now_iso
from hydrahive.federation import catalog_notify
from hydrahive.federation import peer_protocol as proto

logger = logging.getLogger(__name__)

MAX_ITEMS = 500
MAX_TITLE = 300
MAX_ID = 128
MAX_TEXT_FIELD = 300
STATUSES = {
    "task": {"open", "in_progress", "done", "cancelled"},
    "idea": {"new", "review", "planned", "parked", "done", "dropped"},
}

_RATE_MAX = 30
_RATE_WINDOW_S = 60.0
_rate: dict[str, list[float]] = {}  # eigener Zähler, getrennt von peer_inbound (Aufträge)
_rate_lock = threading.Lock()       # accept_push läuft in Worker-Threads


class CatalogReplay(proto.PeerRejected):
    def __init__(self, last_seq: int) -> None:
        super().__init__("peer_replay", f"seq nicht neuer als {last_seq}")
        self.last_seq = last_seq


def audit(peer_name: str, message: str, *, severity: str = "info") -> None:
    try:
        errors_log.record(
            "federation.catalog", severity=severity, error_type="catalog_push", message=f"{peer_name}: {message}",
        )
    except Exception as e:  # Audit darf die Annahme nie kippen
        logger.warning("Katalog-Audit nicht geschrieben: %s", e)


def _rate_ok(peer_id: str) -> bool:
    now = time.monotonic()
    with _rate_lock:
        hits = [t for t in _rate.get(peer_id, []) if now - t < _RATE_WINDOW_S]
        ok = len(hits) < _RATE_MAX
        if ok:
            hits.append(now)
        _rate[peer_id] = hits
    return ok


def _opt_str(value: Any, limit: int = MAX_TEXT_FIELD) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError
    return value


def _opt_bool(value: Any) -> bool:
    """``shared``/``remote_edits`` aus dem Push (docs/specs/federation-shared-
    tasks.md §Schalter). Fehlend = False (ältere Clients ohne die Felder).
    Jeder andere Typ als bool/None lehnt den ganzen Push ab, wie bei den
    übrigen Feldern (peer_payload_invalid)."""
    if value is None:
        return False
    if not isinstance(value, bool):
        raise proto.PeerRejected("peer_payload_invalid", "shared/remote_edits muss bool sein")
    return value


def _req_str(value: Any, limit: int) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError
    return value


def _item(raw: Any) -> dict:
    """Ein Eintrag aus ``items`` → bereinigte Metadaten. ValueError(Grund) bei Fehler."""
    if not isinstance(raw, dict):
        raise ValueError("not_object")
    kind = raw.get("kind")
    if kind not in STATUSES:
        raise ValueError("kind_invalid")
    if raw.get("status") not in STATUSES[kind]:
        raise ValueError("status_invalid")
    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title_invalid")
    if len(title) > MAX_TITLE:
        raise ValueError("title_too_long")
    try:
        return {
            "kind": kind,
            "item_id": _req_str(raw.get("item_id"), MAX_ID),
            "owner": _req_str(raw.get("owner"), MAX_ID),
            "title": title,
            "status": raw["status"],
            "priority": _opt_str(raw.get("priority"), 32),
            "project_id": _opt_str(raw.get("project_id"), MAX_ID),
            "project_name": _opt_str(raw.get("project_name")),
            "created_at": _opt_str(raw.get("created_at"), 64),
            "updated_at": _req_str(raw.get("updated_at"), 64),
        }
    except ValueError:
        raise ValueError("field_invalid") from None


def _ref(raw: Any) -> tuple[str, str] | None:
    """(kind, item_id) aus einem Eintrag, soweit lesbar — für die Merkliste der Verworfenen."""
    if isinstance(raw, dict) and raw.get("kind") in STATUSES:
        item_id = raw.get("item_id")
        if isinstance(item_id, str) and item_id and len(item_id) <= MAX_ID:
            return raw["kind"], item_id
    return None


def _deleted(raw: Any) -> list[tuple[str, str]]:
    if not isinstance(raw, list):
        raise proto.PeerRejected("peer_payload_invalid", "deleted ist keine Liste")
    out = []
    for entry in raw:
        ref = _ref(entry)
        if ref:
            out.append(ref)
    return out


def _full_versions(raw: Any) -> dict[tuple[str, str], dict[str, str]] | None:
    """``{owner: {kind: [[id, updated_at], …]}}`` → {(owner, kind): {id: updated_at}}.

    Ganz oder gar nicht: Eine unlesbare Liste würde beim Abgleich sonst echte
    Einträge löschen. Deshalb lehnt sie die ganze Nachricht ab.
    """
    if raw is None:
        return None
    bad = proto.PeerRejected("peer_payload_invalid", "full_versions unlesbar")
    if not isinstance(raw, dict):
        raise bad
    out: dict[tuple[str, str], dict[str, str]] = {}
    for owner, kinds in raw.items():
        if not isinstance(owner, str) or not owner or len(owner) > MAX_ID or not isinstance(kinds, dict):
            raise bad
        for kind, pairs in kinds.items():
            if kind not in STATUSES or not isinstance(pairs, list):
                raise bad
            versions: dict[str, str] = {}
            for pair in pairs:
                if not (isinstance(pair, list) and len(pair) == 2):
                    raise bad
                try:
                    versions[_req_str(pair[0], MAX_ID)] = _req_str(pair[1], 64)
                except ValueError:
                    raise bad from None
            out[(owner, kind)] = versions
    return out


def accept_push(peer: dict, payload: dict) -> dict:
    """Schritte 2–5 + Verbuchen. Rückgabe ``{ack_seq, resync}``. Wirft PeerRejected."""
    if not peer.get("catalog_accept"):
        raise proto.PeerRejected("peer_catalog_not_accepted", "Katalog-Annahme für diesen Partner aus")
    seq = payload.get("seq")
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1 or seq > proto.MAX_INT:
        raise proto.PeerRejected("peer_payload_invalid", "seq fehlt")
    current = hub_db.last_seq(peer["id"])
    if seq <= current:
        raise CatalogReplay(current)
    if not _rate_ok(peer["id"]):
        raise proto.PeerRejected("peer_rate_limited", f"mehr als {_RATE_MAX} Katalog-Nachrichten/Minute")
    raw_items, raw_deleted = payload.get("items", []), payload.get("deleted", [])
    if not isinstance(raw_items, list):
        raise proto.PeerRejected("peer_payload_invalid", "items ist keine Liste")
    if len(raw_items) > MAX_ITEMS or (isinstance(raw_deleted, list) and len(raw_deleted) > MAX_ITEMS):
        raise proto.PeerRejected("peer_payload_too_large", f"mehr als {MAX_ITEMS} Einträge")
    deleted = _deleted(raw_deleted)
    full = _full_versions(payload.get("full_versions"))
    interval = payload.get("interval_seconds")
    interval = (interval if isinstance(interval, int) and not isinstance(interval, bool)
                and 0 < interval <= 86_400 else None)   # nur Anzeige („nicht aktuell“), groß = ungültig
    shared = _opt_bool(payload.get("shared"))
    remote_edits = _opt_bool(payload.get("remote_edits"))

    items, rejected, reasons = [], [], {}
    for raw in raw_items:
        try:
            items.append(_item(raw))
        except ValueError as e:
            reason = str(e) or "invalid"
            reasons[reason] = reasons.get(reason, 0) + 1
            ref = _ref(raw)
            if ref:
                updated = raw.get("updated_at") if isinstance(raw.get("updated_at"), str) else None
                rejected.append((*ref, updated, reason))
    try:
        res = hub_db.apply_push(
            peer["id"], seq=seq, interval_seconds=interval, now=now_iso(),
            items=items, deleted=deleted, rejected=rejected, full_versions=full,
            shared=shared, remote_edits=remote_edits,
        )
    except hub_db.SeqReplay as e:  # gleichzeitiger Push mit derselben seq
        raise CatalogReplay(e.last_seq) from e
    peers_db.touch(peer["id"])
    if res.upserted or res.deleted or res.pruned:
        catalog_notify.mark(exclude=peer["id"])   # Anstupsen (V7); der Absender kennt seine Änderung
    if res.upserted or res.deleted or res.pruned or reasons or res.resync:
        audit(peer["name"], (
            f"Push seq {seq} angenommen: {res.upserted} Einträge, {res.deleted} gelöscht, "
            f"{res.pruned} beim Abgleich entfernt, {sum(reasons.values())} verworfen {reasons or ''}, "
            f"{len(res.resync)} resync"
        ).rstrip())
    return {"ack_seq": seq, "resync": res.resync}
