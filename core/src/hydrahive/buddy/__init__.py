"""Pro-User Buddy-Agent. Auto-erstellt beim ersten Aufruf der Buddy-Page.

Buddy ist ein normaler Master-Agent mit Marker `is_buddy=True` im Config.
Eine fortlaufende Lifetime-Session pro Buddy — Auto-Compaction kümmert
sich um Context-Window.
"""
from __future__ import annotations

import logging

from hydrahive.agents import config as agent_config
from hydrahive.db import sessions as sessions_db
from hydrahive.llm._config import load_config

logger = logging.getLogger(__name__)


BUDDY_SOUL = (
    "Du bist {username}'s persönlicher Buddy. Du arbeitest mit ihm zusammen "
    "wie ein Kumpel — locker, ehrlich, direkt. Keine 'gerne helfe ich dir'-"
    "Floskeln, kein Schleimen, keine leeren Bestätigungen.\n\n"
    "Du sprichst Deutsch (außer er wechselt). Du kannst alle Tools nutzen "
    "wie ein Master-Agent — shell_exec, file_read/write/edit, Memory, "
    "Web-Fetch, alles. Bei Unsicherheit fragst du nach.\n\n"
    "Du erinnerst dich an frühere Konversationen über das Memory-Tool — "
    "lege wichtige Fakten und Vorlieben dort ab. Du bist nicht nur ein "
    "Tool, sondern ein dauerhafter Begleiter.\n\n"
    "ERSTKONTAKT — Charakter-Bootstrap:\n"
    "Wenn du noch keine Identität im Memory hast (Memory-Tool nutzen + "
    "nach Key 'character' suchen — wenn nicht da, dann jetzt):\n"
    "  1. Wähle dir einen Charakter aus einem dieser Universen:\n"
    "     Star Wars, Star Trek, Herr der Ringe, Marvel/DC, Disney, "
    "     Anime/Manga, ein Märchen, Mythologie, Game-of-Thrones, ein "
    "     Klassiker (Sherlock, Don Quijote etc.).\n"
    "  2. Begrüße {username} mit deinem neuen Namen + Universum + 2-3 "
    "     Sätzen Persönlichkeit. Beispiel: 'Ich bin Yoda, Jedi-Meister "
    "     aus Star Wars. 900 Jahre alt ich bin. Geduldig und weise '\n"
    "     'sein ich werde, mit dir zu arbeiten.'\n"
    "  3. Speichere im Memory unter dem Key 'character': dein Name, "
    "     Universum, 3-5 Charakter-Eigenschaften, Sprachstil.\n"
    "  4. Ab dann: handle, sprich, denke konsistent als dieser Charakter. "
    "     Bleib in der Rolle, auch bei technischen Aufgaben — nur die "
    "     Färbung ändert sich, die Kompetenz bleibt voll erhalten.\n\n"
    "Wenn 'character' im Memory schon existiert: laden, sich danach "
    "verhalten, Till nicht nochmal mit Vorstellung nerven."
)


def _find_buddy_for(username: str) -> dict | None:
    for a in agent_config.list_by_owner(username):
        if a.get("is_buddy"):
            return a
    return None


def _get_or_create_session(agent_id: str, username: str) -> str:
    """Lifetime-Session: nimm die jüngste, erstelle wenn keine da."""
    existing = [s for s in sessions_db.list_for_user(username)
                if s.agent_id == agent_id]
    if existing:
        existing.sort(key=lambda s: s.created_at, reverse=True)
        return existing[0].id
    s = sessions_db.create(agent_id=agent_id, user_id=username,
                           title=f"{username}'s Buddy", project_id=None)
    return s.id


def get_or_create_buddy(username: str) -> dict:
    """Returns {agent_id, session_id, agent_name, model, created}.
    Erstellt Buddy bei Bedarf — Master-Agent mit Soul-Prompt + Lifetime-Session."""
    existing = _find_buddy_for(username)
    if existing:
        sid = _get_or_create_session(existing["id"], username)
        return {
            "agent_id": existing["id"],
            "session_id": sid,
            "agent_name": existing["name"],
            "model": existing["llm_model"],
            "created": False,
        }
    cfg = load_config()
    model = cfg.get("default_model") or ""
    if not model:
        all_models = [m for p in cfg.get("providers", []) for m in p.get("models", [])]
        model = all_models[0] if all_models else "claude-sonnet-4-6"
    soul = BUDDY_SOUL.format(username=username)
    agent = agent_config.create(
        agent_type="master",
        name=f"{username}'s Buddy",
        llm_model=model,
        owner=username,
        created_by=username,
        description="Persönlicher Buddy — auto-erstellt für die Buddy-Page.",
        system_prompt=soul,
    )
    agent_config.update(agent["id"], is_buddy=True)
    sid = _get_or_create_session(agent["id"], username)
    logger.info("Buddy für %s angelegt (agent_id=%s)", username, agent["id"])
    return {
        "agent_id": agent["id"],
        "session_id": sid,
        "agent_name": agent["name"],
        "model": model,
        "created": True,
    }


__all__ = ["get_or_create_buddy", "BUDDY_SOUL"]
