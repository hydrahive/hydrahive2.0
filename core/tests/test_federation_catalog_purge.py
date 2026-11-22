"""Auftrag B3, Stück 1 — Aufräumen des Löschprotokolls nach 7 Tagen im
Katalog-Timer-Loop (docs/specs/federation-shared-tasks.md §Änderungsnummer
"Aufräumen nach 7 Tagen"). Läuft nur auf dem Hub (mindestens ein Partner mit
``catalog_accept = 1``), nie auf einem reinen Client.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from hydrahive.db import federation_catalog_revs as revs
from hydrahive.db.connection import db
from hydrahive.federation import catalog_runner


def _peer(*, catalog_accept: bool) -> str:
    peer_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            "INSERT INTO federation_peers "
            "(id, name, url, public_key, fingerprint, status, catalog_accept, created_at) "
            "VALUES (?, ?, 'https://x', ?, ?, 'active', ?, 'now')",
            (peer_id, f"peer-{peer_id}", peer_id, peer_id, 1 if catalog_accept else 0),
        )
    return peer_id


def _write_old_deletion(days_old: int) -> int:
    old = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat(timespec="milliseconds")
    with db(immediate=True) as conn:
        return revs.write_deletion(
            conn, origin_fp="fp-old", kind="task", item_id=str(uuid.uuid4()),
            owner="till", deleted_at=old,
        )


def _deletion_count() -> int:
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM federation_catalog_deletions").fetchone()[0]


def _purged_rev() -> int:
    with db() as conn:
        return int(conn.execute("SELECT purged_rev FROM federation_catalog_counter WHERE id = 1").fetchone()[0])


def test_hub_raeumt_alte_loeschzeilen_auf(client):
    peer_id = _peer(catalog_accept=True)
    before = _deletion_count()
    old_rev = _write_old_deletion(8)  # älter als 7 Tage
    assert _deletion_count() == before + 1

    catalog_runner._purge_deletions_if_hub()

    assert _deletion_count() == before
    assert _purged_rev() >= old_rev

    with db() as conn:
        conn.execute("DELETE FROM federation_peers WHERE id = ?", (peer_id,))


def test_client_ohne_angenommene_partner_raeumt_nicht_auf(client, monkeypatch):
    """Isoliert von anderen Katalog-Tests, die evtl. eigene catalog_accept=1-
    Partner in der (session-weiten) Test-DB zurücklassen: `any_accepting`
    wird direkt gemockt, statt sich auf den globalen DB-Zustand zu verlassen."""
    monkeypatch.setattr(catalog_runner.catalog_db, "any_accepting", lambda: [])
    before = _deletion_count()
    _write_old_deletion(8)

    catalog_runner._purge_deletions_if_hub()

    assert _deletion_count() == before + 1  # nicht aufgeräumt

    with db() as conn:
        conn.execute("DELETE FROM federation_catalog_deletions WHERE origin_fp = 'fp-old'")


def test_junge_loeschzeile_bleibt_auch_auf_dem_hub(client):
    peer_id = _peer(catalog_accept=True)
    before = _deletion_count()
    with db(immediate=True) as conn:
        revs.write_deletion(
            conn, origin_fp="fp-young", kind="task", item_id=str(uuid.uuid4()),
            owner="till", deleted_at=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        )

    catalog_runner._purge_deletions_if_hub()

    assert _deletion_count() == before + 1  # jung, bleibt

    with db() as conn:
        conn.execute("DELETE FROM federation_peers WHERE id = ?", (peer_id,))
        conn.execute("DELETE FROM federation_catalog_deletions WHERE origin_fp = 'fp-young'")


async def test_timer_tick_raeumt_auf_wenn_hub(client, monkeypatch):
    """timer_tick ruft das Aufräumen auf — Smoke-Test über den Thread-Wrapper,
    ohne vollen Sync-Lauf (load_config liefert hier 'inactive')."""
    peer_id = _peer(catalog_accept=True)
    _write_old_deletion(8)
    before = _deletion_count()

    result = await catalog_runner.timer_tick(1)

    assert result == "inactive"  # keine Einstellungen aktiv, aber Aufräumen lief trotzdem
    assert _deletion_count() == before - 1

    with db() as conn:
        conn.execute("DELETE FROM federation_peers WHERE id = ?", (peer_id,))
