"""Werkzeug-Ergebnis `module_view`: bedienbare Modul-Ansicht im Chat (docs/specs/module-view-sandbox.md §2.2).

Das Modul-Werkzeug liefert `ToolResult.ok(text, result_type="module_view", module=…, view_id=…, title=…)`.
Hier wird nur geprüft und durchgereicht; die Ansicht selbst holt der Chat über die signierte Adresse des Moduls.
"""
from __future__ import annotations

import re

from hydrahive.tools.base import ToolResult

_MODULE_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_VIEW_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
TITLE_MAX = 200


def _module_loaded(module_id: str) -> bool:
    from hydrahive.modules import registry  # lazy: REGISTRY wird zur Laufzeit befüllt
    entry = registry.REGISTRY.get(module_id)
    return bool(entry and entry.loaded)


def module_view_media(result: ToolResult) -> list[dict] | None:
    """Ein Media-Eintrag für den Chat – oder None, wenn das Ergebnis keine gültige Modul-Ansicht ist."""
    if not result.success or result.result_type != "module_view":
        return None
    meta = result.metadata or {}
    module, view_id, title = meta.get("module"), meta.get("view_id"), meta.get("title")
    if not (isinstance(module, str) and _MODULE_RE.match(module) and _module_loaded(module)):
        return None
    if not (isinstance(view_id, str) and _VIEW_RE.match(view_id)):
        return None
    title = title[:TITLE_MAX] if isinstance(title, str) else ""
    return [{"kind": "module_view", "module": module, "view_id": view_id, "title": title}]
