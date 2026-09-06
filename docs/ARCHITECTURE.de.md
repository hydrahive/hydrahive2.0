# HydraHive-Architektur

> 🇬🇧 [English version](ARCHITECTURE.md)

> **Zielgruppe:** Mitwirkende, Operatoren und System-Architekten
> **Validiert gegen:** das aktuelle Repository am 2026-09-06
> **Verwandt:** [Feature-Inventar](FEATURES.md) bzw. [FEATURES.de.md](FEATURES.de.md) · [Produkt-Baseline](../SPEC.md) · [Beitragen](../CONTRIBUTING.md)

HydraHive ist eine selbstgehostete AI-Orchestrierungs-Plattform. Die Steuerebene ist ein Python/FastAPI-Prozess mit einer React-Webanwendung. Sie koordiniert LLM-Calls, Tools, Workspaces, Memory, Media-Jobs, externe Integrationen und optionale Compute-Infrastruktur.

Dieses Dokument beschreibt die aktuelle Implementierung. Detaillierte Design-Aufzeichnungen unter `docs/specs/` und `docs/plans/` können einen früheren Zeitpunkt darstellen.

---

## 1. Design-Prinzipien

1. **Steuerebene und Nutzerdaten selbst hosten.** HydraHive speichert eigene Konfiguration, Workspaces und Konversations-Zustand auf dem Host. Cloud-Model-Anfragen bleiben eine explizite externe Datengrenze.
2. **Ressourcen-Ownership in Richtung stabiler Identitäten bewegen.** Neuere Principal-basierte Pfade nutzen unveränderliche User-IDs; Projekt-Ressourcen nutzen Mitgliedschaft/Rollen. Legacy-Username-basierte Routen benötigen weiterhin routen-spezifische Ownership-Checks.
3. **Agenten explizite Capabilities geben.** Jeder Agent erhält nur seine konfigurierten nativen, MCP- und Plugin-Tools.
4. **Lange Runs recoverable halten.** Sessions persistieren Messages und Tool-Results, können sich von HTTP-Requests abkoppeln, History compakten und nach Iterations-Limits fortsetzen.
5. **Extensions unterscheidbar halten.** Module, Themes, Service-Extensions und Agent-Tool-Plugins haben unterschiedliche Verträge und Vertrauensgrenzen.
6. **Fehler wo möglich isolieren.** Ein kaputtes Runtime-Modul, Plugin oder externer Provider sollte unrelated Komponenten nicht am Start hindern.
7. **Lokale Operation bevorzugen, keine falschen Offline-Behauptungen.** Lokale Modelle und Media-Worker werden unterstützt, aber viele Deployments nutzen absichtlich Cloud-Provider und Drittanbieter-Dienste.

---

## 2. Runtime-Übersicht

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Clients                                                              │
│ React-Web-App · REST-Clients · SSE-Streams · WebSocket-Clients       │
│ WhatsApp · Discord · Matrix · Remote-Compute-Nodes                   │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ HTTPS / WS
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ nginx (Default-Linux-Deployment)                                     │
│ TLS · Static-Frontend · /api-Proxy · WS-Upgrades · VNC · mTLS-Gate   │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ Loopback HTTP / WS
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ FastAPI-Anwendung                                                    │
│ Auth/Ownership · Routen · Modul-Router · Static-Fallback            │
├──────────────┬──────────────┬───────────────┬────────────────────────┤
│ Agent-Runner │ Projekte/Git │ Media-Jobs    │ Admin/Infrastruktur     │
│ Skills       │ Dateien/Gr.  │ Atelier/Video │ Server/VMs/Container   │
│ Memory       │ Tasks        │ Lokale Worker │ Extensions/Updates     │
├──────────────┴──────────────┴───────────────┴────────────────────────┤
│ Integrationen: LLM/Media-Provider · MCP · Plugins · AgentLink        │
│ Home Assistant · Mail · SABnzbd/Indexer · OAuth · Matrix etc.        │
└──────────────┬───────────────────┬───────────────────┬───────────────┘
               │                   │                   │
               ▼                   ▼                   ▼
      SQLite + File-Store   optional PostgreSQL   externe Dienste
      Workspaces/Media      Data-Mining-Mirror   und Model-APIs
```

Die Backend-Anwendung und alle Core-Router-Registrierungen werden in `core/src/hydrahive/api/main.py` assembliert. Runtime-Modul-Router werden nach der Modul-Discovery gemountet. Die Standard-Linux-Proxy-Konfiguration wird von `installer/modules/60-nginx.sh` generiert.

---

## 3. Hauptprozesse und Komponenten

### 3.1 FastAPI-Backend

Das Backend besitzt:

- Authentifizierung und Autorisierung;
- Agent/Session-Konfiguration;
- den iterativen Modell/Tool-Runner;
- Persistenz- und Migrations-Initialisierung;
- Projekt-Workspace- und Source-Control-Operationen;
- Media-Generierung und Job-Status;
- Modul/Theme/Plugin-Discovery;
- Kommunikations-Kanäle;
- Administrations- und Host-Infrastruktur-APIs.

Beim Start werden Logging, Datenbank, gebündelte/Runtime-Module, Themes, Background-Jobs und Kommunikations-Runtimes initialisiert. Modul-Routen werden nach der Modul-Discovery angehängt. In Production serviert nginx das gebaute Frontend direkt; in Development serviert Vite das Frontend und proxied API-Requests.

**Quelle:** `core/src/hydrahive/api/main.py`.

### 3.2 React-Frontend

Das Frontend ist eine React-19 + TypeScript + Vite Single-Page-Application. Es nutzt Route-Level-Code-Splitting für die meisten Screens. Wichtige Routen-Familien decken ab:

- Buddy, Chat, Agenten und Runs;
- Projekte, Tasks, Dateien, Graphen und Spezialisten;
- Media-Galerie, Prompt-Archiv, Atelier und Video-Editor;
- Modelle, Provider, Credentials, MCP und Integrationen;
- Module, Themes, Plugins und Extensions;
- User-Feature-Bereiche wie Butler, Smart Home und Media Center;
- Admin-, Server-, VM/Container- und Compute-Node-Seiten.

Installierte Modul-Frontends werden nach `frontend/src/modules` kopiert, vom Build-Generator entdeckt und in die Anwendung kompiliert. Sie können Routen, Navigation, Buddy-Widgets, Projekt-Workspace-Tabs und Media-Beiträge hinzufügen.

**Quellen:** `frontend/src/App.tsx`, `frontend/src/modules/`, `frontend/package.json`.

### 3.3 nginx-Kante

Das Standard-Linux-Install platziert nginx vor das Backend. Die generierte Konfiguration:

- leitet HTTP auf HTTPS um, außer für den Health-Ingest-Pfad;
- serviert `frontend/dist`;
- proxied `/api/` und WebSocket-Upgrades;
- nutzt per Default ein selbstsigniertes Zertifikat;
- wendet CSP-, HSTS-, Frame-, MIME- und Permissions-Header an;
- wendet Request-Size-Limits für Chat-Uploads und größere API-Uploads an;
- proxied VNC- und AgentLink-Pfade;
- verlangt ein gültiges Client-Zertifikat am Compute-Agent-Connect-Endpoint und injiziert ein Proxy-Secret.

Der FastAPI-Prozess bindet im Installer per Default auf Loopback, daher ist der Proxy der vorgesehene Netzwerk-Eingangspunkt.

**Quelle:** `installer/modules/60-nginx.sh`.

---

## 4. Identität, Authentifizierung und Autorisierung

### Authentifizierung

- Login-Credentials werden gegen einen file-backed User-Store verifiziert.
- Neue Passwörter nutzen bcrypt.
- Legacy-SHA-256-Passwort-Hashes werden nach erfolgreichem Login auf bcrypt migriert.
- Browser/API-Sessions nutzen ablaufende HS256-JWTs.
- Langlebiger API-Zugriff kann verwaltete `hhk_…`-API-Keys nutzen.

### Stabile Ownership

Neue User-eigene Ressourcen sollten von `require_principal` abhängen, das die unveränderliche User-ID des Tokens gegen den aktuellen User-Store auflöst. Ein gelöschter/wiedererstellter oder umbenannter User erbt nicht stillschweigend alte Ressourcen, nur weil ein Username passt.

### Rollen und Projekte

- Die globalen Rollen sind `admin` und `user`.
- Admin-Routen erzwingen die aktuell gespeicherte Rolle.
- Der User-Store verhindert das Degradieren des letzten Administrators.
- Projekte haben Owner und Member mit projektspezifischen Rollen.
- Projekt-APIs zentralisieren Zugriffs-Checks, statt nur Routen-Parametern zu vertrauen.

### Credential-Speicherung

Credential-Werte werden mit AES-GCM verschlüsselt, bevor sie in Per-User-Dateien geschrieben werden. Credential-Dateien werden atomar geschrieben und auf Mode `0600` gesetzt, wo unterstützt. Das Matching basiert auf Profil-Auswahl und URL/Host-Patterns; Tools erhalten passende Secrets serverseitig.

**Quellen:** `core/src/hydrahive/api/middleware/auth.py`, `api/middleware/users.py`, `api/routes/_project_route_helpers.py`, `credentials/store.py`, `projects/members.py`.

---

## 5. Agent- und Session-Modell

### Agent-Typen

HydraHive repräsentiert Buddy, persönliche Agenten, Projekt-Agenten und Spezialisten durch die gleiche Core-Agent-Konfiguration, mit Feldern, die Ownership, Projekt-Zuordnung, Spezialisten-Relation und Buddy-Status identifizieren.

Eine Agent-Konfiguration kann wählen:

- Primär-, Fallback- und Compaction-Modelle;
- System-Prompt und wiederverwendbare Skills;
- Native/Plugin-Tools und MCP-Server;
- Temperature, maximale Output-Tokens und Reasoning-Effort;
- maximale Iterationen und Context-Compaction-Settings;
- Long-Term-Memory- und Tool-Confirmation-Verhalten.

### Sessions

Sessions binden einen User an einen Agent und persistieren Messages in SQLite. Metadata kann pro Session Model- und Reasoning-Overrides halten. Sessions können archiviert, getaggt, exportiert, geforkt, abgehängt und fortgesetzt werden.

### Projekte und Workspaces

Der Run-Kontext löst entweder auf den Agent-Workspace oder einen Projekt-Workspace auf. Projekt-Prompts enthalten einen generierten Layout-Hint, der Repositories und Workspace-Pfade beschreibt. Der Tool-Kontext trägt die authentifizierte User-ID, Projekt-ID, Session-ID und effektiven Workspace.

**Quellen:** `core/src/hydrahive/agents/`, `db/sessions.py`, `db/messages.py`, `runner/_run_workspace.py`, `projects/_paths.py`, `workspace/`.

---

## 6. Runner-Datenfluss

Ein normaler Chat-Turn folgt dieser Sequenz:

```text
User-Message
   │
   ▼
Session-Route validiert Owner, Agent und Request
   │
   ├─ persistiert Attachment-Metadata/-Dateien
   ├─ erstellt oder hängt einen Run-Task an
   └─ returnt/streamt Run-Events
   ▼
Runner löst Agent + Projekt-Workspace + Tool-Kontext auf
   │
   ├─ lädt System-Prompt und Skills
   ├─ lädt Native-, MCP- und Plugin-Schemas
   ├─ recallt Long-Term-Memory, wenn aktiviert
   └─ hängt User-Message an
   ▼
Bereite History vor
   │
   ├─ heilt unvollständige Tool-Use-Sequenzen
   └─ compactet, wenn Context-Schwellen es erfordern
   ▼
Rufe Primary-Modell; versuche konfigurierte Fallbacks, wenn angemessen
   │
   ├─ streamt Text/Reasoning-Events
   ├─ persistiert Assistant-Blöcke und Token-Metadata
   └─ audittet Provider/Model/Kosten-Schätzung
   ▼
Keine Tool-Calls? ───────────► Run abschließen + Hintergrund-Kompression
   │
   ▼
Validiere Tool-Calls gegen Allowlist und Permissions
   │
   ├─ optionale User-Bestätigung
   ├─ führe Native-/MCP-/Plugin-Tool aus
   ├─ persistiere Result-Blöcke
   └─ setze Model-Loop fort
```

Schutzverhalten umfasst:

- expliziter Abbruch;
- maximale Iterationen, die einen fortsetzbaren Pausen-State erzeugen;
- Erkennung wiederholter Tool-Loops;
- sichtbare Fehler bei leeren Model-Antworten;
- explizites Handling abgeschnittener Tool-Argumente an `max_tokens`;
- Output-Kompression/-Limits für sehr große Tool-Results;
- Context-Window-bewusste Compaction.

Run-Tasks sind vom initialen Request entkoppelt, damit Browser-Disconnects die Arbeit nicht beenden müssen.

**Quellen:** `core/src/hydrahive/runner/runner.py`, `runner/_runner_iter.py`, `runner/_runner_tools.py`, `runner/concurrency.py`, `api/routes/sessions_messages.py`, `api/routes/_session_msg_helpers.py`.

---

## 7. LLM- und Media-Provider-Layer

### Text-Modelle

Der LLM-Layer normalisiert Calls über direkte/provider-spezifische Adapter und LiteLLM-kompatibles Routing. Er pflegt:

- Provider-Konfiguration;
- Model-Discovery und Metadata;
- Context-Window/Capability-Records;
- OAuth/API-Key-Pfade;
- Retry/Fallback-Verhalten;
- Token- und Cost-Accounting.

Der aktuelle Provider-Katalog/die Konfiguration hat explizite Pfade für Anthropic, OpenAI, OpenAI Codex OAuth, OpenRouter, Groq, Mistral, Google Gemini, NVIDIA NIM, MiniMax und Ollama. Modelle weiterer Anbieter können über Aggregatoren wie OpenRouter oder NVIDIA NIM erscheinen, ohne einen dedizierten Direkt-Provider-Adapter zu implizieren.

### Generierte Medien

Media-Generierung ist vom Text-Runner getrennt. Tools und API-Routen reichen Bild-, Musik-, Sprach-, Transkriptions- oder Video-Arbeit an provider-spezifische Helfer ein. Asynchrone Video-Jobs behalten Provider-Job-State und Media-Metadata bis zur Vollendung.

Lokale Bild/Video-Generierung nutzt ein separates Local-Media-Subsystem mit Model-Katalogen, Installern, Job-Tracking und Worker-Backends. Das automatisierte Setup ist NVIDIA/CUDA-orientiert und daher host-abhängig.

**Quellen:** `core/src/hydrahive/llm/`, `oauth/`, `tools/generate_*.py`, `tools/transcribe_audio.py`, `llm/video_backends/`, `media_*.py`, `api/routes/media_*.py`.

---

## 8. Memory und Data Mining

HydraHive pflegt mehrere verwandte Datenformen:

1. **Messages und Sessions** — der kanonische Konversations-Record;
2. **Summaries/Compaction-Records** — verdichteter Kontext für lange Sessions;
3. **Observations** — vom Agent geschriebene durable Notizen;
4. **Memory-Cards** — versioniertes, verstärktes Wissen mit Confidence, Expiry und Supersession;
5. **LLM/Tool/Session-Audit-Events** — operationelle und Data-Mining-Records;
6. **optionale PostgreSQL-Mirrors** — query-orientierte Kopien für sessionsübergreifende Suche und Analytics.

Bei aktiviertem Long-Term-Memory lädt der Runner hoch-gerankte Cards und kann cue-getriebenen semantischen Recall für substantielle Prompts durchführen. Konsolidierung und Kompression sind best-effort Background-Jobs, sodass ein Fehler die fertige Antwort nicht invalidiert.

Die Data-Mining-API ist eine authentifizierte geteilte Analytics-Grenze statt einer strengen Per-User-Query-Schicht: mehrere Endpoints können den Mirror global inspizieren oder einen Username-Filter akzeptieren. Deployments mit gegenseitig nicht vertrauenswürdigen Nutzern sollten diese Oberfläche einschränken, bis feiner-granulare Autorisierung hinzugefügt ist.

**Quellen:** `core/src/hydrahive/tools/_memory_*.py`, `tools/_observations.py`, `cards/`, `db/_mirror_*.py`, `api/routes/datamining*.py`, `compaction/`.

---

## 9. Persistenz und Filesystem-Layout

### Code-Defaults

Sofern nicht überschrieben:

```text
HH_DATA_DIR=/var/lib/hydrahive2
├── sessions.db             # primäre SQLite-Anwendungs-Datenbank
├── agents/                 # Agent-Konfiguration/Prompts
├── projects/               # Projekt-Metadata/-Konfiguration
├── workspaces/             # Master-, Projekt- und Spezialisten-Workspaces
├── credentials/            # verschlüsselte Per-User-Credential-Profile
├── modules/                # installierte Runtime-Module
├── plugins/                # installierte Agent-Tool-Plugins
├── vms/                    # lokale VM-Disks, ISOs, Logs und VNC-Tokens
└── ...                     # subsystem-spezifischer Runtime-State

HH_CONFIG_DIR=/etc/hydrahive2
├── users.json              # file-backed User und Passwort-Hashes
├── api_keys.json           # HydraHive-API-Key-Records
├── llm.json                # Provider/Model/Media-Backend-Konfiguration
├── mcp_servers.json        # MCP-Konfiguration
├── env                     # optionale systemd-Environment-Overrides
└── compute-pki/            # Compute-CA und Zertifikate
```

Themes werden nach `frontend/src/themes` kopiert und Modul-Frontend-Kopien nach `frontend/src/modules`; sie sind Build-Inputs statt dynamisch servierter JavaScript-Bundles.

Nicht jeder Pfad existiert, bevor sein Feature genutzt wird. Mehrere Config-Stores nutzen atomare Temp-File-and-Rename-Updates; nebenläufige Stores fügen File-Locking hinzu, wo nötig.

### Standard-Linux-Deployment

```text
/opt/hydrahive2             # Source und Python-virtualenv
/var/lib/hydrahive2         # HH_DATA_DIR
/etc/hydrahive2             # Secrets, TLS/Compute-Konfiguration und Env-Overrides
/etc/systemd/system          # Application/Helper-Units und Timer
/var/log/hydrahive2-*.log   # Update- und Helper-Workflow-Logs
```

Der optionale PostgreSQL-Mirror ist getrennt vom primären SQLite-Store und sollte nicht als einzige Kopie der Konversations-Daten behandelt werden.

**Quellen:** `core/src/hydrahive/settings/`, `installer/install.sh`, `installer/modules/20-paths.sh`, `50-systemd.sh`.

---

## 10. Erweiterbarkeits-Verträge

HydraHive hat vier verschiedene Paket-Mechanismen.

### 10.1 Runtime-Module

Runtime-Module werden aus `HH_DATA_DIR/modules/<id>` geladen und enthalten eine `manifest.json`. Ihr Python-Backend exponiert `register(ctx)`. Durch den Modul-Kontext können sie registrieren:

- FastAPI-Router;
- native Agent-Tools;
- Datenbank-Migrationen;
- überwachte periodische Jobs;
- Butler-Trigger-, -Condition- und -Action-Typen;
- ein optionales, vom Modul deklariertes Service-Verzeichnis.

Ein Modul kann auch ein Frontend-Paket bereitstellen, das in die Hauptanwendung kompiliert wird. Der Loader protokolliert Fehler pro Modul und lädt andere weiter. Das Repository liefert ein erforderliches Tasks-Modul, ein Patientenakte-Modul und ein Beispiel-Template; der offizielle Hub enthält den breiteren Katalog.

**Quellen:** `core/src/hydrahive/modules/loader.py`, `modules/context.py`, `modules/manifest.py`, `modules/example/`.

### 10.2 Themes

Theme-Pakete tragen CSS und Metadata bei. Das Frontend wendet das aktive Theme dynamisch an; das Theme-Management teilt die Package-Management-UI, lädt aber kein Python-Backend.

**Quellen:** `core/src/hydrahive/themes/`, `api/routes/themes.py`, `frontend/src/shared/theme.ts`, `frontend/src/shared/themes/registry.ts`, `frontend/src/themes/index.generated.ts`.

### 10.3 Service-Extensions

Service-Extensions sind admin-verwaltete Deployment-Deskriptoren unter `extensions/manifests`. Install/Uninstall-Skripte oder Docker-Compose-Dateien können Drittanbieter-Software provisionieren. Diese Operationen sind absichtlich privilegiert und nicht dasselbe wie das Laden eines HydraHive-UI-Moduls.

Der systemd-Service erhält eng dokumentierte `sudo`-Capabilities für Extension-Operationen, aber der aktuelle Installer erlaubt `/bin/bash` durch sudo. Daher sind der Admin-Endpoint und der Administrator-Account kritische Vertrauensgrenzen.

**Quellen:** `core/src/hydrahive/api/routes/extensions.py`, `api/routes/_extensions_*.py`, `extensions/`, `installer/modules/50-systemd.sh`.

### 10.4 Agent-Tool-Plugins

Plugins werden aus `HH_DATA_DIR/plugins/<name>/plugin.yaml` entdeckt. Der Loader validiert das Manifest, importiert das Entry-Modul und ruft `on_load(ctx)` auf. Ein gewähltes Plugin trägt normale Tool-Schemas zu einem Agent bei, und `tool_bridge.py` ruft die registrierte Async-Tool-Implementierung auf.

Plugin-Python-Code läuft innerhalb des Backend-Prozesses. Es gibt an dieser Grenze keinen Subprozess und keine OS-Sandbox; installierte Plugins sind vollständig vertrauenswürdiger Anwendungs-Code. Pro Plugin Load-Failures sind isoliert, sodass ein anderes kaputtes Plugin die Discovery nicht stoppen muss.

**Quellen:** `core/src/hydrahive/plugins/manifest.py`, `plugins/loader.py`, `plugins/context.py`, `plugins/tool_bridge.py`.

---

## 11. Projekt-Engineering-Subsystem

Ein Projekt kombiniert:

- Identität, Owner und Member;
- einen Workspace;
- ein oder mehrere Source-Repository-Verzeichnisse;
- einen Projekt-Agent und Spezialisten;
- Tasks-Modul-Records, verknüpft per Projekt-ID;
- Sessions, Statistiken und Projekt-Audit-Entries;
- optionale MCP/Plugin/LLM-Key-Integration-Settings;
- optionale Samba/SMB-Mounts, VM/Container-Zuweisungen und Media-Workspace;
- einen optionalen Code-Graph.

Git-Operationen laufen gegen Repository-Mappings innerhalb des Projekt-Workspaces. Gitea-Operationen nutzen den konfigurierten Projekt-Integration/Token-Pfad.

Der Code-Graph lässt das lokale `graphify`-Binary über gewählte Projekt-Verzeichnisse laufen. Query-Tools exponieren Natural-Language-Query, Explanation, Shortest-Paths und Reverse-Impact-Traversal. Graph-Ergebnisse sind nur nach einem erfolgreichen Build/Refresh aktuell.

**Quellen:** `core/src/hydrahive/projects/`, `api/routes/projects*.py`, `code_graph*.py`, `tools/code_graph_tools.py`, `modules/tasks/`.

---

## 12. Compute- und Host-Infrastruktur

### Remote-Compute-Nodes

Der separate `node-agent`-Prozess läuft auf einem verwalteten Node und verbindet sich mit HydraHive. Die Architektur nutzt:

- eine generierte Compute-CA;
- Node-Enrollment und Client-Zertifikate;
- nginx-mTLS-Verifikation für den Connect-Endpoint;
- ein proxy-injiziertes Secret und Node-Identity-Header;
- Heartbeats, Metriken und Command/Workload-Messages.

Siehe [node-agent/README.md](../node-agent/README.md) und [compute-node-runbook.md](compute-node-runbook.md).

### Federation-Workstations

HydraHive kann andere Workstations per URL/Token registrieren, ihre A2A-Cards refreshen, Remote-Audit-Daten abrufen und Client-Bootstrap-Konfigurationen mit optionalen Tailscale-Details generieren. Dies ist getrennt vom Compute-Node-Command-Kanal.

### Lokal und Node-platzierte VMs und Container

Der Linux-Installer kann provisionieren:

- libvirt/QEMU und websockify für VMs und Browser-VNC;
- Incus für System-Container und Browser-Terminal-Sessions.

Diese Komponenten sind optional und auf Hosts ohne erforderlichen Kernel, Virtualisierung und Privilege-Support nicht verfügbar.

**Quellen:** `core/src/hydrahive/compute/`, `federation/`, `vms/`, `containers/`, `api/routes/federation.py`, `node-agent/`, `installer/modules/65-vms.sh`, `70-containers.sh`.

---

## 13. Kommunikations-Architektur

Kommunikations-Adapter übersetzen eine externe Message in eine HydraHive-Session/Run und senden das Ergebnis zurück an den Kanal.

Implementierte Kanal-Familien umfassen:

- WhatsApp über eine gebündelte Node-Bridge;
- Discord über Bot-Konfiguration;
- Matrix-basierter Team-Chat;
- IMAP/SMTP-Mail-Tools;
- Voice-Upload/Stream-Pfade, gestützt auf konfigurierte STT/TTS-Komponenten.

Kanäle sind optionale Runtimes. Ihre Verfügbarkeit wird durch installierte Bridge-Komponenten, Credentials und Service-Health bestimmt, nicht nur durch das Vorhandensein von API-Routen.

**Quellen:** `core/src/hydrahive/communication/`, `teamchat/`, `voice/`, `api/routes/communication_whatsapp*.py`, `communication_discord*.py`, `teamchat.py`, `stt.py`, `tts.py`.

---

## 14. Deployment und Lifecycle

### Linux

`installer/install.sh` orchestriert nummerierte Installer-Module. Das normale Deployment besteht aus:

- `hydrahive`-Service-User;
- Python-3.12-virtualenv;
- gebauten React-Assets;
- Loopback-uvicorn-Service;
- nginx-HTTPS-Kante;
- systemd-Helper/Timern für Update, Restart, Voice, Bridge, Samba und Migration-Requests;
- optional AgentLink, Samba, PostgreSQL, WhatsApp, VMs, Container, Voice und Tailscale.

`KillMode=process` wird genutzt, sodass ein Backend-Restart VM/Container-Child-Prozesse nicht automatisch beendet.

### Updates und Migration

Die UI kann Update/Restart-Arbeit anfordern, indem sie Trigger-Dateien schreibt, die von privilegierten systemd-Helpern konsumiert werden. Das Update-Skript baut, testet und kann rollbacken. Migration nutzt einen dedizierten rsync-Workflow und kann lange laufen.

### macOS

`installer/install-mac.sh` bietet ein experimentelles natives Setup. Es kann Linux-spezifisches systemd-, libvirt-, Incus- oder nginx-Service-Verhalten nicht unverändert bereitstellen.

**Quellen:** `installer/install.sh`, `installer/update.sh`, `installer/migrate.sh`, `installer/modules/`.

---

## 15. Sicherheitsgrenzen und operationelle Konsequenzen

| Grenze | Konsequenz |
|---|---|
| Browser ↔ nginx | TLS und Security-Header schützen Transport/UI; Default-Zertifikat ist selbstsigniert |
| nginx ↔ FastAPI | Backend sollte im Standard-Deployment loopback-only bleiben |
| User ↔ Projekt | Mitgliedschafts/Rollen-Checks müssen jede Projekt-Ressource schützen |
| Agent ↔ Tool | Tool-Zuweisung und Confirmations kontrollieren Capability, aber ein erlaubtes Tool kann mächtig sein |
| HydraHive ↔ Model-Provider | Prompt, Attachment und Tool-Kontext, die an Cloud-Modelle gesendet werden, verlassen den Host |
| Core ↔ Modul/Plugin | Installierter Code ist vertrauenswürdig; Failure-Isolation ist keine Malicious-Code-Sandbox |
| Admin ↔ Extension-Installer | Extension-Installation kann per Design Root-Code-Execution werden |
| HydraHive ↔ Compute-Node | Node-Identität stützt sich auf Enrollment, Client-Zertifikate und Proxy-Checks |
| Credential-Store ↔ Tool | Secrets werden nur serverseitig entschlüsselt und sollten nie in Tool-Output zurückgegeben werden |

Für eine ausführlichere missbrauchsorientierte Analyse siehe [SECURITY_THREAT_MODEL.md](SECURITY_THREAT_MODEL.md).

---

## 16. Verifikations-Karte

Bei Änderung eines Subsystems diese primären Verifikations-Ziele nutzen:

| Änderung | Mindest-Checks |
|---|---|
| Backend/API | `cd core && python -m pytest && python -m ruff check src tests` |
| Frontend/Routen | `cd frontend && npx tsc --noEmit && npm run build` |
| Modul | Core-Modul-Loader-Tests plus eigene Tests/Build des Moduls |
| Plugin | Loader/Executor-Tests und Manifest-Fixture-Validierung |
| Installer/Proxy | `bash -n` auf geänderten Skripten; generierte nginx/systemd-Konfiguration auf kompatiblem Host validieren |
| Dokumentation | Link/Path-Checks, Command-Review und Source-Cross-Check gegen aktuelle Routen/Manifest/Config-Dateien |

CI führt aktuell Backend-Tests/ruff und den Frontend-TypeScript-Check aus. Einiges Infrastruktur-Verhalten lässt sich nur auf einem kompatiblen Linux-Host vollständig verifizieren.
