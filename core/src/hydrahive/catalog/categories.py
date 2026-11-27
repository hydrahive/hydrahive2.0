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
#: Die Namen SIND die ``Tool.category``-Werte (Till 26.11.: englische Namen aus dem Code, eine Bezeichnung statt zwei).
#: Nur so wirkt ``approve()`` (prüft ``Tool.category``); der Test ``test_kategorien_heissen_wie_tool_category`` sichert das.
#: Ausnahme ``skills``: list_skills/load_skill liegen in ``agents``, die Kategorie ``agents`` würde sonst Authoring-Nähe
#: suggerieren – bestätigt werden kann darin nichts (kein Tool hat category ``skills``).
CATEGORY_MAP: dict[str, tuple[str, ...]] = {
    "files": ("file_read", "file_write", "file_patch", "read_document"),
    "web": ("web_search",),
    "memory": ("read_memory", "write_memory", "search_memory", "datamining_search", "datamining_semantic",
                    "datamining_timeline", "datamining_today"),
    "tasks": ("todo_write",),
    "media": ("analyze_image", "generate_image", "generate_music", "generate_speech", "generate_video",
               "transcribe_audio"),
    "code": ("graph_query", "graph_explain", "graph_path", "graph_affected", "graph_refresh"),
    "help": ("help_search", "help_read", "error_report_prepare"),
    "prompts": ("list_prompts", "get_prompt", "save_prompt"),
    "skills": ("list_skills", "load_skill"),
    "mail": ("read_mail",),
}

#: Kurzbeschreibung je Kategorie auf Deutsch – für die Kategorien-Zeilen im Prompt (Plan-Aufgabe 5).
CATEGORY_LABELS: dict[str, str] = {
    "files": "Dateien lesen, schreiben, ändern, PDFs lesen",
    "web": "im Internet suchen",
    "memory": "Notizen merken, Gedächtnis und frühere Gespräche durchsuchen",
    "tasks": "Aufgabenliste der Sitzung",
    "media": "Bilder, Videos, Musik, Sprache erzeugen; Bilder beschreiben; Audio abtippen",
    "code": "Code-Graph: Zusammenhänge im Code verstehen",
    "help": "HydraHive-Hilfe lesen, Fehlerbericht vorbereiten",
    "prompts": "gespeicherte Prompts nutzen",
    "skills": "Skills auflisten und laden",
    "mail": "E-Mails lesen",
}

_PLUGIN_PREFIX = "plugin__"
_MCP_PREFIX = "mcp__"
#: Nie über eine Kategorie: ask_agent und die Katalog-Werkzeuge selbst (die kommen im Katalog-Modus fest dazu).
from hydrahive.catalog import CATALOG_TOOLS as _CATALOG_TOOLS  # noqa: E402
_ALWAYS = frozenset({"ask_agent"}) | _CATALOG_TOOLS


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


_WARNED = False


def _warn_once(exc: Exception) -> None:
    """Einmal je Prozess warnen statt bei jedem Aufruf mit Traceback (Review #784: >600 kB Log bei fehlender Tabelle)."""
    global _WARNED
    if _WARNED:
        logger.debug("Kategorien-Bestätigungen nicht lesbar: %s", exc)
        return
    _WARNED = True
    logger.warning("Kategorien-Bestätigungen nicht lesbar – nur festes Mapping (%s: %s)", type(exc).__name__, exc)


def tools_in_category(category: str) -> list[str]:
    """Freigegebene Tool-Namen einer Kategorie (festes Mapping + Bestätigtes), nach Abzug der Ausschlüsse."""
    from hydrahive.tools import REGISTRY
    if category not in CATEGORY_MAP:
        return []                                       # nur Kategorien aus dem festen Mapping (S2) – auch für Altdaten
    names = list(CATEGORY_MAP[category])
    try:
        for tool in sorted(_approved(category)):
            reg = REGISTRY.get(tool)
            if reg is not None and (reg.category or "other") == category:     # nur, solange es wirklich dort liegt
                names.append(tool)
    except Exception as exc:  # noqa: BLE001 — Fail-closed: nur das feste Mapping
        _warn_once(exc)
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
    if category not in CATEGORY_MAP:
        # Spec S2: Kategorien nur aus dem festen Mapping im Kern. Sonst ließe sich z. B. webmin_call über
        # kategorie:system oder run_tool über kategorie:catalog freigeben (Review #784, sollte).
        raise ValueError(f"Unbekannte Kategorie {category!r} – erlaubt: {', '.join(sorted(CATEGORY_MAP))}.")
    reg = REGISTRY.get(tool)
    if reg is None or _excluded(tool):
        raise ValueError(f"{tool} kann nie über eine Kategorie frei werden.")
    if (reg.category or "other") != category:
        raise ValueError(f"{tool} gehört nicht zur Kategorie {category}.")
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO tool_category_approvals(category, tool, approved_by, approved_at) "
                     "VALUES (?, ?, ?, ?)", (category, tool, by_admin, now_iso()))
        _audit(conn, by_admin, "tool_category_approve", category, tool)


def _audit(conn, username: str, action: str, category: str, tool: str) -> None:
    """Audit-Eintrag im selben Log wie die übrigen Admin-Aktionen (``access_audit``), in der Transaktion der Änderung."""
    from hydrahive.agents._tool_pool_audit import log
    log(conn, username, action, f"tool_category:{category}", [tool])


def list_approvals() -> list[dict]:
    """Alle Bestätigungen (Kategorie, Tool, wer, wann); ``active`` = wirkt heute (Tool liegt noch dort und ist nicht ausgeschlossen)."""
    from hydrahive.db.connection import db
    from hydrahive.tools import REGISTRY
    with db() as conn:
        rows = conn.execute("SELECT category, tool, approved_by, approved_at FROM tool_category_approvals "
                            "ORDER BY category, tool").fetchall()
    out = []
    for r in rows:
        reg = REGISTRY.get(r["tool"])
        active = (r["category"] in CATEGORY_MAP and reg is not None and (reg.category or "other") == r["category"]
                  and not _excluded(r["tool"]))
        out.append({**dict(r), "active": active})
    return out


def revoke(category: str, tool: str, by_admin: str) -> bool:
    """Admin widerruft eine Bestätigung. Nicht-Admin → PermissionError; ``False``, wenn es keine solche Bestätigung gab.

    Das feste Mapping (``CATEGORY_MAP``) lässt sich so nicht widerrufen – nur Bestätigungen aus der Tabelle.
    """
    from hydrahive.api.middleware.users import get_by_username
    from hydrahive.db.connection import db
    user = get_by_username(by_admin)
    if not user or user.get("role") != "admin":
        raise PermissionError("Nur ein Admin darf Kategorie-Bestätigungen widerrufen.")
    with db() as conn:
        cur = conn.execute("DELETE FROM tool_category_approvals WHERE category = ? AND tool = ?", (category, tool))
        if cur.rowcount:
            _audit(conn, by_admin, "tool_category_revoke", category, tool)
    return bool(cur.rowcount)
