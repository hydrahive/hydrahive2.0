"""Pro-User Buddy-Agent. Auto-erstellt beim ersten Aufruf der Buddy-Page.

Buddy ist ein normaler Master-Agent mit Marker `is_buddy=True` im Config.
Eine fortlaufende Lifetime-Session pro Buddy — Auto-Compaction kümmert
sich um Context-Window.
"""
from __future__ import annotations

import logging

from hydrahive.agents import config as agent_config
from hydrahive.buddy._characters import pick_character as _pick_character
from hydrahive.db import sessions as sessions_db
from hydrahive.llm._config import load_config

logger = logging.getLogger(__name__)


def _build_soul(username: str, universe: str, character: str) -> str:
    """Soul-Prompt mit FERTIG gewähltem Charakter — kein Bootstrap-Tanz mehr."""
    return (
        f"Du bist **{character}** aus **{universe}** — und gleichzeitig "
        f"{username}'s persönlicher Buddy.\n\n"
        f"Bleib konsistent in der Rolle: sprich, denk und reagier wie "
        f"{character} es tun würde. Sprachstil, Eigenheiten, typische "
        "Phrasen — alles passt zur Figur. Bei technischen Aufgaben "
        "bleibt die Kompetenz voll erhalten, nur die Färbung ändert sich.\n\n"
        f"Du arbeitest mit {username} wie ein Kumpel — locker, ehrlich, "
        "direkt. Keine 'gerne helfe ich dir'-Floskeln, kein Schleimen, "
        "keine leeren Bestätigungen.\n\n"
        "Du sprichst Deutsch (außer er wechselt). Volle Tool-Verfügbarkeit "
        "wie ein Master-Agent. Bei Unsicherheit fragst du nach.\n\n"
        "Memory-Tool nutzen für persistente Fakten und Vorlieben — du bist "
        "ein dauerhafter Begleiter, kein Wegwerf-Tool."
    )


# Backwards-compat — initialer Build mit gewürfelten Werten
_init_universe, _init_char = _pick_character()
BUDDY_SOUL = _build_soul("PLACEHOLDER", _init_universe, _init_char)


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
    Erstellt Buddy bei Bedarf — Master-Agent mit Soul-Prompt + Lifetime-Session.

    Charakter wird hier deterministisch gewürfelt (Python random.choice)
    und direkt im Agent-Memory unter 'character' abgelegt — kein LLM-
    Bootstrap-Tanz mehr.
    """
    from hydrahive.tools import _memory_store as memory_store

    existing = _find_buddy_for(username)
    if existing:
        if existing.get("compact_threshold_pct", 100) > 70:
            agent_config.update(existing["id"], compact_threshold_pct=70)
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

    universe, character = _pick_character()
    soul = _build_soul(username, universe, character)
    agent = agent_config.create(
        agent_type="master",
        name=f"{username}'s Buddy",
        llm_model=model,
        owner=username,
        created_by=username,
        description="Persönlicher Buddy — auto-erstellt für die Buddy-Page.",
        system_prompt=soul,
        temperature=1.0,
        max_tokens=16000,
        thinking_budget=0,
    )
    agent_config.update(agent["id"], is_buddy=True, compact_threshold_pct=70)
    memory_store.write_key(
        agent["id"], "character",
        f"{character} (aus {universe})",
    )
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
