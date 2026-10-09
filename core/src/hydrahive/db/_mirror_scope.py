"""Mirror — welche Datamining-Ereignisse ein Agent sehen darf (docs/specs/datamining-access.md).

Baut aus Agent-Einstellung ``knowledge_access``, Projekt des Laufs und Nutzer eine WHERE-Bedingung
für die Tabelle ``events``. Werte gehen nur als Parameter ins SQL, nie per String.

Regeln (Spec §2):
- immer nur Ereignisse des eigenen Nutzers,
- ``scope="project"``: nur Projekt des Laufs + freigegebene Projekte (leer → nichts),
- ``scope="user"``: alles des Nutzers,
- Sitzungen über der Höchststufe des Agenten (``max_level``) sind unsichtbar. Stufe einer Sitzung =
  höchste Stufe ihrer Werkzeuge (db/_mirror_levels.py, knowledge-spaces.md §2.1). ``sensitive: true`` aus E0
  wird als ``max_level: gesundheit`` verstanden.
- E2a (knowledge-spaces.md §2.2): ``groups`` geben zusätzlich die Projekt-Sitzungen der Gruppenmitglieder frei –
  nie deren Buddy-/Master-Sitzungen, höchstens Stufe ``normal``. Agenten mit Außenwirkung (shell_exec, Discord
  schreibend, Mail, Browser …) sehen höchstens ``normal``; Master/Buddys behalten ihre Stufe für den eigenen Nutzer.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from hydrahive.db import _mirror_groups as groups
from hydrahive.db._mirror_levels import LEVELS, hidden_tools

SCOPES = ("project", "user")


@dataclass(frozen=True)
class Scope:
    username: str
    scope: str = "project"
    projects: tuple[str, ...] = field(default_factory=tuple)
    max_level: str = "normal"
    group_users: tuple[str, ...] = field(default_factory=tuple)   # Mitglieder freigegebener Gruppen
    master_agents: tuple[str, ...] = field(default_factory=tuple)  # deren Sitzungen sind für Gruppen tabu


def defaults_for(agent_type: str) -> dict:
    """Standard je Agent-Typ: Master/Buddy sieht alles des Nutzers, sonst nur das Projekt."""
    if agent_type == "master":
        return {"scope": "user", "projects": [], "max_level": "gesundheit"}
    return {"scope": "project", "projects": [], "max_level": "normal"}


def scope_for(agent: dict | None, *, username: str, project_id: str | None) -> Scope:
    """Wirksame Sicht eines Agenten in einem Lauf. Unbekannte Werte fallen auf das Strengste zurück."""
    agent = agent or {}
    base = defaults_for(str(agent.get("type") or ""))
    cfg = {**base, **(agent.get("knowledge_access") or {})}
    scope = cfg.get("scope") if cfg.get("scope") in SCOPES else "project"
    projects = [str(p) for p in (cfg.get("projects") or []) if p]
    if project_id:
        projects.insert(0, str(project_id))
    own = agent.get("knowledge_access") or {}
    level = _max_level(own, base["max_level"])
    if agent.get("type") != "master" and groups.has_outward_tools(agent.get("tools")):
        level = "normal"                                  # Außenwirkung: nie über normal
    members = groups.group_usernames(own.get("groups"), exclude=username) if own.get("groups") else ()
    return Scope(username=username, scope=scope, projects=tuple(dict.fromkeys(projects)), max_level=level,
                 group_users=members, master_agents=groups.master_agent_ids() if members else ())


def _max_level(own: dict, default: str) -> str:
    """Eigene Einstellung vor Standard: ``max_level`` gewinnt, sonst E0-Feld ``sensitive``
    (true → gesundheit, false → normal), sonst Standard des Typs. Unbekannter Wert → normal (streng)."""
    if "max_level" in own:
        return own["max_level"] if own["max_level"] in LEVELS else "normal"
    if "sensitive" in own:
        return "gesundheit" if own["sensitive"] is True else "normal"
    return default


def where(sc: Scope, start: int, *, alias: str = "events") -> tuple[list[str], list, int]:
    """(Bedingungen, Parameter, nächster Index) für ``events``. ``start`` = erster freier $-Index.

    Ohne Nutzer gibt es nie Treffer (``FALSE``), statt ungefiltert alles zu liefern.
    """
    conds: list[str] = []
    params: list = []
    i = start
    if not sc.username:
        return ["FALSE"], [], i
    if sc.scope != "user" and not sc.projects:
        own = ["FALSE"]                                   # Projekt-Sicht ohne Projekt: eigenes Wissen leer
    else:
        own = [f"{alias}.username = ${i}"]; params.append(sc.username); i += 1
        if sc.scope != "user":
            own.append(f"{alias}.project_id = ANY(${i}::text[])"); params.append(list(sc.projects)); i += 1
    if not sc.group_users:
        if own == ["FALSE"]:
            return ["FALSE"], [], start
        conds.extend(own)
    else:
        # Gruppenmitglieder: nur Projekt-Sitzungen, keine Master/Buddy-Agenten, höchstens Stufe normal.
        grp = [f"{alias}.username = ANY(${i}::text[])", f"{alias}.project_id IS NOT NULL",
               f"{alias}.agent_id IS NOT NULL", f"{alias}.agent_id <> ALL(${i + 1}::text[])"]
        params.extend([list(sc.group_users), list(sc.master_agents)]); i += 2
        normal_hidden = hidden_tools("normal")
        if normal_hidden:
            grp.append(f"{alias}.session_id <> ALL(ARRAY(SELECT DISTINCT g.session_id FROM events g "
                       f"WHERE g.tool_name = ANY(${i}::text[])))")
            params.append(normal_hidden); i += 1
        conds.append(f"(({' AND '.join(own)}) OR ({' AND '.join(grp)}))")
    hidden = hidden_tools(sc.max_level)
    if hidden:
        # Sitzungen über der Höchststufe EINMAL bestimmen (Index events_tool) und ausschließen.
        # Vorher NOT EXISTS je Treffer: bei häufigen Wörtern 2,2 s statt 0,08 s (gemessen 09.10., .2).
        conds.append(
            f"{alias}.session_id <> ALL(ARRAY(SELECT DISTINCT s.session_id FROM events s "
            f"WHERE s.tool_name = ANY(${i}::text[])))"
        )
        params.append(hidden); i += 1
    return conds, params, i
