"""run-status liefert die offene Tool-Bestätigung (docs/specs/harakiri-confirm-noise.md, Punkt 3).

Wer nach längerer Abwesenheit die Sitzung neu lädt, soll das Banner wieder sehen –
der Lauf wartet ja weiter. Und: Stopp über den echten Run-Task räumt sie auf.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.api.routes import _session_msg_helpers as H
from hydrahive.runner import concurrency as C
from hydrahive.runner import tool_confirmation as tc
from hydrahive.runner.event_bus import bus
from hydrahive.runner.events import TextDelta


def test_run_status_includes_pending_confirm(client, auth_headers):
    from hydrahive.db import sessions as sessions_db

    s = sessions_db.create(agent_id="a1", user_id="testuser", title="t")
    r = client.get(f"/api/sessions/{s.id}/run-status", headers=auth_headers)
    assert r.status_code == 200 and r.json()["pending_confirm"] is None

    async def register():
        tc.register("cid-1", session_id=s.id, tool_name="shell_exec",
                    arguments={"cmd": "touch /etc/x"}, reason="Schreibzugriff auf geschützten Pfad: /etc")
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(register())
        body = client.get(f"/api/sessions/{s.id}/run-status", headers=auth_headers).json()
        assert body["pending_confirm"] == {
            "call_id": "cid-1", "tool_name": "shell_exec",
            "arguments": {"cmd": "touch /etc/x"}, "reason": "Schreibzugriff auf geschützten Pfad: /etc",
        }
        # Andere Sitzung sieht sie nicht.
        other = sessions_db.create(agent_id="a1", user_id="testuser", title="u")
        assert client.get(f"/api/sessions/{other.id}/run-status", headers=auth_headers).json()["pending_confirm"] is None
    finally:
        tc._pending.clear()
        loop.close()


@pytest.mark.asyncio
async def test_stop_of_waiting_run_task_clears_pending(monkeypatch):
    async def fake_runner(session_id, user_content, **kw):
        yield TextDelta(text="x")
        tc.register("cid-stop", session_id=session_id, tool_name="shell_exec")
        await tc.wait("cid-stop", timeout=None)  # wartet ohne Limit
        yield TextDelta(text="nie")

    monkeypatch.setattr(H, "runner_run", fake_runner)
    H.start_run_task("int-confirm-stop", "hi")
    for _ in range(100):
        if tc.pending_for("int-confirm-stop"):
            break
        await asyncio.sleep(0.01)
    assert tc.pending_for("int-confirm-stop") is not None
    assert C.cancel("int-confirm-stop") is True
    for _ in range(100):
        if not C.is_running("int-confirm-stop"):
            break
        await asyncio.sleep(0.01)
    assert not C.is_running("int-confirm-stop")
    assert tc.pending_for("int-confirm-stop") is None and "cid-stop" not in tc._pending
    bus.close("int-confirm-stop")
