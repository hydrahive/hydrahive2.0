from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path


class Settings:
    """Single source of truth for all paths and runtime config.

    Values come from environment variables with sensible defaults.
    Never hardcode paths anywhere else — always import settings.
    """

    # ------------------------------------------------------------------ paths

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

    # ------------------------------------------------------------------ server

    @cached_property
    def host(self) -> str:
        return os.environ.get("HH_HOST", "127.0.0.1")

    @cached_property
    def port(self) -> int:
        return int(os.environ.get("HH_PORT", "8765"))

    @cached_property
    def secret_key(self) -> str:
        key = os.environ.get("HH_SECRET_KEY", "")
        if not key:
            raise RuntimeError("HH_SECRET_KEY is not set")
        return key

    @cached_property
    def jwt_algorithm(self) -> str:
        return "HS256"

    @cached_property
    def jwt_expire_minutes(self) -> int:
        return int(os.environ.get("HH_JWT_EXPIRE_MINUTES", "1440"))

    # ------------------------------------------------------------------ agentlink

    @cached_property
    def agentlink_url(self) -> str:
        return os.environ.get("HH_AGENTLINK_URL", "http://127.0.0.1:7700")

    # ------------------------------------------------------------------ communication

    @cached_property
    def backend_internal_url(self) -> str:
        return os.environ.get("HH_INTERNAL_URL", f"http://127.0.0.1:{self.port}")

    @cached_property
    def whatsapp_enabled(self) -> bool:
        return os.environ.get("HH_WA_ENABLED", "1").lower() in ("1", "true", "yes")

    @cached_property
    def whatsapp_data_dir(self) -> Path:
        return self.data_dir / "whatsapp"

    # ------------------------------------------------------------------ vms

    @cached_property
    def vms_dir(self) -> Path:
        return self.data_dir / "vms"

    @cached_property
    def vms_isos_dir(self) -> Path:
        return self.vms_dir / "isos"

    @cached_property
    def vms_disks_dir(self) -> Path:
        return self.vms_dir / "disks"

    @cached_property
    def vms_pids_dir(self) -> Path:
        return self.vms_dir / "pids"

    @cached_property
    def vms_logs_dir(self) -> Path:
        return self.vms_dir / "logs"

    @cached_property
    def vms_vnc_tokens_dir(self) -> Path:
        return self.vms_dir / "vnc-tokens"

    @cached_property
    def vms_bridge(self) -> str:
        return os.environ.get("HH_VMS_BRIDGE", "br0")

    # ------------------------------------------------------------------ butler

    @cached_property
    def butler_dir(self) -> Path:
        return self.config_dir / "butler"

    @cached_property
    def butler_secrets_file(self) -> Path:
        return self.config_dir / "butler_hook_secrets.json"

    @cached_property
    def whatsapp_bridge_port(self) -> int:
        return int(os.environ.get("HH_WA_BRIDGE_PORT", "8767"))

    @cached_property
    def whatsapp_bridge_url(self) -> str:
        return f"http://127.0.0.1:{self.whatsapp_bridge_port}"

    @cached_property
    def whatsapp_bridge_secret_file(self) -> Path:
        return self.config_dir / "whatsapp_bridge.secret"

    # ------------------------------------------------------------------ helpers

    def ensure_dirs(self) -> None:
        """Create all required data directories if they don't exist."""
        for d in (self.data_dir, self.agents_dir, self.projects_dir,
                  self.plugins_dir, self.config_dir):
            d.mkdir(parents=True, exist_ok=True)


# Module-level singleton — import this everywhere
settings = Settings()
