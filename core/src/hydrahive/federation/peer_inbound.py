"""Eingehende Aufträge von gekoppelten Servern (docs/specs/server-peering.md).

Ablauf auf dem Empfänger:
1. ``accept_task`` (aus der Route): Absender/Signatur/Frische sind geprüft.
   Hier noch: Einmaligkeit, Freigabe des Ziel-Agenten. Dann wird der Auftrag
   in den LOKALEN AgentLink gelegt, signiert mit dem eigenen HMAC wie jeder
   lokale Auftrag. Der bestehende handoff_receiver führt ihn aus.
2. Die lokale Antwort landet über ``register_pending`` bei uns. Ein
   Hintergrund-Task schickt sie signiert an den Partner zurück.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from hydrahive.agentlink import (
    ContextBlock, Handoff, State, TaskBlock, cancel_pending, post_state, register_pending,
)
from hydrahive.agentlink.checkpoints import split_checkpoint_findings
from hydrahive.agentlink.runtime_profiles import normalize_profile, reason_with_profile
from hydrahive.db import errors_log
from hydrahive.db import federation_peers as peers_db
from hydrahive.federation import peer_protocol as proto
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_TASK_TYPES = {"bug_fix", "feature", "review", "research", "refactor"}
_REPLY_TIMEOUT = 1_900  # > deep-Profil (1800 s); der lokale Lauf bricht vorher ab


def _audit(peer: dict, message: str, *, severity: str = "info") -> None:
    errors_log.record("federation.peer", severity=severity, error_type="peer_task", message=f"{peer['name']}: {message}")


async def accept_task(peer: dict, payload: dict) -> str:
    """Nimmt den geprüften Auftrag an. Rückgabe: lokale State-ID."""
    task_id = payload["task_id"]
    target = payload.get("target_agent")
    task = payload.get("task")
    if not isinstance(target, str) or not isinstance(task, str) or not task.strip():
        raise proto.PeerRejected("peer_payload_invalid", "Ziel oder Aufgabe fehlt")
    if not peers_db.claim_task(task_id, peer["id"], "in"):
        raise proto.PeerRejected("peer_replay", f"Auftrag {task_id} schon gesehen")
    if not peers_db.is_agent_allowed(peer["id"], target):
        peers_db.set_task_status(task_id, "rejected")
        _audit(peer, f"Auftrag an nicht freigegebenen Agenten {target} abgelehnt", severity="warning")
        raise proto.PeerRejected("peer_agent_not_allowed", f"Agent {target} nicht freigegeben")

    task_type = payload.get("task_type") if payload.get("task_type") in _TASK_TYPES else "feature"
    profile = normalize_profile(payload.get("profile"))
    state = State(
        agent_id=f"peer:{peer['name']}",
        task=TaskBlock(type=task_type, description=f"[Auftrag von Server {peer['name']}]\n{task}"),
        context=ContextBlock(),
        handoff=Handoff(
            to_agent=settings.agentlink_agent_id,
            reason=reason_with_profile(target, profile, task[:120]),
        ),
    )
    sent = await post_state(state)
    if not sent.id:
        peers_db.set_task_status(task_id, "error")
        raise proto.PeerRejected("peer_local_failed", "AgentLink lieferte keine State-ID")
    fut = register_pending(sent.id, settings.agentlink_agent_id)
    peers_db.set_task_status(task_id, "running", local_state_id=sent.id)
    peers_db.touch(peer["id"])
    _audit(peer, f"Auftrag {task_id} → Agent {target} angenommen")
    asyncio.create_task(_relay_reply(peer, task_id, sent.id, fut), name=f"peer-reply-{task_id}")
    return sent.id


def _reply_text(response: State) -> tuple[str, str]:
    findings = response.working_memory.findings if response.working_memory else []
    visible, _checkpoint = split_checkpoint_findings(findings)
    description = response.task.description if response.task else ""
    parts = [description] if description else []
    parts.extend(f"- {item}" for item in visible)
    status = "done" if response.task and response.task.status == "done" else "error"
    return status, "\n".join(parts)


async def _relay_reply(peer: dict, task_id: str, state_id: str, fut: asyncio.Future) -> None:
    try:
        response = await asyncio.wait_for(fut, timeout=_REPLY_TIMEOUT)
        status, output = _reply_text(response)
    except asyncio.TimeoutError:
        cancel_pending(state_id)
        status, output = "error", "Keine Antwort vom lokalen Agenten (Timeout)"
    payload = proto.new_reply(task_id, status, output)
    try:
        await send_signed(peer, "/api/peering/replies", payload)
        peers_db.set_task_status(task_id, status)
    except Exception as exc:
        peers_db.set_task_status(task_id, "undelivered")
        logger.warning("Server-Kopplung: Antwort %s an %s nicht zustellbar: %s", task_id, peer["name"], exc)


async def send_signed(peer: dict, path: str, payload: dict) -> httpx.Response:
    """POST an den Partner. Tailnet-Partner haben meist ein selbst ausgestelltes
    Zertifikat; vertraut wird der Ed25519-Signatur, nicht dem TLS-Zertifikat."""
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:  # noqa: S501
        r = await client.post(peer["url"] + path, json=payload, headers=proto.signed_headers(payload))
        r.raise_for_status()
        return r
