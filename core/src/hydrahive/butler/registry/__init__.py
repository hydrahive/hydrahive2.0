"""Registry-Pattern für Butler-Subtypes.

Drei Registries: TRIGGERS, CONDITIONS, ACTIONS. Jeder Subtype eine eigene
File unter triggers/, conditions/, actions/. Die jeweiligen __init__.py
importieren ihre Subtypes und registrieren sie.

Phase 1: Struktur + Meta-API. Phase 2 füllt mit Implementations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from hydrahive.butler.models import TriggerEvent


@dataclass(frozen=True)
class ParamSchema:
    """Beschreibung eines Param-Felds für die Inspector-UI im Frontend."""
    key: str
    label: str
    kind: str  # "text" | "textarea" | "select" | "time" | "number" | "checkbox" | "list_text"
    required: bool = False
    options: list[str] = field(default_factory=list)
    placeholder: str | None = None
    default: Any = None


@dataclass(frozen=True)
class TriggerSpec:
    subtype: str
    label: str
    description: str
    params: list[ParamSchema]
    matches: Callable[[dict[str, Any], TriggerEvent], bool]


@dataclass(frozen=True)
class ConditionSpec:
    subtype: str
    label: str
    description: str
    params: list[ParamSchema]
    evaluate: Callable[[dict[str, Any], TriggerEvent], bool]


@dataclass(frozen=True)
class ActionSpec:
    subtype: str
    label: str
    description: str
    params: list[ParamSchema]
    execute: Callable[[dict[str, Any], TriggerEvent], "ActionResult"]


@dataclass
class ActionResult:
    ok: bool
    detail: str | None = None


TRIGGERS: dict[str, TriggerSpec] = {}
CONDITIONS: dict[str, ConditionSpec] = {}
ACTIONS: dict[str, ActionSpec] = {}


def register_trigger(spec: TriggerSpec) -> None:
    TRIGGERS[spec.subtype] = spec


def register_condition(spec: ConditionSpec) -> None:
    CONDITIONS[spec.subtype] = spec


def register_action(spec: ActionSpec) -> None:
    ACTIONS[spec.subtype] = spec


def all_specs() -> dict[str, list[dict]]:
    """Meta-API für die Frontend-Inspector-UI: liefert alle bekannten
    Subtypes mit Param-Schemas (ohne Callables — nur JSON-serialisierbar)."""
    def _ps(p: ParamSchema) -> dict:
        return {
            "key": p.key, "label": p.label, "kind": p.kind,
            "required": p.required, "options": list(p.options),
            "placeholder": p.placeholder, "default": p.default,
        }
    return {
        "triggers": [
            {"subtype": s.subtype, "label": s.label, "description": s.description,
             "params": [_ps(p) for p in s.params]}
            for s in TRIGGERS.values()
        ],
        "conditions": [
            {"subtype": s.subtype, "label": s.label, "description": s.description,
             "params": [_ps(p) for p in s.params]}
            for s in CONDITIONS.values()
        ],
        "actions": [
            {"subtype": s.subtype, "label": s.label, "description": s.description,
             "params": [_ps(p) for p in s.params]}
            for s in ACTIONS.values()
        ],
    }


def load_builtins() -> None:
    """Importiert die builtin-Subtypes — wird vom App-Lifespan aufgerufen."""
    from hydrahive.butler.registry import triggers, conditions, actions  # noqa: F401
