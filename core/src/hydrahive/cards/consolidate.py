"""Card-Writer (L2): verdichtet eine Mirror-Session zu einer getaggten Gist-Card.

Quelle = Datamining-Mirror (`get_session_detail`). `crystallize_session` wird
NICHT als Einstieg genutzt (agent-lokal → None für externe/importierte Sessions),
nur das Prompt-Muster ist wiederverwendet. Groundedness via `event_type_counts`
(Task 2). Kein Contradiction-Reasoning / Verify-Gate (= v2).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from hydrahive.db._mirror_cards import upsert_card
from hydrahive.db._mirror_cards_model import Card, derive_groundedness
from hydrahive.db._mirror_sessions import (
    event_type_counts,
    get_session_detail,
    list_sessions,
)

logger = logging.getLogger(__name__)


def _is_claude(model: str) -> bool:
    from hydrahive.llm import client as llm_client
    return llm_client._strip_provider_prefix(model or "").startswith("claude-")


async def _llm_tags(events: list[dict], model: str) -> dict:
    """Ein LLM-Call → geparste Card-Tags. Claude: Assistant-Prefill '{' erzwingt
    JSON-Output (verhindert Prosa/Fortführen, Mode 1+3). Bei Exception: leere Tags."""
    from hydrahive.cards._consolidate_prompts import (
        CARD_SYSTEM,
        card_user_message,
        parse_card_response,
    )
    from hydrahive.runner.llm_bridge import call_with_tools

    messages: list[dict] = [{"role": "user", "content": card_user_message(events)}]
    prefill = _is_claude(model)
    if prefill:
        messages.append({"role": "assistant", "content": "{"})
    try:
        blocks, _, _ = await call_with_tools(
            model=model, system_prompt=CARD_SYSTEM, messages=messages,
            tools=[], temperature=0.0, max_tokens=512,
        )
    except Exception as e:
        logger.warning("consolidate: LLM-Fehler %s — leere Tags", e)
        return {"gist": "", "valence": "neutral", "salience": "low", "topics": []}
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    if prefill:
        text = "{" + text
    return parse_card_response(text)


async def consolidate_session(session_id: str, model: str) -> Card | None:
    """Eine Mirror-Session → eine Card (idempotent via upsert_card). None, wenn
    Session fehlt ODER nach Retry kein Gist erzeugbar (retry-fähig, nicht lautlos
    leer speichern)."""
    detail = await get_session_detail(session_id)
    if not detail:
        return None
    meta = detail.get("session") or {}
    events = detail.get("events") or []

    tags = await _llm_tags(events, model)
    if not tags["gist"]:
        tags = await _llm_tags(events, model)  # ein Retry gegen Varianz
    if not tags["gist"]:
        logger.warning(
            "consolidate_session %s: kein Gist nach Retry — Card NICHT gespeichert (retry-fähig)",
            session_id,
        )
        return None

    counts = await event_type_counts(session_id)
    groundedness = derive_groundedness(
        counts.get("tool_result", 0), counts.get("assistant_text", 0)
    )

    embedding = None
    from hydrahive.llm._config import load_config
    from hydrahive.llm.embed import aembed
    embed_model = load_config().get("embed_model", "")
    if embed_model:
        try:
            embedding = await aembed(tags["gist"], embed_model, embed_type="db")
        except Exception as e:
            logger.warning("consolidate_session %s: Embedding-Fehler %s", session_id, e)

    created_at = meta.get("started_at")
    card = Card(
        card_id=f"card:{session_id}",
        session_id=session_id,
        gist=tags["gist"],
        valence=tags["valence"],
        salience=tags["salience"],
        groundedness=groundedness,
        topics=tags["topics"],
        agent_id=meta.get("agent_id"),
        agent_name=meta.get("agent_name"),
        username=meta.get("username"),
        created_at=str(created_at) if created_at is not None else None,
        source={"session_id": session_id, "event_count": len(events)},
        consolidation_model=model,
    )
    await upsert_card(card, embedding)
    logger.info(
        "consolidate_session %s: Card (valence=%s salience=%s grounded=%s, %d events)",
        session_id, card.valence, card.salience, card.groundedness, len(events),
    )
    return card


async def consolidate_recent(lookback_hours: int, model: str, limit: int = 200) -> int:
    """Batch: alle Mirror-Sessions im Zeitfenster → Cards. Gibt Anzahl Cards zurück."""
    from_date = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()
    sessions = await list_sessions(from_date=from_date, limit=limit)
    n = 0
    for s in sessions:
        sid = s.get("id")
        if not sid:
            continue
        try:
            if await consolidate_session(sid, model):
                n += 1
        except Exception as e:
            logger.warning("consolidate_recent: Session %s fehlgeschlagen: %s", sid, e)
    logger.info(
        "consolidate_recent: %d Cards aus %d Sessions (lookback %dh)",
        n, len(sessions), lookback_hours,
    )
    return n
