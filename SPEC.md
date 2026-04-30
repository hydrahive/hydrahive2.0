# HydraHive2 — Produktspezifikation

> Stand: 2026-04-28 | Status: Freigegeben

---

## Vision

Ein selbst gehostetes KI-Agenten-System das auf einem Linux-Server mit einem Bash-Befehl
installiert wird und danach wie ein privates Claude-Team funktioniert — Masteragenten mit
vollständiger Handlungsfähigkeit, Projektagenten mit isolierten Workspaces, ausleihbare
Spezialisten.

---

## Nicht-Ziele

- Kein SaaS, kein Abo, keine Cloud-Abhängigkeit
- Kein Docker, kein Kubernetes — läuft direkt auf dem Host (systemd-Services)
- Kein Vendor-Lock-in — LLM-Provider wechseln = eine Zeile Config
- Keine eingebauten Features die nicht in dieser Spec stehen — alles andere wird Plugin
- Kein "ich darf das nicht" — Agenten arbeiten wie Claude Code, nicht wie ein gesperrter Chatbot

---

## Architektur: 3 Ebenen

```
User (WhatsApp / Discord / Telegram / Matrix / Web)
        │
        ▼
  ┌─────────────┐
  │ Masteragent │  ← persönlich, Soul, Gedächtnis, Fähigkeiten, kein Kontextverlust
  └──────┬──────┘
         │ AgentLink
         ▼
  ┌─────────────────┐
  │  Projektagent   │  ← workspace-gebunden, task-fokussiert, eigene Config
  └────────┬────────┘
           │ AgentLink (leihen)
           ▼
  ┌─────────────────────┐
  │  Spezialist-Agent   │  ← Domain-Experte, ausleihbar, gibt Ergebnis zurück
  └─────────────────────┘
```

**AgentLink** ist ein eigenständiger Service (kein HydraHive-Code) der den direkten
State-Transfer zwischen Agents übernimmt — kein Chat-Overhead, kein Latenz-Problem.
Wird vom Installer mitinstalliert. Ermöglicht auch Federation zwischen zwei HydraHive-Servern.

---

## Komponenten

### Masteragent

- Eine Instanz pro Benutzer, automatisch beim User-Anlegen erstellt
- Hat eine **Soul** (Identität, Charakter, Verhaltensmuster als Markdown-Dateien)
- Hat **Gedächtnis** (Markdown-Files, lesen + schreiben, lernt aus Erfahrungen)
- Hat **Fähigkeiten / Skills** (wiederverwendbare Verhaltensmuster, analog Claude Code Skills)
- **Kein Kontextverlust** — 3-stufige Compaction wie OpenClaw: autoCompact + microCompact + sessionMemoryCompact
- **Unrestricted** — kein Ausführungsmodus, arbeitet wie Claude Code, tut was nötig ist
- Kann alle Messenger empfangen und beantworten
- Kann Projektagenten über AgentLink beauftragen
- Kann Spezialisten direkt ausleihen
- Vergibt Ausführungsmodi an Projekt- und Spezialisten-Agenten
- Tools: alle (shell, file, web, git, memory, ask_agent, MCP, email)

### Projektagent

- Eine Instanz pro Projekt
- Kein Soul, keine persönliche Identität — ist auf das Projekt fixiert
- Hat einen isolierten **Workspace** (eigenes Verzeichnis, eigenes Git-Repo)
- Kennt nur seinen Workspace — kein Zugriff außerhalb
- Eigene Config (LLM-Modell, Tools, Ausführungsmodus)
- Kann Spezialisten über AgentLink ausleihen
- Tools: file (nur Workspace), shell (nur Workspace), git, memory (Projekt-Memory), MCP

### Spezialist-Agent

- Domänen-Experte (Kochrezepte, Security, Datenbank, Medizin, was auch immer)
- Wird nicht dauerhaft betrieben — wird bei Bedarf geliehen
- Bekommt Task + Kontext über AgentLink, gibt Ergebnis zurück, ist danach wieder frei
- **Lernt aus Erfahrungen** — schreibt nach jedem Einsatz Notizen in eigene Memory-Files (was funktioniert hat, was nicht, welche Lösung geholfen hat)
- Hat eigene Skills für seine Domäne
- Mehrere Projektagenten / Masteragenten können denselben Spezialisten nutzen (sequenziell)
- Ausführungsmodus: vom Masteragenten oder Admin zugewiesen
- Tools: je nach Domäne konfigurierbar

---

## Tech-Stack

| Schicht | Technologie | Begründung |
|---|---|---|
| Backend | Python 3.12 + FastAPI | bewährt, async, schnell |
| LLM-Abstraktion | LiteLLM | Provider-unabhängig |
| Frontend | React + TypeScript + Vite | bewährt |
| Datenbank | SQLite (Sessions) + PostgreSQL (AgentLink) | SQLite = zero-config für Core |
| Messaging | Redis (AgentLink Pub/Sub) | niedrige Latenz |
| Agent-Kommunikation | AgentLink (externer Service) | eigenständig, autark |
| Reverse Proxy | nginx | TLS-Termination |
| Service-Management | systemd | kein Docker |
| Matrix | conduwuit | selbst gehostet |
| Git | Gitea (optional) | selbst gehostet |

**Verboten:**
- Kein Docker / Compose im Core
- Keine direkten HTTP-Calls zwischen Agents (nur über AgentLink)
- Keine hardcodierten Pfade — alles über Settings-Singleton
- Kein v1-Pattern (Boss/Worker über Chat) — nur AgentLink

---

## Agent-Isolation (Ausführungsebene)

**Entscheidung:** Agenten werden bei der Code-Ausführung auf OS-Ebene isoliert — nicht durch
eigenen Python-Code, sondern durch Linux-Mechanismen. Die API-Schicht (User-Verwaltung, JWT)
bleibt davon unberührt und braucht keine Root-Rechte.

**Warum nicht "alles ist ein Linux-User":**
- `useradd` aus der API heraus würde root im API-Prozess erfordern → inakzeptables Risiko
- Linux-Usernamen (max 32 Zeichen, ASCII) passen nicht zu beliebigen HydraHive-Usernamen
- Zwei parallele Auth-Systeme (Linux-PAM + JWT) erhöhen Komplexität ohne Nutzen

**Was stattdessen:**

| Ebene | Mechanismus |
|---|---|
| HydraHive-User + Auth | bleibt eigene Schicht (users.json + JWT) |
| Agent-Ausführung (`shell_exec` etc.) | systemd-Unit mit `User=hh-agent`, `PrivateTmp=yes`, `ProtectSystem=strict`, `ReadWritePaths=<workspace>` |
| Projekt-Workspaces | Linux-Gruppe `hh-proj-{id}` — alle Agents im Projekt teilen Zugriff per ACL |
| Ressource-Limits | cgroup via systemd (`MemoryMax=`, `CPUQuota=`) |

**Konsequenz für den Installer:**
- Installer legt einen unprivilegierten System-User `hydrahive` für den API-Prozess an
- Installer legt einen System-User `hh-agent` an unter dem alle Agenten-Prozesse laufen
- Projekte bekommen beim Anlegen eine Linux-Gruppe + `setgid` auf dem Workspace-Verzeichnis
- Die API selbst läuft nie als root

**Wann umsetzen:** Beim Bau des Agent-Runners (`agents/master/runner.py`), nicht in der
Grundstruktur. Die Config-Schicht (was jetzt steht) ist davon unabhängig.

---

## Tools für Agenten

### Core-Tools (immer verfügbar, in Python implementiert)

| Tool | Beschreibung |
|---|---|
| `shell_exec` | Shell-Befehle ausführen — **kein** "ich darf nicht", macht einfach |
| `file_read` | Datei lesen |
| `file_write` | Datei schreiben |
| `file_patch` | Datei patch (diff-basiert) |
| `file_search` | Dateien suchen |
| `dir_list` | Verzeichnisinhalt auflisten |
| `web_search` | Websuche (über lokalen SearxNG) |
| `http_request` | HTTP-Requests |
| `read_memory` | Eigene Memory-Notizen lesen |
| `write_memory` | Eigene Memory-Notizen schreiben |
| `todo_write` | Todo-Liste pro Session führen |
| `ask_agent` | Anderen Agenten über AgentLink beauftragen |
| `send_mail` | E-Mail senden (SMTP-Config nachträglich) |

### MCP-Tools (extern, per Config zugewiesen)

stdio + streamableHttp + SSE. Standard-MCP-Server werden vom Installer mitinstalliert:
GitHub, Filesystem, Git, SQLite, Fetch, Time, Sequential Thinking.

Weitere MCP-Server: per Admin-UI hinzufügen, pro Agent zuweisen.

---

## Plugin-System

Erweiterungen kommen als Plugins — **nicht** eingebaut, **nicht** im Core-Code.

```
plugins/
└── mein-plugin/
    ├── plugin.yaml    ← Name, Version, Beschreibung, benötigte Permissions
    ├── tools/         ← Zusätzliche Tools (Python)
    ├── skills/        ← Zusätzliche Skills (Markdown)
    └── installer.sh   ← Setup (Dependencies, Config)
```

Plugins werden über die Admin-UI installiert (Hub). Core-Code wird dabei nie angefasst.
Ein kaputtes Plugin bricht den Core nicht.

---

## Messenger-Integrationen

| Messenger | Methode |
|---|---|
| WhatsApp | Bridge (whatsmeow) |
| Discord | Bot (discord.py) |
| Telegram | Bot (python-telegram-bot) |
| Matrix | Bot (matrix-nio), Homeserver optional via conduwuit |

Jede Integration: eingehende Nachricht → Masteragent → Antwort zurück.
Loop-Detektion damit Bots sich nicht endlos anschreiben.

---

## Web-Konsole (React)

**Design:**
- Dark/Light Theme (beide)
- Mehrsprachig: Deutsch, Englisch, Chinesisch
- Dunkel gehalten, Farbakzente mit Verläufen — bunt aber nicht poppig
- **Responsive**: Desktop = Sidebar links, Mobile = Navbar unten (wie WhatsApp/Telegram)

**Seiten:**
- **Login** — JWT
- **Dashboard** — Systemstatus, laufende Agents
- **Chat** — mit jedem Agenten chatten (SSE-Streaming)
- **Agenten** — anlegen, bearbeiten, Soul/Skills/Tools konfigurieren
- **Projekte** — anlegen, Workspace, Projektagent konfigurieren
- **Spezialisten** — anlegen, Domäne, Skills zuweisen
- **LLM** — Provider, API-Keys, Modelle
- **MCP** — Server verwalten, pro Agent zuweisen
- **System** — Logs, Health, Services, System-Backup/Restore, Tailscale (Admin)
- **Profil** — eigene Daten exportieren/importieren

---

## Backup / Restore

Zwei getrennte Mechanismen für unterschiedliche Use-Cases.

### System-Backup (Admin, Catastrophe-Recovery)

- **Endpoint**: `POST /api/admin/backup` (Admin) → Stream-Download eines `.tar.gz`
- **Restore**: `POST /api/admin/restore` (Admin) → Multipart-Upload + Service-Restart
- **Inhalt**: SQLite-DB (`sessions.db`), `$HH_CONFIG_DIR` (TLS, llm.json, butler/, whatsapp/, mcp/, plugins/), Workspace-Verzeichnisse aller User
- **Format**: `.tar.gz`, unverschlüsselt (Operator legt Backup-Datei selbst sicher ab)
- **UI**: Card auf System-Page (Admin) — Download-Button + Upload-Restore-Button mit Bestätigungs-Dialog
- **Use-Case**: Server-Migration, Disaster-Recovery, vor riskanten Updates

### User-Backup (Self-Service, DSGVO Art. 20 — Datenportabilität)

- **Endpoint**: `POST /api/me/backup` (User) → Stream-Download eines `.tar.gz`
- **Restore**: `POST /api/me/restore` (User) → Multipart-Upload, kein Service-Restart
- **Inhalt** (restlos, alle eigenen Daten):
  - eigene Agents (Config + system_prompt.md + Memory + Workspace-Files)
  - eigene Projekte (Config + Members-Liste + Project-Agent + Workspace-Files inkl. .git/ wenn vorhanden)
  - eigene Sessions inkl. aller Messages, Tool-Calls, Compactions (kein Toggle — DSGVO verlangt restlos)
  - eigene WhatsApp-Filter-Config (`whatsapp/<username>.json`) + WhatsApp-Auth (`whatsapp/<user>/auth/`) wenn vorhanden
  - eigene Butler-Flows
  - eigene MCP-Server-Configs
- **Format**: `.tar.gz`, unverschlüsselt
- **UI**: Card auf Profile-Page (Self-Service) — Download-Button + Upload-Restore-Button
- **Use-Case**: User wechselt Server, will eigene Daten archivieren, DSGVO-Auskunft

### Nicht-Ziele

- Inkrementelle Backups, Backup-Scheduling, externes Off-Host-Backup (Operator-Sache)
- Backup-Verschlüsselung im Code (User soll die Datei selbst encrypted ablegen)
- Cross-User-Restore (Admin kann nicht mit User-Backup einen anderen User wiederherstellen)
- Selektives Restore (alles oder nichts pro Backup-Typ)

---

## Tailscale-Integration

**Zweck:**
- Sicherer Zugang zu HydraHive2 von mobilen Geräten — kein Router-Port-Forwarding nötig
- Verbindung mehrerer HydraHive2-Server untereinander via HydraLink über Tailscale-IPs

**Was HydraHive2 macht:**
- Tailscale auf dem Host installieren (Installer-Phase oder nachträglich per UI)
- Tailscale-Status anzeigen (verbunden / getrennt, Tailscale-IP, Hostname)
- Login per Auth-Key über die UI — kein SSH nötig
- Invite-Link für weitere Geräte/Server generieren (Clipboard-Copy)
- Tailscale-IP automatisch als HydraLink-Endpoint vorschlagen wenn aktiv

**Frontend (System-Page, Admin):**
- Tailscale-Card: Status (verbunden/getrennt), Tailscale-IP, Hostname
- Login-Button → Auth-Key eingeben → verbinden
- Invite-Link generieren → Clipboard-Copy
- Logout-Button

**Installer:**
- Optionale Phase (wie WhatsApp-Bridge)
- Bei `HH_TAILSCALE_AUTHKEY` in der Installer-Config: automatisch einrichten

**Nicht-Ziele:**
- Tailscale in VMs/Containern installieren (bleibt manuell oder über Butler-Flows)
- Eigenes DERP/Control-Plane-Setup
- ACL-Verwaltung aus HydraHive heraus

---

## Installer

```bash
curl -fsSL https://raw.githubusercontent.com/.../install.sh | sudo bash
```

- Ubuntu 24.04 LTS
- Idempotent — nochmal ausführen macht nichts kaputt
- Profile: `lite` (Cloud-APIs) und `full` (+ Ollama, + GPU)
- Installiert: Python-Venv, Node.js Build, nginx, AgentLink, Redis, SQLite, Standard-MCP-Server
- Optional: Gitea, conduwuit (Matrix), WhatsApp-Bridge, Tailscale
- Nach Installation: Browser öffnen → Setup-Wizard → fertig

Update:
```bash
sudo bash update.sh
```

---

## Qualitätsmaßstab

- Agenten arbeiten wie Claude Code: Tools parallel wo möglich, vor Bearbeiten lesen,
  bei Fehlern selbst debuggen, keine sinnlosen Wiederholungsloops
- Kein "ich kann das nicht" — `shell_exec` führt aus, Punkt
- Kontextverlust = Fehler, nicht Feature
- Ein Neustart des Services verliert keine Session-Daten
- Der Installer läuft auf einem frischen Ubuntu 24.04 ohne manuelle Vorbereitung durch

---

## VM-Management (Core-Komponente)

HydraHive2 kann lokale QEMU/KVM Virtual Machines direkt managen — ohne Proxmox- oder
libvirt-Zwischenschicht. Use-Case: dedizierte Anwendungs-VMs (Game-Server, Test-Umgebungen,
Dev-Sandboxes) die von einem Specialist-Agent administriert werden.

### Funktionsumfang
- VM-Lifecycle: erstellen, starten, stoppen (graceful + hard), löschen — Per-User-Owner
- Disk: qcow2-Erzeugung, ISO-Boot, qcow2/raw/vmdk-Import bestehender Images
- Konsole: VNC im Browser via websockify+noVNC, Token pro VM
- Snapshots: erstellen + offline restore
- Networking: Bridged via `br0` (Default, VMs bekommen DHCP-IPs aus dem LAN), Isoliert optional
- Reconciliation-Loop: tatsächlicher Zustand wird kontinuierlich gegen DB abgeglichen,
  kein Drift bei Crash/kill/Reboot

### Nicht-Ziele
- Multi-Host-Cluster (immer einzelner Host)
- Live-Migration zwischen Hosts
- HA / Auto-Failover
- Externes Backup (Snapshots only — Off-host-Backup ist Sache des Hosts)

### Architektur
`core/src/hydrahive/vms/` als Core-Modul (analog `communication/`). Routen unter
`/api/vms/*`, Per-User-Isolation via `owner` wie bei Agents. Frontend `/vms`.
Alle Module max ~150 Zeilen pro Datei, aufgeteilt in models/db/qemu_args/lifecycle/
reconciler/iso/import_job/snapshots/vnc/events/errors.

---

## Container-Management (Core-Komponente, Schwester von VMs)

HydraHive2 kann LXC-Container über **incus** direkt managen. Sweet-Spot zwischen
Docker (zu eng, Layer-FS-Overhead) und VMs (zu schwer, langsamer Boot): kleine
Dauer-Dienste wie SearXNG, Linkding, Vaultwarden, Eigene Tools.

### Funktionsumfang
- Container-Lifecycle: erstellen, starten, stoppen, neu starten, löschen — Per-User-Owner
- Image: aus offiziellem `images:`-Remote (Ubuntu/Debian/Alpine/Arch) oder lokaler Image-Cache
- Konsole: xterm.js im Browser über `incus exec` WebSocket
- Snapshots: live-fähig via `incus snapshot create` (im Gegensatz zu VM-Snapshots offline)
- Networking: gleiche `br0` wie VMs — Container bekommen DHCP-IP aus dem LAN
- Reconciliation: actual_state wird gegen `incus list` abgeglichen
- Storage: dir-Backend (kein BTRFS/ZFS — Loop-Devices sind in nested-LXC nicht verfügbar)

### Nicht-Ziele
- Eigene Container-Image-Erstellung (User installiert in einem laufenden Container und macht Snapshot)
- Multi-Host-Cluster
- Container-zu-Container-Networking abseits br0 (alle teilen sich die Bridge)

### Voraussetzungen
- incus aus Ubuntu-24.04-Standard-Repo (kein Snap, kein PPA)
- Wenn HydraHive2 selbst in einem LXC-Container läuft: Host-LXC braucht
  `security.nesting=1`, AppArmor-Profile darf nicht confined sein. Sonst
  schlägt der Sub-Container-Start mit "Operation not permitted" fehl.
- Storage-Driver: `dir` (kein /dev/loop nötig)

### Architektur
`core/src/hydrahive/containers/` als Core-Modul. Routen unter `/api/containers/*`.
Frontend `/containers` mit eigener Page. Sidebar-Item neben `/vms`.

---

## Butler — Flow-Builder (Core-Komponente)

Der **Butler** ist ein visueller Flow-Builder für Trigger → Condition → Action-Regeln.
Er war im alten HydraHive eines der besten Features und kommt im Neubau wieder rein —
aber sauberer aufgeteilt (Registry-Pattern, kleine Files, echte Validierung).

Ein „Flow" ist ein gerichteter azyklischer Graph aus drei Node-Typen:
- **Trigger** (genau einer am Anfang) — was den Flow auslöst
- **Condition** (beliebig viele, optional) — Verzweigung mit `true`/`false`-Output
- **Action** (eine oder mehrere am Ende) — was passieren soll

Beispiel-Flow: *„Wenn WhatsApp-Nachricht ankommt UND Sender ist in Whitelist UND
es ist Werktag zwischen 9-17 Uhr, dann leite an Master-Agent mit Instruction
`Antworte freundlich und kurz` weiter — sonst antworte fix mit `Bin gerade nicht erreichbar`."*

### Funktionsumfang

**Trigger** (in Phase 2 implementiert, weitere als Plugin nachrüstbar):
- `message_received` — eingehende Channel-Nachricht (whatsapp / telegram / discord / matrix / all)
- `webhook_received` — eingehender HTTP-POST an `/api/webhooks/butler/<hook_id>` (Pro-Hook-Secret als HMAC)
- `email_received` — IMAP-Polling oder externer Webhook
- `git_event_received` — GitHub/Gitea-Webhook (push / pull_request / issues)
- `cron_fired` — zeitgesteuert (cron-Expression)

**Condition** (in Phase 2):
- `time_window` — lokale Systemzeit zwischen `from`/`to` (Mitternacht-Crossing supported)
- `day_of_week` — Wochentage als Toggle-Liste (Mo-So)
- `contact_in_list` — Sender-ID/E-Mail in einer Liste
- `message_contains` — Substring (case-insensitive) im Nachrichten-Text
- `payload_field_equals` / `payload_field_contains` — Punkt-Notation für JSON-Pfade (`pull_request.state`)
- `regex_match` — Regex auf einem Feld

**Action** (in Phase 2):
- `agent_reply` — Nachricht 1:1 an einen Agent weiterreichen
- `agent_reply_with_prefix` — wie oben, aber mit prepended Instruction (`[BUTLER: …]`)
- `reply_fixed` — feste Antwort über den Channel zurückschicken
- `http_post` — HTTP-Call mit Jinja2-Template-Body
- `send_email` — Email senden (nutzt bestehendes `send_mail`-Tool)
- `discord_post` — Discord-Channel-Message
- `git_create_issue` / `git_add_comment` — GitHub/Gitea
- `ignore` — Flow stoppen (Bypass für default-Verhalten)

**Template-Engine**: Jinja2 in allen Action-Params. Filter wie `{{ msg | truncate(50) }}`,
`{{ event.timestamp | strftime("%H:%M") }}`. Sandbox-Mode (kein Code-Eval).

**Persistenz**: pro Flow eine JSON-File unter `$HH_CONFIG_DIR/butler/<owner>/<flow_id>.json`.
Pro-User-Isolation. Optional `scope: "project"` mit `scope_id` für Projekt-Flows.

**Validierung** (vor jedem Save): Pydantic-Models. Genau ein Trigger pro Flow. Keine
zyklischen Edges. Jeder Node mit gültigen Subtype-Params. Keine Orphan-Nodes
(unverbundene Action ohne Pfad zum Trigger).

**Dry-Run**: `POST /api/butler/<flow_id>/dry_run` mit Mock-Event-JSON. Liefert
Trace-Liste der durchlaufenen Nodes + die *would-execute*-Actions zurück, ohne
echte Side-Effects auszuführen.

**Audit**: jeder Flow hat `created_at`, `modified_at`, `modified_by`. Letzte 10
Executions pro Flow im SQLite-Log mit Trigger-Event + erreichten Actions.

### Frontend: ReactFlow-Canvas mit Drag&Drop

Der Editor läuft auf **`@xyflow/react`** — einer ausgereiften React-Library für
Node-Graph-Editoren. Layout:

- **Linke Sidebar** — Node-Palette mit drei Gruppen (Trigger / Condition / Action),
  Items per Drag&Drop ins Canvas ziehbar. Such-Feld zum Filtern.
- **Center Canvas** — ReactFlow-Viewport mit Snap-Grid (15px), Pan/Zoom,
  MiniMap unten rechts, Controls oben rechts. Nodes farbcodiert: Trigger grün,
  Condition blau (zwei Output-Handles), Action orange.
- **Rechte Sidebar (Inspector)** — Subtype-spezifische Param-Maske wenn ein Node
  selektiert ist. Live-Validierung mit Inline-Errors. „Dry Run"-Knopf öffnet
  Test-Event-Dialog.
- **Top-Bar** — Flow-Auswahl-Dropdown, Name-Input, Enabled-Toggle (grün=aktiv),
  Speichern + Löschen.

Der Editor ist kein Spielzeug — der User soll wirklich grafisch Flows bauen,
ziehen, verbinden, verzweigen. Kein YAML-Editor als Fallback.

### Nicht-Ziele

- Schleifen / Recursion zwischen Nodes (Cycle-Guard verhindert)
- Parallele Async-Execution mit Join-Knoten
- Versions-Historie pro Flow (nur `modified_at`/`modified_by`, kein Diff)
- Code-Action (User-Code im Browser ausführen)
- Inline-Skripte in Conditions

### Voraussetzungen

- Trigger-Hooks in den Channel-Adaptern (WhatsApp ruft `butler.dispatch(event)`
  bevor die normale Master-Agent-Route)
- Webhook-Endpoint mit Pro-Hook-Secret-Verwaltung
- Cron-Daemon für `cron_fired` (kann APScheduler im Backend-Prozess sein)
- Jinja2 als Backend-Dependency (Sandbox-Mode aktivieren)

### Architektur

**Backend** (`core/src/hydrahive/butler/`):
- `models.py` — Pydantic-Models (Flow, Node, Edge, TriggerEvent)
- `persistence.py` — Load/Save JSON-Files mit Validation
- `registry/` — drei Registries (triggers/, conditions/, actions/), jede Subtype-Implementation eine eigene Datei <50 Zeilen
- `executor.py` — DFS-Traversal, Cycle-Guard, Trace-Logger
- `template.py` — Jinja2-Sandbox-Wrapper
- `dispatch.py` — Public API: `butler.dispatch(event)` von Channel-Adaptern aufgerufen
- `audit.py` — Execution-Log in SQLite

**API-Routen** (`api/routes/butler.py` + `api/routes/butler_webhooks.py`):
- `GET/POST/PUT/DELETE /api/butler/flows` — CRUD
- `POST /api/butler/flows/<id>/dry_run` — Test-Lauf
- `GET /api/butler/registry` — Liste aller verfügbaren Trigger/Condition/Action-Subtypes mit Param-Schemas (für Inspector-UI)
- `POST /api/webhooks/butler/<hook_id>` — Generischer Webhook-Eingang
- `POST /api/webhooks/git/<provider>/<hook_id>` — Git-Provider-spezifisch (GitHub/Gitea)

**Frontend** (`frontend/src/features/butler/`, jede Datei <150 Zeilen):
- `ButlerPage.tsx` — Haupt-Container mit Flow-Liste in Top-Bar
- `Canvas/Canvas.tsx` — ReactFlow-Viewport, Custom-Node-Renderer
- `Canvas/TriggerNode.tsx` / `ConditionNode.tsx` / `ActionNode.tsx` — Custom-Node-Components
- `Palette/NodePalette.tsx` — Drag-Source-Liste, getrennte Files für PaletteGroup, PaletteItem
- `Inspector/Inspector.tsx` — Switch auf Subtype, lädt entsprechendes Form-Component
- `Inspector/forms/*.tsx` — pro Subtype eine Form-File (TimeWindowForm, MessageContainsForm, …)
- `useFlowState.ts` — Zustand-Hook für Nodes/Edges/Selection
- `api.ts` + `types.ts`

**Phasenplan**:
- **Phase 1** (~½ Tag): Datenmodell, Persistenz, Validierung, Registry-Skelett, REST-CRUD ohne UI
- **Phase 2** (~1 Tag): Executor + 3 Trigger / 5 Conditions / 5 Actions, Dry-Run-Endpoint, Unit-Tests
- **Phase 3** (~1 Tag): ReactFlow-Frontend (Canvas, Palette, Inspector), Save/Load/Toggle
- **Phase 4** (~½ Tag): Trigger-Hooks in WhatsApp-Adapter und Webhook-Endpoint, Audit-Log, Dry-Run-UI
- **Phase 5** (optional): zusätzliche Trigger/Conditions/Actions als Plugin-Pakete

---

## Was explizit NICHT gebaut wird (ohne separate Entscheidung)

- DREAM-System
- Widget-Dashboard mit Drag&Drop
- Collaborative Composer (Yjs)
- Blueprint/Workflow-Editor
- Vaultwarden
- Xiaozhi Voice-Server
- SearXNG
- AutoDream
- HydraBrain
- Frustrations-Erkennung
- Semantic Index (FAISS)

Diese Liste ist kein Angriff auf vergangene Arbeit — es ist eine Grenze die verhindert
dass wir wieder in dieselbe Falle tappen.
