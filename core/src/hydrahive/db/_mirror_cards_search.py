"""Recall C: cue-getriggerte Kartensuche mit derselben Sicht wie die Datamining-Werkzeuge.

Vorher (bis 09.10.2026) filterte die Suche nur nach Nutzer: Ein Projekt-Agent konnte per Ähnlichkeit
Karten anderer Agenten desselben Nutzers in den System-Prompt bekommen – auch aus Buddy-Sitzungen mit
Gesundheits-/Privat-Werkzeugen (Task ddb1ff35, docs/specs/knowledge-spaces.md §2.3).

Regel:
- **eigene Karten** des Agenten: immer (wie ``top_cards_for`` – sie stehen dort ohnehin im Prompt),
- **fremde Karten**: nur, wenn ihre Sitzung in der Sicht des Agenten liegt (``_mirror_scope.where``:
  Projekt, Gruppen, Schutzstufe, Außenwirkung).
Ohne Nutzer: nie Treffer.
"""
from __future__ import annotations

import logging
from typing import Any

from hydrahive.db._mirror_scope import Scope, where

logger = logging.getLogger(__name__)

ITERATIVE_SCAN = "SET LOCAL hnsw.iterative_scan = relaxed_order"


def card_filter(scope: Scope, agent_id: str | None, start: int) -> tuple[str, list, int]:
    """(Bedingung, Parameter, nächster Index) für ``cards c``. Werte nur als Parameter."""
    if not scope.username:
        return "FALSE", [], start
    i = start
    params: list = [scope.username]
    user = f"c.username = ${i}"
    i += 1
    conds, sparams, i = where(scope, i, alias="e")
    if conds == ["FALSE"]:
        foreign = "FALSE"
    else:
        foreign = (f"EXISTS (SELECT 1 FROM events e WHERE e.session_id = c.session_id "
                   f"AND {' AND '.join(conds)})")
        params.extend(sparams)
    if agent_id:
        own = f"c.agent_id = ${i}"
        params.append(agent_id)
        i += 1
        return f"{user} AND ({own} OR {foreign})", params, i
    return f"{user} AND {foreign}", params, i


async def search_cards(
    query: str, limit: int = 5, *, username: str, agent_id: str | None = None, scope: Scope | None = None,
) -> list[dict[str, Any]]:
    """pgvector-Cosine-Suche über ``cards.embedding`` in der Sicht des Agenten.

    ``scope`` fehlt → nur eigene Karten des Agenten (streng statt ungefiltert)."""
    from hydrahive.db._mirror_cards import _READ_COLS, _parse_row
    from hydrahive.db._mirror_search import _pool

    pool = _pool()
    if not pool or not query.strip() or not username:
        return []
    if scope is None:
        if not agent_id:
            return []
        scope = Scope(username=username, scope="project", projects=())   # where() → FALSE: nur eigene
    if scope.username != username:
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
        cond, params, _ = card_filter(scope, agent_id, 3)
        async with pool.acquire() as conn, conn.transaction():
            # HNSW liefert nur ef_search Kandidaten und filtert danach – bei enger Sicht blieben so 40 von
            # 93 Treffern liegen (gemessen 09.10., 16 Agenten × 3 Fragen). Iterativ (pgvector ≥ 0.8) scannt
            # nach, bis LIMIT erreicht ist: 93/93 bei gleicher Laufzeit. Nur für diese Transaktion.
            await conn.execute(ITERATIVE_SCAN)
            rows = await conn.fetch(
                f"SELECT {_READ_COLS}, "
                "round((1 - (embedding <=> $1::text::vector))::numeric, 3)::float8 AS similarity "
                f"FROM cards c WHERE embedding IS NOT NULL AND {cond} "
                "ORDER BY embedding <=> $1::text::vector LIMIT $2",
                vec_str, limit, *params,
            )
        return [_parse_row(r) for r in rows]
    except Exception as e:
        logger.warning("search_cards fehlgeschlagen: %s", e)
        return []
