from __future__ import annotations

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db
from hydrahive.patientenakte import patients


def test_create_and_get_patient():
    pid = patients.create("u1", {"slug": "alex", "name": "Molke", "vorname": "Alexander",
                                 "adresse": {"ort": "Frankfurt"}})
    p = patients.get("u1", pid)
    assert p["name"] == "Molke"
    assert p["adresse"]["ort"] == "Frankfurt"   # JSON-Roundtrip
    assert "adresse_json" not in p              # internes Feld nicht durchgereicht


def test_list_only_own_patients():
    patients.create("u1", {"slug": "a"})
    patients.create("u2", {"slug": "b"})
    assert {p["slug"] for p in patients.list_for("u1")} == {"a"}


def test_get_foreign_patient_returns_none():
    pid = patients.create("u1", {"slug": "a"})
    assert patients.get("u2", pid) is None


def test_update_patient():
    pid = patients.create("u1", {"slug": "a", "name": "X"})
    assert patients.update("u1", pid, {"name": "Y", "email": "y@z"}) is True
    p = patients.get("u1", pid)
    assert p["name"] == "Y"
    assert p["email"] == "y@z"


def test_update_foreign_patient_fails():
    pid = patients.create("u1", {"slug": "a"})
    assert patients.update("u2", pid, {"name": "Z"}) is False


def test_delete_cascades_entities():
    pid = patients.create("u1", {"slug": "a"})
    with db() as conn:
        conn.execute(
            "INSERT INTO akte_condition (id,patient_id,verifiziert,created_at,updated_at,diagnose) "
            "VALUES (?,?,?,?,?,?)",
            (uuid7(), pid, 0, now_iso(), now_iso(), "X"))
    assert patients.delete("u1", pid) is True
    assert patients.get("u1", pid) is None
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM akte_condition WHERE patient_id=?", (pid,)).fetchone()
    assert row["c"] == 0   # FK ON DELETE CASCADE
