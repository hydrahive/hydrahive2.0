"""/tokens-Endpoint macht das Turn-Netz sichtbar.

Compaction feuert auch bei message_count >= max_turns (window-skaliert), nicht
nur an der Token-Schwelle. Der Endpoint liefert beide Zahlen, damit der
TokenMeter einen turn-getriggerten Compact nicht als „verfrüht" erscheinen lässt.
"""
from __future__ import annotations

import pytest

from hydrahive.db import messages as messages_db


@pytest.fixture
def session_id(client, auth_headers):
    r = client.post("/api/sessions", json={"agent_id": "test-agent-001"}, headers=auth_headers)
    return r.json()["id"]


def test_tokens_endpoint_reports_message_count_and_max_turns(client, auth_headers, session_id):
    for i in range(3):
        messages_db.append(session_id, "user", f"nachricht {i}")

    r = client.get(f"/api/sessions/{session_id}/tokens", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["message_count"] == 3
    # test-agent-001 läuft auf einem 200k-Modell → window-skalierter Floor 1000.
    assert body["max_turns"] == 1000
