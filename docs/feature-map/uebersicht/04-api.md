# Feature Map: API — FastAPI Routes & Middleware

> **Modul:** `core/src/hydrahive/api/`  
> **Was:** Alle HTTP-Endpoints des Systems. FastAPI, Port 8765, via nginx proxied.  
> **Warum:** Das Tor zur Außenwelt — Frontend, Messenger, externe Services kommunizieren alle hier.

---

## Startup

| Datei | Was |
|---|---|
| `main.py` | FastAPI-App-Instanz. Alle Router werden hier eingehängt. |
| `lifespan.py` | Startup/Shutdown-Events. DB-Init, MCP-Start, Communication-Start. |
| `version.py` | API-Version-Endpoint (`GET /api/version`) |

---

## Middleware

| Datei | Typ | Was |
|---|---|---|
| `middleware/auth.py` | JWT-Auth | Prüft Bearer-Token, setzt `request.state.user` |
| `middleware/api_keys.py` | API-Key-Auth | Alternative zu JWT für externe Clients |
| `middleware/users.py` | User-Enrichment | Lädt User-Objekt aus DB nach Auth |
| `middleware/client_ip.py` | IP-Extraktion | Korrekte IP auch hinter nginx (X-Forwarded-For) |
| `middleware/inbound_ratelimit.py` | Rate-Limiting | Pro-User-Request-Throttle |
| `middleware/lockout.py` | Brute-Force-Schutz | IP-Lockout nach zu vielen Fehlversuchen |
| `middleware/errors.py` | Error-Handling | Globaler Exception-Handler → strukturierte JSON-Errors |
| `middleware/secret_compare.py` | Timing-Safe | `hmac.compare_digest` für Secret-Vergleiche |

---

## Route-Gruppen

### Auth & Users
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/auth.py` | `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/logout` | JWT-Login/Logout, Refresh-Token |
| `routes/users.py` | `GET/POST/PUT/DELETE /api/users/*` | User-CRUD, Passwort-Änderung, Avatar |

### Agents & Sessions
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/agents.py` | `GET/POST/PUT/DELETE /api/agents/*` | Agent CRUD, Config, Tools, Skills |
| `routes/agent_memory.py` | `GET/POST/DELETE /api/agents/{id}/memory/*` | Agent-Memory lesen/schreiben/löschen |
| `routes/sessions.py` | `GET/POST/DELETE /api/chat/sessions/*` | Session CRUD, Liste, Titel |
| `routes/sessions_messages.py` | `GET /api/chat/sessions/{id}/messages` | Message-History lesen |

### Chat & Streaming
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/streaming.py` | `POST /api/chat/sessions/{id}/messages`, `GET /api/chat/sessions/{id}/stream` | Haupt-Chat-Endpoint + SSE-Stream |
| `routes/_sse.py` | Helper | SSE-Event-Generator, Heartbeat |

### Buddy
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/buddy.py` | `GET /api/buddy`, `PUT /api/buddy/config`, `GET/POST /api/buddy/sessions` | Buddy-Agent-Config und Sessions |

### Butler
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/butler.py` | `GET/POST/PUT/DELETE /api/butler/rules/*` | Butler-Rules CRUD |
| `routes/_butler_route_helpers.py` | Helper | Validierungs- und Parse-Hilfsfunktionen |

### Projects
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/projects.py` | `GET/POST/PUT/DELETE /api/projects/*` | Projekt CRUD |
| `routes/projects_info.py` | `GET /api/projects/{id}/info` | Projekt-Infos, Stats |
| `routes/projects_files.py` | `GET /api/projects/{id}/files/*` | File-Tree, Datei-Inhalt lesen |
| `routes/projects_files_write.py` | `POST/PUT/DELETE /api/projects/{id}/files/*` | Dateien schreiben/löschen |
| `routes/projects_git.py` | `GET /api/projects/{id}/git/*` | Git-Status, Log, Branches |
| `routes/projects_git_ops.py` | `POST /api/projects/{id}/git/*` | Git-Commit, Push, Pull |
| `routes/projects_git_manage.py` | `POST /api/projects/{id}/git/init` | Git-Repo initialisieren |
| `routes/projects_samba.py` | `POST/DELETE /api/projects/{id}/samba` | Samba-Share an/abschalten |
| `routes/projects_servers.py` | `GET/POST/PUT/DELETE /api/projects/{id}/servers/*` | Dev-Server-Configs |
| `routes/_project_route_helpers.py` | Helper | Pfad-Validierung, Permission-Check |

### LLM & Models
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/llm.py` | `GET /api/llm/models`, `GET /api/llm/speech-models`, `GET /api/llm/transcribe-models`, `GET /api/llm/video-models` | Live-Modell-Listen |
| `routes/llm_catalog.py` | `GET /api/llm/catalog` | Provider-Katalog |
| `routes/llm_oauth.py` | `GET/POST /api/llm/oauth/*` | OAuth-Flows für LLM-Provider |

### Communication (Messenger)
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/communication.py` | `GET/PUT /api/communication/*` | Allgemeine Communication-Config |
| `routes/communication_whatsapp.py` | `GET/POST /api/communication/whatsapp/*` | WhatsApp-Config, Status |
| `routes/communication_whatsapp_incoming.py` | `POST /api/webhooks/whatsapp` | Eingehende WhatsApp-Messages |
| `routes/communication_whatsapp_routes.py` | Helper | WhatsApp-Route-Registrierung |
| `routes/communication_discord.py` | `GET/POST /api/communication/discord/*` | Discord-Config |
| `routes/communication_discord_routes.py` | Helper | Discord-Route-Registrierung |
| `routes/_wa_voice.py` | Helper | WhatsApp Voice-Message Handling |

### Datamining
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/datamining.py` | `POST /api/datamining/search`, `/semantic`, `/timeline`, `/today` | Datamining-Queries |
| `routes/datamining_stats.py` | `GET /api/datamining/stats` | Datamining-Statistiken |
| `routes/datamining_transfer.py` | `POST /api/datamining/transfer` | Daten-Import in Mirror |
| `routes/datamining_issues.py` | `GET /api/datamining/issues` | Datamining-Issue-Tracking |
| `routes/_datamining_rechunk.py` | Helper | Re-Chunking für Mirror |

### Skills & Plugins & MCP
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/skills.py` | `GET/POST/PUT/DELETE /api/skills/*` | Skill CRUD, Skill-Body lesen |
| `routes/_skill_route_helpers.py` | Helper | Skill-Validierung |
| `routes/plugins.py` | `GET/POST/DELETE /api/plugins/*` | Plugin-Hub, Install/Uninstall |
| `routes/mcp.py` | `GET/POST/PUT/DELETE /api/mcp/*` | MCP-Server CRUD |
| `routes/_mcp_schemas.py` | Helper | MCP-Schema-Validierung |

### Credentials & Scratchpad
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/credentials.py` | `GET/POST/PUT/DELETE /api/credentials/*` | Credential-Store CRUD |
| `routes/scratchpad.py` | `GET/PUT /api/scratchpad` | Scratchpad lesen/schreiben |

### Infra (VMs, Container, Backup, Extensions)
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/vms.py` | Haupt-VM-Router | VMs verwalten |
| `routes/vms_lifecycle.py` | `POST /api/vms/{id}/start|stop|pause|resume` | VM-Lifecycle |
| `routes/vms_snapshots.py` | `GET/POST/DELETE /api/vms/{id}/snapshots` | VM-Snapshots |
| `routes/vms_vnc.py` | `GET /api/vms/{id}/vnc` | VNC-Token |
| `routes/vms_ops.py` | `POST /api/vms/{id}/resize|clone` | VM-Operationen |
| `routes/vms_imports.py` | `POST /api/vms/import` | VM-Image-Import |
| `routes/vms_isos.py` | `GET/POST/DELETE /api/vms/isos` | ISO-Verwaltung |
| `routes/containers.py` | Haupt-Container-Router | Container verwalten |
| `routes/containers_crud.py` | CRUD-Endpoints | Container erstellen/löschen |
| `routes/containers_ops.py` | `POST /api/containers/{id}/start|stop` | Container-Operationen |
| `routes/container_console.py` | `GET /api/containers/{id}/console` | WebSocket-Console |
| `routes/backup.py` | `POST/GET /api/backup/*` | Backup erstellen/wiederherstellen |
| `routes/extensions.py` | `GET/POST/PUT/DELETE /api/extensions/*` | Extensions CRUD |
| `routes/_extensions_runner.py` | Helper | Extension-Ausführung |
| `routes/_extensions_docker.py` | Helper | Docker-basierte Extensions |
| `routes/_extensions_status.py` | Helper | Extension-Status |
| `routes/_extensions_stream.py` | Helper | Extension-Output-Streaming |

### Health, FHIR, Federation, System
| Route-Datei | Endpoints | Beschreibung |
|---|---|---|
| `routes/health_data.py` | `GET/POST /api/health/*` | Apple Health Daten |
| `routes/fhir.py` | `GET/POST /api/fhir/*` | FHIR R4 Ressourcen |
| `routes/patientenakte.py` | `GET/POST/PUT/DELETE /api/akte/*` | Patientenakte CRUD |
| `routes/federation.py` | `GET/POST/DELETE /api/federation/*` | Federation-Verbindungen |
| `routes/external_instances.py` | `GET/POST /api/external-instances/*` | Externe HH2-Instanzen |
| `routes/system.py` | `GET /api/system/status` | System-Status |
| `routes/system_admin.py` | `POST /api/system/restart|update` | Admin-Operationen |
| `routes/system_bridge.py` | `POST /api/system/bridge` | System-Bridge (intern) |
| `routes/system_samba.py` | `GET/POST /api/system/samba` | System-weite Samba-Config |
| `routes/dashboard.py` | `GET /api/dashboard` | Dashboard-Daten |
| `routes/analytics.py` | `GET /api/analytics/*` | Session-Analytics |
| `routes/tailscale.py` | `GET/POST /api/tailscale/*` | Tailscale-Status/Config |
| `routes/research_apis.py` | `GET /api/research/*` | Research-API-Proxies |
| `routes/agentlink.py` | `POST/GET /api/agentlink/*` | AgentLink-Handoff-Endpoints |
| `routes/ega.py` | `POST /api/ega/import` | EGA-Daten-Import |
| `routes/workspace.py` | `GET /api/workspace/*` | Workspace-Infos |
| `routes/files.py` | `GET/POST/DELETE /api/files/*` | Allgemeiner File-Upload/-Download |
| `routes/stt.py` | `POST /api/stt` | Speech-to-Text (Wyoming) |
| `routes/tts.py` | `POST /api/tts` | Text-to-Speech |
| `routes/zahnfee.py` | `POST /api/zahnfee/*` | Cleanup-Jobs |

---

## Middleware-Reihenfolge

```
Request
  → client_ip (IP setzen)
  → inbound_ratelimit (Rate-Check)
  → lockout (Brute-Force-Check)
  → auth (JWT oder API-Key prüfen)
  → users (User laden)
  → Route-Handler
  → errors (Exception → JSON)
Response
```

---

## Verwandte Subsysteme

- **→ Runner** (`01-runner.md`): `streaming.py` ruft `runner.run()` auf
- **→ Auth/Security** (`21-auth-security.md`): Middleware-Details
- **→ Streaming** (`22-streaming.md`): SSE-Details
- **→ Communication** (`08-communication.md`): Webhook-Endpoints
