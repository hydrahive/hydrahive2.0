"""Schritt 2-3 einer Runde: suchen → neue URLs holen → extrahieren (parallel, gedrosselt)."""
from __future__ import annotations

import asyncio

from .extractor import extract_finding
from .fetch import fetch_page
from .models import Finding, RunState
from .search import searxng_search

_FETCH_CONCURRENCY = 3   # schont langsame lokale Modelle + freundlich zu Quell-Servern
_MAX_NEW_PER_ROUND = 8


async def gather_round(state: RunState, queries: list[str]) -> int:
    """Sucht alle queries parallel, holt+extrahiert neue URLs. Gibt #neue Findings zurück."""
    search_results = await asyncio.gather(*(searxng_search(q) for q in queries))

    new_results: list[dict] = []
    for results in search_results:
        for item in results:
            url = item["url"]
            if url in state.urls_seen:
                continue
            state.urls_seen.add(url)
            new_results.append(item)
    new_results = new_results[:_MAX_NEW_PER_ROUND]

    sem = asyncio.Semaphore(_FETCH_CONCURRENCY)

    async def _process(item: dict) -> Finding | None:
        async with sem:
            text, image = await fetch_page(item["url"])
            return await extract_finding(state, item, text, image)

    findings = await asyncio.gather(*(_process(it) for it in new_results))
    fresh = [f for f in findings if f is not None]
    state.findings.extend(fresh)
    return len(fresh)
