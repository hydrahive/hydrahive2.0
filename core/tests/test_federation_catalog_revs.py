"""Auftrag B, Stück 1 — `next_rev` (docs/specs/federation-shared-tasks.md
§Änderungsnummer): gemeinsamer Zähler für Items und Löschzeilen, streng
steigend, ohne Doppel. Rein auf der DB-Ebene, kein HTTP (das deckt
test_federation_catalog_shared_push.py / _deletions.py ab).
"""
from __future__ import annotations

from hydrahive.db import federation_catalog_revs as revs
from hydrahive.db.connection import db


def test_next_rev_ist_steigend_und_eindeutig(client):
    with db(immediate=True) as conn:
        a = revs.next_rev(conn)
        b = revs.next_rev(conn)
        c = revs.next_rev(conn)
    assert a < b < c
    assert len({a, b, c}) == 3


def test_next_rev_gemeinsamer_zaehler_ueber_items_und_deletions(client):
    """Eine rev aus write_deletion liegt zwischen zwei next_rev-Aufrufen,
    die eine Item-rev simulieren — der Zähler ist gemeinsam, keine Lücke
    erlaubt doppelte Vergabe."""
    with db(immediate=True) as conn:
        item_rev_1 = revs.next_rev(conn)
        del_rev = revs.write_deletion(
            conn, origin_fp="fp1", kind="task", item_id="t1", owner="till",
            deleted_at="2026-11-22T00:00:00.000+00:00",
        )
        item_rev_2 = revs.next_rev(conn)
    assert item_rev_1 < del_rev < item_rev_2
    assert len({item_rev_1, del_rev, item_rev_2}) == 3


def test_write_deletion_schreibt_zeile_mit_eigener_rev(client):
    with db(immediate=True) as conn:
        rev = revs.write_deletion(
            conn, origin_fp="fp2", kind="idea", item_id="i1", owner="till",
            deleted_at="2026-11-22T00:00:00.000+00:00",
        )
        row = conn.execute(
            "SELECT * FROM federation_catalog_deletions WHERE rev = ?", (rev,),
        ).fetchone()
    assert row is not None
    assert row["origin_fp"] == "fp2"
    assert row["kind"] == "idea"
    assert row["item_id"] == "i1"
    assert row["owner"] == "till"
