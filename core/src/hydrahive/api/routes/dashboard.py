"""Dashboard-Aggregator — fasst Stats, Health, Recent Sessions und Server in
einem Call zusammen. Vermeidet 5+ Round-Trips beim Page-Load."""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.agentlink import is_connected as agentlink_connected
from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.version import current_status
from hydrahive.containers import db as containers_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db.connection import db
from hydrahive.settings import settings
from hydrahive.vms import db as vms_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _today_start_iso() -> str:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat()


def _health() -> dict:
    backend = {"ok": True}
    agentlink = {"ok": agentlink_connected(), "configured": bool(settings.agentlink_url)}
    if not agentlink["configured"]:
        agentlink = {"ok": True, "configured": False}

    ip_bin = shutil.which("ip") or "/sbin/ip"
    bridge_ok = False
    try:
        r = subprocess.run([ip_bin, "-br", "link", "show", "br0"],
                           capture_output=True, text=True, timeout=2)
        bridge_ok = r.returncode == 0
    except Exception:
        pass

    ts_bin = shutil.which("tailscale")
    tailscale_ok = False
    tailscale_present = bool(ts_bin)
    if tailscale_present:
        try:
            r = subprocess.run([ts_bin, "status", "--json", "--peers=false"],
                               capture_output=True, text=True, timeout=2)
            tailscale_ok = r.returncode == 0 and '"BackendState":"Running"' in r.stdout
        except Exception:
            pass

    return {
        "backend": backend,
        "agentlink": agentlink,
        "bridge": {"ok": bridge_ok},
        "tailscale": {"ok": tailscale_ok, "configured": tailscale_present},
    }


@router.get("")
def summary(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    username, role = auth
    today = _today_start_iso()

    user_agent_ids: set[str] = set()
    if role == "admin":
        all_agents = agent_config.list_all()
    else:
        all_agents = agent_config.list_by_owner(username)
    user_agent_ids = {a["id"] for a in all_agents}

    sessions_user = sessions_db.list_for_user(username, limit=200)
    if role == "admin":
        sessions_user = sessions_db.list_for_user(username, limit=200)

    active_sessions = sum(1 for s in sessions_user if s.status == "active")

    with db() as conn:
        if role == "admin":
            tokens_today = conn.execute(
                "SELECT COALESCE(SUM(token_count), 0) FROM messages "
                "WHERE created_at >= ? AND role = 'assistant'", (today,),
            ).fetchone()[0]
            tool_calls_today = conn.execute(
                "SELECT COUNT(*) FROM tool_calls WHERE created_at >= ?", (today,),
            ).fetchone()[0]
        else:
            session_ids = [s.id for s in sessions_user]
            if session_ids:
                placeholders = ",".join("?" * len(session_ids))
                tokens_today = conn.execute(
                    f"SELECT COALESCE(SUM(token_count), 0) FROM messages "
                    f"WHERE session_id IN ({placeholders}) AND created_at >= ? AND role = 'assistant'",
                    [*session_ids, today],
                ).fetchone()[0]
                tool_calls_today = conn.execute(
                    f"SELECT COUNT(*) FROM tool_calls m JOIN messages msg ON m.message_id = msg.id "
                    f"WHERE msg.session_id IN ({placeholders}) AND m.created_at >= ?",
                    [*session_ids, today],
                ).fetchone()[0]
            else:
                tokens_today = 0
                tool_calls_today = 0

    vms = vms_db.list_vms(owner=None if role == "admin" else username)
    containers = containers_db.list_(owner=None if role == "admin" else username)
    servers_running = sum(1 for v in vms if v.actual_state == "running") + \
                      sum(1 for c in containers if c.actual_state == "running")

    agents_by_id = {a["id"]: a for a in all_agents}
    recent_sessions = []
    for s in sessions_user[:10]:
        a = agents_by_id.get(s.agent_id)
        recent_sessions.append({
            "id": s.id,
            "title": s.title or "",
            "agent_id": s.agent_id,
            "agent_name": a.get("name") if a else "?",
            "agent_type": a.get("type") if a else None,
            "status": s.status,
            "updated_at": s.updated_at,
            "project_id": s.project_id,
        })

    servers = []
    for v in vms:
        servers.append({
            "kind": "vm", "id": v.vm_id, "name": v.name,
            "actual_state": v.actual_state, "project_id": v.project_id,
        })
    for c in containers:
        servers.append({
            "kind": "container", "id": c.container_id, "name": c.name,
            "actual_state": c.actual_state, "project_id": c.project_id,
        })

    agents = [{
        "id": a["id"], "type": a["type"], "name": a["name"],
        "owner": a.get("owner"), "project_id": a.get("project_id"),
        "status": a.get("status", "active"),
    } for a in all_agents]
    if role != "admin":
        agents = [a for a in agents if a["id"] in user_agent_ids]

    commit, behind = current_status()

    return {
        "health": _health(),
        "stats": {
            "active_sessions": active_sessions,
            "tokens_today": tokens_today,
            "tool_calls_today": tool_calls_today,
            "servers_running": servers_running,
            "servers_total": len(vms) + len(containers),
        },
        "recent_sessions": recent_sessions,
        "servers": servers,
        "agents": agents,
        "version": {"commit": commit, "update_behind": behind},
    }
