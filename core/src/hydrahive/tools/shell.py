from __future__ import annotations

from hydrahive.tools._launcher import get_launcher
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Führt einen Shell-Befehl im Workspace aus. Gibt stdout, stderr und "
    "Exit-Code zurück. Default-Timeout: 60s. "
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


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    cmd = args.get("cmd", "").strip()
    if not cmd:
        return ToolResult.fail("Leerer Befehl")
    timeout = int(args.get("timeout", 60))
    if timeout < 1 or timeout > 600:
        return ToolResult.fail("Timeout muss zwischen 1 und 600 Sekunden liegen")

    launcher = get_launcher()
    res = await launcher.run(cmd, cwd=ctx.workspace, timeout=timeout)

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


TOOL = Tool(name="shell_exec", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute)
