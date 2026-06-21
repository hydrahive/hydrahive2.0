"""API-Tests: Lauf starten, abfragen, auflisten, Isolation, Validierung.

Die eigentliche Recherche läuft als Hintergrund-Task ohne konfiguriertes Modell und
endet schnell mit status=error — getestet wird die Route-/Persistenz-Schicht, nicht
der LLM-Lauf (der hat seinen eigenen Test in test_loop.py)."""
from __future__ import annotations

BASE = "/api/modules/deepresearch"


def test_start_and_get_run(client, alice):
    r = client.post(f"{BASE}/runs", json={"question": "Was ist X?"}, headers=alice)
    assert r.status_code == 201
    run_id = r.json()["run_id"]
    assert run_id

    g = client.get(f"{BASE}/runs/{run_id}", headers=alice)
    assert g.status_code == 200
    body = g.json()
    assert body["question"] == "Was ist X?"
    assert body["status"] in {"running", "done", "error"}
    assert "progress" in body


def test_list_runs(client, alice):
    client.post(f"{BASE}/runs", json={"question": "Thema eins"}, headers=alice)
    r = client.get(f"{BASE}/runs", headers=alice)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_get_unknown_returns_404(client, alice):
    r = client.get(f"{BASE}/runs/does-not-exist", headers=alice)
    assert r.status_code == 404


def test_user_isolation(client, alice, bob):
    r = client.post(f"{BASE}/runs", json={"question": "Alices Recherche"}, headers=alice)
    run_id = r.json()["run_id"]

    g = client.get(f"{BASE}/runs/{run_id}", headers=bob)
    assert g.status_code == 404

    lst = client.get(f"{BASE}/runs", headers=bob)
    assert all(run["id"] != run_id for run in lst.json())


def test_short_question_rejected(client, alice):
    r = client.post(f"{BASE}/runs", json={"question": "x"}, headers=alice)
    assert r.status_code == 422
