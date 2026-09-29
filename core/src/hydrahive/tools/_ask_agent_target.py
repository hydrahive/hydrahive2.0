"""Zielauflösung für ask_agent: nur Agenten, die der Besitzer des Laufs nutzen darf.

Ein interner Handoff läuft als Besitzer des ZIEL-Agenten
(runner/_handoff_setup._new_session), also mit dessen Werkzeugen, Gedächtnis,
Zugangsdaten und Freigaben. Deshalb gilt:

- Admin: alle Agenten
- sonst: nur eigene Agenten (owner == Besitzer des Laufs)

Das ist strenger als POST /api/sessions (#461). Dort läuft die Session als der
anfragende Nutzer, darum dürfen Projekt-Mitglieder dort das Projekt-Team nutzen.

Namen und Teilstrings werden nur unter den erlaubten Agenten aufgelöst und
müssen eindeutig sein. Passt der Text nur auf fremde Agenten, wird abgelehnt,
statt ihn als externes AgentLink-Ziel weiterzureichen.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TargetResolution:
    """agent gesetzt: internes Ziel. error gesetzt: abgelehnt.
    Beides None: kein interner Agent, also externes AgentLink-Ziel."""
    agent: dict | None = None
    error: str | None = None


def _denied(target: str) -> TargetResolution:
    # Eine Meldung für „gibt es nicht“ und „gehört jemand anderem“,
    # damit fremde Agenten nicht über die Fehlermeldung abfragbar sind.
    return TargetResolution(error=(
        f"Kein Zugriff auf Agent '{target}' (nicht gefunden oder gehört jemand anderem)."
    ))


def _pick(matches: list[dict], target: str) -> TargetResolution | None:
    if len(matches) == 1:
        return TargetResolution(agent=matches[0])
    if len(matches) > 1:
        choices = ", ".join(f"{a.get('name', '')} ({a['id']})" for a in matches[:10])
        return TargetResolution(
            error=f"Agent '{target}' ist mehrdeutig. Bitte per ID wählen: {choices}",
        )
    return None


def resolve_target(target: str, run_owner: str) -> TargetResolution:
    """Löst ``target`` für den Besitzer des Laufs (ToolContext.user_id) auf."""
    from hydrahive.agents import config as agent_config
    from hydrahive.api.middleware.users import get_by_username

    try:
        user = get_by_username(run_owner) if run_owner else None
        all_agents = agent_config.list_all()
        by_id = agent_config.get(target)
    except Exception:
        logger.exception("ask_agent: Ziel '%s' nicht auflösbar", target)
        return TargetResolution(error="Ziel-Agent konnte nicht sicher aufgelöst werden.")
    if user is None:
        return TargetResolution(error="Besitzer des Laufs unbekannt, ask_agent abgelehnt.")

    def allowed(agent: dict) -> bool:
        return user["role"] == "admin" or agent.get("owner") == user["username"]

    # Nur echte IDs zählen (kein Pfad-Trick wie "x/../<id>").
    if by_id is not None and by_id.get("id") == target:
        return TargetResolution(agent=by_id) if allowed(by_id) else _denied(target)

    needle = target.lower()
    mine = [a for a in all_agents if allowed(a)]
    exact = _pick([a for a in mine if a.get("name", "").lower() == needle], target)
    if exact:
        return exact
    partial = _pick([a for a in mine if needle in a.get("name", "").lower()], target)
    if partial:
        return partial
    if by_id is not None or any(needle in a.get("name", "").lower() for a in all_agents):
        return _denied(target)
    return TargetResolution()
