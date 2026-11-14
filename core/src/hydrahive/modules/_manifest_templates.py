"""Eigene Agenten-Templates aus dem Modul-Manifest (Plan E5, Spec agent-templates.md Kap. 3.2).

`"templates": [{"id": "storyteller-ghostwriter", "label": "…", "base": "modul-schreiber"}]`
Beim Laden des Moduls legt der Kern fehlende Templates als Kopie von `base` an (Gruppe „Module“). Vorhandene bleiben
unangetastet – der Admin passt sie danach an. Deinstallation lässt sie stehen.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,47}$")
_DEFAULT_BASE = "modul-schnell"


def parse_templates(raw, error_cls) -> tuple[tuple[str, str, str], ...]:
    """Manifest-Feld → ((id, label, base), …). Wirft error_cls bei kaputter Angabe."""
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise error_cls("manifest.json: templates muss eine Liste sein")
    out = []
    for item in raw:
        if not isinstance(item, dict) or not _ID.match(str(item.get("id") or "")):
            raise error_cls(f"manifest.json: ungültiger templates-Eintrag {item!r}")
        label = str(item.get("label") or item["id"]).strip()[:80]
        base = str(item.get("base") or _DEFAULT_BASE)
        out.append((item["id"], label, base))
    return tuple(out)


def ensure_module_templates(module_id: str, templates: tuple[tuple[str, str, str], ...]) -> list[str]:
    """Fehlende Templates anlegen. Rückgabe: neu angelegte IDs. Fehler nur loggen – das Modul lädt trotzdem."""
    if not templates:
        return []
    from hydrahive.agents import templates as tpl
    created = []
    for tid, label, base in templates:
        try:
            if tpl.get(tid) is not None:
                continue
            source = tpl.get(base) or tpl.get(_DEFAULT_BASE)
            if source is None:
                logger.warning("Modul %s: Basis-Template %s fehlt, %s nicht angelegt", module_id, base, tid)
                continue
            body = {k: v for k, v in source.items() if k not in ("id", "revision", "updated_at", "updated_by")}
            tpl.save(tid, {**body, "label": label, "group": "modules"}, by=f"modul:{module_id}")
            created.append(tid)
        except Exception:
            logger.exception("Modul %s: Template %s nicht angelegt", module_id, tid)
    if created:
        logger.info("Modul %s: Templates angelegt: %s", module_id, ", ".join(created))
    return created
