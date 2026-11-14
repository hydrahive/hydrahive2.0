"""Template zur Laufzeit auflösen (Spec agent-templates.md Kap. 7).

- Agent mit `template` → Werte aus dem Template.
- Agent ohne `template` → None (Aufrufer nutzt die alten Agent-Felder, bis die Migration E3 durch ist).
- Unbekanntes Template → Rückfall auf das System-Template `assistant` bzw. `buddy`, Warnung im Log, nie ein Fehler.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_FALLBACK_IDS = ("assistant", "buddy")


@dataclass(frozen=True)
class ResolvedTemplate:
    id: str
    chain: list[str]
    max_iterations: int
    max_tokens: int
    timeout_seconds: int
    reasoning_effort: str
    compact_threshold_pct: int
    cache_ttl: str
    overrun_pct: int
    cooldown_seconds: int
    summary_max_chars: int
    full_report: str
    on_demand: bool = False
    failover_on: list[str] = field(default_factory=list)


def _build(t: dict) -> ResolvedTemplate:
    b, r = t["budget"], t["reply"]
    return ResolvedTemplate(
        id=t["id"], chain=list(t["chain"]),
        max_iterations=b["max_iterations"], max_tokens=b["max_tokens"], timeout_seconds=b["timeout_seconds"],
        reasoning_effort=b.get("reasoning_effort", ""), compact_threshold_pct=b["compact_threshold_pct"],
        cache_ttl=b.get("cache_ttl", "1h"), overrun_pct=b["overrun_pct"], cooldown_seconds=b["cooldown_seconds"],
        summary_max_chars=r["summary_max_chars"], full_report=r.get("full_report", "file"),
        on_demand=bool(t.get("on_demand")), failover_on=list(t.get("failover_on") or []),
    )


def resolve_role(template_id: str) -> ResolvedTemplate | None:
    """Template per ID; unbekannt → Rückfall-Template mit Warnung; gar keins vorhanden → None."""
    from hydrahive.agents import templates as tpl
    t = tpl.get(template_id) if template_id else None
    if t is None:
        if template_id:
            logger.warning("Template '%s' unbekannt — Rückfall auf Standard-Template", template_id)
        t = next((x for x in (tpl.get(fid) for fid in _FALLBACK_IDS) if x), None)
    return _build(t) if t and t.get("chain") else None


def resolve(agent: dict) -> ResolvedTemplate | None:
    template_id = (agent or {}).get("template") or ""
    if not template_id:
        return None
    return resolve_role(template_id)
