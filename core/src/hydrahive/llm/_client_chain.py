"""Text-LLM über eine Template-Kette (Plan E5, Spec agent-templates.md Kap. 3.2).

`complete(..., template="modul-schnell")` / `stream(..., template=…)`: Kette aus dem Template, Wechsel wie beim
Chat (`runner/_failover.classify`): Anbieterfehler, Timeout, Abbruch, leere Antwort. Beim Streaming wird nur
gewechselt, solange noch kein Text gesendet wurde. Unbekanntes Template → Standard-Template mit Warnung.
`model=` bleibt erlaubt (Rückwärtskompatibilität). Module erkennen die Fähigkeit an `SUPPORTS_TEMPLATE`.
"""
from __future__ import annotations

import logging
from typing import AsyncIterator

logger = logging.getLogger(__name__)

SUPPORTS_TEMPLATE = True


def _role_chain(template: str) -> list[str]:
    from hydrahive.agents.templates import resolve_role
    try:
        t = resolve_role(template)
    except Exception as exc:  # Template-Datei kaputt: Modul muss trotzdem antworten
        logger.warning("Template %s nicht lesbar: %s", template, exc)
        t = None
    return list(t.chain) if t is not None and t.chain else []


async def complete(
    messages: list[dict], model: str | None = None,
    temperature: float = 0.7, max_tokens: int = 4096, *, template: str | None = None,
) -> str:
    from hydrahive.llm import client
    chain = _role_chain(template) if template and not model else []
    if not chain:
        return await client._complete_one(messages, model=model, temperature=temperature, max_tokens=max_tokens)
    from hydrahive.runner import _model_cooldown as cooldown
    from hydrahive.runner._failover import PROVIDER_CATEGORIES, SWITCH_CATEGORIES, classify
    models, _ = cooldown.available(chain)
    last: Exception | None = None
    for i, target in enumerate(models):
        has_next = i < len(models) - 1
        try:
            text = await client._complete_one(messages, model=target, temperature=temperature, max_tokens=max_tokens)
        except Exception as exc:
            reason = classify(exc)
            if not has_next or reason not in SWITCH_CATEGORIES:
                raise
            if reason in PROVIDER_CATEGORIES:
                cooldown.mark_down(target, cooldown.DEFAULT_COOLDOWN_SECONDS)
            logger.warning("Template %s: %s → %s wegen %s", template, target, models[i + 1], reason)
            last = exc
            continue
        if (text or "").strip() or not has_next:
            return text
        logger.warning("Template %s: leere Antwort von %s → %s", template, target, models[i + 1])
    raise last or RuntimeError("Alle Modelle der Kette fehlgeschlagen")


async def stream(
    messages: list[dict], model: str | None = None,
    temperature: float = 0.7, max_tokens: int = 4096, *, template: str | None = None,
) -> AsyncIterator[str]:
    from hydrahive.llm import client
    chain = _role_chain(template) if template and not model else []
    if not chain:
        async for chunk in client._stream_one(messages, model=model, temperature=temperature, max_tokens=max_tokens):
            yield chunk
        return
    from hydrahive.runner import _model_cooldown as cooldown
    from hydrahive.runner._failover import PROVIDER_CATEGORIES, SWITCH_CATEGORIES, classify
    models, _ = cooldown.available(chain)
    for i, target in enumerate(models):
        has_next = i < len(models) - 1
        sent = False
        try:
            async for chunk in client._stream_one(messages, model=target, temperature=temperature,
                                                  max_tokens=max_tokens):
                if chunk:
                    sent = True
                yield chunk
        except Exception as exc:
            reason = classify(exc)
            if sent or not has_next or reason not in SWITCH_CATEGORIES:
                raise
            if reason in PROVIDER_CATEGORIES:
                cooldown.mark_down(target, cooldown.DEFAULT_COOLDOWN_SECONDS)
            logger.warning("Template %s (Stream): %s → %s wegen %s", template, target, models[i + 1], reason)
            continue
        if sent or not has_next:
            return
        logger.warning("Template %s (Stream): leere Antwort von %s → %s", template, target, models[i + 1])
