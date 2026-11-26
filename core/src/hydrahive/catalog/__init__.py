"""Tool-Katalog (docs/specs/tool-skill-katalog.md, Katalog Etappe 3).

Eine Suchhilfe über die Tools: Index (``index``), Hybrid-Suche (``search``) und Speicher (``_store``). Der Katalog erweitert nie
ein Recht: gesucht wird nur innerhalb der Freigabe des Laufs, und MCP-Tools kommen nie hinein.
"""

#: Die Katalog-Werkzeuge selbst (Spec E4). Eine Stelle für alle Prüfer: nie über run_tool, nie im Katalog, nie über eine
#: Kategorie, nicht einzeln im Agenten-Editor vergebbar – sie kommen nur über tool_mode catalog dazu (Plan-Aufgabe 5).
CATALOG_TOOLS: frozenset[str] = frozenset({"run_tool", "find_tools", "find_skills"})
