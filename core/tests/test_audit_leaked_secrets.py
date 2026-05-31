"""Tests für das Secret-Audit-Skript: scannt messages + tool_calls + Observation-
JSONLs, bereinigt."""
from __future__ import annotations

import json

from hydrahive.db import init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db import tools as tools_db
from hydrahive.db.connection import db
from hydrahive.scripts import audit_leaked_secrets as audit
from hydrahive.settings import settings

LEAK = "sk-or-v1-" + "c" * 64


def _seed_observation(agent_id: str = "test-agent-001", session_id: str = "obs-sess"):
    obs_dir = settings.agents_dir / agent_id / "observations"
    obs_dir.mkdir(parents=True, exist_ok=True)
    obs_file = obs_dir / f"{session_id}.jsonl"
    obs_file.write_text(json.dumps({"tool_output": {"stdout": f"KEY={LEAK}"}}) + "\n", encoding="utf-8")
    return obs_file


def _seed():
    init_db()
    s = sessions_db.create(agent_id="test-agent-001", user_id="admin")
    m = messages_db.append(s.id, "assistant", f"output war OPENROUTER_API_KEY={LEAK}")
    tc = tools_db.create(m.id, "shell_exec", {}, session_id=s.id)
    tools_db.finish(tc.id, result={"stdout": f"KEY={LEAK}"}, status="success")
    return s.id, m.id, tc.id


def test_find_hits_findet_secret_in_message_und_tool_call():
    session_id, message_id, tool_call_id = _seed()
    hits = audit.find_hits()
    ids = {h.row_id for h in hits}
    assert message_id in ids
    assert tool_call_id in ids


def test_find_hits_maskiert_und_leakt_den_wert_nicht():
    _seed()
    hits = audit.find_hits()
    for h in hits:
        for masked in h.masked:
            assert LEAK not in masked


def test_redact_hits_entfernt_secret_aus_db():
    _seed()
    assert audit.redact_hits() >= 2
    with db() as conn:
        for source, col in (("messages", "content"), ("tool_calls", "result")):
            rows = conn.execute(f"SELECT {col} AS t FROM {source} WHERE {col} IS NOT NULL").fetchall()
            for row in rows:
                assert LEAK not in row["t"]


def test_find_hits_findet_secret_in_observation_jsonl():
    init_db()
    _seed_observation()
    hits = audit.find_hits()
    assert "observations" in {h.source for h in hits}


def test_redact_hits_bereinigt_observation_jsonl():
    init_db()
    obs_file = _seed_observation()
    audit.redact_hits()
    assert LEAK not in obs_file.read_text(encoding="utf-8")
