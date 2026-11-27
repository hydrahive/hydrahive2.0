"""Zuweisung von Tools/Skills in ask_agent (Katalog Etappe 5, Spec E1/D2/S3/S5, K5).

Zuweisung = Anfrage ∩ Freigabe-Pool des ZIELS (``agents/tool_pools.tool_pool_for``). Sie kommt zu den eigenen Tools des Ziels
dazu und gilt nur für diesen Auftrag (``agentlink/runtime_profiles`` trägt sie im signierten reason, der Runner liest sie
aus ``runner/_assigned_tools``). Außerhalb des Pools → Fehler mit Grund; nie zuweisbar: Authoring, ask_agent, Katalog-Werkzeuge.
Föderierte Ziele (``persona@workstation``) nehmen keine Zuweisung an: die Gegenstelle entscheidet über ihre Werkzeuge.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MAX_ASSIGNED = 40

FEDERATED_REFUSAL = ("Föderierte Ziele (name@server) nehmen keine Zuweisung von tools/skills an – die Gegenstelle "
                     "entscheidet über ihre eigenen Werkzeuge und Skills.")


def wants_assignment(args: dict) -> bool:
    return bool(args.get("tools") or args.get("skills"))


def _names(value: object, field: str) -> tuple[list[str], str | None]:
    if value is None:
        return [], None
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        return [], f"{field} muss eine Liste von Namen sein."
    return list(dict.fromkeys(v.strip() for v in value)), None


def _project_of(target_agent: dict) -> dict | None:
    pid = target_agent.get("project_id")
    if not pid:
        return None
    from hydrahive.projects import config as project_config
    return project_config.get(pid)


def resolve_assignment(args: dict, target_agent: dict, run_user: str) -> tuple[str | None, list[str], list[str]]:
    """(Fehlertext | None, Tool-Namen, Skill-Namen). Ohne ``tools``/``skills`` im Auftrag: (None, [], []) wie heute."""
    tools, err = _names(args.get("tools"), "tools")
    if err:
        return err, [], []
    skills, err = _names(args.get("skills"), "skills")
    if err:
        return err, [], []
    if not tools and not skills:
        return None, [], []

    accepted_tools: list[str] = []
    if tools:
        from hydrahive.agents.tool_pools import FORBIDDEN, tool_pool_for
        from hydrahive.catalog.categories import CATEGORY_MAP, PREFIX, resolve_categories
        pool = tool_pool_for(target_agent, _project_of(target_agent))
        never: list[str] = []
        outside: list[str] = []
        for item in tools:
            if item in FORBIDDEN:
                never.append(item)
            elif item.startswith(PREFIX) and item[len(PREFIX):] not in CATEGORY_MAP:
                outside.append(item)
            else:
                for name in resolve_categories([item]):
                    if name in pool:
                        accepted_tools.append(name)
                    else:
                        outside.append(name)
                if item.startswith(PREFIX) and not resolve_categories([item]):
                    outside.append(item)
        if never or outside:
            parts = []
            if never:
                parts.append(f"nie zuweisbar (Authoring, ask_agent, Katalog-Werkzeuge): {', '.join(never)}")
            if outside:
                parts.append(f"nicht im Freigabe-Pool von '{target_agent.get('name') or target_agent.get('id')}': "
                             f"{', '.join(dict.fromkeys(outside))}")
            return ("Zuweisung abgelehnt – " + "; ".join(parts) + f". Im Freigabe-Pool: {', '.join(pool) or '(leer)'}. "
                    "Den Pool legt der Besitzer des Agenten fest."), [], []
        accepted_tools = list(dict.fromkeys(accepted_tools))

    accepted_skills: list[str] = []
    if skills:
        from hydrahive.skills import list_for_agent
        owner = target_agent.get("owner") or run_user
        visible = {s.name for s in list_for_agent(
            target_agent["id"], owner, disabled=list(target_agent.get("disabled_skills") or []),
            project_id=target_agent.get("project_id"))}
        missing = [s for s in skills if s not in visible]
        if missing:
            return (f"Zuweisung abgelehnt – Skill nicht gefunden oder für '{target_agent.get('name') or target_agent['id']}' "
                    f"nicht sichtbar: {', '.join(missing)}."), [], []
        accepted_skills = skills

    if len(accepted_tools) + len(accepted_skills) > MAX_ASSIGNED:
        return f"Zuweisung abgelehnt – höchstens {MAX_ASSIGNED} Tools und Skills je Auftrag.", [], []
    return None, accepted_tools, accepted_skills
