from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded
from hydrahive.projects import _members_model


class MemberEntry(BaseModel):
    username: str = Field(..., min_length=1)
    role: str = Field("write", pattern="^(read|write|admin)$")


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    # Akzeptiert Legacy (list[str]) und neues Format (list[{username, role}]).
    members: list[str | MemberEntry] = []
    llm_model: str
    init_git: bool = False


# MCP-Server-IDs (mcp/_validation.validate_id) und Plugin-Namen: a-z A-Z 0-9 _ -
_ID_ITEM = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")


class ProjectUpdate(BaseModel):
    """PATCH-Felder. Alles andere verwirft pydantic still — notes/tags und die
    MCP-/Plugin-Einschränkung fehlten hier, das UI speicherte ins Leere
    (Task 3223371d). Ein Projekt-LLM-Key wird bewusst NICHT angenommen: kein
    Code nutzt ihn, und im Klartext in config.json gehört er nicht."""
    name: str | None = None
    description: str | None = None
    status: str | None = None
    members: list[str | MemberEntry] | None = None
    allowed_specialists: list[str] | None = None
    notes: str | None = Field(default=None, max_length=100_000)
    tags: list[Annotated[str, Field(min_length=1, max_length=64)]] | None = Field(default=None, max_length=50)
    mcp_server_ids: list[Annotated[str, _ID_ITEM]] | None = Field(default=None, max_length=50)
    allowed_plugins: list[Annotated[str, _ID_ITEM]] | None = Field(default=None, max_length=100)


def check_project_access(
    project: dict, username: str, role: str, required: str = "read"
) -> None:
    """Setzt Projekt-Rollen durch. System-Admins (Auth-role) dürfen alles.

    ``required`` ist die Mindest-Projektrolle (read < write < admin).
    """
    if role == "admin":
        return
    if _members_model.has_at_least(_members_model.role_of(project, username), required):
        return
    raise coded(status.HTTP_403_FORBIDDEN, "project_no_access")


TEXT_FILE_EXTS = {
    ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml",
    ".yml", ".toml", ".ini", ".cfg", ".sh", ".bash", ".env", ".gitignore",
    ".dockerfile", ".html", ".css", ".scss", ".xml", ".csv", ".log",
    ".sql", ".rs", ".go", ".java", ".c", ".cpp", ".h", ".rb", ".php",
}

TEXT_FILE_NAMES = {
    "Dockerfile", "Makefile", "Procfile", "Rakefile", "Gemfile",
    "LICENSE", "README", "CHANGELOG", "AUTHORS", "CONTRIBUTORS",
    "TODO", "NOTES", ".env", ".gitignore", ".dockerignore",
}


def is_text_file(target: Path) -> bool:
    if target.name in TEXT_FILE_NAMES:
        return True
    return target.suffix.lower() in TEXT_FILE_EXTS


def safe_workspace_path(workspace: Path, rel: str) -> Path:
    """Resolve `rel` inside `workspace`, blocking path-traversal."""
    try:
        resolved = (workspace / rel).resolve()
    except (OSError, ValueError):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_path")
    workspace_resolved = workspace.resolve()
    if resolved == workspace_resolved:
        return resolved
    try:
        resolved.relative_to(workspace_resolved)
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "path_traversal")
    return resolved
