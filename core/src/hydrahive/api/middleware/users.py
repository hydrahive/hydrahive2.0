from __future__ import annotations

import json
import logging
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

# User-Struktur:
# {"username": {"password_hash": "...", "role": "admin|user"}}


def _load() -> dict:
    path: Path = settings.users_config
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _save(users: dict) -> None:
    settings.users_config.parent.mkdir(parents=True, exist_ok=True)
    settings.users_config.write_text(json.dumps(users, indent=2))


def _hash(password: str) -> str:
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def verify(username: str, password: str) -> dict | None:
    """Returns user dict {username, role} or None if invalid."""
    users = _load()
    user = users.get(username)
    if not user:
        return None
    if user["password_hash"] != _hash(password):
        return None
    return {"username": username, "role": user["role"]}


def create(username: str, password: str, role: str = "user") -> None:
    """Creates a new user. Raises ValueError if username exists."""
    users = _load()
    if username in users:
        raise ValueError(f"User '{username}' existiert bereits")
    users[username] = {"password_hash": _hash(password), "role": role}
    _save(users)
    logger.info("User '%s' angelegt (role=%s)", username, role)


def update_password(username: str, new_password: str) -> None:
    users = _load()
    if username not in users:
        raise ValueError(f"User '{username}' nicht gefunden")
    users[username]["password_hash"] = _hash(new_password)
    _save(users)


def delete(username: str) -> None:
    users = _load()
    users.pop(username, None)
    _save(users)


def list_users() -> list[dict]:
    return [
        {"username": k, "role": v["role"]}
        for k, v in _load().items()
    ]


def ensure_admin(username: str, password: str) -> None:
    """Creates admin user if no users exist yet (first-run setup)."""
    if not _load():
        create(username, password, role="admin")
        logger.info("Admin '%s' beim ersten Start angelegt", username)
