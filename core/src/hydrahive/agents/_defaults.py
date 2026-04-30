from __future__ import annotations

# `ask_agent` ist optional und wird zur Laufzeit gefiltert (siehe unten) —
# nur wenn AgentLink konfiguriert ist (settings.agentlink_url), sonst würde
# der Master ein Tool sehen das nur Stub-Fehler zurückgibt.
_BASE_TOOLS: dict[str, list[str]] = {
    "master": [
        "shell_exec", "file_read", "file_write", "file_patch", "file_search",
        "dir_list", "web_search", "http_request",
        "read_memory", "write_memory", "search_memory",
        "todo_write", "ask_agent", "send_mail",
    ],
    "project": [
        "shell_exec", "file_read", "file_write", "file_patch", "file_search",
        "dir_list",
        "read_memory", "write_memory", "search_memory",
        "todo_write", "ask_agent",
    ],
    "specialist": [],
}


def _filtered() -> dict[str, list[str]]:
    """Filtert nicht-registrierte Tools raus — primär ask_agent wenn
    AgentLink nicht konfiguriert ist."""
    from hydrahive.tools import REGISTRY  # lazy um Zyklen zu vermeiden
    return {
        agent_type: [t for t in tools if t in REGISTRY]
        for agent_type, tools in _BASE_TOOLS.items()
    }


class _LazyDefaultTools(dict):
    """dict-Wrapper der bei jedem Zugriff frisch filtert — Settings-Wechsel
    zur Laufzeit (z.B. in Tests) werden so erfasst."""
    def __getitem__(self, key):
        return _filtered()[key]
    def keys(self):
        return _BASE_TOOLS.keys()
    def items(self):
        return _filtered().items()
    def values(self):
        return _filtered().values()
    def __iter__(self):
        return iter(_BASE_TOOLS.keys())


DEFAULT_TOOLS = _LazyDefaultTools()

DEFAULT_TEMPERATURE = 0.7
# Höher als üblich, damit Code-Generation (Tetris, längere Files) durchläuft.
# Ein Tool-Use mit 5000-Zeichen-content braucht ~1500-2000 Tokens nur fürs Input-JSON.
DEFAULT_MAX_TOKENS = 8192
DEFAULT_THINKING_BUDGET = 0
