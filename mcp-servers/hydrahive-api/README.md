# HydraHive API MCP Server

FastMCP-basierter MCP-Server der Claude Code vollwertigen Zugriff auf HydraHive gibt:
Sessions, Agenten, Workspace, Datamining und bidirektionale AgentLink-Integration.

## 20 Tools

| Prefix | Tools |
|--------|-------|
| `hh_` (System) | `hh_status`, `hh_token_stats` |
| `hh_` (Sessions) | `hh_list_sessions`, `hh_get_session`, `hh_get_messages`, `hh_send_message` |
| `hh_` (Agenten) | `hh_list_agents`, `hh_get_agent`, `hh_update_agent` |
| `hh_` (Workspace) | `hh_list_projects`, `hh_list_files`, `hh_read_file` |
| `hh_dm_` (Datamining) | `hh_dm_search`, `hh_dm_get_session`, `hh_dm_list_sessions`, `hh_dm_stats` |
| `hh_al_` (AgentLink) | `hh_al_status`, `hh_al_send`, `hh_al_check_inbox`, `hh_al_reply` |

## Installation

### Abhängigkeiten

```bash
cd mcp-servers/hydrahive-api
pip install -e ".[dev]"
```

### Claude Code Integration

Server hinzufügen (Passwort oder API-Key eintragen):

```bash
# Option A: User/Passwort
claude mcp add hydrahive -s user \
  -e HH_BASE_URL=https://192.168.3.22 \
  -e HH_USER=admin \
  -e HH_PASS=DEIN_PASSWORT \
  -e HH_AGENT_ID=claude-code \
  -e HH_VERIFY_SSL=0 \
  -- python3 /home/<user>/hydrahive2/mcp-servers/hydrahive-api/server.py

# Option B: API-Key (hhk_...)
claude mcp add hydrahive -s user \
  -e HH_BASE_URL=https://192.168.3.22 \
  -e HH_API_KEY=hhk_DEIN_API_KEY \
  -e HH_AGENT_ID=claude-code \
  -e HH_VERIFY_SSL=0 \
  -- python3 /home/<user>/hydrahive2/mcp-servers/hydrahive-api/server.py
```

Passwort nachträglich setzen:

```bash
claude mcp update hydrahive -s user -e HH_PASS=ECHTES_PASSWORT
```

Status prüfen:

```bash
claude mcp list
```

## Umgebungsvariablen

| Variable | Pflicht | Beispiel | Beschreibung |
|---|---|---|---|
| `HH_BASE_URL` | Ja | `https://192.168.3.22` | HydraHive-Basis-URL |
| `HH_USER` | Wenn kein API-Key | `admin` | Login-Username |
| `HH_PASS` | Wenn kein API-Key | `...` | Login-Passwort |
| `HH_API_KEY` | Wenn kein User/Pass | `hhk_...` | API-Key |
| `HH_AGENT_ID` | Nein | `claude-code` | AgentLink-Name (Default: claude-code) |
| `HH_VERIFY_SSL` | Nein | `0` | SSL-Verifikation aus (0 = off) |

## Tests

```bash
cd mcp-servers/hydrahive-api
python3 -m pytest tests/ -v
```

## Dateistruktur

```
mcp-servers/hydrahive-api/
├── server.py          # FastMCP-Einstiegspunkt (20 Tools, Lifespan)
├── _auth.py           # JWT-Login oder API-Key, Token-Refresh
├── _rest.py           # Async REST-Client für alle HH API-Calls
├── _agentlink.py      # WebSocket + In-Memory-Handoff-Queue
├── tools/
│   ├── system.py      # hh_status, hh_token_stats
│   ├── sessions.py    # hh_list_sessions, hh_get_session, ...
│   ├── agents.py      # hh_list_agents, hh_get_agent, hh_update_agent
│   ├── workspace.py   # hh_list_projects, hh_list_files, hh_read_file
│   ├── agentlink.py   # hh_al_status, hh_al_send, ...
│   └── datamining.py  # hh_dm_search, hh_dm_get_session, ...
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_rest.py
│   ├── test_server.py
│   ├── test_agentlink.py
│   └── test_tools_*.py
└── pyproject.toml
```
