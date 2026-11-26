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
    logger.info("Tool-Katalog: %d Einträge", len(entries))
    return len(entries)
