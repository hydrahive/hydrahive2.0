"""Laufzeitwerte eines Agenten bestimmen – aus dem Template oder (Altbestand) aus der Agent-Config.

Spec agent-templates.md Kap. 7. Agenten mit `template` nehmen Kette, Budget, Denktiefe, Kompaktierung und
Cache-Dauer aus dem Template. Agenten ohne `template` verhalten sich exakt wie vorher, bis die Migration (E3)
durch ist. Ein Modell, das der Nutzer im Chat bewusst für die Sitzung wählt (`model_override`), hat weiter Vorrang
als Primärmodell; die Kette des Templates bleibt als Failover dahinter.
"""
from __future__ import annotations

from dataclasses import dataclass

from hydrahive.agents._defaults import DEFAULT_COMPACT_THRESHOLD_PCT, DEFAULT_MAX_ITERATIONS, DEFAULT_MAX_TOKENS
from hydrahive.agents.templates import resolve
from hydrahive.runner._model_cooldown import DEFAULT_COOLDOWN_SECONDS


@dataclass(frozen=True)
class RunSettings:
    template_id: str | None
    primary_model: str
    fallback_models: list[str]
    compact_model: str
    compact_threshold_pct: int
    cache_ttl: str
    reasoning_effort: str | None
    max_iterations: int
    max_tokens: int
    cooldown_seconds: int


def run_settings(agent: dict, *, session_budget=None) -> RunSettings:
    """`session_budget`: Budget einer delegierten Sitzung (AgentLink), sonst None."""
    t = resolve(agent)
    if t is not None:
        iterations, tokens = t.max_iterations, t.max_tokens
        if session_budget is not None:
            iterations, tokens = session_budget.max_iterations, session_budget.max_tokens
        return RunSettings(
            template_id=t.id, primary_model=t.chain[0], fallback_models=list(t.chain[1:]),
            compact_model=agent.get("compact_model") or t.chain[0],
            compact_threshold_pct=t.compact_threshold_pct, cache_ttl=t.cache_ttl,
            reasoning_effort=t.reasoning_effort or None, max_iterations=iterations, max_tokens=tokens,
            cooldown_seconds=t.cooldown_seconds,
        )
    if session_budget is not None:
        iterations, tokens = session_budget.max_iterations, session_budget.max_tokens
    else:
        iterations = int(agent.get("max_iterations") or DEFAULT_MAX_ITERATIONS)
        tokens = int(agent.get("max_tokens") or DEFAULT_MAX_TOKENS)
    model = agent.get("llm_model") or ""
    return RunSettings(
        template_id=None, primary_model=model,
        fallback_models=list(agent.get("fallback_models", []) or []),
        compact_model=agent.get("compact_model") or model,
        compact_threshold_pct=int(agent.get("compact_threshold_pct", DEFAULT_COMPACT_THRESHOLD_PCT)),
        cache_ttl=agent.get("cache_ttl") or "1h", reasoning_effort=agent.get("reasoning_effort") or None,
        max_iterations=iterations, max_tokens=tokens, cooldown_seconds=DEFAULT_COOLDOWN_SECONDS,
    )


def chain_with_override(rs: RunSettings, override: str | None) -> tuple[str, list[str]]:
    """Primärmodell + Failover; ein Sitzungs-Override setzt sich vor die Kette (ohne Duplikat)."""
    if not override or override == rs.primary_model:
        return rs.primary_model, list(rs.fallback_models)
    rest = [m for m in [rs.primary_model, *rs.fallback_models] if m != override]
    return override, rest if rs.template_id else list(rs.fallback_models)
