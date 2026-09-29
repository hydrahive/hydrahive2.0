"""Token oder API-Key → aktueller Nutzer (Task a9706460).

Früher galt die Rolle, die beim Login ins JWT (24 h gültig) bzw. in den
API-Key-Eintrag geschrieben wurde. Jetzt zählt immer der Stand in users.json:

JWT:
- braucht die feste Nutzer-ID (uid). Alle JWTs seit #361 (17.07.2026) haben sie.
- der Nutzer muss existieren und noch gleich heißen (sonst: gelöscht oder
  neu angelegter Namensvetter).
- die Rolle kommt aus users.json, nicht aus dem Token.

API-Key:
- Service-Keys (Rolle ``projektx``, Föderations-Client) sind keine Nutzer.
  Sie behalten ihre Sonderrolle und sind damit nie Admin.
- Nutzer-Keys: Die Rolle im Key muss der aktuellen entsprechen. Ein Key ist
  eine ausdrückliche Vollmacht, ein Rollenwechsel macht ihn ungültig.
- Alte Keys ohne user_id werden beim ersten Einsatz an den Nutzer gebunden.

Wirft 401 (``invalid_token`` bzw. ``token_expired``) statt Zugriff zu gewähren.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import status

from hydrahive.api.middleware.errors import coded

API_KEY_PREFIX = "hhk_"
SERVICE_ROLES = frozenset({"projektx"})
USER_ROLES = frozenset({"admin", "user"})


@dataclass(frozen=True, slots=True)
class Identity:
    username: str
    role: str
    user_id: str | None      # None nur bei Service-Keys

    @property
    def is_service(self) -> bool:
        return self.user_id is None


def _invalid():
    return coded(status.HTTP_401_UNAUTHORIZED, "invalid_token")


def _current(user_id: str | None, username: str | None) -> dict:
    from hydrahive.api.middleware.users import get_by_id

    if not isinstance(user_id, str) or not user_id:
        raise _invalid()
    current = get_by_id(user_id)
    if not current or current["username"] != username:
        raise _invalid()
    return current


def _from_api_key(token: str) -> Identity:
    from hydrahive.api.middleware import api_keys
    from hydrahive.api.middleware.users import get_by_username

    key = api_keys.verify(token)
    if not key:
        raise _invalid()
    role, username = key.get("role"), key.get("username")
    if role in SERVICE_ROLES:
        # Eigener Name statt des eingetragenen Besitzers (z. B. "admin"): Sonst
        # gälte der Client bei Namens-Besitzprüfungen (Sessions …) als admin.
        return Identity(username=f"service:{role}", role=role, user_id=None)
    if role not in USER_ROLES:
        raise _invalid()
    user_id = key.get("user_id")
    if not user_id:
        user = get_by_username(username) if username else None
        if not user:
            raise _invalid()
        user_id = user["user_id"]
        api_keys.bind_legacy_keys(username, user_id)
    current = _current(user_id, username)
    if current["role"] != role:
        raise _invalid()
    return Identity(username=current["username"], role=current["role"], user_id=current["user_id"])


def resolve_credential(token: str) -> Identity:
    """Prüft JWT oder API-Key gegen den aktuellen Nutzerbestand."""
    if token.startswith(API_KEY_PREFIX):
        return _from_api_key(token)
    from hydrahive.api.middleware.auth import _decode

    payload = _decode(token)
    current = _current(payload.get("uid"), payload.get("sub"))
    return Identity(username=current["username"], role=current["role"], user_id=current["user_id"])
