"""GET /api/agents/activity/{session_id}/trace — Live-Tool-Verlauf für den Büro-Drawer (Spec agent-office.md §2)."""
from __future__ import annotations

from hydrahive.agents import config as agent_config
from hydrahive.db import sessions as sessions_db
from hydrahive.db import tools as tools_db


def _login(client, user="testuser"):
    r = client.post("/api/auth/login", json={"username": user, "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_ohne_auth_401(client):
    assert client.get("/api/agents/activity/irgendwas/trace").status_code == 401


def test_fremde_session_404(client):
    a = agent_config.create(agent_type="specialist", name="X", llm_model="m", owner="boss",
                            temperature=0.7, max_tokens=1024, thinking_budget=0)
    s = sessions_db.create(agent_id=a["id"], user_id="boss")
    r = client.get(f"/api/agents/activity/{s.id}/trace", headers=_login(client, "testuser"))
    assert r.status_code == 404
    agent_config.delete(a["id"])


def test_unbekannte_session_404(client):
    r = client.get("/api/agents/activity/gibt-es-nicht/trace", headers=_login(client))
    assert r.status_code == 404


def test_liefert_tool_calls_der_eigenen_session_neueste_zuerst(client):
    a = agent_config.create(agent_type="specialist", name="X", llm_model="m", owner="testuser",
                            temperature=0.7, max_tokens=1024, thinking_budget=0)
    s = sessions_db.create(agent_id=a["id"], user_id="testuser")
    from hydrahive.db import messages as messages_db
    msg = messages_db.append(s.id, "assistant", [{"type": "text", "text": "x"}])
    c1 = tools_db.create(message_id=msg.id, tool_name="shell_exec", arguments={"cmd": "ls"},
                         session_id=s.id, agent_id=a["id"], user_id="testuser")
    tools_db.finish(c1.id, "ok", status="success", duration_ms=12)
    c2 = tools_db.create(message_id=msg.id, tool_name="file_read", arguments={"path": "x"},
                         session_id=s.id, agent_id=a["id"], user_id="testuser")
    tools_db.finish(c2.id, "nicht gefunden", status="error", duration_ms=3)

    r = client.get(f"/api/agents/activity/{s.id}/trace", headers=_login(client))
    assert r.status_code == 200
    body = r.json()
    assert [e["tool_name"] for e in body["calls"]] == ["file_read", "shell_exec"]
    assert body["calls"][0]["status"] == "error" and body["calls"][0]["duration_ms"] == 3
    agent_config.delete(a["id"])
