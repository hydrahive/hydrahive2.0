"""Jinja2-Template-Rendering für Butler-Action-Params.

Sandbox-Mode: kein `__import__`, keine Attribute-Zugriffe auf Magie.
Verfügbare Variablen pro Render: `event` (TriggerEvent als dict).
"""
from __future__ import annotations

from typing import Any

from jinja2.sandbox import SandboxedEnvironment

from hydrahive.butler.models import TriggerEvent

_ENV = SandboxedEnvironment(autoescape=False)


def render(template: str, event: TriggerEvent) -> str:
    """Rendert einen Template-String. Bei Fehlern den Original-String
    zurück — der Butler soll nicht hart kaputt gehen wegen Tippfehlern."""
    if not template:
        return template
    try:
        tmpl = _ENV.from_string(template)
        return tmpl.render(event=event.model_dump())
    except Exception:
        return template


def render_dict(d: dict[str, Any], event: TriggerEvent) -> dict[str, Any]:
    """Rendert alle String-Values eines Dicts. Nicht-Strings unverändert."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        out[k] = render(v, event) if isinstance(v, str) else v
    return out
