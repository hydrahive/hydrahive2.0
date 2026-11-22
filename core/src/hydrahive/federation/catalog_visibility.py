"""Hub: Sichtbarkeit eines Ursprungs O (docs/specs/federation-shared-tasks.md
§Schalter "Wenn die Sichtbarkeit wegfällt").

``origin_visible`` prüft Bedingung 2 der Spec für einen Ursprung O (einen
Partner, der Katalogeinträge an den Hub liefert): O ist für den Hub nur dann
eine gültige Quelle, wenn alle drei gelten — ``catalog_accept = 1``,
``status = active``, ``shared = 1`` (gemeldet im letzten ``catalog_push``,
gespeichert in ``federation_catalog_sources.shared``).

``on_visibility_change`` wird an den drei Stellen aufgerufen, die diese drei
Werte ändern können: ``shared`` im Push (``db/federation_catalog_hub.py``),
``catalog_accept`` per Route (``db/federation_catalog.py``), Statuswechsel
active/blocked per Route (``db/federation_peers.py``). Läuft immer in
derselben Transaktion wie die Änderung selbst — der Aufrufer hält die
Schreibsperre (``db(immediate=True)``).
"""
from __future__ import annotations

import sqlite3

from hydrahive.db import federation_catalog_revs as revs


def origin_visible(peer_row: dict | None, source_row: dict | None) -> bool:
    """Bedingung 2 der Spec für den Ursprung O.

    ``peer_row``: Zeile aus ``federation_peers`` (braucht ``catalog_accept``,
    ``status``) · ``source_row``: Zeile aus ``federation_catalog_sources``
    (braucht ``shared``) oder ``None``, wenn die Quelle noch nie gepusht hat
    (dann ist sie nicht sichtbar — Standard aus).
    """
    if not peer_row:
        return False
    if not peer_row.get("catalog_accept"):
        return False
    if peer_row.get("status") != "active":
        return False
    if not source_row or not source_row.get("shared"):
        return False
    return True


def on_visibility_change(conn: sqlite3.Connection, peer_id: str, before: bool, after: bool, now: str) -> None:
    """Reagiert auf einen Wechsel der Sichtbarkeit von O.

    Wegfall (``before`` True, ``after`` False): Löschzeile für JEDEN
    Katalogeintrag von O (die Katalogzeilen selbst bleiben auf dem Hub stehen
    — er zeigt sie im Katalog-Reiter weiter, Spec §Schalter).

    Wiederkehr (``before`` False, ``after`` True): alle Einträge von O
    bekommen eine neue ``rev``, damit sie beim nächsten Abholen erneut
    verteilt werden (Spec §Schalter: "Wird die Bedingung wieder erfüllt,
    bekommen alle Einträge von O eine neue rev").

    Kein Wechsel: nichts tun.
    """
    if before == after:
        return
    from hydrahive.federation import catalog_notify   # Anstupsen (V7), nur Speicher, wirft nie
    catalog_notify.mark(exclude=peer_id)
    peer = conn.execute(
        "SELECT fingerprint FROM federation_peers WHERE id = ?", (peer_id,),
    ).fetchone()
    if not peer:
        return
    origin_fp = peer["fingerprint"]
    rows = conn.execute(
        "SELECT kind, item_id, owner FROM federation_catalog_items WHERE peer_id = ?", (peer_id,),
    ).fetchall()
    if before and not after:
        for r in rows:
            revs.write_deletion(
                conn, origin_fp=origin_fp, kind=r["kind"], item_id=r["item_id"],
                owner=r["owner"], deleted_at=now,
            )
    else:
        for r in rows:
            rev = revs.next_rev(conn)
            conn.execute(
                "UPDATE federation_catalog_items SET rev = ? WHERE peer_id = ? AND kind = ? AND item_id = ?",
                (rev, peer_id, r["kind"], r["item_id"]),
            )
