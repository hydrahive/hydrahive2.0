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
- Kein Docker für den Core — HydraHive selbst läuft direkt auf dem Host (systemd-Services).
  Docker ist als optionaler Installations-Kanal für Extensions erlaubt.
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
| Datenbank | SQLite (Sessions) + PostgreSQL (AgentLink, Datamining-Mirror optional) | SQLite = zero-config für Core |
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

## Agent-Tool-Kontrolle (Sicherheits-Modell)

**Entscheidung:** Agents arbeiten mit voller Tool-Macht — wie Claude Code oder OpenClaw.
Keine OS-Sandbox, kein User-pro-Agent, keine sudoers-Whitelist, kein cgroup-Limit pro Agent.
Sicherheit kommt aus zwei Schichten:

1. **HydraHive-User-Auth + Per-User-Owner-Pattern** (users.json + JWT) — entscheidet
   wer welchen Agent starten darf
2. **Per-Agent Tool-Bestätigung** (`require_tool_confirm: bool`) — wenn aktiv,
   muss der User vor jedem Tool-Call im Chat per Banner bestätigen (Allow / Deny),
   sonst läuft das Tool direkt durch. Auto-Deny nach 5 Minuten ohne Antwort.

**Warum nicht systemd-User-Isolation pro Agent:**
- "Darf ich nicht"-Pattern killt den Workflow — User muss ständig manuell ran
- Sandbox bricht VM/Container/Tailscale-Tools (kein /dev/kvm, keine Network-Namespaces)
- Privilegierte Operationen (apt install, systemctl, samba) wären über separate
  Backend-API-Endpoints mit Code-Pflege-Aufwand → keine Funktionsparität zum
  freien shell_exec
- HydraHive 1 hat genau diese Sandbox-Strenge gehabt und wurde dadurch unbrauchbar

**Sicherheits-Eckpunkte trotzdem:**

| Ebene | Mechanismus |
|---|---|
| HydraHive-User + Auth | eigene Schicht (users.json + JWT) |
| Agent-Ausführung | im hydrahive-Service-User, voller Tool-Zugriff inkl. sudo |
| Pro-Agent-Filterung | `tools[]`-Liste am Agent — nur erlaubte Tools werden registriert |
| Pro-Tool-Permission | `require_tool_confirm` → Banner-Prompt vor Ausführung |
| Pro-Plugin-Permission | Plugins müssen am Agent explizit aktiviert sein |
| Service-Isolation | `ProtectSystem=strict` + `ReadWritePaths` am hydrahive-Service selbst |

**Konsequenz für den Installer:**
- Installer legt System-User `hydrahive` an, unter dem API + alle Agent-Subprocesses laufen
- API läuft nie als root, Subprocess-Privilegien = Service-Privilegien
- Kein zweiter System-User pro Agent, keine Linux-Gruppe pro Projekt
- Projekte werden über DB + workspace-Pfade getrennt, nicht über Filesystem-ACLs

**Implementierung:** `core/src/hydrahive/runner/tool_confirmation.py` (Pending-Store mit
asyncio-Future), `frontend/src/features/chat/ToolConfirmBanner.tsx` (UI), Toggle im
AgentForm-Overview-Tab.

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
| `read_scratchpad` | Scratchpad lesen (Tills Ideen + eigene Agent-Notizen) |
| `write_scratchpad` | In die eigene Agent-Zone des Scratchpads schreiben |
| `ask_agent` | Anderen Agenten über AgentLink beauftragen |
| `send_mail` | E-Mail senden (SMTP-Config nachträglich) |

### MCP-Tools (extern, per Config zugewiesen)

stdio + streamableHttp + SSE. Standard-MCP-Server werden vom Installer mitinstalliert:
GitHub, Filesystem, Git, SQLite, Fetch, Time, Sequential Thinking.

Weitere MCP-Server: per Admin-UI hinzufügen, pro Agent zuweisen.

---

## Media-Generierung (Core-Komponente)

Agenten können Medien *erzeugen* — alles über OpenRouter (ein API-Key, ein
Endpoint deckt den Cluster ab). Bild/Musik/Sprache/Transkription laufen synchron
über `chat/completions` (gestreamtes Audio/Bild), Video über die asynchrone
Jobs-API (`POST /api/v1/videos`).

### Core-Tools

| Tool | Beschreibung |
|---|---|
| `generate_image` | Bild aus Text-Prompt |
| `generate_music` | Musik/Audio aus Text-Prompt (Lyria 3) |
| `generate_speech` | Text-to-Speech (gpt-audio) |
| `transcribe` | Audio → Text |
| `generate_video` | Video aus Text/Bild (asynchroner Job) |

Erzeugte Dateien landen im Agent-Workspace und erscheinen im Chat als
Bild/Audio/Video. Base64-Daten gehen nie in den LLM-Kontext.

### Zentrale Modellwahl pro Kategorie

Das aktive Modell pro Media-Typ wird zentral in `llm.json` verwaltet
(`media_models.{image,music,tts,transcribe,video}`) — erweitert das bestehende
`default_model`/`embed_model`-Muster. Befüllt live aus `/models` nach
Output-Modalität gefiltert (Video via `/api/v1/videos/models`), verwaltet auf
der LLM-Seite der Web-Konsole. Provider/Modell wechseln = eine Zeile Config
(siehe Nicht-Ziele Z. 21). Der Tool-Parameter `model` überschreibt den
zentralen Default pro Aufruf.

### Nicht-Ziele
- Keine eigenen Media-Modelle trainieren oder hosten
- Kein clientseitiges Multi-Provider-Fan-out — ein gewähltes Modell pro Kategorie

### Architektur
Backend `core/src/hydrahive/tools/generate_*.py` + geteilter Helfer
`tools/_openrouter_media.py` (Key + Speicherung). Modell-Resolver
`llm/media_models.py`. Frontend: Abschnitt „Media-Modelle" in
`features/llm/LlmPage.tsx`.

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
  - **Live-Sync über Geräte** — mehrere offene Clients (Geräte/Tabs) derselben
    Session bleiben synchron: löst ein Client einen Lauf aus, sehen die anderen
    offenen Clients die Antwort live erscheinen. Jeder Client abonniert einen
    per-Session SSE-Broadcast-Kanal (`/api/sessions/{id}/stream`); bei
    Lauf-Fortschritt lädt er nach. Der auslösende Client behält sein direktes
    Token-Streaming.
  - Header-Switcher: aktuelles Modell und Reasoning-Effort (low/medium/high)
    pro Session umschaltbar. Effort mappt auf OpenAI `reasoning_effort`
    (GPT-5) bzw. Anthropic `extended_thinking.budget_tokens`. Bei Providern
    ohne Reasoning-Support ist der Effort-Switch deaktiviert/unsichtbar.
  - **Media-Rendering** — Chat rendert Anhänge inline:
    - Bilder: `<img>` Tag
    - Audio: `<audio>` Player
    - Video: `<video>` Player
    - PDF / EPUB: nativer Browser-Embed (`<embed>` / `<iframe>`)
    - Backend serviert lokale Dateien über `/api/files/serve?path=...`
      mit Path-Sanitizing (kein Directory-Traversal), Whitelist auf
      erlaubte Verzeichnisse per Config
    - Agent gibt gefundene Dateien als `[media:<pfad>]`-Marker zurück —
      Frontend erkennt den Marker und rendert den passenden Player
- **Agenten** — anlegen, bearbeiten, Soul/Skills/Tools konfigurieren
- **Projekte** — anlegen, Workspace, Projektagent konfigurieren
- **Spezialisten** — anlegen, Domäne, Skills zuweisen
- **LLM** — Provider, API-Keys, Modelle
  - Modell-Catalog: pro konfiguriertem Provider eine Tabelle mit allen
    verfügbaren Modellen. Live aus dem Provider-Endpoint (z.B.
    /v1/models bei OpenAI/NVIDIA/etc.) gejoint mit interner Metadata
    (Context-Window, Tool-Use-Support, Kategorie, Größe). Suche + Filter.
    "Test"-Button macht einen Mini-Call (1 API-Credit) zum Verifizieren.
    "Im Agent nutzen"-Button setzt das Modell als Agent-Default.
  - OAuth-Login pro Provider in der Web-UI: Anthropic (Browser-Redirect),
    MiniMax (Device-Code-Flow), OpenAI Codex (Authorization-Code-Callback).
    Backend hält Access- und Refresh-Token in llm.json, refresht automatisch
    vor Ablauf. Pro Provider entweder API-Key ODER OAuth-Token (UI zeigt was
    gerade aktiv ist).
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

## PostgreSQL Datamining-Mirror (optional)

Alle Chat-Events werden zusätzlich zu SQLite in PostgreSQL gespiegelt — roh, ungekürzt,
blockweise aufgeteilt. Grundstein für Datamining, Analyse und semantische Suche.
Aktiviert durch Setzen von `HH_PG_MIRROR_DSN`. Wenn nicht gesetzt: inaktiv, kein Fehler.

### Was gespiegelt wird

Jede Message aus dem Chat-Kontext wird in einzelne Events aufgeteilt:

| event_type | Bedeutung |
|---|---|
| `user_input` | Texteingabe des Users |
| `assistant_text` | Textantwort des Agents |
| `tool_call` | Tool-Aufruf (Name + vollständiger Input als JSONB) |
| `tool_result` | Tool-Ausgabe (gechukt bei > 8.000 Zeichen) |
| `thinking` | Extended-Thinking-Blöcke |
| `compaction` | Compaction-Summary |

Jedes Event trägt: `username`, `agent_id`, `agent_name`, `project_id`, `session_id`,
`created_at` (sekundengenau) sowie eine Chunk-ID im Format `{message_id}:{block}:{chunk}`
die das Zusammensetzen zerstückelter Tool-Outputs ermöglicht.

### Embedding-Spalte

`embedding vector(4096)` — kompatibel mit `nvidia/nv-embed-v2` (NVIDIA NIM).
Bleibt NULL bis ein separater Embedding-Worker läuft. Der HNSW-Index (pgvector)
wird nur über non-NULL Rows gebaut.

### Schema angelegt durch

`db/mirror.py` beim Start — `CREATE TABLE IF NOT EXISTS` + Indizes, idempotent.
`CREATE EXTENSION IF NOT EXISTS vector` muss vorab einmalig auf dem PG-Server ausgeführt werden.

### Externe Instanzen (Live-Ingest)

Externe Clients — primär eigenständige Claude-Code-Instanzen — spiegeln ihre
Konversation live in dasselbe Datamining, über den vorhandenen
`messages.append() → Mirror`-Pfad. Eine externe Instanz wird im Modell wie ein
normaler Agent behandelt: eigener registrierter `agent_id` + eigener Login-User,
damit `agent_name` und `username` sauber zuordbar sind.

**Endpoint:** `POST /api/sessions/{id}/log` (`require_auth`, Owner-Check) hängt
eine Message an und löst den Mirror aus. **Kein** Agenten-Lauf (im Gegensatz zu
`/inject`) — reines Mitschreiben.

**Idempotenz:** Der Client liefert eine stabile Message-ID (z.B. die
Transkript-Eintrags-UUID); der Insert ist `INSERT OR IGNORE`. Derselbe Eintrag
landet nie doppelt, egal wie oft der Client erneut sendet.

**Erfassung (Claude-Code-Seite):** Ein Stop-Hook in `~/.claude/` liest das
Transkript und sendet neue Einträge. Der Hook lebt außerhalb des Core; der Core
stellt nur den Endpoint bereit. Erfasst wird alles — Scope ist opt-in pro Instanz
über deren Hook-Config.

### Externe Instanzen — Verwaltung (GUI)

Admin-Oberfläche zum Anlegen und Verwalten externer Instanzen. Eine Instanz =
ein als `external` markierter Agent + dessen Owner-User + dessen API-Key — keine
eigene Tabelle, der Agent-Marker ist die Einheit.

**Endpoints (alle `require_admin`):**
- `POST /api/external-instances` — orchestriert in einem Schritt: User (eigenes
  Login, zufälliges Passwort), Agent (`external=true`, `owner`=User), API-Key
  *für diesen User* (nötig, da `api_keys.create` den Key an den Owner bindet).
  Gibt **einmalig** `username`, `agent_id` (uuid), `api_key` (Klartext) + den
  fertigen Hook-Config-Block zurück.
- `GET /api/external-instances` — Liste der `external`-Agenten mit Owner-User,
  Key-Anzahl und Aktivität (Session-Count + Last-Activity aus `agent_stats`).
- `DELETE /api/external-instances/{agent_id}` — entfernt Agent + Owner-User + Keys.
- `POST /api/external-instances/{agent_id}/rotate-key` — alten Key widerrufen,
  neuen einmalig ausgeben.

**Agent-Config:** neues Feld `external: bool` (default false) markiert die Einheit.

**Frontend:** als dritter Abschnitt „Datamining-Instanzen" auf der bestehenden
Federation-Seite (`features/federation/`, admin-only) — neben „Workstations" und
„Clients", kein eigener Menüpunkt. Liste + Wizard; der Wizard zeigt API-Key +
Hook-Config (`HH_BASE_URL`/`HH_API_KEY`/`HH_AGENT_ID`=uuid + `settings.json`-Snippet)
**einmalig** nach dem Anlegen. Die Liste zeigt je Instanz die Agent-ID
(= `HH_AGENT_ID`) zum Nachschlagen/Kopieren — der API-Key bleibt einmalig.

**Abgrenzung zu `/federation/clients`:** Jenes erzeugt admin-eigene Keys
(`role=projektx`, AgentLink/Tailscale-Config) für ProjektX-Clients. Dieser Pfad
legt pro Instanz einen eigenen User + Agent an und zielt aufs Datamining-Mirroring
— getrennte Endpoints, aber co-lokalisiert auf derselben Seite.

### Nicht-Ziele

- Kein Retry bei PG-Ausfall (fire-and-forget, Datamining-Verlust akzeptabel)
- Keine Rück-Synchronisation von SQLite → PG (Mirror startet ab Aktivierung)
- Kein Embedding-Worker im Core (separater Service, kommt später)
- Keine Abfrage-API im Backend (direkter DB-Zugriff durch Datamining-Tools)
- Kein Agenten-Lauf beim Ingest (`/log` schreibt nur, `/inject` führt aus)
- Keine Redaction im Core — Secrets clientseitig im Hook filtern, falls nötig
- Externe-Instanz-Verwaltung ohne eigene Registry-Tabelle (Agent-`external`-Marker + abgeleitete Sicht)

### Knowledge Graph (Wissensgraph)

Visuelle Wissenskarte aller Datamining-Events — Grundlage sind die Embedding-Vektoren.

**Technischer Ansatz:**
- UMAP: reduziert Embedding-Vektoren auf 2D-Koordinaten (on-demand, serverseitig)
- HDBSCAN: clustert Events automatisch zu semantischen Themengruppen
- Cosine-Similarity via pgvector: Kanten zwischen ähnlichen Events (Schwellwert konfigurierbar)
- D3.js Force-Graph: interaktive Visualisierung im Frontend (Zoom, Filter, Click-to-Detail)

**Frontend — neuer Tab "Graph" auf der Datamining-Seite:**
- Nodes = Events/Cluster, eingefärbt nach Thema
- Edges = semantische Ähnlichkeit über Cosine-Similarity-Schwellwert
- Klick auf Node → Event-Detail
- Filter nach Agent, User, Zeitraum

Keine externe Graph-Datenbank — alles on-demand aus pgvector berechnet.

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
- Disk-Interface pro VM wählbar: `virtio` (Default, schnellste, für Neu-Installationen),
  `sata` (kompatibel, für importierte Images aus VirtualBox/HH1/etc.), `ide` (Notnagel)
- Machine-Type pro VM wählbar: `q35` (Default, ICH9, modern), `pc` (i440FX, kompatibel —
  für FreeBSD-ZFS-Boot, Windows XP, sehr alte Linux, VirtualBox-Imports)
- Network-Device pro VM wählbar: `virtio-net-pci` (Default, schnell), `e1000` (Intel-NIC,
  von Haus aus in fast jedem Gast-OS unterstützt — für Imports ohne virtio-net-Treiber)
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

## Buddy — Persönlicher User-Agent (Core-Komponente)

Pro User ein eigener „Buddy"-Agent. Auto-erstellt beim ersten Aufruf der
Buddy-Page, fortlaufende Lifetime-Session (Auto-Compaction kümmert sich
ums Context-Window). Soul-Prompt ist Charakter-basiert — der Buddy ist
keine sterile Assistenz, sondern eine Persönlichkeit.

### Funktionsumfang
- Lifetime-Session pro User, keine Session-Wechsel
- Charakter-Auswahl beim Erst-Setup
- Marker `is_buddy=True` im Agent-Config — sonst normaler Master-Agent
- Slash-Commands für häufige Aktionen (`/extensions`, eigenes Pill-UI)
- Volle Tool-Suite des Master-Agenten

### Nicht-Ziele
- Mehrere Buddies pro User
- Wechselnde Charaktere (Charakter wird einmal beim Setup gewählt)

### Architektur
Backend `core/src/hydrahive/buddy/`. API `/api/buddy/*`.
Frontend `frontend/src/features/buddy/` (BuddyPage + Thread + Panels).
Sidebar-Item neben den anderen Agent-Tabs.

---

## Zahnfee — Nächtliche Datamining-Briefings (Core-Komponente)

Asyncio-Hintergrundtask der einmal pro Tag (konfigurierbare Stunde) aus
Datamining-Events der letzten N Stunden ein Morgen-Briefing erstellt.
Strukturierter LLM-Output — keine Roman-Texte.

### Funktionsumfang
- Scheduler läuft im Backend-Lifespan, prüft stündlich ob Zahnfee-Zeit ist
- 1x pro Tag aktiv (konfigurierbare `run_hour`, `lookback_hours`)
- LLM bekommt Datamining-Events, antwortet im JSON-Schema
  `{open, went_well, went_badly, today}` — je max. 5 Punkte
- Briefing wird persistiert; Frontend zeigt das aktuelle Briefing
- Per-User-Toggle (`enabled`)

### Nicht-Ziele
- Mehrere Briefings pro Tag
- Push-Benachrichtigungen (User holt sich's auf der Page ab)
- Multi-User-Briefings (eines pro Instanz)

### Voraussetzungen
- Datamining-Mirror muss aktiv sein (sonst leeres Briefing)

### Architektur
Backend `core/src/hydrahive/zahnfee/` (config, scheduler, runner, storage).
Briefing in `$HH_DATA_DIR/zahnfee/`. API `/api/zahnfee/*`.
Frontend `frontend/src/features/zahnfee/`.

---

## Proaktiver Recall — Gist-Cards & Gedächtnis-Abruf (Core-Komponente)

Macht aus dem passiven Datamining-Archiv ein abrufbares Gedächtnis: ein
Offline-Batch verdichtet Sessions zu getaggten Gist-Cards, die beim Recall
billig in den Agenten-Kontext kommen — geprüfte Essenz statt Roh-Protokoll.
Modell: capture → konsolidieren → mit Verifikation abrufen. Karten sind eine
abgeleitete, recompute-safe Schicht über dem immutablen Datamining, getrennt
vom handkuratierten Memory.

### Funktionsumfang (v1)
- Konsolidierung (Schlaf-Batch): automatisierter Offline-Lauf (nutzt die
  Zahnfee-/Crystallize-Maschinerie) schreibt pro Session eine Gist-Card mit
  gist, valence (good/bad/neutral), salience (high/low), groundedness
  (observed/claimed/mixed, in v1 aus dem Event-Typ-Mix abgeleitet), topics,
  source (session_id) und Embedding. Billiges Modell.
- Derived Card-Store: eigener, recompute-safe Store (wipe-and-rebuild aus
  Roh-Events), getrennt vom kuratierten Memory; nutzt Memory-v2-Primitive
  (confidence/superseded) und die Embedding-Pipeline wieder.
- Recall: A — Top-N Karten (recency × salience) beim Session-Start in den
  gecachten System-Prompt. C — cue-getriggert verwandte Karten per pgvector.
  Karten tragen source → Agent gräbt bei Bedarf via datamining_search.

### Nicht-Ziele (v1 — bewusst später, eigene Entscheidung = Ausbaustufe „v2")
- Kein Contradiction-Reasoning / Umklassifizieren
- Kein Verify-before-trust-Gate beim Recall
- Keine Modell-Eskalation
- Keine blinde Suche pro Turn (nur A-Grundstock + C-Cue)

### Voraussetzungen
- Datamining-Mirror aktiv (Quelle der Konsolidierung)
- Embedding/pgvector aktiv (für C-Recall)

### Architektur
Konsolidierung baut auf `tools/_crystallize.py` (Session→Digest+Lessons, LLM)
und der Zahnfee-Batch-/Scheduler-Maschinerie auf; eigener abgeleiteter
Card-Store; Recall über `runner/system_prompt.py` (Prompt-Weaving) + pgvector.
Card-Schema ist der Vertrag (`docs/superpowers/specs/2026-05-29-proactive-recall-design.md`).

---

## Scratchpad — Mensch→Agent-Ideenfläche (Core-Komponente)

Ein persistenter Ort pro User, an dem der Mensch Ideen notiert und veranschaulicht
(Markdown inkl. abhakbarer Punkte und Mermaid-Diagramme), die sein Buddy/Masteragent
auslesen und ergänzen kann. Bewusste Übergabefläche für unstrukturierte Gedanken —
ergänzt das automatische Datamining-Gedächtnis (Proaktiver Recall) um expliziten,
handgeschriebenen Input. Mensch- und Agent-Inhalt liegen in getrennten Zonen, sodass
der Agent den Text des Menschen technisch nicht überschreiben kann.

### Funktionsumfang
- Global pro User (ein Scratchpad, nicht projektgebunden), persistent über Sessions
- Markdown mit GitHub-Task-Checkboxen (`- [ ]`/`- [x]`) und Mermaid-Code-Blöcken
- Zwei getrennte Zonen je User: `user.md` (nur Mensch, via Web-Konsole) und
  `agent.md` (nur Agent, via Tool) — physisch getrennte Dateien
- Hybrid-Anbindung: statischer Hinweis im System-Prompt (cache-stabil) plus Tools
  `read_scratchpad` (liest beide Zonen) und `write_scratchpad` (schreibt nur Agent-Zone)
- Web-Konsole: eigener Menüpunkt; Mensch-Zone editierbar, Agent-Zone read-only + leerbar

### Nicht-Ziele (v1)
- Mermaid-Rendering im Browser (v1: Code-Block; Rendering = Ausbaustufe v1.1)
- Bild-/Foto-Upload oder freies Zeichen-Whiteboard (multimodal-abhängig)
- Pro-Projekt- oder Pro-Agent-Scratchpads
- Versionierung/History der Inhalte

### Architektur
Backend `core/src/hydrahive/scratchpad/` (service: get/save/clear, atomic write,
Größenlimit pro Zone). API `/api/scratchpad` (GET beide Zonen, PUT nur Mensch-Zone,
DELETE Agent-Zone). Core-Tools `read_scratchpad` + `write_scratchpad`. Speicher
`$HH_DATA_DIR/scratchpad/<user_id>/{user,agent}.md`. Statischer Prompt-Hinweis im
`stable_system`-Block (kein Cache-Bruch). Frontend `frontend/src/features/scratchpad/`.
Design: `docs/superpowers/specs/2026-05-31-scratchpad-design.md`.

---

## Forschungs-APIs — Wissenschaftliche & medizinische Quellen für Agenten (Core-Komponente)

Eine kuratierte Registry offener wissenschaftlicher/medizinischer APIs (Literatur,
Medikamente, Krankheiten/Gene, klinische Studien), die Agenten für Recherche nutzen.
Die meisten Quellen sind schlüssellos; für die wenigen mit Key/Token verwaltet die
Registry diese verschlüsselt und injiziert sie transparent beim Aufruf. Kein eigenes
Tool pro API — die Agenten rufen die Endpoints über das vorhandene `fetch_url`-Tool;
ein Skill liefert das How-to (Endpoints + Query-Syntax).

### Funktionsumfang
- Registry (system-weit, Admin): vorbefüllte Liste von Forschungs-APIs, gruppiert nach
  Kategorie (Literatur, Medikamente, Krankheiten/Gene, klinische Studien). Pro Eintrag:
  Name, Kategorie, base_url/url_pattern, docs_url, needs_key, auth_type
  (query/header/bearer) + auth_param, polite_email (z.B. OpenAlex), rate_limit, enabled.
  Keyless-Quellen standardmäßig aktiv.
- Key-Verwaltung: optionale API-Keys/Tokens verschlüsselt gespeichert (AES, wie der
  Credential-Store); im UI nur bei needs_key sichtbar; Reveal/Test pro Eintrag.
- Transparente Injektion: `fetch_url` injiziert den passenden Key/Token (per url_pattern)
  aus der Registry zusätzlich zum per-User-Credential-Store — der Agent sieht den Key nie.
- Agenten-Wissen: ein `medical-research`-Skill (Markdown, system_defaults) dokumentiert
  die Quellen + Query-Syntax; der Agent lädt ihn bei Bedarf (load_skill), statt die Liste
  dauerhaft in den Prompt zu weben.
- UI: Konfigurationsseite im Health-Bereich (Toggle/Key/Test pro Quelle, nach Kategorie).

### Nicht-Ziele
- Kein eigenes Wrapper-Tool pro API (generisch über fetch_url + Skill)
- Kein Caching/Speichern abgerufener Paper/Volltexte (Agent nutzt Treffer live)
- Keine deutsche Arzneimittel-DB (keine gute offene API; Mapping über Wirkstoff/INN)
- Kein Scraping/Nicht-API-Quellen, keine kommerziellen Lizenz-APIs (z.B. DrugBank kommerziell)
- Keine automatische/geplante Recherche (nur agent-getriggert)

### Voraussetzungen
- `fetch_url`-Tool (für Calls + Key-Injektion)
- Skills-System (für das How-to)
- Internet-Zugang des Backends zu den Endpoints

### Architektur
Backend `core/src/hydrahive/research/` (Registry-Modell + verschlüsselte Persistenz in
`/etc/hydrahive2/research_apis.json`, 0600) + `api/routes/research_apis.py` (Admin-CRUD,
Test); Erweiterung der `fetch_url`-Key-Injektion um die Registry als zweite Quelle.
Frontend: View in `features/health/` (Sidebar „Forschungs-APIs"). Skill:
`skills/system_defaults/medical-research.md`. Vorbefüllte Quellen u.a.: PubMed/E-utilities,
Europe PMC, OpenAlex, Semantic Scholar, Crossref, CORE, bioRxiv/medRxiv, openFDA, RxNorm,
ICD-11 (WHO), MyGene/MyVariant, Open Targets, HPO, ClinicalTrials.gov v2.

---

## Patientenakte — Strukturierte elektronische Akte (Health-Extension, Core-Komponente)

Strukturierte, persistente, multi-Patient-fähige elektronische Patientenakte (ePA-light)
als schreibbarer Kern der Health-Extension. Abgegrenzt von der read-only eGA/FHIR-
Importschicht (Kassendaten): die Patientenakte ist die von Agenten und Nutzer befüllbare
Akte, in die aus Dokumenten/Daten extrahierte medizinische Informationen einfließen.

### Funktionsumfang
- Datenmodell: FHIR-R4-angelehnt, pragmatisch relational (eigene SQLite-Tabellen, kein
  FHIR-Server). Entitäten: Patient, Diagnose (Condition), Medikament, Laborwert
  (Observation), Ereignis/Prozedur (Encounter), Bildgebung (ImagingStudy), Allergie,
  Arzt (Practitioner), Dokument (DocumentReference), Notiz. Jeder Datensatz trägt
  quelle/confidence/verifiziert (manuell vs. KI-extrahiert) + external_id (Idempotenz).
- Befüllung: Token-geschützte REST-API (JSON), damit Agenten Datensätze anlegen/
  aktualisieren (CRUD + Batch für Laborwerte). Idempotenz über external_id.
- Dokumente: Upload (PDF/Bild/DICOM-Verweis) + vom Agenten geliefertem OCR-Text;
  Volltextsuche über Einträge + OCR.
- UI: Eigener Health-Bereich „Patientenakte" — Patienten-Auswahl, Dashboard, Timeline,
  Detail-Listen, Lab-Trend-Charts, Quellen-/Verifiziert-Markierung.
- Datenschutz (Art. 9 DSGVO): Verschlüsselung-at-rest sensibler Felder, Zugriffskontrolle
  pro Nutzer, Audit-Log, Export + vollständige Löschung pro Patient.
- Migration: Import-Skript für den bestehenden YAML-Prototyp (akten/<patient>/*.yaml + CSV).

### Nicht-Ziele (v1)
- Kein vollwertiger FHIR-Server (nur FHIR-angelehntes relationales Schema)
- Keine automatische medizinische Befundung/Diagnose durch das System
- Keine KIM/TI-Anbindung an Praxis-Systeme
- Keine DICOM-Bildanzeige im Browser (nur Verweis + Vorschau-JPG)
- Keine server-seitige OCR-Engine (OCR-Text liefert der befüllende Agent mit)

### Voraussetzungen
- Auth-System (require_auth + hhk_-API-Keys für Agenten-Befüllung)
- Skills-System (Befüll-How-to für Agenten)
- credentials/_crypto (Verschlüsselung-at-rest), SQLite FTS5 (Volltextsuche)

### Architektur
Backend `core/src/hydrahive/patientenakte/` (eigene relationale SQLite-Domäne, Migration
023+; registry-getriebener generischer Service-/Route-Layer über alle Entitäten) +
`api/routes/patientenakte.py` (Token/JWT-CRUD + Batch + Timeline/Summary/Search/Export).
Abgegrenzt vom read-only eGA/FHIR-Blob-Store (`db/fhir.py`), der unangetastet als
Kassendaten-Import bestehen bleibt. Frontend: `features/health/` (Sidebar „Patientenakte"
primär; bestehende eGA/FHIR-Views unter „Kassendaten / Import"). Skill:
`skills/system_defaults/medical-akte.md`.

---

## Voice — STT/TTS für Sprache-Eingang/Ausgang (Core-Komponente)

Wyoming-Whisper als lokaler STT-Server (Container, Port 10300) plus
TTS-Helpers. Wird sowohl von `/api/stt` + `/api/tts` als auch vom
WhatsApp-Adapter genutzt — Sprachnachrichten verstehen + senden.

### Funktionsumfang
- STT via Wyoming-Whisper (faster-whisper Backend)
- Audio-Konvertierung zu 16kHz Mono raw-PCM via ffmpeg
  (akzeptiert mp3/ogg/wav/m4a/…)
- TTS-Wrapper mit Quota-Tracking (`_quota.py`)
- TTS provider-wählbar (pro User): **Browser** (Web Speech, clientseitig),
  **Lokal** (Wyoming-Piper, incus-Container Port 10200 — ohne Cloud-Key),
  **MiniMax** (`mmx`-CLI) oder **OpenRouter** (echtes TTS via `/audio/speech`,
  Modell zentral über `media_models.tts`, siehe Media-Generierung)
- WhatsApp-Voice-Eingang: `_wa_voice.py` ruft direkt `transcribe_bytes()`

### Nicht-Ziele
- Eigene Voice-Modelle trainieren
- Streaming-STT mit Partial-Results (Single-Shot reicht)
- Voice-Cloning

### Voraussetzungen
- Container-Subsystem aktiv (Whisper-STT + optional Piper-TTS als incus-Container)
- ffmpeg im Backend-Pfad

### Architektur
Backend `core/src/hydrahive/voice/` (stt, tts, _audio_utils, _quota).
Installer-Modul `installer/modules/55-voice.sh` setzt die lokalen
Wyoming-Container als incus-LXC auf: faster-whisper (STT, Port 10300) und
Piper (TTS, Port 10200). Kein Docker (SPEC).

---

## Home Assistant — Integration via MCP-Server (Core-Komponente)

HydraHive2 exposed seine eigenen Funktionen als **MCP-Server (Model Context Protocol)**
den Home Assistant's MCP-Client-Integration konsumiert. Damit stehen HydraHive-Tools
einem HA-Conversation-Agenten (Anthropic / OpenAI / Ollama) als zusätzliche
Tool-Suite zur Verfügung — neben den HA-eigenen Tools für Smart Home und Mediaplayer.

```
[NABU Voice / HA Satellite]
     ↓ Wake Word + STT (HA-Whisper)
[HA Assist Pipeline]
     ↓ Conversation Agent (z.B. Anthropic-Integration in HA, User-eigener Key)
     ↓ Verfügbare Tools:
        • HA-eigene Smart-Home-Tools (light.turn_on, media_player.play_media, ...)
        • HA-Plex-Integration (nativ)
        • HydraHive MCP-Server: hh_query_memory, hh_delegate_to_agent, ...
     ↓ Claude wählt das richtige Tool je nach User-Anfrage
[Antwort über HA-TTS zurück ans Gerät]
```

**Warum dieser Ansatz statt Custom Conversation Agent:**

- Ein "Custom Conversation Agent" in HA wäre eine HA-Custom-Integration in Python —
  separates Repository, HACS-Distribution, doppelter Pflegeaufwand
- HA's eigene Conversation-Agenten sind bereits ausgereift; HA macht Smart Home,
  Plex, Klima, Mediaplayer bereits nativ und gut
- Mit der MCP-Integration in HA ab 2024 ist der Weg vorgezeichnet: HydraHive
  bringt Tools rein, HA's LLM nutzt sie

### Funktionsumfang

**MCP-Endpoint** (SSE, weil HA's MCP-Client SSE erwartet):
- `GET /api/ha-mcp/sse` — SSE-Stream für MCP-Protokoll-Events
- `POST /api/ha-mcp/messages` — JSON-RPC Requests
- Bearer-Token-Auth über `Authorization`-Header; Token pro HydraHive-User

**Erste Tool-Suite** (alle Tools laufen im Kontext eines HH-Users):

| Tool | Wirkung |
|---|---|
| `hh_query_memory(query)` | Durchsucht Master-Agent-Memory semantisch |
| `hh_list_agents()` | Listet User-eigene Agents und Spezialisten |
| `hh_delegate_to_agent(agent_name, task)` | Delegiert Task an einen HH-Agent über AgentLink |
| `hh_recent_messages(channel?, limit)` | Letzte Messenger-Nachrichten aus dem Datamining-Mirror |
| `hh_query_messages(text, since?)` | Volltextsuche in eGA-Messages |
| `hh_run_butler_flow(flow_id, payload?)` | Triggert einen Butler-Flow manuell |
| `hh_agent_status(agent_id)` | Aktueller Zustand eines HH-Agenten |

Weitere Tools per Plugin nachrüstbar (siehe Plugin-System).

### Konfiguration

- HydraHive-seitig: MCP-Endpoint ist immer aktiv wenn die Integration installiert ist.
  Token-Verwaltung pro User: Profile-Page → "MCP-Token erzeugen" → Token wird einmalig
  angezeigt und in der DB gehasht gespeichert (wie API-Keys).
- HA-seitig: Integration "Model Context Protocol" hinzufügen → URL =
  `http://<hydrahive>:8000/api/ha-mcp/sse`, Bearer-Token aus HydraHive einfügen
- Im HA-Conversation-Agent (Anthropic-Integration o.ä.) wird der MCP-Server unter
  "Control Home Assistant" / "Available Tools" sichtbar und aktivierbar

### Nicht-Ziele

- Kein eigener Conversation Agent in HydraHive — HA bleibt der LLM-Gateway
- Kein eigener STT/TTS — HA Whisper/Piper bleibt zuständig
- Keine Wake-Word-Verarbeitung in HydraHive — läuft auf dem Satelliten
- Keine Reimplementierung von HA-Smart-Home-Tools (light, media_player, …)
- Keine Plex-Direktanbindung (HA's native Plex-Integration reicht)
- Kein Push HydraHive → HA ohne Tool-Aufruf vom HA-LLM

### Trade-offs (ehrlich)

- Sprachbefehle laufen über den **HA-Conversation-Agent**, nicht den HydraHive-Master-Agent.
  Soul, Skills und Lifetime-Session des Master-Agenten kommen nur indirekt über MCP-Tools rein.
- User braucht in HA einen LLM-Provider (Anthropic / OpenAI / Ollama), getrennt vom
  HydraHive-LLM-Stack.
- Conversation-State (Dialog-Historie eines Sprachbefehls) lebt in HA, nicht in HydraHive.

### Architektur

`core/src/hydrahive/ha_mcp/`:
- `server.py` — SSE-Transport + JSON-RPC-Loop
- `auth.py` — Bearer-Token-Validierung gegen User-Tabelle
- `registry.py` — Tool-Registry (Plugins können andocken)
- `tools/memory.py`, `tools/agents.py`, `tools/messages.py`, `tools/butler.py` —
  je Tool eine Datei <150 Zeilen

`api/routes/ha_mcp.py` → `/api/ha-mcp/*`.

Frontend `frontend/src/features/profile/HaMcpTokenCard.tsx` — Token-Erzeugung
und -Widerruf auf der Profile-Page.

### Nebenprojekt-Option

Wenn die HA-MCP-Integration in der Praxis Lücken zeigt (z.B. fehlende Notifications,
limitiertes Streaming), wird das Sprach-Routing als separates Projekt **`hh-voice-bridge`**
ausgelagert: ein eigener kleiner Service der Wake Word + STT direkt entgegennimmt
(Wyoming) und mit dem HydraHive-Master-Agenten redet. Kein Bestandteil von Core.

---

## Extensions — App Manager (Core-Komponente)

HydraHive2 kann externe Software-Pakete nachträglich über die Web-UI installieren, verwalten
und deinstallieren. Das System ist deklarativ: jede Extension ist ein JSON-Manifest + Bash-Scripts.
Extensions unterstützen zwei Installations-Kanäle: **nativ** (systemd-Service) und **Docker**
(docker-compose). Docker ist optional — nur verfügbar wenn Docker auf dem Host installiert ist
und nur für Extensions, nie für HydraHive selbst.

### Manifest-Format

```json
{
  "id": "gitea",
  "name": "Git-Server (Gitea)",
  "description": "Self-hosted Git-Hosting — Repositories, Issues, CI.",
  "icon": "GitBranch",
  "category": "tools",
  "install_script": "extensions/install/gitea.sh",
  "uninstall_script": "extensions/uninstall/gitea.sh",
  "service": "gitea",
  "health_url": "http://127.0.0.1:3001/api/v1/version",
  "open_url": ":3001/",
  "installed_check": "/usr/local/bin/gitea",
  "install_params": []
}
```

### Docker-Erweiterung im Manifest

Extensions können optional einen `docker`-Block haben. Ist Docker auf dem Host verfügbar,
zeigt die UI eine Auswahl: Nativ oder Docker. Ohne Docker-Block: nur nativer Install.

```json
{
  "id": "paperless-ngx",
  "name": "Paperless-ngx",
  "install_script": "extensions/install/paperless-ngx.sh",
  "installed_check": "/opt/paperless-ngx/manage.py",
  "docker": {
    "compose_file": "extensions/docker/paperless-ngx.compose.yml",
    "service_name": "paperless-ngx",
    "health_url": "http://127.0.0.1:8010/",
    "open_url": ":8010/"
  }
}
```

### Erster Catalog (aus HydraHive 1 portiert)

| Kategorie | Extensions |
|---|---|
| Tools | Gitea, Code-Server, Heimdall |
| KI | Ollama |
| Netzwerk | Headscale, Pi-hole, AdGuard Home |
| Sicherheit | Vaultwarden |
| Produktivität | Bookstack, Paperless-ngx, Vikunja, Monica CRM, Radicale |
| Media | Plex, Sabnzbd, Sonarr, Radarr |
| Gaming | Minecraft, Valheim |
| Sonstiges | SearXNG |

### Installations-Mechanismus

- **Nativ**: Backend führt `sudo -n /bin/bash install.sh` aus, Service läuft als systemd-Unit
- **Docker**: Backend führt `docker compose -f compose.yml up -d` aus, kein systemd-Service nötig
- Backend prüft beim Start ob Docker verfügbar ist (`docker info`) — Flag in der Extensions-Liste
- Frontend zeigt bei Extensions mit `docker`-Block eine Toggle-Auswahl (Nativ / Docker),
  sonst nur den nativen Install-Button
- Output wird per SSE live ans Frontend gestreamt
- Status bei Docker: Container läuft (`docker ps`) + `health_url` antwortet
- Status nativ: `installed_check`-Pfad existiert + systemd-Service aktiv + `health_url` antwortet
- Optional: `install_params` → Parameter-Dialog vor Installation (z.B. DNS-IP)
- Validierung vor Ausführung: Pflichtfelder, Script existiert, keine destruktiven Pattern
  (`rm -rf /`, `curl|bash`, `mkfs`)

### Nicht-Ziele

- Kein Docker für HydraHive selbst — nur für Extensions auf eigener Hardware
- Kein automatisches Docker-Fallback wenn nativ fehlschlägt (User wählt explizit)
- Keine Docker-Netzwerke zwischen Extensions (jede Extension ist isoliert)
- Keine automatischen Updates (manuell über Uninstall + Reinstall)
- Kein Extension-Hub / Online-Catalog (nur lokale Manifests)
- Kein Rollback bei fehlgeschlagener Installation

### Architektur

**Backend** `api/routes/extensions.py`:
- `GET /api/admin/extensions` — alle Manifests + Status
- `POST /api/admin/extensions/{id}/install` — SSE-Stream
- `POST /api/admin/extensions/{id}/uninstall` — SSE-Stream

**Daten** `extensions/`:
- `manifests/*.json` — Deklarationen
- `install/*.sh` — Installer (idempotent)
- `uninstall/*.sh` — Deinstaller

**Frontend** `features/extensions/`:
- Kategorie-Sidebar + Extension-Cards (Name, Icon, Status-Badge)
- Install-Modal mit Live-Log (SSE)
- Parameter-Dialog wenn `install_params` gesetzt

---

## Streaming-Downloader

Ermöglicht das Herunterladen von abonnierten Streaming-Inhalten für lokale
Plex-Bibliotheken. Erster unterstützter Anbieter: **Ghostflix** (Bunny CDN basiert).

**Seite:** `/streaming` — eigene Seite in der Web-Konsole, Zugriff für alle User

### Ghostflix-Integration

- User hinterlegt Ghostflix-Credentials einmalig in den eigenen Profileinstellungen
- Serien-URL eingeben → HydraHive fetcht die Seite authentifiziert,
  parst `episodes_data` aus dem HTML, zeigt Episodenliste
- Episoden einzeln oder alle auswählen, Plex-Ausgabepfad konfigurieren
- Download läuft im Hintergrund via `yt-dlp`, Fortschritt per SSE ans Frontend
- Bereits heruntergeladene Folgen werden übersprungen
- Output-Dateinamen Plex-kompatibel: `Serientitel - S01E01.mkv`

### Technische Umsetzung

- `core/src/hydrahive/streaming/` — scraper.py, downloader.py, api routes
- `frontend/src/features/streaming/` — StreamingPage, EpisodeList, DownloadProgress
- yt-dlp als Systemabhängigkeit (wird vom Installer geprüft/installiert)
- Credentials verschlüsselt in DB (nie im Klartext in Logs oder Responses)
- Gleichzeitige Downloads: max. 1 pro User (queue-based)

### Nicht-Ziele dieses Moduls

- Kein automatisches Monitoring (kein "neue Folge → auto-download")
- Keine Metadaten-Enrichment (kein TMDB/TheTVDB-Lookup)
- Keine anderen Streaming-Dienste in Phase 1 (nur Ghostflix)

---

## Was explizit NICHT gebaut wird (ohne separate Entscheidung)

- DREAM-System
- Widget-Dashboard mit Drag&Drop
- Collaborative Composer (Yjs)
- Blueprint/Workflow-Editor
- AutoDream
- HydraBrain
- Frustrations-Erkennung
- Semantic Index (FAISS)

Diese Liste ist kein Angriff auf vergangene Arbeit — es ist eine Grenze die verhindert
dass wir wieder in dieselbe Falle tappen.
