from __future__ import annotations
from typing import Any
from _rest import RestClient


async def list_sessions(
    client: RestClient, agent_id: str | None = None, limit: int = 20
) -> list[dict]:
    try:
        params: dict = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        result = await client.get("/api/sessions", params=params)
        return result if isinstance(result, list) else result.get("items", [])
    except Exception as e:
        return [{"error": str(e), "code": "sessions_failed"}]


async def get_session(client: RestClient, session_id: str) -> dict[str, Any]:
    try:
        return await client.get(f"/api/sessions/{session_id}")
    except Exception as e:
        return {"error": str(e), "code": "session_not_found"}


async def get_messages(
    client: RestClient, session_id: str, limit: int = 50
) -> list[dict]:
    try:
        result = await client.get(
            f"/api/sessions/{session_id}/messages", params={"limit": limit}
        )
        return result if isinstance(result, list) else result.get("messages", [])
    except Exception as e:
        return [{"error": str(e), "code": "messages_failed"}]


async def send_message(
    client: RestClient, session_id: str, message: str
) -> dict[str, Any]:
    try:
        return await client.post(
            f"/api/sessions/{session_id}/messages",
            body={"content": message, "role": "user"},
        )
    except Exception as e:
        return {"error": str(e), "code": "send_failed"}
