# HydraHive 2.0 — Exhaustive Feature Map

> **Erstellt:** 2026-06-02  
> **Zweck:** Vollständige Dokumentation aller Subsysteme für Buddy-Agents  
> **Prinzip:** Lieber 10× zu viel als zu wenig. Alles ist dokumentiert.

---

## Index aller Subsysteme (36 Dateien)

### Core Engine
| Datei | Subsystem | Kurzbeschreibung |
|---|---|---|
| `01-runner.md` | Runner / LLM-Loop | Herz des Systems. Agent-Ausführung, Tool-Dispatch, Iterations-Steuerung |
| `02-tools.md` | Tools | Alle ~45 Agent-Tools. REGISTRY, Dispatcher, Custom-Tools |
| `03-db.md` | Datenbank | SQLite-Hauptschicht + PostgreSQL-Mirror. Alle Tabellen. |
| `04-api.md` | FastAPI | Alle Routes, Middleware-Stack, Startup-Sequenz |
| `05-agents.md` | Agents | Konfiguration, Typen (Master/Project/Specialist/Buddy) |
| `06-compaction.md` | Compaction | Context-Window-Management. Summaries, Triggers, Strategien |

### Features & Module
| Datei | Subsystem | Kurzbeschreibung |
|---|---|---|
| `07-butler.md` | Butler | Visueller Flow-Builder. Automation ohne Code. |
| `08-communication.md` | Communication | WhatsApp, Discord, E-Mail. Multi-Messenger-Integration |
| `09-buddy.md` | Buddy | Persönlicher Agent pro User. Chat, Voice, Skills, Profil |
| `10-plugins.md` | Plugins | Dynamische Tool-Erweiterungen. Python-Packages. |
| `11-skills.md` | Skills | Markdown-Prompt-Templates. Wiederverwendbare Anweisungen. |
| `12-llm.md` | LLM | Provider-Catalog, OpenRouter, Modell-Verwaltung, Media-Models |
| `13-mcp.md` | MCP | Model Context Protocol. Externe MCP-Server als Tool-Quellen. |
| `14-agentlink.md` | AgentLink | Agent-zu-Agent-Handoffs. ask_agent-Protokoll. |
| `15-projects.md` | Projects | Workspaces, Git-Integration, Samba-Toggle, Members |
| `16-datamining.md` | Datamining | Langzeitgedächtnis. Session-Search, Timeline, Semantic, Graph |
| `17-memory.md` | Memory | Strukturiertes Agent-Gedächtnis. Key/Value, Confidence, TTL |
| `18-patientenakte.md` | Patientenakte | FHIR R4. Diagnosen, Medikamente, Labor, Impfungen, Dokumente |

### Frontend
| Datei | Subsystem | Kurzbeschreibung |
|---|---|---|
| `19-frontend-chat.md` | Chat UI | Haupt-Chat-Interface. Messages, Tool-Cards, Emotes, Workspace |
| `20-frontend-architecture.md` | Frontend-Architektur | React/Vite/TypeScript. Feature-Folder-Pattern. Routing. |

### Infrastruktur
| Datei | Subsystem | Kurzbeschreibung |
|---|---|---|
| `21-auth-security.md` | Auth & Security | JWT, API-Keys, Rate-Limiting, Lockout, Prompt-Injection-Schutz |
| `22-streaming.md` | Streaming | SSE. Real-time Token-Streaming vom Runner zum Frontend. |
| `23-vms.md` | VMs | QEMU/KVM. Lifecycle, Snapshots, Browser-VNC. |
| `24-containers.md` | Containers | LXC/Docker. Lifecycle, Stats, Logs, Console. |
| `25-extensions.md` | Extensions | Installierbare Erweiterungen. Tool-Registrierung. |
| `26-federation.md` | Federation | Multi-Server-Verbund. Cross-Instance-Handoffs. |
| `27-multimodal.md` | Multimodal | TTS, Bildgenerierung, Video, Musik, Transkription. OpenRouter. |
| `28-samba.md` | Samba | SMB-Shares auf Projekt-Workspaces. |
| `29-voice.md` | Voice | STT+TTS+Voice-Mode. Sprachsteuerung. |
| `30-credentials.md` | Credentials | AES-256-Vault. Secrets für Tools und Federation. |
| `31-settings.md` | Settings | Systemkonfiguration. Umgebungsvariablen, DB-Overrides. |

### Spezial-Module
| Datei | Subsystem | Kurzbeschreibung |
|---|---|---|
| `32-zahnfee.md` | Zahnfee | Zahngesundheits-Tracking. FDI-Schema, Termine, KI-Analyse. |
| `33-scratchpad.md` | Scratchpad | User-Notizen + Agent-Zone. Zwei-Zonen-Modell. |
| `34-webmin.md` | Webmin | Server-Monitoring via XML-RPC. CPU, RAM, Disk, SMART. |
| `35-system-hooks.md` | System-Hooks | Event-Hooks + APScheduler. Background-Tasks. |

---

## Kritische Architekturregel

**EINE Richtung für Imports:**
```
api → runner → tools → db (Grundschicht)
```
Niemals zirkulär. Niemals `db` importiert `runner`.

**VERBOTEN:**
- `db` importiert `runner`
- `runner` importiert `api`
- `tools` importiert `runner`

---

## Deployment-Stack

```
nginx (Reverse Proxy, SSL-Terminierung)
  ↓
uvicorn (ASGI, FastAPI)
  ↓
HydraHive2 Core (Python 3.11+)
  ├── SQLite (primär)
  ├── PostgreSQL (optional, Mirror)
  └── Redis (optional, Caching)

Frontend:
  React 18 + Vite → static dist/ ← nginx serviert
```

---

## Datenpfade

| Pfad | Inhalt |
|---|---|
| `/opt/hydrahive2/` | Code (Core + Frontend) |
| `/var/lib/hydrahive2/` | Runtime-Daten |
| `/var/lib/hydrahive2/workspaces/master/` | Master-Workspace |
| `/var/lib/hydrahive2/workspaces/projects/` | Projekt-Workspaces |
| `/var/lib/hydrahive2/agents/` | Agent-Memory, Observations |
| `/var/lib/hydrahive2/credentials.enc` | Verschlüsselter Credential-Vault |
| `/var/lib/hydrahive2/db/hydrahive.db` | SQLite-Hauptdatenbank |
| `/etc/hydrahive2/` | System-Config |
| `/etc/samba/hh-projects.d/` | Samba-Share-Configs |

---

## Emotes

159 Hydra-Emotes in `frontend/public/illustrations/emoticons/`.
Format: `:hydra-NAME:` im Chat.
Generiert via `generate_image`-Tool, eingebunden via `remarkHydraEmotes.ts`.
