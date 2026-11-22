"""Hub-Seite des Föderations-Katalogs: Annahme von ``catalog_push``.

docs/specs/federation-catalog.md §Datenmodell (Hub-Seite) und §Ablauf 3. Alles,
was ein Push ändert (Seq, Upsert, Löschungen, Abgleich, Status der Quelle),
passiert in EINER Transaktion mit Schreibsperre. Zwei gleichzeitige Pushes
desselben Partners können so weder dieselbe ``seq`` doppelt verbuchen noch sich
gegenseitig überschreiben.

``updated_at`` ist ein undurchsichtiger Wert der Quelle. Verglichen wird nur
innerhalb derselben Zeile (gleiche ``kind``), nie über Arten hinweg.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from hydrahive.db import federation_catalog_revs as revs
from hydrahive.db.connection import db
from hydrahive.federation.catalog_visibility import on_visibility_change, origin_visible


class SeqReplay(Exception):
    def __init__(self, last_seq: int) -> None:
        super().__init__(f"seq <= {last_seq}")
        self.last_seq = last_seq


@dataclass
class PushResult:
    upserted: int = 0
    skipped_older: int = 0
    deleted: int = 0
    pruned: int = 0
    resync: list[dict] = field(default_factory=list)
    item_count: int = 0


def last_seq(peer_id: str) -> int:
    with db() as conn:
        row = conn.execute(
            "SELECT last_seq FROM federation_catalog_sources WHERE peer_id = ?", (peer_id,),
        ).fetchone()
    return int(row["last_seq"]) if row else 0


_UPSERT = """
INSERT INTO federation_catalog_items
    (peer_id, kind, item_id, owner, title, status, priority, project_id, project_name,
     created_at, updated_at, received_at)
VALUES (:peer_id, :kind, :item_id, :owner, :title, :status, :priority, :project_id, :project_name,
        :created_at, :updated_at, :now)
ON CONFLICT (peer_id, kind, item_id) DO UPDATE SET
    owner = excluded.owner, title = excluded.title, status = excluded.status,
    priority = excluded.priority, project_id = excluded.project_id,
    project_name = excluded.project_name, created_at = excluded.created_at,
    snapshot_stale = CASE WHEN excluded.updated_at IS NOT federation_catalog_items.updated_at
                          THEN 1 ELSE federation_catalog_items.snapshot_stale END,
    updated_at = excluded.updated_at, received_at = excluded.received_at
WHERE excluded.updated_at >= COALESCE(federation_catalog_items.updated_at, '')
"""


def apply_push(
    peer_id: str,
    *,
    seq: int,
    interval_seconds: int | None,
    now: str,
    items: list[dict],
    deleted: list[tuple[str, str]],
    rejected: list[tuple[str, str, str | None, str]],
    full_versions: dict[tuple[str, str], dict[str, str]] | None,
    shared: bool = False,
    remote_edits: bool = False,
) -> PushResult:
    """Verbucht einen geprüften Push. Wirft SeqReplay, wenn ``seq`` nicht neu ist.

    ``items``: gültige Metadaten · ``deleted``: (kind, item_id) · ``rejected``:
    (kind, item_id, updated_at, reason) · ``full_versions``: (owner, kind) →
    {item_id: updated_at} oder None.

    ``shared``/``remote_edits`` (docs/specs/federation-shared-tasks.md
    §Schalter): was diese Quelle gerade meldet, wird in
    ``federation_catalog_sources`` abgelegt. Ändert sich dabei die
    Sichtbarkeit von O (``origin_visible``, Bedingung 2 der Spec), schreibt
    ``on_visibility_change`` Löschzeilen (Wegfall) bzw. neue ``rev`` für alle
    Einträge von O (Wiederkehr) — in derselben Transaktion wie der Wechsel.
    """
    res = PushResult()
    with db(immediate=True) as conn:
        row = conn.execute(
            "SELECT last_seq, shared FROM federation_catalog_sources WHERE peer_id = ?", (peer_id,),
        ).fetchone()
        current = int(row["last_seq"]) if row else 0
        if seq <= current:
            raise SeqReplay(current)
        # Sichtbarkeit VOR dem Wechsel: peer-Status/catalog_accept ändern sich
        # hier nicht, nur row["shared"] (ALTER Wert) vs. shared (NEUER Wert,
        # Funktionsargument). Peer-Zeile für catalog_accept/status brauchen
        # wir trotzdem, Bedingung 2 prüft alle drei.
        peer = conn.execute(
            "SELECT catalog_accept, status, fingerprint FROM federation_peers WHERE id = ?", (peer_id,),
        ).fetchone()
        before_visible = origin_visible(dict(peer) if peer else None, dict(row) if row else None)

        for item in items:
            cur = conn.execute(_UPSERT, {**item, "peer_id": peer_id, "now": now})
            if cur.rowcount:
                res.upserted += 1
                # rev bei JEDEM angenommenen Upsert neu (Spec §Änderungsnummer),
                # auch bei updated_at-Gleichstand. Abgelehnte/ältere Upserts
                # (WHERE oben greift nicht, rowcount=0) vergeben keine rev.
                rev = revs.next_rev(conn)
                conn.execute(
                    "UPDATE federation_catalog_items SET rev = ? "
                    "WHERE peer_id = ? AND kind = ? AND item_id = ?",
                    (rev, peer_id, item["kind"], item["item_id"]),
                )
                conn.execute(
                    "DELETE FROM federation_catalog_rejected WHERE peer_id = ? AND kind = ? AND item_id = ?",
                    (peer_id, item["kind"], item["item_id"]),
                )
            else:
                res.skipped_older += 1
        origin_fp = peer["fingerprint"]
        for kind, item_id in deleted:
            existing = conn.execute(
                "SELECT owner FROM federation_catalog_items WHERE peer_id = ? AND kind = ? AND item_id = ?",
                (peer_id, kind, item_id),
            ).fetchone()
            cur = conn.execute(
                "DELETE FROM federation_catalog_items WHERE peer_id = ? AND kind = ? AND item_id = ?",
                (peer_id, kind, item_id),
            )
            res.deleted += cur.rowcount
            if cur.rowcount and existing:
                # Spec §Änderungsnummer: Push mit "deleted" → Löschzeile.
                revs.write_deletion(
                    conn, origin_fp=origin_fp, kind=kind, item_id=item_id,
                    owner=existing["owner"], deleted_at=now,
                )
            conn.execute(
                "DELETE FROM federation_catalog_rejected WHERE peer_id = ? AND kind = ? AND item_id = ?",
                (peer_id, kind, item_id),
            )
        conn.executemany(
            "INSERT INTO federation_catalog_rejected (peer_id, kind, item_id, updated_at, reason) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT (peer_id, kind, item_id) DO UPDATE SET "
            "updated_at = excluded.updated_at, reason = excluded.reason",
            [(peer_id, k, i, u, r) for k, i, u, r in rejected],
        )
        if full_versions is not None:
            _reconcile(conn, peer_id, full_versions, res, origin_fp, now)

        res.item_count = conn.execute(
            "SELECT COUNT(*) FROM federation_catalog_items WHERE peer_id = ?", (peer_id,),
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO federation_catalog_sources "
            "(peer_id, last_seq, interval_seconds, last_push_at, last_full_at, item_count, "
            " shared, remote_edits) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (peer_id) DO UPDATE SET "
            "last_seq = excluded.last_seq, interval_seconds = excluded.interval_seconds, "
            "last_push_at = excluded.last_push_at, "
            "last_full_at = COALESCE(excluded.last_full_at, federation_catalog_sources.last_full_at), "
            "item_count = excluded.item_count, "
            "shared = excluded.shared, remote_edits = excluded.remote_edits",
            (
                peer_id, seq, interval_seconds, now, now if full_versions is not None else None,
                res.item_count, 1 if shared else 0, 1 if remote_edits else 0,
            ),
        )
        # Sichtbarkeit NACH dem Wechsel (Spec §Schalter "Wenn die Sichtbarkeit
        # wegfällt"/Wiederkehr): Bedingung 2 mit dem NEUEN shared-Wert, Peer
        # selbst (catalog_accept/status) ändert sich in diesem Pfad nicht.
        after_visible = origin_visible(
            dict(peer) if peer else None, {"shared": 1 if shared else 0},
        )
        on_visibility_change(conn, peer_id, before_visible, after_visible, now)
    return res


def _reconcile(
    conn, peer_id: str, full: dict[tuple[str, str], dict[str, str]], res: PushResult,
    origin_fp: str, now: str,
) -> None:
    """Stündlicher Abgleich: Hub entfernt, was fehlt; Abweichungen → resync.

    Abgeglichen werden nur Arten, die in der Liste vorkommen (bei irgendeinem
    Nutzer, auch als leere Liste). Fehlt eine Art ganz, hat der Client dafür
    gerade keine Quelle (Modul lädt nicht) — dann bleibt sie unangetastet statt
    alles zu löschen. Innerhalb einer gelisteten Art gilt ein fehlender Nutzer
    als leer (abgewählt).
    """
    kinds = {kind for (_o, kind) in full}
    stored = [r for r in conn.execute(
        "SELECT kind, item_id, owner, updated_at FROM federation_catalog_items WHERE peer_id = ?", (peer_id,),
    ).fetchall() if r["kind"] in kinds]
    listed = {(kind, item_id) for (_o, kind), versions in full.items() for item_id in versions}
    for r in stored:
        if (r["kind"], r["item_id"]) not in listed:
            cur = conn.execute(
                "DELETE FROM federation_catalog_items WHERE peer_id = ? AND kind = ? AND item_id = ?",
                (peer_id, r["kind"], r["item_id"]),
            )
            res.pruned += cur.rowcount
            if cur.rowcount:
                # Spec §Änderungsnummer: Abgleich entfernt Fehlendes → Löschzeile.
                revs.write_deletion(
                    conn, origin_fp=origin_fp, kind=r["kind"], item_id=r["item_id"],
                    owner=r["owner"], deleted_at=now,
                )
    for r in conn.execute(
        "SELECT kind, item_id FROM federation_catalog_rejected WHERE peer_id = ?", (peer_id,),
    ).fetchall():
        if r["kind"] in kinds and (r["kind"], r["item_id"]) not in listed:
            conn.execute(
                "DELETE FROM federation_catalog_rejected WHERE peer_id = ? AND kind = ? AND item_id = ?",
                (peer_id, r["kind"], r["item_id"]),
            )

    have = {(r["owner"], r["kind"], r["item_id"]): r["updated_at"] for r in stored}
    rejected = {
        (r["kind"], r["item_id"]): r["updated_at"]
        for r in conn.execute(
            "SELECT kind, item_id, updated_at FROM federation_catalog_rejected WHERE peer_id = ?", (peer_id,),
        ).fetchall()
    }
    for (owner, kind), versions in sorted(full.items()):
        for item_id, updated_at in versions.items():
            if have.get((owner, kind, item_id)) == updated_at:
                continue
            if rejected.get((kind, item_id), object()) == updated_at:
                continue  # verworfen und unverändert → keine Dauerschleife
            res.resync.append({"username": owner, "kind": kind})
            break
