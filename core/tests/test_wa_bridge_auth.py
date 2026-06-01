"""WhatsApp-Adapter sendet das Bridge-Secret als Header (Issue #181).

Die Node-Bridge validiert eingehende Requests gegen HH_WA_BRIDGE_SECRET; der
Adapter muss diesen Header daher auf allen Bridge-Calls mitschicken.
"""
from __future__ import annotations

import asyncio

from hydrahive.communication.whatsapp.adapter import WhatsAppAdapter


def test_adapter_sets_bridge_secret_header():
    adapter = WhatsAppAdapter("http://127.0.0.1:8767", "TOPSECRET")
    client = asyncio.run(adapter._http())
    try:
        assert client.headers.get("X-HH-Bridge-Secret") == "TOPSECRET"
    finally:
        asyncio.run(adapter.aclose())


def test_adapter_without_secret_sends_no_header():
    adapter = WhatsAppAdapter("http://127.0.0.1:8767")
    client = asyncio.run(adapter._http())
    try:
        assert client.headers.get("X-HH-Bridge-Secret") is None
    finally:
        asyncio.run(adapter.aclose())
