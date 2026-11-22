"""Hub: Ausschluss bei PUT /api/federation/catalog/settings
(docs/specs/federation-shared-tasks.md §Schalter "Der Hub schließt bei sich
etwas aus").

Nutzer abgewählt oder Projekt neu ausgeschlossen: Löschzeilen für die
betroffenen EIGENEN Einträge des Hubs, ermittelt über die Katalog-Quellen
(``list_versions`` liefert ``(item_id, updated_at, project_id)`` je Nutzer —
dasselbe Feld, das ``catalog_plan._collect_full`` für den Abgleich nutzt).
Die Katalogzeilen selbst gibt es für eigene Einträge nie (Grundsatz aus
federation-catalog.md), nur das Löschprotokoll.

Gegenrichtung (Nutzer wieder ausgewählt, Projekt wieder freigegeben):
``reset_local = 1`` in ALLEN Zeilen von ``federation_catalog_sources`` — das
wertet V2 aus (der Hub antwortet dann beim nächsten ``catalog_pull`` jedes
Clients einmal mit ``reset_local``).
"""
from __future__ import annotations

import logging

from hydrahive.db import federation_catalog_revs as revs
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db
from hydrahive.federation import peer_identity
from hydrahive.modules import catalog_sources

logger = logging.getLogger(__name__)


def _own_fingerprint() -> str:
    return peer_identity.fingerprint(peer_identity.public_key_b64())


def _delete_for_user(fp: str, username: str, now: str) -> int:
    """Löschzeile für jeden Katalog-Eintrag von ``username`` über alle
    Katalog-Quellen (``source_kinds``). Gibt die Anzahl zurück."""
    count = 0
    for kind in catalog_sources.source_kinds():
        source = catalog_sources.get_source(kind)
        if source is None:
            continue
        try:
            versions = source.list_versions(username) or []
        except Exception as e:
            logger.warning("Ausschluss beim Hub: Quelle %s für %s fehlgeschlagen: %s", kind, username, e)
            continue
        with db(immediate=True) as conn:
            for v in versions:
                if len(v) < 1 or not v[0]:
                    continue
                revs.write_deletion(
                    conn, origin_fp=fp, kind=kind, item_id=str(v[0]), owner=username, deleted_at=now,
                )
                count += 1
    return count


def _delete_for_newly_excluded_project(fp: str, username: str, project_id: str, now: str) -> int:
    """Löschzeile für Einträge von ``username``, die jetzt in ``project_id``
    liegen (neu ausgeschlossenes Projekt, Nutzer bleibt ausgewählt)."""
    count = 0
    for kind in catalog_sources.source_kinds():
        source = catalog_sources.get_source(kind)
        if source is None:
            continue
        try:
            versions = source.list_versions(username) or []
        except Exception as e:
            logger.warning("Ausschluss beim Hub: Quelle %s für %s fehlgeschlagen: %s", kind, username, e)
            continue
        with db(immediate=True) as conn:
            for v in versions:
                if len(v) < 3 or not v[0] or v[2] != project_id:
                    continue
                revs.write_deletion(
                    conn, origin_fp=fp, kind=kind, item_id=str(v[0]), owner=username, deleted_at=now,
                )
                count += 1
    return count


def _reset_local_for_all_sources() -> None:
    with db() as conn:
        conn.execute("UPDATE federation_catalog_sources SET reset_local = 1")


def apply_hub_exclusion_change(
    *, before_users: set[str], after_users: set[str],
    before_excluded: set[str], after_excluded: set[str],
) -> None:
    """Wird aus ``PUT /api/federation/catalog/settings`` aufgerufen, NACH dem
    Speichern der neuen Nutzerauswahl/Projektliste. Wirft nie — ein Fehler
    hier darf die Antwort der Route nicht kippen (Aufrufer sichert mit
    try/except ab, analog ``safe_refresh_gate``)."""
    now = now_iso()
    fp = _own_fingerprint()

    removed_users = before_users - after_users
    for username in removed_users:
        _delete_for_user(fp, username, now)

    newly_excluded = after_excluded - before_excluded
    if newly_excluded:
        for username in after_users:  # nur noch ausgewählte Nutzer: war vorher schon weg, hier egal
            for project_id in newly_excluded:
                _delete_for_newly_excluded_project(fp, username, project_id, now)

    added_users = after_users - before_users
    freed_projects = before_excluded - after_excluded
    if added_users or freed_projects:
        _reset_local_for_all_sources()
