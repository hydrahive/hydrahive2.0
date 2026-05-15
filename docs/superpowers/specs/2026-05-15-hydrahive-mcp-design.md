# HydraHive API MCP-Server — Design-Spec

> Stand: 2026-05-15 | Status: Freigegeben

---

## Ziel

Claude Code als vollwertigen internen Agenten in HydraHive einbinden — mit Zugriff auf alle
relevanten API-Bereiche und bidirektionaler AgentLink-Integration (Handoffs senden + empfangen).

---

## Entscheidung

**Option B: Ein MCP-Server-Prozess mit Background-WebSocket.**

FastMCP bedient Tool-Calls. Ein asyncio-Hintergrund-Task hält die AgentLink-WebSocket-Verbindung
und schreibt eingehende Handoffs in eine In-Memory-Queue. Ein zweiter Prozess (Daemon) ist nicht
nötig. Der bestehende Datamining-MCP-Server wird als Modul eingegliedert — kein separater Prozess.

---

## Dateistruktur

```
mcp-servers/hydrahive-api/
├── server.py          # FastMCP-Instanz, Startup/Shutdown-Lifecycle
├── _auth.py           # Login via User/Pass oder API-Key, Token-Refresh
├── _rest.py           # Zentraler REST-Client (alle HH API-Calls)
├── _agentlink.py      # WebSocket-Verbindung + In-Memory-Handoff-Queue
├── tools/
│   ├── sessions.py    # Session lesen, Nachrichten schicken
│   ├── agents.py      # Agenten lesen, Config updaten
│   ├── workspace.py   # Projekt-Dateien lesen
│   ├── agentlink.py   # Handoffs senden, Inbox prüfen, antworten
│   ├── system.py      # Health, Token-Stats, AgentLink-Status
│   └── datamining.py  # Datamining-Suche, Sessions, Stats
└── pyproject.toml
```

---

## Konfiguration

Alle Werte via Umgebungsvariablen:

| Variable | Beispiel | Bedeutung |
|---|---|---|
| `HH_BASE_URL` | `https://192.168.178.218` | HydraHive-Basis-URL |
| `HH_USER` | `admin` | Login-Username (alternativ zu API-Key) |
| `HH_PASS` | `...` | Login-Passwort |
| `HH_API_KEY` | `hhk_...` | API-Key (alternativ zu User/Pass) |
| `HH_AGENT_ID` | `claude-code` | Unser Name in AgentLink |
| `HH_VERIFY_SSL` | `0` | SSL-Verifikation (0 = off für self-signed) |

---

## Tools

### Sessions
| Tool | Parameter | Beschreibung |
|---|---|---|
| `hh_list_sessions` | `agent_id?`, `limit?` | Laufende + letzte Sessions |
| `hh_get_session` | `session_id` | Details + Token-Verbrauch |
| `hh_get_messages` | `session_id`, `limit?` | Nachrichten-Verlauf |
| `hh_send_message` | `session_id`, `message` | Nachricht in Session injizieren |

### Agenten
| Tool | Parameter | Beschreibung |
|---|---|---|
| `hh_list_agents` | — | Alle Agenten mit Kurzinfo |
| `hh_get_agent` | `agent_id` | Vollständige Config |
| `hh_update_agent` | `agent_id`, `field`, `value` | Config-Feld setzen |

### Workspace
| Tool | Parameter | Beschreibung |
|---|---|---|
| `hh_list_projects` | — | Alle Projekte |
| `hh_list_files` | `project_id`, `path?` | Verzeichnis-Listing |
| `hh_read_file` | `project_id`, `path` | Dateiinhalt lesen (read-only) |

### System
| Tool | Parameter | Beschreibung |
|---|---|---|
| `hh_status` | — | Health, Version, Uptime |
| `hh_token_stats` | — | Token/Kosten-Übersicht |

### AgentLink
| Tool | Parameter | Beschreibung |
|---|---|---|
| `hh_al_status` | — | Verbindungsstatus, bekannte Agenten |
| `hh_al_send` | `to_agent`, `task_type`, `description`, `context?` | Handoff abschicken |
| `hh_al_check_inbox` | — | Eingegangene Handoffs aus der Queue |
| `hh_al_reply` | `state_id`, `result` | Handoff beantworten |

### Datamining
| Tool | Parameter | Beschreibung |
|---|---|---|
| `hh_dm_search` | `q`, `event_type?`, `from_date?`, `to_date?`, `limit?` | Volltextsuche |
| `hh_dm_get_session` | `session_id` | Session-Chunks zusammengesetzt |
| `hh_dm_list_sessions` | `limit?` | Letzte Sessions mit Event-Anzahl |
| `hh_dm_stats` | — | Token/Kosten-Statistiken |

---

## Datenfluss

### Startup
```
1. _auth.py   Login → JWT-Token cachen (oder API-Key direkt nutzen)
2. _rest.py   GET /api/agentlink/status → AgentLink-URL ermitteln
3. _agentlink POST /states → als "claude-code" bei AgentLink registrieren
4. _agentlink WebSocket verbinden → asyncio-Background-Task starten
5. FastMCP    Tools registrieren → bereit für Calls
```

### Eingehender Handoff
```
AgentLink WS-Push → _agentlink.py empfängt WSEvent
                  → GET /states/{id} → State holen
                  → asyncio.Queue
hh_al_check_inbox → Queue leeren, Liste zurückgeben
hh_al_reply(id)   → POST /states mit reply_to:<id> in reason
```

### Ausgehender Handoff
```
hh_al_send(...)   → State-Objekt bauen
                  → POST /states an AgentLink-URL
                  → state_id zurückgeben (für reply-Matching)
```

---

## Fehlerbehandlung

- Alle Tools geben bei Fehler `{"error": "...", "code": "..."}` zurück — kein Exception-Crash
- 401 → automatischer Token-Refresh (re-login), dann Retry
- WebSocket-Disconnect: exponentieller Backoff, max 5 Versuche, Status in `hh_al_status()` sichtbar
- `hh_read_file` ist read-only — kein Write-Zugriff auf Workspace
- SSL-Fehler bei `HH_VERIFY_SSL=0` werden ignoriert (self-signed Zertifikat)

---

## Installation in Claude Code

`.claude/settings.json` (oder global `~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "hydrahive": {
      "command": "python",
      "args": ["/home/till/claudeneu/mcp-servers/hydrahive-api/server.py"],
      "env": {
        "HH_BASE_URL": "https://192.168.178.218",
        "HH_USER": "admin",
        "HH_PASS": "...",
        "HH_AGENT_ID": "claude-code",
        "HH_VERIFY_SSL": "0"
      }
    }
  }
}
```

---

## Abgrenzung

- Der bestehende `mcp-servers/datamining/server.py` bleibt erhalten für HydraHive-interne Nutzung
- Der neue Server ersetzt ihn als Claude-Code-MCP-Eintrag
- Kein Write-Zugriff auf Workspace-Dateien (read-only)
- Keine VM/Container/Kommunikations-Tools (zu spezifisch, kein Mehrwert für Claude Code)
