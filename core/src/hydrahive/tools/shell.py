from __future__ import annotations

import logging
import os

from hydrahive.tools._launcher import get_launcher
from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


_DESCRIPTION = (
    "Führt einen Shell-Befehl im Workspace aus. Gibt stdout, stderr und "
    "Exit-Code zurück. Default-Timeout: 60s. "
    "Wenn das Projekt git_repos mit Token konfiguriert hat, sind GH_TOKEN + "
    "GITHUB_TOKEN automatisch gesetzt — `gh issue create` etc. funktionieren ohne "
    "extra Auth. "
    "WICHTIG: Für Multimedia-Generierung (Bild, Musik, Video, Sprache, "
    "Bild-Beschreibung) RUFE NIE `mmx ...` via shell_exec auf. Nutze "
    "stattdessen IMMER die dedizierten Tools `image`, `music`, `video`, "
    "`speech`, `vision` — die liefern absolute Pfade zurück, die im Chat "
    "automatisch als Bild/Audio/Video gerendert werden. shell_exec mit "
    "mmx liefert nur relative Pfade im Workspace, die der User nicht sieht."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "cmd": {
            "type": "string",
            "description": "Shell-Befehl der ausgeführt werden soll.",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in Sekunden (default 60).",
            "default": 60,
        },
        "description": {
            "type": "string",
            "description": "Kurze Beschreibung was der Befehl macht (optional).",
        },
    },
    "required": ["cmd"],
}


def _first_token_in(project: dict) -> str | None:
    repos = project.get("git_repos", {}) or {}
    for r in repos.values():
        if isinstance(r, dict) and r.get("git_token"):
            return r["git_token"]
    return project.get("git_token") or None


def _resolve_gh_token(ctx: ToolContext) -> str | None:
    """Findet den GitHub-Token für die aktuelle Tool-Invocation.

    Master-Agent: kein eigenes project_id — wir suchen alle Projekte des
    Owners und nehmen den ersten Token. Reicht wenn der User einen GitHub-
    Account hat. Edge-Case Multi-Account-User: später per cwd-basiertem
    Lookup ergänzen.

    Project-Agent: project_id ist gesetzt → direkt der Projekt-Token.
    """
    try:
        from hydrahive.agents import config as agent_config
        from hydrahive.projects import config as project_config
    except Exception:
        return None
    agent = agent_config.get(ctx.agent_id)
    if not agent:
        return None
    project_id = agent.get("project_id")
    if project_id:
        project = project_config.get(project_id)
        if project:
            return _first_token_in(project)
    owner = agent.get("owner") or ""
    if not owner:
        return None
    for p in project_config.list_for_user(owner):
        token = _first_token_in(p)
        if token:
            return token
    return None


def _build_env(ctx: ToolContext) -> dict:
    env = os.environ.copy()
    token = _resolve_gh_token(ctx)
    if token:
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token
    return env


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    cmd = args.get("cmd", "").strip()
    if not cmd:
        return ToolResult.fail("Leerer Befehl")
    timeout = int(args.get("timeout", 60))
    if timeout < 1 or timeout > 600:
        return ToolResult.fail("Timeout muss zwischen 1 und 600 Sekunden liegen")

    launcher = get_launcher()
    res = await launcher.run(cmd, cwd=ctx.workspace, timeout=timeout, env=_build_env(ctx))

    output = {
        "exit_code": res.exit_code,
        "stdout": res.stdout,
        "stderr": res.stderr,
    }
    if res.timed_out:
        output["timed_out"] = True
        return ToolResult(
            success=False,
            output=output,
            error=f"Timeout nach {timeout}s",
            metadata={"exit_code": res.exit_code},
        )
    return ToolResult.ok(output, exit_code=res.exit_code)


TOOL = Tool(name="shell_exec", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="shell")
