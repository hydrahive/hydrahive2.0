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
- **System** — Logs, Health, Services
- **Backup/Restore**

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

## Was explizit NICHT gebaut wird (ohne separate Entscheidung)

- DREAM-System
- Widget-Dashboard mit Drag&Drop
- Collaborative Composer (Yjs)
- Blueprint/Workflow-Editor
- Butler-Regeln
- Vaultwarden
- Xiaozhi Voice-Server
- SearXNG
- AutoDream
- HydraBrain
- Frustrations-Erkennung
- Semantic Index (FAISS)

Diese Liste ist kein Angriff auf vergangene Arbeit — es ist eine Grenze die verhindert
dass wir wieder in dieselbe Falle tappen.
