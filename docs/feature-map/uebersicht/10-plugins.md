# Feature Map: Plugins — Dynamische Tool-Erweiterungen

> **Modul:** `core/src/hydrahive/plugins/`  
> **Datenpfad:** `/var/lib/hydrahive2/plugins/`  
> **Was:** Erweiterbare Tool-Plugins. Können nachträglich installiert werden ohne Core-Code zu ändern.  
> **Warum:** Core bleibt schlank. Spezialisierte Tools (code-metrics, git-stats, ...) als separate Pakete.

---

## Dateien (Backend)

| Datei | Verantwortung |
|---|---|
| `plugins/__init__.py` | Plugin-System-Init, `tool_bridge` exportieren |
| `tool_bridge.py` | Bridge zwischen Runner-Dispatcher und Plugin-Tools. `PREFIX = "plugin__"` |

---

## Plugin-Verzeichnis-Struktur

```
/var/lib/hydrahive2/plugins/<plugin-name>/
├── manifest.json          # Plugin-Metadata
└── tools/
    ├── <tool-name>.json   # Tool-Schema (JSON)
    └── <tool-name>.sh     # Tool-Implementierung (Shell-Script)
    # oder
    └── <tool-name>.py     # Tool-Implementierung (Python)
```

---

## manifest.json Format

```json
{
  "name": "code-metrics",
  "version": "1.0.0",
  "description": "Code-Analyse Tools (LOC, Complexity, Languages)",
  "author": "HydraHive",
  "tools": ["files", "complexity", "languages", "loc"],
  "requires": []
}
```

---

## Tool-Naming

Plugin-Tools haben immer das Präfix `plugin__`:
```
plugin__code-metrics__files
plugin__code-metrics__complexity
plugin__file-search__grep
plugin__git-stats__git_commits
plugin__http-tester__request
plugin__hello-world__hello
```

Schema: `plugin__<plugin-name>__<tool-name>`

---

## Installierte Plugins (aktuell)

| Plugin | Tools | Beschreibung |
|---|---|---|
| `code-metrics` | `files`, `complexity`, `languages`, `loc` | Code-Analyse: Dateiliste, Komplexität, Sprachen, LOC |
| `file-search` | `grep`, `find`, `tree` | Datei-Suche: Regex-Grep, Find by Name, Verzeichnis-Baum |
| `git-stats` | `git_authors`, `git_commits`, `git_files`, `git_diff` | Git-Statistiken: Autoren, Commits, Diff |
| `http-tester` | `request`, `validate`, `compare` | HTTP-Tests: Request, JSON-Schema-Validierung, JSON-Diff |
| `hello-world` | `hello` | Demo-Plugin |
| `minimax-creator` | (MiniMax-spezifisch) | MiniMax Video/Image-Generation |

---

## Plugin-Tool-Bridge

```python
# tool_bridge.py
PREFIX = "plugin__"

async def call(tool_name: str, args: dict, ctx: ToolContext) -> ToolResult:
    # "plugin__code-metrics__files" → plugin="code-metrics", tool="files"
    plugin_name, tool_name = parse_tool_name(tool_name)
    plugin = load_plugin(plugin_name)
    return await plugin.execute(tool_name, args, ctx)

def schemas_for(tool_names: list[str]) -> list[dict]:
    # Gibt Schemas für alle plugin__-Tools zurück
```

---

## Plugin-Hub (optional)

- Plugins können aus einem Hub installiert werden
- `GET /api/plugins/hub` → verfügbare Plugins
- `POST /api/plugins/install` → Plugin aus Hub laden
- `DELETE /api/plugins/{name}` → Plugin entfernen
- Lokale Plugins möglich (Zip-Upload)

---

## Plugin schreiben (Kurzanleitung)

```bash
mkdir -p /var/lib/hydrahive2/plugins/my-plugin/tools

# manifest.json
cat > /var/lib/hydrahive2/plugins/my-plugin/manifest.json << 'EOF'
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Mein Plugin",
  "tools": ["my_tool"]
}
EOF

# Tool-Schema (JSON)
cat > /var/lib/hydrahive2/plugins/my-plugin/tools/my_tool.json << 'EOF'
{
  "name": "plugin__my-plugin__my_tool",
  "description": "Mein Tool tut was.",
  "input_schema": {
    "type": "object",
    "properties": {
      "input": {"type": "string", "description": "Input-Text"}
    },
    "required": ["input"]
  }
}
EOF

# Tool-Implementierung (Shell)
cat > /var/lib/hydrahive2/plugins/my-plugin/tools/my_tool.sh << 'EOF'
#!/bin/bash
echo "Du hast eingegeben: $INPUT"
EOF
chmod +x /var/lib/hydrahive2/plugins/my-plugin/tools/my_tool.sh
```

---

## Verwandte Subsysteme

- **→ Runner / Dispatcher** (`01-runner.md`): Dispatcher nutzt `plugin_bridge.call()`
- **→ Tools** (`02-tools.md`): Plugin-Tools ergänzen die Built-in-Tools
- **→ API** (`04-api.md`): `routes/plugins.py` — CRUD-Endpoints
