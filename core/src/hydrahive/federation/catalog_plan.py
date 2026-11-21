"""Client: was ein Katalog-Lauf schickt (docs/specs/federation-catalog.md §Ablauf 2).

Reine Planung ohne Netz. Liest die Modul-Quellen über
``catalog_sources.get_source(kind)`` und baut daraus Einträge, Löschungen,
Abgleichsliste und die Cursor, die NACH vollständigem Ack gesetzt werden.

Cursor je Nutzer und Art: ab ``updated_at >= cursor`` (die letzte Zeitstufe geht
absichtlich noch einmal mit, Tasks sind nur sekundengenau), innerhalb des Laufs
per Keyset ``(updated_at, item_id)`` geblättert. ``updated_at`` wird nur
innerhalb derselben Art verglichen, nie über Arten hinweg.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from hydrahive.db import federation_catalog_client as client_db
from hydrahive.modules import catalog_sources

logger = logging.getLogger(__name__)

KINDS = ("task", "idea")
PAGE = 500                 # Einträge je Nachricht und je Abfrage (Spec: höchstens 500)
MAX_PAGES = 2_000          # Sicherung gegen eine Quelle, die nie endet
MAX_TITLE = 300
META_FIELDS = ("kind", "item_id", "owner", "title", "status", "priority",
               "project_id", "project_name", "created_at", "updated_at")

Message = tuple[list[dict], list[dict], "dict | None"]  # (items, deleted, full_versions)


@dataclass
class Plan:
    items: list[dict] = field(default_factory=list)
    deleted: list[dict] = field(default_factory=list)
    cursors: dict[tuple[str, str], str] = field(default_factory=dict)
    full_versions: dict | None = None
    problems: list[str] = field(default_factory=list)


def meta(row: object, kind: str, username: str) -> dict | None:
    """Genau die Metadaten der Spec. Fremde Art/fremder Besitzer → verworfen."""
    if not isinstance(row, dict) or not row.get("item_id") or not row.get("updated_at"):
        return None
    if row.get("kind", kind) != kind or row.get("owner", username) != username:
        return None
    out = {f: row.get(f) for f in META_FIELDS}
    out.update(kind=kind, owner=username, title=str(out.get("title") or "")[:MAX_TITLE])
    return out


def _collect_changed(cfg: client_db.SyncConfig, pairs: set[tuple[str, str]], plan: Plan) -> None:
    cursors = client_db.get_cursors()
    for username, kind in sorted(pairs):
        source = catalog_sources.get_source(kind)
        if source is None:
            continue
        cursor = cursors.get((username, kind))
        after = (cursor, "") if cursor else None   # (c, "") heißt: updated_at >= c
        highest: str | None = None
        found: list[dict] = []
        try:
            for _ in range(MAX_PAGES):
                rows = source.list_changed(username, after, PAGE) or []
                for row in rows:
                    item = meta(row, kind, username)
                    if item is None:
                        continue
                    if highest is None or item["updated_at"] > highest:
                        highest = item["updated_at"]
                    if item["project_id"] not in cfg.excluded_projects:
                        found.append(item)
                if len(rows) < PAGE:
                    break
                after = (rows[-1]["updated_at"], rows[-1]["item_id"])
        except Exception as e:  # kaputte Quelle: diese Art auslassen, ihr Cursor bleibt stehen
            logger.warning("Katalog-Sync: Quelle %s für %s fehlgeschlagen: %s", kind, username, e)
            plan.problems.append(f"source_failed:{kind}")
            continue
        plan.items.extend(found)
        if highest is not None:
            plan.cursors[(username, kind)] = highest


def _collect_full(cfg: client_db.SyncConfig, plan: Plan) -> None:
    """Abgleich: (item_id, updated_at) je Nutzer und Art, gefiltert wie der Push.

    Scheitert eine Quelle, geht in diesem Lauf KEINE Liste raus — der Hub würde
    sonst alle Einträge dieser Art löschen.
    """
    full: dict[str, dict[str, list[list[str]]]] = {}
    for username in cfg.users:
        full[username] = {}
        for kind in KINDS:
            source = catalog_sources.get_source(kind)
            if source is None:
                continue
            try:
                versions = source.list_versions(username) or []
            except Exception as e:
                logger.warning("Katalog-Sync: Abgleich %s für %s fehlgeschlagen: %s", kind, username, e)
                plan.problems.append(f"source_failed:{kind}")
                return
            full[username][kind] = [
                [str(v[0]), str(v[1])] for v in versions
                if len(v) >= 3 and v[0] and v[1] and v[2] not in cfg.excluded_projects
            ]
    plan.full_versions = full


def _collect_deleted(cfg: client_db.SyncConfig, entries: list[tuple[str, str, str]], plan: Plan) -> None:
    """Event-Push: gemeldete Einträge, die weg sind oder jetzt in einem
    ausgeschlossenen Projekt liegen, sofort als ``deleted`` (nur Art + ID)."""
    seen: set[tuple[str, str]] = set()
    for kind, username, item_id in entries:
        source = catalog_sources.get_source(kind)
        if source is None or (kind, item_id) in seen:
            continue
        try:
            full = source.get_full(username, item_id)
        except Exception:
            continue
        if full is None or (isinstance(full, dict) and full.get("project_id") in cfg.excluded_projects):
            seen.add((kind, item_id))
            plan.deleted.append({"kind": kind, "item_id": item_id})


def build_plan(
    cfg: client_db.SyncConfig,
    *,
    pairs: set[tuple[str, str]],
    entries: list[tuple[str, str, str]] | tuple = (),
    full: bool = False,
) -> Plan:
    plan = Plan()
    _collect_deleted(cfg, list(entries), plan)
    _collect_changed(cfg, pairs, plan)
    if full:
        _collect_full(cfg, plan)
    return plan


def messages(plan: Plan, *, heartbeat: bool) -> list[Message]:
    """Nachrichten zu höchstens PAGE Einträgen bzw. Löschungen.

    Leerer Plan: eine leere Nachricht nur als Lebenszeichen (Timer) oder für den
    Abgleich. Die Abgleichsliste hängt an der LETZTEN Nachricht, dann hat der Hub
    die Einträge des Laufs schon.
    """
    chunks = [plan.items[i:i + PAGE] for i in range(0, len(plan.items), PAGE)]
    dels = [plan.deleted[i:i + PAGE] for i in range(0, len(plan.deleted), PAGE)]
    count = max(len(chunks), len(dels))
    if count == 0 and (heartbeat or plan.full_versions is not None):
        count = 1
    out: list[Message] = [
        (chunks[i] if i < len(chunks) else [], dels[i] if i < len(dels) else [], None) for i in range(count)
    ]
    if out and plan.full_versions is not None:
        items, deleted, _ = out[-1]
        out[-1] = (items, deleted, plan.full_versions)
    return out
