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


def test_tree_rejects_foreign_agent(client, admin_headers, auth_headers):
    # Agent gehört admin; testuser darf nicht in dessen Workspace (IDOR-Schutz)
    agent = _agent(client, admin_headers)
    res = client.get(f"/api/workspace/tree?agent_id={agent['id']}&path=", headers=auth_headers)
    assert res.status_code == 404


def test_raw_serves_file(client, admin_headers):
    agent = _agent(client, admin_headers)
    aid = agent["id"]
    client.put("/api/workspace/file", headers=admin_headers,
               json={"agent_id": aid, "path": "hello.txt", "content": "raw-bytes"})
    res = client.get(f"/api/workspace/raw?agent_id={aid}&path=hello.txt", headers=admin_headers)
    assert res.status_code == 200, res.text
    assert res.content == b"raw-bytes"
    # XSS-Härtung: untrusted Workspace-Bytes nie scriptfähig ausliefern
    assert "sandbox" in res.headers.get("content-security-policy", "")
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert "attachment" in res.headers.get("content-disposition", "")


def test_raw_rejects_traversal(client, admin_headers):
    agent = _agent(client, admin_headers)
    res = client.get(f"/api/workspace/raw?agent_id={agent['id']}&path=../../etc/passwd", headers=admin_headers)
    assert res.status_code == 403


def test_git_repos_empty_for_fresh_workspace(client, admin_headers):
    agent = _agent(client, admin_headers)
    res = client.get(f"/api/workspace/git/repos?agent_id={agent['id']}", headers=admin_headers)
    assert res.status_code == 200, res.text
    assert res.json() == []


def test_git_status_unknown_repo_404(client, admin_headers):
    agent = _agent(client, admin_headers)
    res = client.get(f"/api/workspace/git/status?agent_id={agent['id']}&repo=nope", headers=admin_headers)
    assert res.status_code == 404


def test_write_rejects_oversized_file(client, admin_headers):
    agent = _agent(client, admin_headers)
    big = "x" * (2 * 1024 * 1024 + 1)  # > 2 MB
    res = client.put("/api/workspace/file", headers=admin_headers,
                     json={"agent_id": agent["id"], "path": "big.txt", "content": big})
    assert res.status_code == 413


def test_git_commit_empty_message_rejected(client, admin_headers):
    agent = _agent(client, admin_headers)
    res = client.post("/api/workspace/git/commit", headers=admin_headers,
                      json={"agent_id": agent["id"], "message": "  "})
    assert res.status_code == 400


def test_git_status_rejects_foreign_agent(client, admin_headers, auth_headers):
    agent = _agent(client, admin_headers)
    res = client.get(f"/api/workspace/git/status?agent_id={agent['id']}", headers=auth_headers)
    assert res.status_code == 404
