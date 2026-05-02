"""MCP route schemas + shared helper."""
from __future__ import annotations

from pydantic import BaseModel

from hydrahive.mcp import manager as mcp_manager


class McpServerCreate(BaseModel):
    id: str
    name: str
    transport: str
    description: str = ""
    enabled: bool = True
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    url: str | None = None
    headers: dict[str, str] | None = None


class McpServerUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    url: str | None = None
    headers: dict[str, str] | None = None


class QuickAddRequest(BaseModel):
    template_id: str
    server_id: str
    inputs: dict[str, str] = {}


def annotate_status(server: dict) -> dict:
    """Connect-Status aus Manager pro Server beimischen."""
    out = dict(server)
    pool = {s["id"]: s["connected"] for s in mcp_manager.status()}
    out["connected"] = bool(pool.get(server["id"], False))
    return out
