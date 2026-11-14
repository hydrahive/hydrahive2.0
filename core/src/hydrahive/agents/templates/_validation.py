"""Prüfung und Normalisierung eines Agenten-Templates (Spec agent-templates.md Kap. 6).

Grenzen entsprechen den bisherigen Agenten-Grenzen (agents/_validation.py), damit eine Migration keine
Werte verliert. Fehler tragen einen festen Code (für i18n im Frontend), nie freien Text.
"""
from __future__ import annotations

import re
from typing import Any

GROUPS = ("personal", "projects", "specialists", "modules", "system")
EFFORTS = ("", "low", "medium", "high", "xhigh", "max", "ultra")
CACHE_TTLS = ("5m", "1h")
FAILOVER_ON = ("auth", "quota", "rate_limit", "overload", "timeout", "stream_abort", "empty")
FULL_REPORT = ("file", "inline")
MAX_CHAIN = 3

_ID = re.compile(r"^[a-z][a-z0-9-]{1,40}$")

# Feld: (Standard, Minimum, Maximum)
_BUDGET_INT: dict[str, tuple[int, int, int]] = {
    "max_iterations": (32, 1, 250),
    "max_tokens": (16_384, 1, 200_000),
    "timeout_seconds": (540, 30, 3_600),
    "compact_threshold_pct": (75, 30, 100),
    "overrun_pct": (20, 0, 100),
    "cooldown_seconds": (300, 0, 3_600),
}
_REPLY_INT: dict[str, tuple[int, int, int]] = {"summary_max_chars": (2_000, 200, 20_000)}


class TemplateError(ValueError):
    """Ungültiges Template. `code` ist ein fester Fehlercode."""

    def __init__(self, code: str, field: str = "") -> None:
        super().__init__(code if not field else f"{code}:{field}")
        self.code = code
        self.field = field


def check_id(template_id: str) -> str:
    if not isinstance(template_id, str) or not _ID.match(template_id):
        raise TemplateError("template_id_invalid")
    return template_id


def _ints(raw: dict, spec: dict[str, tuple[int, int, int]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for key, (default, lo, hi) in spec.items():
        value = raw.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
            raise TemplateError("budget_out_of_range", key)
        out[key] = value
    return out


def _chain(raw: Any) -> list[str]:
    if not isinstance(raw, list) or not raw:
        raise TemplateError("chain_empty")
    if len(raw) > MAX_CHAIN:
        raise TemplateError("chain_too_long")
    chain = [m.strip() if isinstance(m, str) else "" for m in raw]
    if any(not m for m in chain):
        raise TemplateError("chain_entry_empty")
    if len(set(chain)) != len(chain):
        raise TemplateError("chain_duplicate")
    return chain


def normalize(data: dict) -> dict:
    """Geprüfte, vollständige Fassung (ohne id/revision/updated_*). Wirft TemplateError."""
    if not isinstance(data, dict):
        raise TemplateError("template_invalid")
    label = str(data.get("label") or "").strip()
    if not label or len(label) > 80:
        raise TemplateError("label_invalid")
    group = data.get("group") or "specialists"
    if group not in GROUPS:
        raise TemplateError("group_invalid")

    raw_budget = data.get("budget") or {}
    if not isinstance(raw_budget, dict):
        raise TemplateError("budget_out_of_range")
    budget: dict[str, Any] = _ints(raw_budget, _BUDGET_INT)
    effort = raw_budget.get("reasoning_effort", "") or ""
    if effort not in EFFORTS:
        raise TemplateError("reasoning_effort_invalid")
    ttl = raw_budget.get("cache_ttl", "1h") or "1h"
    if ttl not in CACHE_TTLS:
        raise TemplateError("cache_ttl_invalid")
    budget["reasoning_effort"] = effort
    budget["cache_ttl"] = ttl

    raw_reply = data.get("reply") or {}
    reply: dict[str, Any] = _ints(raw_reply, _REPLY_INT)
    full = raw_reply.get("full_report", "file")
    if full not in FULL_REPORT:
        raise TemplateError("full_report_invalid")
    reply["full_report"] = full

    failover_on = data.get("failover_on", list(FAILOVER_ON))
    if not isinstance(failover_on, list) or any(f not in FAILOVER_ON for f in failover_on):
        raise TemplateError("failover_on_invalid")

    return {
        "label": label, "group": group, "chain": _chain(data.get("chain")),
        "failover_on": list(dict.fromkeys(failover_on)), "budget": budget, "reply": reply,
        "on_demand": bool(data.get("on_demand", False)),
        "description": str(data.get("description") or "")[:500],
    }
