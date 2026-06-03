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


def _matrix_file(name: str) -> str:
    """Liest eine vom tuwunel-Installer geschriebene Datei (config_dir/matrix/<name>).

    Pfad direkt aus HH_CONFIG_DIR (nicht self.config_dir) — verhindert
    cached_property-Freeze bei Test-Collection (vgl. overrides.py).
    """
    try:
        return (_config_dir() / "matrix" / name).read_text().strip()
    except OSError:
        return ""


class _TeamchatMixin:
    @property
    def teamchat_enabled(self) -> bool:
        # Explizites Flag (Env/GUI-Override) gewinnt — Admin kann an/aus erzwingen.
        explicit = env_or_override("teamchat_enabled", "HH_TEAMCHAT_ENABLED", "").strip().lower()
        if explicit:
            return explicit in ("1", "true", "yes")
        # Sonst aktiv, sobald der Homeserver konfiguriert ist (tuwunel-Extension
        # installiert → server_name + registration_token vorhanden). „Konditional
        # wie Mail/WhatsApp" — kein manuelles Flag pro Deployment nötig.
        return bool(self.matrix_server_name and self.matrix_registration_token)

    @property
    def matrix_homeserver_url(self) -> str:
        return env_or_override("matrix_homeserver_url", "HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167").strip()

    @property
    def matrix_server_name(self) -> str:
        # env/override gewinnt; sonst die vom tuwunel-Installer geschriebene Datei.
        value = env_or_override("matrix_server_name", "HH_MATRIX_SERVER_NAME", "").strip()
        return value or _matrix_file("server_name")

    @property
    def matrix_registration_token(self) -> str:
        # env/override gewinnt; sonst die vom tuwunel-Installer geschriebene Datei.
        value = env_or_override("matrix_registration_token", "HH_MATRIX_REGISTRATION_TOKEN", "").strip()
        return value or _matrix_file("registration_token")
