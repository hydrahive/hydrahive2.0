"""Memory-View API: Memory-Einträge, Crystals und Sessions eines Agents.

Endpoints:
  GET    /api/agents/{agent_id}/memory                    — Memory-Browser
  DELETE /api/agents/{agent_id}/memory/{key}              — Eintrag löschen
  GET    /api/agents/{agent_id}/crystals                  — Crystal-Liste
  GET    /api/agents/{agent_id}/memory-sessions           — Session-Liste
  GET    /api/agents/{agent_id}/memory-sessions/{session_id}/observations — Compressed Observations
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._agent_schemas import check_agent_access

router = APIRouter(prefix="/api/agents", tags=["memory"])


def _get_agent_or_404(agent_id: str) -> dict:
    agent = agent_config.get(agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    return agent


# ---------------------------------------------------------------------------
# GET /api/agents/{agent_id}/memory
# ---------------------------------------------------------------------------

@router.get("/{agent_id}/memory")
def get_agent_memory(
    agent_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    project: str | None = Query(None, description="Projekt-Filter"),
    q: str | None = Query(None, description="Substring-Suche auf Key + Content"),
    include_expired: bool = Query(False, description="Abgelaufene Einträge einschließen"),
    limit: int = Query(200, ge=1, le=2000),
) -> dict:
    """Gibt Memory-Einträge eines Agents zurück. Filterbar nach Projekt und Text."""
    username, role = auth
    agent = _get_agent_or_404(agent_id)
    check_agent_access(agent, username, role)

    from hydrahive.tools._memory_store import load, is_expired

    # Memory-Browser zeigt alle Einträge — load() statt load_filtered()
    # (load_filtered hat Agent-Semantik: ohne aktives Projekt nur globale Einträge)
    raw = load(agent_id)
    data = {
        k: v for k, v in raw.items()
        if v.get("is_latest", True)
        and (include_expired or not is_expired(v))
        and _project_matches_simple(v, project)
    }

    # Textsuche
    if q:
        q_lower = q.lower()
        data = {
            k: v for k, v in data.items()
            if q_lower in k.lower() or q_lower in str(v.get("content", "")).lower()
        }

    # Sortierung: neueste zuerst (updated_at desc)
    entries = sorted(
        data.items(),
        key=lambda kv: kv[1].get("updated_at") or kv[1].get("created_at") or "",
        reverse=True,
    )[:limit]

    return {
        "agent_id": agent_id,
        "total": len(data),
        "entries": [
            {
                "key": k,
                "content": v.get("content", ""),
                "confidence": v.get("confidence"),
                "project": v.get("project"),
                "expires_at": v.get("expires_at"),
                "created_at": v.get("created_at"),
                "updated_at": v.get("updated_at"),
                "reinforcements": v.get("reinforcements", 0),
                "is_latest": v.get("is_latest", True),
            }
            for k, v in entries
        ],
    }


def _project_matches_simple(entry: dict, project: str | None) -> bool:
    """Browser-Filter: project=None → alle Einträge; project='x' → nur 'x'."""
    if project is None:
        return True  # kein Filter → alles anzeigen
    return entry.get("project") == project


# ---------------------------------------------------------------------------
# DELETE /api/agents/{agent_id}/memory/{key}
# ---------------------------------------------------------------------------

@router.delete(
    "/{agent_id}/memory/{key:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_memory_entry(agent_id: str, key: str) -> None:
    """Löscht einen Memory-Eintrag. Nur Admin."""
    _get_agent_or_404(agent_id)

    from hydrahive.tools._memory_store import delete_key
    if not delete_key(agent_id, key):
        raise coded(status.HTTP_404_NOT_FOUND, "memory_key_not_found")


# ---------------------------------------------------------------------------
# GET /api/agents/{agent_id}/crystals
# ---------------------------------------------------------------------------

@router.get("/{agent_id}/crystals")
def get_agent_crystals(
    agent_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    project: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
) -> dict:
    """Gibt Crystals (Session-Digests) eines Agents zurück."""
    username, role = auth
    agent = _get_agent_or_404(agent_id)
    check_agent_access(agent, username, role)

    from hydrahive.tools._crystallize import list_crystals
    crystals = list_crystals(agent_id, project=project, limit=limit)

    return {
        "agent_id": agent_id,
        "total": len(crystals),
        "crystals": [
            {
                "id": c.get("id"),
                "session_id": c.get("session_id"),
                "project": c.get("project"),
                "created_at": c.get("created_at"),
                "narrative": c.get("narrative", ""),
                "key_outcomes": c.get("key_outcomes", []),
                "files_affected": c.get("files_affected", []),
                "lessons": c.get("lessons", []),
                "observation_count": c.get("observation_count", 0),
                "source_observation_ids": c.get("source_observation_ids", []),
            }
            for c in crystals
        ],
    }


# ---------------------------------------------------------------------------
# GET /api/agents/{agent_id}/memory-sessions
# ---------------------------------------------------------------------------

@router.get("/{agent_id}/memory-sessions")
def get_agent_memory_sessions(
    agent_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    project: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    """Gibt Sessions eines Agents zurück mit Observation-Count und Crystal-Status."""
    username, role = auth
    agent = _get_agent_or_404(agent_id)
    check_agent_access(agent, username, role)

    from hydrahive.tools._sessions import session_list
    from hydrahive.tools._crystallize import list_crystals

    sessions = session_list(agent_id, project=project, limit=limit)

    # N+1-Vermeidung: alle Crystals einmal laden, dann als Set
    all_crystals = list_crystals(agent_id, limit=1000)
    crystallized = {c.get("session_id") for c in all_crystals}

    result = []
    for s in sessions:
        sid = s.get("id", "")
        result.append({
            "session_id": sid,
            "project": s.get("project"),
            "model": s.get("model"),
            "status": s.get("status", "unknown"),
            "started_at": s.get("started_at"),
            "ended_at": s.get("ended_at"),
            "first_prompt": s.get("first_prompt"),
            "observation_count": s.get("observation_count", 0),
            "has_crystal": sid in crystallized,
        })

    return {
        "agent_id": agent_id,
        "total": len(result),
        "sessions": result,
    }


# ---------------------------------------------------------------------------
# GET /api/agents/{agent_id}/memory-sessions/{session_id}/observations
# ---------------------------------------------------------------------------

@router.get("/{agent_id}/memory-sessions/{session_id}/observations")
def get_session_observations(
    agent_id: str,
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Gibt CompressedObservations einer Session zurück (für Session-Drawer)."""
    username, role = auth
    agent = _get_agent_or_404(agent_id)
    check_agent_access(agent, username, role)

    from hydrahive.tools._compress import load_compressed
    observations = load_compressed(agent_id, session_id)

    return {
        "agent_id": agent_id,
        "session_id": session_id,
        "total": len(observations),
        "observations": [
            {
                "id": o.get("id"),
                "type": o.get("type", "other"),
                "title": o.get("title", ""),
                "facts": o.get("facts", []),
                "concepts": o.get("concepts", []),
                "files": o.get("files", []),
                "importance": o.get("importance", 5),
                "narrative": o.get("narrative", ""),
                "timestamp": o.get("timestamp"),
            }
            for o in observations
        ],
    }
