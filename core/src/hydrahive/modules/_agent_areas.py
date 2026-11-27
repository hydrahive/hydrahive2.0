"""Manifest-Feld ``agent_areas`` (docs/specs/agent-bereiche.md 4.1): Module melden Bereiche für den Agenten-Editor.

Zwei Formen::

    {"area": "home_control", "tools": ["ha_scene_activate"]}                         # Zuordnung zu einem vorhandenen Bereich
    {"id": "vr_studio", "group": "creative", "name": {"de": "…", "en": "…"},          # ein neuer Bereich
     "sentence": {"de": "…", "en": "…"}, "marks": ["costly"], "tools": ["vr_*"]}

Hier wird nur die FORM geprüft. Ob ein Bereich vorhanden ist und ob ein Kern-Bereich überschrieben würde, entscheidet
``agents/_area_registry`` beim Auflösen (Kern gewinnt, Warnung im Log). Fehlt das Feld, ändert sich nichts.
"""
from __future__ import annotations

from hydrahive.agents.areas import GROUPS, MARKS, Area, check_pattern

MAX_ENTRIES = 40
MAX_TOOLS = 200


def parse_agent_areas(raw: object, error_cls: type[Exception]) -> tuple[dict, ...]:
    """Manifest-Feld → Tupel geprüfter Einträge (als dict). Wirft ``error_cls`` bei kaputter Angabe."""
    if raw is None:
        return ()
    if not isinstance(raw, list) or len(raw) > MAX_ENTRIES:
        raise error_cls(f"manifest.json: 'agent_areas' muss eine Liste mit höchstens {MAX_ENTRIES} Einträgen sein")
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            raise error_cls(f"manifest.json: ungültiger agent_areas-Eintrag {item!r}")
        tools = item.get("tools")
        if not isinstance(tools, list) or not tools or len(tools) > MAX_TOOLS:
            raise error_cls("manifest.json: agent_areas-Eintrag braucht 'tools' (nicht leere Liste)")
        try:
            for pattern in tools:
                check_pattern(pattern)
            if item.get("area") is not None:
                if not isinstance(item["area"], str):
                    raise ValueError("'area' muss ein Text sein")
                out.append({"area": item["area"], "tools": list(tools)})
            elif item.get("id") is not None:
                marks = [m for m in (item.get("marks") or [])]
                if not set(marks) <= set(MARKS):
                    raise ValueError(f"unbekannte Markierung in {marks!r}")
                Area(id=str(item["id"]), group=str(item.get("group")), name=item.get("name") or {},
                     sentence=item.get("sentence") or {}, marks=tuple(marks), tools=tuple(tools))   # prüft alles
                out.append({"id": item["id"], "group": item["group"], "name": dict(item["name"]),
                            "sentence": dict(item["sentence"]), "marks": marks, "tools": list(tools)})
            else:
                raise ValueError("weder 'area' noch 'id'")
        except (ValueError, TypeError, AttributeError) as exc:
            raise error_cls(f"manifest.json: ungültiger agent_areas-Eintrag ({exc})") from exc
    return tuple(out)


__all__ = ["parse_agent_areas", "GROUPS"]
