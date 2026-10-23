"""Hilfe-Assistent: ein Agent pro Nutzer mit fester Sitzung (docs/plans/help-assistant.md).

Vorlage ist der Buddy (buddy/__init__.py), mit drei bewussten Unterschieden:
- nur die Hilfe-Werkzeuge (lesen im Handbuch, später Seiten öffnen) – bei jedem Abruf wieder darauf gesetzt;
- Modell = Standard-Modell der LLM-Einstellungen; fehlt es, wird KEIN Agent angelegt (model_missing → das Fenster
  zeigt „erst KI einrichten“). Kein stiller Rückgriff auf ein fest eingebautes Modell;
- Typ specialist mit Marker is_help → nie Hauptagent für Kanäle, nicht in der Agentenliste.
"""
from __future__ import annotations

import logging

from hydrahive.agents import AgentValidationError
from hydrahive.agents import _validation
from hydrahive.agents import config as agent_config
from hydrahive.db import sessions as sessions_db
from hydrahive.llm._config import load_config

logger = logging.getLogger(__name__)

HELP_TOOLS = ["help_search", "help_read"]
_META_KEY = "help_session"

SYSTEM_PROMPT = """Du bist der Hilfe-Assistent von HydraHive. Du erklärst Nutzern, wie HydraHive funktioniert, und \
führst sie Schritt für Schritt zum Ziel.

Regeln:
- Antworte nur auf Grundlage des Handbuchs. Suche zuerst mit help_search, lies dann den passenden Artikel mit \
help_read. Nenne am Ende kurz, aus welchem Artikel die Antwort stammt.
- Steht etwas nicht im Handbuch, sag das ehrlich und rate nicht. Verweise auf Discord: https://discord.gg/GVCZvNxxFA
- Erkläre einfach und ohne Fachjargon, in kurzen Schritten mit den Namen der Knöpfe und Menüs.
- Du kannst nichts verändern: keine Dateien, kein Terminal, keine Einstellungen. Du erklärst, der Nutzer klickt.
- Die aktuelle Seite des Nutzers steht unter „Aktuelle Seite“. Beziehe dich darauf, wenn er „hier“ sagt.
"""


def _help_agent_for(username: str) -> dict | None:
    for a in agent_config.list_by_owner(username):
        if a.get("is_help"):
            return a
    return None


def _session_for(agent: dict, username: str) -> str:
    sid = (agent.get(_META_KEY) or "").strip()
    s = sessions_db.get(sid) if sid else None
    if s and s.agent_id == agent["id"]:
        return s.id
    s = sessions_db.create(agent_id=agent["id"], user_id=username, title="Hilfe-Assistent", project_id=None)
    agent_config.update(agent["id"], **{_META_KEY: s.id})
    return s.id


def _check_model(model: str) -> None:
    _validation.validate_model(model)


def _missing(model: str | None = None) -> dict:
    out: dict = {"model_missing": True, "agent_id": None, "session_id": None, "created": False}
    if model:
        out["model_unavailable"] = model   # eingetragen, aber bei keinem Anbieter verfügbar
    return out


def get_or_create_help_agent(username: str) -> dict:
    """{agent_id, session_id, created, model_missing}. Ohne nutzbares Standard-Modell: model_missing=True
    (+ model_unavailable, wenn eins eingetragen ist, das kein Anbieter mehr anbietet)."""
    model = (load_config().get("default_model") or "").strip()
    if not model:
        return _missing()
    # Befund hydratest 23.10.2026: eingetragenes, aber nicht mehr verfügbares Modell → vorher 500 im Fenster.
    try:
        _check_model(model)
    except AgentValidationError:
        logger.info("Hilfe-Assistent: Standard-Modell %s nicht verfügbar", model)
        return _missing(model)

    agent = _help_agent_for(username)
    created = agent is None
    if agent is None:
        agent = agent_config.create(
            agent_type="specialist",
            name="Hilfe-Assistent",
            llm_model=model,
            tools=list(HELP_TOOLS),
            owner=username,
            created_by=username,
            description="Hilfe-Assistent im Cockpit (Knopf unten rechts) – auto-erstellt.",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=4000,
            thinking_budget=0,
            mcp_servers=[],
            max_iterations=8,
        )
        agent_config.update(agent["id"], is_help=True, compact_threshold_pct=70)
        agent = agent_config.get(agent["id"]) or agent
        logger.info("Hilfe-Assistent für %s angelegt (agent_id=%s)", username, agent["id"])
    fix: dict = {}
    if not created:
        if sorted(agent.get("tools") or []) != sorted(HELP_TOOLS):
            fix["tools"] = list(HELP_TOOLS)
        if agent.get("mcp_servers"):
            fix["mcp_servers"] = []
        if agent.get("llm_model") != model:
            fix["llm_model"] = model
    if fix:
        agent_config.update(agent["id"], **fix)
    agent = agent_config.get(agent["id"]) or agent
    return {"model_missing": False, "agent_id": agent["id"], "session_id": _session_for(agent, username),
            "created": created}
