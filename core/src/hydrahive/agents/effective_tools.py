"""Eine einzige Stelle für die wirksamen Tools eines Agenten (docs/specs/tool-skill-katalog.md S6, Katalog Etappe 1).

Alle Prüfer rechnen hier: der Runner (Tool-Liste und ``allowed_tools``), die Gedächtnis-Einstufung (``_mirror_scope``,
``agent_knowledge``) und später ``run_tool``. So kann kein Weg an einer Stufe vorbeilaufen.

Feste Reihenfolge (S6):
    Config ∪ Pool  →  Kategorien auflösen  →  ``scope_tools`` (Projekt, Container-Allowlist)
    →  ``access_filter_tools`` (Besitzer)

Der Katalog ist nur eine Suchhilfe und erweitert nie ein Recht: Was hier nicht herauskommt, darf der Agent nicht.
In dieser Etappe ist ``pool`` immer ``None`` und ``resolve_categories`` die Identität; Pool (Aufgabe 6) und Kategorien
(Aufgabe 4) hängen sich später an genau diesen beiden Stellen ein. MCP-Server bleiben im Runner wie bisher daneben.
"""
from __future__ import annotations


def resolve_categories(names: list[str]) -> list[str]:
    """Ersetzt ``kategorie:<name>`` durch bestätigte Tool-Namen. Bis Aufgabe 4: Identität."""
    return list(names)


def _union(config_tools: list[str] | None, pool: list[str] | None) -> list[str]:
    """Config zuerst, dann Pool in Eingabereihenfolge; Duplikate raus, Reihenfolge stabil."""
    return list(dict.fromkeys([*(config_tools or []), *(pool or [])]))


def effective_tool_names(agent: dict, *, username: str, project: dict | None,
                         pool: list[str] | None = None) -> list[str]:
    """Wirksame lokale Tool-Namen eines Agenten in einem Lauf (ohne MCP; die liefert der Runner daneben)."""
    from hydrahive.access.tool_filter import filter_tools as access_filter_tools
    from hydrahive.runner._project_tool_scope import scope_tools

    names = resolve_categories(_union(agent.get("tools"), pool))
    # scope_tools kennt auch MCP-Server; hier gehen keine mit, sie bleiben Sache des Runners.
    scoped, _ = scope_tools(project, names, [])
    return access_filter_tools(username, scoped)


def possible_tool_names(agent: dict) -> set[str]:
    """Config ∪ Pool des Agenten OHNE Projekt- und Besitzer-Filter.

    Für die Gedächtnis-Einstufung (D4): Der Agent wird nach dem beurteilt, was er bekommen KÖNNTE, nicht nach dem,
    was in diesem Lauf gerade durch den Filter kommt. Das ist die strengere Richtung.
    """
    # ``tool_pool`` gibt es erst ab Plan-Aufgabe 6. Gesetzt werden darf es NUR über agents/tool_pools.py (Besitzer-Prüfung
    # E5/S5); die Agenten-API lehnt das Feld ab (AgentUpdate kennt es nicht). effective_tool_names liest es bewusst NICHT –
    # der Pool kommt dort nur als geprüfter Parameter herein.
    return set(resolve_categories(_union(agent.get("tools"), agent.get("tool_pool"))))
