"""Prüft einen Flow gegen die Registry: Kennt der Server jeden Baustein?

Die Palette im Frontend ist statisch. Damit kein Flow gespeichert wird, den der
Executor nur still überspringen würde, lehnen die Speicher-Routen unbekannte
Subtypes ab. Module tragen ihre Subtypes in dieselben Registries ein und sind
damit automatisch erlaubt.
"""
from __future__ import annotations

from hydrahive.butler.models import Flow
from hydrahive.butler.registry import ACTIONS, CONDITIONS, TRIGGERS

_REGISTRY_BY_TYPE = {
    "trigger": TRIGGERS,
    "condition": CONDITIONS,
    "action": ACTIONS,
}


def unknown_subtypes(flow: Flow) -> list[str]:
    """Liefert die Subtypes der Knoten, die in keiner Registry stehen.

    Reihenfolge wie im Flow, ohne Duplikate.
    """
    missing: list[str] = []
    for node in flow.nodes:
        registry = _REGISTRY_BY_TYPE.get(node.type, {})
        if node.subtype not in registry and node.subtype not in missing:
            missing.append(node.subtype)
    return missing
