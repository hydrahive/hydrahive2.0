"""Read helpers + atomic save for project configs."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from hydrahive.projects._paths import config_path, projects_root

logger = logging.getLogger(__name__)


def _save_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)


def _normalize(cfg: dict) -> dict:
    cfg.setdefault("status", "active")
    cfg.setdefault("description", "")
    cfg.setdefault("members", [])
    cfg.setdefault("git_initialized", False)
    cfg.setdefault("git_token", "")
    cfg.setdefault("git_repos", {})
    cfg.setdefault("samba_enabled", False)
    cfg.setdefault("notes", "")
    cfg.setdefault("tags", [])
    cfg.setdefault("mcp_server_ids", [])
    cfg.setdefault("allowed_plugins", [])
    cfg.setdefault("allowed_specialists", [])
    cfg.setdefault("llm_api_key", "")
    cfg.setdefault("metadata", {})
    cfg.setdefault("updated_at", cfg.get("created_at", ""))
    return cfg


def get(project_id: str) -> dict | None:
    path = config_path(project_id)
    if not path.exists():
        return None
    return _normalize(json.loads(path.read_text()))


def list_all() -> list[dict]:
    if not projects_root().exists():
        return []
    out = []
    for d in sorted(projects_root().iterdir()):
        p = d / "config.json"
        if p.exists():
            try:
                out.append(_normalize(json.loads(p.read_text())))
            except json.JSONDecodeError:
                logger.warning("Defekte Project-Config: %s", p)
    return out


def list_for_user(username: str) -> list[dict]:
    return [p for p in list_all()
            if username in p.get("members", []) or p.get("created_by") == username]
