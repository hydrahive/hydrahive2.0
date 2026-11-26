"""Katalog-Einträge bauen (Spec S7): aus REGISTRY und Plugin-Tools, nie aus MCP.

``name`` ist der volle Name inklusive Präfix (``plugin__x__tool``) und damit der eindeutige Schlüssel. Die Such-Werkzeuge
selbst (``run_tool``, ``find_tools``, ``find_skills``) stehen nicht im Katalog.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

#: Nie im Katalog: die Werkzeuge der Suche selbst.
EXCLUDED = frozenset({"run_tool", "find_tools", "find_skills"})
MCP_PREFIX = "mcp__"


@dataclass(frozen=True)
class CatalogEntry:
    name: str
    kind: Literal["tool", "skill"]
    title: str
    text: str
    category: str = "other"
    owner_scope: str = "system"
    schema: dict | None = None


def _plugin_tools() -> list[dict]:
    """Plugin-Tools als {name, description, schema}; ohne geladene Plugins leer."""
    try:
        from hydrahive.plugins import tool_bridge
        from hydrahive.plugins.tool_bridge import REGISTRY as PLUGINS
    except Exception:  # noqa: BLE001 — Plugin-System nicht verfügbar → nur Kern
        return []
    out: list[dict] = []
    for plugin in PLUGINS.values():
        if not getattr(plugin, "loaded", False):
            continue
        for tool in plugin.tools:
            out.append({"name": tool_bridge.make_tool_name(plugin.name, tool.name),
                        "description": tool.description, "schema": tool.schema})
    return out


def _title_for(name: str, description: str) -> str:
    first = (description or "").strip().split(". ")[0].strip()
    return (first[:140] or name)


def build_entries() -> list[CatalogEntry]:
    """Aktueller Stand aller Tool-Einträge (ohne MCP, ohne Such-Werkzeuge)."""
    from hydrahive.tools import REGISTRY
    entries: dict[str, CatalogEntry] = {}
    for name, tool in REGISTRY.items():
        if name in EXCLUDED or name.startswith(MCP_PREFIX):
            continue
        entries[name] = CatalogEntry(
            name=name, kind="tool", title=_title_for(name, tool.description),
            text=f"{name.replace('_', ' ')}. {tool.description}", category=getattr(tool, "category", "other") or "other",
            owner_scope="module" if getattr(tool, "module_id", "") else "system", schema=tool.schema)
    for meta in _plugin_tools():
        name = meta["name"]
        if name in EXCLUDED or name.startswith(MCP_PREFIX):
            continue
        entries[name] = CatalogEntry(
            name=name, kind="tool", title=_title_for(name, meta["description"]),
            text=f"{name.replace('_', ' ')}. {meta['description']}", category="plugin", owner_scope="plugin",
            schema=meta.get("schema"))
    return list(entries.values())


def rebuild_tool_index() -> int:
    """Index neu aufbauen und im Speicher ablegen. Entfernte Tools verschwinden. Liefert die Anzahl Einträge.

    Embeddings entstehen nie hier, sondern im Hintergrund (``_store.sync_embeddings``); dieser Aufruf blockiert nie.
    """
    from hydrahive.catalog import _store
    entries = build_entries()
    _store.get_store().replace_all(entries, kind="tool")
    logger.debug("Tool-Katalog: %d Einträge", len(entries))
    return len(entries)


async def warm_catalog() -> None:
    """Beim Start im Hintergrund: Index bauen, dann Vektoren nachholen (nie blockierend, Fehler nur geloggt).

    Vektoren liegen im Speicher (≈ 50–500 Einträge × 1–4 KB); eine Postgres-Tabelle lohnt erst bei viel mehr Einträgen.
    Ohne Embed-Modell oder Postgres bleibt es bei der Wortsuche (K9).
    """
    from hydrahive.catalog import _store
    try:
        rebuild_tool_index()
        from hydrahive.db import mirror
        from hydrahive.llm._config import load_config
        model = (load_config() or {}).get("embed_model") or ""
        done = await _store.sync_embeddings(_store.get_store(), pool=mirror._pool, model=model)
        logger.info("Tool-Katalog: %d Vektoren berechnet", done)
    except Exception:  # noqa: BLE001 — der Start darf daran nie scheitern
        logger.warning("Tool-Katalog: Aufwärmen fehlgeschlagen – nur Wortsuche", exc_info=True)


def build_skill_entries(agent: dict, *, user_id: str, project_id: str | None) -> list[CatalogEntry]:
    """Skill-Einträge genau für diesen Agenten (S7): nur, was ``skills.loader.list_for_agent`` liefert.

    Skills gehören Nutzern, Projekten und Agenten und stehen deshalb NIE im globalen Speicher; ``find_skills`` baut diese
    Menge je Aufruf und sucht nur darin. ``owner_scope`` ist der Bereich des Skills (system/user/project/agent).
    """
    from hydrahive.skills import list_for_agent
    owner = agent.get("owner") or user_id
    skills = list_for_agent(agent.get("id", ""), owner, disabled=list(agent.get("disabled_skills") or []),
                            project_id=project_id or agent.get("project_id"))
    return [CatalogEntry(
        name=s.name, kind="skill", title=(s.description or s.name).strip()[:140],
        text=f"{s.name.replace('-', ' ').replace('_', ' ')}. {s.description} {s.when_to_use}",
        category="skill", owner_scope=s.scope) for s in skills]
