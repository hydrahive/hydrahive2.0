from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Listet alle Projekte des aktuellen Users mit deren Workspace-Pfad, "
    "konfigurierten Repos und Members. Nutzt der Master-Agent um zu wissen, "
    "welche Projekte es gibt und wo. Im Master-Workspace gibt es zusätzlich "
    "Symlinks unter `~/projects/<projektname>/` die direkt in die Projekt-"
    "Workspaces zeigen — `cd projects/<name>` wechselt rein."
)

_SCHEMA = {
    "type": "object",
    "properties": {},
    "required": [],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    from hydrahive.projects._paths import workspace_path
    agent = agent_config.get(ctx.agent_id)
    if not agent:
        return ToolResult.fail("Agent nicht gefunden")
    owner = agent.get("owner") or ""
    if not owner:
        return ToolResult.ok({"projects": []})

    projects = project_config.list_for_user(owner)
    out = []
    for p in projects:
        repos = []
        for name, cfg in (p.get("git_repos") or {}).items():
            repos.append({
                "name": name,
                "remote_url": (cfg or {}).get("remote_url") or "",
                "has_token": bool((cfg or {}).get("git_token")),
            })
        out.append({
            "id": p["id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "status": p.get("status", "active"),
            "workspace": str(workspace_path(p["id"])),
            "repos": repos,
            "members": p.get("members", []),
            "samba_enabled": bool(p.get("samba_enabled")),
        })
    return ToolResult.ok({"projects": out, "count": len(out)})


TOOL = Tool(
    name="list_projects",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="agents",
)
