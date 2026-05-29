"""Orchestriert externe Instanzen als Einheit: dedizierter User + Agent
(`external=true`) + API-Key (für diesen User). Keine eigene Tabelle — der
external-Marker am Agent ist die Einheit; Liste/Status werden abgeleitet."""
from __future__ import annotations

import secrets

from hydrahive.agents import config as agent_config
from hydrahive.agents._defaults import DEFAULT_MAX_TOKENS
from hydrahive.api.middleware import api_keys, users
from hydrahive.db import sessions as sessions_db, token_stats


def create_instance(name: str, llm_model: str) -> dict:
    """Legt User + external-Agent + API-Key an. Gibt den Key einmalig zurück.
    Rollt bei Teilfehler das bereits Angelegte zurück."""
    users.create(name, secrets.token_urlsafe(24), role="user")  # ValueError wenn User existiert
    try:
        agent = agent_config.create(
            agent_type="master", name=name, llm_model=llm_model, owner=name,
            external=True, temperature=0.7, max_tokens=DEFAULT_MAX_TOKENS, thinking_budget=0,
        )
    except Exception:
        users.delete(name)
        raise
    try:
        key = api_keys.create(name=f"{name}-hook", username=name, role="user")
    except Exception:
        agent_config.delete(agent["id"])
        users.delete(name)
        raise
    return {"username": name, "agent_id": agent["id"], "api_key": key}


def list_instances() -> list[dict]:
    out: list[dict] = []
    for a in agent_config.list_all():
        if not a.get("external"):
            continue
        owner = a.get("owner")
        keys = api_keys.list_keys(username=owner) if owner else []
        stats = token_stats.agent_stats(a["id"])
        recent = sessions_db.list_for_agent(a["id"], limit=1)
        out.append({
            "agent_id": a["id"],
            "name": a.get("name"),
            "username": owner,
            "key_count": len(keys),
            "session_count": stats.get("session_count", 0),
            "last_activity": recent[0].updated_at if recent else None,
        })
    return out


def _owner_is_dedicated(owner: str) -> bool:
    """Owner-User nur dann mitlöschen, wenn er eine dedizierte Instanz-Identität
    ist: Rolle 'user' UND besitzt keine weiteren Agenten. Schützt admin und
    geteilte User davor, beim Löschen einer Instanz mitgelöscht zu werden.
    Nach agent_config.delete() aufrufen — dann zählt der gelöschte Agent nicht mehr."""
    role = next((u["role"] for u in users.list_users() if u["username"] == owner), None)
    if role != "user":
        return False
    return not agent_config.list_by_owner(owner)


def delete_instance(agent_id: str) -> bool:
    a = agent_config.get(agent_id)
    if not a or not a.get("external"):
        return False
    owner = a.get("owner")
    agent_config.delete(agent_id)
    if owner and _owner_is_dedicated(owner):
        for k in api_keys.list_keys(username=owner):
            api_keys.delete(k["id"])
        users.delete(owner)
    return True


def rotate_key(agent_id: str) -> str | None:
    a = agent_config.get(agent_id)
    if not a or not a.get("external"):
        return None
    owner = a.get("owner")
    if not owner:
        return None
    # Erst neuen Key erzeugen, DANN alte löschen — sonst stünde die Instanz bei
    # einem Fehler nach dem Löschen ohne Key da (ausgesperrt).
    old = api_keys.list_keys(username=owner)
    new_key = api_keys.create(name=f"{a.get('name')}-hook", username=owner, role="user")
    for k in old:
        api_keys.delete(k["id"])
    return new_key
