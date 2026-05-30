from __future__ import annotations

BASE = "/api/health/patientenakte"


def _new_patient(client, headers, **data):
    data.setdefault("slug", "alex")
    return client.post(f"{BASE}/patients", json=data, headers=headers).json()["id"]


def test_create_patient_and_list(client, auth_headers):
    r = client.post(f"{BASE}/patients", json={"slug": "alex", "name": "Molke"}, headers=auth_headers)
    assert r.status_code == 200
    pid = r.json()["id"]
    r2 = client.get(f"{BASE}/patients", headers=auth_headers)
    assert any(p["id"] == pid for p in r2.json())


def test_get_patient_includes_counts(client, auth_headers):
    pid = _new_patient(client, auth_headers)
    client.post(f"{BASE}/patients/{pid}/conditions", json={"diagnose": "X"}, headers=auth_headers)
    body = client.get(f"{BASE}/patients/{pid}", headers=auth_headers).json()
    assert body["counts"]["conditions"] == 1


def test_create_condition_via_api(client, auth_headers):
    pid = _new_patient(client, auth_headers)
    r = client.post(f"{BASE}/patients/{pid}/conditions",
                    json={"external_id": "k75", "diagnose": "Leberabszess", "icd_code": "K75.0"},
                    headers=auth_headers)
    assert r.status_code == 200
    items = client.get(f"{BASE}/patients/{pid}/conditions", headers=auth_headers).json()
    assert items[0]["icd_code"] == "K75.0"


def test_idempotent_batch_via_api(client, auth_headers):
    pid = _new_patient(client, auth_headers)
    for _ in range(2):
        client.post(f"{BASE}/patients/{pid}/observations/batch",
                    json={"items": [{"external_id": "h1", "parameter": "HbA1c",
                                     "wert": 6.4, "datum": "2026-05-01"}]},
                    headers=auth_headers)
    assert len(client.get(f"{BASE}/patients/{pid}/observations", headers=auth_headers).json()) == 1


def test_timeline_and_summary_endpoints(client, auth_headers):
    pid = _new_patient(client, auth_headers)
    client.post(f"{BASE}/patients/{pid}/conditions",
                json={"diagnose": "X", "diagnostiziert_am": "2020-01-01"}, headers=auth_headers)
    assert client.get(f"{BASE}/patients/{pid}/summary", headers=auth_headers).json()["conditions"] == 1
    assert len(client.get(f"{BASE}/patients/{pid}/timeline", headers=auth_headers).json()) == 1


def test_entity_get_patch_delete(client, auth_headers):
    pid = _new_patient(client, auth_headers)
    eid = client.post(f"{BASE}/patients/{pid}/conditions", json={"diagnose": "A"},
                      headers=auth_headers).json()["id"]
    assert client.get(f"{BASE}/patients/{pid}/conditions/{eid}", headers=auth_headers).json()["diagnose"] == "A"
    assert client.patch(f"{BASE}/patients/{pid}/conditions/{eid}", json={"diagnose": "B"},
                        headers=auth_headers).json()["ok"]
    assert client.get(f"{BASE}/patients/{pid}/conditions/{eid}", headers=auth_headers).json()["diagnose"] == "B"
    assert client.delete(f"{BASE}/patients/{pid}/conditions/{eid}", headers=auth_headers).json()["ok"]
    assert client.get(f"{BASE}/patients/{pid}/conditions/{eid}", headers=auth_headers).status_code == 404


def test_unknown_entity_404(client, auth_headers):
    pid = _new_patient(client, auth_headers)
    assert client.get(f"{BASE}/patients/{pid}/nonsense", headers=auth_headers).status_code == 404


def test_foreign_patient_404(client, auth_headers, admin_headers):
    pid = _new_patient(client, auth_headers)            # gehört testuser
    # admin ist ein anderer Owner -> darf testusers Patient nicht sehen
    assert client.get(f"{BASE}/patients/{pid}/conditions", headers=admin_headers).status_code == 404
    assert client.get(f"{BASE}/patients/{pid}", headers=admin_headers).status_code == 404
