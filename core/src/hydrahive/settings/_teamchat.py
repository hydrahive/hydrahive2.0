"""Teamchat-Settings (Matrix / Element-Homeserver).

Bewusst `@property` (nicht `cached_property`): GUI-Overrides müssen live greifen,
ohne Dienst-Neustart — identisches Muster wie `_mail.py`.
"""
from __future__ import annotations

from hydrahive.settings.overrides import env_or_override


class _TeamchatMixin:
    @property
    def teamchat_enabled(self) -> bool:
        return env_or_override("teamchat_enabled", "HH_TEAMCHAT_ENABLED", "0").lower() in ("1", "true", "yes")

    @property
    def matrix_homeserver_url(self) -> str:
        return env_or_override("matrix_homeserver_url", "HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167").strip()

    @property
    def matrix_server_name(self) -> str:
        return env_or_override("matrix_server_name", "HH_MATRIX_SERVER_NAME", "").strip()

    @property
    def matrix_registration_token(self) -> str:
        return env_or_override("matrix_registration_token", "HH_MATRIX_REGISTRATION_TOKEN", "").strip()
