"""Mirror — Card-Store: abgeleitete, recompute-safe Gist-Cards, getrennt vom
kuratierten Memory. Tabelle/Embedding-Spalte siehe `_mirror_ddl` (cards in
DDL_TABLES + ensure_embed_col(table="cards")). Listing/Suche für Recall A+C
folgen in eigenen Funktionen (Tasks 5/6)."""
from __future__ import annotations

import json
import logging
from typing import Any

from hydrahive.db._mirror_cards_model import Card
from hydrahive.db._mirror_search import _dt, _pool

logger = logging.getLogger(__name__)

_COLS = (
    "card_id, session_id, gist, valence, salience, groundedness, topics, "
    "agent_id, agent_name, username, created_at, source, confidence, "
    "superseded_by, supersedes, schema_version, computed_at, consolidation_model, "
    "embedding, embedding_model, embedded_at"
)

# Felder ohne embedding — embedding (großer Vektor) wird beim Lesen nicht gebraucht.
_READ_COLS = (
    "card_id, session_id, gist, valence, salience, groundedness, topics, "
    "agent_id, agent_name, username, created_at, source, confidence, "
    "superseded_by, supersedes, schema_version, computed_at, consolidation_model"
)


def _vec_str(embedding: list[float] | None) -> str | None:
    """pgvector-Literal wie in _mirror_embed/_mirror_search ('[a,b,c]' → $::text::vector)."""
    if not embedding:
        return None
    return "[" + ",".join(str(x) for x in embedding) + "]"


# asyncpg liefert JSONB als Text-String (kein Codec registriert) → beim Lesen
# zurück nach Python-Objekt parsen. Schreiben passiert via json.dumps + $::jsonb.
_JSONB_FIELDS = ("topics", "source", "superseded_by", "supersedes")


def _loads(v: Any) -> Any:
    if not isinstance(v, str):
        return v
    try:
        return json.loads(v)
    except (ValueError, TypeError):
        return v


async def upsert_card(card: Card, embedding: list[float] | None = None) -> None:
    """Schreibt/aktualisiert eine Card idempotent (ON CONFLICT card_id).
    recompute-safe: derselbe card_id → genau eine Zeile, überschrieben."""
    pool = _pool()
    if not pool:
        return
    vec = _vec_str(embedding)
    embed_model: str | None = None
    if vec is not None:
        from hydrahive.llm._config import load_config
        embed_model = load_config().get("embed_model", "") or None
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO cards ({_COLS})
                VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8,$9,$10,$11,$12::jsonb,$13,
                        $14::jsonb,$15::jsonb,$16,now(),$17,
                        $18::text::vector,$19,
                        CASE WHEN $18::text IS NULL THEN NULL ELSE now() END)
                ON CONFLICT (card_id) DO UPDATE SET
                    session_id=EXCLUDED.session_id, gist=EXCLUDED.gist,
                    valence=EXCLUDED.valence, salience=EXCLUDED.salience,
                    groundedness=EXCLUDED.groundedness, topics=EXCLUDED.topics,
                    agent_id=EXCLUDED.agent_id, agent_name=EXCLUDED.agent_name,
                    username=EXCLUDED.username, created_at=EXCLUDED.created_at,
                    source=EXCLUDED.source, confidence=EXCLUDED.confidence,
                    superseded_by=EXCLUDED.superseded_by, supersedes=EXCLUDED.supersedes,
                    schema_version=EXCLUDED.schema_version, computed_at=EXCLUDED.computed_at,
                    consolidation_model=EXCLUDED.consolidation_model,
                    embedding=EXCLUDED.embedding, embedding_model=EXCLUDED.embedding_model,
                    embedded_at=EXCLUDED.embedded_at
                """,
                card.card_id, card.session_id, card.gist, card.valence, card.salience,
                card.groundedness, json.dumps(card.topics or []), card.agent_id,
                card.agent_name, card.username,
                _dt(card.created_at) if card.created_at else None,
                json.dumps(card.source) if card.source is not None else None,
                card.confidence, json.dumps(card.superseded_by or []),
                json.dumps(card.supersedes or []), card.schema_version,
                card.consolidation_model, vec, embed_model,
            )
    except Exception as e:
        logger.warning("upsert_card(%s) fehlgeschlagen: %s", card.card_id, e)


def _parse_row(row) -> dict[str, Any]:
    """asyncpg-Row → dict mit geparsten JSONB-Feldern (topics/source/superseded)."""
    d = dict(row)
    for k in _JSONB_FIELDS:
        if k in d:
            d[k] = _loads(d.get(k))
    return d


async def get_card(card_id: str) -> dict[str, Any] | None:
    pool = _pool()
    if not pool:
        return None
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_READ_COLS} FROM cards WHERE card_id = $1", card_id
            )
        return _parse_row(row) if row else None
    except Exception as e:
        logger.warning("get_card(%s) fehlgeschlagen: %s", card_id, e)
        return None


async def wipe_cards() -> int:
    """Löscht alle Cards (für wipe-and-rebuild der abgeleiteten Schicht).
    Berührt NUR die cards-Tabelle, nie das kuratierte Memory."""
    pool = _pool()
    if not pool:
        return 0
    try:
        async with pool.acquire() as conn:
            status = await conn.execute("DELETE FROM cards")
        tail = status.split()[-1] if status else ""
        return int(tail) if tail.isdigit() else 0
    except Exception as e:
        logger.warning("wipe_cards fehlgeschlagen: %s", e)
        return 0


async def top_cards_for(agent_id: str | None, limit: int = 8) -> list[dict[str, Any]]:
    """Recall A: Top-N Cards eines Agents nach recency × salience (high zuerst,
    dann jüngste). Ohne agent_id: über alle (Fallback)."""
    pool = _pool()
    if not pool:
        return []
    order = "(salience = 'high') DESC, created_at DESC NULLS LAST"
    try:
        async with pool.acquire() as conn:
            if agent_id:
                rows = await conn.fetch(
                    f"SELECT {_READ_COLS} FROM cards WHERE agent_id = $1 "
                    f"ORDER BY {order} LIMIT $2",
                    agent_id, limit,
                )
            else:
                rows = await conn.fetch(
                    f"SELECT {_READ_COLS} FROM cards ORDER BY {order} LIMIT $1", limit
                )
        return [_parse_row(r) for r in rows]
    except Exception as e:
        logger.warning("top_cards_for(%s) fehlgeschlagen: %s", agent_id, e)
        return []


async def search_cards(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Recall C: cue-getriggerte pgvector-Cosine-Suche über cards.embedding —
    selbes Muster wie _mirror_search._semantic_search, nur auf der cards-Tabelle."""
    pool = _pool()
    if not pool or not query.strip():
        return []
    from hydrahive.llm._config import load_config
    from hydrahive.llm.embed import aembed
    model = load_config().get("embed_model", "")
    if not model:
        return []
    try:
        vec = await aembed(query, model, embed_type="query")
        if vec is None:
            return []
        vec_str = "[" + ",".join(str(x) for x in vec) + "]"
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {_READ_COLS}, "
                "round((1 - (embedding <=> $1::text::vector))::numeric, 3)::float8 AS similarity "
                "FROM cards WHERE embedding IS NOT NULL "
                "ORDER BY embedding <=> $1::text::vector LIMIT $2",
                vec_str, limit,
            )
        return [_parse_row(r) for r in rows]
    except Exception as e:
        logger.warning("search_cards fehlgeschlagen: %s", e)
        return []
