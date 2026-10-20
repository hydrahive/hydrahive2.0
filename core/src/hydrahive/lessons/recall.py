"""Lehren vor der Arbeit auswählen (Spec 10c): passende eigene Lehren zur Eingabe, höchstens drei.

Ähnlichkeit = Kosinus zwischen Eingabe und Auslöser (`cue`), Schwelle aus der Messung vom 20.10.2026. Ohne
Embedding-Modell ein einfacher Wort-Abgleich. Fehler beim Einbetten liefern einfach keine Lehren.
"""
from __future__ import annotations

import logging
import math
import re

from hydrahive.lessons import store

logger = logging.getLogger(__name__)

THRESHOLD = 0.42           # gemessen: passende ≥ 0,43, unpassende ≤ 0,39 (text-embedding-3-small)
LIMIT = 3
MIN_WORDS = 3
CONFIDENCE_WEIGHT = {"high": 1.0, "medium": 0.8, "low": 0.6}
CONFIRM_BONUS = 0.2
_WORD = re.compile(r"[a-zäöüß0-9]{4,}", re.IGNORECASE)
WORD_HITS = 2
# Füllwörter zählen beim Wort-Abgleich nicht (Auslöser beginnen fast alle mit „Wenn …“)
_FILLER = frozenset("""wenn eine einer einem einen dann nicht noch auch aber oder und dass diese dieser dieses
oben unten über unter nach beim ohne mehr sehr schon immer wird werden wurde sind kann soll muss bitte habe haben
when with that this then than from have does into only also some what which there their about after""".split())


def _embed_model() -> str:
    from hydrahive.llm._config import load_config
    return str(load_config().get("embed_model") or "")


async def _embed(texts: list[str], model: str, embed_type: str = "db") -> list[list[float] | None]:
    from hydrahive.llm.embed import aembed_batch
    return await aembed_batch(texts, model, embed_type=embed_type)


def _cos(a: list[float], b: list[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def _scope_ok(row: dict, project_id: str | None) -> bool:
    return row.get("scope") == (f"project:{project_id}" if project_id else "agent")


def _score(row: dict, similarity: float) -> float:
    return similarity * (1 + CONFIRM_BONUS * int(row.get("confirmations", 0))) * CONFIDENCE_WEIGHT.get(row.get("confidence"), 0.6)


async def _similarities(agent_id: str, text: str, rows: list[dict], model: str) -> dict[str, float]:
    missing = [r for r in rows if r.get("cue_model") != model or not r.get("cue_vec")]
    vecs = {r["id"]: r["cue_vec"] for r in rows if r not in missing}
    if missing:
        fresh = await _embed([r["cue"] for r in missing], model, embed_type="db")
        new = {r["id"]: v for r, v in zip(missing, fresh) if v}
        vecs.update(new)
        if new:
            store.set_cue_vecs(agent_id, new, model)
    query = (await _embed([text], model, embed_type="query"))[0]
    return {lid: _cos(query, v) for lid, v in vecs.items()} if query else {}


def _word_similarities(text: str, rows: list[dict]) -> dict[str, float]:
    def words(t: str) -> set[str]:
        return {w.lower() for w in _WORD.findall(t)} - _FILLER
    mine = words(text)
    out = {}
    for r in rows:
        hits = len(mine & words(r.get("cue", "")))
        if hits >= WORD_HITS:
            out[r["id"]] = THRESHOLD + 0.01 * hits
    return out


async def pick(agent_id: str, text: str, *, project_id: str | None) -> list[dict]:
    """Bis zu LIMIT passende aktive Lehren, mit Feld `similarity`; zählt sie als gezeigt."""
    if len(text.split()) < MIN_WORDS:
        return []
    rows = [r for r in store.current(agent_id) if r.get("status") == "active" and _scope_ok(r, project_id)]
    if not rows:
        return []
    model = _embed_model()
    try:
        sims = await _similarities(agent_id, text, rows, model) if model else _word_similarities(text, rows)
    except Exception as e:  # noqa: BLE001 – Abruf ist best-effort, darf den Lauf nie stören
        logger.warning("lessons.recall: Einbetten fehlgeschlagen: %s", e)
        return []
    chosen = sorted((r for r in rows if sims.get(r["id"], 0.0) >= THRESHOLD),
                    key=lambda r: _score(r, sims[r["id"]]), reverse=True)[:LIMIT]
    if chosen:
        store.note_shown(agent_id, chosen)
    return [{**r, "similarity": round(sims[r["id"]], 3), "cue_vec": None} for r in chosen]
