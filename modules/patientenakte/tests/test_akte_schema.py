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
    from backend.schema import ENTITIES

    with db() as conn:
        for spec in ENTITIES.values():
            actual = {r["name"] for r in conn.execute(f"PRAGMA table_info({spec.table})")}
            missing = set(spec.fields) - actual
            assert not missing, f"{spec.table}: registry fields not in table: {missing}"


def test_registry_keys_match_lastenheft():
    from backend.schema import ENTITIES

    assert set(ENTITIES) == {
        "conditions", "medications", "observations", "events", "imaging",
        "allergies", "practitioners", "documents", "notes",
    }


# ── SSOT (Single Source of Truth) für die UI ─────────────────────────────────
# Diese Guards verhindern Drift zwischen Backend-Registry und Frontend.
# Früher lagen Feld-/Label-/Spalten-Definitionen handgespiegelt in akteFields.ts,
# api.ts (LABEL_FIELDS) und AkteEntityList.tsx (ENTITY_COLUMNS) — und drifteten
# (z.B. Spalte "sicherheit" statt "schweregrad" → still leere Zelle).

VALID_FIELD_TYPES = {"text", "number", "date", "textarea", "select"}


def test_fields_derived_from_ui_fields():
    """fields ist abgeleitet aus ui_fields (eine Quelle, keine Doppelung)."""
    from backend.schema import ENTITIES

    for key, spec in ENTITIES.items():
        assert spec.fields == tuple(f.key for f in spec.ui_fields), key


def test_ui_field_keys_unique():
    from backend.schema import ENTITIES

    for key, spec in ENTITIES.items():
        keys = [f.key for f in spec.ui_fields]
        assert len(keys) == len(set(keys)), f"{key}: doppelte ui_field keys"


def test_ui_field_types_are_valid():
    from backend.schema import ENTITIES

    for key, spec in ENTITIES.items():
        for f in spec.ui_fields:
            assert f.type in VALID_FIELD_TYPES, f"{key}.{f.key}: bad type {f.type!r}"


def test_select_fields_have_options():
    from backend.schema import ENTITIES

    for key, spec in ENTITIES.items():
        for f in spec.ui_fields:
            if f.type == "select":
                assert f.options, f"{key}.{f.key}: select ohne options"


def test_each_entity_has_required_label_field():
    """Mind. ein Pflichtfeld pro Entität — sonst leere Einträge ohne Label."""
    from backend.schema import ENTITIES

    for key, spec in ENTITIES.items():
        required = [f.key for f in spec.ui_fields if f.required]
        assert required, f"{key}: kein required-Feld"


def test_label_fields_subset_of_fields():
    from backend.schema import ENTITIES

    for key, spec in ENTITIES.items():
        assert spec.label_fields, f"{key}: keine label_fields"
        unknown = set(spec.label_fields) - set(spec.fields)
        assert not unknown, f"{key}: label_fields nicht in fields: {unknown}"


def test_list_columns_subset_of_fields():
    """Der Guard, der die toten Spalten (körperstelle/sicherheit/…) fängt."""
    from backend.schema import ENTITIES

    for key, spec in ENTITIES.items():
        unknown = set(spec.list_columns) - set(spec.fields)
        assert not unknown, f"{key}: list_columns nicht in fields: {unknown}"


def test_numeric_fields_subset_of_fields():
    from backend.schema import ENTITIES

    for key, spec in ENTITIES.items():
        unknown = set(spec.numeric_fields) - set(spec.fields)
        assert not unknown, f"{key}: numeric_fields nicht in fields: {unknown}"
