"""Der Hauptagent eines Nutzers — Ziel für eingehende Kanäle.

WhatsApp, Discord, Mail und Voice sollen beim Buddy landen. Nutzer können neben
dem Buddy weitere Master-Agenten haben (z. B. den beim Anlegen erzeugten
„<user>'s Assistant“). Die Reihenfolge von `list_by_owner` hängt nur von der
Sortierung der Agenten-IDs ab und darf die Auswahl nicht bestimmen.
"""
from __future__ import annotations

from hydrahive.agents._config_utils import list_by_owner


def primary_agent_for(username: str) -> dict | None:
    """Aktiver Buddy des Nutzers, sonst der erste aktive Master, sonst None."""
    masters = [a for a in list_by_owner(username)
               if a.get("type") == "master" and a.get("status") != "disabled"]
    for agent in masters:
        if agent.get("is_buddy"):
            return agent
    return masters[0] if masters else None
