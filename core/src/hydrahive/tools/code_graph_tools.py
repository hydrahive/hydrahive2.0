"""Agenten-Tools für den Code-Graph: den lokalen Wissensgraphen abfragen statt
den Quellcode zu durchwühlen.

Dünne Wrapper über die graphify-CLI (query/explain/path/affected) auf der
graph.json des aktiven Projekts (<workspace>/.graphify/out/graph.json). Der
Graph muss vorher im Cockpit ("Code-Graph" → Graph bauen) erstellt worden sein.
"""
from __future__ import annotations

import asyncio

from hydrahive.tools.base import Tool, ToolContext, ToolResult


def _graph_json(project_id: str | None):
    """Pfad zur graph.json des Projekts, oder None wenn kein Graph existiert."""
    if not project_id:
        return None
    from hydrahive.code_graph import _out_dir
    graph = _out_dir(project_id) / "graph.json"
    return graph if graph.is_file() else None


async def _run_graphify(args: list[str], project_id: str | None) -> ToolResult:
    from hydrahive.code_graph import _graphify_bin
    graph = _graph_json(project_id)
    if graph is None:
        return ToolResult.fail(
            "Kein Code-Graph vorhanden. Erst im Cockpit unter 'Code-Graph' den Graph bauen."
        )
    binary = _graphify_bin()
    if not binary.is_file():
        return ToolResult.fail("graphify ist nicht installiert (Code-Graph erst im Cockpit bauen).")
    cmd = [str(binary), *args, "--graph", str(graph)]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        return ToolResult.fail("Graph-Abfrage Timeout")
    if proc.returncode != 0:
        return ToolResult.fail(f"Graph-Abfrage fehlgeschlagen: {err.decode(errors='replace')[-300:]}")
    return ToolResult.ok(out.decode(errors="replace").strip() or "Keine Treffer.")


async def _query(args: dict, ctx: ToolContext) -> ToolResult:
    question = (args.get("question") or "").strip()
    if not question:
        return ToolResult.fail("question fehlt")
    budget = int(args.get("budget", 2000))
    return await _run_graphify(["query", question, "--budget", str(budget)], ctx.project_id)


async def _explain(args: dict, ctx: ToolContext) -> ToolResult:
    node = (args.get("node") or "").strip()
    if not node:
        return ToolResult.fail("node fehlt")
    return await _run_graphify(["explain", node], ctx.project_id)


async def _path(args: dict, ctx: ToolContext) -> ToolResult:
    a = (args.get("from_node") or "").strip()
    b = (args.get("to_node") or "").strip()
    if not a or not b:
        return ToolResult.fail("from_node und to_node erforderlich")
    return await _run_graphify(["path", a, b], ctx.project_id)


async def _affected(args: dict, ctx: ToolContext) -> ToolResult:
    node = (args.get("node") or "").strip()
    if not node:
        return ToolResult.fail("node fehlt")
    depth = int(args.get("depth", 2))
    return await _run_graphify(["affected", node, "--depth", str(depth)], ctx.project_id)


TOOL_QUERY = Tool(
    name="graph_query",
    description=(
        "Fragt den Code-Graph des aktiven Projekts mit einer natürlichsprachigen Frage ab "
        "(BFS-Traversal). Liefert relevante Knoten mit Datei:Zeile — schneller/günstiger als "
        "den Quellcode zu durchsuchen. Voraussetzung: Graph wurde im Cockpit gebaut. "
        "Beispiel: 'was hängt an require_auth und wie läuft der Auth-Flow?'"
    ),
    schema={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Frage in natürlicher Sprache"},
            "budget": {"type": "integer", "description": "Max. Tokens der Antwort (default 2000)"},
        },
        "required": ["question"],
    },
    execute=_query,
    category="code",
)

TOOL_EXPLAIN = Tool(
    name="graph_explain",
    description=(
        "Erklärt einen Knoten (Funktion/Klasse/Datei) des Code-Graphs und seine Nachbarn "
        "in einfacher Sprache. Voraussetzung: Graph wurde im Cockpit gebaut."
    ),
    schema={
        "type": "object",
        "properties": {"node": {"type": "string", "description": "Name des Knotens, z.B. 'require_auth' oder 'auth.py'"}},
        "required": ["node"],
    },
    execute=_explain,
    category="code",
)

TOOL_PATH = Tool(
    name="graph_path",
    description=(
        "Findet den kürzesten Pfad zwischen zwei Knoten im Code-Graph — zeigt wie zwei "
        "Symbole/Dateien zusammenhängen. Voraussetzung: Graph wurde im Cockpit gebaut."
    ),
    schema={
        "type": "object",
        "properties": {
            "from_node": {"type": "string", "description": "Start-Knoten"},
            "to_node": {"type": "string", "description": "Ziel-Knoten"},
        },
        "required": ["from_node", "to_node"],
    },
    execute=_path,
    category="code",
)

TOOL_AFFECTED = Tool(
    name="graph_affected",
    description=(
        "Reverse-Traversal: findet Knoten, die von einer Änderung an X betroffen wären "
        "('was bricht, wenn ich X ändere?'). Voraussetzung: Graph wurde im Cockpit gebaut."
    ),
    schema={
        "type": "object",
        "properties": {
            "node": {"type": "string", "description": "Knoten, dessen Änderung untersucht wird"},
            "depth": {"type": "integer", "description": "Traversal-Tiefe (default 2)"},
        },
        "required": ["node"],
    },
    execute=_affected,
    category="code",
)
