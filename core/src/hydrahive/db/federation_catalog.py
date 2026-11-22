"""DB-Operationen für den Föderations-Katalog (docs/specs/federation-catalog.md).

Etappe 1: nur Hub-Markierung und Katalog-Einstellungen auf dem Client, noch
kein Versand. Die Hub-seitigen Tabellen (`federation_catalog_items`,
`federation_catalog_rejected`, `federation_catalog_sources`) werden hier noch
nicht gelesen oder geschrieben — das kommt mit dem Versand (Etappe 3).
"""
from __future__ import annotations

from typing import Any

from hydrahive.db.connection import db

_SETTINGS_COLUMNS = (
    "enabled", "interval_seconds", "seq",
    "last_push_at", "last_ok_at", "last_full_at", "last_error",
)


def _row(r: Any) -> dict:
    return dict(r)


# --- Hub-Markierung (federation_peers.is_hub / .catalog_accept) ------------

def any_hub() -> dict | None:
    """Der Partner, der aktuell als Hub markiert ist (höchstens einer)."""
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM federation_peers WHERE is_hub = 1 LIMIT 1",
        ).fetchone()
    return _row(row) if row else None


def any_accepting() -> list[dict]:
    """Partner, von denen dieser Server Katalog-Daten annimmt."""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM federation_peers WHERE catalog_accept = 1 ORDER BY name",
        ).fetchall()
    return [_row(r) for r in rows]


class CatalogConflict(Exception):
    """Hub-/Annahme-Regel verletzt; die Route macht daraus ein 409 mit Code."""

    def __init__(self, code: str, **params: Any) -> None:
        super().__init__(code)
        self.code = code
        self.params = params


def set_hub(peer_id: str, is_hub: bool) -> dict | None:
    """Hub-Markierung setzen. Prüfen und Schreiben in EINER Transaktion mit
    Schreibsperre (BEGIN IMMEDIATE): zwei gleichzeitige Anfragen können so weder
    zwei Hubs noch Hub + Annehmen erzeugen. Cursor nur bei echter Änderung leeren
    (Spec Ablauf 2: Hub-Wechsel → voller Abgleich). None = Partner unbekannt."""
    with db(immediate=True) as conn:
        peer = conn.execute("SELECT * FROM federation_peers WHERE id = ?", (peer_id,)).fetchone()
        if not peer:
            return None
        if is_hub:
            if peer["status"] != "active":
                raise CatalogConflict("peer_not_active")
            if conn.execute("SELECT 1 FROM federation_peers WHERE catalog_accept = 1 LIMIT 1").fetchone():
                raise CatalogConflict("catalog_hub_conflict")
            other = conn.execute(
                "SELECT name FROM federation_peers WHERE is_hub = 1 AND id != ? LIMIT 1", (peer_id,),
            ).fetchone()
            if other:
                raise CatalogConflict("catalog_hub_exists", name=other["name"])
        conn.execute(
            "UPDATE federation_peers SET is_hub = ? WHERE id = ?", (1 if is_hub else 0, peer_id),
        )
        if bool(peer["is_hub"]) != is_hub:
            conn.execute("DELETE FROM federation_catalog_cursors")
            conn.execute("UPDATE federation_catalog_settings SET last_full_at = NULL WHERE id = 1")
        row = conn.execute("SELECT * FROM federation_peers WHERE id = ?", (peer_id,)).fetchone()
    return _row(row)


def set_catalog_accept(peer_id: str, accept: bool) -> dict | None:
    """Annahme setzen, atomar gegen gleichzeitiges Setzen eines Hubs."""
    with db(immediate=True) as conn:
        peer = conn.execute("SELECT * FROM federation_peers WHERE id = ?", (peer_id,)).fetchone()
        if not peer:
            return None
        if accept:
            if peer["status"] != "active":
                raise CatalogConflict("peer_not_active")
            if conn.execute("SELECT 1 FROM federation_peers WHERE is_hub = 1 LIMIT 1").fetchone():
                raise CatalogConflict("catalog_hub_conflict")
        conn.execute(
            "UPDATE federation_peers SET catalog_accept = ? WHERE id = ?", (1 if accept else 0, peer_id),
        )
        row = conn.execute("SELECT * FROM federation_peers WHERE id = ?", (peer_id,)).fetchone()
    return _row(row)


# --- Katalog-Einstellungen (federation_catalog_settings, eine Zeile) -------

def gate_inputs() -> tuple[bool, str | None, list[str]]:
    """Rein lesend (kein INSERT): (enabled, Hub-Status oder None, Nutzerauswahl).

    Für den Schalter von `ctx.catalog_changed` (federation/catalog_changes.py).
    Fehlt die Einstellungszeile, gilt der Standard „aus“.
    """
    with db() as conn:
        row = conn.execute("SELECT enabled FROM federation_catalog_settings WHERE id = 1").fetchone()
        hub = conn.execute("SELECT status FROM federation_peers WHERE is_hub = 1 LIMIT 1").fetchone()
        users = conn.execute("SELECT username FROM federation_catalog_users ORDER BY username").fetchall()
    return (bool(row and row["enabled"]), hub["status"] if hub else None, [r["username"] for r in users])


def get_settings() -> dict:
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO federation_catalog_settings (id) VALUES (1)")
        row = conn.execute(
            "SELECT * FROM federation_catalog_settings WHERE id = 1",
        ).fetchone()
    return _row(row)


def update_settings(*, enabled: bool, interval_seconds: int, shared: bool = False, remote_edits: bool = False) -> dict:
    """``shared``/``remote_edits`` (docs/specs/federation-shared-tasks.md §Schalter,
    Standard aus). ``remote_edits`` hat noch keine Wirkung — das bestätigt Till
    vor Etappe G4 (Bearbeiten), siehe Spec Z. 86–90. Nur speichern, nichts tut
    damit heute etwas."""
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO federation_catalog_settings (id) VALUES (1)")
        conn.execute(
            "UPDATE federation_catalog_settings "
            "SET enabled = ?, interval_seconds = ?, shared = ?, remote_edits = ? WHERE id = 1",
            (1 if enabled else 0, interval_seconds, 1 if shared else 0, 1 if remote_edits else 0),
        )
        row = conn.execute(
            "SELECT * FROM federation_catalog_settings WHERE id = 1",
        ).fetchone()
    return _row(row)


# --- Nutzerauswahl (federation_catalog_users) -------------------------------

def list_selected_users() -> list[str]:
    with db() as conn:
        rows = conn.execute(
            "SELECT username FROM federation_catalog_users ORDER BY username",
        ).fetchall()
    return [r["username"] for r in rows]


def set_selected_users(usernames: list[str]) -> list[str]:
    unique = sorted(set(usernames))
    with db() as conn:
        conn.execute("DELETE FROM federation_catalog_users")
        conn.executemany(
            "INSERT INTO federation_catalog_users (username) VALUES (?)",
            [(u,) for u in unique],
        )
    return unique


# --- Ausgeschlossene Projekte (federation_catalog_excluded_projects) -------

def list_excluded_projects() -> list[str]:
    with db() as conn:
        rows = conn.execute(
            "SELECT project_id FROM federation_catalog_excluded_projects ORDER BY project_id",
        ).fetchall()
    return [r["project_id"] for r in rows]


def set_excluded_projects(project_ids: list[str]) -> list[str]:
    unique = sorted(set(project_ids))
    with db() as conn:
        conn.execute("DELETE FROM federation_catalog_excluded_projects")
        conn.executemany(
            "INSERT INTO federation_catalog_excluded_projects (project_id) VALUES (?)",
            [(p,) for p in unique],
        )
    return unique


# --- Cursor (federation_catalog_cursors) ------------------------------------

def reset_all_cursors() -> None:
    """Voller Abgleich beim nächsten Lauf (Spec Ablauf 2: Hub-Wechsel oder
    Auswahländerung setzt den Cursor zurück). ``last_full_at`` leeren, damit der
    nächste Timer-Lauf auch die Versionsliste schickt und Abgewähltes sofort
    vom Hub verschwindet, nicht erst bis zu 60 min später."""
    with db() as conn:
        conn.execute("DELETE FROM federation_catalog_cursors")
        conn.execute("UPDATE federation_catalog_settings SET last_full_at = NULL WHERE id = 1")
