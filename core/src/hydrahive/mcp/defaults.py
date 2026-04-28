"""Quick-Add-Templates für die offiziellen MCP-Server aus der SPEC.

Jedes Template kennt ggf. `user_inputs` — Felder die der User vor dem Anlegen
ausfüllen muss (z.B. Pfad für filesystem, GitHub-Token).
Platzhalter im args-Array bzw. env-Dict mit `{name}` werden ersetzt.
"""
from __future__ import annotations


TEMPLATES: list[dict] = [
    {
        "id": "filesystem",
        "name": "Filesystem",
        "description": "Datei- und Verzeichniszugriff auf einen User-definierten Ordner",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "{path}"],
        "env": {},
        "user_inputs": [
            {"key": "path", "label": "Wurzel-Verzeichnis", "default": "/home/till", "required": True},
        ],
    },
    {
        "id": "memory",
        "name": "Memory",
        "description": "Knowledge-Graph-Memory (persistente Notizen, Beziehungen)",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": {},
        "user_inputs": [],
    },
    {
        "id": "sequential-thinking",
        "name": "Sequential Thinking",
        "description": "Chain-of-Thought-Helfer für komplexe Probleme",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "env": {},
        "user_inputs": [],
    },
    {
        "id": "fetch",
        "name": "Fetch",
        "description": "HTTP-Fetch + HTML→Markdown-Konvertierung (Python via uvx)",
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {},
        "user_inputs": [],
    },
    {
        "id": "time",
        "name": "Time",
        "description": "Zeit, Datum, Zeitzonen-Konvertierung (Python via uvx)",
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-time"],
        "env": {},
        "user_inputs": [],
    },
    {
        "id": "git",
        "name": "Git",
        "description": "Git-Repo-Inspektion (status, log, diff, blame) — Python via uvx",
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-git", "--repository", "{repo_path}"],
        "env": {},
        "user_inputs": [
            {"key": "repo_path", "label": "Repository-Pfad", "default": "/home/till/claudeneu", "required": True},
        ],
    },
    {
        "id": "sqlite",
        "name": "SQLite",
        "description": "SQLite-DB-Abfragen (Python via uvx)",
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-sqlite", "--db-path", "{db_path}"],
        "env": {},
        "user_inputs": [
            {"key": "db_path", "label": "DB-Pfad", "default": "/tmp/test.db", "required": True},
        ],
    },
    {
        "id": "github",
        "name": "GitHub",
        "description": "GitHub-API: Repos, Issues, PRs, Search (braucht Personal-Access-Token)",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "{token}"},
        "user_inputs": [
            {"key": "token", "label": "GitHub PAT", "default": "", "required": True, "secret": True},
        ],
    },
]


def get_template(template_id: str) -> dict | None:
    return next((t for t in TEMPLATES if t["id"] == template_id), None)


def render(template: dict, inputs: dict[str, str]) -> dict:
    """Fülle {placeholder}-Platzhalter in args/env mit User-Input."""
    args = [a.format(**inputs) if "{" in a else a for a in template.get("args", [])]
    env = {k: v.format(**inputs) if "{" in v else v for k, v in template.get("env", {}).items()}
    return {
        "name": template["name"],
        "transport": template["transport"],
        "command": template.get("command", ""),
        "args": args,
        "env": env,
        "description": template["description"],
    }
