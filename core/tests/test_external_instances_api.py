from __future__ import annotations

import pytest

from hydrahive.agents import external_instances as ei
from tests.conftest import error_code

MODEL = "claude-3-7-sonnet-20250219"


@pytest.fixture(autouse=True)
def _cleanup_external(client):
    yield
    for inst in ei.list_instances():
        ei.delete_instance(inst["agent_id"])


def test_create_requires_admin(client, auth_headers):
    r = client.post("/api/external-instances",
                    json={"name": "x", "llm_model": MODEL}, headers=auth_headers)
    assert r.status_code == 403


def test_admin_create_and_list(client, admin_headers):
    r = client.post("/api/external-instances",
                    json={"name": "api-inst", "llm_model": MODEL}, headers=admin_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["api_key"].startswith("hhk_") and body["username"] == "api-inst"
    lst = client.get("/api/external-instances", headers=admin_headers).json()
    assert any(i["name"] == "api-inst" for i in lst)


def test_delete_instance(client, admin_headers):
    aid = client.post("/api/external-instances",
                      json={"name": "del-inst", "llm_model": MODEL}, headers=admin_headers).json()["agent_id"]
    assert client.delete(f"/api/external-instances/{aid}", headers=admin_headers).status_code == 204


def test_rotate_key(client, admin_headers):
    aid = client.post("/api/external-instances",
                      json={"name": "rot-inst", "llm_model": MODEL}, headers=admin_headers).json()["agent_id"]
    rk = client.post(f"/api/external-instances/{aid}/rotate-key", headers=admin_headers)
    assert rk.status_code == 200 and rk.json()["api_key"].startswith("hhk_")


def test_duplicate_name_409(client, admin_headers):
    client.post("/api/external-instances", json={"name": "dup-api", "llm_model": MODEL}, headers=admin_headers)
    r = client.post("/api/external-instances", json={"name": "dup-api", "llm_model": MODEL}, headers=admin_headers)
    assert r.status_code == 409


def test_invalid_model_400(client, admin_headers):
    # Leeres Modell triggert validate_model unabhängig von der LLM-Config
    # (in der Testumgebung gibt es keine, sonst würde auch ein Tippfehler greifen).
    r = client.post("/api/external-instances",
                    json={"name": "badmodel", "llm_model": ""}, headers=admin_headers)
    assert r.status_code == 400
    assert error_code(r) == "validation_error"


def test_invalid_model_rolls_back_user(client, admin_headers):
    from hydrahive.api.middleware import users
    client.post("/api/external-instances",
                json={"name": "rollback-u", "llm_model": ""}, headers=admin_headers)
    assert not any(u["username"] == "rollback-u" for u in users.list_users())
