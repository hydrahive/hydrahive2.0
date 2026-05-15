"""HydraHive MCP Server — FastMCP Entry Point mit 20 Tools."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from _auth import Auth
from _rest import RestClient
from _agentlink import AgentLinkClient

from tools.system import get_status, get_token_stats
from tools.sessions import list_sessions, get_session, get_messages, send_message
from tools.agents import list_agents, get_agent, update_agent
from tools.workspace import list_projects, list_files, read_file
from tools.datamining import dm_search, dm_get_session, dm_list_sessions, dm_stats
from tools.agentlink import al_status, al_send, al_check_inbox, al_reply

# --- Singletons (initialisiert beim Import, kein env-var-Zwang) ---
_auth = Auth()
_rest = RestClient(_auth)
_al = AgentLinkClient(
    rest=_rest,
    agent_id=os.environ.get("HH_AGENT_ID", "claude-code"),
    base_url=_auth.base_url,
)


@asynccontextmanager
async def lifespan(server: FastMCP):
    await _auth.ensure_token()
    await _al.start()
    yield
    await _al.stop()


mcp = FastMCP("hydrahive", lifespan=lifespan)


# --- System ---

@mcp.tool()
async def hh_status() -> dict[str, Any]:
    """HydraHive-Systemstatus und Versionsinformationen."""
    return await get_status(_rest)


@mcp.tool()
async def hh_token_stats() -> dict[str, Any]:
    """Token- und Kostenstatistiken aus dem Dashboard."""
    return await get_token_stats(_rest)


# --- Sessions ---

@mcp.tool()
async def hh_list_sessions(agent_id: str | None = None, limit: int = 20) -> list[dict]:
    """Laufende und letzte Sessions auflisten, optional nach Agent gefiltert."""
    return await list_sessions(_rest, agent_id=agent_id, limit=limit)


@mcp.tool()
async def hh_get_session(session_id: str) -> dict[str, Any]:
    """Details und Token-Verbrauch einer Session abrufen."""
    return await get_session(_rest, session_id=session_id)


@mcp.tool()
async def hh_get_messages(session_id: str, limit: int = 50) -> list[dict]:
    """Nachrichten-Verlauf einer Session abrufen."""
    return await get_messages(_rest, session_id=session_id, limit=limit)


@mcp.tool()
async def hh_send_message(session_id: str, message: str) -> dict[str, Any]:
    """Eine Nachricht in eine laufende Session injizieren."""
    return await send_message(_rest, session_id=session_id, message=message)


# --- Agents ---

@mcp.tool()
async def hh_list_agents() -> list[dict]:
    """Alle Agenten mit Kurzinfo auflisten."""
    return await list_agents(_rest)


@mcp.tool()
async def hh_get_agent(agent_id: str) -> dict[str, Any]:
    """Vollständige Konfiguration eines Agenten abrufen."""
    return await get_agent(_rest, agent_id=agent_id)


@mcp.tool()
async def hh_update_agent(agent_id: str, field: str, value: Any) -> dict[str, Any]:
    """Ein Konfigurationsfeld eines Agenten setzen."""
    return await update_agent(_rest, agent_id=agent_id, field=field, value=value)


# --- Workspace ---

@mcp.tool()
async def hh_list_projects() -> list[dict]:
    """Alle Workspace-Projekte auflisten."""
    return await list_projects(_rest)


@mcp.tool()
async def hh_list_files(project_id: str, path: str = "") -> dict[str, Any]:
    """Verzeichnis-Listing eines Projekts abrufen."""
    return await list_files(_rest, project_id=project_id, path=path)


@mcp.tool()
async def hh_read_file(project_id: str, path: str) -> dict[str, Any]:
    """Dateiinhalt aus einem Projekt lesen (read-only)."""
    return await read_file(_rest, project_id=project_id, path=path)


# --- Datamining ---

@mcp.tool()
async def hh_dm_search(
    q: str = "",
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Events im Datamining-Index per Volltextsuche finden."""
    return await dm_search(
        _rest, q=q, event_type=event_type,
        from_date=from_date, to_date=to_date, limit=limit,
    )


@mcp.tool()
async def hh_dm_get_session(session_id: str) -> dict[str, Any]:
    """Eine Datamining-Session als zusammengesetzte Chunks abrufen."""
    return await dm_get_session(_rest, session_id=session_id)


@mcp.tool()
async def hh_dm_list_sessions(limit: int = 20) -> list[dict]:
    """Letzte Datamining-Sessions mit Event-Anzahl auflisten."""
    return await dm_list_sessions(_rest, limit=limit)


@mcp.tool()
async def hh_dm_stats() -> dict[str, Any]:
    """Token- und Kostenstatistiken aus dem Datamining abrufen."""
    return await dm_stats(_rest)


# --- AgentLink ---

@mcp.tool()
async def hh_al_status() -> dict[str, Any]:
    """AgentLink-Verbindungsstatus und bekannte Agenten anzeigen."""
    return await al_status(_rest, _al)


@mcp.tool()
async def hh_al_send(
    to_agent: str,
    task_type: str,
    description: str,
    context: dict | None = None,
) -> dict[str, Any]:
    """Einen Handoff per AgentLink an einen anderen Agenten abschicken."""
    return await al_send(_al, to_agent=to_agent, task_type=task_type,
                         description=description, context=context)


@mcp.tool()
async def hh_al_check_inbox() -> list[dict]:
    """Eingegangene AgentLink-Handoffs aus der Inbox lesen."""
    return await al_check_inbox(_al)


@mcp.tool()
async def hh_al_reply(state_id: str, result: str) -> dict[str, Any]:
    """Auf einen empfangenen AgentLink-Handoff antworten."""
    return await al_reply(_al, state_id=state_id, result=result)


if __name__ == "__main__":
    mcp.run()
