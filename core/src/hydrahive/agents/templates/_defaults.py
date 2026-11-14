"""Start-Templates (Spec agent-templates.md 6.1, Entscheidung Till 14.11.2026).

Primär je Rolle, Failover für alle ChatGPT bzw. Sonnet (jeweils der ANDERE Anbieter als Primär),
Notfall für alle MiniMax M3.1. Es werden nur Modelle eingetragen, die der Katalog kennt; fehlt eines,
bleibt die Stufe leer und die Ampel zeigt das. Budgetwerte sind Startwerte, änderbar auf der Seite.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Bevorzugte IDs je Modellfamilie, erste verfügbare gewinnt.
_FAMILY: dict[str, tuple[str, ...]] = {
    "opus": ("claude-opus-5-5", "claude-opus-5", "claude-opus-4-8"),
    "sonnet": ("claude-sonnet-5", "claude-sonnet-4-6", "claude-sonnet-4-5"),
    "fable": ("claude-fable-5-1", "claude-fable-5"),
    "chatgpt": ("openai-codex/gpt-5.6-terra", "openai-codex/gpt-5.6-sol", "openai-codex/gpt-5.5"),
    "minimax": ("MiniMax-M3.1-Flash", "MiniMax-M3", "openrouter/minimax/minimax-m3:free"),
}

# id: (label, group, primär-familie, budget, extras)
_ROLES: dict[str, tuple[str, str, str, dict, dict]] = {
    "buddy": ("Buddy", "personal", "sonnet", {"max_iterations": 30, "timeout_seconds": 600}, {}),
    "assistant": ("Assistant", "personal", "sonnet", {"max_iterations": 30, "timeout_seconds": 600}, {}),
    "projekt-master": ("Projekt-Master", "projects", "opus",
                       {"max_iterations": 60, "max_tokens": 32_768, "timeout_seconds": 1_200,
                        "reasoning_effort": "high"}, {}),
    "reviewer": ("Reviewer", "specialists", "opus",
                 {"max_iterations": 96, "max_tokens": 32_768, "timeout_seconds": 1_800}, {}),
    "security": ("Security", "specialists", "fable",
                 {"max_iterations": 96, "max_tokens": 32_768, "timeout_seconds": 1_800}, {"on_demand": True}),
    "backend": ("Backend", "specialists", "sonnet",
                {"max_iterations": 96, "max_tokens": 32_768, "timeout_seconds": 1_800}, {}),
    "frontend": ("Frontend", "specialists", "sonnet",
                 {"max_iterations": 96, "max_tokens": 32_768, "timeout_seconds": 1_800}, {}),
    "recherche": ("Recherche", "specialists", "sonnet", {"max_iterations": 32, "timeout_seconds": 900}, {}),
    "klein": ("Klein & schnell", "specialists", "sonnet",
              {"max_iterations": 8, "max_tokens": 8_192, "timeout_seconds": 180}, {}),
    "modul-schreiber": ("Modul-Schreiber", "modules", "sonnet", {"max_tokens": 32_768}, {}),
    "modul-schnell": ("Modul-Schnell", "modules", "sonnet", {"max_tokens": 8_192}, {}),
    "zahnfee": ("Zahnfee", "system", "sonnet", {"max_iterations": 30, "timeout_seconds": 1_800}, {}),
    "kompaktierung": ("Kompaktierung", "system", "sonnet", {"max_tokens": 16_384}, {}),
    "lehren": ("Lehren & Karten", "system", "sonnet", {"max_tokens": 8_192}, {}),
    "hilfe": ("Hilfe", "system", "sonnet", {"max_iterations": 8, "timeout_seconds": 300}, {}),
}


def _catalog_ids() -> set[str]:
    """Bekannte Modell-IDs (Registry-Cache, sonst eingebauter Katalog). Nie ein Netzwerkaufruf."""
    try:
        from hydrahive.llm import registry
        known = registry.known_ids()
        if known:
            return set(known)
    except Exception as exc:  # Start darf nie an der Registry scheitern
        logger.warning("Registry für Start-Templates nicht verfügbar: %s", exc)
    from hydrahive.llm import _catalog_data
    ids: set[str] = set()
    for value in vars(_catalog_data).values():
        if isinstance(value, dict):
            ids.update(k for k in value if isinstance(k, str))
        elif isinstance(value, (list, tuple)):
            ids.update(v for v in value if isinstance(v, str))
    return ids


def _pick(family: str, known: set[str]) -> str:
    return next((m for m in _FAMILY[family] if m in known), "")


def build(known: set[str] | None = None) -> dict[str, dict]:
    """Start-Templates als {id: rohe Daten} (noch nicht normalisiert)."""
    known = _catalog_ids() if known is None else known
    out: dict[str, dict] = {}
    for tid, (label, group, primary, budget, extras) in _ROLES.items():
        first = _pick(primary, known)
        second = _pick("sonnet" if primary == "chatgpt" else "chatgpt", known)
        chain = [m for m in dict.fromkeys([first, second, _pick("minimax", known)]) if m]
        out[tid] = {"label": label, "group": group, "chain": chain, "budget": dict(budget), **extras}
    return out
