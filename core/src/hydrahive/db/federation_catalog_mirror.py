"""Client: Kopie der Hub-Metadaten (docs/specs/federation-shared-tasks.md
§Verteilung, §Datenmodell ``federation_catalog_mirror``).

Nur Datenbank, kein Netz. Eine abgeholte Seite wird in EINER Transaktion
geschrieben, und erst darin rücken ``pull_rev``/``pull_local_cursor`` vor: bricht
das Schreiben ab, bleibt auch der Stand stehen und die Seite kommt noch einmal.
Die Kopie wird nie gepusht (sie liegt im Kern, nicht in den Modultabellen).
"""
from __future__ import annotations

import json

from hydrahive.db.connection import db

KINDS = ("task", "idea")
_FIELDS = ("origin_fp", "kind", "item_id", "origin_name", "owner", "title", "status", "priority",
           "project_id", "project_name", "created_at", "updated_at")

# Upsert nur, wenn das neue updated_at ≥ dem gespeicherten ist. Der Schlüssel
# enthält kind, verglichen wird also nur innerhalb derselben Art.
_UPSERT = f"""
INSERT INTO federation_catalog_mirror ({", ".join(_FIELDS)}, received_at)
VALUES ({", ".join("?" * len(_FIELDS))}, ?)
ON CONFLICT (origin_fp, kind, item_id) DO UPDATE SET
    origin_name = excluded.origin_name, owner = excluded.owner, title = excluded.title,
    status = excluded.status, priority = excluded.priority, project_id = excluded.project_id,
    project_name = excluded.project_name, created_at = excluded.created_at,
    updated_at = excluded.updated_at, received_at = excluded.received_at
WHERE COALESCE(excluded.updated_at, '') >= COALESCE(federation_catalog_mirror.updated_at, '')
"""


def state() -> tuple[int, dict]:
    """``(pull_rev, pull_local_cursor)``; Cursor je Art, ``None`` = von vorn."""
    with db() as conn:
        row = conn.execute(
            "SELECT pull_rev, pull_local_cursor FROM federation_catalog_settings WHERE id = 1",
        ).fetchone()
    cursor = {}
    if row and row["pull_local_cursor"]:
        try:
            raw = json.loads(row["pull_local_cursor"])
            cursor = raw if isinstance(raw, dict) else {}
        except ValueError:
            cursor = {}
    return (int(row["pull_rev"]) if row else 0), {k: cursor.get(k) for k in KINDS}


def apply_page(items: list[dict], deleted: list[dict], next_rev: int, local_next: dict, now: str) -> int:
    """Eine geprüfte Seite schreiben und danach den Stand weitersetzen. Rückgabe: geschriebene Zeilen."""
    written = 0
    with db(immediate=True) as conn:
        for it in items:
            cur = conn.execute(_UPSERT, (*[it.get(f) for f in _FIELDS], now))
            written += cur.rowcount
        conn.executemany(
            "DELETE FROM federation_catalog_mirror WHERE origin_fp = ? AND kind = ? AND item_id = ?",
            [(d["origin_fp"], d["kind"], d["item_id"]) for d in deleted],
        )
        conn.execute("INSERT OR IGNORE INTO federation_catalog_settings (id) VALUES (1)")
        conn.execute(
            "UPDATE federation_catalog_settings SET pull_rev = ?, pull_local_cursor = ? WHERE id = 1",
            (int(next_rev), json.dumps({k: local_next.get(k) for k in KINDS})),
        )
    return written


def reset_local_cursor() -> None:
    """``reset_local`` vom Hub: Cursor für Hub-Einträge auf „von vorn“."""
    with db() as conn:
        conn.execute("UPDATE federation_catalog_settings SET pull_local_cursor = NULL WHERE id = 1")


def keep_only(keys: set[tuple[str, str, str]]) -> int:
    """Voller Abgleich: alles löschen, was nicht in ``keys`` (origin_fp, kind, item_id) steht."""
    with db(immediate=True) as conn:
        rows = conn.execute("SELECT origin_fp, kind, item_id FROM federation_catalog_mirror").fetchall()
        gone = [tuple(r) for r in rows if (r["origin_fp"], r["kind"], r["item_id"]) not in keys]
        conn.executemany(
            "DELETE FROM federation_catalog_mirror WHERE origin_fp = ? AND kind = ? AND item_id = ?", gone,
        )
    return len(gone)


def save_instances(instances: object, now: str) -> None:
    """``instances`` aus der Pull-Antwort ersetzen den gemerkten Stand der Ursprünge."""
    if not isinstance(instances, list):
        return
    rows = [(str(i["origin_fp"])[:128], str(i.get("origin_name") or "")[:128] or None,
             i.get("last_seen") if isinstance(i.get("last_seen"), str) else None,
             1 if i.get("stale") else 0, now)
            for i in instances[:500] if isinstance(i, dict) and isinstance(i.get("origin_fp"), str)]
    with db(immediate=True) as conn:
        conn.execute("DELETE FROM federation_catalog_mirror_instances")
        conn.executemany("INSERT OR REPLACE INTO federation_catalog_mirror_instances VALUES (?, ?, ?, ?, ?)", rows)


def clear() -> None:
    """Kopie leeren und Stand auf „von vorn“ (Spec §Schalter „Der Client leert seine Kopie“)."""
    with db() as conn:
        conn.execute("DELETE FROM federation_catalog_mirror")
        conn.execute("DELETE FROM federation_catalog_mirror_instances")
        conn.execute("INSERT OR IGNORE INTO federation_catalog_settings (id) VALUES (1)")
        conn.execute(
            "UPDATE federation_catalog_settings SET pull_rev = 0, pull_local_cursor = NULL, "
            "last_full_pull_at = NULL WHERE id = 1",
        )


def record_pull_status(*, ok_at: str | None = None, full_at: str | None = None, error: str | None = None) -> None:
    """``last_pull_at``/``last_full_pull_at`` bei Erfolg, ``last_pull_error`` (leer bei Erfolg)."""
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO federation_catalog_settings (id) VALUES (1)")
        if ok_at:
            conn.execute("UPDATE federation_catalog_settings SET last_pull_at = ?, last_pull_error = NULL "
                         "WHERE id = 1", (ok_at,))
        if full_at:
            conn.execute("UPDATE federation_catalog_settings SET last_full_pull_at = ? WHERE id = 1", (full_at,))
        if error:
            conn.execute("UPDATE federation_catalog_settings SET last_pull_error = ? WHERE id = 1", (error,))


def last_full_pull_at() -> str | None:
    with db() as conn:
        row = conn.execute("SELECT last_full_pull_at FROM federation_catalog_settings WHERE id = 1").fetchone()
    return row["last_full_pull_at"] if row else None
