# Feature Map: AgentLink — Agent-zu-Agent Handoff

> **Modul:** `core/src/hydrahive/agentlink/`  
> **Was:** Protokoll und Client für Agent-zu-Agent-Kommunikation. ask_agent-Tool nutzt das.  
> **Warum:** Komplexe Tasks können auf spezialisierte Sub-Agents delegiert werden.

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `client.py` | HTTP-Client. `send_task()`, `poll_result()`. Kommuniziert mit AgentLink-Service. |
| `protocol.py` | Datenmodelle: `HandoffState`, `TaskRequest`, `TaskResult` |
| `_ws_listener.py` | WebSocket-Listener für async Ergebnis-Notifications |
| `_ws_state.py` | WebSocket-Verbindungs-State |

---

## Datenfluss

```
Master-Agent ruft ask_agent auf:
  Tool: ask_agent(agent_id="project-agent-1", task="Analysiere diese Datei")

tools/ask_agent.py:
  → agentlink/client.py: send_task(agent_id, task, context)
    → POST /api/agentlink/handoff
    → Response: {handoff_id: "uuid", status: "queued"}
  
  → Poll bis Ergebnis da:
    → GET /api/agentlink/handoff/{id}/status
    → Oder: WebSocket-Notification

Target-Agent (project-agent-1):
  → Holt Task: GET /api/agentlink/handoff/pending
  → Führt Task aus (Runner.run())
  → Liefert Ergebnis: POST /api/agentlink/handoff/{id}/result

Master-Agent bekommt Ergebnis zurück:
  → ask_agent gibt HandoffResult.text zurück
  → Master kann weiter arbeiten
```

---

## ask_agent-Tool Parameter

```python
ask_agent(
    agent_id="project-agent-1",    # Ziel-Agent ID oder Name
    task="Was ist die Antwort?",    # Task-Beschreibung
    task_type="feature",            # bug_fix|feature|review|research|refactor
    context={
        "error_log": "...",         # Optionale Zusatz-Infos
        "code_snippet": "...",
        "related_files": ["a.py"],
        "files": [{"name": "a.py", "content": "..."}],
        "errors": ["TypeError: ..."],
        "git": {"branch": "main", "commit": "abc123"}
    },
    required_skills=["code-review"] # Skills die der Ziel-Agent haben muss
)
```

---

## Federation via AgentLink

AgentLink ermöglicht auch Cross-Instance-Handoffs:
```
Lokaler Master → ask_agent(agent_id="geralt@projektx-till")
                                              ↑
                               Format: "persona@workstation-name"
```

Der AgentLink-Service routet den Task an die richtige Instanz.

---

## Persistenz

- Handoffs werden in `db/agent_handoffs.py` gespeichert
- Status: `queued → running → completed | failed`
- Timeout: konfigurierbar (Default: 5 Minuten)
- Ergebnisse bleiben in DB für Datamining

---

## API-Endpoints (routes/agentlink.py)

| Endpoint | Beschreibung |
|---|---|
| `POST /api/agentlink/handoff` | Neuen Handoff erstellen |
| `GET /api/agentlink/handoff/pending` | Offene Handoffs abholen (für Target-Agent) |
| `GET /api/agentlink/handoff/{id}/status` | Status abfragen |
| `POST /api/agentlink/handoff/{id}/result` | Ergebnis einliefern |
| `GET /api/agentlink/ws` | WebSocket für Push-Notifications |

---

## Import-Regeln (CRITICAL)

```python
# AgentLink darf NUR importiert werden in:
from hydrahive.agentlink import ...     # Im agentlink/-Modul selbst
from hydrahive.tools.ask_agent import ... # Im ask_agent-Tool
from hydrahive.api.routes.agentlink import ... # Im API-Route

# VERBOTEN:
# Import von agentlink in runner.py, db.py, etc.
```

---

## Verwandte Subsysteme

- **→ Tools** (`02-tools.md`): `ask_agent.py` ist das Tool das AgentLink nutzt
- **→ Runner** (`01-runner.md`): Target-Agent nutzt Runner für Task-Ausführung
- **→ Federation** (`26-federation.md`): Cross-Instance-Handoffs
- **→ DB** (`03-db.md`): `agent_handoffs` Tabelle
