"""Echte Import-Zyklen aus graph.json berechnen.

graphify's eigener Zyklus-Report kollabiert jeden Knoten auf seinen Datei-
Basename — bei Python-Projekten mit vielen `__init__.py` erzeugt das massenhaft
Scheinzyklen (jedes `__init__.py -> __init__.py`). Hier bauen wir den
Import-Graphen stattdessen auf Datei-Ebene mit vollen Pfaden auf und finden
echte stark-zusammenhängende Komponenten (Tarjan, iterativ)."""
from __future__ import annotations

import json
from pathlib import Path

_IMPORT_RELATIONS = {"imports", "imports_from", "re_exports"}


def _node_files(data: dict) -> dict[str, str]:
    """id -> lesbarer Datei-Schlüssel (repo-qualifiziert, damit gleichnamige
    Dateien aus verschiedenen Repos nicht verschmelzen)."""
    files: dict[str, str] = {}
    for n in data.get("nodes", []):
        if not isinstance(n, dict):
            continue
        src = n.get("source_file")
        if not src:
            continue
        repo = n.get("repo")
        files[n.get("id")] = f"{repo}/{src}" if repo else src
    return files


def _import_graph(data: dict) -> dict[str, set[str]]:
    """Gerichteter Datei→Datei-Import-Graph (ohne Selbstkanten)."""
    files = _node_files(data)
    adj: dict[str, set[str]] = {}
    for link in data.get("links", []):
        if not isinstance(link, dict) or link.get("relation") not in _IMPORT_RELATIONS:
            continue
        src, dst = files.get(link.get("source")), files.get(link.get("target"))
        if not src or not dst or src == dst:
            continue
        adj.setdefault(src, set()).add(dst)
        adj.setdefault(dst, set())
    return adj


def _sccs(adj: dict[str, set[str]]) -> list[list[str]]:
    """Tarjan-SCC, iterativ (keine Rekursionsgrenze bei großen Graphen)."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    result: list[list[str]] = []
    counter = 0

    for root in list(adj):
        if root in index:
            continue
        work: list[tuple[str, int]] = [(root, 0)]
        while work:
            node, child_i = work[-1]
            if child_i == 0:
                index[node] = low[node] = counter
                counter += 1
                stack.append(node)
                on_stack.add(node)
            children = sorted(adj.get(node, ()))
            if child_i < len(children):
                work[-1] = (node, child_i + 1)
                nxt = children[child_i]
                if nxt not in index:
                    work.append((nxt, 0))
                elif nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
            else:
                if low[node] == index[node]:
                    comp: list[str] = []
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        comp.append(w)
                        if w == node:
                            break
                    if len(comp) > 1:
                        result.append(comp)
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
    return result


def _cycle_path(scc: list[str], adj: dict[str, set[str]]) -> list[str]:
    """Einen konkreten Zyklus innerhalb einer SCC extrahieren (für die Anzeige)."""
    members = set(scc)
    start = min(scc)
    path: list[str] = []
    seen: set[str] = set()
    node = start
    while node not in seen:
        seen.add(node)
        path.append(node)
        nxt = next((t for t in sorted(adj.get(node, ())) if t in members), None)
        if nxt is None:
            break
        if nxt in seen:
            path.append(nxt)
            return path[path.index(nxt):]
        node = nxt
    return path + [start]


def import_cycles(graph_json: Path, limit: int = 10) -> list[str]:
    """Liste echter Import-Zyklen als lesbare Pfade ('a.py -> b.py -> a.py')."""
    try:
        data = json.loads(graph_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    adj = _import_graph(data)
    cycles = [_cycle_path(scc, adj) for scc in _sccs(adj)]
    cycles.sort(key=len, reverse=True)
    return [" -> ".join(c) for c in cycles[:limit]]
