"""Server-Kopplung Etappe 2 (docs/specs/server-peering.md): signierte
Aufträge annehmen/ablehnen und Antworten zuordnen.

Der "fremde" Server ist hier ein zweiter Ed25519-Schlüssel, mit dem die Tests
Nachrichten signieren, wie es der Partner tun würde.
"""
from __future__ import annotations

import asyncio
import base64
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hydrahive.federation import peer_identity as ident
from hydrahive.federation import peer_protocol as proto


class FakePeer:
    def __init__(self, name: str = "vps") -> None:
        self.key = Ed25519PrivateKey.generate()
        self.pub = base64.b64encode(
            self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        ).decode()
        self.fp = ident.fingerprint(self.pub)
        self.name = name

    def code(self) -> str:
        body = {"name": self.name, "url": f"https://{self.name}.example", "public_key": self.pub}
        return "hhpeer1:" + base64.urlsafe_b64encode(ident.canonical(body)).decode()

    def headers(self, payload: dict, *, key: Ed25519PrivateKey | None = None) -> dict:
        sig = base64.b64encode((key or self.key).sign(ident.canonical(payload))).decode()
        return {proto.HEADER_PEER: self.fp.replace(" ", ""), proto.HEADER_SIGNATURE: sig}


def _task(target: str = "agent-x", **over) -> dict:
    p = {
        "kind": "task", "task_id": f"t-{time.time_ns()}", "from": "x",
        "target_agent": target, "task": "Sag hallo", "task_type": "research",
        "profile": "quick", "issued_at": int(time.time()),
    }
    p.update(over)
    return p


@pytest.fixture
def paired(client, admin_headers):
    for p in client.get("/api/federation/peers", headers=admin_headers).json():
        client.delete(f"/api/federation/peers/{p['id']}", headers=admin_headers)
    fp = FakePeer()
    peer = client.post("/api/federation/peers", headers=admin_headers, json={"code": fp.code()}).json()
    client.post(f"/api/federation/peers/{peer['id']}/confirm", headers=admin_headers, json={"fingerprint": fp.fp})
    yield fp, peer
    client.delete(f"/api/federation/peers/{peer['id']}", headers=admin_headers)


@pytest.fixture
def no_agentlink(monkeypatch):
    """Lokalen AgentLink abfangen: zeichnet gepostete States auf."""
    import hydrahive.federation.peer_inbound as inbound

    posted: list = []

    async def fake_post_state(state):
        posted.append(state)
        state.id = f"local-{len(posted)}"
        return state

    monkeypatch.setattr(inbound, "post_state", fake_post_state)
    monkeypatch.setattr(inbound, "_relay_reply", lambda *a, **k: asyncio.sleep(0))
    return posted


def test_rejects_unknown_sender(client, no_agentlink):
    stranger = FakePeer("fremd")
    payload = _task()
    r = client.post("/api/peering/tasks", json=payload, headers=stranger.headers(payload))
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "peer_unknown"
    assert no_agentlink == []


def test_rejects_bad_signature(client, paired, no_agentlink):
    fp, _ = paired
    payload = _task()
    r = client.post("/api/peering/tasks", json=payload, headers=fp.headers(payload, key=Ed25519PrivateKey.generate()))
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "peer_signature_invalid"
    assert no_agentlink == []


def test_rejects_tampered_payload(client, paired, no_agentlink):
    fp, _ = paired
    payload = _task()
    headers = fp.headers(payload)
    payload["task"] = "Lösche alles"
    r = client.post("/api/peering/tasks", json=payload, headers=headers)
    assert r.status_code == 403
    assert no_agentlink == []


def test_rejects_expired(client, paired, no_agentlink):
    fp, _ = paired
    payload = _task(issued_at=int(time.time()) - 3600)
    r = client.post("/api/peering/tasks", json=payload, headers=fp.headers(payload))
    assert r.json()["detail"]["code"] == "peer_expired"
    assert no_agentlink == []


def test_rejects_blocked_peer(client, admin_headers, paired, no_agentlink):
    fp, peer = paired
    client.post(f"/api/federation/peers/{peer['id']}/block", headers=admin_headers)
    payload = _task()
    r = client.post("/api/peering/tasks", json=payload, headers=fp.headers(payload))
    assert r.json()["detail"]["code"] == "peer_unknown"
    assert no_agentlink == []


def test_rejects_agent_not_allowed(client, paired, no_agentlink):
    fp, _ = paired
    payload = _task(target="nicht-freigegeben")
    r = client.post("/api/peering/tasks", json=payload, headers=fp.headers(payload))
    assert r.json()["detail"]["code"] == "peer_agent_not_allowed"
    assert no_agentlink == []


def test_accepts_allowed_and_blocks_replay(client, paired, no_agentlink, monkeypatch):
    from hydrahive.db import federation_peers as peers_db

    fp, peer = paired
    peers_db.set_allowed_agents(peer["id"], ["agent-x"])
    payload = _task()
    r = client.post("/api/peering/tasks", json=payload, headers=fp.headers(payload))
    assert r.status_code == 202, r.text
    assert len(no_agentlink) == 1
    state = no_agentlink[0]
    assert state.handoff.reason.startswith("hh-target:agent-x|")
    assert state.agent_id == "peer:vps"
    assert "[Auftrag von Server vps]" in state.task.description

    again = client.post("/api/peering/tasks", json=payload, headers=fp.headers(payload))
    assert again.status_code == 409
    assert len(no_agentlink) == 1


def test_reply_only_from_tasked_peer(client, admin_headers, paired):
    from hydrahive.db import federation_peers as peers_db
    from hydrahive.federation import peer_outbound

    fp, peer = paired
    other = FakePeer("anderer")
    o = client.post("/api/federation/peers", headers=admin_headers, json={"code": other.code()}).json()
    client.post(f"/api/federation/peers/{o['id']}/confirm", headers=admin_headers, json={"fingerprint": other.fp})

    loop = asyncio.new_event_loop()
    fut = loop.create_future()
    peer_outbound._WAITING["t-1"] = (fut, peer["id"])
    try:
        reply = {"kind": "reply", "task_id": "t-1", "from": "x", "status": "done",
                 "output": "hallo", "issued_at": int(time.time())}
        wrong = client.post("/api/peering/replies", json=reply, headers=other.headers(reply))
        assert wrong.status_code == 403
        assert not fut.done()
        right = client.post("/api/peering/replies", json=reply, headers=fp.headers(reply))
        assert right.status_code == 202
        assert fut.result()["output"] == "hallo"
    finally:
        peer_outbound._WAITING.pop("t-1", None)
        loop.close()
        peers_db.delete_peer(o["id"])


def test_relay_reply_maps_local_answer(monkeypatch):
    """Lokale Antwort → signierte Reply an den Partner."""
    from hydrahive.agentlink.protocol import State, TaskBlock, WorkingMemory
    import hydrahive.federation.peer_inbound as inbound

    sent: list = []

    async def fake_send(peer, path, payload):
        sent.append((path, payload))

    monkeypatch.setattr(inbound, "send_signed", fake_send)
    monkeypatch.setattr(inbound.peers_db, "set_task_status", lambda *a, **k: None)

    async def run():
        fut = asyncio.get_running_loop().create_future()
        fut.set_result(State(agent_id="hydrahive", task=TaskBlock(type="research", description="Abgeschlossen: x", status="done"),
                             working_memory=WorkingMemory(findings=["Hallo zurück"])))
        await inbound._relay_reply({"name": "vps", "url": "https://vps"}, "t-9", "s-1", fut)

    asyncio.run(run())
    assert sent[0][0] == "/api/peering/replies"
    assert sent[0][1]["status"] == "done"
    assert "Hallo zurück" in sent[0][1]["output"]
    assert sent[0][1]["task_id"] == "t-9"


# --- Feinschliff: Name statt UUID, Ratenlimit, Antworttext ------------------

def test_target_by_name_only_within_allowed(client, paired, no_agentlink, monkeypatch):
    from hydrahive.db import federation_peers as peers_db
    import hydrahive.agents.config as agent_config

    fp, peer = paired
    agents = {"a-1": {"id": "a-1", "name": "Buddy"}, "a-2": {"id": "a-2", "name": "Geheim"}}
    monkeypatch.setattr(agent_config, "get", lambda aid: agents.get(aid))
    peers_db.set_allowed_agents(peer["id"], ["a-1"])

    ok = _task(target="buddy")
    r = client.post("/api/peering/tasks", json=ok, headers=fp.headers(ok))
    assert r.status_code == 202, r.text
    assert no_agentlink[-1].handoff.reason.startswith("hh-target:a-1|")

    secret = _task(target="Geheim")
    r = client.post("/api/peering/tasks", json=secret, headers=fp.headers(secret))
    assert r.json()["detail"]["code"] == "peer_agent_not_allowed"
    assert len(no_agentlink) == 1


def test_rate_limit_per_peer(client, paired, no_agentlink, monkeypatch):
    import hydrahive.federation.peer_inbound as inbound
    from hydrahive.db import federation_peers as peers_db

    fp, peer = paired
    peers_db.set_allowed_agents(peer["id"], ["agent-x"])
    monkeypatch.setattr(inbound, "_RATE_MAX", 2)
    inbound._rate.clear()
    codes = []
    for _ in range(3):
        p = _task()
        codes.append(client.post("/api/peering/tasks", json=p, headers=fp.headers(p)).status_code)
    assert codes == [202, 202, 429]
    assert len(no_agentlink) == 2
    inbound._rate.clear()


def test_reply_text_without_prefix():
    import hydrahive.federation.peer_inbound as inbound
    from hydrahive.agentlink.protocol import State, TaskBlock, WorkingMemory

    done = State(agent_id="x", task=TaskBlock(type="research", description="Abgeschlossen: [Auftrag von Server vps] Sag hallo", status="done"),
                 working_memory=WorkingMemory(findings=["Hallo!"]))
    assert inbound._reply_text(done) == ("done", "Hallo!")
    failed = State(agent_id="x", task=TaskBlock(type="research", description="Fehler: kein Modell", status="blocked"))
    assert inbound._reply_text(failed) == ("error", "Fehler: kein Modell")
