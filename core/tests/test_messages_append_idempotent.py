from __future__ import annotations

import pytest

from hydrahive.db import messages as messages_db


@pytest.fixture
def session_id(client, auth_headers):
    r = client.post("/api/sessions", json={"agent_id": "test-agent-001"}, headers=auth_headers)
    assert r.status_code == 201
    return r.json()["id"]


def test_append_with_explicit_id_is_idempotent(session_id):
    m1 = messages_db.append(session_id, "user", "hallo", message_id="fixed-1")
    m2 = messages_db.append(session_id, "user", "hallo", message_id="fixed-1")
    assert m1.id == "fixed-1"
    assert m2.id == "fixed-1"
    msgs = messages_db.list_for_session(session_id)
    assert len([m for m in msgs if m.id == "fixed-1"]) == 1


def test_append_without_id_generates_unique_ids(session_id):
    a = messages_db.append(session_id, "user", "eins")
    b = messages_db.append(session_id, "user", "zwei")
    assert a.id != b.id
    ids = {m.id for m in messages_db.list_for_session(session_id)}
    assert {a.id, b.id} <= ids


def test_append_honours_explicit_created_at(session_id):
    m = messages_db.append(session_id, "user", "x", message_id="ts-1",
                           created_at="2025-11-01T08:00:00Z")
    assert m.created_at == "2025-11-01T08:00:00Z"
    got = messages_db.get("ts-1")
    assert got is not None and got.created_at == "2025-11-01T08:00:00Z"
