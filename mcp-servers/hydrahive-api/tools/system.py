from __future__ import annotations
from typing import Any
from _rest import RestClient


async def get_status(client: RestClient) -> dict[str, Any]:
    try:
        return await client.get("/api/health")
    except Exception as e:
        return {"error": str(e), "code": "health_failed"}


async def get_token_stats(client: RestClient) -> dict[str, Any]:
    try:
        return await client.get("/api/dashboard")
    except Exception as e:
        return {"error": str(e), "code": "stats_failed"}
