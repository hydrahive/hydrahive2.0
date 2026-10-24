from __future__ import annotations

import json
import re
from typing import Any

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

DEFAULT_PREFERENCES: dict[str, Any] = {
    "active_project_id": None,
    "active_media_project_id": None,
    "active_vault_scope": "private",
    "cockpit_layout": {},
    # Startseite und Bereichs-Leiste (docs/specs/startdesktop.md)
    "landing": "start",
    "active_area": None,
    "area_last": {},
}

LANDINGS = ("start", "buddy", "dashboard")
_AREA_ID = re.compile(r"^[a-z0-9-]{1,32}$")
_APP_PATH = re.compile(r"^/[A-Za-z0-9/_-]{0,120}$")
AREA_LAST_MAX = 20


def _area_id(value: Any) -> str | None:
    return value if isinstance(value, str) and _AREA_ID.match(value) else None


def _area_last(value: Any) -> dict[str, str]:
    """Bereich → zuletzt benutzter Pfad. Falsche Einträge fallen weg, höchstens AREA_LAST_MAX."""
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for key, path in value.items():
        if len(out) >= AREA_LAST_MAX:
            break
        if _area_id(key) and isinstance(path, str) and _APP_PATH.match(path):
            out[key] = path
    return out

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
    if data.get("landing") not in LANDINGS:
        data["landing"] = "start"
    data["active_area"] = _area_id(data.get("active_area"))
    data["area_last"] = _area_last(data.get("area_last"))
    return data


def get(user_id: str) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT preferences FROM user_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return _normalize(None)
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
