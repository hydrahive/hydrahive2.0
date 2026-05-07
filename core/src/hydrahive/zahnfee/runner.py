"""Zahnfee-Runner — Datamining laden, LLM aufrufen, Briefing speichern."""
from __future__ import annotations

import json
import logging
import re
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


def _extract_json(raw: str) -> dict:
    """Versucht JSON aus der LLM-Antwort zu extrahieren — auch wenn Markdown drumherum ist."""
    raw = raw.strip()

    # 1. Direkt als JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. JSON-Block in ```...``` oder ```json...```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Erstes {...} das alle vier Keys enthält
    m = re.search(r"\{[^{}]*\"open\"[^{}]*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    # 4. Fallback: Markdown-Abschnitte parsen (## Offen, ## Gut, ...)
    sections: dict[str, str] = {}
    mapping = {
        "offen": "open", "open": "open",
        "gut gelaufen": "went_well", "went_well": "went_well", "gut": "went_well",
        "schlecht gelaufen": "went_badly", "went_badly": "went_badly", "schlecht": "went_badly",
        "heute": "today", "today": "today", "heute relevant": "today",
    }
    current_key: str | None = None
    buf: list[str] = []
    for line in raw.splitlines():
        header = re.match(r"^#{1,3}\s+(.+)", line)
        if header:
            if current_key and buf:
                sections[current_key] = "\n".join(buf).strip()
            buf = []
            current_key = mapping.get(header.group(1).strip().lower())
        elif current_key:
            buf.append(line)
    if current_key and buf:
        sections[current_key] = "\n".join(buf).strip()

    if sections:
        return {
            "open": sections.get("open", ""),
            "went_well": sections.get("went_well", ""),
            "went_badly": sections.get("went_badly", ""),
            "today": sections.get("today", ""),
        }

    # 5. Letzter Ausweg: gesamten Text in "open" packen
    return {"open": raw[:2000], "went_well": "", "went_badly": "", "today": ""}


def _format_events(events: list[dict]) -> str:
    """Formatiert Events als kompakten Text für den LLM-Kontext."""
    if not events:
        return "Keine Aktivitäten in diesem Zeitraum."

    lines: list[str] = []
    for ev in events:
        ts_raw = ev.get("created_at", "")
        ts = (ts_raw.isoformat() if hasattr(ts_raw, "isoformat") else str(ts_raw))[:16]
        agent = ev.get("agent_name", "?")
        etype = ev.get("event_type", "?")
        text = (ev.get("snippet") or ev.get("text") or ev.get("tool_name") or "")[:300]
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
        "Erstelle jetzt das Morgen-Briefing. "
        "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt — kein Markdown, keine Erklärungen, kein Text davor oder danach:\n"
        '{"open": "...", "went_well": "...", "went_badly": "...", "today": "..."}'
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
        logger.info("zahnfee: LLM-Antwort (%d Zeichen): %.200s", len(raw), raw)
        parsed = _extract_json(raw)
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
