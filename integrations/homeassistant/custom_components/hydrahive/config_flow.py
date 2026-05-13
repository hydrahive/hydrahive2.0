"""Config Flow für HydraHive Conversation Agent."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_AGENT_ID, CONF_AGENT_NAME, CONF_API_KEY, CONF_ENDPOINT, CONF_VERIFY_SSL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENDPOINT): str,
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
)


class HydraHiveConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow — Schritt 1: Endpoint+Key, Schritt 2: Agent-Auswahl."""

    VERSION = 1

    def __init__(self) -> None:
        self._endpoint: str = ""
        self._api_key: str = ""
        self._verify_ssl: bool = True
        self._agents: list[dict] = []

    async def _fetch_agents(self) -> list[dict] | None:
        """GET /api/agents — None bei Auth-Fehler, [] bei Verbindungsfehler."""
        try:
            session = async_get_clientsession(self.hass, verify_ssl=self._verify_ssl)
            async with session.get(
                f"{self._endpoint}/api/agents",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 401:
                    return None
                resp.raise_for_status()
                return await resp.json()
        except Exception as exc:
            _LOGGER.debug("Verbindungsfehler beim Abrufen der Agents: %s", exc)
            return []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._endpoint = user_input[CONF_ENDPOINT].rstrip("/")
            self._api_key = user_input[CONF_API_KEY].strip()
            self._verify_ssl = user_input.get(CONF_VERIFY_SSL, True)

            agents = await self._fetch_agents()
            if agents is None:
                errors["base"] = "invalid_auth"
            elif not agents:
                errors["base"] = "cannot_connect"
            else:
                self._agents = agents
                return await self.async_step_agent()

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)

    async def async_step_agent(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        if user_input is not None:
            agent_id = user_input[CONF_AGENT_ID]
            agent = next((a for a in self._agents if a["id"] == agent_id), None)
            agent_name = agent["name"] if agent else agent_id

            await self.async_set_unique_id(f"{self._endpoint}_{agent_id}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"HydraHive — {agent_name}",
                data={
                    CONF_ENDPOINT: self._endpoint,
                    CONF_API_KEY: self._api_key,
                    CONF_VERIFY_SSL: self._verify_ssl,
                    CONF_AGENT_ID: agent_id,
                    CONF_AGENT_NAME: agent_name,
                },
            )

        options = {a["id"]: a["name"] for a in self._agents}
        return self.async_show_form(
            step_id="agent",
            data_schema=vol.Schema({vol.Required(CONF_AGENT_ID): vol.In(options)}),
        )
