"""Bereichs-Verzeichnis: Kern-Bereiche plus Meldungen der Module, aufgelöst gegen die registrierten Tools (Spec 4.1).

Regeln: Der Kern gewinnt immer. Ein Modul darf keinen Kern-Bereich überschreiben und kein Kern-Tool in einen anderen Bereich
ziehen (Warnung im Log, nichts doppelt). Ein neuer Modul-Bereich mit schon vergebener ID wird verworfen (der erste gewinnt).
Tools ohne Bereich (und nicht in der Grundausstattung) stehen unter ``unassigned``; MCP-Tools gehören nie dazu.
"""
from __future__ import annotations

import logging

from hydrahive.agents.areas import BASE_TOOLS, CORE_AREAS, GROUP_NAMES, GROUPS, Area, matches, tools_of

logger = logging.getLogger(__name__)
_MCP_PREFIX = "mcp__"


def _registered() -> list[str]:
    from hydrahive.tools import REGISTRY
    return sorted(n for n in REGISTRY if not n.startswith(_MCP_PREFIX))


def _module_entries() -> list[tuple[str, dict]]:
    """(Modul-ID, agent_areas-Eintrag) aller geladenen Module, stabil nach Modul-ID sortiert."""
    from hydrahive.modules.registry import REGISTRY as MODULES
    out: list[tuple[str, dict]] = []
    for name in sorted(MODULES):
        loaded = MODULES[name]
        manifest = getattr(loaded, "manifest", None)
        if manifest is None or not getattr(loaded, "loaded", False):
            continue
        out.extend((manifest.id, e) for e in manifest.agent_areas)
    return out


def _resolve() -> tuple[list[dict], dict[str, str]]:
    """(Bereiche mit aufgelösten Tools, Tool → Bereichs-ID). Eine Quelle für alle Fragen."""
    registered = _registered()
    core_ids = {a.id for a in CORE_AREAS}
    owner: dict[str, str] = {}                      # Tool → Bereich
    areas: dict[str, dict] = {}
    for a in CORE_AREAS:
        tools = tools_of(a, registered)
        areas[a.id] = {"id": a.id, "group": a.group, "name": a.name, "sentence": a.sentence, "marks": list(a.marks),
                       "tools": tools, "source": "core"}
        for t in tools:
            owner.setdefault(t, a.id)
    for module_id, entry in _module_entries():
        if "area" in entry:
            target = entry["area"]
            if target not in areas:
                logger.warning("Modul %s: agent_areas verweist auf unbekannten Bereich %r – verworfen", module_id, target)
                continue
            tools = sorted({n for n in registered if any(matches(p, n) for p in entry["tools"])})
        else:
            new_id = entry["id"]
            if new_id in core_ids:
                logger.warning("Modul %s: Kern-Bereich %r lässt sich nicht überschreiben – verworfen", module_id, new_id)
                continue
            if new_id in areas:
                logger.warning("Modul %s: Bereich %r ist schon von einem anderen Modul vergeben – verworfen",
                               module_id, new_id)
                continue
            Area(id=new_id, group=entry["group"], name=entry["name"], sentence=entry["sentence"],
                 marks=tuple(entry["marks"]), tools=tuple(entry["tools"]))      # nochmal prüfen (defensiv)
            areas[new_id] = {"id": new_id, "group": entry["group"], "name": entry["name"], "sentence": entry["sentence"],
                             "marks": list(entry["marks"]), "tools": [], "source": module_id}
            target = new_id
            tools = sorted({n for n in registered if any(matches(p, n) for p in entry["tools"])})
        for t in tools:
            if t in owner and owner[t] != target:
                logger.warning("Modul %s: Tool %r liegt schon im Bereich %r – bleibt dort (Kern gewinnt)",
                               module_id, t, owner[t])
                continue
            if t in BASE_TOOLS:
                logger.warning("Modul %s: Tool %r gehört zur Grundausstattung – nicht zuordenbar", module_id, t)
                continue
            owner[t] = target
            if t not in areas[target]["tools"]:
                areas[target]["tools"].append(t)
    for a in areas.values():
        a["tools"] = sorted(a["tools"])
    return list(areas.values()), owner


def _lang(lang: str) -> str:
    return lang if lang in ("de", "en") else "de"


def all_areas(lang: str = "de") -> list[dict]:
    """Kern- und Modul-Bereiche, Namen und Sätze in ``lang`` (unbekannt → de); Tools = registrierte Namen."""
    lang = _lang(lang)
    out = []
    for a in _resolve()[0]:
        out.append({**a, "name": a["name"][lang], "sentence": a["sentence"][lang]})
    return out


def area_of(tool: str) -> str | None:
    """Bereichs-ID des Tools, ``"base"`` für die Grundausstattung, sonst None."""
    if tool in BASE_TOOLS:
        return "base"
    return _resolve()[1].get(tool)


def unassigned() -> list[str]:
    """Registrierte Tools ohne Bereich und nicht in der Grundausstattung (sortiert, ohne MCP)."""
    owner = _resolve()[1]
    return [t for t in _registered() if t not in BASE_TOOLS and t not in owner]


def groups(lang: str = "de") -> list[dict]:
    lang = _lang(lang)
    return [{"id": g, "name": GROUP_NAMES[g][lang]} for g in GROUPS]
