"""Ersatzmodelle eines Agenten prüfen (Till 14.11.2026, Anlass: Projekt anlegen gab 500 beim Mac-User).

Form-Fehler bleiben hart. Ein gerade nicht verfügbares Ersatzmodell ist nur eine Warnung – der Failover überspringt
es im Betrieb. Das Hauptmodell prüft weiter `_validation.validate_model` hart.

Wird am Ende von `_validation` eingebunden; Zugriffe auf `_validation` deshalb erst beim Aufruf.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def unknown_fallback_models(models: list[str]) -> list[str]:
    """Rückgabe: Ersatzmodelle, die nicht in der Live-Liste stehen (ohne Doppelte). Leere Liste → keine Prüfung."""
    from hydrahive.agents import _validation as v
    if not isinstance(models, list):
        raise v.AgentValidationError("fallback_models muss eine Liste sein")
    if any(not isinstance(m, str) or not m for m in models):
        raise v.AgentValidationError("fallback_models darf keine leeren Einträge enthalten")
    available = v._available_models()
    unknown = [m for m in dict.fromkeys(models) if available and m not in available]
    if unknown:
        logger.warning("Ersatzmodelle nicht in der Live-Modell-Liste: %s", ", ".join(unknown))
    return unknown


def validate_fallback_models(models: list[str]) -> None:
    """Alte, harte Prüfung (jedes Ersatzmodell muss verfügbar sein) – für Aufrufer außerhalb des Agenten-Anlegens."""
    from hydrahive.agents import _validation as v
    unknown_fallback_models(models)
    for m in models:
        v.validate_model(m)
