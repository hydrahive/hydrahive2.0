"""Plan eines Löschvorgangs: was gesperrt, gepackt und gelöscht wird (Spec archiv-system.md, Etappe 2).

Der Plan ist reines JSON und steht im Auftrag (config_dir/archive-jobs.json). So kann ein
Neustart ab Schritt 6 genau das zu Ende löschen, was vorher beschlossen war – auch wenn das
Objekt inzwischen halb weg ist.
"""
from __future__ import annotations

from hydrahive.agents import config as agent_config
from hydrahive.agents._paths import agent_dir
from hydrahive.archive import _targets as t


class PlanError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _agent_part(agent: dict, prefix: str = "") -> dict:
    ws = t.own_workspace(agent)
    return {"id": agent["id"], "name": agent.get("name") or agent["id"], "prefix": prefix,
            "agent_dir": str(agent_dir(agent["id"])), "workspace": str(ws) if ws else None}


def _project_part(project: dict) -> dict:
    from hydrahive.projects._paths import project_dir, workspace_path
    from hydrahive.smbmounts import db as mounts_db
    agents = t.project_agents(project)
    agent_ids = {a["id"] for a in agents}
    return {
        "id": project["id"], "name": project.get("name") or project["id"],
        "owner": project.get("created_by"), "members": project.get("members") or [],
        "project_dir": str(project_dir(project["id"])), "workspace": str(workspace_path(project["id"])),
        "agents": [_agent_part(a, f"agents/{a['id']}/") for a in agents],
        "sessions": t.project_sessions(project, agents),
        "unhook": t.foreign_project_sessions(project["id"], agent_ids),
        "mounts": [f"mounts/{m.name}" for m in mounts_db.list_for_project(project["id"])],
    }


def build(kind: str, target_id: str) -> dict:
    if kind not in t.KINDS:
        raise PlanError("unknown_kind")
    if kind in ("agent", "instance"):
        return _agent_plan(kind, target_id)
    if kind == "project":
        from hydrahive.projects import config as project_config
        project = project_config.get(target_id)
        if not project:
            raise PlanError("not_found")
        part = _project_part(project)
        return {"kind": kind, "id": target_id, "name": part["name"], "owner": part["owner"], "projects": [part],
                "agents": [], "sessions": [], "user": None}
    return _user_plan(target_id)


def _agent_plan(kind: str, agent_id: str) -> dict:
    try:
        agent = agent_config.get(agent_id)
    except ValueError:
        agent = None
    if not agent or (kind == "instance" and not agent.get("external")):
        raise PlanError("not_found")
    user = None
    owner = agent.get("owner")
    if kind == "instance" and owner:
        # Wie external_instances._owner_is_dedicated: Nutzer nur mit weg, wenn er eine reine
        # Instanz-Identität ist (Rolle user, keine weiteren Agenten). Schützt admin und geteilte Nutzer.
        others = [a for a in agent_config.list_by_owner(owner) if a["id"] != agent_id]
        part = _user_part(owner) if not others else None
        user = part if part and part["role"] == "user" else None
    return {"kind": kind, "id": agent_id, "name": agent.get("name") or agent_id, "owner": agent.get("owner"),
            "agents": [_agent_part(agent)], "sessions": t.agent_sessions(agent_id), "projects": [], "user": user}


def _user_part(username: str) -> dict | None:
    from hydrahive.api.middleware import users
    u = users.get_by_username(username)
    if not u:
        return None
    return {"name": username, "user_id": u["user_id"], "role": u["role"]}


def _user_plan(username: str) -> dict:
    user = _user_part(username)
    if user is None:
        raise PlanError("not_found")
    own = t.user_projects(username)
    parts = [_project_part(p) for p in own]
    in_projects = {s for p in parts for s in p["sessions"]}
    mine, foreign = t.user_agents(username, {p["id"] for p in own})
    user["memberships"] = [p["id"] for p in t.user_memberships(username)]
    user["hand_over"] = [a["id"] for a in foreign]
    return {"kind": "user", "id": username, "name": username, "owner": username, "user": user,
            "projects": parts, "agents": [_agent_part(a, f"agents/{a['id']}/") for a in mine],
            "sessions": t.user_sessions(username, in_projects)}


def all_agent_ids(plan: dict) -> list[str]:
    ids = [a["id"] for a in plan["agents"]]
    for p in plan["projects"]:
        ids += [a["id"] for a in p["agents"]]
    return ids


def all_session_ids(plan: dict) -> list[str]:
    return list(plan["sessions"]) + [s for p in plan["projects"] for s in p["sessions"]]
