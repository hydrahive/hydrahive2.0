from __future__ import annotations

from hydrahive.db.connection import db

EXPECTED_TABLES = {
    "akte_patient", "akte_condition", "akte_medication", "akte_observation",
    "akte_encounter", "akte_imaging", "akte_allergy", "akte_practitioner",
    "akte_document", "akte_note",
}


def test_migration_creates_all_akte_tables():
    with db() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'akte_%'"
        ).fetchall()
    names = {r["name"] for r in rows}
    assert EXPECTED_TABLES <= names


def test_observation_has_numeric_wert_and_refs():
    with db() as conn:
        cols = {r["name"]: r["type"] for r in conn.execute("PRAGMA table_info(akte_observation)")}
    assert cols.get("wert") == "REAL"
    assert cols.get("referenz_min") == "REAL"
    assert "wert_text" in cols


def test_entity_has_common_columns():
    with db() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(akte_condition)")}
    assert {"id", "patient_id", "external_id", "quelle", "confidence", "verifiziert",
            "sort_date", "extra_json", "created_at", "updated_at"} <= cols


def test_registry_columns_subset_of_tables():
    """Guard: jede Registry-Spalte existiert wirklich in der Tabelle (kein Drift)."""
    from hydrahive.patientenakte.schema import ENTITIES

    with db() as conn:
        for spec in ENTITIES.values():
            actual = {r["name"] for r in conn.execute(f"PRAGMA table_info({spec.table})")}
            missing = set(spec.fields) - actual
            assert not missing, f"{spec.table}: registry fields not in table: {missing}"


def test_registry_keys_match_lastenheft():
    from hydrahive.patientenakte.schema import ENTITIES

    assert set(ENTITIES) == {
        "conditions", "medications", "observations", "events", "imaging",
        "allergies", "practitioners", "documents", "notes",
    }
