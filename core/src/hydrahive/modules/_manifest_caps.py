"""Manifest-Feld ``capabilities`` (docs/specs/access-groups.md §8).

Ein Modul meldet damit prüfbare Funktionen an. Erlaubte IDs:
``module.<modul-id>`` (Grundfreigabe) und ``<modul-id>.<name>`` (feinere Funktion).
Ohne Angabe bleibt ein Modul für alle offen.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
DEFAULTS = ("everyone", "admin_only")


@dataclass(frozen=True)
class CapabilitySpec:
    id: str
    label: str
    default: str = "everyone"
    tools: tuple[str, ...] = ()


def parse_capabilities(module_id: str, value: object, error: type[Exception]) -> tuple[CapabilitySpec, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise error("manifest.json: 'capabilities' muss eine Liste sein")
    out: list[CapabilitySpec] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise error("manifest.json: jede Capability muss ein Objekt sein")
        cap_id = str(item.get("id", ""))
        if not _valid_id(module_id, cap_id):
            raise error(
                f"manifest.json: ungültige Capability-ID {cap_id!r} "
                f"(erlaubt: 'module.{module_id}' oder '{module_id}.<name>')"
            )
        if cap_id in seen:
            raise error(f"manifest.json: Capability {cap_id!r} doppelt")
        seen.add(cap_id)
        default = str(item.get("default", "everyone"))
        if default not in DEFAULTS:
            raise error(f"manifest.json: Capability {cap_id!r}: default muss {DEFAULTS} sein")
        tools = item.get("tools", [])
        if not isinstance(tools, list) or not all(isinstance(t, str) and t for t in tools):
            raise error(f"manifest.json: Capability {cap_id!r}: 'tools' muss eine Liste von Namen sein")
        out.append(CapabilitySpec(id=cap_id, label=str(item.get("label", cap_id)),
                                  default=default, tools=tuple(tools)))
    return tuple(out)


def _valid_id(module_id: str, cap_id: str) -> bool:
    if cap_id == f"module.{module_id}":
        return True
    prefix, dot, name = cap_id.partition(".")
    return prefix == module_id and dot == "." and bool(_NAME_RE.match(name))
