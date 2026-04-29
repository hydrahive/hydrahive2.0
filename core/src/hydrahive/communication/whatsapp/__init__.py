"""WhatsApp-Channel — Baileys-Bridge + Python-Adapter."""
from hydrahive.communication.whatsapp.adapter import WhatsAppAdapter
from hydrahive.communication.whatsapp.process import (
    BRIDGE_DIR,
    BridgeProcess,
    ensure_secret,
)

__all__ = ["WhatsAppAdapter", "BridgeProcess", "BRIDGE_DIR", "ensure_secret"]
