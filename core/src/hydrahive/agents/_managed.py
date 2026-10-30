"""Verwaltete Agenten (docs/specs/projekt-container-ausfuehrung.md, K1c).

Ein Modul (z. B. hydralabor) legt einen Agenten an und setzt `managed_by`. Danach ändern nur noch das Modul selbst
(mit seiner Kennung) die festen Felder. Andere Wege – Route, configure_specialist, interne Aufrufe ohne Kennung –
dürfen nur die freien Felder ändern. So kann niemand den eingesperrten Labor-Agenten zum Server-Agenten umbauen.
"""
from __future__ import annotations

import re

FIELD = "managed_by"
FREE = frozenset({"llm_model", "fallback_models", "reasoning_effort", "status", "updated_at"})
_NAME = re.compile(r"^[a-z][a-z0-9_-]{1,62}$")


class AgentManaged(PermissionError):
    """Feld eines verwalteten Agenten ohne die Kennung des verwaltenden Moduls geändert."""

    def __init__(self, managed_by: str) -> None:
        super().__init__(f"agent_managed:{managed_by}")
        self.managed_by = managed_by


def check_name(name: str) -> str:
    if not isinstance(name, str) or not _NAME.match(name):
        raise ValueError("managed_by ungültig")
    return name


def guard(cfg: dict, changes: dict, by: str | None) -> None:
    """Wirft AgentManaged, wenn ein festes Feld ohne die richtige Kennung WIRKLICH geändert werden soll.

    Die Einstellungsseite schickt das ganze Objekt; unverändert mitgeschickte Felder zählen nicht. Verglichen wird
    exakt (Reihenfolge von Listen zählt), damit keine Umdeutung durchrutscht."""
    owner = cfg.get(FIELD)
    if not owner or by == owner:
        return
    changed = {k for k, v in changes.items() if k not in FREE and cfg.get(k) != v}
    if changed:
        raise AgentManaged(owner)


def set_managed(agent_id: str, module_id: str) -> dict:
    """Agent als „verwaltet von <Modul>“ markieren. Nur für Module (Kern-Funktion, keine Route)."""
    from hydrahive.agents._config_utils import get, save_atomic
    from hydrahive.agents._paths import config_path
    from hydrahive.db._utils import now_iso
    cfg = get(agent_id)
    if not cfg:
        raise KeyError(f"Agent '{agent_id}' nicht gefunden")
    cfg[FIELD] = check_name(module_id)
    cfg["updated_at"] = now_iso()
    save_atomic(config_path(agent_id), cfg)
    return cfg
