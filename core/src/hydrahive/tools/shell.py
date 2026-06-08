from __future__ import annotations

import logging
import os

from hydrahive.tools._launcher import get_launcher
from hydrahive.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


_DESCRIPTION = (
    "Führt einen Shell-Befehl im Workspace aus (bash). Gibt stdout, stderr und "
    "Exit-Code zurück. Default-Timeout: 60s. "
    "GH_TOKEN + GITHUB_TOKEN sind automatisch gesetzt wenn das Projekt einen GitHub-Token hat — "
    "`gh issue create`, `git push` etc. ohne extra Auth. "
    "GITEA_TOKEN ist gesetzt wenn ein Credential für localhost/127.0.0.1 (lokales Gitea) existiert — "
    "für Gitea-Pushes: `git -c http.extraHeader='Authorization: token '\"$GITEA_TOKEN\" push ...`. "
    "HH_SSH_KEYFILE ist gesetzt wenn ein System-SSH-Key vorhanden ist — "
    "für SSH zu bekannten Hosts: `ssh -i $HH_SSH_KEYFILE -o StrictHostKeyChecking=no user@host 'cmd'`. "
    "SSH mit Passwort: `sshpass -p '<pass>' ssh -o StrictHostKeyChecking=no <user>@<host> '<cmd>'` — "
    "Befehle in einem einzigen Aufruf bündeln."
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
# DSN-Passwörter, Service-Tokens.
# Provider-API-Keys werden hier NICHT hartcodiert, sondern aus llm._config (SSOT)
# gezogen: apply_keys() schreibt sie ins Prozess-ENV für LiteLLM, also müssen sie
# wieder raus — sonst liest ein Agent sie per `echo $OPENROUTER_API_KEY`. Über
# _ENV_MAP, damit ein neuer Provider nicht erneut durchrutscht (so wie OpenRouter).
_STATIC_ENV_DENYLIST = {
    "HH_SECRET_KEY",
    "HH_JWT_SECRET",
    "HH_PG_MIRROR_DSN",
    "HH_DATABASE_URL",
    "HH_AGENTLINK_TOKEN",
    "DISCORD_BOT_TOKEN",
    "MINIMAX_API_KEY",  # MiniMax: direktes SDK, nicht über _ENV_MAP/LiteLLM
}


def _env_denylist() -> set[str]:
    from hydrahive.llm._config import provider_env_vars

    return _STATIC_ENV_DENYLIST | provider_env_vars()


_GITEA_LOCAL_HOSTS = {"localhost", "127.0.0.1", "127.0.1.1"}


def _resolve_gitea_token(ctx: ToolContext) -> str | None:
    """Gitea-Token aus dem Credential-Store für den aktuellen User.

    Anforderungen: type=="bearer" + url_pattern-Hostname ist ein bekannter lokaler
    Gitea-Host. Parsed url_pattern für exakten Hostname-Vergleich (kein Substring-Match
    gegen beliebige Muster). Ergebnis → GITEA_TOKEN in der Env.
    """
    import urllib.parse as _up
    try:
        from hydrahive.credentials import list_credentials
    except ImportError:
        return None
    owner = getattr(ctx, "user_id", None) or ""
    if not owner:
        return None
    for cred in list_credentials(owner):
        if cred.type != "bearer":
            continue
        pattern = (cred.url_pattern or "").strip()
        if not pattern:
            continue
        try:
            host = _up.urlparse(pattern).hostname or ""
        except Exception:
            continue
        if host.lower() in _GITEA_LOCAL_HOSTS:
            return cred.value
    return None


def _resolve_ssh_keyfile() -> str | None:
    """System-SSH-Key des hydrahive-Service-Accounts, falls vorhanden."""
    try:
        from hydrahive.settings import settings
        data_dir = str(settings.data_dir)
    except Exception:
        data_dir = os.environ.get("HH_DATA_DIR", "/var/lib/hydrahive2")
    candidates = [
        os.path.join(data_dir, ".ssh", "id_ed25519"),
        os.path.join(data_dir, ".ssh", "id_rsa"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _build_env(ctx: ToolContext) -> dict:
    denylist = _env_denylist()
    env = {k: v for k, v in os.environ.items() if k not in denylist}
    token = _resolve_gh_token(ctx)
    if token:
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token
    gitea_token = _resolve_gitea_token(ctx)
    if gitea_token:
        env["GITEA_TOKEN"] = gitea_token
    ssh_keyfile = _resolve_ssh_keyfile()
    if ssh_keyfile:
        env["HH_SSH_KEYFILE"] = ssh_keyfile
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
