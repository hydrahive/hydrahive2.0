from __future__ import annotations

import json
from pathlib import Path

from hydrahive.settings import settings


def _memory_file(agent_id: str) -> Path:
    return settings.agents_dir / agent_id / "memory.json"


def load(agent_id: str) -> dict[str, str]:
    path = _memory_file(agent_id)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save(agent_id: str, data: dict[str, str]) -> None:
    path = _memory_file(agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_key(agent_id: str, key: str) -> str | None:
    return load(agent_id).get(key)


def write_key(agent_id: str, key: str, content: str) -> None:
    data = load(agent_id)
    data[key] = content
    save(agent_id, data)


def delete_key(agent_id: str, key: str) -> bool:
    data = load(agent_id)
    if key not in data:
        return False
    del data[key]
    save(agent_id, data)
    return True


def list_keys(agent_id: str) -> list[str]:
    return sorted(load(agent_id).keys())
