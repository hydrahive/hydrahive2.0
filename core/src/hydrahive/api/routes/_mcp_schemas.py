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


SECRET_MASK = "***"


def for_viewer(server: dict, role: str) -> dict:
    """env/headers-Werte (oft API-Schlüssel) nur für Admins; andere sehen nur die Schlüsselnamen."""
    if role == "admin":
        return server
    out = dict(server)
    for field in ("env", "headers"):
        if isinstance(out.get(field), dict):
            out[field] = {k: SECRET_MASK for k in out[field]}
    return out
