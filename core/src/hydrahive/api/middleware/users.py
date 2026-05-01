from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import bcrypt

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

# User-Struktur:
# {"username": {"password_hash": "...", "role": "admin|user"}}
# password_hash kann bcrypt ($2b$...) oder Legacy-SHA256 (64 hex chars) sein.
# Legacy-Hashes werden beim nächsten erfolgreichen Login transparent auf bcrypt
# migriert (lazy re-hash).


def _load() -> dict:
    path: Path = settings.users_config
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _save(users: dict) -> None:
    """Atomic write — verhindert truncated users.json bei parallelem
    Login + Hash-Migration (Race-Condition vor Fix war beobachtbar)."""
    settings.users_config.parent.mkdir(parents=True, exist_ok=True)
    tmp = settings.users_config.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(users, indent=2))
    tmp.replace(settings.users_config)


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _is_bcrypt(stored: str) -> bool:
    return stored.startswith(("$2a$", "$2b$", "$2y$"))


def _verify_hash(password: str, stored: str) -> bool:
    if _is_bcrypt(stored):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored.encode("ascii"))
        except ValueError:
            return False
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == stored


def verify(username: str, password: str) -> dict | None:
    """Returns user dict {username, role} or None if invalid.

    Migrates legacy SHA256 hashes to bcrypt on successful login.
    """
    users = _load()
    user = users.get(username)
    if not user:
        return None
    stored = user["password_hash"]
    if not _verify_hash(password, stored):
        return None
    if not _is_bcrypt(stored):
        users[username]["password_hash"] = _hash(password)
        _save(users)
        logger.info("User '%s' Hash auf bcrypt migriert", username)
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


def update_role(username: str, role: str) -> None:
    if role not in ("admin", "user"):
        raise ValueError(f"Ungültige Rolle: {role}")
    users = _load()
    if username not in users:
        raise ValueError(f"User '{username}' nicht gefunden")
    if users[username]["role"] == "admin" and role != "admin":
        admins = [u for u, v in users.items() if v["role"] == "admin"]
        if len(admins) <= 1:
            raise ValueError("last_admin")
    users[username]["role"] = role
    _save(users)
    logger.info("User '%s' Rolle auf '%s' geändert", username, role)


def delete(username: str) -> None:
    users = _load()
    users.pop(username, None)
    _save(users)


def list_users() -> list[dict]:
    return [
        {"username": k, "role": v["role"]}
        for k, v in _load().items()
    ]


def ensure_admin(username: str, password: str) -> bool:
    """Creates admin user if no users exist yet. Returns True if a new user was created."""
    if not _load():
        create(username, password, role="admin")
        logger.info("Admin '%s' beim ersten Start angelegt", username)
        return True
    return False
