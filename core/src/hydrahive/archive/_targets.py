"""Was gehört zu einem Lösch-Ziel? (Spec archiv-system.md, Etappe 2, „Was in welches Paket kommt“)

Nur Lesen. Gelöscht und gepackt wird in _remove.py bzw. _bundle.py.
"""
from __future__ import annotations

from pathlib import Path

from hydrahive.agents import config as agent_config
from hydrahive.agents._paths import agent_dir, workspace_for

KINDS = ("agent", "project", "user", "instance", "orphan_agent")
ARCHIVE_KIND = {"agent": "agents", "instance": "agents", "orphan_agent": "agents", "project": "projects",
                "user": "users"}
REASON = {"agent": "agent_deleted", "instance": "instance_deleted", "project": "project_deleted",
          "user": "user_deleted", "orphan_agent": "orphan"}


def own_workspace(agent: dict) -> Path | None:
    """Arbeitsordner, der nur diesem Agenten gehört. Der Projekt-Agent teilt sich den des Projekts → None."""
    if agent.get("type") == "project":
        return None
    return workspace_for(agent)


def agent_sessions(agent_id: str) -> list[str]:
    from hydrahive.db.connection import db
    with db() as conn:
        rows = conn.execute("SELECT id FROM sessions WHERE agent_id = ? ORDER BY created_at", (agent_id,)).fetchall()
    return [r["id"] for r in rows]


def project_agents(project: dict) -> list[dict]:
    """Projekt-Agent zuerst, dann alle Agenten mit dieser project_id (Spezialisten, Storyteller-Helfer)."""
    out, seen = [], set()
    main = agent_config.get(project.get("agent_id") or "") if project.get("agent_id") else None
    if main:
        out.append(main)
        seen.add(main["id"])
    for a in agent_config.list_all():
        if a.get("project_id") == project["id"] and a["id"] not in seen:
            out.append(a)
            seen.add(a["id"])
    return out


def project_sessions(project: dict, agents: list[dict]) -> list[str]:
    """Chats der Projekt-Agenten. Ein Buddy-Chat, der nur dem Projekt zugeordnet ist, gehört nicht dazu."""
    ids: list[str] = []
    for a in agents:
        ids += agent_sessions(a["id"])
    return ids


def foreign_project_sessions(project_id: str, agent_ids: set[str]) -> list[str]:
    """Chats fremder Agenten (z. B. Buddy), die nur auf das Projekt zeigen – werden abgehängt, nicht gelöscht."""
    from hydrahive.db.connection import db
    with db() as conn:
        rows = conn.execute("SELECT id, agent_id FROM sessions WHERE project_id = ?", (project_id,)).fetchall()
    return [r["id"] for r in rows if r["agent_id"] not in agent_ids]


def user_projects(username: str) -> list[dict]:
    """Projekte, die der Nutzer angelegt hat – die werden mitgelöscht (Till, 13.10.)."""
    from hydrahive.projects import _config_io
    return [p for p in _config_io.list_all() if p.get("created_by") == username]


def user_memberships(username: str) -> list[dict]:
    """Fremde Projekte, in denen er nur Mitglied ist."""
    from hydrahive.projects import _config_io, _members_model
    return [p for p in _config_io.list_all()
            if p.get("created_by") != username and _members_model.is_member(p, username)]


def user_agents(username: str, own_project_ids: set[str]) -> tuple[list[dict], list[dict]]:
    """(seine Agenten fürs Nutzer-Paket, seine Agenten in fremden Projekten → gehen an den Projekt-Ersteller)."""
    mine, foreign = [], []
    for a in agent_config.list_by_owner(username):
        pid = a.get("project_id")
        if pid and pid in own_project_ids:
            continue                                   # kommt ins Projekt-Paket
        if pid and a.get("type") != "master":
            foreign.append(a)
        else:
            mine.append(a)
    return mine, foreign


def user_sessions(username: str, exclude: set[str]) -> list[str]:
    """Alle Chats des Nutzers, die nicht schon in einem Projekt-Paket stecken."""
    from hydrahive.db.connection import db
    with db() as conn:
        rows = conn.execute("SELECT id FROM sessions WHERE user_id = ? ORDER BY created_at", (username,)).fetchall()
    return [r["id"] for r in rows if r["id"] not in exclude]


def agent_sources(agent: dict, prefix: str = "") -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = [(f"{prefix}agent", agent_dir(agent["id"]))]
    ws = own_workspace(agent)
    if ws is not None:
        out.append((f"{prefix}workspace", ws))
    return out
