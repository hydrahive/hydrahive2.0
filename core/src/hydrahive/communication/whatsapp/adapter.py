"""WhatsApp-Channel-Adapter — spricht mit der Baileys-Bridge per HTTP."""
from __future__ import annotations

import logging

import httpx

from hydrahive.communication.base import ChannelStatus

logger = logging.getLogger(__name__)


class WhatsAppAdapter:
    name = "whatsapp"
    label = "WhatsApp"

    def __init__(self, bridge_url: str):
        self._base = bridge_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def status(self, username: str) -> ChannelStatus:
        try:
            r = await (await self._http()).get(f"{self._base}/status/{username}")
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as e:
            return ChannelStatus(
                connected=False,
                state="error",
                detail=f"Bridge nicht erreichbar: {e}",
            )
        phone = data.get("phone")
        return ChannelStatus(
            connected=data.get("connected", False),
            state=data.get("state", "disconnected"),
            detail=f"+{phone}" if phone else None,
            qr_data_url=data.get("qr_data_url"),
        )

    async def connect(self, username: str) -> ChannelStatus:
        r = await (await self._http()).post(f"{self._base}/connect/{username}")
        r.raise_for_status()
        return await self.status(username)

    async def disconnect(self, username: str) -> None:
        await (await self._http()).post(f"{self._base}/disconnect/{username}")

    async def send(self, username: str, to: str, text: str) -> None:
        r = await (await self._http()).post(
            f"{self._base}/send/{username}",
            json={"to": to, "text": text},
        )
        r.raise_for_status()

    async def send_audio(self, username: str, to: str, audio_b64: str) -> None:
        """Sendet Sprachnachricht (ptt) — audio als base64 OGG/Opus."""
        r = await (await self._http()).post(
            f"{self._base}/send/{username}",
            json={"to": to, "audio_base64": audio_b64},
        )
        r.raise_for_status()

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
