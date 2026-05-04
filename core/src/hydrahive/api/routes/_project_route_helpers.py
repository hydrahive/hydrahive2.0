from __future__ import annotations

from pathlib import Path

from fastapi import status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    members: list[str] = []
    llm_model: str
    init_git: bool = False


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    members: list[str] | None = None
    allowed_specialists: list[str] | None = None


def check_project_access(project: dict, username: str, role: str) -> None:
    if role == "admin":
        return
    if username in project.get("members", []) or project.get("created_by") == username:
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
