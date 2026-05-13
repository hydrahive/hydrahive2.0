"""HydraHive ConversationEntity — sendet Text an /api/voice/chat."""
from __future__ import annotations

import logging
import uuid
from typing import Literal

import aiohttp
from homeassistant.components.conversation import ConversationEntity
from homeassistant.components.conversation.models import ConversationInput, ConversationResult
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.intent import IntentResponse

from .const import CONF_AGENT_ID, CONF_AGENT_NAME, CONF_API_KEY, CONF_ENDPOINT, CONF_VERIFY_SSL

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([HydraHiveConversationEntity(entry)])


class HydraHiveConversationEntity(ConversationEntity):
    _attr_has_entity_name = True
    _attr_supported_languages: list[str] | Literal["*"] = "*"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_name = entry.data[CONF_AGENT_NAME]
        self._attr_unique_id = f"hydrahive_{entry.data[CONF_AGENT_ID]}"

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        conversation_id = user_input.conversation_id or str(uuid.uuid4())
        reply = await self._call_hh(
            text=user_input.text,
            conversation_id=conversation_id,
            language=user_input.language,
        )
        intent_response = IntentResponse(language=user_input.language)
        intent_response.async_set_speech(reply)
        return ConversationResult(response=intent_response, conversation_id=conversation_id)

    async def _call_hh(self, *, text: str, conversation_id: str, language: str) -> str:
        data = self._entry.data
        verify_ssl = data.get(CONF_VERIFY_SSL, True)
        session = async_get_clientsession(self.hass, verify_ssl=verify_ssl)
        try:
            async with session.post(
                f"{data[CONF_ENDPOINT]}/api/voice/chat",
                headers={"Authorization": f"Bearer {data[CONF_API_KEY]}"},
                json={
                    "text": text,
                    "conversation_id": conversation_id,
                    "agent_id": data[CONF_AGENT_ID],
                    "language": language,
                },
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                resp.raise_for_status()
                body = await resp.json()
                return body.get("reply") or "(Kein Text-Output vom Agent.)"
        except aiohttp.ClientError as exc:
            _LOGGER.error("HydraHive-Anfrage fehlgeschlagen: %s", exc)
            return "Entschuldigung, ich konnte HydraHive nicht erreichen."
        except Exception as exc:
            _LOGGER.error("Unerwarteter Fehler beim HydraHive-Aufruf: %s", exc)
            return "Entschuldigung, ein unerwarteter Fehler ist aufgetreten."
