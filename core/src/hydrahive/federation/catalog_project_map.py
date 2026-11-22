"""Gemeinsame Taskpflege: fremde Einträge eigenen Projekten zuordnen
(docs/specs/federation-shared-tasks.md §Projektzuordnung).

Die Zuordnung wird beim Lesen berechnet, nichts davon wird gespeichert. Reihenfolge:

1. **Manuell** (``federation_catalog_project_map`` für Nutzer, Ursprung und
   Ursprungsprojekt): ein eigenes Projekt oder ``hidden`` („nicht anzeigen“). Ein
   manuelles Ziel gilt nur, solange es das Projekt noch gibt und der Nutzer Mitglied
   ist (Admins: jedes), sonst fällt die Zeile auf „nicht zugeordnet“ zurück.
2. **Gleicher Name:** genau ein eigenes Projekt, dessen Name getrimmt und ohne
   Groß-/Kleinschreibung gleich ``project_name`` des Ursprungs ist, und der Nutzer
   ist Mitglied (Admins: jedes Projekt).
3. Sonst **nicht zugeordnet**, mit Grund.

Benennt der Ursprung ein Projekt um, wandert die automatische Zuordnung mit dem
neuen Namen. Eine manuelle Zuordnung hängt an ``origin_project_id`` und bleibt.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from hydrahive.db.federation_catalog_project_map import manual_rows as load_manual
from hydrahive.projects import _members_model
from hydrahive.projects import config as project_config

HIDDEN = "hidden"
# Gründe (``reason``): woher die Zuordnung kommt bzw. warum es keine gibt
MANUAL, NAME, HIDDEN_REASON = "manual", "name", "hidden"
AMBIGUOUS, NO_MATCH, NOT_MEMBER, NO_PROJECT = "ambiguous", "no_match", "not_member", "no_project"
TARGET_GONE = "target_unavailable"


@dataclass(frozen=True)
class Assignment:
    local_project_id: str | None    # eigenes Projekt oder None (nicht angezeigt / nicht zugeordnet)
    hidden: bool                    # manuell „nicht anzeigen“
    reason: str                     # manual · name · hidden · ambiguous · no_match · not_member ·
                                    # no_project · target_unavailable

    @property
    def assigned(self) -> bool:
        return self.local_project_id is not None


def normalize(name: str | None) -> str:
    return " ".join((name or "").split()).casefold()


class Resolver:
    """Rechnet viele Einträge eines Nutzers schnell: Projekte und manuelle Zeilen werden
    einmal geladen. Für P2 (``catalog_foreign_list``) gedacht: ein Resolver je Anfrage."""

    def __init__(self, username: str, *, is_admin: bool, projects: Iterable[dict] | None = None,
                 manual: dict[tuple[str, str], str] | None = None) -> None:
        self.username, self.is_admin = username, is_admin
        all_projects = list(projects if projects is not None else project_config.list_all())
        self._by_id = {p["id"]: p for p in all_projects}
        self._by_name: dict[str, list[dict]] = {}
        for p in all_projects:
            self._by_name.setdefault(normalize(p.get("name")), []).append(p)
        self._manual = manual if manual is not None else load_manual(username)

    def _allowed(self, project: dict) -> bool:
        return self.is_admin or _members_model.is_member(project, self.username)

    def resolve(self, origin_fp: str, origin_project_id: str | None, project_name: str | None) -> Assignment:
        if not origin_project_id:
            return Assignment(None, False, NO_PROJECT)       # nur in projektübergreifenden Listen
        target = self._manual.get((origin_fp, origin_project_id))
        if target == HIDDEN:
            return Assignment(None, True, HIDDEN_REASON)
        if target is not None:
            project = self._by_id.get(target)
            if project is not None and self._allowed(project):
                return Assignment(target, False, MANUAL)
            return Assignment(None, False, TARGET_GONE)
        matches = self._by_name.get(normalize(project_name), []) if normalize(project_name) else []
        if not matches:
            return Assignment(None, False, NO_MATCH)
        if len(matches) > 1:
            return Assignment(None, False, AMBIGUOUS)
        if not self._allowed(matches[0]):
            return Assignment(None, False, NOT_MEMBER)
        return Assignment(matches[0]["id"], False, NAME)


def resolve(username: str, *, is_admin: bool, origin_fp: str, origin_project_id: str | None,
            project_name: str | None) -> Assignment:
    """Ein einzelner Eintrag. Für viele Einträge ``Resolver`` nehmen."""
    return Resolver(username, is_admin=is_admin).resolve(origin_fp, origin_project_id, project_name)

