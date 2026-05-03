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
from collections import defaultdict
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


def _search_all(event_type: str, from_date: str, to_date: str, limit: int = 500) -> list[dict]:
    """Hilfsfunktion: alle Events eines Typs in einem Zeitraum holen."""
    data = _get("/api/datamining/search", {
        "q": "",
        "event_type": event_type,
        "from_date": from_date,
        "to_date": to_date,
        "limit": limit,
    })
    return data.get("results", [])


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


@mcp.tool()
def daily_summary(date: str) -> str:
    """Tagesübersicht: was wurde an einem Tag erledigt, von wem, in welchen Sessions.

    date: ISO-Datum, z.B. "2026-05-03"
    Gibt pro Agent und Session aus: was der User gefragt hat + welche Tools aufgerufen wurden.
    Rein deterministisch, kein LLM.
    """
    to_date = date + "T23:59:59"

    try:
        user_inputs = _search_all("user_input", date, to_date)
        tool_calls  = _search_all("tool_call",  date, to_date)
        errors      = _get("/api/datamining/search", {
            "q": "", "from_date": date, "to_date": to_date,
            "event_type": "tool_result", "limit": 500,
        }).get("results", [])
        errors = [e for e in errors if e.get("is_error")]
    except Exception as e:
        return json.dumps({"error": str(e)})

    # Nach Session gruppieren
    sessions: dict[str, dict] = {}

    def _session(sid: str, agent: str, user: str) -> dict:
        if sid not in sessions:
            sessions[sid] = {"session_id": sid, "agent": agent, "user": user,
                             "requests": [], "tools": defaultdict(int), "errors": 0}
        return sessions[sid]

    for e in user_inputs:
        s = _session(e["session_id"], e.get("agent_name", "?"), e.get("username", "?"))
        text = (e.get("snippet") or "").strip()
        if text:
            s["requests"].append({"time": e["created_at"][:19].replace("T", " "), "text": text[:200]})

    for e in tool_calls:
        s = _session(e["session_id"], e.get("agent_name", "?"), e.get("username", "?"))
        tool = e.get("tool_name") or "unknown"
        s["tools"][tool] += 1

    for e in errors:
        sid = e["session_id"]
        if sid in sessions:
            sessions[sid]["errors"] += 1

    # defaultdict → dict für JSON
    result = []
    for s in sorted(sessions.values(), key=lambda x: x["requests"][0]["time"] if x["requests"] else ""):
        result.append({
            "session_id": s["session_id"],
            "agent": s["agent"],
            "user": s["user"],
            "requests": s["requests"],
            "tool_calls": dict(s["tools"]),
            "errors": s["errors"],
        })

    total_tools = sum(sum(s["tool_calls"].values()) for s in result)
    total_errors = sum(s["errors"] for s in result)

    return json.dumps({
        "date": date,
        "sessions": len(result),
        "total_tool_calls": total_tools,
        "total_errors": total_errors,
        "by_session": result,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def error_report(
    from_date: str,
    to_date: Optional[str] = None,
) -> str:
    """Fehler-Report: alle fehlgeschlagenen Tool-Calls in einem Zeitraum.

    from_date: ISO-Datum z.B. "2026-05-03"
    to_date: optional, default = gleicher Tag wie from_date
    Gruppiert nach Agent und Tool-Name.
    """
    if not to_date:
        to_date = from_date + "T23:59:59"

    try:
        data = _get("/api/datamining/search", {
            "q": "", "event_type": "tool_result",
            "from_date": from_date, "to_date": to_date, "limit": 500,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

    all_results = data.get("results", [])
    errors = [e for e in all_results if e.get("is_error")]

    if not errors:
        return json.dumps({"from_date": from_date, "to_date": to_date, "errors": 0, "details": []})

    # Nach Agent + session gruppieren
    by_agent: dict[str, list] = defaultdict(list)
    for e in errors:
        agent = e.get("agent_name", "?")
        by_agent[agent].append({
            "time": e["created_at"][:19].replace("T", " "),
            "session_id": e["session_id"],
            "snippet": (e.get("snippet") or "")[:300],
        })

    return json.dumps({
        "from_date": from_date,
        "to_date": to_date,
        "errors": len(errors),
        "by_agent": {k: v for k, v in sorted(by_agent.items())},
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def tool_stats(
    from_date: str,
    to_date: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> str:
    """Tool-Nutzungsstatistik: wie oft wurde welches Tool in einem Zeitraum aufgerufen.

    from_date: ISO-Datum z.B. "2026-05-03"
    to_date: optional, default = gleicher Tag wie from_date
    Zeigt Aufrufe pro Tool und pro Agent, sortiert nach Häufigkeit.
    """
    if not to_date:
        to_date = from_date + "T23:59:59"

    params: dict = {"q": "", "event_type": "tool_call",
                    "from_date": from_date, "to_date": to_date, "limit": 500}
    if agent_name:
        params["agent_name"] = agent_name

    try:
        data = _get("/api/datamining/search", params)
    except Exception as e:
        return json.dumps({"error": str(e)})

    events = data.get("results", [])

    by_tool: dict[str, int] = defaultdict(int)
    by_agent: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for e in events:
        tool = e.get("tool_name") or "unknown"
        agent = e.get("agent_name", "?")
        by_tool[tool] += 1
        by_agent[agent][tool] += 1

    return json.dumps({
        "from_date": from_date,
        "to_date": to_date,
        "total_calls": len(events),
        "by_tool": dict(sorted(by_tool.items(), key=lambda x: -x[1])),
        "by_agent": {
            agent: dict(sorted(tools.items(), key=lambda x: -x[1]))
            for agent, tools in sorted(by_agent.items())
        },
    }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    if not _token and (HH_USER or HH_PASS):
        _login()
    mcp.run()
