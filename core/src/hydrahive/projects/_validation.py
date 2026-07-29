from __future__ import annotations

from hydrahive.api.middleware import users as users_module


class ProjectValidationError(ValueError):
    pass


_VALID_STATUS = {"active", "paused", "archived"}


def validate_name(name: str) -> None:
    if not name or not name.strip():
        raise ProjectValidationError("Projektname darf nicht leer sein")
    if len(name) > 200:
        raise ProjectValidationError("Projektname zu lang (max 200 Zeichen)")


def validate_status(status: str) -> None:
    if status not in _VALID_STATUS:
        raise ProjectValidationError(
            f"Ungültiger Status: '{status}' (erlaubt: {', '.join(_VALID_STATUS)})"
        )


def validate_member(username: str) -> None:
    if not username:
        raise ProjectValidationError("Username darf nicht leer sein")
    known = {u["username"] for u in users_module.list_users()}
    if username not in known:
        raise ProjectValidationError(f"User '{username}' existiert nicht")


_VALID_ROLES = {"read", "write", "admin"}


def validate_role(role: str) -> None:
    if role not in _VALID_ROLES:
        raise ProjectValidationError(
            f"Ungültige Rolle: '{role}' (erlaubt: {', '.join(sorted(_VALID_ROLES))})"
        )


def validate_members(members: list) -> None:
    """Akzeptiert Legacy (list[str]) und neues Format (list[{username, role}])."""
    if not isinstance(members, list):
        raise ProjectValidationError("members muss eine Liste sein")
    for m in members:
        if isinstance(m, str):
            validate_member(m)
        elif isinstance(m, dict):
            validate_member(m.get("username") or "")
            validate_role(m.get("role") or "write")
        else:
            raise ProjectValidationError("Member muss str oder {username, role} sein")
