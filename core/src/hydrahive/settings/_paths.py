"""Pfad- und File-Properties als Mixin der Settings-Klasse.

Alle Verzeichnisse + Konfig-Files + Logs landen hier. Werte werden via
HH_*-Env-Vars überschrieben, sonst Defaults aus /var/lib + /etc + /var/log.
"""
from __future__ import annotations

import os
import tempfile
from functools import cached_property
from pathlib import Path


class _PathsMixin:
    @cached_property
    def base_dir(self) -> Path:
        return Path(os.environ.get("HH_BASE_DIR", "/opt/hydrahive2"))

    @cached_property
    def data_dir(self) -> Path:
        return Path(os.environ.get("HH_DATA_DIR", "/var/lib/hydrahive2"))

    @cached_property
    def config_dir(self) -> Path:
        return Path(os.environ.get("HH_CONFIG_DIR", "/etc/hydrahive2"))

    @cached_property
    def agents_dir(self) -> Path:
        return self.data_dir / "agents"

    @cached_property
    def projects_dir(self) -> Path:
        return self.data_dir / "projects"

    @cached_property
    def plugins_dir(self) -> Path:
        return self.data_dir / "plugins"

    @cached_property
    def plugin_hub_cache(self) -> Path:
        return self.data_dir / ".plugin-cache" / "hub"

    @cached_property
    def plugin_hub_git_url(self) -> str:
        return os.environ.get(
            "HH_PLUGIN_HUB_GIT_URL",
            "https://github.com/hydrahive/hydrahive2-plugins.git",
        )

    @cached_property
    def tmp_dir(self) -> Path:
        return Path(os.environ.get("HH_TMP_DIR", tempfile.gettempdir()))

    @cached_property
    def media_dirs(self) -> list[Path]:
        """Zusätzliche Verzeichnisse die über /api/files ausgeliefert werden dürfen.

        HH_MEDIA_DIRS: Doppelpunkt-getrennte Liste absoluter Pfade.
        Beispiel: HH_MEDIA_DIRS=/home/till/security bücherei:/mnt/ebooks
        """
        raw = os.environ.get("HH_MEDIA_DIRS", "")
        return [Path(p) for p in raw.split(":") if p.strip()]

    @cached_property
    def oauth_pending_path(self) -> Path:
        return self.data_dir / "oauth_pending.json"

    @cached_property
    def numba_cache_dir(self) -> Path:
        return Path(os.environ.get("HH_NUMBA_CACHE", str(self.data_dir / ".numba-cache")))

    @property
    def servable_prefixes(self) -> tuple[str, ...]:
        return (str(self.tmp_dir) + "/", str(self.data_dir) + "/")

    # ------------------------------------------------------------------ DBs/Configs

    @cached_property
    def sessions_db(self) -> Path:
        return self.data_dir / "sessions.db"

    @cached_property
    def mcp_config(self) -> Path:
        return self.config_dir / "mcp_servers.json"

    @cached_property
    def llm_config(self) -> Path:
        return self.config_dir / "llm.json"

    @cached_property
    def users_config(self) -> Path:
        return self.config_dir / "users.json"

    @cached_property
    def api_keys_config(self) -> Path:
        return self.config_dir / "api_keys.json"

    @cached_property
    def research_apis_config(self) -> Path:
        return self.config_dir / "research_apis.json"

    @cached_property
    def voice_conversations_path(self) -> Path:
        return self.data_dir / "voice_conversations.json"

    # ------------------------------------------------------------------ logs

    @cached_property
    def log_dir(self) -> Path:
        return Path(os.environ.get("HH_LOG_DIR", "/var/log"))

    @cached_property
    def update_log(self) -> Path:
        return self.log_dir / "hydrahive2-update.log"

    @cached_property
    def voice_log(self) -> Path:
        return self.log_dir / "hydrahive2-voice.log"

    @cached_property
    def samba_log_path(self) -> Path:
        return Path(os.environ.get("HH_SAMBA_LOG", "/var/log/hydrahive2-samba.log"))

    @cached_property
    def bridge_log_path(self) -> Path:
        return Path(os.environ.get("HH_BRIDGE_LOG", "/var/log/hydrahive2-bridge.log"))

    # ------------------------------------------------------------------ helpers

    def ensure_dirs(self) -> None:
        """Create all required data directories if they don't exist."""
        for d in (self.data_dir, self.agents_dir, self.projects_dir,
                  self.plugins_dir, self.config_dir):
            d.mkdir(parents=True, exist_ok=True)
