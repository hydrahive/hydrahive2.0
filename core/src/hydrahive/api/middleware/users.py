from __future__ import annotations

import fcntl
import hashlib
import json
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from uuid import NAMESPACE_URL, uuid4, uuid5

import bcrypt

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

# User-Struktur:
# {"username": {"user_id": "uuid", "password_hash": "...", "role": "admin|user"}}
# password_hash kann bcrypt ($2b$...) oder Legacy-SHA256 (64 hex chars) sein.
# Fehlende user_id und Legacy-Hashes werden transparent migriert.


def _read_unlocked() -> dict:
    path: Path = settings.users_config
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _save_unlocked(users: dict) -> None:
    """Atomic write while the caller holds the cross-process users lock."""
    settings.users_config.parent.mkdir(parents=True, exist_ok=True)
    tmp = settings.users_config.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(users, indent=2))
    tmp.replace(settings.users_config)


def _migrate_user_ids(users: dict) -> bool:
    changed = False
    for username, user in users.items():
        if not user.get("user_id"):
            # Deterministic only for one-time legacy migration: parallel workers
            # must not mint competing IDs for the same pre-migration record.
            legacy_key = f"hydrahive-user:{username}:{user.get('password_hash', '')}"
            user["user_id"] = str(uuid5(NAMESPACE_URL, legacy_key))
            changed = True
    return changed


@contextmanager
def _locked_users() -> Iterator[dict]:
    """Serialize reads that may migrate and every users.json mutation."""
    path: Path = settings.users_config
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        users = _read_unlocked()
        migrated = _migrate_user_ids(users)
        before = json.dumps(users, sort_keys=True)
        try:
            yield users
        except Exception:
            raise
        else:
            if migrated or json.dumps(users, sort_keys=True) != before:
                _save_unlocked(users)
                if migrated:
                    logger.info("Bestehende Benutzer um stabile user_id ergänzt")
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _load() -> dict:
    with _locked_users() as users:
        return users


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
    """Returns public user data or None and lazily migrates legacy hashes."""
    with _locked_users() as users:
        user = users.get(username)
        if not user:
            return None
        stored = user["password_hash"]
        if not _verify_hash(password, stored):
            return None
        if not _is_bcrypt(stored):
            user["password_hash"] = _hash(password)
            logger.info("User '%s' Hash auf bcrypt migriert", username)
        return {"user_id": user["user_id"], "username": username, "role": user["role"]}


def create(username: str, password: str, role: str = "user") -> str:
    """Creates a new user and returns its immutable ID.

    Raises ValueError if the username already exists.
    """
    user_id = str(uuid4())
    password_hash = _hash(password)
    with _locked_users() as users:
        if username in users:
            raise ValueError(f"User '{username}' existiert bereits")
        users[username] = {
            "user_id": user_id,
            "password_hash": password_hash,
            "role": role,
        }
    logger.info("User '%s' angelegt (role=%s, user_id=%s)", username, role, user_id)
    return user_id


def update_password(username: str, new_password: str) -> None:
    password_hash = _hash(new_password)
    with _locked_users() as users:
        if username not in users:
            raise ValueError(f"User '{username}' nicht gefunden")
        users[username]["password_hash"] = password_hash


def update_role(username: str, role: str) -> None:
    if role not in ("admin", "user"):
        raise ValueError(f"Ungültige Rolle: {role}")
    with _locked_users() as users:
        if username not in users:
            raise ValueError(f"User '{username}' nicht gefunden")
        if users[username]["role"] == "admin" and role != "admin":
            admins = [u for u, value in users.items() if value["role"] == "admin"]
            if len(admins) <= 1:
                raise ValueError("last_admin")
        users[username]["role"] = role
    logger.info("User '%s' Rolle auf '%s' geändert", username, role)


def delete(username: str) -> None:
    with _locked_users() as users:
        users.pop(username, None)


def get_by_username(username: str) -> dict | None:
    """Returns one public user record without exposing the user list."""
    with _locked_users() as users:
        user = users.get(username)
        if not user:
            return None
        return {"user_id": user["user_id"], "username": username, "role": user["role"]}


def get_by_id(user_id: str) -> dict | None:
    """Returns one public user record for an immutable ID."""
    with _locked_users() as users:
        for username, user in users.items():
            if user["user_id"] == user_id:
                return {"user_id": user_id, "username": username, "role": user["role"]}
    return None


def list_users() -> list[dict]:
    with _locked_users() as users:
        return [
            {"user_id": value["user_id"], "username": username, "role": value["role"]}
            for username, value in users.items()
        ]


def ensure_admin(username: str, password: str) -> bool:
    """Creates admin user if no users exist yet. Returns whether it was created."""
    user_id = str(uuid4())
    password_hash = _hash(password)
    with _locked_users() as users:
        if users:
            return False
        users[username] = {
            "user_id": user_id,
            "password_hash": password_hash,
            "role": "admin",
        }
    logger.info("Admin '%s' beim ersten Start angelegt", username)
    return True
