"""GET /api/health/patientenakte/_schema — liefert die UI-Registry (SSOT).

Das Frontend zieht diese Antwort einmal und rendert Formulare/Spalten/Labels
generisch, statt schema.py handzuspiegeln. Kritisch: _schema ist eine literale
Route, die VOR /{entity} stehen muss — sonst matcht der Catch-all und liefert
404 "Unbekannte Entität: _schema".
"""
from __future__ import annotations

BASE = "/api/modules/patientenakte/akte"

EXPECTED_ENTITIES = {
    "conditions", "medications", "observations", "events", "imaging",
    "allergies", "practitioners", "documents", "notes",
}


def test_schema_endpoint_requires_auth(client):
    assert client.get(f"{BASE}/_schema").status_code == 401


def test_schema_not_swallowed_by_entity_catchall(client, auth_headers):
    """Route-Order-Guard: _schema != entity → 200, nicht 404."""
    r = client.get(f"{BASE}/_schema", headers=auth_headers)
    assert r.status_code == 200, r.text


def test_schema_lists_all_entities(client, auth_headers):
    body = client.get(f"{BASE}/_schema", headers=auth_headers).json()
    assert set(body["entities"]) == EXPECTED_ENTITIES


def test_schema_entity_shape(client, auth_headers):
    body = client.get(f"{BASE}/_schema", headers=auth_headers).json()
    cond = body["entities"]["conditions"]
    assert cond["label"] == "Diagnosen"
    assert cond["label_fields"] == ["diagnose"]
    assert cond["list_columns"] == ["icd_code", "status"]
    keys = [f["key"] for f in cond["ui_fields"]]
    assert keys[0] == "diagnose"
    diagnose = cond["ui_fields"][0]
    assert diagnose["required"] is True
    assert diagnose["type"] == "text"


def test_schema_select_field_carries_options(client, auth_headers):
    body = client.get(f"{BASE}/_schema", headers=auth_headers).json()
    status = next(f for f in body["entities"]["conditions"]["ui_fields"] if f["key"] == "status")
    assert status["type"] == "select"
    assert "aktuell" in status["options"]
