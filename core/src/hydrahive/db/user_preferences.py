from __future__ import annotations

import json
from typing import Any

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

DEFAULT_PREFERENCES: dict[str, Any] = {
    "active_project_id": None,
    "active_media_project_id": None,
    "active_vault_scope": "private",
    "cockpit_layout": {},
}

_ALLOWED_TOP_LEVEL = set(DEFAULT_PREFERENCES.keys())


def _normalize(raw: dict[str, Any] | None) -> dict[str, Any]:
    data = dict(DEFAULT_PREFERENCES)
    if raw:
        for key, value in raw.items():
            if key in _ALLOWED_TOP_LEVEL:
                data[key] = value
    if not isinstance(data.get("cockpit_layout"), dict):
        data["cockpit_layout"] = {}
    if data.get("active_vault_scope") not in ("private", "family", "business"):
        data["active_vault_scope"] = "private"
    return data


def get(user_id: str) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT preferences FROM user_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return dict(DEFAULT_PREFERENCES)
    try:
        parsed = json.loads(row["preferences"])
    except (json.JSONDecodeError, TypeError):
        parsed = {}
    return _normalize(parsed if isinstance(parsed, dict) else {})


def patch(user_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    current = get(user_id)
    for key, value in changes.items():
        if key in _ALLOWED_TOP_LEVEL:
            current[key] = value
    current = _normalize(current)
    with db() as conn:
        conn.execute(
            """INSERT INTO user_preferences (user_id, preferences, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 preferences = excluded.preferences,
                 updated_at = excluded.updated_at""",
            (user_id, json.dumps(current, ensure_ascii=False), now_iso()),
        )
    return current
