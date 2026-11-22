"""Ursprung (Client): ``catalog_fetch`` des eigenen Hubs beantworten.

docs/specs/federation-catalog.md §Ablauf 4. Der Hub fragt den Volltext eines
Eintrags an, der Client antwortet synchron und selbst signiert. Herausgegeben
wird nur, wenn ALLES stimmt:

- Absender gekoppelt, ``active``, Signatur gültig, frisch (``verify_incoming``)
- Absender ist **unser Hub** (``is_hub = 1``)            sonst Audit ``peer_not_hub``
- Katalog-Sync ``enabled``                              sonst ``peer_catalog_disabled``
- ``msg_id`` noch nicht gesehen (Speicher, MAX_AGE_SECONDS) sonst ``peer_replay``
- höchstens 60 Anfragen/Minute                          sonst ``peer_rate_limited``
- ``owner`` ausgewählt, Art bekannt, Eintrag existiert und gehört ``owner``,
  Projekt nicht ausgeschlossen                           sonst ``item_unavailable``

Nach außen gibt es in jedem Fehlerfall dieselbe Antwort: ``404`` ohne Code.
Ob es den Eintrag gibt, verrät der Client nie. Der Grund steht nur im Audit.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from hydrahive.db import federation_catalog_client as client_db
from hydrahive.federation import peer_identity as ident
from hydrahive.federation import peer_protocol as proto
from hydrahive.federation.catalog_hub import audit
from hydrahive.modules import catalog_sources

KINDS = ("task", "idea")
TEXT_FIELD = {"task": "description", "idea": "body"}
META_FIELDS = ("kind", "item_id", "owner", "title", "status", "priority",
               "project_id", "project_name", "created_at", "updated_at")
NOTE_FIELDS = ("author", "agent_name", "body", "created_at")
_RATE_MAX = 60
_RATE_WINDOW_S = 60.0

# Replay-Schutz und Rate-Limit liegen bewusst im Prozessspeicher (Spec: „im Speicher“).
# Annahme: genau EIN uvicorn-Prozess (installer/modules/50-systemd.sh:106, ohne --workers).
# Bei mehreren Workern gälte der Schutz nur je Worker, dann in SQLite auslagern.
# Nach einem Neustart ist eine abgefangene Anfrage im 5-min-Fenster wieder gültig
# (Security-Review #738, LOW, akzeptiert).
_lock = threading.Lock()
_seen: dict[str, float] = {}       # msg_id → läuft ab (monotonic)
_rate: list[float] = []            # nur der eine Hub fragt an, ein Zähler reicht


class Unavailable(Exception):
    """Nach außen immer 404. ``reason`` geht nur ins Audit."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _remember(msg_id: str) -> bool:
    """msg_id merken. False = schon gesehen (Wiederholung)."""
    now = time.monotonic()
    with _lock:
        for key in [k for k, until in _seen.items() if until <= now]:
            del _seen[key]
        if msg_id in _seen:
            return False
        _seen[msg_id] = now + proto.MAX_AGE_SECONDS + proto.MAX_SKEW_SECONDS
        return True


def _rate_ok() -> bool:
    now = time.monotonic()
    with _lock:
        _rate[:] = [t for t in _rate if now - t < _RATE_WINDOW_S]
        if len(_rate) >= _RATE_MAX:
            return False
        _rate.append(now)
        return True


def _truncate(full: dict, kind: str) -> dict:
    """Metadaten + Text (+ Anmerkungen bei Ideen), zusammen höchstens MAX_TEXT Zeichen."""
    item = {f: full.get(f) for f in META_FIELDS}
    budget = proto.MAX_TEXT
    field = TEXT_FIELD[kind]
    text = str(full.get(field) or "")[:budget]
    budget -= len(text)
    item[field] = text
    if kind == "idea":
        notes: list[dict] = []
        for note in full.get("notes") or []:
            if not isinstance(note, dict) or budget <= 0:
                break
            body = str(note.get("body") or "")[:budget]
            budget -= len(body)
            notes.append({**{f: note.get(f) for f in NOTE_FIELDS}, "body": body})
        item["notes"] = notes
    return item


def _lookup(cfg: client_db.SyncConfig, payload: dict) -> dict:
    kind, item_id, owner = payload.get("item_kind"), payload.get("item_id"), payload.get("owner")
    if kind not in KINDS or not isinstance(item_id, str) or not item_id or not isinstance(owner, str):
        raise Unavailable("payload_invalid")
    if owner not in cfg.users:
        raise Unavailable("user_not_selected")
    source = catalog_sources.get_source(kind)
    if source is None:
        raise Unavailable("no_source")
    try:
        full = source.get_full(owner, item_id)
    except Exception:
        raise Unavailable("source_failed") from None
    if not isinstance(full, dict):
        raise Unavailable("unknown")
    if full.get("owner", owner) != owner or full.get("item_id", item_id) != item_id:
        raise Unavailable("not_owner")
    if full.get("project_id") in cfg.excluded_projects:
        raise Unavailable("project_excluded")
    return _truncate({**full, "kind": kind, "item_id": item_id, "owner": owner}, kind)


def answer_fetch(peer: dict, payload: dict) -> tuple[dict, dict[str, str]]:
    """Geprüfte Anfrage (Schritt 1 erledigt die Route) beantworten.

    Rückgabe: (signierte Antwort, Header). Wirft Unavailable → Route antwortet 404.
    """
    cfg = client_db.load_config()
    if not peer.get("is_hub") or not cfg.hub or cfg.hub.get("id") != peer.get("id"):
        raise Unavailable("peer_not_hub")
    if not cfg.enabled:
        raise Unavailable("peer_catalog_disabled")
    if not _remember(payload["msg_id"]):
        raise Unavailable("peer_replay")
    if not _rate_ok():
        raise Unavailable("peer_rate_limited")
    item = _lookup(cfg, payload)
    reply = proto.new_catalog_item(payload["msg_id"], item)
    audit(peer["name"], f"Nachladen {item['kind']} {item['item_id'][:8]} für {item['owner']} beantwortet")
    return reply, {proto.HEADER_SIGNATURE: ident.sign(reply)}


def describe(payload: Any) -> str:
    """Kurzbeschreibung einer Anfrage fürs Audit (ohne Inhalte)."""
    if not isinstance(payload, dict):
        return "?"
    item_id = payload.get("item_id")
    short = item_id[:8] if isinstance(item_id, str) else "?"
    return f"{payload.get('item_kind')!s:.8} {short} owner={payload.get('owner')!s:.64}"


def _reset_for_tests() -> None:
    with _lock:
        _seen.clear()
        _rate.clear()
