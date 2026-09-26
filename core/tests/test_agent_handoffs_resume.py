from hydrahive.db import agent_handoffs, init_db, sessions
from hydrahive.db.connection import db
from hydrahive.settings import settings


def test_resume_claim_is_bound_and_single_use(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "sessions.db")
    init_db()
    session = sessions.create(agent_id="spec-1", user_id="u")
    handoff = agent_handoffs.create(
        incoming_state_id="state-1",
        from_agent="hydrahive/project-a",
        agent_id="spec-1",
        session_id=session.id,
    )
    agent_handoffs.update_status(handoff["id"], "paused")

    assert agent_handoffs.claim_resumable(
        handoff["id"], from_agent="hydrahive/project-b", agent_id="spec-1",
    ) is None
    assert agent_handoffs.claim_resumable(
        handoff["id"], from_agent="hydrahive/project-a", agent_id="other",
    ) is None

    claimed = agent_handoffs.claim_resumable(
        handoff["id"], from_agent="hydrahive/project-a", agent_id="spec-1",
    )
    assert claimed is not None
    assert claimed["session_id"] == session.id
    assert agent_handoffs.claim_resumable(
        handoff["id"], from_agent="hydrahive/project-a", agent_id="spec-1",
    ) is None

    assert agent_handoffs.restore_paused_claim(handoff["id"]) is True
    assert agent_handoffs.claim_resumable(
        handoff["id"], from_agent="hydrahive/project-a", agent_id="spec-1",
    ) is not None

    with db() as conn:
        status = conn.execute(
            "SELECT status FROM agent_handoffs WHERE id = ?", (handoff["id"],),
        ).fetchone()["status"]
    assert status == "resumed"
