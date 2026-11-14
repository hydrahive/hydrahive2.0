"""Harte Bindung von Agenten an Templates (Spec agent-templates.md Kap. 5, Plan E3).

Ist `template` gesetzt, kommen Modell, Fallback und Budget nur noch aus dem Template. Diese Felder am Agenten
zu ändern wird abgelehnt (`agent_bound_to_template`); unverändert mitgeschickte Werte (die Einstellungsseite
schickt das ganze Objekt) zählen nicht. Die alten Werte bleiben bis zur Aufräum-Etappe in der Datei, damit
ein Zurückrollen möglich ist.
"""
from __future__ import annotations

from typing import Any

BOUND_FIELDS = frozenset({
    "llm_model", "fallback_models", "max_iterations", "max_tokens", "handoff_timeout_seconds",
    "reasoning_effort", "compact_threshold_pct", "cache_ttl", "compact_model",
})


def check_template(template_id: str) -> None:
    from hydrahive.agents import templates as tpl
    from hydrahive.agents._validation import AgentValidationError
    if not template_id or tpl.get(template_id) is None:
        raise AgentValidationError("template_unknown")


def guard(cfg: dict, changes: dict[str, Any]) -> None:
    """Wirft, wenn ein gebundenes Feld eines gebundenen Agenten WIRKLICH geändert werden soll."""
    from hydrahive.agents._validation import AgentValidationError
    if "template" in changes:
        if changes["template"]:
            check_template(changes["template"])
        else:
            changes["template"] = None          # Bindung lösen nur ausdrücklich (Admin-Werkzeug, E3-Rückweg)
    bound = changes.get("template", cfg.get("template"))
    if not bound:
        return
    changed = sorted(k for k in BOUND_FIELDS if k in changes and cfg.get(k) != changes[k])
    if changed:
        raise AgentValidationError(f"agent_bound_to_template:{','.join(changed)}")


def create_defaults(template_id: str) -> dict[str, Any]:
    """Werte für ein neues, gebundenes Agent-JSON (Pflichtfelder der alten Struktur, aus dem Template)."""
    from hydrahive.agents import templates as tpl
    check_template(template_id)
    t = tpl.get(template_id)
    chain = list(t["chain"])
    b = t["budget"]
    return {"llm_model": chain[0], "fallback_models": chain[1:], "max_tokens": b["max_tokens"],
            "max_iterations": b["max_iterations"], "handoff_timeout_seconds": b["timeout_seconds"],
            "reasoning_effort": b.get("reasoning_effort", ""), "compact_threshold_pct": b["compact_threshold_pct"],
            "cache_ttl": b.get("cache_ttl", "1h")}


def default_template_for(agent_type: str, name: str = "") -> str:
    """Standard-Template je Agent-Typ/Name (Zuordnungsregeln Plan E3). Spezialisten: siehe _migrate."""
    n = (name or "").lower()
    if agent_type == "master":
        return "assistant" if n.endswith("assistant") else "buddy"
    if agent_type == "project":
        return "projekt-master"
    if "hilfe" in n or "help" in n:
        return "hilfe"
    from hydrahive.agents.templates._migrate import specialist_template
    return specialist_template(n)


def template_if_available(template_id: str) -> str | None:
    """Template-ID, wenn es das Template mit nutzbarer Kette gibt, sonst None (Anlegen dann wie bisher)."""
    from hydrahive.agents import templates as tpl
    try:
        t = tpl.get(template_id)
    except Exception:  # Template-Datei kaputt: Anlegen darf daran nicht scheitern
        return None
    return template_id if t and t.get("chain") else None
