"""Projekt-Einschränkung für MCP-Server und Plugins (Task 3223371d).

Die Projekt-Felder mcp_server_ids / allowed_plugins wurden im UI gepflegt, aber
nie ausgewertet. Sie wirken jetzt als Schnittmenge: ein Projekt kann die Tools
eines Agenten nur EINSCHRÄNKEN, nie erweitern. Leere Liste = keine Einschränkung.
"""
from __future__ import annotations

from hydrahive.plugins.tool_bridge import parse_tool_name


def scope_tools(project: dict | None, local_tools: list[str],
                mcp_servers: list[str]) -> tuple[list[str], list[str]]:
    """Liefert (local_tools, mcp_servers) nach Anwendung der Projekt-Listen."""
    if not project:
        return local_tools, mcp_servers
    allowed_mcp = set(project.get("mcp_server_ids") or [])
    allowed_plugins = set(project.get("allowed_plugins") or [])
    if allowed_mcp:
        mcp_servers = [s for s in mcp_servers if s in allowed_mcp]
    if allowed_plugins:
        kept = []
        for name in local_tools:
            parsed = parse_tool_name(name)
            if parsed is None or parsed[0] in allowed_plugins:
                kept.append(name)
        local_tools = kept
    return local_tools, mcp_servers
