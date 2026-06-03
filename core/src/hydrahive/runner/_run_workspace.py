"""Wählt das Arbeitsverzeichnis (cwd) für einen Run.

Hat die Session ein gültiges Projekt, ist das Projekt-Workspace das cwd — so
arbeitet der Agent (Buddy/Master) direkt im Projekt-Repo statt in seinem
generischen Agent-Workspace. Das ist der Grund, warum der Master sonst „sucht":
ohne aktives Projekt kennt er kein eindeutiges Arbeitsverzeichnis.

Konservativ: nur `session.project_id` weist das Projekt-Workspace zu. Der
tool_config-Pfad (Agent-zu-Agent-Runs) bleibt unverändert beim Agent-Workspace.
"""
from __future__ import annotations

from pathlib import Path

from hydrahive.agents._paths import ensure_workspace as _agent_workspace


def resolve_run_context(session, agent: dict, tool_config: dict | None = None) -> tuple[Path, str | None]:
    """Liefert (workspace, project_id) für den Run."""
    project_id = getattr(session, "project_id", None)
    if project_id:
        from hydrahive.projects import config as project_config
        from hydrahive.projects._paths import ensure_workspace as project_workspace

        if project_config.get(project_id):
            return project_workspace(project_id), project_id

    return _agent_workspace(agent), (tool_config or {}).get("project_id")


def effective_tool_config(agent: dict, tool_config: dict | None) -> dict:
    """ctx.config für den Run: persistente Agent-tool_config als Basis, der
    per-Run-tool_config (z.B. Agent-zu-Agent) überschreibt. So feuern die
    smtp/imap-Overrides in send_mail/read_mail aus der Agent-Config (Schicht 2)."""
    return {**(agent.get("tool_config") or {}), **(tool_config or {})}


def project_layout_hint(workspace: Path, project: dict) -> str:
    """Beschreibt die Projekt-Struktur fürs System-Prompt — wo die Repos liegen,
    welche Assets daneben. Der cwd ist der Projekt-Root; Repos sind Unterordner
    (`clone_into → workspace/<repo_name>/`). Ohne diesen Hinweis tastet der Agent
    sich durch (pwd/ls/git remote), um das richtige Repo zu finden.
    """
    name = project.get("name") or "?"
    repos = set(project.get("git_repos", {})) - {"_root"}
    lines = [
        f"Aktives Projekt: {name}",
        f"Arbeitsverzeichnis (cwd): {workspace}",
    ]
    entries: list[str] = []
    try:
        for p in sorted(workspace.iterdir(), key=lambda x: x.name):
            if p.name == ".git" or not p.is_dir():
                continue
            is_repo = p.name in repos or (p / ".git").exists()
            entries.append(f"  - ./{p.name}/" + (" (Git-Repo)" if is_repo else ""))
            if len(entries) >= 20:
                break
    except OSError:
        pass
    if entries:
        lines.append("Inhalt:")
        lines.extend(entries)
    named = sorted(repos)
    if len(named) == 1:
        lines.append(f"Für Git-Arbeit ins Repo wechseln: cd ./{named[0]}/")
    lines.append("Bleib in diesem Projekt — arbeite nicht in anderen Verzeichnissen.")
    return "\n".join(lines)
