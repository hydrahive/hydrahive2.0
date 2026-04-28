from __future__ import annotations

from hydrahive.api.middleware import users as users_module


class ProjectValidationError(ValueError):
    pass


_VALID_STATUS = {"active", "archived"}


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


def validate_members(members: list[str]) -> None:
    if not isinstance(members, list):
        raise ProjectValidationError("members muss eine Liste sein")
    for m in members:
        validate_member(m)
