"""Member-Management für Projekte. Admin-only auf Route-Ebene."""
from __future__ import annotations

from hydrahive.db._utils import now_iso
from hydrahive.projects import _validation
from hydrahive.projects._paths import config_path
from hydrahive.projects.config import _save_atomic, get


def add(project_id: str, username: str) -> dict:
    _validation.validate_member(username)
    cfg = get(project_id)
    if not cfg:
        raise KeyError(f"Projekt '{project_id}' nicht gefunden")
    if username in cfg["members"]:
        return cfg
    cfg["members"].append(username)
    cfg["updated_at"] = now_iso()
    _save_atomic(config_path(project_id), cfg)
    return cfg


def remove(project_id: str, username: str) -> dict:
    cfg = get(project_id)
    if not cfg:
        raise KeyError(f"Projekt '{project_id}' nicht gefunden")
    if username not in cfg["members"]:
        return cfg
    cfg["members"].remove(username)
    cfg["updated_at"] = now_iso()
    _save_atomic(config_path(project_id), cfg)
    return cfg
