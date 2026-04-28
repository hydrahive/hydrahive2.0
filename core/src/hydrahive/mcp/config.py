"""MCP-Server-Registry: persistierte Liste konfigurierter Server."""
from __future__ import annotations

import json
import logging
from typing import Any

from hydrahive.db._utils import now_iso
from hydrahive.mcp import _validation
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


def _path():
    return settings.mcp_config


def _load_all() -> dict:
    p = _path()
    if not p.exists():
        return {"servers": []}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        logger.warning("Defekte MCP-Config — leer behandelt")
        return {"servers": []}


def _save_atomic(data: dict) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(p)


def list_all() -> list[dict]:
    return list(_load_all().get("servers", []))


def get(server_id: str) -> dict | None:
    for s in list_all():
        if s.get("id") == server_id:
            return s
    return None


def create(
    *,
    server_id: str,
    name: str,
    transport: str,
    command: str | None = None,
    args: list[str] | None = None,
    env: dict | None = None,
    url: str | None = None,
    headers: dict | None = None,
    description: str = "",
    enabled: bool = True,
) -> dict:
    cfg: dict[str, Any] = {
        "id": server_id,
        "name": name.strip(),
        "transport": transport,
        "description": description,
        "enabled": enabled,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    if transport == "stdio":
        cfg["command"] = command or ""
        cfg["args"] = list(args or [])
        cfg["env"] = dict(env or {})
    else:
        cfg["url"] = url or ""
        cfg["headers"] = dict(headers or {})

    _validation.validate(cfg)

    data = _load_all()
    if any(s.get("id") == cfg["id"] for s in data["servers"]):
        raise _validation.McpValidationError(f"Server-ID '{cfg['id']}' existiert bereits")
    data["servers"].append(cfg)
    _save_atomic(data)
    logger.info("MCP-Server angelegt: %s (%s)", cfg["id"], transport)
    return cfg


def update(server_id: str, **changes: Any) -> dict:
    data = _load_all()
    for i, s in enumerate(data["servers"]):
        if s.get("id") != server_id:
            continue
        for protected in ("id", "created_at"):
            changes.pop(protected, None)
        s.update(changes)
        s["updated_at"] = now_iso()
        _validation.validate(s)
        data["servers"][i] = s
        _save_atomic(data)
        return s
    raise KeyError(f"MCP-Server '{server_id}' nicht gefunden")


def delete(server_id: str) -> bool:
    data = _load_all()
    before = len(data["servers"])
    data["servers"] = [s for s in data["servers"] if s.get("id") != server_id]
    if len(data["servers"]) == before:
        return False
    _save_atomic(data)
    logger.info("MCP-Server gelöscht: %s", server_id)
    return True
