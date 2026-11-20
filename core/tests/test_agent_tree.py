"""Agenten-Baum (runner/agent_tree.py, GET /sessions/{sid}/delegations/tree).

Till 20.11.2026: „ich sehe in keinster Weise, was die Agenten tun“. Der Baum zeigt alle
Ebenen mit Kosten, Befehlen im Klartext und markiert riskante bzw. gesperrte Befehle.
"""
from __future__ import annotations

import uuid

from hydrahive.db import agent_handoffs as handoffs_db
from hydrahive.db import delegations as delegations_db
from hydrahive.db import init_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db import tools as tools_db
from hydrahive.db.connection import db
from hydrahive.runner import agent_tree
from hydrahive.tools import _shell_guard

pytest_plugins = ["tests.test_background_delegation"]


def _session(title: str) -> str:
    return sessions_db.create(agent_id="test-agent-001", user_id="admin", title=title).id


def _delegate(parent: str, depth: int, name: str) -> tuple[dict, str]:
    state_id = f"st-{uuid.uuid4().hex}"
    d = delegations_db.create(session_id=parent, agent_id="a", user_id="admin", target_agent_id=name,
                              target_name=name, task="t", state_id=state_id, depth=depth, timeout_seconds=600)
    sid = _session(name)
    handoffs_db.create(incoming_state_id=state_id, from_agent="hydrahive", agent_id=name, session_id=sid)
    return d, sid


def _llm(sid: str, cost_micros: int, model: str = "claude-sonnet-5") -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO llm_calls (id, session_id, created_at, provider, model, completion_tokens, cost_micros)
               VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now','+1 second'), 'test', ?, 100, ?)""",
            (uuid.uuid4().hex, sid, model, cost_micros),
        )


def _tool(sid: str, cmd: str, error: str | None = None) -> None:
    tc = tools_db.create(message_id=messages_db.append(sid, "assistant", "x").id, tool_name="shell_exec", arguments={"cmd": cmd},
                         session_id=sid)
    tools_db.finish(tc.id, result={"ok": error is None}, status="error" if error else "success",
                    error_message=error)


def test_baum_zeigt_alle_ebenen_kosten_und_riskante_befehle(client):
    init_db()
    buddy = _session("buddy")
    pa, pa_sid = _delegate(buddy, 1, "Projekt-Agent")
    sp, sp_sid = _delegate(pa_sid, 2, "backend-engineer")
    _llm(pa_sid, 2_350_000, "claude-opus-5-5")
    _llm(sp_sid, 1_440_000)
    _tool(sp_sid, "pytest -q")
    _tool(sp_sid, 'ssh 192.168.178.197 "sudo -u hydrahive cat /etc/hydrahive2/pg_mirror.dsn"')
    _tool(sp_sid, "ssh host ls", error=f"Zugriff gesperrt. {_shell_guard.BLOCK_MARKER} nach Vorfall).")

    tree = agent_tree.build(buddy, "admin")

    assert tree["summary"]["active"] == 2 and tree["summary"]["total"] == 2
    root = tree["nodes"][0]
    assert root["target_name"] == "Projekt-Agent" and root["children"][0]["target_name"] == "backend-engineer"
    assert root["cost"]["cost_usd"] == 2.35 and root["children"][0]["cost"]["cost_usd"] == 1.44
    assert tree["summary"]["cost_usd_active_chains"] == 3.79
    flagged = root["children"][0]["flagged_tools"]
    assert len(flagged) == 2 and flagged[0]["risky"] and flagged[1]["blocked"]
    assert tree["summary"]["risky_commands"] == 2
    assert root["children"][0]["tool_count"] == 3


def test_geheimnisse_in_befehlen_werden_geschwaerzt():
    assert "geheim123" not in agent_tree.redact("psql postgresql://u:geheim123@127.0.0.1/db")
    assert "abc" not in agent_tree.redact("HH_SECRET_KEY=abc echo")
    assert "pw" not in agent_tree.redact("sshpass -p pw ssh host")
    assert agent_tree.redact("pytest -q") == "pytest -q"


def test_kosten_nur_im_zeitfenster_des_auftrags(client):
    """Fortgesetzte Aufträge teilen die Ziel-Session: ein fertiger Auftrag zählt keine späteren Kosten."""
    init_db()
    buddy = _session("buddy")
    d, sid = _delegate(buddy, 1, "spez")
    _llm(sid, 1_000_000)
    with db() as conn:
        conn.execute("UPDATE agent_delegations SET status='done', finished_at=strftime('%Y-%m-%dT%H:%M:%fZ','now','+2 seconds') WHERE id=?", (d["id"],))
        conn.execute("""INSERT INTO llm_calls (id, session_id, created_at, provider, model, completion_tokens, cost_micros)
                        VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now','+1 hour'), 'test', 'm', 1, 9000000)""", (uuid.uuid4().hex, sid))
    node = agent_tree.build(buddy, "admin")["nodes"][0]
    assert node["cost"]["cost_usd"] == 1.0


def test_route_liefert_baum_nur_dem_besitzer(client, admin_headers, auth_headers):
    init_db()
    sid = sessions_db.create(agent_id="test-agent-001", user_id="admin", title="x").id
    r = client.get(f"/api/sessions/{sid}/delegations/tree", headers=admin_headers)
    assert r.status_code == 200 and r.json()["summary"]["total"] == 0
    fremd = client.get(f"/api/sessions/{sid}/delegations/tree", headers=auth_headers)
    assert fremd.status_code in (403, 404)                     # fremde Session: kein Einblick
