# Feature Map: MCP — Model Context Protocol

> **Modul:** `core/src/hydrahive/mcp/`  
> **Was:** Integration von MCP-Servern als Tool-Quellen. Agents können MCP-Tools genau wie Built-in-Tools nutzen.  
> **Warum:** MCP ist der aufkommende Standard für LLM-Tool-Integration. Drittanbieter-Server sofort nutzbar.

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `mcp/__init__.py` | MCP-System-Init |
| `tool_bridge.py` | Bridge zwischen Runner und MCP-Servern. `PREFIX = "mcp__"`. |

---

## Wie MCP funktioniert

```
Agent-Config:
  "mcp_servers": ["my-mcp-server"]

Runner startet:
  → mcp_bridge.schemas_for_servers(["my-mcp-server"])
  → Verbindet sich mit MCP-Server (stdio / HTTP / SSE)
  → Lädt Tool-Schemas vom Server
  → Tool-Names bekommen Präfix: "mcp__<server-id>__<tool-name>"

LLM ruft Tool auf:
  → dispatcher erkennt "mcp__"-Präfix
  → mcp_bridge.call(tool_name, args)
  → MCP-Server führt Tool aus
  → Result zurück an LLM
```

---

## MCP-Transport-Typen

| Typ | Beschreibung | Use Case |
|---|---|---|
| `stdio` | Subprocess, kommuniziert via stdin/stdout | Lokale Programme, CLIs |
| `http` | HTTP-Requests an HTTP-Server | Web-Services, APIs |
| `sse` | Server-Sent Events | Streaming-fähige Server |

---

## MCP-Server-Config (in DB)

```json
{
  "id": "my-mcp-server",
  "name": "My Custom MCP Server",
  "transport": "stdio",
  "command": "/usr/local/bin/my-mcp-server",
  "args": ["--config", "/etc/my-config.json"],
  "env": {"API_KEY": "credential:my-api-key"},
  "enabled": true
}
```

---

## Eigene MCP-Server von HydraHive

HH2 liefert eigene MCP-Server mit:

### `mcp-servers/datamining/`
- Macht Datamining-Funktionen als MCP-Tools verfügbar
- Nützlich für externe Clients die MCP sprechen

### `mcp-servers/hydrahive-api/`
- Wrapper um die HH2-API als MCP-Server
- Ermöglicht externen Agents Zugriff auf HH2-Funktionen

### `mcp-servers/minimax/`
- MiniMax-spezifische Funktionen via MCP

---

## Tool-Naming

```
mcp__<server-id>__<tool-name>

Beispiel:
  Server-ID: "filesystem"
  Tool: "read_file"
  → "mcp__filesystem__read_file"
```

---

## API-Endpoints

| Endpoint | Beschreibung |
|---|---|
| `GET /api/mcp` | Alle konfigurierten MCP-Server |
| `POST /api/mcp` | Neuen MCP-Server hinzufügen |
| `PUT /api/mcp/{id}` | MCP-Server-Config ändern |
| `DELETE /api/mcp/{id}` | MCP-Server entfernen |
| `POST /api/mcp/{id}/test` | Verbindung testen |

---

## Verwandte Subsysteme

- **→ Runner / Dispatcher** (`01-runner.md`): MCP-Tool-Calls gehen durch Dispatcher
- **→ Plugins** (`10-plugins.md`): Plugins sind ähnlich, aber anders implementiert
- **→ Tools** (`02-tools.md`): MCP-Tools ergänzen REGISTRY und Plugin-Tools
