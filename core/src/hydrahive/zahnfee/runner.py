"""Zahnfee-Runner — Datamining laden, LLM aufrufen, Briefing speichern."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from hydrahive.zahnfee import config as cfg_mod
from hydrahive.zahnfee import storage

logger = logging.getLogger(__name__)


async def _fetch_events(lookback_hours: int) -> list[dict]:
    """Holt Events der letzten X Stunden direkt aus der Datamining-DB."""
    from hydrahive.db import mirror_query, mirror as mirror_mod
    if not mirror_mod._pool:
        return []
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=lookback_hours)
    try:
        events = await mirror_query.search_events(
            q="",
            from_date=since.date().isoformat(),
            limit=500,
        )
        return events
    except Exception as e:
        logger.warning("zahnfee: events laden fehlgeschlagen: %s", e)
        return []


def _format_events(events: list[dict]) -> str:
    """Formatiert Events als kompakten Text für den LLM-Kontext."""
    if not events:
        return "Keine Aktivitäten in diesem Zeitraum."

    lines: list[str] = []
    for ev in events:
        ts = ev.get("created_at", "")[:16]
        agent = ev.get("agent_name", "?")
        etype = ev.get("event_type", "?")
        text = (ev.get("text") or ev.get("tool_name") or ev.get("tool_output") or "")[:300]
        if text:
            lines.append(f"[{ts}] {agent} ({etype}): {text}")

    return "\n".join(lines[:300])


async def run() -> storage.Briefing:
    """Hauptfunktion — generiert ein Briefing und speichert es."""
    cfg = cfg_mod.load()
    model = cfg.model or None

    logger.info("zahnfee: starte briefing-generierung (lookback=%dh)", cfg.lookback_hours)

    events: list[dict] = []
    if cfg.source_datamining:
        events = await _fetch_events(cfg.lookback_hours)

    context = _format_events(events)
    event_count = len(events)

    user_msg = (
        f"Hier sind die Aktivitäten der letzten {cfg.lookback_hours} Stunden "
        f"({event_count} Events):\n\n{context}\n\n"
        "Erstelle das Morgen-Briefing im vorgegebenen JSON-Format."
    )

    try:
        from hydrahive.llm.client import complete
        soul = cfg.soul.strip() or cfg_mod.DEFAULT_SOUL
        raw = await complete(
            messages=[
                {"role": "system", "content": soul},
                {"role": "user", "content": user_msg},
            ],
            model=model,
            temperature=0.3,
            max_tokens=2048,
        )
        # JSON aus dem Response extrahieren
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        briefing = storage.Briefing(
            generated_at=storage.now_iso(),
            date=storage.today_str(),
            open_items=parsed.get("open", ""),
            went_well=parsed.get("went_well", ""),
            went_badly=parsed.get("went_badly", ""),
            today=parsed.get("today", ""),
        )
    except Exception as e:
        logger.error("zahnfee: briefing-generierung fehlgeschlagen: %s", e)
        briefing = storage.Briefing(
            generated_at=storage.now_iso(),
            date=storage.today_str(),
            open_items="",
            went_well="",
            went_badly="",
            today="",
            error=str(e),
        )

    storage.save(briefing)
    logger.info("zahnfee: briefing gespeichert (%s)", briefing.date)
    return briefing
