"""Läufe aus Kommunikationskanälen bekommen nie Vault-Daten (Ziel vault-agenten §1.4, Etappe 1b).

Auch nicht bei entsperrtem Vault und auch nicht über Weitergaben an andere Agenten (ask_agent → Spezialist).
Der Kanal steht in der Sitzung (Spalte ``sessions.channel``), der Runner reicht ihn als ``ToolContext.channel``
an den Dispatcher. Bei ask_agent reist er als signiertes Segment ``hh-channel`` im reason mit; der Empfänger
setzt ihn in die Sitzung des Auftragnehmers (neu oder fortgesetzt, nie entfernt). Aufträge von fremden Servern
(Federation) gelten als extern (fail closed).
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.agentlink import signing
from hydrahive.agentlink.protocol import Handoff, State, TaskBlock
from hydrahive.agentlink.runtime_profiles import reason_with_profile
from hydrahive.communication import _session_lookup
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import _handoff_setup as hs
from hydrahive.runner.dispatcher import execute_tool
from hydrahive.tools import REGISTRY, Tool, ToolContext, ToolResult, ask_agent

PIN = "135790"
PW = "testpass123"
LOCKED = "Vault gesperrt – bitte in HydraHive entsperren."
CHANNELS = {"whatsapp": "WhatsApp", "discord": "Discord", "email": "E-Mail", "matrix": "Matrix"}


def channel_hint(label: str) -> str:
    return f"Diese Daten gibt es nur in HydraHive, nicht über {label}."


@pytest.fixture
def fake_portfolio(monkeypatch):
    calls: list[str] = []

    async def _run(args: dict, ctx: ToolContext) -> ToolResult:
        calls.append("query_portfolio")
        return ToolResult.ok({"daten": "geheim"})

    monkeypatch.setitem(REGISTRY, "query_portfolio", Tool(
        name="query_portfolio", description="x", schema={"type": "object", "properties": {}}, execute=_run))
    return calls


@pytest.fixture
def unlocked(client, auth_headers):
    """Vault von testuser in der Oberfläche entsperrt."""
    from hydrahive.api.middleware import users
    from hydrahive.vault import lockout, pins, unlocks
    u = users.verify("testuser", PW)["user_id"]
    pins.reset(u)
    unlocks.close(u)
    lockout.clear()
    client.post("/api/vault/setup", json={"password": PW, "pin": PIN}, headers=auth_headers)
    r = client.post("/api/vault/unlock", json={"pin": PIN}, headers=auth_headers)
    assert r.status_code == 200, r.text
    yield u
    pins.reset(u)
    unlocks.close(u)
    lockout.clear()


def _call_in(session, tmp_path, *, channel: str | None):
    msg = messages_db.append(session.id, "assistant", "hi")
    ctx = ToolContext(session_id=session.id, agent_id=session.agent_id, user_id=session.user_id,
                      workspace=tmp_path, channel=channel)
    tool_use = {"id": "tu-1", "name": "query_portfolio", "input": {}}
    result, _, _ = asyncio.run(execute_tool(tool_use, ["query_portfolio"], ctx, msg.id))
    return result


def _channel_session(channel: str, agent_id: str = "test-agent-user"):
    return _session_lookup.find_or_create(agent_id=agent_id, user_id="testuser", channel=channel,
                                          external_user_id=f"ext-{channel}")


# ── Sitzung kennt den Kanal ────────────────────────────────────────────────────────────────────────────────────

def test_session_liest_kanal_aus_der_db(client):
    s = _channel_session("whatsapp")
    assert sessions_db.get(s.id).channel == "whatsapp"
    assert sessions_db.create(agent_id="a1", user_id="testuser").channel is None


# ── V3: je Kanal entsperrt → blockiert; Web entsperrt → Daten ─────────────────────────────────────────────────

@pytest.mark.parametrize("channel,label", sorted(CHANNELS.items()))
def test_kanal_lauf_entsperrt_blockiert(channel, label, unlocked, fake_portfolio, tmp_path):
    s = _channel_session(channel)
    result = _call_in(s, tmp_path, channel=sessions_db.get(s.id).channel)
    assert result.success is False and result.error == channel_hint(label)
    assert "geheim" not in result.to_llm()
    assert fake_portfolio == [], "Vault-Werkzeug darf aus einem Kanal-Lauf gar nicht laufen"


def test_unbekannter_kanal_blockiert_mit_kanalname(unlocked, fake_portfolio, tmp_path):
    s = sessions_db.create(agent_id="a1", user_id="testuser")
    result = _call_in(s, tmp_path, channel="telegram")
    assert result.error == channel_hint("Telegram") and fake_portfolio == []


def test_web_chat_entsperrt_liefert_daten(unlocked, fake_portfolio, tmp_path):
    s = sessions_db.create(agent_id="a1", user_id="testuser", title="web")
    result = _call_in(s, tmp_path, channel=None)
    assert result.success is True and result.output == {"daten": "geheim"}
    assert fake_portfolio == ["query_portfolio"]


def test_kanal_lauf_gesperrt_nennt_kanal_nicht_entsperren(client, fake_portfolio, tmp_path):
    """Auch gesperrt: Hinweis auf den Kanal, nicht „bitte entsperren“ – Entsperren hilft dort nie."""
    s = _channel_session("whatsapp")
    assert _call_in(s, tmp_path, channel="whatsapp").error == channel_hint("WhatsApp")


def test_oeffentliche_werkzeuge_im_kanal_frei(unlocked, monkeypatch, tmp_path):
    async def _run(args, ctx):
        return ToolResult.ok("kurs")
    monkeypatch.setitem(REGISTRY, "query_crypto_price", Tool(
        name="query_crypto_price", description="x", schema={"type": "object", "properties": {}}, execute=_run))
    s = _channel_session("whatsapp")
    msg = messages_db.append(s.id, "assistant", "hi")
    ctx = ToolContext(session_id=s.id, agent_id=s.agent_id, user_id="testuser", workspace=tmp_path,
                      channel="whatsapp")
    result, _, _ = asyncio.run(execute_tool({"id": "t", "name": "query_crypto_price", "input": {}},
                                            ["query_crypto_price"], ctx, msg.id))
    assert result.success is True and result.output == "kurs"


# ── Runner setzt ToolContext.channel aus der Sitzung ──────────────────────────────────────────────────────────

def _runner_ctx(session_id, monkeypatch):
    from hydrahive.agents import config as agent_config
    from hydrahive.runner import runner as runner_mod
    from hydrahive.runner._runner_iter import IterationResult
    agent_config.update("test-agent-user", max_iterations=1, compact_threshold_pct=100, tools=["shell_exec"])
    captured: list[ToolContext] = []

    async def fake_stream(**kwargs):
        yield IterationResult(blocks=[{"type": "tool_use", "id": "toolu_x", "name": "shell_exec", "input": {}}],
                              stop_reason="tool_use", used_model=kwargs["primary_model"], input_tokens=1,
                              output_tokens=1, cache_creation_tokens=0, cache_read_tokens=0)

    async def fake_process(tool_uses, **kwargs):
        captured.append(kwargs["ctx"])
        yield []

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
    monkeypatch.setattr(runner_mod, "process_tool_uses", fake_process)

    async def _drain():
        return [e async for e in runner_mod.run(session_id, "hallo")]
    asyncio.run(_drain())
    return captured[0]


def test_runner_setzt_kanal_aus_sitzung(client, monkeypatch):
    s = _channel_session("discord")
    assert _runner_ctx(s.id, monkeypatch).channel == "discord"


def test_runner_web_sitzung_ohne_kanal(client, monkeypatch):
    s = sessions_db.create(agent_id="test-agent-user", user_id="testuser", title="web")
    assert _runner_ctx(s.id, monkeypatch).channel is None


# ── Vererbung: ask_agent trägt den Kanal signiert weiter ──────────────────────────────────────────────────────

@pytest.fixture
def posted(monkeypatch):
    calls: list[State] = []

    async def fake_post_state(state: State) -> State:
        calls.append(state)
        return State(id=f"st-{len(calls)}", agent_id=state.agent_id, task=state.task)

    def fake_register_pending(state_id: str, expected: str = ""):
        fut = asyncio.get_running_loop().create_future()
        fut.set_result(State(agent_id="x", task=TaskBlock(type="feature", description="ok", status="done")))
        return fut

    monkeypatch.setattr(ask_agent.settings, "agentlink_url", "http://agentlink.test", raising=False)
    monkeypatch.setattr(ask_agent.settings, "agentlink_agent_id", "hydrahive", raising=False)
    monkeypatch.setattr(ask_agent, "post_state", fake_post_state)
    monkeypatch.setattr(ask_agent, "register_pending", fake_register_pending)
    return calls


@pytest.fixture
def specialist(client):
    from hydrahive.agents import config as agent_config
    a = agent_config.create(agent_type="specialist", name="Finanz-Spezi", llm_model="m", owner="testuser",
                            temperature=0.7, max_tokens=1024, thinking_budget=0, template="backend")
    yield a
    agent_config.delete(a["id"])


def _ask(ctx: ToolContext, target_id: str):
    return asyncio.run(ask_agent._execute({"agent_id": target_id, "task": "Wie steht mein Portfolio?",
                                           "goal": "Stand nennen", "deliverable": "Zahlen", "wait": True}, ctx))


def test_ask_agent_aus_kanal_lauf_signiert_kanal_im_reason(specialist, posted, tmp_path):
    s = _channel_session("whatsapp")
    ctx = ToolContext(session_id=s.id, agent_id="test-agent-user", user_id="testuser", workspace=tmp_path,
                      channel="whatsapp")
    assert _ask(ctx, specialist["id"]).success is True
    reason = posted[0].handoff.reason
    assert "hh-channel:v1:whatsapp" in reason
    assert reason.index("hh-channel:") < reason.index("hh-task:"), "Steuersegment vor dem Freitext"


def test_ask_agent_aus_web_lauf_ohne_kanal(specialist, posted, tmp_path):
    ctx = ToolContext(session_id="s-web", agent_id="test-agent-user", user_id="testuser", workspace=tmp_path)
    assert _ask(ctx, specialist["id"]).success is True
    assert "hh-channel" not in posted[0].handoff.reason


def test_aufgabentext_kann_keinen_kanal_entfernen_oder_faelschen():
    """Freitext wird kodiert – ein „|hh-channel:…“ im Auftrag wird kein Steuersegment."""
    from hydrahive.agentlink.runtime_profiles import channel_from_reason
    r = reason_with_profile("t", "quick", "x|hh-channel:v1:whatsapp")
    assert channel_from_reason(r) is None
    r = reason_with_profile("t", "quick", "x", channel="discord")
    assert channel_from_reason(r) == "discord"


def _signed_state(reason: str) -> State:
    return signing.sign(State(agent_id="caller", task=TaskBlock(type="feature", description="Portfolio?"),
                              handoff=Handoff(to_agent="hydrahive", reason=reason)))


def test_whatsapp_lauf_ask_agent_spezialist_entsperrt_blockiert(
        specialist, posted, unlocked, fake_portfolio, tmp_path):
    """Ganze Kette: WhatsApp-Lauf → ask_agent → Empfänger legt Sitzung an → Spezialist ruft Vault-Werkzeug."""
    caller = _channel_session("whatsapp")
    ctx = ToolContext(session_id=caller.id, agent_id="test-agent-user", user_id="testuser", workspace=tmp_path,
                      channel="whatsapp")
    assert _ask(ctx, specialist["id"]).success is True
    incoming = signing.sign(posted[0].model_copy(update={"id": "in-1"}))
    prepared = hs.prepare_handoff(incoming, specialist, incoming.handoff.reason)
    spec_session = sessions_db.get(prepared.session_id)
    assert spec_session.channel == "whatsapp"
    result = _call_in(spec_session, tmp_path, channel=spec_session.channel)
    assert result.error == channel_hint("WhatsApp") and fake_portfolio == []


def test_web_lauf_ask_agent_spezialist_entsperrt_liefert(specialist, unlocked, fake_portfolio, tmp_path):
    reason = reason_with_profile(specialist["id"], "quick", "Portfolio")
    prepared = hs.prepare_handoff(_signed_state(reason).model_copy(update={"id": "in-web"}), specialist, reason)
    spec_session = sessions_db.get(prepared.session_id)
    assert spec_session.channel is None
    assert _call_in(spec_session, tmp_path, channel=spec_session.channel).success is True


def test_fortgesetzte_handoff_sitzung_uebernimmt_kanal(specialist, client):
    from hydrahive.db import agent_handoffs
    thread = "a" * 24
    first = reason_with_profile(specialist["id"], "quick", "erst", thread=thread)
    st1 = _signed_state(first).model_copy(update={"id": "in-a"})
    p1 = hs.prepare_handoff(st1, specialist, first)
    assert sessions_db.get(p1.session_id).channel is None
    agent_handoffs.update_status(p1.handoff_id, "done")

    second = reason_with_profile(specialist["id"], "quick", "dann", thread=thread, channel="email")
    st2 = _signed_state(second).model_copy(update={"id": "in-b"})
    p2 = hs.prepare_handoff(st2, specialist, second)
    assert p2.continued is True and p2.session_id == p1.session_id
    assert sessions_db.get(p2.session_id).channel == "email"
    agent_handoffs.update_status(p2.handoff_id, "done")

    third = reason_with_profile(specialist["id"], "quick", "noch", thread=thread)
    p3 = hs.prepare_handoff(_signed_state(third).model_copy(update={"id": "in-c"}), specialist, third)
    assert p3.continued is True and p3.session_id == p1.session_id
    assert sessions_db.get(p3.session_id).channel == "email", "Kanal wird nie entfernt"


def test_fremder_server_gilt_als_extern(monkeypatch):
    """Federation: Herkunft des Auftrags auf dem fremden Server unbekannt → fail closed."""
    from hydrahive.agentlink.runtime_profiles import channel_from_reason
    from hydrahive.federation import peer_inbound as pi
    posted_states: list[State] = []

    async def fake_post(state):
        posted_states.append(state)
        return State(id="loc-1", agent_id=state.agent_id, task=state.task)

    monkeypatch.setattr(pi, "post_state", fake_post)
    monkeypatch.setattr(pi.peers_db, "claim_task", lambda *a: True)
    monkeypatch.setattr(pi, "_rate_ok", lambda _p: True)
    monkeypatch.setattr(pi, "_resolve_target", lambda _p, t: t)
    monkeypatch.setattr(pi.peers_db, "is_agent_allowed", lambda *a: True)
    monkeypatch.setattr(pi.peers_db, "set_task_status", lambda *a, **k: None)
    monkeypatch.setattr(pi.peers_db, "touch", lambda *a: None)
    monkeypatch.setattr(pi, "_audit", lambda *a, **k: None)
    monkeypatch.setattr(pi, "register_pending", lambda *a: asyncio.get_running_loop().create_future())

    async def _no_relay(*a, **k):
        return None
    monkeypatch.setattr(pi, "_relay_reply", _no_relay)

    async def _go():
        await pi.accept_task({"id": "p1", "name": "fremd"}, {"task_id": "t1", "target_agent": "spec", "task": "x"})
    asyncio.run(_go())
    assert channel_from_reason(posted_states[0].handoff.reason) == "federation"


def test_federation_kanal_hinweis(unlocked, fake_portfolio, tmp_path):
    s = sessions_db.create(agent_id="a1", user_id="testuser")
    assert _call_in(s, tmp_path, channel="federation").error == channel_hint("einen fremden Server")


# ── Kanal nicht per API entfernbar ────────────────────────────────────────────────────────────────────────────

def test_kanal_nicht_per_api_entfernbar(client, auth_headers):
    s = _channel_session("whatsapp")
    for body in ({"channel": None}, {"channel": ""}, {"metadata": {"channel": None}}, {"title": "neu"}):
        r = client.patch(f"/api/sessions/{s.id}", json=body, headers=auth_headers)
        assert r.status_code in (200, 422), r.text
        assert sessions_db.get(s.id).channel == "whatsapp", body


def test_sessions_update_laesst_kanal_stehen(client):
    s = _channel_session("matrix")
    sessions_db.update(s.id, title="x", status="active", metadata={"a": 1})
    assert sessions_db.get(s.id).channel == "matrix"


def test_set_channel_entfernt_nie(client):
    s = _channel_session("discord")
    sessions_db.adopt_channel(s.id, None)
    assert sessions_db.get(s.id).channel == "discord"
    sessions_db.adopt_channel(s.id, "whatsapp")
    assert sessions_db.get(s.id).channel == "discord", "vorhandener Kanal bleibt"


# ── Zeitplan/Butler ohne Kanal → wie 1a ───────────────────────────────────────────────────────────────────────

def test_zeitplan_sitzung_ohne_kanal_entsperrt_liefert(unlocked, fake_portfolio, tmp_path):
    s = sessions_db.create(agent_id="a1", user_id="testuser", title="Automatisch: Morgenroutine",
                           metadata={"flow_id": "f", "schedule_id": "t"})
    assert s.channel is None
    assert _call_in(s, tmp_path, channel=sessions_db.get(s.id).channel).success is True


def test_zeitplan_sitzung_ohne_kanal_gesperrt_hinweis(client, fake_portfolio, tmp_path):
    from hydrahive.api.middleware import users
    from hydrahive.vault import unlocks
    unlocks.close(users.verify("testuser", PW)["user_id"])
    s = sessions_db.create(agent_id="a1", user_id="testuser", title="Automatisch")
    assert _call_in(s, tmp_path, channel=None).error == LOCKED and fake_portfolio == []
