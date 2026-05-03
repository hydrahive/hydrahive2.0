#!/usr/bin/env python3
"""HydraHive Datamining MCP-Server — REST API Variante.

Spricht gegen die HydraHive REST-API, kein direkter DB-Zugriff.
Konfiguration via Umgebungsvariablen:
  HH_BASE_URL   — z.B. https://192.168.178.218
  HH_TOKEN      — JWT-Token (aus /api/auth/login) ODER
  HH_USER / HH_PASS — für automatischen Login
  HH_VERIFY_SSL — "1" für Zertifikat-Prüfung (default: 0 = deaktiviert)
"""
import json
import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("HH_BASE_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.environ.get("HH_TOKEN", "")
HH_USER = os.environ.get("HH_USER", "")
HH_PASS = os.environ.get("HH_PASS", "")
VERIFY_SSL = os.environ.get("HH_VERIFY_SSL", "0").lower() not in ("0", "false", "no")

mcp = FastMCP("datamining")
_token: str = TOKEN


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token}"} if _token else {}


def _login() -> None:
    global _token
    if not HH_USER or not HH_PASS:
        raise RuntimeError("Kein Token und kein HH_USER/HH_PASS gesetzt")
    r = httpx.post(f"{BASE_URL}/api/auth/login",
                   json={"username": HH_USER, "password": HH_PASS}, timeout=10, verify=VERIFY_SSL)
    r.raise_for_status()
    _token = r.json()["access_token"]


def _get(path: str, params: dict | None = None) -> dict:
    global _token
    url = f"{BASE_URL}{path}"
    r = httpx.get(url, params=params, headers=_headers(), timeout=15, verify=VERIFY_SSL)
    if r.status_code == 401 and (HH_USER or HH_PASS):
        _login()
        r = httpx.get(url, params=params, headers=_headers(), timeout=15, verify=VERIFY_SSL)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def search(
    query: str,
    event_type: Optional[str] = None,
    username: Optional[str] = None,
    agent_name: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    semantic: bool = False,
    limit: int = 20,
) -> str:
    """Durchsucht alle Chat-Events nach einem Begriff.

    Durchsucht: Textnachrichten, Tool-Outputs, Tool-Inputs, Tool-Namen.
    Optionale Filter: event_type, username, agent_name, Datumsbereich.
    semantic=True: semantische Ähnlichkeitssuche via pgvector statt ILIKE.
    event_type: user_input | assistant_text | tool_call | tool_result | compaction | thinking
    """
    params: dict = {"q": query, "limit": limit}
    if event_type:
        params["event_type"] = event_type
    if username:
        params["username"] = username
    if agent_name:
        params["agent_name"] = agent_name
    if from_date:
        params["from_date"] = from_date
    if to_date:
        params["to_date"] = to_date
    if semantic:
        params["semantic"] = "true"

    try:
        data = _get("/api/datamining/search", params)
    except Exception as e:
        return json.dumps({"error": str(e)})

    results = data.get("results", [])
    return json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2)


@mcp.tool()
def semantic_search(
    query: str,
    event_type: Optional[str] = None,
    username: Optional[str] = None,
    agent_name: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Semantische Ähnlichkeitssuche über alle Chat-Events via pgvector.

    Findet Events die inhaltlich ähnlich zur Query sind — auch ohne exakte Wortübereinstimmung.
    Gibt Ergebnisse sortiert nach Ähnlichkeit zurück (höchste zuerst).
    event_type: user_input | assistant_text | tool_call | tool_result | compaction | thinking
    """
    params: dict = {"q": query, "semantic": "true", "limit": limit}
    if event_type:
        params["event_type"] = event_type
    if username:
        params["username"] = username
    if agent_name:
        params["agent_name"] = agent_name
    if from_date:
        params["from_date"] = from_date
    if to_date:
        params["to_date"] = to_date

    try:
        data = _get("/api/datamining/search", params)
    except Exception as e:
        return json.dumps({"error": str(e)})

    if data.get("error"):
        return json.dumps({"error": data["error"]})

    results = data.get("results", [])
    return json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2)


@mcp.tool()
def get_session(session_id: str) -> str:
    """Gibt alle Events einer Session chronologisch zurück.

    Liefert ein vollständiges Bild der Session inkl. aller Tool-Calls und Outputs.
    """
    try:
        data = _get(f"/api/datamining/sessions/{session_id}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Session {session_id!r} nicht gefunden"})
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})

    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
def list_sessions(
    username: Optional[str] = None,
    agent_name: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Listet die letzten Sessions auf mit Event-Anzahl und Zeitstempeln.

    Optionale Filter: username, agent_name.
    """
    params: dict = {"limit": limit}
    if username:
        params["username"] = username
    if agent_name:
        params["agent_name"] = agent_name

    try:
        data = _get("/api/datamining/sessions", params)
    except Exception as e:
        return json.dumps({"error": str(e)})

    sessions = data.get("sessions", [])
    return json.dumps({"count": len(sessions), "sessions": sessions},
                      ensure_ascii=False, indent=2, default=str)


if __name__ == "__main__":
    if not _token and (HH_USER or HH_PASS):
        _login()
    mcp.run()
