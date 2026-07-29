"""Member-Management für Projekte. Admin-Rechte werden auf Route-Ebene geprüft.

Members sind ``list[{username, role}]`` — Struktur-Zugriff läuft über
``_members_model``. ``created_by`` ist implizit admin und steht nicht in der
Liste.
"""
from __future__ import annotations

from hydrahive.db._utils import now_iso
from hydrahive.projects import _validation
from hydrahive.projects import _members_model
from hydrahive.projects._paths import config_path
from hydrahive.projects.config import _save_atomic, get

DEFAULT_ROLE = _members_model.DEFAULT_ROLE


def _entry(cfg: dict, username: str) -> dict | None:
    for m in cfg["members"]:
        if m["username"] == username:
            return m
    return None


def add(project_id: str, username: str, role: str = DEFAULT_ROLE) -> dict:
    _validation.validate_member(username)
    _validation.validate_role(role)
    cfg = get(project_id)
    if not cfg:
        raise KeyError(f"Projekt '{project_id}' nicht gefunden")
    existing = _entry(cfg, username)
    if existing:
        # Idempotent: bereits Member -> ggf. Rolle aktualisieren.
        existing["role"] = role
    else:
        cfg["members"].append({"username": username, "role": role})
    cfg["updated_at"] = now_iso()
    _save_atomic(config_path(project_id), cfg)
    from hydrahive.agents._workspace_links import sync_links_for_user
    sync_links_for_user(username)
    return cfg


def set_role(project_id: str, username: str, role: str) -> dict:
    _validation.validate_role(role)
    cfg = get(project_id)
    if not cfg:
        raise KeyError(f"Projekt '{project_id}' nicht gefunden")
    entry = _entry(cfg, username)
    if not entry:
        raise KeyError(f"'{username}' ist kein Member von '{project_id}'")
    entry["role"] = role
    cfg["updated_at"] = now_iso()
    _save_atomic(config_path(project_id), cfg)
    return cfg


def remove(project_id: str, username: str) -> dict:
    cfg = get(project_id)
    if not cfg:
        raise KeyError(f"Projekt '{project_id}' nicht gefunden")
    entry = _entry(cfg, username)
    if not entry:
        return cfg
    cfg["members"].remove(entry)
    cfg["updated_at"] = now_iso()
    _save_atomic(config_path(project_id), cfg)
    from hydrahive.agents._workspace_links import sync_links_for_user
    sync_links_for_user(username)
    return cfg
