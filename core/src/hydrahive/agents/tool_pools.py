"""Freigabe-Pools (Katalog Etappe 5, Spec E1/E3/E5/S3/S5): die EINE Quelle für „was darf diesem Agenten zugewiesen werden“.

* Agenten-Pool  (``agent_tool_pools``): setzt nur der ``owner`` des Agenten oder ein Admin.
* Besitzer-Freigabe (``owner_tool_grants``): setzt nur ein Admin; deckelt, was ein Nicht-Admin in seinen Pool legen darf
  (Standard leer = nichts, E5). Admins sind nicht gedeckelt.
* Projekt-Pool (``project_tool_pools``): setzt nur die Projektrolle ``admin`` (oder ein Admin); schränkt nur ein (S5).

Nie im Pool, nie über eine Kategorie: ``AUTHORING_TOOLS``, ``ask_agent`` und die Katalog-Werkzeuge (S3); MCP-Tools nie.
Lesen (``tool_pool_for``) schneidet noch einmal: Besitzer-Freigabe (für Einträge von Nicht-Admins) und Projekt-Pool. Wird
eine Freigabe später kleiner, schrumpft der wirksame Pool mit. Das Config-Feld ``agent["tool_pool"]`` gibt es nicht mehr.

Die Identität (``actor``) kommt von den Routen aus dem Token, nie aus einem Request-Body.
"""
from __future__ import annotations

import logging
import re
import sqlite3

from hydrahive.catalog import CATALOG_TOOLS
from hydrahive.catalog.categories import CATEGORY_MAP, PREFIX, resolve_categories
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db
from hydrahive.tools._project_authoring import AUTHORING_TOOLS

logger = logging.getLogger(__name__)

#: Nie über Pool oder Zuweisung (Spec S3): Authoring, ask_agent (keine Ketten-Delegation), die Katalog-Werkzeuge selbst.
FORBIDDEN: frozenset[str] = frozenset(AUTHORING_TOOLS) | {"ask_agent"} | CATALOG_TOOLS
_ITEM = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")
MAX_ITEMS = 200


def _is_admin(username: str) -> bool:
    from hydrahive.api.middleware.users import get_by_username
    user = get_by_username(username) if username else None
    return bool(user) and user.get("role") == "admin"


def check_item(item: object) -> str:
    """Prüft einen Eintrag (Tool-Name oder ``kategorie:<name>``); ValueError mit deutschem Grund, sonst der Name."""
    if not isinstance(item, str) or not _ITEM.fullmatch(item):
        raise ValueError(f"Ungültiger Eintrag: {str(item)[:60]!r} (erlaubt: Tool-Name oder kategorie:<name>)")
    if item.startswith(PREFIX):
        if item[len(PREFIX):] not in CATEGORY_MAP:
            raise ValueError(f"Unbekannte Kategorie: {item}")
        return item
    if item in FORBIDDEN:
        raise ValueError(f"{item} lässt sich nie über einen Pool oder eine Zuweisung vergeben.")
    if item.startswith("mcp__"):
        raise ValueError(f"{item}: MCP-Werkzeuge gehören nicht in einen Pool.")
    from hydrahive.tools import REGISTRY
    if item not in REGISTRY and not item.startswith("plugin__"):
        raise ValueError(f"Unbekanntes Werkzeug: {item}")
    return item


def _clean(items: object) -> list[str]:
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise ValueError("items muss eine Liste sein (höchstens 200 Einträge).")
    return list(dict.fromkeys(check_item(i) for i in items))


def _rows(sql: str, params: tuple) -> list:
    """Lesen; fehlt die Tabelle (Migration 068 noch nicht gelaufen), gibt es auch keine Einträge."""
    try:
        with db() as conn:
            return conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            logger.debug("Pool-Tabellen fehlen (Migration 068)")
            return []
        raise


# ── Lesen ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def owner_grants(username: str) -> list[str]:
    return [r["tool_or_category"] for r in _rows(
        "SELECT tool_or_category FROM owner_tool_grants WHERE username = ? ORDER BY rowid", (username,))]


def agent_pool_items(agent_id: str) -> list[str]:
    return [r["tool_or_category"] for r in _rows(
        "SELECT tool_or_category FROM agent_tool_pools WHERE agent_id = ? ORDER BY rowid", (agent_id,))]


def project_pool_items(project_id: str) -> list[str]:
    return [r["tool_or_category"] for r in _rows(
        "SELECT tool_or_category FROM project_tool_pools WHERE project_id = ? ORDER BY rowid", (project_id,))]


def _covered(item: str, grants: list[str]) -> bool:
    """Deckt die Besitzer-Freigabe diesen Eintrag? Eine Kategorie nur, wenn sie selbst freigegeben ist."""
    if item in grants:
        return True
    return not item.startswith(PREFIX) and item in set(resolve_categories(list(grants)))


def tool_pool_for(agent: dict, project: dict | None = None, *, capped: bool = True) -> list[str]:
    """Wirksamer Pool: Agenten-Pool (Kategorien aufgelöst) ohne FORBIDDEN, geschnitten mit Besitzer-Freigabe (nur Einträge
    von Nicht-Admins) und Projekt-Pool (leer = keine Einschränkung). Reihenfolge stabil.

    ``capped=False`` (nur ``possible_tool_names``, Gedächtnis-Einstufung D4): ohne Schnitte – der Agent wird nach dem
    beurteilt, was er bekommen KÖNNTE (strengere Richtung).
    """
    agent_id = agent.get("id")
    if not agent_id:
        return []
    rows = _rows("SELECT tool_or_category, by_admin, set_by FROM agent_tool_pools WHERE agent_id = ? ORDER BY rowid",
                 (agent_id,))
    if not rows:
        return []
    owner = agent.get("owner") or ""
    cap_needed = capped and not _is_admin(owner)
    grants = owner_grants(owner) if cap_needed else []
    names: list[str] = []
    admin_now: dict[str, bool] = {}
    for row in rows:
        item = row["tool_or_category"]
        # by_admin gilt nur, solange der Setzende HEUTE noch Admin ist (Review #786: sonst umginge eine Zeile eines
        # später degradierten Admins den Besitzer-Deckel dauerhaft).
        setter = row["set_by"] or ""
        if setter not in admin_now:
            admin_now[setter] = bool(row["by_admin"]) and _is_admin(setter)
        if cap_needed and not admin_now[setter] and not _covered(item, grants):
            continue
        names.extend(resolve_categories([item]))
    names = [n for n in dict.fromkeys(names) if n not in FORBIDDEN and not n.startswith("mcp__")]
    if capped and project and project.get("id"):
        limit = project_pool_items(project["id"])
        if limit:
            allowed = set(resolve_categories(limit))
            names = [n for n in names if n in allowed]
    return names


# ── Schreiben ─────────────────────────────────────────────────────────────────────────────────────────────────────

def set_agent_pool(actor: str, agent_id: str, items: list[str]) -> list[str]:
    """Pool eines Agenten setzen (ersetzt). Nur ``owner`` oder Admin; jedes Item ⊆ Besitzer-Freigabe, außer Admin (E5).

    PermissionError → API 403, ValueError → 400, KeyError → 404.
    """
    from hydrahive.agents import config as agent_config
    agent = agent_config.get(agent_id)
    if not agent:
        raise KeyError(agent_id)
    admin = _is_admin(actor)
    if not admin and agent.get("owner") != actor:
        raise PermissionError("Den Pool setzt nur der Besitzer des Agenten oder ein Admin.")
    clean = _clean(items)
    if not admin:
        grants = owner_grants(actor)
        outside = [i for i in clean if not _covered(i, grants)]
        if outside:
            raise PermissionError(f"Nicht in deiner Besitzer-Freigabe: {', '.join(outside)}. "
                                  "Ein Admin legt fest, was du vergeben darfst.")
    stamp = now_iso()
    with db(immediate=True) as conn:
        conn.execute("DELETE FROM agent_tool_pools WHERE agent_id = ?", (agent_id,))
        conn.executemany(
            "INSERT INTO agent_tool_pools(agent_id, tool_or_category, by_admin, set_by, set_at) VALUES (?, ?, ?, ?, ?)",
            [(agent_id, i, 1 if admin else 0, actor, stamp) for i in clean])
    logger.info("Agenten-Pool %s gesetzt von %s: %s", agent_id, actor, clean)
    return clean


def set_project_pool(actor: str, project_id: str, items: list[str]) -> list[str]:
    """Projekt-Pool setzen (ersetzt). Nur Projektrolle ``admin`` oder Admin (S5). Schränkt nur ein, nie erweitern."""
    from hydrahive.projects import _members_model
    from hydrahive.projects import config as project_config
    project = project_config.get(project_id)
    if not project:
        raise KeyError(project_id)
    if not _is_admin(actor) and _members_model.role_of(project, actor) != "admin":
        raise PermissionError("Den Projekt-Pool setzt nur ein Projekt-Admin oder ein Admin.")
    clean = _clean(items)
    stamp = now_iso()
    with db(immediate=True) as conn:
        conn.execute("DELETE FROM project_tool_pools WHERE project_id = ?", (project_id,))
        conn.executemany("INSERT INTO project_tool_pools(project_id, tool_or_category, set_by, set_at) VALUES (?, ?, ?, ?)",
                         [(project_id, i, actor, stamp) for i in clean])
    logger.info("Projekt-Pool %s gesetzt von %s: %s", project_id, actor, clean)
    return clean


def set_owner_grants(admin: str, username: str, items: list[str]) -> list[str]:
    """Besitzer-Freigabe eines Nutzers setzen (ersetzt). Nur Admin (E5); der Nutzer muss existieren."""
    from hydrahive.api.middleware.users import get_by_username
    if not _is_admin(admin):
        raise PermissionError("Die Besitzer-Freigabe setzt nur ein Admin.")
    if not get_by_username(username):
        raise KeyError(username)
    clean = _clean(items)
    stamp = now_iso()
    with db(immediate=True) as conn:
        conn.execute("DELETE FROM owner_tool_grants WHERE username = ?", (username,))
        conn.executemany("INSERT INTO owner_tool_grants(username, tool_or_category, granted_by, granted_at) "
                         "VALUES (?, ?, ?, ?)", [(username, i, admin, stamp) for i in clean])
    logger.info("Besitzer-Freigabe %s gesetzt von %s: %s", username, admin, clean)
    return clean


def remove_agent(agent_id: str) -> None:
    """Beim Löschen eines Agenten: Pool aufräumen (Fehler hier dürfen das Löschen nie verhindern)."""
    try:
        with db() as conn:
            conn.execute("DELETE FROM agent_tool_pools WHERE agent_id = ?", (agent_id,))
    except Exception:  # noqa: BLE001
        logger.warning("Pool von Agent %s nicht aufgeräumt", agent_id, exc_info=True)


def remove_project(project_id: str) -> None:
    try:
        with db() as conn:
            conn.execute("DELETE FROM project_tool_pools WHERE project_id = ?", (project_id,))
    except Exception:  # noqa: BLE001
        logger.warning("Pool von Projekt %s nicht aufgeräumt", project_id, exc_info=True)


def remove_user(username: str) -> None:
    """Beim Löschen eines Nutzers: Besitzer-Freigabe entfernen (Buddy-Review #786) – sonst erbt ein später gleichnamig
    angelegter Nutzer die alten Freigaben. Fehler dürfen das Löschen nie verhindern."""
    try:
        with db() as conn:
            conn.execute("DELETE FROM owner_tool_grants WHERE username = ?", (username,))
    except Exception:  # noqa: BLE001
        logger.warning("Besitzer-Freigabe von %s nicht aufgeräumt", username, exc_info=True)
