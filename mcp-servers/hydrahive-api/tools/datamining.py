from __future__ import annotations
from typing import Any
from _rest import RestClient


async def dm_search(
    client: RestClient,
    q: str = "",
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    try:
        params: dict = {"q": q, "limit": limit}
        if event_type:
            params["event_type"] = event_type
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        return await client.get("/api/datamining/search", params=params)
    except Exception as e:
        return {"error": str(e), "code": "dm_search_failed"}


async def dm_get_session(client: RestClient, session_id: str) -> dict[str, Any]:
    try:
        return await client.get(f"/api/datamining/sessions/{session_id}")
    except Exception as e:
        return {"error": str(e), "code": "dm_session_failed"}


async def dm_list_sessions(client: RestClient, limit: int = 20) -> list[dict]:
    try:
        result = await client.get("/api/datamining/sessions", params={"limit": limit})
        return result if isinstance(result, list) else result.get("items", [])
    except Exception as e:
        return [{"error": str(e), "code": "dm_list_failed"}]


async def dm_stats(client: RestClient) -> dict[str, Any]:
    try:
        return await client.get("/api/datamining/stats/latest")
    except Exception as e:
        return {"error": str(e), "code": "dm_stats_failed"}
