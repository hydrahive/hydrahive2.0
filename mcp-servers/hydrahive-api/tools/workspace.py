from __future__ import annotations
from typing import Any
from _rest import RestClient


async def list_projects(client: RestClient) -> list[dict]:
    try:
        result = await client.get("/api/projects")
        return result if isinstance(result, list) else result.get("items", [])
    except Exception as e:
        return [{"error": str(e), "code": "projects_failed"}]


async def list_files(
    client: RestClient, project_id: str, path: str = ""
) -> dict[str, Any]:
    try:
        params = {"path": path} if path else {}
        return await client.get(f"/api/projects/{project_id}/files", params=params)
    except Exception as e:
        return {"error": str(e), "code": "files_failed"}


async def read_file(
    client: RestClient, project_id: str, path: str
) -> dict[str, Any]:
    try:
        return await client.get(
            f"/api/projects/{project_id}/files/read", params={"path": path}
        )
    except Exception as e:
        return {"error": str(e), "code": "read_failed"}
