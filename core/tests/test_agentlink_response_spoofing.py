"""ask_agent-Antwort-States müssen vom beauftragten Ziel stammen (Issue #184).

Ohne Absender-Prüfung konnte ein gefälschter State mit reason='reply_to:<id>'
die wartende Future überschreiben (Prompt-Injection in den Reasoning-Loop).
"""
from __future__ import annotations

import asyncio

from hydrahive.agentlink import client
from hydrahive.agentlink.protocol import State, TaskBlock


def _run(coro):
    return asyncio.run(coro)


def _reply(agent_id: str) -> State:
    return State(agent_id=agent_id, task=TaskBlock(type="feature", description="done"))


def test_resolve_accepts_expected_sender():
    async def body():
        client._PENDING_FUTURES.clear()
        fut = client.register_pending("sid-1", "spec-1")
        resp = _reply("spec-1")
        assert client.resolve_pending("sid-1", resp) is True
        assert fut.done() and fut.result() is resp
    _run(body())


def test_resolve_rejects_foreign_sender_and_keeps_future_pending():
    async def body():
        client._PENDING_FUTURES.clear()
        fut = client.register_pending("sid-2", "spec-1")
        assert client.resolve_pending("sid-2", _reply("attacker")) is False
        # Future bleibt offen — keine Spoof-induzierte DoS, echte Antwort kann noch lösen
        assert not fut.done()
        assert client.pending_handoffs_count() == 1
        # echte Antwort vom richtigen Absender löst auf
        good = _reply("spec-1")
        assert client.resolve_pending("sid-2", good) is True
        assert fut.result() is good
    _run(body())


def test_resolve_tolerates_name_suffix():
    async def body():
        client._PENDING_FUTURES.clear()
        fut = client.register_pending("sid-3", "hydrahive")
        assert client.resolve_pending("sid-3", _reply("hydrahive/Master")) is True
        assert fut.done()
    _run(body())


def test_resolve_without_expected_sender_is_backward_compatible():
    async def body():
        client._PENDING_FUTURES.clear()
        fut = client.register_pending("sid-4")
        assert client.resolve_pending("sid-4", _reply("anyone")) is True
        assert fut.done()
    _run(body())
