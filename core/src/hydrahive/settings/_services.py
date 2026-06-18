"""Service-Konfig als Mixins: Server, JWT, AgentLink, Datamining, Communication."""
from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path

from hydrahive.settings.overrides import env_or_override


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

    @cached_property
    def update_check_enabled(self) -> bool:
        """Background-Update-Check via `git ls-remote` an das Origin-Repo.

        Default ON. Auf ``false`` setzen für strikt offline-only Betrieb —
        dann wird auch der Health-Endpoint kein ``update_behind`` mehr liefern.
        Sendet sonst keine Daten außer dem Standard-Git-Protocol-Request.
        """
        val = env_or_override("update_check_enabled", "HH_UPDATE_CHECK_ENABLED", "true").strip().lower()
        return val not in {"0", "false", "no", "off"}


class _AgentLinkMixin:
    @cached_property
    def agentlink_url(self) -> str:
        """AgentLink-REST-URL. Leer ⇒ AgentLink nicht angebunden,
        ask_agent-Tool wird nicht registriert."""
        return env_or_override("agentlink_url", "HH_AGENTLINK_URL", "").strip()

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
    def agentlink_token(self) -> str:
        """Shared-Secret für die AgentLink-Anbindung (Issue #177). Leer ⇒ kein
        Header. Wenn gesetzt: als ``Authorization: Bearer`` auf allen REST-Calls
        und beim WS-Subscribe mitgeschickt, damit nur autorisierte Clients mit
        dem AgentLink-Service sprechen. Die harte Inbound-Garantie (kein Master-
        Fallback) liegt in handoff_receiver — der Token ist Transport-Hygiene."""
        return env_or_override("agentlink_token", "HH_AGENTLINK_TOKEN", "").strip()

    @cached_property
    def agentlink_handoff_timeout(self) -> int:
        """Wie lange ein ask_agent-Aufruf max. auf eine Antwort wartet (Sekunden)."""
        return int(os.environ.get("HH_AGENTLINK_HANDOFF_TIMEOUT", "600"))

    @cached_property
    def agentlink_run_timeout(self) -> int:
        """Max. Laufzeit eines eingehenden Handoff-Runs (Sekunden), bevor der
        handoff_receiver mit einer Fehler-Antwort abbricht statt still zu hängen.
        Bewusst < agentlink_handoff_timeout, damit der Auftraggeber eine klare
        Fehler-Antwort bekommt, bevor sein eigenes Caller-Timeout zuschlägt."""
        return int(os.environ.get("HH_AGENTLINK_RUN_TIMEOUT", "540"))

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
        return env_or_override("discord_enabled", "HH_DISCORD_ENABLED", "1").lower() in ("1", "true", "yes")

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

    @cached_property
    def health_api_key(self) -> str:
        """API-Key für Health Auto Export Ingest. Leer ⇒ Endpoint antwortet mit 403."""
        return env_or_override("health_api_key", "HH_HEALTH_API_KEY", "").strip()

    @cached_property
    def health_ingest_user(self) -> str:
        """User-ID unter der eingehende Health-Daten abgelegt werden.
        Der Health-Key bindet an genau diesen einen User (Single-Device-Ingest).
        Default 'till'."""
        return os.environ.get("HH_HEALTH_INGEST_USER", "till").strip() or "till"
