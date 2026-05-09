"""POST /api/voice/chat — Home Assistant Conversation Agent."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_key(client) -> str:
    """Erzeugt einen API-Key für admin (der die test-agent-001 ownt)."""
    from hydrahive.api.middleware.api_keys import create
    return create(name="ha-test", username="admin", role="admin")


@pytest.fixture
def user_api_key(client) -> str:
    """API-Key für testuser — der ownt KEIN Agent in der test-fixture."""
    from hydrahive.api.middleware.api_keys import create
    return create(name="ha-user", username="testuser", role="user")


@pytest.fixture
def fake_runner(monkeypatch):
    """Patch runner.run so it appends a fake assistant message + yields Done.

    Returns a callable that lets each test set what reply text the fake should
    produce. Default: 'Hallo aus dem Test'.
    """
    state = {"reply": "Hallo aus dem Test", "raise_error": None}

    def set_reply(text: str) -> None:
        state["reply"] = text

    def set_error(msg: str) -> None:
        state["raise_error"] = msg

    async def fake_run(session_id, user_input, *, tool_config=None, extra_system=None):
        from hydrahive.db import messages as messages_db
        from hydrahive.runner.events import Done, Error

        if state["raise_error"]:
            yield Error(message=state["raise_error"])
            return
        msg = messages_db.append(
            session_id, "assistant",
            [{"type": "text", "text": state["reply"]}],
        )
        yield Done(message_id=msg.id, iterations=1)

    monkeypatch.setattr("hydrahive.api.routes.voice.runner_run", fake_run)
    return type("FakeRunner", (), {"set_reply": staticmethod(set_reply),
                                   "set_error": staticmethod(set_error)})


def test_voice_chat_no_auth(client: TestClient):
    """Ohne Authorization-Header → 401."""
    r = client.post("/api/voice/chat", json={
        "text": "Hi", "conversation_id": "c1", "agent_id": "test-agent-001",
    })
    assert r.status_code == 401


def test_voice_chat_invalid_api_key(client: TestClient):
    """Ungültiger API-Key → 401."""
    r = client.post(
        "/api/voice/chat",
        headers={"Authorization": "Bearer hhk_thisisnotaregisteredkey"},
        json={"text": "Hi", "conversation_id": "c1", "agent_id": "test-agent-001"},
    )
    assert r.status_code == 401


def test_voice_chat_with_api_key_returns_reply(client: TestClient, api_key, fake_runner):
    """Gültiger Key + existierender Agent + funktionierender Runner → 200 + reply."""
    fake_runner.set_reply("Es ist 14 Uhr.")
    r = client.post(
        "/api/voice/chat",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"text": "Wie spät?", "conversation_id": "ha-conv-1",
              "agent_id": "test-agent-001"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["reply"] == "Es ist 14 Uhr."
    assert data["conversation_id"] == "ha-conv-1"
    assert data["end_conversation"] is False


def test_voice_chat_unknown_agent(client: TestClient, api_key, fake_runner):
    """Nicht existierender Agent → 404."""
    r = client.post(
        "/api/voice/chat",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"text": "Hi", "conversation_id": "c1", "agent_id": "does-not-exist"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "agent_not_found"


def test_voice_chat_foreign_agent_forbidden(
    client: TestClient, user_api_key, fake_runner
):
    """testuser versucht test-agent-001 (admin's) zu nutzen → 403."""
    r = client.post(
        "/api/voice/chat",
        headers={"Authorization": f"Bearer {user_api_key}"},
        json={"text": "Hi", "conversation_id": "c1", "agent_id": "test-agent-001"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "agent_no_access"


def test_voice_chat_conversation_mapping_persists(
    client: TestClient, api_key, fake_runner
):
    """Zwei Calls mit gleicher conversation_id → gleiche HydraHive-Session."""
    from hydrahive.settings import settings

    # Erster Call: legt Mapping an
    r1 = client.post(
        "/api/voice/chat",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"text": "Erste Frage", "conversation_id": "ha-stable",
              "agent_id": "test-agent-001"},
    )
    assert r1.status_code == 200

    map_path = settings.voice_conversations_path
    assert map_path.exists()
    data = json.loads(map_path.read_text())
    assert "ha-stable" in data
    sid_first = data["ha-stable"]["session_id"]

    # Zweiter Call mit gleicher conv-id → Mapping unverändert
    r2 = client.post(
        "/api/voice/chat",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"text": "Zweite Frage", "conversation_id": "ha-stable",
              "agent_id": "test-agent-001"},
    )
    assert r2.status_code == 200
    data2 = json.loads(map_path.read_text())
    assert data2["ha-stable"]["session_id"] == sid_first

    # Dritter Call mit anderer conv-id → neue Session
    r3 = client.post(
        "/api/voice/chat",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"text": "Andere Konversation", "conversation_id": "ha-other",
              "agent_id": "test-agent-001"},
    )
    assert r3.status_code == 200
    data3 = json.loads(map_path.read_text())
    assert data3["ha-other"]["session_id"] != sid_first


def test_voice_chat_runner_error_returns_500(
    client: TestClient, api_key, fake_runner
):
    """Runner-Error wird zu 500 voice_run_failed."""
    fake_runner.set_error("LLM nicht erreichbar")
    r = client.post(
        "/api/voice/chat",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"text": "Hi", "conversation_id": "c-err",
              "agent_id": "test-agent-001"},
    )
    assert r.status_code == 500
    assert r.json()["detail"]["code"] == "voice_run_failed"


def test_extract_text_helper():
    """_extract_text filtert tool_use-Blocks raus, joint text-Blocks."""
    from hydrahive.api.routes.voice import _extract_text

    blocks = [
        {"type": "text", "text": "Erst denke ich."},
        {"type": "tool_use", "id": "t1", "name": "shell", "input": {}},
        {"type": "text", "text": "Dann antworte ich."},
    ]
    assert _extract_text(blocks) == "Erst denke ich.\nDann antworte ich."

    assert _extract_text("string-direkt") == "string-direkt"
    assert _extract_text([]) == ""
    assert _extract_text([{"type": "tool_use"}]) == ""
