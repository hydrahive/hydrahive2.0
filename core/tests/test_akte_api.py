from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from hydrahive.api.main import app
from hydrahive.api.middleware.auth import require_auth

BASE = "/api/health/patientenakte"


@pytest.fixture
def client():
    app.dependency_overrides[require_auth] = lambda: ("u1", "user")
    yield TestClient(app)
    app.dependency_overrides.clear()


def _new_patient(client, **data):
    data.setdefault("slug", "alex")
    return client.post(f"{BASE}/patients", json=data).json()["id"]


def test_create_patient_and_list(client):
    r = client.post(f"{BASE}/patients", json={"slug": "alex", "name": "Molke"})
    assert r.status_code == 200
    pid = r.json()["id"]
    r2 = client.get(f"{BASE}/patients")
    assert any(p["id"] == pid for p in r2.json())


def test_get_patient_includes_counts(client):
    pid = _new_patient(client)
    client.post(f"{BASE}/patients/{pid}/conditions", json={"diagnose": "X"})
    body = client.get(f"{BASE}/patients/{pid}").json()
    assert body["counts"]["conditions"] == 1


def test_create_condition_via_api(client):
    pid = _new_patient(client)
    r = client.post(f"{BASE}/patients/{pid}/conditions",
                    json={"external_id": "k75", "diagnose": "Leberabszess", "icd_code": "K75.0"})
    assert r.status_code == 200
    items = client.get(f"{BASE}/patients/{pid}/conditions").json()
    assert items[0]["icd_code"] == "K75.0"


def test_idempotent_batch_via_api(client):
    pid = _new_patient(client)
    for _ in range(2):
        client.post(f"{BASE}/patients/{pid}/observations/batch",
                    json={"items": [{"external_id": "h1", "parameter": "HbA1c",
                                     "wert": 6.4, "datum": "2026-05-01"}]})
    assert len(client.get(f"{BASE}/patients/{pid}/observations").json()) == 1


def test_timeline_and_summary_endpoints(client):
    pid = _new_patient(client)
    client.post(f"{BASE}/patients/{pid}/conditions",
                json={"diagnose": "X", "diagnostiziert_am": "2020-01-01"})
    assert client.get(f"{BASE}/patients/{pid}/summary").json()["conditions"] == 1
    assert len(client.get(f"{BASE}/patients/{pid}/timeline").json()) == 1


def test_entity_get_patch_delete(client):
    pid = _new_patient(client)
    eid = client.post(f"{BASE}/patients/{pid}/conditions", json={"diagnose": "A"}).json()["id"]
    assert client.get(f"{BASE}/patients/{pid}/conditions/{eid}").json()["diagnose"] == "A"
    assert client.patch(f"{BASE}/patients/{pid}/conditions/{eid}", json={"diagnose": "B"}).json()["ok"]
    assert client.get(f"{BASE}/patients/{pid}/conditions/{eid}").json()["diagnose"] == "B"
    assert client.delete(f"{BASE}/patients/{pid}/conditions/{eid}").json()["ok"]
    assert client.get(f"{BASE}/patients/{pid}/conditions/{eid}").status_code == 404


def test_unknown_entity_404(client):
    pid = _new_patient(client)
    assert client.get(f"{BASE}/patients/{pid}/nonsense").status_code == 404


def test_foreign_patient_404(client):
    pid = _new_patient(client)
    app.dependency_overrides[require_auth] = lambda: ("u2", "user")
    assert client.get(f"{BASE}/patients/{pid}/conditions").status_code == 404
    assert client.get(f"{BASE}/patients/{pid}").status_code == 404
