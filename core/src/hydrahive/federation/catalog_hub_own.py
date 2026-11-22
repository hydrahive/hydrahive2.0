"""Hub: eigene Einträge verteilen (docs/specs/federation-shared-tasks.md
§Änderungsnummer "Eigene Einträge des Hubs").

Eigene Einträge des Hubs werden NIE in ``federation_catalog_items`` kopiert
(Grundsatz aus federation-catalog.md). Dieser Schritt prüft nur, ob ein
vorgemerkter eigener Eintrag noch existiert bzw. noch nicht ausgeschlossen
ist; fehlt er, schreibt er eine Löschzeile mit dem EIGENEN Fingerprint als
``origin_fp``. Existiert er, passiert nichts — ``catalog_pull`` (V2) liest
die Quelle direkt, keine Kopie nötig.

Läuft im selben Katalog-Loop wie der Client-Push, unter derselben Sperre
(``catalog_sync._lock``), nach ``catalog_changes.drain_hub()``.
"""
from __future__ import annotations

import logging

from hydrahive.db import federation_catalog_client as client_db
from hydrahive.db import federation_catalog_revs as revs
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db
from hydrahive.federation import catalog_changes, peer_identity
from hydrahive.modules import catalog_sources

logger = logging.getLogger(__name__)


def _is_excluded(row: dict | None, excluded_projects: frozenset[str]) -> bool:
    """Fehlt der Eintrag ganz, oder liegt er jetzt in einem ausgeschlossenen
    Projekt (Filter wie catalog_plan._collect_full)."""
    if row is None:
        return True
    return row.get("project_id") in excluded_projects


def hub_distribute_step() -> bool:
    """Leert die Hub-Vormerkungen, schreibt Löschzeilen für Fehlendes/
    Ausgeschlossenes. Rückgabe: ob sich etwas geändert hat (V3 hängt das
    Anstupsen daran). Wirft nie — Fehler werden geloggt, der Timer-Lauf holt
    verpasste Löschungen über den stündlichen Abgleich nach (sinngemäß; der
    Hub hat hier keinen eigenen Abgleich, aber ein einzelner Fehler bricht
    den Lauf nicht ab).
    """
    entries, overflow = catalog_changes.drain_hub()
    if not entries and not overflow:
        return False
    try:
        cfg = client_db.load_config()
    except Exception as e:
        logger.warning("Katalog-Verteilung (eigene Einträge): Einstellungen nicht lesbar: %s", e)
        return False

    changed = False
    now = now_iso()
    fp = peer_identity.fingerprint(peer_identity.public_key_b64())
    seen: set[tuple[str, str]] = set()
    for kind, username, item_id in entries:
        if (kind, item_id) in seen:
            continue
        seen.add((kind, item_id))
        source = catalog_sources.get_source(kind)
        if source is None:
            continue
        try:
            row = source.get_full(username, item_id)
        except Exception as e:
            logger.warning("Katalog-Verteilung: Quelle %s für %s fehlgeschlagen: %s", kind, username, e)
            continue
        if _is_excluded(row if isinstance(row, dict) else None, cfg.excluded_projects):
            with db(immediate=True) as conn:
                revs.write_deletion(
                    conn, origin_fp=fp, kind=kind, item_id=item_id, owner=username, deleted_at=now,
                )
            changed = True
    return changed
