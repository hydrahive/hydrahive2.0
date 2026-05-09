"""Service-Konfig als Mixins: Server, JWT, AgentLink, Datamining, Communication."""
from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path


class _ServerMixin:
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


class _AgentLinkMixin:
    @cached_property
    def agentlink_url(self) -> str:
        """AgentLink-REST-URL. Leer ⇒ AgentLink nicht angebunden,
        ask_agent-Tool wird nicht registriert."""
        return os.environ.get("HH_AGENTLINK_URL", "").strip()

    @cached_property
    def agentlink_ws_url(self) -> str:
        """AgentLink-WebSocket-URL. Wenn leer aber agentlink_url gesetzt:
        wird automatisch aus REST-URL abgeleitet (http→ws, https→wss + /ws)."""
        explicit = os.environ.get("HH_AGENTLINK_WS_URL", "").strip()
        if explicit:
            return explicit
        rest = self.agentlink_url
        if not rest:
            return ""
        ws = rest.replace("http://", "ws://").replace("https://", "wss://")
        return ws.rstrip("/") + "/ws"

    @cached_property
    def agentlink_agent_id(self) -> str:
        """Eindeutige Agent-ID dieser HydraHive-Instanz im AgentLink-Netz.
        Default: 'hydrahive'. Bei mehreren Instanzen pro User unterscheidbar setzen."""
        return os.environ.get("HH_AGENTLINK_AGENT_ID", "hydrahive").strip()

    @cached_property
    def agentlink_handoff_timeout(self) -> int:
        """Wie lange ein ask_agent-Aufruf max. auf eine Antwort wartet (Sekunden)."""
        return int(os.environ.get("HH_AGENTLINK_HANDOFF_TIMEOUT", "600"))

    @cached_property
    def agentlink_dashboard_url(self) -> str:
        """URL des AgentLink-Frontends (separates statisches SPA, default 9001)."""
        return os.environ.get("HH_AGENTLINK_DASHBOARD_URL", "").strip()


class _CommunicationMixin:
    @cached_property
    def pg_mirror_dsn(self) -> str:
        return os.environ.get("HH_PG_MIRROR_DSN", "").strip()

    @cached_property
    def backend_internal_url(self) -> str:
        return os.environ.get("HH_INTERNAL_URL", f"http://127.0.0.1:{self.port}")

    @cached_property
    def discord_enabled(self) -> bool:
        return os.environ.get("HH_DISCORD_ENABLED", "1").lower() in ("1", "true", "yes")

    @cached_property
    def discord_config_dir(self) -> Path:
        return self.config_dir / "discord"

    @cached_property
    def whatsapp_enabled(self) -> bool:
        return os.environ.get("HH_WA_ENABLED", "1").lower() in ("1", "true", "yes")

    @cached_property
    def whatsapp_data_dir(self) -> Path:
        return self.data_dir / "whatsapp"

    @cached_property
    def whatsapp_bridge_port(self) -> int:
        return int(os.environ.get("HH_WA_BRIDGE_PORT", "8767"))

    @cached_property
    def whatsapp_bridge_url(self) -> str:
        return f"http://127.0.0.1:{self.whatsapp_bridge_port}"

    @cached_property
    def whatsapp_bridge_secret_file(self) -> Path:
        return self.config_dir / "whatsapp_bridge.secret"
