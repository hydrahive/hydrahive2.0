"""Tests H5: nativer TK-eGA-Pfad (db/ega.py + /api/ega/*).

Deckt upsert (imported/updated/errors), _stable_id-Fallback, _display-Branches,
Per-User-Isolation, summary/timeline, cost_summary inkl. kaputter Geldwerte
(MEDIUM-Befund), sowie Route-Wiring + 422 bei kaputtem ZIP.
"""
from __future__ import annotations

import pytest

from backend import ega_store as ega_db


@pytest.fixture(autouse=True)
def _ensure_db(setup_test_env):
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    init_db()
    yield
    with db() as conn:
        conn.execute("DELETE FROM ega_records")


# --- _stable_id ----------------------------------------------------------

def test_stable_id_mit_tk_id():
    rid = ega_db._stable_id("Encounter", {"id": "abc123"})
    assert rid == "Enc-abc123"


def test_stable_id_fallback_hash_deterministisch():
    rec = {"metaInformation": {"contentProviderDetails": {"businessObjectId": "BO-1"}}}
    a = ega_db._stable_id("Condition", rec)
    b = ega_db._stable_id("Condition", rec)
    assert a == b
    assert len(a) == 32
    assert "-" not in a  # reiner Hash, kein Prefix


def test_stable_id_fallback_ohne_boid_nutzt_record_json():
    rid = ega_db._stable_id("Procedure", {"code": {"text": "X"}})
    assert len(rid) == 32


# --- upsert_records ------------------------------------------------------

def test_upsert_imported_dann_updated():
    rec = ("Encounter", {"id": "e1", "serviceProvider": {"name": "Dr. A"},
                         "period": {"start": "2026-01-01"}})
    r1 = ega_db.upsert_records([rec], user_id="u1")
    assert r1 == {"imported": 1, "updated": 0, "errors": 0}
    r2 = ega_db.upsert_records([rec], user_id="u1")
    assert r2 == {"imported": 0, "updated": 1, "errors": 0}


def test_upsert_zaehlt_errors():
    # set ist nicht JSON-serialisierbar → json.dumps wirft → wird als error gezählt
    bad = ("Encounter", {"id": "e2", "bad": {1, 2, 3}})
    r = ega_db.upsert_records([bad], user_id="u1")
    assert r["errors"] == 1
    assert r["imported"] == 0


# --- _display Branches ---------------------------------------------------

def test_display_encounter():
    d = ega_db._display("Encounter", {"serviceProvider": {"name": "Praxis Dr. B"},
                                      "period": {"start": "2026-03-02"}})
    assert "Praxis Dr. B" in d and "2026-03-02" in d


def test_display_condition_nutzt_coding_display():
    d = ega_db._display("Condition", {"code": {"coding": [{"code": "I10", "display": "Hypertonie"}]}})
    assert d == "Hypertonie"


def test_display_ambulant_claim():
    d = ega_db._display("AmbulantClaim", {"organization": {"name": "MVZ X"},
                                          "billablePeriod": {"start": "2026-02-15"}})
    assert d == "MVZ X (2026-02)"


def test_display_unbekannter_typ_fallback():
    assert ega_db._display("Unbekannt", {}) == "Unbekannt"


# --- summary / timeline / Isolation --------------------------------------

def test_summary_zaehlt_pro_dto_type():
    ega_db.upsert_records([
        ("Encounter", {"id": "e1"}),
        ("Encounter", {"id": "e2"}),
        ("Condition", {"id": "c1"}),
    ], user_id="u1")
    s = ega_db.summary(user_id="u1")
    assert s == {"Encounter": 2, "Condition": 1}


def test_timeline_sortiert_und_limitiert():
    ega_db.upsert_records([
        ("Encounter", {"id": "e1", "period": {"start": "2026-01-01"}}),
        ("Encounter", {"id": "e2", "period": {"start": "2026-03-01"}}),
        ("Encounter", {"id": "e3", "period": {"start": "2026-02-01"}}),
    ], user_id="u1")
    tl = ega_db.timeline(user_id="u1", limit=2)
    assert len(tl) == 2
    assert tl[0]["sort_date"] == "2026-03-01"  # neueste zuerst
    assert tl[1]["sort_date"] == "2026-02-01"


def test_per_user_isolation():
    ega_db.upsert_records([("Encounter", {"id": "e1"})], user_id="u1")
    assert ega_db.summary(user_id="u2") == {}
    assert ega_db.query_by_type(user_id="u2", dto_type="Encounter") == []
    assert ega_db.timeline(user_id="u2") == []


# --- cost_summary (inkl. kaputte Geldwerte, MEDIUM-Befund) ---------------

def test_cost_summary_summiert_korrekt():
    ega_db.upsert_records([
        ("AmbulantClaim", {"id": "a1", "total": {"value": "100.50"}}),
        ("AmbulantClaim", {"id": "a2", "total": {"value": "49.50"}}),
        ("MedicationClaim", {"id": "m1", "total": {"value": "20.00"},
                             "item": [{"detail": [
                                 {"service": {"coding": [{"code": "zuzahlung"}]}, "net": {"value": "5.00"}},
                             ]}]}),
    ], user_id="u1")
    c = ega_db.cost_summary(user_id="u1")
    assert c["ambulant_eur"] == 150.0
    assert c["medikamente_eur"] == 20.0
    assert c["medikamente_zuzahlung_eur"] == 5.0


def test_cost_summary_kaputte_werte_degradieren_zu_null():
    ega_db.upsert_records([
        ("AmbulantClaim", {"id": "a1", "total": {"value": "12,50"}}),   # Komma → float wirft
        ("AmbulantClaim", {"id": "a2", "total": {}}),                    # fehlender value
        ("AmbulantClaim", {"id": "a3", "total": {"value": None}}),       # None
        ("AmbulantClaim", {"id": "a4", "total": {"value": "30.00"}}),    # gültig
    ], user_id="u1")
    c = ega_db.cost_summary(user_id="u1")
    # Nur der gültige Wert zählt, kein Crash
    assert c["ambulant_eur"] == 30.0


# --- Route-Wiring --------------------------------------------------------

def test_route_costs_roundtrip(client, auth_headers):
    ega_db.upsert_records([
        ("AmbulantClaim", {"id": "a1", "total": {"value": "42.00"}}),
    ], user_id="testuser")
    resp = client.get("/api/modules/patientenakte/ega/costs", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["ambulant_eur"] == 42.0


def test_route_summary_und_timeline(client, auth_headers):
    ega_db.upsert_records([
        ("Condition", {"id": "c1", "code": {"coding": [{"display": "Diabetes"}]},
                       "metaInformation": {"sortDate": "2026-01-05"}}),
    ], user_id="testuser")
    s = client.get("/api/modules/patientenakte/ega/summary", headers=auth_headers)
    assert s.status_code == 200
    assert s.json().get("Condition") == 1
    tl = client.get("/api/modules/patientenakte/ega/timeline", headers=auth_headers)
    assert tl.status_code == 200
    assert tl.json()["count"] == 1


def test_route_import_kaputtes_zip_422(client, auth_headers):
    resp = client.post(
        "/api/modules/patientenakte/ega/import",
        files={"file": ("export.zip", b"das ist kein zip", "application/zip")},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "invalid_ega_zip"
