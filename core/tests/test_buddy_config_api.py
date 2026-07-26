from __future__ import annotations


def _ensure_buddy(client, headers):
    response = client.get("/api/buddy/state", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_buddy_config_requires_authentication(client):
    assert client.get("/api/buddy/config").status_code == 401
    assert client.patch("/api/buddy/config", json={"temperature": 0.5}).status_code == 401


def test_buddy_owner_can_read_and_patch_full_safe_config(client, auth_headers):
    state = _ensure_buddy(client, auth_headers)

    response = client.get("/api/buddy/config", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["agent_id"] == state["agent_id"]

    patched = client.patch(
        "/api/buddy/config",
        headers=auth_headers,
        json={
            "temperature": 0.5,
            "max_tokens": 10_000,
            "require_tool_confirm": True,
            "longterm_memory": False,
            "disabled_skills": ["debugging"],
            "mcp_servers": ["docs"],
        },
    )
    assert patched.status_code == 200

    current = client.get("/api/buddy/config", headers=auth_headers).json()
    assert current["temperature"] == 0.5
    assert current["max_tokens"] == 10_000
    assert current["require_tool_confirm"] is True
    assert current["longterm_memory"] is False
    assert current["disabled_skills"] == ["debugging"]
    assert current["mcp_servers"] == ["docs"]


def test_buddy_config_rejects_protected_or_invalid_fields(client, auth_headers):
    _ensure_buddy(client, auth_headers)

    protected = client.patch(
        "/api/buddy/config", headers=auth_headers, json={"owner": "admin"}
    )
    invalid = client.patch(
        "/api/buddy/config", headers=auth_headers, json={"temperature": 9}
    )

    assert protected.status_code == 422
    assert invalid.status_code == 422
