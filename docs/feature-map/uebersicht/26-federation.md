# Feature Map: Federation — Multi-Server-Verbund

> **Modul:** `core/src/hydrahive/federation/`  
> **Frontend:** `frontend/src/features/federation/`  
> **Was:** Mehrere HH2-Instanzen können miteinander kommunizieren.  
> **Warum:** Homelab mit mehreren Servern — Agents können sich gegenseitig beauftragen.

---

## Konzept

```
Server A (Main)              Server B (Projektserver)
├── Seven of Nine   ─────────────────────────────→  ├── Geralt (project-agent)
├── Buddy           ←─────────────────────────────  ├── ISBN-Extractor
└── ...             ask_agent("geralt@projektx-b")  └── ...
```

Format: `persona@workstation-name` — z.B. `geralt@projektx-till`

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `federation/__init__.py` | Federation-Init |
| `federation/registry.py` | Bekannte Server-Instanzen verwalten |
| `federation/client.py` | HTTP-Client für Cross-Instance-Requests |
| `federation/router.py` | Routing: lokaler Agent oder Remote-Handoff? |
| `federation/auth.py` | Inter-Server-Auth (Shared-Secret oder mTLS) |
| `api/routes/federation.py` | API-Endpoints für Federation-Mgmt |

---

## Server-Registrierung

```json
{
  "id": "projektx-till",
  "name": "Projektserver Till",
  "url": "https://projektx.local",
  "auth_token": "credential:federation-projektx",
  "agents": ["geralt", "isbn-extractor"],
  "last_seen": "2026-06-02T10:00:00",
  "status": "online"
}
```

---

## Routing-Logik

```python
# ask_agent Tool:
agent_id = "geralt@projektx-till"

# federation/router.py:
if "@" in agent_id:
    persona, workstation = agent_id.split("@")
    server = registry.get_server(workstation)
    return client.forward_handoff(server, persona, task, context)
else:
    return local_agentlink.send_task(agent_id, task)
```

---

## Inter-Server-Auth

Jeder Federation-Request trägt einen signierten Header:
```
X-HH2-Federation-Token: <signed-jwt>
X-HH2-Source: "main-server"
```

Target-Server prüft Signatur gegen gespeichertes Secret.

---

## API-Endpoints

| Endpoint | Beschreibung |
|---|---|
| `GET /api/federation/servers` | Registrierte Server |
| `POST /api/federation/servers` | Server registrieren |
| `DELETE /api/federation/servers/{id}` | Server entfernen |
| `POST /api/federation/servers/{id}/ping` | Verbindung testen |
| `POST /api/federation/handoff` | Incoming Handoff empfangen (für Remote-Server) |

---

## Verwandte Subsysteme

- **→ AgentLink** (`14-agentlink.md`): Federation nutzt AgentLink-Protokoll
- **→ Auth** (`21-auth-security.md`): Inter-Server-Auth
- **→ Credentials** (`32-credentials.md`): Federation-Secrets im Credential-Store
