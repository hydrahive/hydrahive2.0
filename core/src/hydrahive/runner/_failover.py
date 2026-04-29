"""LLM-Failover-Erkennung — bei Quota/Overload/Auth-Fehlern Modell wechseln.

Signal-Liste aus altem HydraHive (`orchestrator_llm.py`). Pragmatischer
Substring-Match auf `str(exc).lower()` — Provider-Fehlertexte sind
relativ stabil, exotische Edge-Cases nehmen wir in Kauf.
"""
from __future__ import annotations

_FAILOVER_SIGNALS = [
    "401", "authentication_error", "expired", "oauth token has expired",
    "invalid api key", "invalid x-api-key", "unauthorized",
    "402", "payment", "credit", "quota", "insufficient",
    "429", "rate_limit", "rate limit",
    "529", "overloaded", "capacity", "credit_balance",
    "your credit balance is too low",
    "exceeded your current quota",
    "this request would exceed",
    "billing",
]


def should_failover(exc: Exception) -> bool:
    """True wenn der Fehler einen Modellwechsel rechtfertigt."""
    err = str(exc).lower()
    return any(s in err for s in _FAILOVER_SIGNALS)
