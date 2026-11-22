"""Hub: eigene Einträge für ``catalog_pull`` (docs/specs/federation-shared-tasks.md
§Änderungsnummer „Eigene Einträge des Hubs“).

Eigene Einträge stehen nie in ``federation_catalog_items``. Sie werden über die
Katalog-Quellen gelesen, mit einem Cursor je Art beim Client (``local_after``),
gleiches Format wie beim Push: ``(updated_at, item_id)``, verglichen nur
innerhalb derselben Art. Es gelten die Nutzerauswahl und die ausgeschlossenen
Projekte des Hubs (dieselben Tabellen wie auf einem Client), dazu die
Nutzerliste von C (Bedingung 4).
"""
from __future__ import annotations

import logging

from hydrahive.db import federation_catalog as catalog_db
from hydrahive.federation import peer_identity as ident
from hydrahive.federation.catalog_plan import KINDS, meta
from hydrahive.modules import catalog_sources

logger = logging.getLogger(__name__)


def own_fp() -> str:
    return ident.fingerprint(ident.public_key_b64())


def _scope(users: list[str]) -> tuple[list[str], set[str]]:
    selected = set(catalog_db.list_selected_users())
    return sorted(selected & set(users)), set(catalog_db.list_excluded_projects())


def _key(row: dict) -> tuple[str, str]:
    return (str(row["updated_at"]), str(row["item_id"]))


def changes(users: list[str], local_after: dict, budget: int, byte_budget: int | None = None,
            *, size=None) -> tuple[list[dict], dict, bool]:
    """Geänderte eigene Einträge nach ``local_after``.

    Rückgabe ``(items, local_next, more)``. ``local_next[kind]`` richtet sich nach
    dem höchsten gelesenen Eintrag, auch wenn er wegen eines ausgeschlossenen
    Projekts nicht mitgeht (sonst bliebe der Cursor dort stehen). Eine Art ohne
    Quelle oder mit kaputter Quelle behält ihren alten Cursor. ``byte_budget`` mit
    ``size(entry)``: zusätzlich höchstens so viele Bytes (F2), gemessen wie in der Antwort.
    """
    owners, excluded = _scope(users)
    fp = own_fp()
    items: list[dict] = []
    local_next = {k: local_after.get(k) for k in KINDS}
    more = False
    bytes_left = byte_budget
    for kind in KINDS:
        left = budget - len(items)
        source = catalog_sources.get_source(kind)
        if source is None or not owners:
            continue
        if left <= 0:
            more = True
            continue
        after = tuple(local_after[kind]) if local_after.get(kind) else None
        try:
            rows = _merged(source, owners, after, left + 1, kind)
        except Exception as e:  # kaputte Quelle: Art auslassen, Cursor bleibt
            logger.warning("catalog_pull: Quelle %s fehlgeschlagen: %s", kind, e)
            continue
        cut = len(rows) > left
        if cut:
            rows, more = rows[:left], True
        kept_rows = []
        for row in rows:
            if row.get("project_id") not in excluded:
                entry = {**row, "origin_fp": fp, "origin_name": None}
                if bytes_left is not None and size is not None:
                    n = size(entry)
                    if (items or kept_rows) and n > bytes_left:
                        cut = more = True
                        break
                    bytes_left -= n
                items.append(entry)
            kept_rows.append(row)
        rows = kept_rows
        if rows:
            # Mitten im Blättern genau weiter (Keyset). Ist die Art durch, geht die
            # letzte Zeitstufe beim nächsten Abholen noch einmal mit (wie beim Push:
            # Tasks sind nur sekundengenau). Der Client übernimmt nur, was neuer ist.
            local_next[kind] = list(_key(rows[-1])) if cut else [rows[-1]["updated_at"], ""]
    return items, local_next, more


def _merged(source, owners: list[str], after, limit: int, kind: str) -> list[dict]:
    """Je Nutzer ``list_changed`` und zusammengeführt nach ``(updated_at, item_id)``."""
    rows: list[dict] = []
    for username in owners:
        for raw in source.list_changed(username, after, limit) or []:
            item = meta(raw, kind, username)
            if item is not None:
                rows.append(item)
    rows.sort(key=_key)
    return rows[:limit]


def keys(users: list[str]) -> list[list[str]]:
    """Alle sichtbaren eigenen Schlüssel ``[own_fp, kind, item_id, updated_at]`` (für ``full_keys``).

    Wirft, wenn eine Quelle scheitert: Eine unvollständige Liste würde beim
    Client sonst Einträge löschen (gleiche Regel wie beim Abgleich des Pushs).
    """
    owners, excluded = _scope(users)
    fp = own_fp()
    out: list[list[str]] = []
    for kind in KINDS:
        source = catalog_sources.get_source(kind)
        if source is None:
            continue
        for username in owners:
            for v in source.list_versions(username) or []:
                if len(v) >= 3 and v[0] and v[1] and v[2] not in excluded:
                    out.append([fp, kind, str(v[0]), str(v[1])])
    return out
