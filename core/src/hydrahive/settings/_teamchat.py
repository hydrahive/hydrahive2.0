"""Teamchat-Settings (Matrix / Element-Homeserver).

Bewusst `@property` (nicht `cached_property`): GUI-Overrides müssen live greifen,
ohne Dienst-Neustart — identisches Muster wie `_mail.py`.
"""
from __future__ import annotations

import os
from pathlib import Path

from hydrahive.settings.overrides import env_or_override

# Direkt aus Env lesen — NICHT über self.config_dir (cached_property würde zur
# Import-Zeit einfrieren und Test-Envs vergiften; identisches Muster wie overrides.py).
_CONFIG_DIR_DEFAULT = "/etc/hydrahive2"


def _config_dir() -> Path:
    return Path(os.environ.get("HH_CONFIG_DIR", _CONFIG_DIR_DEFAULT))


class _TeamchatMixin:
    @property
    def teamchat_enabled(self) -> bool:
        return env_or_override("teamchat_enabled", "HH_TEAMCHAT_ENABLED", "0").lower() in ("1", "true", "yes")

    @property
    def matrix_homeserver_url(self) -> str:
        return env_or_override("matrix_homeserver_url", "HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167").strip()

    @property
    def matrix_server_name(self) -> str:
        value = env_or_override("matrix_server_name", "HH_MATRIX_SERVER_NAME", "").strip()
        if value:
            return value
        # Fallback: tuwunel Extension schreibt den gewählten Namen in diese Datei.
        # Pfad direkt aus HH_CONFIG_DIR (nicht self.config_dir) — verhindert
        # cached_property-Freeze bei Test-Collection (vgl. overrides.py).
        sn_file = _config_dir() / "matrix" / "server_name"
        try:
            return sn_file.read_text().strip()
        except OSError:
            return ""

    @property
    def matrix_registration_token(self) -> str:
        return env_or_override("matrix_registration_token", "HH_MATRIX_REGISTRATION_TOKEN", "").strip()
