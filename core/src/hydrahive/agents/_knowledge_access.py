"""Agent-Einstellung ``knowledge_access``: welches Datamining-Wissen ein Agent lesen darf.

Spec: docs/specs/datamining-access.md. Nur über die Admin-Route änderbar (PATCH /api/agents/{id});
``configure_specialist``/``create_specialist`` und die Buddy-Einstellungen übernehmen das Feld nicht
(feste Feldlisten). Die Auswertung macht ``db._mirror_scope.scope_for``.
"""
from __future__ import annotations

from typing import Any

from hydrahive.agents._validation import AgentValidationError

_SCOPES = ("project", "user")
_KEYS = {"scope", "projects", "sensitive", "max_level"}
MAX_PROJECTS = 50


def normalize(value: Any) -> dict | None:
    """Prüft und vereinheitlicht ``knowledge_access``. ``None``/leer → Feld entfernen (Standard je Typ)."""
    if value in (None, {}, ""):
        return None
    if not isinstance(value, dict):
        raise AgentValidationError("knowledge_access muss ein Objekt sein")
    unknown = set(value) - _KEYS
    if unknown:
        raise AgentValidationError(f"knowledge_access: unbekannte Felder {sorted(unknown)}")
    out: dict = {}
    if "scope" in value:
        if value["scope"] not in _SCOPES:
            raise AgentValidationError(f"knowledge_access.scope muss eins von {_SCOPES} sein")
        out["scope"] = value["scope"]
    if "projects" in value:
        projects = value["projects"]
        if not isinstance(projects, list) or not all(isinstance(p, str) and p.strip() for p in projects):
            raise AgentValidationError("knowledge_access.projects muss eine Liste von Projekt-IDs sein")
        if len(projects) > MAX_PROJECTS:
            raise AgentValidationError(f"knowledge_access.projects: höchstens {MAX_PROJECTS} Projekte")
        from hydrahive.projects import config as project_config
        missing = [p for p in projects if not project_config.get(p.strip())]
        if missing:
            raise AgentValidationError(f"knowledge_access.projects: unbekannte Projekte {missing}")
        out["projects"] = list(dict.fromkeys(p.strip() for p in projects))
    if "max_level" in value:
        from hydrahive.db._mirror_levels import LEVELS
        if value["max_level"] not in LEVELS:
            raise AgentValidationError(f"knowledge_access.max_level muss eins von {LEVELS} sein")
        out["max_level"] = value["max_level"]
    if "sensitive" in value:
        if not isinstance(value["sensitive"], bool):
            raise AgentValidationError("knowledge_access.sensitive muss true oder false sein")
        out["sensitive"] = value["sensitive"]
    return out
