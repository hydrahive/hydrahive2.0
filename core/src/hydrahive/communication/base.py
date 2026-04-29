"""Channel-Interface für Kommunikationswege (WhatsApp, Telegram, Mail, ...).

Jeder konkrete Channel-Adapter implementiert dieses Protocol und meldet sich
beim Backend-Start in der Registry an. Die Foundation legt fest *was* ein
Channel können muss — Implementierung leben in `communication/<channel>/`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------- IncomingEvent

@dataclass
class IncomingEvent:
    """Eine eingehende Nachricht aus einem Kommunikationskanal."""
    channel: str                     # z.B. "whatsapp"
    external_user_id: str            # z.B. "4915123456789@c.us"
    target_username: str             # HydraHive-User dem das Konto gehört
    text: str
    sender_name: str | None = None   # Display-Name aus dem Channel
    media_type: str | None = None    # z.B. "audio/ogg" für Sprachnachrichten
    media_data: str | None = None    # base64 wenn Audio etc.
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------- ChannelStatus

@dataclass
class ChannelStatus:
    """Zustand eines Channels für einen User. UI rendert das."""
    connected: bool
    state: str                       # "disconnected" | "waiting_qr" | "connecting" | "connected" | "error"
    detail: str | None = None        # menschlich, z.B. "Telefon: +49…" oder Fehlertext
    qr_data_url: str | None = None   # QR als data: URL falls auf Login wartet
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------- Channel-Protocol

@runtime_checkable
class Channel(Protocol):
    """Was ein Channel-Adapter implementieren muss."""

    name: str  # z.B. "whatsapp"
    label: str  # menschlich, z.B. "WhatsApp"

    async def status(self, username: str) -> ChannelStatus: ...
    async def connect(self, username: str) -> ChannelStatus: ...
    async def disconnect(self, username: str) -> None: ...
    async def send(self, username: str, to: str, text: str) -> None: ...
