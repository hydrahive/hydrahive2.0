from __future__ import annotations
from typing import Any
from _agentlink import AgentLinkClient
from _rest import RestClient

async def al_status(rest: RestClient, al: AgentLinkClient) -> dict[str, Any]:
    try:
        info = await rest.get("/api/agentlink/status")
        return {
            **info,
            "ws_connected": al.is_connected(),
            "ws_last_error": al.last_error(),
            "inbox_count": al._queue.qsize(),
            "our_agent_id": al.agent_id,
        }
    except Exception as e:
        return {"error": str(e), "code": "al_status_failed"}

async def al_send(
    al: AgentLinkClient,
    to_agent: str,
    task_type: str,
    description: str,
    context: dict | None = None,
) -> dict[str, Any]:
    try:
        return await al.send_state(
            to_agent=to_agent,
            task_type=task_type,
            description=description,
            context=context,
        )
    except Exception as e:
        return {"error": str(e), "code": "al_send_failed"}

def al_check_inbox(al: AgentLinkClient) -> list[dict]:
    return al.drain_inbox()

async def al_reply(
    al: AgentLinkClient, state_id: str, result: str
) -> dict[str, Any]:
    try:
        return await al.reply_to_handoff(state_id=state_id, result=result)
    except Exception as e:
        return {"error": str(e), "code": "al_reply_failed"}
