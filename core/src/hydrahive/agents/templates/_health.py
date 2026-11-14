"""Ampel und Bindungen der Templates (Spec agent-templates.md Kap. 5, 10).

Ampel:
- green: alle Modelle der Kette sind bekannt und keines ist gerade gesperrt.
- yellow: Primärmodell gerade gesperrt (Failover aktiv) oder zwei Stufen beim selben Anbieter.
- red: ein Modell der Kette ist im Katalog unbekannt oder die Kette ist leer.
"""
from __future__ import annotations

from hydrahive.llm._pricing import provider_from_model


def _provider(model: str) -> str:
    if model.startswith("openai-codex/"):
        return "openai-codex"
    return provider_from_model(model)


def health(template: dict, known: set[str]) -> dict:
    from hydrahive.runner import _model_cooldown as cooldown
    chain = list(template.get("chain") or [])
    unknown = [m for m in chain if known and m not in known]
    providers = [_provider(m) for m in chain]
    same_provider = len(set(providers)) < len(providers)
    primary_down = bool(chain) and cooldown.is_down(chain[0])
    if not chain or unknown:
        state = "red"
    elif primary_down or same_provider:
        state = "yellow"
    else:
        state = "green"
    return {"state": state, "unknown_models": unknown, "same_provider": same_provider,
            "primary_down": primary_down, "providers": providers}


def bindings(agents: list[dict]) -> dict[str, list[dict]]:
    """{template_id: [kurze Agent-Infos]}; Agenten ohne Template unter "" (ungebunden)."""
    out: dict[str, list[dict]] = {}
    for a in agents:
        out.setdefault(a.get("template") or "", []).append({
            "id": a.get("id"), "name": a.get("name"), "type": a.get("type"), "owner": a.get("owner"),
            "managed_by": a.get("managed_by") or None, "llm_model": a.get("llm_model") or "",
        })
    return out
