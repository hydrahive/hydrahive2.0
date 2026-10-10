"""Wer darf welche Datei über /api/files sehen? (Issue #538, Sicherheitsbefund 10.10.2026)

Vorher reichte ein Login: jede Datei unter data_dir/workspaces (alle Projekte, Master, Spezialisten) und unter /tmp war
für jeden angemeldeten Nutzer lesbar. Jetzt wird der AUFGELÖSTE Pfad (Symlinks, ``..``) einer Wurzel zugeordnet:

    workspaces/projects/<pid>/…       Mitglied des Projekts (Rolle ≥ read) – wie die Projekt-Routen
    workspaces/master/<aid>/…         Besitzer des Agenten
    workspaces/specialists/<aid>/…    Besitzer des Agenten; gehört er zu einem Projekt, auch dessen Mitglieder
    workspaces/<sonst>, /tmp          nur System-Admin
    HH_MEDIA_DIRS                     wie bisher alle Angemeldeten (vom Admin bewusst freigegeben)
    data_dir außerhalb workspaces/    niemand (sessions.db, Konfiguration) – auch wenn data_dir unter /tmp liegt

System-Admins dürfen alles unter den erlaubten Wurzeln. Unbekanntes Projekt bzw. unbekannter Agent → 404, damit nicht
erkennbar ist, ob es ihn gibt. Reihenfolge: erst Workspaces, dann Medienordner, zuletzt /tmp – data_dir kann selbst
unter /tmp liegen (Tests, HH_DATA_DIR), dann gilt die strengere Workspace-Regel.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import status

from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings


def _under(real: Path, root: Path) -> tuple[str, ...] | None:
    try:
        return real.relative_to(root).parts
    except ValueError:
        return None


def _deny() -> None:
    raise coded(status.HTTP_403_FORBIDDEN, "path_not_allowed")


def _missing() -> None:
    raise coded(status.HTTP_404_NOT_FOUND, "file_not_found")


def _project_reader(project: dict | None, username: str) -> bool:
    from hydrahive.projects import _members_model
    return bool(project) and _members_model.has_at_least(_members_model.role_of(project, username), "read")


def _check_project(pid: str, username: str) -> None:
    from hydrahive.projects import config as project_config
    project = project_config.get(pid) if pid else None
    if project is None:
        _missing()
    if not _project_reader(project, username):
        _deny()


def _check_agent(aid: str, kind: str, username: str) -> None:
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    agent = agent_config.get(aid) if aid else None
    if agent is None or agent.get("type", "specialist") != kind:
        _missing()
    if agent.get("owner") == username:
        return
    if kind == "specialist" and agent.get("project_id"):
        if _project_reader(project_config.get(agent["project_id"]), username):
            return
    _deny()


def check_read(real: Path, username: str, role: str) -> None:
    """Wirft 403/404, wenn ``username`` die (bereits aufgelöste) Datei ``real`` nicht sehen darf."""
    workspaces = (settings.data_dir / "workspaces").resolve()
    parts = _under(real, workspaces)
    if parts is not None:
        if role == "admin":
            return
        if len(parts) < 3:            # Datei direkt in workspaces/ oder workspaces/<art>/ – gehört niemandem
            _deny()
        kind, owner_id = parts[0], parts[1]
        if kind == "projects":
            _check_project(owner_id, username)
        elif kind == "master":
            _check_agent(owner_id, "master", username)
        elif kind == "specialists":
            _check_agent(owner_id, "specialist", username)
        else:
            _deny()
        return
    for d in settings.media_dirs:
        try:
            if _under(real, d.resolve()) is not None:
                return
        except OSError:
            continue
    if _under(real, settings.data_dir.resolve()) is not None:
        _deny()                       # sessions.db, Konfiguration … – auch wenn data_dir unter /tmp liegt
    if role != "admin":               # /tmp: LLM-Ausgaben, aber auch Zwischenstände anderer Nutzer
        _deny()
