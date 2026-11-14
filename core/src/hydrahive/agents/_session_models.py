"""Welche Modelle darf man im Chat für eine Sitzung wählen? (Entscheidung Till 14.11.2026, Option B)

- Buddy: freie Wahl (wie bisher).
- Agent mit Template: nur die Modelle seiner Kette (Primär, Failover, Notfall). Man kann bei einem hakenden
  Anbieter umschalten, kommt aber nicht aus der Vorgabe des Admins heraus.
- Agent ohne Template (Altbestand): wie bisher frei.
"""
from __future__ import annotations


def allowed_session_models(agent: dict | None) -> list[str] | None:
    """Liste erlaubter Modelle; None = keine Einschränkung."""
    if not agent or agent.get("is_buddy") or not agent.get("template"):
        return None
    from hydrahive.agents.templates import resolve
    t = resolve(agent)
    return list(t.chain) if t else None


def is_allowed(agent: dict | None, model: str) -> bool:
    allowed = allowed_session_models(agent)
    return allowed is None or model in allowed
