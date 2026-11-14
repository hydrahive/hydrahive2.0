"""Modelle des Projekt-Agenten vor dem Anlegen prüfen (Mac-User 14.11.2026: 500 statt Meldung).

Hauptmodell nicht verfügbar → Fehler mit Code, Template und Link (nichts wird angelegt).
Ersatzmodell nicht verfügbar oder Template ohne Modelle → Projekt wird angelegt, die Antwort trägt Warnungen
mit Link zur Template-Seite. Leere Live-Liste (Erst-Setup) → keine Prüfung, wie bisher.
"""
from __future__ import annotations

from typing import Any


class TemplateModelUnavailable(ValueError):
    def __init__(self, template: str, model: str) -> None:
        super().__init__(f"Modell '{model}' aus Template '{template}' ist nicht verfügbar")
        self.template = template
        self.model = model


def template_link(template_id: str) -> str:
    return f"/admin?section=llm&tab=templates&template={template_id}"


def _warning(code: str, template: str, model: str = "") -> dict[str, Any]:
    return {"code": code, "template": template, "model": model, "link": template_link(template)}


def check(template_id: str | None) -> list[dict[str, Any]]:
    """Warnungen für die Antwort; wirft TemplateModelUnavailable, wenn das Hauptmodell fehlt."""
    if not template_id:
        return []
    from hydrahive.agents import templates as tpl
    from hydrahive.agents._validation import _available_models
    try:
        t = tpl.get(template_id)
    except Exception:  # kaputte Template-Datei: Anlegen fällt wie bisher auf das Modell des Aufrufers zurück
        return [_warning("template_not_configured", template_id)]
    chain = [m for m in (t or {}).get("chain") or [] if isinstance(m, str) and m]
    if not chain:
        return [_warning("template_not_configured", template_id)]
    available = set(_available_models())
    if not available:
        return []
    if chain[0] not in available:
        raise TemplateModelUnavailable(template_id, chain[0])
    return [_warning("template_fallback_unavailable", template_id, m)
            for m in dict.fromkeys(chain[1:]) if m not in available]
