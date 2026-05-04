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
    "GITHUB_TOKEN automatisch gesetzt — `gh issue create` etc. funktionieren "
    "ohne extra Auth."
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
    except ImportError:
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


# Sensitive ENV-Variablen die NICHT an shell_exec weitergegeben werden:
# JWT-Signing-Key (= jeder mit dem Key kann beliebige User-Tokens fälschen),
# DSN-Passwörter, Provider-API-Keys aus Service-Config.
_ENV_DENYLIST = {
    "HH_SECRET_KEY",
    "HH_JWT_SECRET",
    "HH_PG_MIRROR_DSN",
    "HH_DATABASE_URL",
    "HH_AGENTLINK_TOKEN",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "MINIMAX_API_KEY",
    "DISCORD_BOT_TOKEN",
}


def _build_env(ctx: ToolContext) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in _ENV_DENYLIST}
    token = _resolve_gh_token(ctx)
    if token:
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token
    return env


import re

# Hard-Block: mmx speech-Synthese via shell_exec. LLM rief das früher gerne auf
# wenn der User "lies vor"/"sende mir was als audio" sagte und hat damit das
# tägliche TTS-Kontingent gefressen. Quoten-relevante Calls laufen NUR über
# api/routes/tts.py (mit Daily-Cap) oder das dedizierte plugin minimax_creator.speech.
_BLOCKED_MMX_SPEECH = re.compile(r"\bmmx\b.*\b(speech|tts)\b", re.IGNORECASE)
_MMX_MUSIC_GEN = re.compile(r"\bmmx\b.*\bmusic\b.*\bgenerate\b", re.IGNORECASE)


def _rewrite_cmd(cmd: str) -> str:
    if _MMX_MUSIC_GEN.search(cmd) and "--model" not in cmd:
        cmd = cmd.rstrip() + " --model music-2.6"
    return cmd


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    cmd = args.get("cmd", "").strip()
    if not cmd:
        return ToolResult.fail("Leerer Befehl")
    if _BLOCKED_MMX_SPEECH.search(cmd):
        return ToolResult.fail(
            "mmx speech/tts via shell_exec ist gesperrt — nutze das dedizierte "
            "Tool 'speech' (plugin minimax-creator) oder den /api/tts-Endpoint."
        )
    cmd = _rewrite_cmd(cmd)
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
