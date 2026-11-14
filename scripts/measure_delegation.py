#!/usr/bin/env python3
"""Messung der Delegation (Plan E6 agent-templates, „Messung vorher/nachher“). Nur lesen.

Liest sessions.db (SQLite, schreibgeschützt geöffnet) und gibt je Agent-Typ und je Projekt-Agent aus:
- Sitzungen mit LLM-Aufrufen, Tokens je Sitzung (Eingabe inkl. Cache, Ausgabe), Cache-Trefferquote
- Ø / max Kontext (Eingabe-Tokens je LLM-Aufruf inkl. Cache)
- Anteil `ask_agent` an allen Werkzeugaufrufen
- Delegationen (agent_delegations): Anzahl, Fehlerquote (status != done)
- Modellwechsel (messages.metadata.model_switches, ab E1)

Aufruf: python3 scripts/measure_delegation.py [--db PFAD] [--agents PFAD] [--days 14] [--out DATEI.md]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _agent_types(agents_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for f in agents_dir.glob("*/config.json"):
        try:
            c = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        out[c.get("id") or f.parent.name] = {"type": c.get("type") or "?", "name": c.get("name") or "?",
                                            "template": c.get("template") or "", "buddy": bool(c.get("is_buddy"))}
    return out


def _kind(info: dict | None) -> str:
    if not info:
        return "unbekannt"
    return "buddy" if info["buddy"] else info["type"]


def collect(conn: sqlite3.Connection, since: str, agents: dict[str, dict]) -> dict:
    llm = conn.execute(
        "SELECT agent_id, session_id, COALESCE(prompt_tokens,0), COALESCE(cache_read_tokens,0), "
        "COALESCE(cache_creation_tokens,0), COALESCE(completion_tokens,0) FROM llm_calls WHERE created_at >= ?",
        (since,)).fetchall()
    tools = conn.execute(
        "SELECT agent_id, tool_name FROM tool_calls WHERE created_at >= ? AND agent_id IS NOT NULL", (since,)).fetchall()
    deleg = conn.execute("SELECT agent_id, status FROM agent_delegations WHERE created_at >= ?", (since,)).fetchall()
    switches = conn.execute(
        "SELECT s.agent_id, m.metadata FROM messages m JOIN sessions s ON s.id = m.session_id "
        "WHERE m.created_at >= ? AND m.role = 'assistant' AND m.metadata LIKE '%model_switches%'", (since,)).fetchall()

    per: dict[str, dict] = defaultdict(lambda: {"sessions": set(), "calls": 0, "in": 0, "cache_read": 0,
                                                "out": 0, "ctx_max": 0, "tools": 0, "ask_agent": 0,
                                                "deleg": 0, "deleg_fail": 0, "switches": 0})
    for aid, sid, prompt, cread, ccreate, comp in llm:
        p = per[aid or "?"]
        ctx = prompt + cread + ccreate
        p["sessions"].add(sid)
        p["calls"] += 1
        p["in"] += ctx
        p["cache_read"] += cread
        p["out"] += comp
        p["ctx_max"] = max(p["ctx_max"], ctx)
    for aid, name in tools:
        per[aid]["tools"] += 1
        per[aid]["ask_agent"] += name == "ask_agent"
    for aid, status in deleg:
        per[aid]["deleg"] += 1
        per[aid]["deleg_fail"] += status != "done"
    for aid, meta in switches:
        try:
            per[aid or "?"]["switches"] += len(json.loads(meta or "{}").get("model_switches") or [])
        except json.JSONDecodeError:
            pass
    status: dict[str, int] = defaultdict(int)
    for _aid, st in deleg:
        status[st] += 1
    out = {aid: {**v, "sessions": len(v["sessions"]), "kind": _kind(agents.get(aid)),
                 "name": (agents.get(aid) or {}).get("name", aid)} for aid, v in per.items()}
    return {**out, "_status": dict(status)}


def _row(label: str, v: dict) -> str:
    s = v["sessions"] or 1
    calls = v["calls"] or 1
    hit = v["cache_read"] / v["in"] if v["in"] else 0.0
    ask = v["ask_agent"] / v["tools"] if v["tools"] else 0.0
    fail = v["deleg_fail"] / v["deleg"] if v["deleg"] else 0.0
    return (f"| {label} | {v['sessions']} | {v['in'] // s:,} | {v['out'] // s:,} | {hit:.0%} | {v['in'] // calls:,} | "
            f"{v['ctx_max']:,} | {ask:.0%} ({v['ask_agent']}/{v['tools']}) | {v['deleg']} / {fail:.0%} | {v['switches']} |")


_HEAD = ("| {} | Sitzungen | Eingabe/Sitzung | Ausgabe/Sitzung | Cache-Treffer | Ø Kontext | max Kontext | "
         "ask_agent-Anteil | Delegationen / Fehler | Modellwechsel |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")


def report(data: dict, days: int, since: str) -> str:
    by_kind: dict[str, dict] = {}
    for aid, v in data.items():
        if aid == "_status":
            continue
        k = by_kind.setdefault(v["kind"], {"sessions": 0, "calls": 0, "in": 0, "cache_read": 0, "out": 0,
                                          "ctx_max": 0, "tools": 0, "ask_agent": 0, "deleg": 0, "deleg_fail": 0,
                                          "switches": 0})
        for key in k:
            k[key] = max(k[key], v[key]) if key == "ctx_max" else k[key] + v[key]
    lines = [f"# Delegation – Messung ({datetime.now(UTC):%Y-%m-%d}, letzte {days} Tage ab {since[:10]})", "",
             "Tokens: Eingabe inkl. Cache (gelesen + geschrieben). Kontext = Eingabe-Tokens je LLM-Aufruf.", "",
             "## Je Agent-Typ", "", _HEAD.format("Typ")]
    lines += [_row(k, v) for k, v in sorted(by_kind.items())]
    lines += ["", "## Delegationen nach Ausgang", "", "| Ausgang | Anzahl |", "|---|---:|"]
    lines += [f"| {k} | {n} |" for k, n in sorted(data.get("_status", {}).items(), key=lambda x: -x[1])]
    lines += ["", "## Projekt-Agenten (Top 15 nach Sitzungen)", "", _HEAD.format("Agent")]
    projects = sorted((v for a, v in data.items() if a != "_status" and v["kind"] == "project"),
                      key=lambda v: -v["sessions"])[:15]
    lines += [_row(v["name"][:40].replace("|", "/"), v) for v in projects]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/var/lib/hydrahive2/sessions.db")
    ap.add_argument("--agents", default="/var/lib/hydrahive2/agents")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--out")
    a = ap.parse_args()
    since = (datetime.now(UTC) - timedelta(days=a.days)).strftime("%Y-%m-%dT%H:%M:%S")
    conn = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    try:
        text = report(collect(conn, since, _agent_types(Path(a.agents))), a.days, since)
    finally:
        conn.close()
    if a.out:
        Path(a.out).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
