from __future__ import annotations
from typing import Any
from _rest import RestClient


async def list_agents(client: RestClient) -> list[dict]:
    try:
        result = await client.get("/api/agents")
        return result if isinstance(result, list) else result.get("items", [])
    except Exception as e:
        return [{"error": str(e), "code": "agents_failed"}]


async def get_agent(client: RestClient, agent_id: str) -> dict[str, Any]:
    try:
        return await client.get(f"/api/agents/{agent_id}")
    except Exception as e:
        return {"error": str(e), "code": "agent_not_found"}


async def update_agent(
    client: RestClient, agent_id: str, field: str, value: Any
) -> dict[str, Any]:
    try:
        return await client.patch(f"/api/agents/{agent_id}", body={field: value})
    except Exception as e:
        return {"error": str(e), "code": "update_failed"}
