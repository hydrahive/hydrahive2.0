"""Migration 050: Tabellen für Gruppen, Funktions-Freigaben und Audit (Spec access-groups §6)."""
from __future__ import annotations

import sqlite3

import pytest

from hydrahive.db.connection import db
from tests._access_rows import _own_access_rows  # noqa: F401  (autouse)


def _tables() -> set[str]:
    with db() as c:
        return {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_access_tables_exist(client):
    tables = _tables()
    for name in ("access_groups", "access_group_members", "access_capability_grants", "access_audit"):
        assert name in tables, f"Tabelle {name} fehlt"


def test_resource_shares_not_yet_created(client):
    # Teilen einzelner Sachen kommt erst in Etappe 2.
    assert "access_resource_shares" not in _tables()


def test_grant_rejects_unknown_subject_type(client):
    with pytest.raises(sqlite3.IntegrityError):
        with db() as c:
            c.execute(
                "INSERT INTO access_capability_grants "
                "(capability, subject_type, subject_id, level, granted_by, granted_at) "
                "VALUES ('module.x', 'foo', 'u1', 'use', 'admin', '2026-09-29T00:00:00Z')"
            )


def test_grant_rejects_unknown_level(client):
    with pytest.raises(sqlite3.IntegrityError):
        with db() as c:
            c.execute(
                "INSERT INTO access_capability_grants "
                "(capability, subject_type, subject_id, level, granted_by, granted_at) "
                "VALUES ('module.x', 'user', 'u1', 'owner', 'admin', '2026-09-29T00:00:00Z')"
            )


def test_group_delete_cascades_members(client):
    with db() as c:
        c.execute(
            "INSERT INTO access_groups (id, name, created_by, created_at, updated_at) "
            "VALUES ('g-mig', 'Mig-Test', 'admin', 't', 't')"
        )
        c.execute(
            "INSERT INTO access_group_members (group_id, user_id, added_by, added_at) "
            "VALUES ('g-mig', 'u1', 'admin', 't')"
        )
    with db() as c:
        c.execute("DELETE FROM access_groups WHERE id = 'g-mig'")
        left = c.execute(
            "SELECT COUNT(*) FROM access_group_members WHERE group_id = 'g-mig'"
        ).fetchone()[0]
    assert left == 0
