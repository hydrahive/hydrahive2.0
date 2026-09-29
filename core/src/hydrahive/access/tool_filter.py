"""Werkzeuge nach Freigaben des Besitzers filtern (docs/specs/access-groups.md §7 Regel 6, §9).

Agenten erben die Rechte ihres Besitzers. Maßgeblich ist der Besitzer des Laufs
(ToolContext.user_id, heute der Nutzername). Geprüft werden nur Werkzeuge, die
ein Modul einer deklarierten Funktion zuordnet. Core-, MCP- und Plugin-Werkzeuge
bleiben unberührt.
"""
from __future__ import annotations

from hydrahive.access import check
from hydrahive.access.capabilities import catalog


def _capability(tool_name: str) -> str | None:
    from hydrahive.tools import REGISTRY
    tool = REGISTRY.get(tool_name)
    module_id = getattr(tool, "module_id", "") if tool else ""
    return catalog().capability_for_tool(tool_name, module_id=module_id)


def tool_denied(username: str, tool_name: str) -> str | None:
    """Funktion, die fehlt, oder None wenn das Werkzeug erlaubt ist."""
    cap = _capability(tool_name)
    if cap is None or check.can_use_as(username, cap):
        return None
    return cap


def filter_tools(username: str, tool_names: list[str]) -> list[str]:
    """Entfernt Werkzeuge ohne Freigabe. Reihenfolge bleibt erhalten."""
    return [name for name in tool_names if tool_denied(username, name) is None]
