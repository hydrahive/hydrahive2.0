"""Protokoll der Bereichs-Änderungen in Bereichssprache (docs/specs/agent-bereiche.md 4.7).

Liest ``access_audit`` (dasselbe Log wie alle Admin-Aktionen). Gefiltert wird nach der AKTION, nie nach dem Ziel (Review #789
M5): nur Pool-, Freigabe- und Bestätigungs-Änderungen, nie etwa ``user_purge``. Die Tool-Namen im ``detail`` werden über das
Bereichs-Verzeichnis auf Bereichsnamen abgebildet; die Tool-Namen selbst stehen nur in ``tools`` (für die Expertenansicht).
"""
from __future__ import annotations

from hydrahive.agents import _area_registry as registry

ACTIONS = ("tool_pool_set", "tool_grants_set", "tool_category_approve", "tool_category_revoke")
DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def _tools(detail: str) -> list[str]:
    """Tool-Namen aus dem ``detail`` („a, b“, „(leer)“ oder leer); ohne Dubletten, Reihenfolge stabil."""
    out: list[str] = []
    for part in (detail or "").split(","):
        name = part.strip()
        if name and name != "(leer)" and name not in out:
            out.append(name)
    return out


def _actor_names() -> dict[str, str]:
    from hydrahive.api.middleware.users import list_users
    return {u["user_id"]: u["username"] for u in list_users()}


def entries(lang: str = "de", limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Neueste zuerst. ``areas`` = Bereichsnamen (je einmal, in Reihenfolge des ersten Tools), ``unknown`` = Tools ohne Bereich."""
    from hydrahive.db.connection import db
    limit = max(1, min(int(limit), MAX_LIMIT))
    marks = ",".join("?" for _ in ACTIONS)
    with db() as conn:
        rows = conn.execute(
            f"SELECT id, at, actor_id, action, target, detail FROM access_audit WHERE action IN ({marks}) "
            "ORDER BY id DESC LIMIT ?", (*ACTIONS, limit)).fetchall()
    catalog = registry.all_areas(lang)
    names = {a["id"]: a["name"] for a in catalog}
    owner = {t: a["id"] for a in catalog for t in a["tools"]}               # Tool → Bereich, einmal aufgelöst
    actors = _actor_names()
    out: list[dict] = []
    for r in rows:
        tools = _tools(r["detail"])
        areas: list[str] = []
        unknown: list[str] = []
        for t in tools:
            label = names.get(owner.get(t, ""))                          # Grundausstattung und Unbekanntes: kein Bereich
            if label is None:
                unknown.append(t)
            elif label not in areas:
                areas.append(label)
        out.append({"at": r["at"], "actor": actors.get(r["actor_id"], ""), "action": r["action"], "target": r["target"],
                    "areas": areas, "tools": tools, "unknown": unknown})
    return out
