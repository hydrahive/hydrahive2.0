from __future__ import annotations

MODEL = "claude-3-7-sonnet-20250219"  # im Test-Katalog gültig (wie conftest-Agent)


def test_create_agent_stores_external_flag(client, admin_headers):
    r = client.post("/api/agents",
                    json={"type": "master", "name": "ext-test", "llm_model": MODEL, "external": True},
                    headers=admin_headers)
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    got = client.get(f"/api/agents/{aid}", headers=admin_headers).json()
    assert got["external"] is True


def test_create_agent_defaults_external_false(client, admin_headers):
    r = client.post("/api/agents",
                    json={"type": "master", "name": "int-test", "llm_model": MODEL},
                    headers=admin_headers)
    assert r.status_code == 201, r.text
    assert r.json().get("external") is False
