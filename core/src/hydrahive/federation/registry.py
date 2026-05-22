"""A2A-Card-Fetch und Remote-Chat für Federation-Workstations."""
from __future__ import annotations

import asyncio
import json
import logging
import time

import httpx

from hydrahive.db import federation as fed_db

logger = logging.getLogger(__name__)

# In-memory card cache: ws_id → (card_dict, fetched_at)
_card_cache: dict[str, tuple[dict, float]] = {}
_CACHE_TTL = 60.0  # seconds


async def fetch_card(ws_id: str, force: bool = False) -> dict | None:
    """Fetch A2A card from /.well-known/agent.json. Caches 60s."""
    ws = fed_db.get_workstation(ws_id)
    if not ws:
        return None

    if not force:
        cached = _card_cache.get(ws_id)
        if cached and (time.monotonic() - cached[1]) < _CACHE_TTL:
            return cached[0]

    url = f"{ws['url']}/.well-known/agent.json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            card = resp.json()
    except Exception as e:
        logger.warning("A2A card fetch fehlgeschlagen für %s: %s", ws["name"], e)
        return None

    card_json = json.dumps(card)
    fed_db.update_card(ws_id, card_json)
    _card_cache[ws_id] = (card, time.monotonic())
    return card


async def remote_chat(ws_id: str, input_text: str, persona_id: str = "", system: str = "") -> str:
    """POST /remote/chat an eine Workstation. Gibt den Antwort-Text zurück."""
    ws = fed_db.get_workstation(ws_id)
    if not ws:
        raise ValueError(f"Workstation '{ws_id}' nicht gefunden")
    if not ws.get("token"):
        raise ValueError(f"Kein Token für Workstation '{ws['name']}' — kann nicht verbinden")

    url = f"{ws['url']}/remote/chat"
    payload: dict = {"input": input_text}
    if persona_id:
        payload["persona_id"] = persona_id
    if system:
        payload["system"] = system

    headers = {
        "Authorization": f"Bearer {ws['token']}",
        "X-Caller": "hydrahive2",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return data.get("text") or ""


async def refresh_all_cards() -> None:
    """Alle aktivierten Workstations im Hintergrund aktualisieren."""
    workstations = fed_db.list_workstations()
    tasks = [
        fetch_card(ws["id"], force=True)
        for ws in workstations
        if ws.get("enabled")
    ]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
