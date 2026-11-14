"""Agenten-Templates: Modellkette, Budget und Antwortformat je Rolle (Spec docs/specs/agent-templates.md).

Öffentliche API:
- list_templates(), get(id), history(id)
- save(id, data, by), revert(id, revision, by), delete(id)   – nur aus Admin-Routen aufrufen
- resolve(agent) / resolve_role(id) → ResolvedTemplate | None
"""
from __future__ import annotations

import logging

from hydrahive.agents.templates import _defaults, _store
from hydrahive.agents.templates._resolve import ResolvedTemplate, resolve, resolve_role
from hydrahive.agents.templates._validation import GROUPS, TemplateError, check_id, normalize
from hydrahive.db._utils import now_iso

logger = logging.getLogger(__name__)

__all__ = [
    "GROUPS", "ResolvedTemplate", "TemplateError", "check_id", "normalize",
    "delete", "get", "history", "list_templates", "resolve", "resolve_role", "revert", "save",
]


def _ensure_defaults() -> dict:
    data = _store.load()
    if data["templates"]:
        return data
    with _store.mutate() as fresh:
        if not fresh["templates"]:
            stamp = now_iso()
            for tid, raw in _defaults.build().items():
                try:
                    body = normalize(raw)
                except TemplateError as exc:   # z. B. keine Modelle bekannt: Template ohne Kette überspringen
                    logger.warning("Start-Template %s übersprungen: %s", tid, exc.code)
                    continue
                fresh["templates"][tid] = {**body, "id": tid, "revision": 1,
                                           "updated_at": stamp, "updated_by": "system"}
    return _store.load()


def list_templates() -> list[dict]:
    data = _ensure_defaults()
    return sorted((dict(t) for t in data["templates"].values()),
                  key=lambda t: (GROUPS.index(t.get("group", "specialists")), t["label"].lower()))


def get(template_id: str) -> dict | None:
    t = _ensure_defaults()["templates"].get(template_id)
    return dict(t) if t else None


def history(template_id: str) -> list[dict]:
    return [dict(h) for h in _ensure_defaults()["history"].get(template_id, [])]


def save(template_id: str, data: dict, *, by: str) -> dict:
    check_id(template_id)
    body = normalize(data)
    _ensure_defaults()
    with _store.mutate() as store:
        old = store["templates"].get(template_id)
        if old:
            _store.push_history(store, template_id, old)
        new = {**body, "id": template_id, "revision": (old or {}).get("revision", 0) + 1,
               "updated_at": now_iso(), "updated_by": by}
        store["templates"][template_id] = new
    return dict(new)


def revert(template_id: str, revision: int, *, by: str) -> dict:
    old = next((h for h in history(template_id) if h.get("revision") == revision), None)
    if old is None:
        raise TemplateError("revision_unknown")
    return save(template_id, old, by=by)


def delete(template_id: str) -> None:
    with _store.mutate() as store:
        if store["templates"].pop(template_id, None) is None:
            raise TemplateError("template_unknown")
