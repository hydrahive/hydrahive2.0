from __future__ import annotations

import pytest

from hydrahive.patientenakte import entities, patients


@pytest.fixture
def pid():
    return patients.create("u1", {"slug": "alex"})


def test_create_and_list(pid):
    entities.create("u1", pid, "conditions",
                    {"diagnose": "Diabetes", "icd_code": "E11", "diagnostiziert_am": "2021-05-01"})
    items = entities.list_for("u1", pid, "conditions")
    assert len(items) == 1
    assert items[0]["diagnose"] == "Diabetes"
    assert items[0]["sort_date"] == "2021-05-01"     # aus diagnostiziert_am abgeleitet
    assert "extra_json" not in items[0]


def test_external_id_upsert_no_duplicate(pid):
    entities.create("u1", pid, "conditions", {"external_id": "x1", "diagnose": "A"})
    entities.create("u1", pid, "conditions", {"external_id": "x1", "diagnose": "A-korrigiert"})
    items = entities.list_for("u1", pid, "conditions")
    assert len(items) == 1
    assert items[0]["diagnose"] == "A-korrigiert"    # upsert, kein Duplikat


def test_array_field_roundtrip(pid):
    entities.create("u1", pid, "medications",
                    {"name": "Metformin", "nebenwirkungen": ["Übelkeit", "Durchfall"]})
    item = entities.list_for("u1", pid, "medications")[0]
    assert item["nebenwirkungen"] == ["Übelkeit", "Durchfall"]


def test_numeric_field_stored_as_number(pid):
    entities.create("u1", pid, "observations",
                    {"parameter": "HbA1c", "wert": 6.4, "einheit": "%", "datum": "2026-05-01"})
    item = entities.list_for("u1", pid, "observations")[0]
    assert item["wert"] == 6.4


def test_batch_create(pid):
    n = entities.batch_create("u1", pid, "observations", [
        {"parameter": "HbA1c", "wert": 7.8, "datum": "2025-03-01"},
        {"parameter": "eGFR", "wert": 93, "datum": "2025-03-01"},
    ])
    assert n == 2
    assert len(entities.list_for("u1", pid, "observations")) == 2


def test_filter_by_q(pid):
    entities.create("u1", pid, "conditions", {"diagnose": "Diabetes mellitus"})
    entities.create("u1", pid, "conditions", {"diagnose": "Hypertonie"})
    items = entities.list_for("u1", pid, "conditions", q="diabet")
    assert len(items) == 1


def test_filter_by_status(pid):
    entities.create("u1", pid, "medications", {"name": "Metformin", "status": "aktuell"})
    entities.create("u1", pid, "medications", {"name": "Insulin", "status": "historisch"})
    items = entities.list_for("u1", pid, "medications", status="aktuell")
    assert {i["name"] for i in items} == {"Metformin"}


def test_get_update_delete(pid):
    eid = entities.create("u1", pid, "conditions", {"diagnose": "X"})
    assert entities.get("u1", pid, "conditions", eid)["diagnose"] == "X"
    assert entities.update("u1", pid, "conditions", eid, {"diagnose": "Y"}) is True
    assert entities.get("u1", pid, "conditions", eid)["diagnose"] == "Y"
    assert entities.delete("u1", pid, "conditions", eid) is True
    assert entities.get("u1", pid, "conditions", eid) is None


def test_unknown_entity_raises(pid):
    with pytest.raises(KeyError):
        entities.create("u1", pid, "nonsense", {})


def test_foreign_patient_blocked():
    pid2 = patients.create("u2", {"slug": "b"})
    with pytest.raises(PermissionError):
        entities.create("u1", pid2, "conditions", {"diagnose": "X"})
