"""Runnable check: der Research-Loop mit gestubbtem LLM + Suche + Fetch.

Kein Netzwerk, kein echtes Modell — prüft, dass plan→runden→synth→stop→final
einen zitierten Bericht mit Quellen erzeugt und sauber mit 0 Treffern umgeht.
"""
from __future__ import annotations

import pytest

import backend.research.gather as gather_mod
import backend.research.llm as llm_mod
from backend.research import run_research
from backend.research.models import RunState


async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
    content = messages[-1]["content"]
    if "Zerlege die Frage" in content:
        return '{"category":"general","subquestions":["Was ist X?","Wie funktioniert X?"]}'
    if "Suchanfragen" in content:
        return '["X grundlagen","X funktionsweise"]'
    if "Extrahiere NUR Information" in content:
        return '{"relevant":true,"summary":"X ist ein Testthema.","evidence":"Beleg 42"}'
    if "Aktualisiere den Arbeitsbericht" in content:
        return "## Überblick\nX ist ein Testthema ([Quelle](https://a.test/1))."
    if "YES oder NO" in content:
        return "YES"
    if "Schreibe den finalen Bericht" in content:
        return (
            "# X — Recherchebericht\n\n"
            "## Executive Summary\nX ist ein gut dokumentiertes Testthema "
            "([Quelle](https://a.test/1)).\n\n"
            "## Details\nWeitere Fakten ([Quelle B](https://b.test/2)).\n\n"
            "## Fazit\nDie Recherche ist abgeschlossen."
        )
    return ""


async def fake_search(query, count=8):
    return [
        {"title": "Quelle A", "url": "https://a.test/1", "snippet": "…"},
        {"title": "Quelle B", "url": "https://b.test/2", "snippet": "…"},
    ]


async def fake_fetch(url):
    return ("Langer Seitentext über X. " * 30, "https://img.test/og.jpg")


@pytest.fixture
def stub(monkeypatch):
    monkeypatch.setattr(llm_mod, "complete", fake_complete)
    monkeypatch.setattr(gather_mod, "searxng_search", fake_search)
    monkeypatch.setattr(gather_mod, "fetch_page", fake_fetch)


@pytest.mark.asyncio
async def test_loop_produces_cited_report(stub):
    state = RunState(question="Was ist X?")
    result = await run_research(state, min_rounds=2, max_rounds=4)

    assert result["markdown"].startswith("#")
    assert "https://a.test/1" in result["markdown"]          # Inline-Zitat überlebt
    urls = [s["url"] for s in result["sources"]]
    assert "https://a.test/1" in urls
    assert result["sources"][0]["image"] == "https://img.test/og.jpg"   # OG-Image mitgeführt
    assert result["category"] == "general"
    assert result["stats"]["rounds"] == 2                    # stoppt nach min_rounds bei YES
    assert result["stats"]["sources"] >= 1


@pytest.mark.asyncio
async def test_loop_handles_no_results(stub, monkeypatch):
    async def empty_search(query, count=8):
        return []

    monkeypatch.setattr(gather_mod, "searxng_search", empty_search)
    state = RunState(question="Frage ohne Treffer")
    result = await run_research(state, min_rounds=1, max_rounds=2)

    assert result["sources"] == []
    assert result["markdown"]               # Fallback-Bericht statt Crash
    assert result["stats"]["sources"] == 0
