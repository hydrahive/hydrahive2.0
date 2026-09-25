"""GET /sessions/{id}/messages muss begrenzbar sein.

Ohne Limit lud der Chat bei jedem Reload den kompletten Verlauf — in einer real
gemessenen Session 9.667 Nachrichten / 41 MB. Das blockierte den Browser und ließ
frisch gesendete Nachrichten scheinbar verschwinden.
"""
from __future__ import annotations

from tests.conftest import error_code


def _session_with(client, headers, n):
    res = client.post("/api/sessions", headers=headers,
                      json={"agent_id": "test-agent-001", "title": "lang"})
    assert res.status_code in (200, 201), res.text
    sid = res.json()["id"]
    from hydrahive.db import messages as messages_db
    for i in range(n):
        messages_db.append(sid, "user", f"m{i:03d}")
    return sid


def test_limit_returns_only_newest_messages(client, admin_headers):
    sid = _session_with(client, admin_headers, 30)

    res = client.get(f"/api/sessions/{sid}/messages?limit=5", headers=admin_headers)

    assert res.status_code == 200
    body = res.json()
    assert len(body) == 5
    assert [m["content"] for m in body] == ["m025", "m026", "m027", "m028", "m029"]


def test_without_limit_everything_is_returned(client, admin_headers):
    sid = _session_with(client, admin_headers, 12)

    res = client.get(f"/api/sessions/{sid}/messages", headers=admin_headers)

    assert res.status_code == 200
    assert len(res.json()) == 12


def test_limit_is_bounded(client, admin_headers):
    sid = _session_with(client, admin_headers, 3)

    assert client.get(f"/api/sessions/{sid}/messages?limit=0",
                      headers=admin_headers).status_code == 422
    assert client.get(f"/api/sessions/{sid}/messages?limit=100000",
                      headers=admin_headers).status_code == 422


def test_limit_still_requires_ownership(client, auth_headers, admin_headers):
    sid = _session_with(client, admin_headers, 3)

    res = client.get(f"/api/sessions/{sid}/messages?limit=2", headers=auth_headers)

    assert res.status_code == 403
    assert error_code(res) == "session_no_access"
