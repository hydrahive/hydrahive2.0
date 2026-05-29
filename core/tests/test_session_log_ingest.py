from __future__ import annotations

import asyncio
import inspect
from unittest.mock import patch

import pytest

from hydrahive.db import messages as messages_db, mirror
from hydrahive.api.routes import sessions_messages
from tests.conftest import error_code


@pytest.fixture
def session_id(client, auth_headers):
    r = client.post("/api/sessions", json={"agent_id": "test-agent-001"}, headers=auth_headers)
    assert r.status_code == 201
    return r.json()["id"]


def test_owner_can_log_text_message(client, auth_headers, session_id):
    r = client.post(f"/api/sessions/{session_id}/log",
                    json={"role": "user", "content": "hallo welt", "message_id": "u-1"},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "message_id": "u-1"}
    msgs = client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers).json()
    assert any(m["id"] == "u-1" and m["content"] == "hallo welt" for m in msgs)


def test_log_is_idempotent(client, auth_headers, session_id):
    body = {"role": "user", "content": "doppelt", "message_id": "dup-1"}
    client.post(f"/api/sessions/{session_id}/log", json=body, headers=auth_headers)
    client.post(f"/api/sessions/{session_id}/log", json=body, headers=auth_headers)
    msgs = client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers).json()
    assert len([m for m in msgs if m["id"] == "dup-1"]) == 1


def test_log_accepts_assistant_block_content(client, auth_headers, session_id):
    blocks = [
        {"type": "text", "text": "ich rufe ein tool"},
        {"type": "tool_use", "id": "tu_1", "name": "Bash", "input": {"command": "ls"}},
    ]
    r = client.post(f"/api/sessions/{session_id}/log",
                    json={"role": "assistant", "content": blocks, "message_id": "a-1"},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    msgs = client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers).json()
    logged = next(m for m in msgs if m["id"] == "a-1")
    assert logged["content"][1]["name"] == "Bash"


def test_log_unknown_session_404(client, auth_headers):
    r = client.post("/api/sessions/does-not-exist/log",
                    json={"role": "user", "content": "x"}, headers=auth_headers)
    assert r.status_code == 404
    assert error_code(r) == "session_not_found"


def test_log_non_owner_403(client, auth_headers, admin_headers):
    r = client.post("/api/sessions", json={"agent_id": "test-agent-001"}, headers=admin_headers)
    admin_sid = r.json()["id"]
    r = client.post(f"/api/sessions/{admin_sid}/log",
                    json={"role": "user", "content": "fremd"}, headers=auth_headers)
    assert r.status_code == 403
    assert error_code(r) == "session_no_access"


def test_log_invalid_role_422(client, auth_headers, session_id):
    r = client.post(f"/api/sessions/{session_id}/log",
                    json={"role": "system", "content": "nope"}, headers=auth_headers)
    assert r.status_code == 422


def test_log_ingest_is_async_for_mirror_loop():
    """Regression-Guard: schedule_message braucht einen laufenden Event-Loop.
    Als sync def liefe der Endpoint im Threadpool ohne Loop → Mirror still
    verworfen, Datamining bliebe leer (genau der Zweck des Endpoints)."""
    assert inspect.iscoroutinefunction(sessions_messages.log_ingest)


def test_append_schedules_mirror_write_when_pool_active(client, auth_headers, session_id):
    """Deckt den in Prod relevanten Pfad ab (Mirror aktiv): append in einem
    laufenden Loop mit gesetztem _pool MUSS write_message tatsächlich aufrufen.
    Dieser Pfad war vorher ungetestet (Tests laufen sonst mit _pool=None)."""
    seen: list[str] = []

    async def fake_write(pool, m, s):
        seen.append(m.id)

    async def drive():
        with patch.object(mirror, "_pool", object()), \
             patch.object(mirror, "write_message", fake_write):
            messages_db.append(session_id, "user", "x", message_id="mir-1")
            await asyncio.sleep(0)  # dem fire-and-forget-Task einen Tick geben

    asyncio.run(drive())
    assert seen == ["mir-1"]
