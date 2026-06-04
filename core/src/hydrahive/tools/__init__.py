"""Core-Tools für HydraHive2-Agenten.

Jedes Tool ist ein eigenes Modul mit einem `TOOL`-Objekt. Die Registry
unten importiert alle und stellt sie dem Runner zur Verfügung.

Public API:
    REGISTRY                    — dict[name, Tool]
    list_tools()                — alle Tools
    get_tool(name)              — einzelnes Tool, raises KeyError
    schemas_for(names)          — JSON-Schemas für LLM (Anthropic-Format)
"""

from hydrahive.tools import (
    ask_agent,
    datamining,
    analyze_image,
    generate_image,
    generate_music,
    generate_speech,
    generate_video,
    transcribe_audio,
    file_patch,
    file_read,
    file_write,
    fetch_url,
    health_data,
    list_projects,
    list_skills,
    load_skill,
    read_mail,
    read_memory,
    search_memory,
    send_mail,
    shell,
    todo,
    web_browser,
    web_search,
    webmin_call,
    webmin_status,
    write_memory,
)
from hydrahive.settings import settings
from hydrahive.tools.base import Tool, ToolContext, ToolResult


def _build_registry() -> dict[str, Tool]:
    """Liste der aktiven Tools. ask_agent nur wenn AgentLink konfiguriert ist —
    sonst sieht der Master ein Tool das immer mit einem Stub-Fehler antwortet,
    was Loop-Detection triggern und Iterationen verschwenden kann (#13)."""
    tools: list[Tool] = [
        shell.TOOL,
        file_read.TOOL,
        file_write.TOOL,
        file_patch.TOOL,
        web_search.TOOL,
        fetch_url.TOOL,
        health_data.TOOL,
        read_memory.TOOL,
        write_memory.TOOL,
        search_memory.TOOL,
        todo.TOOL,
        send_mail.TOOL,
        read_mail.TOOL,
        list_projects.TOOL,
        list_skills.TOOL,
        load_skill.TOOL,
        analyze_image.TOOL,
        generate_image.TOOL,
        generate_music.TOOL,
        generate_speech.TOOL,
        generate_video.TOOL,
        transcribe_audio.TOOL,
        datamining.TOOL_SEARCH,
        datamining.TOOL_SEMANTIC,
        datamining.TOOL_TIMELINE,
        datamining.TOOL_TODAY,
    ]
    if settings.agentlink_url:
        tools.append(ask_agent.TOOL)
    tools.append(web_browser.TOOL)
    tools.append(webmin_status.TOOL)
    tools.append(webmin_call.TOOL)
    return {t.name: t for t in tools}


REGISTRY: dict[str, Tool] = _build_registry()

# Unveränderliche Menge der beim Import vorhandenen Core-Tool-Namen.
_CORE_TOOL_NAMES: frozenset[str] = frozenset(REGISTRY)

# Namen von Modul-Tools die KEIN Core-Tool überlagern.
_MODULE_TOOL_NAMES: set[str] = set()

# Originale Core-Tools die durch ein Modul-Tool temporär verdrängt wurden.
_DISPLACED_CORE: dict[str, Tool] = {}


def register_module_tools(tools: list[Tool]) -> None:
    """Merged Modul-Tools idempotent in REGISTRY. Vorher gemergte Modul-Tools
    werden zuerst entfernt — load_all ist idempotent, ein erneuter Aufruf darf
    nicht duplizieren oder Leichen hinterlassen. REGISTRY bleibt die einzige
    Tool-Quelle, damit get_tool/schemas_for/_defaults unverändert funktionieren.

    Wenn ein Modul-Tool denselben Namen wie ein Core-Tool hat, übernimmt es
    temporär den REGISTRY-Slot. Beim Reset (leere Liste oder neuer Satz) wird
    das Original-Core-Tool WIEDERHERGESTELLT statt gelöscht."""
    # 1. Nicht-Core-Modul-Tools entfernen
    for name in _MODULE_TOOL_NAMES:
        REGISTRY.pop(name, None)
    # 2. Verdrängte Core-Tools wiederherstellen
    REGISTRY.update(_DISPLACED_CORE)
    # 3. Interne Zustandskarten leeren
    _MODULE_TOOL_NAMES.clear()
    _DISPLACED_CORE.clear()
    # 4. Neue Modul-Tools eintragen
    for tool in tools:
        if tool.name in _CORE_TOOL_NAMES and tool.name in REGISTRY:
            # Core-Original merken, bevor es überschrieben wird
            _DISPLACED_CORE[tool.name] = REGISTRY[tool.name]
        else:
            _MODULE_TOOL_NAMES.add(tool.name)
        REGISTRY[tool.name] = tool

# Tools die je nach Setup conditional registriert werden. Auf der Validation-
# Ebene werden sie toleriert — der Runner filtert sie über schemas_for() ohnehin
# raus wenn nicht in REGISTRY. Verhindert Validation-Fail bei bestehenden
# Agent-Configs nachdem AgentLink z.B. aus HH_AGENTLINK_URL entfernt wird (#78).
# ask_agent: nur aktiv wenn AgentLink konfiguriert
# file_search, dir_list, http_request: entfernte Tools — in alten Configs tolerieren
OPTIONAL_TOOLS: frozenset[str] = frozenset({"ask_agent", "web_browser", "file_search", "dir_list", "http_request", "webmin_status", "webmin_call"})


def list_tools() -> list[Tool]:
    return list(REGISTRY.values())


def get_tool(name: str) -> Tool:
    return REGISTRY[name]


def schemas_for(names: list[str]) -> list[dict]:
    """Anthropic-format tool schemas: {name, description, input_schema}."""
    out = []
    for name in names:
        tool = REGISTRY.get(name)
        if not tool:
            continue
        out.append({
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.schema,
        })
    return out


__all__ = [
    "REGISTRY",
    "Tool",
    "ToolContext",
    "ToolResult",
    "list_tools",
    "get_tool",
    "schemas_for",
    "register_module_tools",
]
