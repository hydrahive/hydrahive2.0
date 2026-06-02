"""Smoke-Tests für FHIR-Import und Abfrage."""
from __future__ import annotations

import pytest


def _bundle(resources: list[dict]) -> dict:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": r} for r in resources],
    }


def _condition(resource_id: str, code: str, display: str) -> dict:
    return {
        "resourceType": "Condition",
        "id": resource_id,
        "code": {"coding": [{"code": code, "display": display}]},
        "clinicalStatus": {"coding": [{"code": "active"}]},
    }


def test_import_bundle(client, auth_headers):
    bundle = _bundle([_condition("c1", "I10", "Hypertonie"), _condition("c2", "E11", "Diabetes")])
    resp = client.post("/api/fhir/import", json=bundle, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 2
    assert data["updated"] == 0
    assert data["errors"] == 0


def test_import_merge_upsert(client, auth_headers):
    bundle = _bundle([_condition("c1", "I10", "Hypertonie")])
    client.post("/api/fhir/import", json=bundle, headers=auth_headers)
    # Zweiter Import — selbe ID, aktualisierter Display
    bundle2 = _bundle([_condition("c1", "I10", "Arterielle Hypertonie")])
    resp = client.post("/api/fhir/import", json=bundle2, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 0
    assert data["updated"] == 1


def test_import_invalid_bundle(client, auth_headers):
    resp = client.post("/api/fhir/import", json={"resourceType": "Patient"}, headers=auth_headers)
    assert resp.status_code == 422


def test_get_resources(client, auth_headers):
    bundle = _bundle([_condition("c1", "I10", "Hypertonie")])
    client.post("/api/fhir/import", json=bundle, headers=auth_headers)
    resp = client.get("/api/fhir/resources/Condition", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


def test_user_isolation(client, auth_headers, admin_headers):
    bundle = _bundle([_condition("c-private", "I10", "Privat")])
    client.post("/api/fhir/import", json=bundle, headers=auth_headers)
    resp = client.get("/api/fhir/resources/Condition", headers=admin_headers)
    ids = [e["resource"]["id"] for e in resp.json()["resources"]]
    assert "c-private" not in ids


def test_summary(client, auth_headers):
    bundle = _bundle([_condition("c1", "I10", "Hypertonie")])
    client.post("/api/fhir/import", json=bundle, headers=auth_headers)
    resp = client.get("/api/fhir/summary", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json().get("Condition", 0) >= 1


# --- #209 (M10): gemischtes Bundle zählt den Per-Entry-errors-Pfad -----------

def test_import_mixed_bundle_counts_per_entry_errors(client, auth_headers):
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": _condition("mix-ok", "I10", "Gültig")},  # ok
            {"resource": {"resourceType": "Observation"}},          # id fehlt → error
            {"resource": {"id": "no-type"}},                        # resourceType fehlt → error
        ],
    }
    resp = client.post("/api/fhir/import", json=bundle, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] >= 1
    assert data["errors"] == 2


# --- #210 (L2): fhir.timeline ist gebounded ----------------------------------

def test_fhir_timeline_respektiert_limit(client, auth_headers):
    from hydrahive.db import fhir as fhir_db
    bundle = _bundle([_condition(f"tl{i}", "I10", f"D{i}") for i in range(5)])
    client.post("/api/fhir/import", json=bundle, headers=auth_headers)
    rows = fhir_db.timeline("testuser", limit=2)
    assert len(rows) == 2
