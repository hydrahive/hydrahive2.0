"""Systemrollen-Templates in llm.json spiegeln (Aufräumen 14.11.2026).

Die LLM-Seite zeigt Chat-Standard und Lehren-Modell nicht mehr – eingestellt wird nur noch am Template
(„assistant“ = Chat-Standard, „lehren“ = Lehren). Damit alle bisherigen Leser (Hilfe, Buddy-Anlage, Module,
Kompaktierungs-Rückfall …) weiter stimmen, schreibt das Speichern dieser Templates ihr Primärmodell nach
`default_model` bzw. `lessons_model`. Der Lehren-Schalter „aus“ (`lessons_model == "off"`) bleibt unangetastet.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_MIRROR = {"assistant": "chat", "lehren": "lessons"}


def mirror_to_llm_config(template_id: str, chain: list[str]) -> None:
    purpose = _MIRROR.get(template_id)
    if not purpose or not chain:
        return
    from hydrahive.llm import _config
    try:
        if purpose == "lessons" and _config.get_default("lessons") == _config.LESSONS_OFF:
            return
        if _config.get_default(purpose) != chain[0]:
            _config.set_default(purpose, chain[0])
    except Exception:  # Spiegeln darf das Speichern des Templates nie verhindern
        logger.exception("Template %s nicht nach llm.json gespiegelt", template_id)
