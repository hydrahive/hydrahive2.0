from __future__ import annotations


def test_get_empty_scratchpad(client, auth_headers):
    r = client.get("/api/scratchpad", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"user_content": "", "agent_content": ""}


def test_put_then_get_roundtrip(client, auth_headers):
    put = client.put("/api/scratchpad", json={"content": "meine idee"}, headers=auth_headers)
    assert put.status_code == 200
    assert put.json() == {"saved": True}
    got = client.get("/api/scratchpad", headers=auth_headers)
    assert got.json()["user_content"] == "meine idee"


def test_put_only_sets_user_zone(client, auth_headers):
    client.put("/api/scratchpad", json={"content": "USER"}, headers=auth_headers)
    got = client.get("/api/scratchpad", headers=auth_headers)
    assert got.json()["user_content"] == "USER"
    assert got.json()["agent_content"] == ""  # PUT berührt agent-Zone nicht


def test_delete_agent_zone(client, auth_headers):
    # auth_headers loggt "testuser" ein → require_auth liefert genau diesen Namen.
    from hydrahive.scratchpad import service
    service.save_agent("testuser", "agent notiz")
    deleted = client.delete("/api/scratchpad/agent", headers=auth_headers)
    assert deleted.status_code == 200
    got = client.get("/api/scratchpad", headers=auth_headers)
    assert got.json()["agent_content"] == ""


def test_requires_auth(client):
    assert client.get("/api/scratchpad").status_code == 401
