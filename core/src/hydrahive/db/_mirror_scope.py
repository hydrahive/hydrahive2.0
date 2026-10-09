"""Mirror — welche Datamining-Ereignisse ein Agent sehen darf (docs/specs/datamining-access.md).

Baut aus Agent-Einstellung ``knowledge_access``, Projekt des Laufs und Nutzer eine WHERE-Bedingung
für die Tabelle ``events``. Werte gehen nur als Parameter ins SQL, nie per String.

Regeln (Spec §2):
- immer nur Ereignisse des eigenen Nutzers,
- ``scope="project"``: nur Projekt des Laufs + freigegebene Projekte (leer → nichts),
- ``scope="user"``: alles des Nutzers,
- Sitzungen mit sensiblen Werkzeugen sind unsichtbar, außer ``sensitive=True``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: Werkzeuge, deren Benutzung eine ganze Sitzung als sensibel markiert (Gesundheit).
SENSITIVE_TOOLS: tuple[str, ...] = ("query_fhir_data", "query_health_data")

SCOPES = ("project", "user")


@dataclass(frozen=True)
class Scope:
    username: str
    scope: str = "project"
    projects: tuple[str, ...] = field(default_factory=tuple)
    sensitive: bool = False


def defaults_for(agent_type: str) -> dict:
    """Standard je Agent-Typ: Master/Buddy sieht alles des Nutzers, sonst nur das Projekt."""
    if agent_type == "master":
        return {"scope": "user", "projects": [], "sensitive": True}
    return {"scope": "project", "projects": [], "sensitive": False}


def scope_for(agent: dict | None, *, username: str, project_id: str | None) -> Scope:
    """Wirksame Sicht eines Agenten in einem Lauf. Unbekannte Werte fallen auf das Strengste zurück."""
    agent = agent or {}
    base = defaults_for(str(agent.get("type") or ""))
    cfg = {**base, **(agent.get("knowledge_access") or {})}
    scope = cfg.get("scope") if cfg.get("scope") in SCOPES else "project"
    projects = [str(p) for p in (cfg.get("projects") or []) if p]
    if project_id:
        projects.insert(0, str(project_id))
    return Scope(username=username, scope=scope, projects=tuple(dict.fromkeys(projects)),
                 sensitive=bool(cfg.get("sensitive")))


def where(sc: Scope, start: int, *, alias: str = "events") -> tuple[list[str], list, int]:
    """(Bedingungen, Parameter, nächster Index) für ``events``. ``start`` = erster freier $-Index.

    Ohne Nutzer gibt es nie Treffer (``FALSE``), statt ungefiltert alles zu liefern.
    """
    conds: list[str] = []
    params: list = []
    i = start
    if not sc.username:
        return ["FALSE"], [], i
    conds.append(f"{alias}.username = ${i}"); params.append(sc.username); i += 1
    if sc.scope != "user":
        if not sc.projects:
            return ["FALSE"], [], start
        conds.append(f"{alias}.project_id = ANY(${i}::text[])"); params.append(list(sc.projects)); i += 1
    if not sc.sensitive:
        conds.append(
            f"NOT EXISTS (SELECT 1 FROM events s WHERE s.session_id = {alias}.session_id "
            f"AND s.tool_name = ANY(${i}::text[]))"
        )
        params.append(list(SENSITIVE_TOOLS)); i += 1
    return conds, params, i
