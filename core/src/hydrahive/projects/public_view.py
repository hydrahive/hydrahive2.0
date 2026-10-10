"""Projekt-Config für API-Antworten und Fremd-Exporte — ohne Secrets.

Die gespeicherte config.json enthält Secrets (webhook_secret, git_token pro
Repo, Altbestand llm_api_key). GET /api/projects lieferte sie ungefiltert an
jedes Mitglied, auch an die Rolle "read" (Task 3223371d).

Allowlist statt Denylist: ein künftig neues Secret-Feld taucht nicht still in
der API auf, sondern muss hier bewusst freigegeben werden.
"""
from __future__ import annotations

from typing import Any

PUBLIC_FIELDS = (
    "id", "name", "description", "members", "agent_id", "status",
    "created_at", "updated_at", "created_by", "git_initialized",
    "samba_enabled", "notes", "tags", "metadata",
    "mcp_server_ids", "allowed_plugins", "allowed_specialists", "linked_projects",
)


def public_view(cfg: dict[str, Any]) -> dict[str, Any]:
    """Kopie ohne Secrets; statt der Werte nur has_*-Flags."""
    out = {k: cfg[k] for k in PUBLIC_FIELDS if k in cfg}
    out["has_webhook_secret"] = bool(cfg.get("webhook_secret"))
    # Pro Repo nur, ob ein Token hinterlegt ist. Remote-URLs stehen in git selbst
    # (GET .../git/repos) und können Zugangsdaten enthalten — hier nicht.
    out["git_repos"] = {
        name: {"has_token": bool(rc.get("git_token")) if isinstance(rc, dict) else False}
        for name, rc in (cfg.get("git_repos") or {}).items()
    }
    return out
