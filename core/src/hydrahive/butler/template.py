"""Jinja2-Template-Rendering für Butler-Action-Params.

Sandbox-Mode: kein `__import__`, keine Attribute-Zugriffe auf Magie.
Verfügbare Variablen pro Render: `event` (TriggerEvent als dict).
"""
from __future__ import annotations

import logging

from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger(__name__)

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
    except Exception as e:
        logger.debug("Butler-Template render fehlgeschlagen: %s", e)
        return template
