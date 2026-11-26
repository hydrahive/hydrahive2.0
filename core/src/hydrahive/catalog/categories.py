"""Kategorien-Freigabe (Spec S2, D5, K12): ``kategorie:<name>`` löst sich in bestätigte Tool-Namen auf.

Freigegeben wird nur, was
  * im festen Mapping ``CATEGORY_MAP`` (im Kern gepflegt) steht, oder
  * ein Admin für genau diese Kategorie bestätigt hat (Tabelle ``tool_category_approvals``, Migration 067) UND
    im Moment tatsächlich in dieser Kategorie registriert ist.
Nie frei werden, auch nicht mit Bestätigung: Plugin- und MCP-Tools, Tools mit Capability, ``AUTHORING_TOOLS``, ``ask_agent``
und Außen-Tools (``OUTWARD_TOOLS``). Die Ausschlüsse wirken beim Auflösen, nicht erst bei der Pflege des Mappings.
Fail-closed: Ist die Bestätigungstabelle nicht lesbar, gilt nur das feste Mapping.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

PREFIX = "kategorie:"

#: Feste Zuordnung Kategorie → Kern-Tools (im Kern gepflegt). Ohne Außen-Tools, Authoring, ask_agent und Capability-Tools.
CATEGORY_MAP: dict[str, tuple[str, ...]] = {
    "dateien": ("file_read", "file_write", "file_patch", "read_document"),
    "web": ("web_search",),
    "gedaechtnis": ("read_memory", "write_memory", "search_memory", "datamining_search", "datamining_semantic",
                    "datamining_timeline", "datamining_today"),
    "aufgaben": ("todo_write",),
    "medien": ("analyze_image", "generate_image", "generate_music", "generate_speech", "generate_video",
               "transcribe_audio"),
    "code": ("graph_query", "graph_explain", "graph_path", "graph_affected", "graph_refresh"),
    "hilfe": ("help_search", "help_read", "error_report_prepare"),
    "prompts": ("list_prompts", "get_prompt", "save_prompt"),
    "skills": ("list_skills", "load_skill"),
    "post": ("read_mail",),
}

_PLUGIN_PREFIX = "plugin__"
_MCP_PREFIX = "mcp__"
_ALWAYS = frozenset({"ask_agent"})


def _capability_for(name: str, module_id: str) -> str | None:
    from hydrahive.access.capabilities import CATALOG
    return CATALOG.capability_for_tool(name, module_id=module_id)


def _excluded(name: str) -> bool:
    """S2: Dieses Tool wird nie über eine Kategorie frei."""
    from hydrahive.db._mirror_groups import OUTWARD_TOOLS
    from hydrahive.tools._project_authoring import AUTHORING_TOOLS
    if name.startswith((_PLUGIN_PREFIX, _MCP_PREFIX)) or name in _ALWAYS or name in AUTHORING_TOOLS or name in OUTWARD_TOOLS:
        return True
    from hydrahive.tools import REGISTRY
    tool = REGISTRY.get(name)
    if tool is None:
        return True                                     # unbekannt → nicht frei
    try:
        return _capability_for(name, getattr(tool, "module_id", "") or "") is not None
    except Exception:  # noqa: BLE001 — nicht prüfbar → nicht frei
        return True


def _approved(category: str) -> set[str]:
    from hydrahive.db.connection import db
    with db() as conn:
        rows = conn.execute("SELECT tool FROM tool_category_approvals WHERE category = ?", (category,)).fetchall()
    return {r["tool"] for r in rows}


def tools_in_category(category: str) -> list[str]:
    """Freigegebene Tool-Namen einer Kategorie (festes Mapping + Bestätigtes), nach Abzug der Ausschlüsse."""
    from hydrahive.tools import REGISTRY
    names = list(CATEGORY_MAP.get(category, ()))
    try:
        for tool in sorted(_approved(category)):
            reg = REGISTRY.get(tool)
            if reg is not None and (reg.category or "other") == category:     # nur, solange es wirklich dort liegt
                names.append(tool)
    except Exception:  # noqa: BLE001 — Fail-closed: nur das feste Mapping
        logger.warning("Kategorien-Bestätigungen nicht lesbar – nur festes Mapping", exc_info=True)
    return [n for n in dict.fromkeys(names) if n in REGISTRY and not _excluded(n)]


def resolve_categories(names: list[str]) -> list[str]:
    """Ersetzt ``kategorie:<name>`` durch freigegebene Tool-Namen; alles andere bleibt unverändert. Duplikate raus,
    Reihenfolge stabil. Eine unbekannte Kategorie ergibt nichts."""
    out: list[str] = []
    for name in names:
        if isinstance(name, str) and name.startswith(PREFIX):
            out.extend(tools_in_category(name[len(PREFIX):]))
        else:
            out.append(name)
    return list(dict.fromkeys(out))


def approve(category: str, tool: str, by_admin: str) -> None:
    """Admin bestätigt, dass ``tool`` zur Kategorie gehört und darüber frei sein darf.

    Nicht-Admin → PermissionError. Ausgeschlossenes Tool oder Tool, das nicht in dieser Kategorie registriert ist →
    ValueError (der Eintrag würde ohnehin nie wirken).
    """
    from hydrahive.api.middleware.users import get_by_username
    from hydrahive.db._utils import now_iso
    from hydrahive.db.connection import db
    from hydrahive.tools import REGISTRY
    user = get_by_username(by_admin)
    if not user or user.get("role") != "admin":
        raise PermissionError("Nur ein Admin darf Kategorie-Zuordnungen bestätigen.")
    reg = REGISTRY.get(tool)
    if reg is None or _excluded(tool):
        raise ValueError(f"{tool} kann nie über eine Kategorie frei werden.")
    if (reg.category or "other") != category:
        raise ValueError(f"{tool} gehört nicht zur Kategorie {category}.")
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO tool_category_approvals(category, tool, approved_by, approved_at) "
                     "VALUES (?, ?, ?, ?)", (category, tool, by_admin, now_iso()))
