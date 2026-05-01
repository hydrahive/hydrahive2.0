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
    "Bilder beschreiben/verstehen: `mmx vision describe --image <pfad_oder_url>` — "
    "mmx ist global installiert und mit dem MiniMax-Key authentifiziert."
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


def _resolve_gh_token(ctx: ToolContext) -> str | None:
    """Findet den GitHub-Token für den aktuellen Project-Agent. Wenn das Projekt
    mehrere Repos mit unterschiedlichen Tokens hat, wird der erste genommen —
    Common-Case ist ein User mit einem Account."""
    try:
        from hydrahive.agents import config as agent_config
        from hydrahive.projects import config as project_config
    except Exception:
        return None
    agent = agent_config.get(ctx.agent_id)
    if not agent:
        return None
    project_id = agent.get("project_id")
    if not project_id:
        return None
    project = project_config.get(project_id)
    if not project:
        return None
    repos = project.get("git_repos", {}) or {}
    for r in repos.values():
        if isinstance(r, dict) and r.get("git_token"):
            return r["git_token"]
    return project.get("git_token") or None


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
