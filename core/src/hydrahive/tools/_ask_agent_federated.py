"""ask_agent-Routing für '<agent>@<server>' (ausgelagert aus ask_agent.py).

Reihenfolge: Ist <server> ein aktiver gekoppelter HydraHive-Server
(docs/specs/server-peering.md), geht der Auftrag signiert dorthin. Sonst wie
bisher als A2A-Workstation über /remote/chat.
"""
from __future__ import annotations

import logging

from hydrahive.tools._errors import describe
from hydrahive.tools.base import ToolContext, ToolResult

logger = logging.getLogger(__name__)


async def execute_federated(target: str, task: str, args: dict, ctx: ToolContext) -> ToolResult:
    """Nur mit Freigabe core.federation für den Besitzer des Laufs
    (docs/specs/access-groups.md §7 Regel 6)."""
    from hydrahive.access import check
    if not check.can_use_as(ctx.user_id, "core.federation"):
        return ToolResult.fail(
            "Keine Freigabe für die Föderation (core.federation). "
            "Ein Admin kann sie unter Admin → Freigaben erteilen."
        )
    agent_id, _, server = target.partition("@")
    agent_id, server = agent_id.strip(), server.strip()

    from hydrahive.federation import peer_outbound
    peer = peer_outbound.find_active_peer(server)
    if peer:
        return await _execute_peer(peer, agent_id, task, args)
    return await _execute_workstation(target, task, args, ctx)


async def _execute_peer(peer: dict, target_agent: str, task: str, args: dict) -> ToolResult:
    from hydrahive.agentlink.runtime_profiles import normalize_profile
    from hydrahive.federation import peer_outbound

    if not target_agent:
        return ToolResult.fail("Ziel-Agent fehlt: '<agent-id>@<server>' angeben")
    profile = normalize_profile(args.get("profile"))
    try:
        reply = await peer_outbound.send_task(
            peer, target_agent, task, args.get("task_type") or "feature", profile,
        )
    except TimeoutError:
        return ToolResult.fail(f"Server '{peer['name']}' hat nicht rechtzeitig geantwortet")
    except Exception as e:
        logger.warning("Server-Kopplung: Auftrag an %s fehlgeschlagen: %s", peer["name"], e)
        return ToolResult.fail(f"Server '{peer['name']}': {describe(e)}")
    label = f"{target_agent}@{peer['name']}"
    if reply.get("status") != "done":
        return ToolResult.fail(f"[{label}] {reply.get('output') or 'Fehler ohne Text'}")
    return ToolResult.ok(f"[{label}]: {reply.get('output') or ''}")


async def _execute_workstation(target: str, task: str, args: dict, ctx: ToolContext) -> ToolResult:
    """A2A-Workstation: 'persona@workstation' via /remote/chat (Freigabe schon geprüft)."""
    persona_id, _, ws_name = target.partition("@")
    persona_id = persona_id.strip()
    ws_name = ws_name.strip()

    try:
        from hydrahive.db import federation as fed_db
        from hydrahive.federation.registry import remote_chat

        # Workstation by name, ID, or URL-prefix
        ws = (
            fed_db.get_by_name(ws_name)
            or fed_db.get_workstation(ws_name)
        )
        if not ws:
            return ToolResult.fail(
                f"Federation-Workstation '{ws_name}' nicht gefunden. "
                "Bitte zuerst im Federation-Panel registrieren."
            )
        if not ws.get("enabled"):
            return ToolResult.fail(f"Workstation '{ws['name']}' ist deaktiviert.")

        result = await remote_chat(ws["id"], task, persona_id=persona_id)
        label = f"{persona_id}@{ws['name']}" if persona_id else ws["name"]
        return ToolResult.ok(f"[{label}]: {result}")
    except Exception as e:
        logger.exception("Federation remote_chat fehlgeschlagen: %s", e)
        return ToolResult.fail(f"Federation-Fehler: {describe(e)}")

