# HydraHive 2.0 — Architektur-Übersicht

> **Stand:** 2026-05-07  
> **Zielgruppe:** Entwickler, Contributors, System-Architekten  
> **Verwandte Dokumente:** [SPEC.md](../SPEC.md) · [CLAUDE.md](../CLAUDE.md) · [README.md](../README.md)

---

## Inhaltsverzeichnis

1. [Vision & Design-Prinzipien](#vision--design-prinzipien)
2. [High-Level-Architektur](#high-level-architektur)
3. [Datenfluss](#datenfluss)
4. [Backend-Komponenten](#backend-komponenten)
5. [Frontend-Architektur](#frontend-architektur)
6. [Datenschicht](#datenschicht)
7. [Sicherheitsmodell](#sicherheitsmodell)
8. [Plugin-System](#plugin-system)
9. [Deployment-Architektur](#deployment-architektur)
10. [Design-Entscheidungen (WHY)](#design-entscheidungen-why)

---

## Vision & Design-Prinzipien

HydraHive 2.0 ist ein **selbst gehostetes KI-Agenten-System** — kein SaaS, keine Cloud-Abhängigkeit, keine Daten die woanders landen. Es läuft als einzelner systemd-Service auf einem Linux-Server und stellt eine Web-UI + Multi-Channel-Messaging-Integration bereit.

### Kern-Prinzipien

1. **3-Ebenen-Architektur**: Master → Project → Specialist Agents
2. **Zero-Context-Loss**: Append-only Compaction mit `firstKeptEntryId`-Pointer
3. **Feature Co-location**: Alles was zusammengehört liegt zusammen (kein Shotgun Surgery)
4. **Kleine Dateien**: Max ~200 Zeilen pro Datei, eine Verantwortung pro Modul
5. **Plugin-First**: Alle Erweiterungen als Plugins, Core bleibt schlank
6. **No Docker**: Direktes systemd-Deployment, kein Compose-Overhead

---

## High-Level-Architektur

```
┌────────────────────────────────────────────────────────────────────┐
│                         User-Interfaces                            │
├────────────┬────────────┬────────────┬──────────┬──────────────────┤
│  Web-UI    │ WhatsApp   │  Discord   │ Telegram │  Matrix          │
│ (React/TS) │ (Baileys)  │ (discord.py) │        │ (conduwuit)      │
└────────────┴────────────┴────────────┴──────────┴──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Reverse Proxy (nginx)                         │
│  • TLS-Termination                                                  │
│  • Static-File-Serving (/index.html, /assets/*)                    │
│  • API-Proxy (/api/* → 127.0.0.1:8765)                             │
│  • Security-Headers (CSP, X-Frame-Options, Permissions-Policy)      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Python 3.12)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │   API Routes   │  │    Runner    │  │   Communication       │  │
│  │   (FastAPI)    │  │  (LLM Loop)  │  │  (Discord, WhatsApp)  │  │
│  └────────────────┘  └──────────────┘  └───────────────────────┘  │
│           │                  │                    │                │
│           ▼                  ▼                    ▼                │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │              Core Subsystems                               │   │
│  ├────────────┬──────────┬──────────┬──────────┬─────────────┤   │
│  │  Agents    │  Tools   │  Skills  │  Butler  │  Plugins    │   │
│  │  (Config)  │ (shell,  │ (Markdown│ (Trigger │  (Dynamic   │   │
│  │            │  file,   │  Prompts)│  /Action)│   Loading)  │   │
│  │            │  git)    │          │          │             │   │
│  └────────────┴──────────┴──────────┴──────────┴─────────────┘   │
│           │                  │                    │                │
│           ▼                  ▼                    ▼                │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │              External Integrations                         │   │
│  ├────────────┬──────────┬──────────┬──────────┬─────────────┤   │
│  │ LiteLLM    │ AgentLink│   MCP    │  OAuth   │  Tailscale  │   │
│  │ (Multi-    │ (Agent   │ (stdio,  │ (Anthro- │  (Mesh VPN) │   │
│  │  Provider) │  State   │  HTTP,   │  pic,    │             │   │
│  │            │ Transfer)│  SSE)    │ OpenAI)  │             │   │
│  └────────────┴──────────┴──────────┴──────────┴─────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Persistence Layer                           │
├─────────────────────┬───────────────────────┬───────────────────────┤
│   SQLite (Core DB)  │   JSON Files (Config) │  Workspaces (Git)     │
│  • sessions         │  • agents.json        │  • /projects/<name>/  │
│  • messages         │  • skills/*.md        │  • /master/<user>/    │
│  • tool_calls       │  • users.json         │  • /specialists/      │
│  • events           │  • llm_providers.json │                       │
│  • datamining       │  • mcp_servers.json   │                       │
└─────────────────────┴───────────────────────┴───────────────────────┘
```

---

## Datenfluss

### 1. User-Request → Agent-Response

```
User (Web/Messenger)
    │
    │ HTTP POST /api/chat/sessions/{id}/messages
    ▼
FastAPI Route (api/routes/chat.py)
    │
    │ Validate JWT, check session ownership
    ▼
Runner (runner/runner.py)
    │
    │ 1. Load agent config + system prompt + skills
    │ 2. Load session history (with compaction)
    │ 3. Build LiteLLM request (tools, context, user message)
    ▼
LiteLLM → Anthropic/OpenAI/Groq/...
    │
    │ Stream response chunks
    ▼
Runner (dispatcher.py)
    │
    │ Parse tool calls
    │ Execute tools (shell_exec, file_read, ask_agent, ...)
    │ Loop until final_text
    ▼
Database (db/events.py)
    │
    │ Store messages, tool calls, thinking blocks
    ▼
SSE Stream → Frontend
    │
    │ Real-time message updates
    ▼
User sees response
```

### 2. Agent → Agent (AgentLink)

```
Master Agent
    │
    │ Tool: ask_agent(agent_id="project-agent-1", task="...")
    ▼
AgentLink Client (agentlink/client.py)
    │
    │ POST /api/handoff (AgentLink Service)
    │ Payload: {task, context, files, required_skills}
    ▼
AgentLink Service (external)
    │
    │ Queue state transfer
    ▼
Project Agent Runner
    │
    │ Fetch task via GET /api/handoff/pending
    │ Execute task in isolated workspace
    │ Return result state
    ▼
AgentLink Service
    │
    │ Deliver result back to Master Agent
    ▼
Master Agent continues
```

### 3. Compaction (Context Management)

```
Session reaches token limit
    │
    ▼
Compaction Hook (compaction/hooks.py)
    │
    │ Trigger: after_assistant_text
    ▼
Compactor (compaction/compactor.py)
    │
    │ 1. Select events [firstKeptEntryId : -100]
    │ 2. Send to LLM: "summarize this into 5 bullet points"
    │ 3. Create compaction_block event
    │ 4. Increment firstKeptEntryId
    ▼
Database (events.py)
    │
    │ Append compaction block, keep pointer
    │ Old events remain (append-only), but hidden in context
    ▼
Next request uses compacted context
```

---

## Backend-Komponenten

### Verzeichnis-Struktur

```
core/src/hydrahive/
├── agents/             # Agent persistence, validation, bootstrap
├── agentlink/          # AgentLink client integration
├── api/
│   ├── routes/         # FastAPI endpoints (grouped by domain)
│   └── middleware/     # JWT auth, CORS, rate-limiting
├── backup/             # Backup creation + restore
├── buddy/              # Personal Buddy agent (auto-created per user)
├── butler/             # Visual flow-builder (Trigger → Condition → Action)
├── communication/      # Messenger adapters (Discord, WhatsApp, Matrix)
├── compaction/         # Context compaction logic
├── containers/         # LXC/Docker container management (plugin-ready)
├── credentials/        # Per-user HTTP credential store
├── db/                 # Database layer (SQLite, PostgreSQL mirror)
│   ├── events.py       # Core event storage
│   ├── mirror.py       # PostgreSQL mirror for Datamining
│   └── mirror_query.py # Advanced query layer
├── llm/                # LLM provider catalog, model metadata
├── mcp/                # MCP server management (stdio, HTTP, SSE)
├── messaging/          # Internal messaging system
├── oauth/              # OAuth flows (Anthropic, OpenAI Codex, MiniMax)
├── plugins/            # Plugin loader, manifest parser, hub client
├── projects/           # Project management, workspace isolation
├── runner/             # Agent-LLM loop (core execution engine)
│   ├── runner.py       # Main loop
│   ├── dispatcher.py   # Tool dispatch + execution
│   ├── _call.py        # Single LLM call abstraction
│   ├── _codex_provider.py  # OpenAI Codex Predicted Outputs
│   ├── _llm_bridge_backends.py  # LiteLLM backend wrappers
│   └── tool_confirmation.py  # Per-tool confirmation UI
├── samba/              # Samba share management for workspaces
├── settings/           # Settings singleton (env-based config)
├── skills/             # Skill loader, markdown parser
├── tailscale/          # Tailscale mesh VPN integration
├── tools/              # Core tools (shell_exec, file_*, git_*, ask_agent)
├── vms/                # VM management (QEMU/KVM)
└── voice/              # STT (Wyoming-Whisper) + TTS helpers
```

### Modul-Verantwortungen (Beispiele)

| Modul | Verantwortung | Import-Regel |
|-------|--------------|-------------|
| `runner/runner.py` | Agent-LLM-Loop, Tool-Execution orchestrieren | Import von tools, llm, db — kein Import von api |
| `api/routes/chat.py` | REST-Endpoints für Chat-Sessions | Import von runner, db — kein Business-Logic-Code hier |
| `tools/shell_exec.py` | shell_exec-Tool | Nur stdlib + settings — keine db/llm/api-Imports |
| `db/events.py` | Event-Persistence | Nur sqlalchemy + pydantic — keine llm/runner-Imports |
| `compaction/compactor.py` | Compaction-Logik | Import von llm, db — kein Import von runner/api |
| `agentlink/client.py` | AgentLink HTTP-Client | Nur httpx + settings — kein Import von db/runner |

**Verboten:**
- Zirkuläre Imports (Runner ↔ API)
- AgentLink-Imports außerhalb `agentlink/`, `tools/ask_agent.py`, `api/routes/agentlink.py`
- Hardcodierte Pfade (alles über `settings.*`)
- `print()` statements (nur `logging.getLogger(__name__)`)

---

## Frontend-Architektur

### Feature-Folder-Struktur

```
frontend/src/
├── features/               # Feature-basierte Co-location
│   ├── auth/              # Login, JWT, permissions
│   │   ├── LoginPage.tsx
│   │   ├── permissions.ts  ← EINZIGE Permission-Source
│   │   └── api.ts
│   ├── chat/              # Chat-UI, message rendering, tool cards
│   │   ├── ChatPage.tsx
│   │   ├── useChat.ts     ← Chat-State-Hook
│   │   ├── api.ts         ← Chat-API-Calls
│   │   ├── types.ts
│   │   ├── MessageInput.tsx
│   │   ├── ToolCards.tsx
│   │   └── tool_cards/    ← Tool-specific cards
│   ├── agents/            # Agent CRUD, config
│   ├── projects/          # Project management, file tree
│   ├── datamining/        # Timeline, graph, semantic search
│   ├── llm/               # LLM provider catalog, OAuth
│   ├── plugins/           # Plugin hub, install/uninstall
│   ├── mcp/               # MCP server config
│   ├── butler/            # Butler flow-builder UI
│   ├── communication/     # Messenger channel config
│   └── ...
├── shared/                # Shared components (NOT feature-specific)
│   ├── components/        # Reusable UI (Button, Card, Modal)
│   ├── hooks/             # Generic hooks (useDebounce, useLocalStorage)
│   └── utils/             # Pure functions (formatDate, parseJSON)
├── assets/                # Images, icons
└── i18n/                  # Translations (de, en)
```

### Design-Pattern

- **Feature Co-location**: Alles was zu Chat gehört liegt in `features/chat/` — kein Splitting in `components/`, `hooks/`, `api/`, `types/` über mehrere Verzeichnisse
- **Single Source of Truth**: Permissions nur in `features/auth/permissions.ts`, nie dupliziert
- **API-Layer**: Jedes Feature hat `api.ts` mit allen HTTP-Calls für diese Domäne
- **Type-Safety**: Strikte TypeScript-Types, keine `any`
- **Atomic Components**: Kleine Komponenten (<200 Zeilen), eine Verantwortung

---

## Datenschicht

### SQLite (Core DB)

```sql
-- Haupttabellen
sessions            # Agent-Sessions (user_id, agent_id, created_at)
session_events      # Messages, tool_calls, thinking_blocks (append-only)
session_files       # Attached files (media, documents)
session_metadata    # firstKeptEntryId, compaction_count

agents              # Agent configs (name, model, tools[], system_prompt)
users               # users.json mirror
llm_providers       # Provider credentials (encrypted)
mcp_servers         # MCP server configs
plugins             # Installed plugins
```

**Append-Only Pattern:**
- Events werden NIE gelöscht, nur `firstKeptEntryId` verschoben
- Compaction erstellt neue Events (`compaction_block`), alte bleiben
- Context-Window: Events ab `firstKeptEntryId` bis Ende
- Full-History für Debugging/Datamining verfügbar

### PostgreSQL Mirror (Optional)

- Repliziert SQLite-Events nach PostgreSQL
- Aktiviert erweiterte Datamining-Features:
  - Graph-Visualisierung (Networkx + Numba)
  - Semantic Search (pgvector)
  - Timeline-Aggregationen
- Wird nur für `/api/datamining/*` genutzt
- Core-Funktionalität bleibt SQLite-basiert

### JSON-Konfiguration

```
/var/lib/hydrahive2/
├── agents.json             # Agent-Definitionen
├── users.json              # User-DB (bcrypt-hashes)
├── llm_providers.json      # Provider-Credentials (encrypted)
├── mcp_servers.json        # MCP-Server-Configs
├── skills/                 # Skill-Markdown-Files
│   ├── code-review.md
│   ├── debugging.md
│   └── git-workflow.md
└── workspaces/
    ├── master/<user_id>/   # Master-Agent-Workspaces
    ├── projects/<proj_id>/ # Project-Agent-Workspaces
    └── specialists/<spec_id>/  # Specialist-Agent-Memory
```

---

## Sicherheitsmodell

### Ebenen-Modell

| Ebene | Mechanismus | Zweck |
|-------|------------|-------|
| **1. User-Auth** | JWT (HS256, bcrypt) | Wer darf überhaupt ins System? |
| **2. Ownership** | Per-User-Agent-Isolation | Welche Agents/Projects gehören diesem User? |
| **3. Tool-Filtering** | `tools[]` am Agent | Welche Tools darf dieser Agent nutzen? |
| **4. Tool-Confirmation** | `require_tool_confirm: bool` | Muss User vor Tool-Call bestätigen? |
| **5. Workspace-Isolation** | Pfad-Checks in file/shell-Tools | Projekt-Agents nur im eigenen Workspace |
| **6. Service-Hardening** | systemd-Sandbox | `ProtectSystem=strict`, `NoNewPrivileges` |

### Warum KEINE OS-Level-Sandbox pro Agent?

**Entscheidung (aus SPEC.md):**
- Agents arbeiten wie Claude Code — volle Tool-Macht, kein "darf ich nicht"
- OS-Sandbox bricht privilegierte Tools (VM-Management, Container, Tailscale)
- HydraHive 1 hatte Sandbox → wurde dadurch unbrauchbar
- Sicherheit kommt aus **User-Auth + Owner-Check + Tool-Confirmation**, nicht aus Linux-User-Isolation

**Konsequenz:**
- Alle Agents laufen als `hydrahive`-Systemuser
- Kein `sudo -u agent-123` pro Agent
- Workspace-Isolation via Application-Layer (Pfad-Checks in Tools)

### JWT-Flow

```
User → POST /api/auth/login {username, password}
    ↓
Backend: bcrypt.verify(password, user.password_hash)
    ↓
JWT erstellen: {user_id, username, is_admin, exp: 7d}
    ↓
Frontend: localStorage.setItem("authToken", jwt)
    ↓
Alle API-Calls: Authorization: Bearer <jwt>
    ↓
Middleware: verify_jwt() → FastAPI Dependency
```

---

## Plugin-System

### Architektur

```
plugins/
├── loader.py           # Plugin discovery, manifest parsing
├── manifest.py         # PluginManifest schema (Pydantic)
├── tool_bridge.py      # Tool registration from plugins
└── hub_client.py       # HydraHive Plugin Hub API client

Plugin-Verzeichnis:
/var/lib/hydrahive2/plugins/<plugin-name>/
├── manifest.json       # Metadata, dependencies, tools, hooks
├── __init__.py         # Plugin entry point
└── tools/              # Tool implementations
```

### Manifest-Schema (Beispiel)

```json
{
  "name": "git-stats",
  "version": "1.0.0",
  "description": "Git repository statistics",
  "tools": [
    {
      "name": "git_commits",
      "description": "List recent commits",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {"type": "string"},
          "limit": {"type": "integer", "default": 10}
        }
      }
    }
  ],
  "dependencies": ["gitpython>=3.1"],
  "hooks": {
    "after_tool_call": "plugins.git_stats.hooks:log_git_usage"
  }
}
```

### Plugin-Lifecycle

1. **Installation**: Download → Extract → Validate manifest → `pip install dependencies`
2. **Registration**: Tools werden in Tool-Registry eingetragen
3. **Agent-Assignment**: Admin aktiviert Plugin am Agent via `plugins[]`-Liste
4. **Runtime**: Runner lädt nur aktivierte Plugins, registriert deren Tools
5. **Update**: Check Hub API → Download new version → Reload runner
6. **Uninstall**: Remove directory → Cleanup DB entries

**Design-Regel:**
- Core-Code wird NIE für Plugins geändert
- Plugins greifen auf Core-APIs zu, nicht umgekehrt
- Plugins können eigene Routes registrieren (via Hook)

---

## Deployment-Architektur

### Production (Ubuntu 24.04 via Installer)

```
┌─────────────────────────────────────────────────────────────────┐
│                         Server (Ubuntu 24.04)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  nginx (Port 80/443)                                            │
│    │                                                            │
│    ├─ / → /var/www/hydrahive2/index.html (SPA)                 │
│    ├─ /api/* → http://127.0.0.1:8765 (Backend Proxy)           │
│    └─ /assets/* → /var/www/hydrahive2/assets/ (Static Files)   │
│                                                                 │
│  systemd-Service: hydrahive2.service                            │
│    ├─ User: hydrahive (unprivileged)                           │
│    ├─ ExecStart: /opt/hydrahive2/.venv/bin/python -m hydrahive │
│    ├─ Restart: always                                          │
│    ├─ NoNewPrivileges: true                                    │
│    ├─ ProtectSystem: strict                                    │
│    └─ ReadWritePaths: /var/lib/hydrahive2 /etc/hydrahive2      │
│                                                                 │
│  systemd-Path: hydrahive2-update.path                           │
│    ├─ PathChanged: /var/lib/hydrahive2/update.trigger          │
│    └─ Trigger: hydrahive2-update.service (runs update.sh)      │
│                                                                 │
│  Daten:                                                         │
│    ├─ /var/lib/hydrahive2/ (Workspaces, DB, JSON-Configs)      │
│    ├─ /etc/hydrahive2/ (Secret-Key, users.json)                │
│    └─ /opt/hydrahive2/ (Git-Repo, Code, venv)                  │
│                                                                 │
│  Logs:                                                          │
│    ├─ journalctl -u hydrahive2 -f                              │
│    └─ /var/log/nginx/access.log                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Dev-Setup (lokaler Laptop)

```bash
# Backend (FastAPI)
cd core
python3.12 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m hydrahive

# Frontend (Vite)
cd frontend
npm install
npm run dev  # → http://localhost:5173

# Dev-Start-Script (Backend + Frontend parallel)
./dev-start.sh
```

**Unterschiede Dev ↔ Production:**
- Dev: Backend auf `:8001`, Vite Dev-Server auf `:5173` (HMR)
- Prod: nginx served alles unter einer Domain
- Dev: CORS-Origins include `localhost:5173`
- Prod: CORS-Origins leer (nginx same-origin)

### Self-Update-Flow

```
Admin klickt "Update" in UI
    ↓
POST /api/system/update-trigger
    ↓
Backend: touch /var/lib/hydrahive2/update.trigger
    ↓
systemd-Path-Watcher: hydrahive2-update.path
    ↓
Trigger: hydrahive2-update.service
    ↓
Run (als root): /opt/hydrahive2/installer/update.sh
    ├─ git pull
    ├─ .venv/bin/pip install -e core --upgrade
    ├─ cd frontend && npm install && npm run build
    ├─ systemctl restart hydrahive2
    └─ rm /var/lib/hydrahive2/update.trigger
```

**Warum als root?**
- `git pull` + `systemctl restart` brauchen Schreibrechte auf `/opt/hydrahive2`
- API-Prozess läuft als `hydrahive` (unprivileged) → kann nicht selbst restarten
- Trigger-File-Pattern trennt Privilege-Escalation sauber (API schreibt nur File, systemd macht Rest)

---

## Design-Entscheidungen (WHY)

### 1. Warum SQLite statt PostgreSQL für Core?

**Entscheidung:** SQLite für Sessions/Events, PostgreSQL optional nur für Datamining-Mirror

**Begründung:**
- ✅ Zero-Config: Kein separater DB-Server, kein Networking, kein User-Management
- ✅ Append-Only perfekt für SQLite: kein Locking-Problem bei Writes
- ✅ Backup = File-Copy: `cp hydrahive.db hydrahive.db.backup`
- ✅ Single-Node-System: Kein Multi-Server-Szenario geplant
- ❌ PostgreSQL-Overhead für kleine Instanz nicht gerechtfertigt

**Konsequenz:**
- Core bleibt portabel (läuft auf Raspberry Pi 5)
- Datamining-Features (Graph, Semantic Search) werden optional via Mirror

### 2. Warum keine OS-Level-Sandbox pro Agent?

**Entscheidung:** Alle Agents laufen als `hydrahive`-User, keine `sudo -u agent-123`

**Begründung:**
- ✅ HydraHive 1 hatte Sandbox → wurde unbrauchbar (zu viele "darf ich nicht")
- ✅ Privileged-Tools (VM-Management, Container, Tailscale) funktionieren nur mit breiten Rechten
- ✅ Sicherheit kommt aus User-Auth + Owner-Pattern + Tool-Confirmation, nicht aus Linux-User-Isolation
- ❌ Agent-pro-User würde `/dev/kvm`, Network-Namespaces, `systemctl` brechen

**Konsequenz:**
- Agents arbeiten wie Claude Code (volle Tool-Macht)
- Sicherheit = **wer darf Agent starten** (JWT) + **welche Tools** (`tools[]`) + **Bestätigung** (`require_tool_confirm`)

### 3. Warum Feature-Folders statt Layer-Structure?

**Entscheidung:** `features/chat/` statt `components/Chat + hooks/useChat + api/chatApi`

**Begründung:**
- ✅ Co-location: Alles was zu Chat gehört liegt zusammen → kein Shotgun Surgery
- ✅ Änderungen an Chat-Feature berühren nur ein Verzeichnis
- ✅ Neue Features = neues Verzeichnis (einfaches Onboarding)
- ❌ Layer-Structure verteilt eine Änderung auf 4-5 Verzeichnisse

**Konsequenz:**
- Code bleibt wartbar auch bei 50+ Features
- Delete-Feature = `rm -rf features/xyz/` (keine残ified Files)

### 4. Warum max ~200 Zeilen pro Datei?

**Entscheidung:** Eiserne Regel: Datei > 200 Zeilen → aufteilen

**Begründung:**
- ✅ Lesbarkeit: 200 Zeilen passen auf einen Bildschirm (auch mit Comments)
- ✅ Single Responsibility: Wenn eine Datei zu groß wird, macht sie zu viel
- ✅ Merge-Conflicts seltener: Kleinere Dateien = weniger Kollisionen
- ✅ LLM-Context: Claude kann 200 Zeilen komplett erfassen ohne Truncation

**Konsequenz:**
- Lieber 1000 kleine Dateien als 30 Monster-Dateien
- Review-Prozess prüft Dateigröße (siehe `hh-review`-Skill)

### 5. Warum AgentLink als externer Service?

**Entscheidung:** AgentLink ist eigenständiges Repo, kein HydraHive-Code

**Begründung:**
- ✅ Separation of Concerns: AgentLink = State-Transfer, HydraHive = Agent-Execution
- ✅ Federation: AgentLink kann zwei HydraHive-Server verbinden
- ✅ Technologie-Freiheit: AgentLink könnte auf Rust/Go migriert werden ohne HydraHive zu brechen
- ✅ Skalierung: AgentLink kann separate Redis-Cluster nutzen

**Konsequenz:**
- HydraHive importiert AgentLink nur als HTTP-Client (`agentlink/client.py`)
- AgentLink-Code nie in HydraHive-Repo (außer Installer-Integration)

### 6. Warum Append-Only statt Delete?

**Entscheidung:** Events werden nie gelöscht, nur `firstKeptEntryId` verschoben

**Begründung:**
- ✅ Full-History für Debugging: Alle Tool-Calls, alle Fehler bleiben abrufbar
- ✅ Datamining: Timeline/Graph brauchen vollständige Event-Chain
- ✅ Compaction-Transparenz: User sieht was kompaktiert wurde
- ✅ No-Data-Loss: Kein versehentliches Löschen wichtiger Context

**Konsequenz:**
- DB wächst langfristig → Backup-Strategy wichtig
- PostgreSQL-Mirror für Datamining (SQLite bleibt für Runtime)

### 7. Warum systemd statt Docker?

**Entscheidung:** Direktes systemd-Deployment, kein Docker/Compose

**Begründung:**
- ✅ Simplicité: Ein Service-File, keine Compose-YAML, kein Image-Build
- ✅ Ressourcen: Kein Container-Overhead (wichtig für Raspberry Pi 5)
- ✅ Debugging: `journalctl -u hydrahive2 -f` statt Docker-Logs
- ✅ Security: systemd-Sandbox (`ProtectSystem=strict`) funktioniert direkt

**Konsequenz:**
- Installer muss systemd-Units anlegen (kein `docker-compose up`)
- Production = Ubuntu 24.04 LTS (andere Distros später)

---

## Zusammenfassung

HydraHive 2.0 ist eine **schlanke, selbst gehostete, plugin-erweiterte KI-Agenten-Platform**.

**Kern-Eigenschaften:**
- 🐝 **3-Ebenen-Architektur**: Master → Project → Specialist
- 🔒 **Zero-Cloud**: Alles lokal, keine Daten woanders
- 🧩 **Plugin-First**: Core bleibt klein, Features als Plugins
- 📦 **Single-Binary**: Ein systemd-Service, SQLite-DB, JSON-Config
- 🚀 **Self-Update**: Admin klickt Button, systemd macht `git pull + rebuild + restart`
- 🔐 **JWT + bcrypt**: Pro-User-Isolation, keine OS-Sandbox pro Agent
- 📊 **Append-Only**: Kein Kontextverlust, Full-History, Compaction mit Pointer

**Tech-Stack:**
- Backend: Python 3.12 + FastAPI + LiteLLM
- Frontend: React 19 + TypeScript + Vite
- DB: SQLite (Core) + PostgreSQL (Mirror, optional)
- Proxy: nginx
- Service: systemd

**Deployment:** Ein Bash-Befehl (`sudo ./install.sh`) → fertig.

---

**Fragen? Siehe [SPEC.md](../SPEC.md) für vollständige Produktspezifikation oder [CLAUDE.md](../CLAUDE.md) für Arbeitsregeln.**
