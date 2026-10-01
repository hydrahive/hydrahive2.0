"""Interne AgentLink-Aufträge und Antworten sind signiert (Task 3bd963b2, b1).

Befund 29.09.2026: nginx gibt /agentlink/api ohne Login ins LAN, AgentLink
selbst prüft nichts. Der handoff_receiver startete jeden State mit
"hh-target:<id>" als Lauf des Ziel-Besitzers. Antworten wurden nur am
agent_id-Text erkannt. Beides war von jedem im LAN fälschbar.

Jetzt: HydraHive signiert, was es sendet (HMAC, Schlüssel aus secret_key),
und nimmt Aufträge und Antworten nur mit gültiger Signatur an.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.agentlink import signing
from hydrahive.agentlink.client import register_pending, resolve_pending
from hydrahive.agentlink.protocol import ContextBlock, Handoff, State, TaskBlock
from hydrahive.agentlink.runtime_profiles import profile_from_reason, resume_token_from_reason


def _state(reason: str = "hh-target:agent-1|hh-runtime:v1:standard|hh-task: hallo",
           description: str = "Mach was", sid: str = "st-1") -> State:
    return State(
        id=sid, agent_id="hydrahive/caller",
        task=TaskBlock(type="feature", description=description),
        context=ContextBlock(files=[{"path": "a.py"}], errors=["boom"]),
        handoff=Handoff(to_agent="hydrahive", reason=reason),
    )


# --- Signatur -------------------------------------------------------------

def test_signed_state_verifies():
    s = signing.sign(_state())
    assert signing.is_valid(s)


def test_unsigned_state_is_invalid():
    assert not signing.is_valid(_state())


@pytest.mark.parametrize("change", [
    lambda s: setattr(s.task, "description", "Lösche alles"),
    lambda s: setattr(s.handoff, "reason", s.handoff.reason.replace("agent-1", "agent-2")),
    lambda s: setattr(s, "id", "st-2"),
    lambda s: setattr(s, "agent_id", "evil"),
    lambda s: setattr(s.handoff, "to_agent", "other"),
    lambda s: s.context.files.append({"path": "/etc/shadow"}),
    lambda s: s.context.errors.append("neu"),
    lambda s: setattr(s.task, "type", "bug_fix"),
])
def test_any_change_breaks_signature(change):
    s = signing.sign(_state())
    change(s)
    assert not signing.is_valid(s)


def test_signature_from_other_secret_is_invalid(monkeypatch):
    s = signing.sign(_state())
    monkeypatch.setattr(signing, "_key", lambda: b"x" * 32)
    assert not signing.is_valid(s)


def test_sign_sets_id_when_missing():
    s = signing.sign(_state(sid=None))
    assert s.id and signing.is_valid(s)


def test_signature_segment_does_not_confuse_reason_parsers():
    s = signing.sign(_state(
        reason="hh-target:a|hh-runtime:v1:deep|hh-resume:v1:handoff_12345678|hh-task: x"))
    assert profile_from_reason(s.handoff.reason) == "deep"
    assert resume_token_from_reason(s.handoff.reason) == "handoff_12345678"


def test_double_sign_keeps_single_signature():
    s = signing.sign(signing.sign(_state()))
    assert s.handoff.reason.count("hh-sig:") == 1 and signing.is_valid(s)


# --- Empfänger ------------------------------------------------------------

@pytest.fixture
def receiver(monkeypatch):
    from hydrahive.runner import handoff_receiver as hr
    calls: dict = {"prepared": [], "errors": []}

    def fake_prepare(state, target, reason):
        calls["prepared"].append(state.id)
        raise hr.HandoffSetupError("stop nach Prüfung")

    async def fake_error_reply(state, message):
        calls["errors"].append(message)

    monkeypatch.setattr(hr, "prepare_handoff", fake_prepare)
    monkeypatch.setattr(hr, "_post_error_reply", fake_error_reply)
    monkeypatch.setattr(hr, "_find_target_agent", lambda _id: {"id": "agent-1", "owner": "admin"})
    monkeypatch.setattr(hr.db_agent_handoffs, "seen", lambda sid: sid in calls.setdefault("seen", set()))
    return hr, calls


def _handle(hr, monkeypatch, state: State):
    from hydrahive.agentlink.protocol import WSEvent

    async def fake_get_state(_sid):
        return state

    monkeypatch.setattr(hr, "get_state", fake_get_state)
    asyncio.run(hr.handle(WSEvent(type="handoff_received", state_id=state.id)))


def test_receiver_rejects_unsigned_handoff(receiver, monkeypatch):
    hr, calls = receiver
    logged: list = []
    monkeypatch.setattr(hr.errors_log, "record", lambda *a, **k: logged.append((a, k)))
    _handle(hr, monkeypatch, _state())
    assert calls["prepared"] == []
    assert calls["errors"] == []      # keine Antwort an Fälscher
    # …aber sichtbar im Fehlerprotokoll statt nur im Journal
    assert logged and logged[0][1]["error_type"] == "signature_invalid"


def test_receiver_accepts_related_files_after_agentlink_roundtrip(receiver, monkeypatch):
    hr, calls = receiver
    s = _state(sid="st-files")
    s.context.files = [{"path": "core/x.py"}, {"path": "frontend/y.ts"}]
    signing.sign(s)
    s.context.files = _like_agentlink(s.context.files)
    _handle(hr, monkeypatch, s)
    assert calls["prepared"] == ["st-files"]


def test_receiver_rejects_tampered_handoff(receiver, monkeypatch):
    hr, calls = receiver
    s = signing.sign(_state())
    s.task.description = "rm -rf"
    _handle(hr, monkeypatch, s)
    assert calls["prepared"] == []


def test_receiver_accepts_signed_handoff(receiver, monkeypatch):
    hr, calls = receiver
    s = signing.sign(_state())
    _handle(hr, monkeypatch, s)
    assert calls["prepared"] == [s.id]


def test_receiver_rejects_replayed_state(receiver, monkeypatch):
    hr, calls = receiver
    s = signing.sign(_state())
    calls["seen"] = {s.id}
    _handle(hr, monkeypatch, s)
    assert calls["prepared"] == []


def test_seen_uses_handoff_table(client):
    from hydrahive.db import agent_handoffs
    from tests._own_rows import only_own_rows
    with only_own_rows("agent_handoffs"):
        assert agent_handoffs.seen("st-neu-123") is False
        agent_handoffs.create(incoming_state_id="st-neu-123", from_agent="a", agent_id="b", session_id="s")
        assert agent_handoffs.seen("st-neu-123") is True
        assert agent_handoffs.seen("") is False


# --- Antworten ------------------------------------------------------------

def _reply(to: str, text: str, signed: bool) -> State:
    r = State(agent_id="hydrahive", task=TaskBlock(type="feature", description=text, status="done"),
              handoff=Handoff(to_agent="hydrahive", reason=f"reply_to:{to}"), id=f"r-{text}")
    return signing.sign(r) if signed else r


def test_forged_reply_does_not_resolve_waiting_call():
    async def body():
        fut = register_pending("st-9", "hydrahive")
        assert resolve_pending("st-9", _reply("st-9", "gefälscht", signed=False)) is False
        assert not fut.done()
        assert resolve_pending("st-9", _reply("st-9", "echt", signed=True)) is True
        return (await fut).task.description
    assert asyncio.run(body()) == "echt"


# --- Sender ---------------------------------------------------------------

def test_post_state_signs_everything(monkeypatch):
    from hydrahive.agentlink import client
    sent: list[dict] = []

    class FakeResp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return sent[-1]

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json, headers): sent.append(json); return FakeResp()

    monkeypatch.setattr(client.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(client.post_state(_state(sid=None)))
    assert "hh-sig:" in sent[0]["handoff"]["reason"]
    assert sent[0]["id"]
    assert signing.is_valid(result)


# --- Regression 29.09.2026 nach Deploy: Antwort-ID trotz Signatur finden -----
# #472 hängt "|hh-sig:v1:<hex>" an reason. lifespan._on_event nahm alles nach
# "reply_to:" als ID, also inklusive Signatur. resolve_pending fand die
# wartende Anfrage nie, jeder ask_agent lief in den Timeout (Live-Befund).

def test_reply_target_ignores_signature_segment():
    r = signing.sign(_reply("st-live-1", "ok", signed=False))
    assert "|hh-sig:v1:" in r.handoff.reason
    assert signing.reply_target(r.handoff.reason) == "st-live-1"


@pytest.mark.parametrize("reason,expected", [
    ("reply_to:abc", "abc"),
    ("reply_to: abc ", "abc"),
    ("hh-target:x|hh-task: y", None),
    ("", None),
    ("reply_to:", None),
])
def test_reply_target_parsing(reason, expected):
    assert signing.reply_target(reason) == expected


def test_listener_resolves_signed_reply_end_to_end():
    """Genau der Weg des Live-Fehlers: signierte Antwort → Listener → wartender Aufruf."""
    from hydrahive.agentlink.protocol import WSEvent
    from hydrahive.api import lifespan

    reply = _reply("st-live-2", "fertig", signed=True)

    async def body():
        fut = register_pending("st-live-2", "hydrahive")

        async def fake_get_state(_sid):
            return reply

        await lifespan.dispatch_agentlink_event(
            WSEvent(type="handoff_received", state_id=reply.id), get_state=fake_get_state,
        )
        return fut.done() and fut.result().task.description

    assert asyncio.run(body()) == "fertig"


# --- Rundreise über AgentLink (Befund 01.10.2026) ---------------------------
# AgentLink speichert context.files als FileContext(path, diff, lines, hash):
# fehlende Felder kommen als null zurück, unbekannte fallen weg. Vorher passte
# die Signatur danach nicht mehr → jeder ask_agent mit related_files wurde vom
# Empfänger still verworfen (Auftraggeber sah nur nach 10 min einen Timeout).

def _like_agentlink(files: list[dict]) -> list[dict]:
    keys = ("path", "diff", "lines", "hash")
    return [{k: f.get(k) for k in keys} for f in files]


def test_signature_survives_agentlink_roundtrip():
    s = _state()
    s.context.files = [{"path": "a.py"}, {"path": "b.py", "lines": [3, 9]}]
    signing.sign(s)
    s.context.files = _like_agentlink(s.context.files)
    assert signing.is_valid(s)


def test_unknown_file_keys_dropped_by_agentlink_do_not_break_signature():
    s = _state()
    s.context.files = [{"path": "a.py", "note": "nur lokal"}]
    signing.sign(s)
    s.context.files = _like_agentlink(s.context.files)
    assert signing.is_valid(s)


@pytest.mark.parametrize("change", [
    lambda f: f[0].update(path="/etc/shadow"),
    lambda f: f[0].update(diff="--- injiziert"),
    lambda f: f[0].update(lines=[1, 2]),
    lambda f: f[0].update(hash="abc"),
    lambda f: f.append({"path": "neu.py", "diff": None, "lines": None, "hash": None}),
])
def test_real_changes_still_break_signature_after_roundtrip(change):
    s = signing.sign(_state())
    s.context.files = _like_agentlink(s.context.files)
    change(s.context.files)
    assert not signing.is_valid(s)
