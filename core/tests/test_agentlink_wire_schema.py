"""ask_agent-Payload gegen das echte AgentLink-Schema (Task 54c50a91).

Befund 21.11.2026: Aufträge an Spezialisten „auf Abruf“ (Security) und mit
Budget-Überschreitung scheiterten mit ``AgentLink 422`` bei ``POST /states``.
HydraHive legte Text in ``context.errors``, AgentLink erwartet dort Objekte
``ErrorContext{type, message, stack?}``. Die Tests prüfen die Payload genau so,
wie ``post_state`` sie sendet, gegen eine Kopie des AgentLink-Modells
(``_agentlink_schema.py``, Begründung dort).
"""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path

import pytest

from tests import _agentlink_schema as al
import httpx
from pydantic import ValidationError

from hydrahive.agentlink import client as al_client
from hydrahive.agentlink import signing
from hydrahive.agentlink.protocol import ContextBlock, Handoff, State, TaskBlock
from hydrahive.agents import config as agent_config
from hydrahive.tools import ToolContext, ask_agent

def _find_original() -> Path | None:
    """Original-Schema, falls ``hydralink-work`` in einem Elternordner liegt (Workspace, nicht CI)."""
    for parent in Path(__file__).resolve().parents:
        cand = parent / "hydralink-work" / "agentlink" / "backend" / "main.py"
        if cand.is_file():
            return cand
    return None


_ORIGINAL = _find_original()


class _FakeAgentLink:
    """Steht für ``POST /states`` von AgentLink: validiert gegen ``AgentState`` (422 wie
    FastAPI) und gibt den gespeicherten State zurück (``response_model=AgentState``)."""

    def __init__(self) -> None:
        self.bodies: list[dict] = []
        self.stored: list[al.AgentState] = []

    def client(self, *a, **kw):
        link = self

        class _Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, json=None, headers=None):
                link.bodies.append(json)
                req = httpx.Request("POST", url)
                try:
                    st = al.AgentState.model_validate(json)
                except ValidationError as e:
                    return httpx.Response(422, json={"detail": e.errors(include_url=False)}, request=req)
                link.stored.append(st)
                return httpx.Response(200, json=st.model_dump(mode="json"), request=req)

        return _Client()


@pytest.fixture
def link(monkeypatch):
    fake = _FakeAgentLink()

    def fake_register_pending(state_id: str, expected: str = ""):
        fut = asyncio.get_running_loop().create_future()
        fut.set_result(State(agent_id="x", task=TaskBlock(type="review", description="ok", status="done")))
        return fut

    monkeypatch.setattr(ask_agent.settings, "agentlink_url", "http://agentlink.test", raising=False)
    monkeypatch.setattr(ask_agent.settings, "agentlink_agent_id", "hydrahive", raising=False)
    monkeypatch.setattr(al_client.httpx, "AsyncClient", fake.client)
    monkeypatch.setattr(ask_agent, "register_pending", fake_register_pending)
    return fake


def _agent(template: str | None = None) -> dict:
    return agent_config.create(agent_type="specialist", name=f"Wire {template}", llm_model="m", owner="testuser",
                               temperature=0.7, max_tokens=1024, thinking_budget=0, template=template)


def _run(args: dict, tmp_path):
    ctx = ToolContext(session_id="s", agent_id="test-agent-user", user_id="testuser", workspace=tmp_path)
    return asyncio.run(ask_agent._execute({"task": "Prüfe die Route", "goal": "Lücken finden",
                                           "deliverable": "Befunde", "wait": True, **args}, ctx))


def _post(state: State) -> State:
    """Echtes ``post_state`` (signiert, serialisiert) gegen den nachgebildeten AgentLink."""
    return asyncio.run(al_client.post_state(state))


def test_on_demand_auftrag_wird_angenommen(client, link, tmp_path):
    a = _agent("security")
    try:
        res = _run({"agent_id": a["id"], "task_type": "review",
                    "on_demand_reason": "Neue Auth-Route"}, tmp_path)
        assert res.success is True, res.error
        assert any("Auf Abruf: Neue Auth-Route" in e.message for e in link.stored[0].context.errors)
    finally:
        agent_config.delete(a["id"])


def test_overrun_auftrag_wird_angenommen(client, link, tmp_path):
    a = _agent()
    try:
        res = _run({"agent_id": a["id"], "overrun": True,
                    "overrun_reason": "Review über 40 Dateien"}, tmp_path)
        assert res.success is True, res.error
        assert any("Review über 40 Dateien" in e.message for e in link.stored[0].context.errors)
    finally:
        agent_config.delete(a["id"])


def test_map_context_errors_und_error_log_werden_angenommen(client, link, tmp_path):
    a = _agent()
    try:
        res = _run({"agent_id": a["id"], "context": {"errors": ["e1"], "error_log": "Traceback …"}}, tmp_path)
        assert res.success is True, res.error
        assert [e.message for e in link.stored[0].context.errors] == ["e1", "Traceback …"]
    finally:
        agent_config.delete(a["id"])


def test_signatur_ueberlebt_die_rundreise(client, link, tmp_path):
    """Der Empfänger prüft die Signatur am State, den AgentLink zurückgibt."""
    a = _agent("security")
    try:
        res = _run({"agent_id": a["id"], "task_type": "review", "on_demand_reason": "Neue Auth-Route",
                    "context": {"error_log": "log"}}, tmp_path)
        assert res.success is True, res.error
        back = State.model_validate(link.stored[0].model_dump(mode="json"))
        assert signing.is_valid(back)
    finally:
        agent_config.delete(a["id"])


def test_empfaenger_liest_hinweise(link):
    from hydrahive.runner.handoff_receiver import _build_user_input
    back = _post(State(
        agent_id="a", task=TaskBlock(type="review", description="X"),
        context=ContextBlock(errors=["Auf Abruf: Auth-Route"]),
        handoff=Handoff(to_agent="hydrahive", reason="hh-target:z")))
    assert signing.is_valid(back)
    assert "Auf Abruf: Auth-Route" in _build_user_input(back)


def test_alte_text_eintraege_brechen_nichts(link):
    """States mit Text in errors (alter Stand, Tests, eigene Aufrufer) bleiben lesbar und sendbar."""
    s = State(agent_id="a", task=TaskBlock(type="feature", description="X"),
              context=ContextBlock(errors=["boom", {"type": "error_log", "message": "log"}]))
    assert [e.message for e in s.context.errors] == ["boom", "log"]
    _post(s)


@pytest.mark.skipif(_ORIGINAL is None, reason="hydralink-work liegt nicht neben dem Repo")
def test_kopie_entspricht_agentlink():
    def classes(src: str) -> dict[str, str]:
        tree = ast.parse(src)
        return {n.name: ast.dump(n) for n in tree.body if isinstance(n, ast.ClassDef)}

    copy = classes((Path(__file__).parent / "_agentlink_schema.py").read_text(encoding="utf-8"))
    orig = classes(_ORIGINAL.read_text(encoding="utf-8"))
    for name, dumped in copy.items():
        assert orig.get(name) == dumped, f"{name} weicht vom AgentLink-Original ab"
