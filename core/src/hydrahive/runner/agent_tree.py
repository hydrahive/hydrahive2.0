"""Agenten-Baum einer Chat-Session: wer hat wen beauftragt, was tut jeder gerade, was kostet es.

Till 20.11.2026: „ich sehe in keinster Weise, was die Agenten tun – das ist russisches
Roulette. Ich muss dringend die Ausgaben sehen und die Arbeiten.“ Bisher zeigte der
Chat nur die DIREKTEN Aufträge („arbeitet seit 47 min · Runde 101“).

Hier: alle Ebenen (rekursiv über agent_delegations → agent_handoffs.session_id), je
Knoten Status, Laufzeit, Frist, Kosten (llm_calls.cost_micros), KI-Aufrufe, die letzten
Befehle im Klartext (tool_calls) und ob ein Befehl gesperrt oder riskant war.
Nur Lesen. Geheimnisse in Befehlen werden geschwärzt.
"""
from __future__ import annotations

import json
import re

from hydrahive.db import delegations as delegations_db
from hydrahive.db.connection import db
from hydrahive.runner import delegation_control
from hydrahive.tools import _shell_guard

MAX_DEPTH = 6
RECENT_TOOLS = 8
_SECRET = re.compile(
    r"(postgresql://[^:@\s]+:)[^@\s]+@|((?:SECRET|PASSWORD|PASSWD|TOKEN|API_KEY|DSN)[A-Z_]*=)\S+|(sshpass -p\s*)\S+",
    re.I,
)


def redact(text: str) -> str:
    return _SECRET.sub(lambda m: (m.group(1) or m.group(2) or m.group(3) or "") + "***" + ("@" if m.group(1) else ""),
                       text or "")


_FAR = "9999"   # offenes Ende für laufende Aufträge


def _cost(session_id: str | None, since: str, until: str) -> dict:
    """Kosten NUR im Zeitfenster dieses Auftrags (fortgesetzte Aufträge teilen die Session)."""
    if not session_id:
        return {"calls": 0, "cost_usd": 0.0, "output_tokens": 0, "model": None}
    with db() as conn:
        row = conn.execute(
            """SELECT COUNT(*), COALESCE(SUM(cost_micros),0), COALESCE(SUM(completion_tokens),0),
                      (SELECT model FROM llm_calls WHERE session_id = ? AND created_at BETWEEN ? AND ?
                       ORDER BY created_at DESC LIMIT 1)
               FROM llm_calls WHERE session_id = ? AND created_at BETWEEN ? AND ?""",
            (session_id, since, until, session_id, since, until),
        ).fetchone()
    return {"calls": int(row[0]), "cost_usd": round(row[1] / 1e6, 4), "output_tokens": int(row[2]), "model": row[3]}


def _label(tool: str, args: dict) -> str:
    if tool == "shell_exec":
        return redact(str(args.get("cmd", "")).strip().splitlines()[0] if args.get("cmd") else "")[:160]
    for key in ("path", "agent_id", "url", "query", "pattern", "name"):
        if args.get(key):
            return redact(f"{key}={args[key]}")[:160]
    return ""


def _row(name: str, args_raw: str | None, status: str, ts: str, err: str | None, result: str | None) -> dict:
    try:
        args = json.loads(args_raw) if args_raw else {}
    except (TypeError, ValueError):
        args = {}
    cmd = str(args.get("cmd", "")) if name == "shell_exec" else ""
    blocked = _shell_guard.BLOCK_MARKER in (err or "") or _shell_guard.BLOCK_MARKER in (result or "")[:600]
    return {"tool": name, "label": _label(name, args), "status": status, "at": ts,
            "risky": bool(cmd) and _shell_guard.check_text(cmd) is not None, "blocked": blocked}


def _tools(session_id: str | None, since: str, until: str) -> tuple[list[dict], list[dict], int]:
    """(letzte Befehle, ALLE riskanten/gesperrten Befehle des Zeitfensters, Anzahl Werkzeugaufrufe)."""
    if not session_id:
        return [], [], 0
    with db() as conn:
        rows = conn.execute(
            """SELECT tool_name, arguments, status, created_at, error_message, substr(result, 1, 600) FROM tool_calls
               WHERE session_id = ? AND created_at BETWEEN ? AND ? ORDER BY created_at DESC""",
            (session_id, since, until),
        ).fetchall()
    all_rows = [_row(*r) for r in rows]
    flagged = [r for r in all_rows if r["risky"] or r["blocked"]]
    return all_rows[:RECENT_TOOLS], list(reversed(flagged))[:50], len(all_rows)   # riskante: chronologisch


def _node(d: dict, owner: str, depth: int, seen: set[str]) -> dict:
    base = delegation_control.serialize(d, owner)
    sid = d.get("target_session_id")
    until = d.get("finished_at") or _FAR
    base["cost"] = _cost(sid, d["created_at"], until)
    base["recent_tools"], base["flagged_tools"], base["tool_count"] = _tools(sid, d["created_at"], until)
    base["children"] = _children(sid, owner, depth + 1, seen) if sid else []
    return base


def _children(session_id: str, owner: str, depth: int, seen: set[str]) -> list[dict]:
    if depth > MAX_DEPTH or session_id in seen:
        return []
    seen.add(session_id)
    return [_node(d, owner, depth, seen) for d in delegations_db.list_for_session(session_id, limit=30)]


def _walk(nodes: list[dict]):
    for n in nodes:
        yield n
        yield from _walk(n["children"])


def build(session_id: str, owner: str) -> dict:
    """Baum + Kopfzeile (aktive Agenten, Gesamtkosten der laufenden Ketten, riskante Befehle)."""
    roots = _children(session_id, owner, 1, set())
    flat = list(_walk(roots))
    active = [n for n in flat if n["status"] == "running"]
    active_roots = [r for r in roots if r["status"] == "running" or any(c["status"] == "running" for c in _walk(r["children"]))]
    return {
        "nodes": roots,
        "summary": {
            "active": len(active),
            "total": len(flat),
            "cost_usd_active_chains": round(sum(n["cost"]["cost_usd"] for r in active_roots for n in _walk([r])), 4),
            "risky_commands": sum(len(n["flagged_tools"]) for n in flat),
        },
    }
