"""System-Topologie-Graph aus Mirror-DB.

Knoten: Agenten, Benutzer, Tools
Kanten: User ↔ Agent (Sessions), Agent → Tool (Nutzungen)
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


async def build_topology() -> dict:
    from hydrahive.db import mirror
    pool = mirror._pool
    if not pool:
        return {"active": False, "nodes": [], "links": [], "active_agents": []}

    try:
        async with pool.acquire() as conn:
            agents = await conn.fetch("""
                SELECT agent_name, COUNT(DISTINCT session_id) AS session_count
                FROM events
                WHERE agent_name IS NOT NULL AND agent_name != ''
                GROUP BY agent_name
                ORDER BY session_count DESC
            """)
            users = await conn.fetch("""
                SELECT username, COUNT(DISTINCT session_id) AS session_count
                FROM events
                WHERE username IS NOT NULL AND username != ''
                GROUP BY username
                ORDER BY session_count DESC
            """)
            tools = await conn.fetch("""
                SELECT tool_name, COUNT(*) AS use_count
                FROM events
                WHERE event_type = 'tool_use'
                  AND tool_name IS NOT NULL AND tool_name != ''
                GROUP BY tool_name
                ORDER BY use_count DESC
                LIMIT 60
            """)
            user_agent = await conn.fetch("""
                SELECT username, agent_name, COUNT(DISTINCT session_id) AS session_count
                FROM events
                WHERE username IS NOT NULL AND username != ''
                  AND agent_name IS NOT NULL AND agent_name != ''
                GROUP BY username, agent_name
            """)
            agent_tool = await conn.fetch("""
                SELECT agent_name, tool_name, COUNT(*) AS use_count
                FROM events
                WHERE event_type = 'tool_use'
                  AND agent_name IS NOT NULL AND agent_name != ''
                  AND tool_name IS NOT NULL AND tool_name != ''
                GROUP BY agent_name, tool_name
                ORDER BY use_count DESC
            """)
            active = await conn.fetch("""
                SELECT DISTINCT agent_name
                FROM events
                WHERE agent_name IS NOT NULL
                  AND created_at > NOW() - INTERVAL '60 seconds'
            """)
    except Exception as e:
        logger.warning("Topology: DB-Fehler: %s", e)
        return {"active": True, "nodes": [], "links": [], "active_agents": [], "error": str(e)}

    nodes = []
    max_a = max((r["session_count"] for r in agents), default=1)
    for r in agents:
        nodes.append({
            "id": f"agent:{r['agent_name']}",
            "label": r["agent_name"],
            "type": "agent",
            "group": "agent",
            "val": 2 + (r["session_count"] / max_a) * 8,
            "session_count": r["session_count"],
        })

    max_u = max((r["session_count"] for r in users), default=1)
    for r in users:
        nodes.append({
            "id": f"user:{r['username']}",
            "label": r["username"],
            "type": "user",
            "group": "user",
            "val": 2 + (r["session_count"] / max_u) * 6,
            "session_count": r["session_count"],
        })

    max_t = max((r["use_count"] for r in tools), default=1)
    for r in tools:
        nodes.append({
            "id": f"tool:{r['tool_name']}",
            "label": r["tool_name"],
            "type": "tool",
            "group": "tool",
            "val": 1 + (r["use_count"] / max_t) * 5,
            "use_count": r["use_count"],
        })

    links = []
    for r in user_agent:
        links.append({
            "source": f"user:{r['username']}",
            "target": f"agent:{r['agent_name']}",
            "type": "has_sessions",
            "value": int(r["session_count"]),
        })
    for r in agent_tool:
        links.append({
            "source": f"agent:{r['agent_name']}",
            "target": f"tool:{r['tool_name']}",
            "type": "uses_tool",
            "value": int(r["use_count"]),
        })

    return {
        "active": True,
        "nodes": nodes,
        "links": links,
        "active_agents": [r["agent_name"] for r in active],
    }
