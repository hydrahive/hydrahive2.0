"""Systemrollen (Kompaktierung, Zahnfee, Lehren, Karten, Hilfe) an Templates (Spec agent-templates.md Kap. 7).

`system_chain(role, fallback)`: Kette des Templates; gibt es kein nutzbares Template, die bisherige Einstellung
(`fallback`) als Einzelkette – damit verhält sich eine Installation ohne Template-Datei exakt wie vorher.

`complete_with_chain(...)`: einfacher Text-Aufruf über die Kette, mit denselben Wechselgründen wie der Chat
(`runner/_failover.classify`): Anbieterfehler, Timeout, Verbindungsabbruch und leere Antwort.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def system_chain(role: str, fallback: str | None = None) -> list[str]:
    from hydrahive.agents.templates import resolve_role
    try:
        t = resolve_role(role)
    except Exception as exc:  # Template-Datei kaputt: Systemrolle muss trotzdem laufen
        logger.warning("Template für Systemrolle %s nicht lesbar: %s", role, exc)
        t = None
    if t is not None and t.id == role and t.chain:
        return list(t.chain)
    return [fallback] if fallback else []


async def complete_with_chain(chain: list[str], messages: list[dict], **kw) -> str:
    """Wie `llm.client.complete`, aber über die Kette. Leere Kette → bisheriges Standardmodell."""
    from hydrahive.llm import client
    from hydrahive.runner import _model_cooldown as cooldown
    from hydrahive.runner._failover import PROVIDER_CATEGORIES, SWITCH_CATEGORIES, classify
    if not chain:
        return await client.complete(messages, model=None, **kw)
    models, _ = cooldown.available(chain)
    last: Exception | None = None
    for i, model in enumerate(models):
        has_next = i < len(models) - 1
        try:
            text = await client.complete(messages, model=model, **kw)
        except Exception as exc:
            reason = classify(exc)
            if not has_next or reason not in SWITCH_CATEGORIES:
                raise
            if reason in PROVIDER_CATEGORIES:
                cooldown.mark_down(model, cooldown.DEFAULT_COOLDOWN_SECONDS)
            logger.warning("System-Kette: %s → %s wegen %s", model, models[i + 1], reason)
            last = exc
            continue
        if (text or "").strip() or not has_next:
            return text
        logger.warning("System-Kette: leere Antwort von %s → %s", model, models[i + 1])
    raise last or RuntimeError("Alle Modelle der Kette fehlgeschlagen")
