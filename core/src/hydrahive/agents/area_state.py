"""Bereichs-Status und Umschalten (docs/specs/agent-bereiche.md 4.2/4.3, Review #789 M6).

Bereiche sind nur eine SICHT auf ``agent.tools`` (E1): Nichts hier speichert ``bereich:x``, und nichts hier schreibt in einen
Agenten. ``toggle`` ist rein funktional (das Frontend spiegelt es und speichert über das bestehende ``PATCH /api/agents/{id}``,
nur Admin, Spec 4.8). Aufgelöst wird immer über ``_area_registry`` (Kern-, Modul- und Plugin-Regeln), nie direkt gegen REGISTRY.

``area_seen`` ({bereich: [tools]}) wird beim Speichern der Tools mitgeschrieben (``agents/config.update``). „Neu“ sind nur Tools,
die zu diesem Zeitpunkt noch nicht existierten; ein absichtlich entferntes Tool gilt nie als neu. Fehlt ``area_seen``, gelten alle
heute registrierten Tools als gesehen.
"""
from __future__ import annotations

from hydrahive.agents import _area_registry as registry


def _areas() -> list[dict]:
    return registry.all_areas("de")


def seen_snapshot() -> dict[str, list[str]]:
    """{bereich: heute registrierte Tools} – wird beim Speichern der Tools als ``area_seen`` mitgeschrieben."""
    return {a["id"]: list(a["tools"]) for a in _areas()}


def _seen_for(agent: dict, area_id: str) -> set[str] | None:
    """Die damals bekannten Tools des Bereichs; None = unbekannt (fehlt oder kaputt) → alles gilt als gesehen."""
    raw = agent.get("area_seen")
    if not isinstance(raw, dict):
        return None
    tools = raw.get(area_id)
    if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
        return None
    return set(tools)


def _via_category(agent_tools: list[str]) -> set[str]:
    """Namen, die der Agent nur über ``kategorie:x`` bekommt (aufgelöst, ohne die einzeln eingetragenen)."""
    from hydrahive.catalog.categories import PREFIX, resolve_categories
    cats = [t for t in agent_tools if isinstance(t, str) and t.startswith(PREFIX)]
    return set(resolve_categories(cats)) if cats else set()


def area_states(agent: dict) -> list[dict]:
    """Je Bereich ``{id, state, have, missing, new, via_category}`` (Reihenfolge wie ``all_areas``).

    ``have`` = einzeln in ``agent.tools``; ``via_category`` = nur über ``kategorie:x``; ``missing`` = im Bereich, aber weder
    noch; ``new`` = ``missing`` ∩ (heutige − damals gesehene Tools). ``on`` = einzeln vorhanden und alles, was es beim
    Speichern gab, ist da (``missing`` ⊆ ``new``); ``partial`` = sonst, wenn etwas da ist (einzeln oder über Kategorie);
    ``off`` = sonst. Ein Bereich, dessen Tools nur über ``kategorie:x`` kommen, ist darum „teilweise“, nie „an“.
    """
    tools = [t for t in (agent.get("tools") or []) if isinstance(t, str)]
    have_set = set(tools)
    via = _via_category(tools)
    out: list[dict] = []
    for area in _areas():
        mine = area["tools"]
        have = [t for t in mine if t in have_set]
        via_cat = [t for t in mine if t in via and t not in have_set]
        missing = [t for t in mine if t not in have_set and t not in via]
        seen = _seen_for(agent, area["id"])
        new = [t for t in missing if seen is not None and t not in seen]
        if not mine:
            state = "off"
        elif have and set(missing) <= set(new):
            state = "on"                  # alles, was es beim Speichern gab, ist einzeln da (ggf. mit Hinweis ``new``)
        elif have or via_cat:
            state = "partial"             # auch wenn der Rest nur über kategorie:x kommt (Review-Fokus 4)
        else:
            state = "off"
        out.append({"id": area["id"], "state": state, "have": have, "missing": missing, "new": new,
                    "via_category": via_cat})
    return out


def toggle(agent_tools: list[str], area_id: str, on: bool) -> list[str]:
    """Rein funktional: fügt die Tools des Bereichs hinzu (hinten, ohne Dubletten) bzw. entfernt genau diese.

    Alles andere bleibt stehen (Grundausstattung, Plugin-, MCP- und Altbestand-Namen, ``kategorie:x``), Reihenfolge stabil.
    Unbekannter Bereich → KeyError. Die Eingabeliste wird nicht verändert.
    """
    area = next((a for a in _areas() if a["id"] == area_id), None)
    if area is None:
        raise KeyError(area_id)
    mine = area["tools"]
    if on:
        have = set(agent_tools)
        return [*agent_tools, *[t for t in mine if t not in have]]
    drop = set(mine)
    return [t for t in agent_tools if t not in drop]
