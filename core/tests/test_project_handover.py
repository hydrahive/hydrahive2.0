from pathlib import Path
from types import SimpleNamespace

import pytest

from hydrahive import handover


def test_write_read_redacts_and_uses_project_workspace(monkeypatch, tmp_path):
    workspace = tmp_path / "project"
    monkeypatch.setattr(handover, "ensure_workspace", lambda _pid: workspace)

    path = handover.write_project_handover(
        "p1", session_id="s1", agent_id="a1",
        summary="## Goal\nShip it\nAuthorization: Bearer secret-token",
    )

    assert path == workspace / ".hydrahive" / "HANDOVER.md"
    text = handover.read_project_handover("p1")
    assert text and "## Goal" in text
    assert "secret-token" not in text
    assert not list(path.parent.glob("*.tmp-*"))


def test_prompt_only_for_empty_project_session(monkeypatch):
    session = SimpleNamespace(id="s1", project_id="p1")
    monkeypatch.setattr(handover.sessions_db, "get", lambda _sid: session)
    monkeypatch.setattr(handover, "read_project_handover", lambda _pid: "state")
    monkeypatch.setattr(handover.messages_db, "list_for_session", lambda *_a, **_k: [])
    assert "state" in handover.prompt_for_new_session("s1")

    monkeypatch.setattr(handover.messages_db, "list_for_session", lambda *_a, **_k: [object()])
    assert handover.prompt_for_new_session("s1") is None


@pytest.mark.asyncio
async def test_create_for_session_summarizes_and_writes(monkeypatch, tmp_path):
    session = SimpleNamespace(id="s1", project_id="p1", agent_id="a1")
    monkeypatch.setattr(handover.sessions_db, "get", lambda _sid: session)
    monkeypatch.setattr(handover.messages_db, "list_for_llm", lambda _sid: [SimpleNamespace(role="user", content="goal")])
    monkeypatch.setattr(handover.messages_db, "get_latest_summary", lambda _sid: None)
    monkeypatch.setattr(handover, "ensure_workspace", lambda _pid: tmp_path)

    async def fake_summarize(**kwargs):
        assert "goal" in kwargs["serialized_history"]
        return "## Goal\nContinue"

    monkeypatch.setattr(handover, "summarize", fake_summarize)
    path = await handover.create_for_session("s1", model="test/model")
    assert path == tmp_path / ".hydrahive" / "HANDOVER.md"
    assert "Continue" in path.read_text()


@pytest.mark.asyncio
async def test_create_for_projectless_session_is_noop(monkeypatch):
    monkeypatch.setattr(handover.sessions_db, "get", lambda _sid: SimpleNamespace(project_id=None))
    assert await handover.create_for_session("s1", model="test/model") is None
