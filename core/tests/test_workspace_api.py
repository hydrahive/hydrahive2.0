from __future__ import annotations


def _agent(client, admin_headers):
    res = client.post("/api/agents", headers=admin_headers,
                      json={"type": "specialist", "name": "WS Bot", "llm_model": "claude-haiku-4-5-20251001"})
    assert res.status_code == 201, res.text
    return res.json()


def test_tree_requires_auth(client):
    res = client.get("/api/workspace/tree?agent_id=x&path=")
    assert res.status_code == 401


def test_tree_lists_workspace(client, admin_headers):
    agent = _agent(client, admin_headers)
    res = client.get(f"/api/workspace/tree?agent_id={agent['id']}&path=", headers=admin_headers)
    assert res.status_code == 200, res.text
    assert isinstance(res.json(), list)


def test_tree_rejects_traversal(client, admin_headers):
    agent = _agent(client, admin_headers)
    res = client.get(f"/api/workspace/tree?agent_id={agent['id']}&path=../../etc", headers=admin_headers)
    assert res.status_code == 403
