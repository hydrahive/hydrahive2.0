"""Load/Save für Butler-Flows.

Pro Owner ein Verzeichnis unter `$HH_CONFIG_DIR/butler/<owner>/`,
pro Flow eine JSON-File `<flow_id>.json`. Validation passiert immer
beim Save (Pydantic-Models lehnen Garbage ab) UND beim Load
(falls jemand manuell editiert hat).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from hydrahive.butler.models import Flow
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_FLOW_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
_OWNER_RE = re.compile(r"^[A-Za-z0-9_\-]+$|^project:[A-Za-z0-9_\-]+$")


def _safe_owner(owner: str) -> str:
    if not _OWNER_RE.match(owner):
        raise ValueError("invalid_owner")
    return owner.replace(":", "_")


def _flow_dir(owner: str):
    settings.butler_dir.mkdir(parents=True, exist_ok=True)
    d = settings.butler_dir / _safe_owner(owner)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _flow_path(owner: str, flow_id: str):
    if not _FLOW_ID_RE.match(flow_id):
        raise ValueError("invalid_flow_id")
    return _flow_dir(owner) / f"{flow_id}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def list_flows(owner: str | None = None) -> list[Flow]:
    """`owner=None` listet alle (für Server-Reconciliation),
    sonst nur die des Owners."""
    settings.butler_dir.mkdir(parents=True, exist_ok=True)
    flows: list[Flow] = []
    if owner is not None:
        owners = [owner]
    else:
        owners = [d.name for d in settings.butler_dir.iterdir() if d.is_dir()]
    for o in owners:
        try:
            d = _flow_dir(o)
        except ValueError:
            continue
        for f in d.glob("*.json"):
            try:
                flows.append(Flow.model_validate_json(f.read_text(encoding="utf-8")))
            except Exception as e:
                logger.warning("Skipping invalid flow %s: %s", f, e)
    return flows


def get_flow(owner: str, flow_id: str) -> Flow | None:
    p = _flow_path(owner, flow_id)
    if not p.exists():
        return None
    try:
        return Flow.model_validate_json(p.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Flow %s/%s invalid: %s", owner, flow_id, e)
        return None


def save_flow(flow: Flow, modified_by: str) -> Flow:
    now = _now()
    if not flow.created_at:
        flow.created_at = now
    flow.modified_at = now
    flow.modified_by = modified_by
    p = _flow_path(flow.owner, flow.flow_id)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(flow.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(p)
    return flow


def delete_flow(owner: str, flow_id: str) -> bool:
    p = _flow_path(owner, flow_id)
    if not p.exists():
        return False
    p.unlink()
    return True
