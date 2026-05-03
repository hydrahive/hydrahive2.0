# HydraHive Datamining MCP-Server

Sucht in der PostgreSQL-Events-Tabelle. Kein Core-Code, kein Prompt — reines SQL.

## Installation

```bash
cd mcp-servers/datamining
pip install -e .
```

## Konfiguration in HydraHive

Admin → MCP → Server hinzufügen:

```json
{
  "name": "datamining",
  "command": "python",
  "args": ["/opt/hydrahive2/mcp-servers/datamining/server.py"],
  "env": {
    "PG_MIRROR_DSN": "postgresql://hydrahive_mirror:pass@127.0.0.1:5432/hydrahive_mirror"
  }
}
```

DSN steht nach der Installation in `/etc/hydrahive2/pg_mirror.dsn`.

## Tools

| Tool | Beschreibung |
|---|---|
| `search` | Volltextsuche (ILIKE) über alle Events, optional gefiltert |
| `get_session` | Komplette Session rekonstruieren, Chunks zusammengesetzt |
| `list_sessions` | Letzte Sessions auflisten mit Event-Anzahl |
