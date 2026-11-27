"""Zuweisung aus einem ask_agent-Auftrag im Lauf des Unteragenten (Katalog Etappe 5, Spec E1/D2/S3/E4).

Der Auftraggeber hat die Zuweisung geprüft (``tools/_ask_agent_assign``) und im signierten reason mitgegeben;
``runner/_handoff_setup`` legt sie in ``session.metadata`` ab. Hier wird sie beim Laufstart gelesen und NOCH EINMAL gegen den
Pool geschnitten (Pool/Besitzer-Freigabe können sich seit dem Auftrag geändert haben). Sie wirkt nur in Läufen mit der Herkunft
``handoff`` (der Auftrag selbst), nie in Chat-Läufen derselben Sitzung, und kommt zu den eigenen Tools DAZU (Spec D2).
Gelesen wird einmal je Lauf – die Tool-Liste bleibt im Lauf byte-gleich (E4).
"""
from __future__ import annotations

METADATA_TOOLS = "assigned_tools"
METADATA_SKILLS = "assigned_skills"


def assigned_for_run(session, agent: dict, project: dict | None, origin) -> list[str]:
    """Zugewiesene Tool-Namen für diesen Lauf (geprüft gegen den aktuellen Pool des Agenten), sonst []."""
    if getattr(origin, "kind", None) != "handoff":
        return []
    raw = (getattr(session, "metadata", None) or {}).get(METADATA_TOOLS)
    if not isinstance(raw, list) or not raw:
        return []
    from hydrahive.agents.tool_pools import FORBIDDEN, tool_pool_for
    allowed = set(tool_pool_for(agent, project))
    return [n for n in dict.fromkeys(raw) if isinstance(n, str) and n in allowed and n not in FORBIDDEN]


def assigned_skills_for_run(session, origin) -> list[str]:
    if getattr(origin, "kind", None) != "handoff":
        return []
    raw = (getattr(session, "metadata", None) or {}).get(METADATA_SKILLS)
    return [s for s in raw if isinstance(s, str)] if isinstance(raw, list) else []
