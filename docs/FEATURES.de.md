# HydraHive Feature-Inventar

> 🇬🇧 [English version](FEATURES.md)

Dieses Dokument hält die nutzersichtbaren und operator-orientierten Features fest, die im aktuellen HydraHive-Core-Repository und im offiziellen Modul-Hub implementiert sind.

Es ist ein Inventar, keine Aussage, dass jedes Feature auf jeder Installation aktiv ist. Verfügbarkeit hängt von der authentifizierten Rolle, installierten Modulen, gewählten Installer-Komponenten, Credentials, externen Diensten und Hardware ab.

## Status-Labels

| Label | Bedeutung |
|---|---|
| **Core** | im HydraHive-Core-Backend/Frontend-Repository implementiert |
| **Module** | über den separaten `hydrahive2-modules`-Hub verteilt; Backend wird zur Laufzeit geladen, Frontend bei Installation/Update gebaut |
| **Optional** | implementiert, aber nicht verfügbar bis aktiviert oder konfiguriert |
| **External dependency** | benötigt eine Drittanbieter-API, -Dienst, -Konto oder -Executable |
| **Infrastructure-dependent** | benötigt Host-Fähigkeiten wie libvirt, Incus, Docker, systemd oder NVIDIA/CUDA |
| **Template** | Entwickler-Beispiel statt Produktiv-Feature |

Primäre Verifikations-Quellen:

- API-Assembly: `core/src/hydrahive/api/main.py`;
- Frontend-Routen: `frontend/src/App.tsx`;
- Navigation: `frontend/src/shared/nav-config.ts`;
- native Tools: `core/src/hydrahive/tools/__init__.py`;
- Runtime-Module: `core/src/hydrahive/modules/`;
- Service-Extensions: `extensions/manifests/*.json`;
- Linux-Provisionierung: `installer/install.sh` und `installer/modules/`;
- offizieller Modul-Katalog: `hydrahive2-modules/hub.json` und `manifest.json` jedes Moduls im separaten Repository.

---

## 1. Agenten und Buddy

**Status: Core**

- Persönlicher Buddy wird pro Nutzer angelegt.
- Eigenständige Agenten, Projekt-Agenten und Projekt-Spezialisten.
- Agent-Create/Read/Update/Delete und Enable/Disable.
- System-Prompt und bearbeitbare Agent-Markdown-Dateien.
- Primäres Text-Modell, geordnete Fallback-Modelle und optionales Compaction-Modell.
- Temperature, Output-Token-Limit, Reasoning-Effort, Cache-Lebensdauer und maximale Iterationen.
- Native-/Plugin-Tool-Auswahl und MCP-Server-Zuweisungen.
- Optionale Bestätigung vor Tool-Ausführung.
- Optionale Long-Term-Memory- und Context-Compaction-Kontrollen.
- Agent-Activity-Stream und visueller Activity-Monitor.
- Spezialisten-Erstellung/-Konfiguration und AgentLink-Delegation.
- Externe AgentLink-Instanzen mit generierten API-Keys.

**Quellen:** `core/src/hydrahive/agents/`, `core/src/hydrahive/buddy/`, `core/src/hydrahive/api/routes/agents.py`, `buddy.py`, `agent_activity.py`, `external_instances.py`, `frontend/src/features/agents/`, `frontend/src/features/buddy/`.

### Skills

**Status: Core**

- Markdown-basierte Skills mit Name, Beschreibung, Aktivierungs-Hinweis und Body.
- Globale, Projekt- und Spezialisten-Scopes.
- Pro Agent Disabled-Skill-Listen.
- List/Load/Create/Update/Delete-Tools für Agenten.
- System-Default-Skills, die mit dem Core ausgeliefert werden.

**Quellen:** `core/src/hydrahive/skills/`, `core/src/hydrahive/tools/list_skills.py`, `load_skill.py`, `write_skill.py`, `delete_skill_tool.py`, `frontend/src/features/skills/`.

---

## 2. Chat und Run-Lifecycle

**Status: Core**

- Streaming-Assistant-Output via Server-Sent Events.
- Text- und Datei-Anhänge, inklusive Bild-Content-Blöcken.
- Tool-Use- und Tool-Result-Karten mit Live-Status.
- User-Approval/Denial für bestätigungspflichtige Tool-Calls.
- Serverseitiger Run-Task, der nach dem Schließen des ursprünglichen Browser-Requests weiterlaufen kann.
- Reattach an eine laufende Session, Run-Status-Polling und expliziter Abbruch.
- Resend aus einer früheren Nachricht und Continue nach pausiertem Iterations-Limit.
- Session-Titel/Status-Update, Projekt-Zuordnung und Löschung.
- Pro Session Text-Model- und Reasoning-Effort-Override.
- Projekt-Picker und projekt-gebundener Chat.
- Workspace-Datei-Viewer/Editor und Git-Panel neben dem Chat.
- Nachrichten-Suche, Paginierung und Preview generierter Medien.
- Voice-Input plus Browser/Local/MiniMax/OpenRouter-Speech-Output-Pfade.
- Hydra-Emotes.
- Lokale Slash-Commands: `/help`, `/clear`, `/model`, `/compact`, `/tokens`, `/title`, `/system`, `/tools`, `/skills`, `/agent`, `/export` und direkte Skill-Invocation.

HydraHive exponiert den früher dokumentierten Archive/Tag/Fork-Workflow aktuell nicht als Core-Session-API-Operationen; die implementierten Session-Operationen sind in `sessions.py` und `sessions_messages.py` definiert.

**Quellen:** `core/src/hydrahive/api/routes/sessions.py`, `sessions_messages.py`, `core/src/hydrahive/runner/`, `frontend/src/features/chat/`.

### Runner-Schutzmaßnahmen

- Primary-zu-Fallback-Model-Routing.
- Max-Iterations-Pause.
- Erkennung wiederholter Tool-Loops.
- Expliziter Fehler bei leerem Modell-Output.
- Explizites Fehlschlagen bei Tool-Argumenten, die durch das Output-Token-Limit abgeschnitten wurden.
- Tool-Result-Char-Limits und History-Compaction.
- Heilung unvollständiger Tool-Use-Sequenzen.
- Persistierte Token/Cache/Model-Metadaten und geschätzte Kosten pro LLM-Call.

**Quellen:** `core/src/hydrahive/runner/runner.py`, `_runner_iter.py`, `_runner_tools.py`, `core/src/hydrahive/compaction/`, `core/src/hydrahive/db/llm_calls.py`.

---

## 3. Native Tools, MCP und Plugins

**Status: Core; Tool-Verfügbarkeit ist agent-spezifisch**

Die Core-Registry umfasst Tool-Familien für:

- Shell-Execution und Workspace-File-Read/Write/Patch;
- Web-Suche, authentifiziertes HTTP-Fetch und Browser-Automation;
- Memory-Read/Write/Search und Session-Observations;
- Session-Data-Mining und Timelines;
- Mail-Read/Send;
- Projekt-, Spezialisten- und Skill-Management;
- Agent-zu-Agent-Delegation bei konfiguriertem AgentLink;
- Bild-Analyse und Bild/Musik/Sprache/Video-Generierung;
- Audio-Transkription;
- Prompt-Archive-Zugriff;
- Code-Graph-Query/Explain/Path/Impact/Refresh;
- Webmin-Status und generisches RPC bei Konfiguration.

Installierte Module können weitere Tools beitragen. Aktuelle offizielle Beispiele: Home Assistant, Crypto, Mediacenter, Deep Research, Patientenakte, Scratchpad, Tasks und Atelier-Tools.

### MCP

- MCP-Server-Konfiguration und pro Agent Zuweisung.
- Schemas werden von gewählten Servern entdeckt und mit nativen/Plugin-Schemas zusammengeführt.
- stdio-, streamable-HTTP- und SSE-Transport wie von der MCP-Client-Implementierung definiert.

### Plugins

- Plugin-Hub-Cache plus validierte `plugin.yaml`-Manifeste unter `HH_DATA_DIR/plugins`.
- Dynamische Tool-Schemas, die Agenten zugewiesen werden.
- Plugin-Install/Update/Uninstall-Management.
- Pro Plugin Discovery-/Load-Fehler-Isolation.

Der Loader importiert Plugin-Python und ruft `on_load(ctx)` innerhalb des Backend-Prozesses auf. Es gibt keinen Subprozess und keine OS-Sandbox; installierter Plugin-Code ist vollständig vertrauenswürdiger Code.

**Quellen:** `core/src/hydrahive/tools/__init__.py`, `core/src/hydrahive/mcp/`, `core/src/hydrahive/plugins/`, `core/src/hydrahive/api/routes/mcp.py`, `plugins.py`.

---

## 4. Memory, Compaction und Data Mining

### Agent-Memory

**Status: Core; semantischer Recall benötigt den PostgreSQL-Mirror und Embeddings**

- Pro Agent Observation-Log.
- Persistente Memory-Notizen mit Key, Content, Projekt-Scope, Confidence, Expiry und Supersession-Verhalten.
- Full-Text-ähnliche lokale Memory-Suche.
- Memory-Cards im optionalen PostgreSQL-Mirror.
- Proaktiver Top-Card-Recall und cue-getriggerter semantischer Recall bei aktiviertem Long-Term-Memory.
- Hintergrund-Session-Kompression und Memory-Kristallisation/-Konsolidierung.
- Manuelle Memory-Inspektion und Curation-Seite.

**Quellen:** `core/src/hydrahive/tools/_memory_*.py`, `read_memory.py`, `write_memory.py`, `search_memory.py`, `_observations.py`, `core/src/hydrahive/cards/`, `core/src/hydrahive/db/_mirror_cards*.py`, `frontend/src/features/memory/`.

### Context-Compaction

- Context-Window-bewusste Schwelle.
- Separates Compaction-Modell.
- Konfigurierbare Reserve, behaltene Turns und Tool-Result-Limit.
- Persistierte Compaction-Events.
- Manueller `/compact`-Befehl und Pre-Resume-Compaction.

**Quellen:** `core/src/hydrahive/compaction/`, `core/src/hydrahive/db/compaction_events.py`, `core/src/hydrahive/runner/runner.py`.

### Data Mining

**Status: Optionaler PostgreSQL-Mirror**

- Recent-Event-View.
- Full-Text- und semantische Event-Suche.
- Session-Listing/Detail und Event-Topology-Graph.
- Embedding-Status, Reset, Rechunk und Backfill.
- Importe aus HydraHive-SQLite, Git, JSONL, nginx/journal-Logs und hochgeladener Shell-History.
- GitHub-Issue/PR-Event-Import.
- Tages-, letzte-Session-, pro-Session- und pro-Agent-Token-Statistiken.
- Agent-Tools für semantische Suche, Full-Text-Suche, Timeline und Daily-Summary.

**Sicherheitsgrenze:** die aktuellen Data-Mining-Endpoints erfordern Authentifizierung, aber die Route-Layer ist nicht generell auf den eigenen Username des Aufrufers beschränkt und einige Queries akzeptieren einen expliziten Username-Filter. Als sensitive geteilte Analytics-Oberfläche behandeln und den Nutzerzugriff auf Deployment-Ebene einschränken, bis feiner-granulare Autorisierung implementiert ist.

**Quellen:** `core/src/hydrahive/api/routes/datamining*.py`, `core/src/hydrahive/db/_mirror*.py`, `core/src/hydrahive/tools/datamining*.py`, `frontend/src/features/datamining/`.

---

## 5. Projekte und Engineering-Workspaces

**Status: Core**

- Projekt-Create/Read/Update/Delete.
- Ersteller plus Member mit projektspezifischen Rollen `read`, `write` und `admin`; der Ersteller hat impliziten Projekt-Admin-Zugriff.
- Projekt-Audit-Log.
- Projekt-Sessions und aggregierte Statistiken.
- Projekt-Agenten und -Spezialisten.
- Isolierter Projekt-Workspace.
- File-Tree, Read, Write, Upload und Delete.
- Mehrere Repository-Ordner mit Git-Initialize/Clone/Configure/Status/Diff/Commit/Pull/Push/Remove-Operationen.
- Gitea-Repository-Erstellung und Push/Pull-Integration.
- Samba-Workspace-Share-Konfiguration.
- SMB-Mount-Registry und pro Projekt Zuweisung.
- VM-/Container-Zuweisung zu Projekten.
- Projekt-Integrationen für MCP-IDs, erlaubte Plugins und Projekt-LLM-Key.
- Projekt-gebundene persistente Tasks über das erforderliche Tasks-Modul.

Das aktuelle Tasks-Panel unterstützt Create, Priorität und Status-Übergänge. Das Core-Repository enthält das früher dokumentierte Projekt-Task-Comments- oder GitHub-Issue-Synchronisations-Subsystem nicht.

**Quellen:** `core/src/hydrahive/projects/`, `core/src/hydrahive/api/routes/projects*.py`, `smbmounts.py`, `frontend/src/features/cockpit/project/`, `modules/tasks/`.

### Code-Graph

**Status: Core; benötigt einen Projekt-Build**

- Scan-Verzeichnisse innerhalb eines Projekts wählen.
- Lokalen Graph mit Metriken und Cycle-Report über das `graphify`-Binary bauen.
- Query, Explain, Shortest-Path und Reverse-Impact-Traversal aus Agent-Tools.
- Refresh nach Quelltext-Änderungen.

Der Graph spiegelt seinen letzten erfolgreichen Build; er wird nicht automatisch nach jeder Bearbeitung aktualisiert.

**Quellen:** `core/src/hydrahive/code_graph*.py`, `core/src/hydrahive/api/routes/code_graph.py`, `core/src/hydrahive/tools/code_graph_tools.py`, `frontend/src/features/cockpit/project/ProjectGraphOverlay.tsx`.

---

## 6. Modelle und Provider

**Status: Core; Credentials/Local-Runtime erforderlich**

Der aktuelle Provider-Katalog/die Konfiguration hat explizite Einträge für:

- Anthropic;
- OpenAI;
- OpenAI Codex OAuth;
- OpenRouter;
- Groq;
- Mistral;
- Google Gemini;
- NVIDIA NIM;
- MiniMax;
- Ollama-kompatible lokale oder geschützte Endpoints.

Modelle anderer Anbieter können weiterhin über Aggregatoren wie OpenRouter oder NVIDIA NIM erscheinen; das ist kein dedizierter Direkt-Provider-Adapter.

Capabilities:

- Live-Provider-Model-Listing, wo ein Endpoint existiert;
- statische Fallback-Modelle für ausgewählte Provider;
- Model-Purpose-Klassifikation für Chat, Embeddings, Speech, Transcription, Image, Video und Music;
- Context-Window-, Tool-Use-, Category- und Parameter-Metadaten, wo bekannt;
- Preis-/Usage-Schätzungen;
- kanonische Model-Registry mit Cache- und Incomplete-Fetch-Handling;
- Provider-Keys, Base-URLs, Group-IDs und OAuth-Pfade;
- Model-Tool-Support-Gate;
- pro Agent und pro Session Auswahl.

**Quellen:** `core/src/hydrahive/llm/_catalog_data.py`, `catalog.py`, `registry.py`, `_config.py`, `client.py`, `core/src/hydrahive/oauth/`, `frontend/src/features/llm/`.

### Ollama

- Live-Modell-Katalog und -Capabilities.
- Pull, Running-Model und Delete/Lifecycle-Management.
- Context-Size-Auswahl mit VRAM-aware-Cap.
- `llmfit`-Hardware-Fit-Information bei Installation.

**Quellen:** `core/src/hydrahive/llm/ollama_*.py`, `core/src/hydrahive/api/routes/llm_catalog_ollama.py`, `installer/modules/35-llmfit.sh`.

---

## 7. Generierte Medien und Media Cockpit

### Agent-Media-Tools

**Status: Core; OpenRouter oder konfiguriertes Local-Backend erforderlich**

- Vision-/Bild-Analyse.
- Text-zu-Bild- und Reference-Image-Generierung.
- Optionaler Green-Screen-Chroma-Key für transparente Bild-Ausgabe.
- Text-zu-Musik-Generierung.
- Text-zu-Sprache.
- Text/Bild-zu-Video asynchrone Jobs.
- Audio-Transkription.
- Generierte Dateien werden im aktiven Workspace gespeichert und im Chat vorab angezeigt.

**Quellen:** `core/src/hydrahive/tools/analyze_image.py`, `generate_image.py`, `generate_music.py`, `generate_speech.py`, `generate_video.py`, `transcribe_audio.py`.

### Prompt-Archiv

- Kategorien für Image, Music, System, Video, Speech und Other Prompts.
- Prompt-Text, fester Style-Anchor, Model, Params, Seed, Tags, Notes und Sample-Path.
- User-owned/private und Public Entries.
- List/Get/Save-Agent-Tools.

**Quellen:** `core/src/hydrahive/db/prompt_archive.py`, `core/src/hydrahive/api/routes/prompt_archive.py`, `core/src/hydrahive/tools/prompt_archive.py`.

### Media Cockpit

**Status: Core-Projekt-Workspace; Generierungs-Workflows hängen von installierten Modulen/Backends ab**

- Medien-Projekte, gebunden an HydraHive-Projekte.
- Idee/Brief, Prompts, Drehbuch mit Akten/Szenen/Shots, Referenzen und Assets.
- Workspace-Datei-Browsing und Medien-Asset-Registrierung.
- Timeline-Tracks, Transitions und Export-Library.
- Video-Schnitt/Assembly-Operationen.
- Pluggable `mediaSources` und `mediaWorkflows` aus Modulen.

**Quellen:** `core/src/hydrahive/media_*.py`, `core/src/hydrahive/api/routes/media_*.py`, `frontend/src/features/cockpit/MediaCockpitPage.tsx`, `frontend/src/features/cockpit/media/`.

### Local-Media-Backend

**Status: Optional; NVIDIA/CUDA und Docker vom automatisierten Installer vorausgesetzt**

- ComfyUI- und Switch-HTTP-Backend-Registry.
- Workflow-Import/Parser mit Parameter-Mapping.
- Lokale Bild-/Video-Model-IDs (`local:`-Routing).
- Automatisierter ComfyUI-Docker-Setup auf NVIDIA-Hosts.
- Installer registriert SDXL-Image-, Wan-Text-to-Video- und Wan-First/Last-Frame-Workflows.

Der Local-Media-Installer lädt große Drittanbieter-Modelle und validiert gepinnte SHA-256-Hashes. Ohne kompatible NVIDIA-GPU wird die Phase übersprungen.

**Quellen:** `core/src/hydrahive/api/routes/media_backends.py`, `core/src/hydrahive/llm/video_backends/`, `installer/modules/72-local-media.sh`, `installer/media-workflows/`.

---

## 8. Butler-Automatisierung

**Status: Core; Module können Node-Typen beitragen**

- Flow-Create/Read/Update/Delete.
- Graph aus Trigger-, Condition- und Action-Nodes.
- User- oder Projekt-Scope.
- Dry-Run-Execution.
- Projekt-Webhook-Trigger mit optionalem Projekt-Secret.
- Runtime-Registry durch Module erweitert.
- Überwachte periodische Modul-Jobs.
- Cryptoboard trägt Price/Alert-Poller plus Butler-Trigger/Condition-Typen bei.

Die Webhook-Route behält einen deprecated Kompatibilitätspfad, wenn ein Projekt kein konfiguriertes Secret hat. Vor dem Exponieren von Projekt-Webhooks ein Secret konfigurieren.

**Quellen:** `core/src/hydrahive/butler/`, `core/src/hydrahive/api/routes/butler.py`, `core/src/hydrahive/modules/context.py`, `frontend/src/features/butler/`, `hydrahive2-modules/cryptoboard/backend/__init__.py`.

---

## 9. Kommunikation, Voice und Research

### WhatsApp

**Status: Optional Bridge**

- Node-Bridge-Installation und Secret.
- Pairing/Status, Chats/Nachrichten und Inbound-Processing.
- Text/Media-Handling und Voice-Conversion-Support.
- Route- und Runtime-Health-Management.

**Quellen:** `core/src/hydrahive/communication/whatsapp/`, `core/src/hydrahive/api/routes/communication_whatsapp*.py`, `installer/modules/45-whatsapp.sh`.

### Discord

**Status: Optional Bot**

- Bot-Konfiguration, Enable/Disable-State und Message-Bridge.

**Quellen:** `core/src/hydrahive/communication/discord/`, `core/src/hydrahive/api/routes/communication_discord*.py`.

### Matrix-Teamchat

**Status: Optional Matrix-Homeserver**

- Team-Chat-Rooms/Messages und authentifizierte API.
- Tuwunel kann separat aus dem Extension-Katalog installiert werden.

**Quellen:** `core/src/hydrahive/teamchat/`, `core/src/hydrahive/api/routes/teamchat.py`, `core/src/hydrahive/settings/_teamchat.py`.

### Mail

**Status: Optional IMAP/SMTP**

- Agent-Tools zum Mail-Lesen ohne als gelesen zu markieren und zum Senden von Klartext-Mail.
- Globale Defaults plus Tool-spezifische Credential-Konfiguration.
- Optionaler Incoming-Mail-Watcher/Butler-Integration.

**Quellen:** `core/src/hydrahive/tools/read_mail.py`, `send_mail.py`, `core/src/hydrahive/settings/_mail.py`, `core/src/hydrahive/communication/mail/watcher.py`.

### Voice

**Status: Core-STT/TTS-APIs plus optional Install/Module**

- Browser-Voice-Input und Browser/Local/Cloud-Voice-Output im Chat.
- Core-STT- und TTS-Endpoints.
- Installer kann Wyoming Faster Whisper und Wyoming Piper in Incus provisionieren; installiert außerdem das optionale MiniMax-`mmx`-CLI.
- Offizielles Voice-Modul stellt eine Voicebox für den Home-Assistant-Voice-PE-Pfad bereit.

**Quellen:** `core/src/hydrahive/api/routes/stt.py`, `tts.py`, `core/src/hydrahive/voice/`, `frontend/src/features/chat/useVoice*.ts`, `installer/modules/55-voice.sh`, `hydrahive2-modules/voice/`.

### Research-APIs

- Konfigurierbare Research-API-Profile.
- Deep-Research-Modul führt mehrstufige Web-Recherche durch und liefert einen zitierten Bericht.

**Quellen:** `core/src/hydrahive/research/`, `core/src/hydrahive/api/routes/research_apis.py`, `hydrahive2-modules/deepresearch/`.

---

## 10. Infrastruktur

### Compute-Nodes und Jobs

**Status: Core; Remote-Node-Agent erforderlich**

- Node-Enrollment/Bootstrap, Recovery-Ergebnis und Zertifikats-Lifecycle.
- mTLS-geschützter Compute-Agent-Kanal über die Standard-nginx-Kante.
- Heartbeats, Node-Health, Sequence/Nonce-Checks und Audit-Records.
- Remote-Command/Job-Queue und Console-Tickets.
- CPU/RAM/Storage/GPU-Inventar, wo gemeldet.
- Placement-Felder für VM/Container-Runtimes.

**Quellen:** `core/src/hydrahive/compute/`, `core/src/hydrahive/api/routes/compute_*.py`, `node-agent/`, `installer/modules/60-nginx.sh`.

### Virtuelle Maschinen

**Status: Infrastructure-dependent**

- VM-Create/List/Update/Delete.
- Start, Stop, Restart, Pause, Resume, Shutdown und Force-Actions.
- ISO-Upload/List/Delete.
- Disk-Import und Passthrough.
- Snapshot-Lifecycle.
- Browser-VNC-Tickets/Proxy.
- Local- oder Compute-Node-Runtime-Placement.

**Quellen:** `core/src/hydrahive/vms/`, `core/src/hydrahive/api/routes/vms*.py`, `frontend/src/features/vms/`, `installer/modules/65-vms.sh`.

### Container

**Status: Infrastructure-dependent**

- Incus-Container-Create/Read/Update/Delete.
- Start, Stop, Restart und Snapshot-Operationen.
- Browser-Terminal/WebSocket-Console.
- Local- oder Compute-Node-Placement.

**Quellen:** `core/src/hydrahive/containers/`, `core/src/hydrahive/api/routes/containers*.py`, `frontend/src/features/containers/`, `installer/modules/70-containers.sh`.

### Federation und Tailscale

- Workstation-Registry mit gecachten A2A-Cards und Remote-Audit-Retrieval.
- TLS-Verifikation per Default pro Workstation, mit explizitem Opt-out für Self-Signed-LAN/Tailnet-Peers.
- Client-Config-Generator kombiniert einen HydraHive-API-Key, AgentLink-Koordinaten und optionale Tailscale-Invitation.
- Tailscale-Status/Setup-Endpoints und optionale Installer-Phase.

**Quellen:** `core/src/hydrahive/federation/`, `core/src/hydrahive/api/routes/federation.py`, `tailscale.py`, `core/src/hydrahive/tailscale/`, `installer/modules/80-tailscale.sh`.

---

## 11. Offizieller Modul-Hub

**Status: separates Repository; Install/Update baut das Frontend neu und fordert einen Backend-Restart an**

Der offizielle Hub enthält aktuell **18 Einträge**:

```text
18 directories with manifest.json
= 17 end-user modules + 1 example template
```

| Modul | Aktuelle Manifest-Version | Capability | Agent-/Runtime-Beiträge |
|---|---:|---|---|
| Archiver | 2.0.2 | archiviert Webseiten, Forum-Threads und Dokumente; Jobs, Drive-Status, Diagnose, Repair/Export | Router, Migration |
| Atelier | 1.6.5 | projekt-gebundene Bild/Video/Musik/Film-Produktion mit Charakteren, Drehbuch, Shots, Galerie und Composition | Read/Write-Tools; hängt von Video-Editor ab |
| Blueprint | 1.0.2 | visueller Node-Canvas für Layouts und Workflows | Router, Migration |
| Brettspiele | 1.0.2 | Browser-Brettspiele inklusive Schach und Ergebnis-Speicherung | Routers, Migration, Buddy-Widget |
| Cryptoboard | 1.1.2 | Preise, Charts, Watchlist, Portfolio/Trades, CSV-Import, Wallets, Alerts, Indikatoren und News | 3 Tools, Butler-Typen, 2 Poll-Jobs, Migration |
| Deep Research | 1.0.2 | mehrstufige, quellenbasierte Recherche-Berichte | `research_report`-Tool, Router, Migration |
| Haushaltsbuch | 1.5.3 | Haushalts-Mitglieder, Ledger, Budgets/Planung, Bank-Import und experimentelles Read-Only-Lidl-Plus-Beleg-Sync | Routers, Migration |
| Home Assistant | 1.0.2 | Entities listen/lesen, Templates rendern und Services aufrufen | 4 Tools, Router, Migration |
| Mediacenter | 0.8.1 | profil-gefilterte Treasure-Maps-Suche und kontrollierte SABnzbd-Queue/History | 5 Tools, Routers, Migration |
| Minigames | 1.0.2 | kleine Browser-Spiele und Highscores | Router, Migration, Buddy-Widget |
| Musicplayer | 1.0.1 | Playlist/Equalizer für generierte und hochgeladene Musik | Routers, Migration, Buddy-Widget |
| Notizbuch | 1.0.2 | User-Notizen | CRUD-Router, Migration |
| Meine Akte | 1.0.2 | strukturierter Record, eGA/FHIR-Importe und Apple-Health-Views | 2 Read-Tools, Routers, Migrations, Buddy-Widget |
| Scratchpad | 1.0.2 | getrennte User- und Agent-Notiz-Zonen | 2 Tools, Router |
| Aufgaben | 1.0.1 | persistente Tasks über Sessions und optionale Projekt-Relation | 4 Tools, Router, Migration, Buddy/Workspace-UI |
| Video-Editor | 0.1.2 | Browser-Timeline, Trimming und Hybrid-Export | Router; Dependency von Atelier |
| Voice | 0.8.0 | Voicebox/HA-Voice-PE-Assistent-Settings, Transcript, STT/TTS und Speech | Routers |
| Beispiel-Modul | 1.0.1 | minimales Entwickler-Beispiel | Template-Router und Migration |

Versionen und Beschreibungen oben stammen direkt aus den Modul-Manifesten zum Zeitpunkt dieses Inventars. Die installierte Version kann abweichen, bis der Administrator aktualisiert.

### Modul-Lifecycle

- Die Default-Hub-URL ist `https://github.com/hydrahive/hydrahive2-modules.git`.
- Zusätzliche kommaseparierte Hub-URLs sind konfigurierbar; bei Überlappung gewinnt die erste Modul-ID.
- Hub-Operationen nutzen einen lokalen shallow Git-Cache und ein 15-Sekunden-Git-Command-Timeout.
- Installation kopiert das volle Modul nach `HH_DATA_DIR/modules/<id>` und sein Frontend nach `frontend/src/modules/<id>`.
- Abhängigkeiten werden zuerst installiert.
- Das Frontend wird neu gebaut, dann wird ein verzögerter Restart-Request geschrieben.
- Deinstallation entfernt Modul-Dateien, behält aber bewusst Modul-Datenbank-Tabellen/Daten.
- Ein fehlerhafter Modul-Load ist gegenüber anderen Modulen isoliert.
- Das Tasks-Modul wird von Core-Cockpit-Features benötigt und aus der gebündelten Quelle repariert, wenn es fehlt oder unvollständig ist.

**Quellen:** separates Repository `hub.json` und `*/manifest.json`; Core `core/src/hydrahive/modules/hub_client.py`, `installer.py`, `loader.py`, `context.py`.

---

## 12. Service-Extensions

**Status: Core-Admin-Lifecycle; jeder Drittanbieter-Dienst ist optional**

Das Core-Repository enthält **32 Extension-Manifeste**, berechnet als:

```text
find extensions/manifests -name '*.json' → 32 files
```

Zugehörige lokale Assets:

```text
29 install scripts
29 uninstall scripts
5 Docker Compose files
```

Katalog nach Kategorie:

- **AI:** AnythingLLM, Ollama, Skill Seekers;
- **development:** Go, Java 21, Node.js, Rust;
- **tools:** Code Server, Gitea, SearXNG, ShadowBroker;
- **network:** AdGuard Home, Headscale, Pi-hole, Tuwunel;
- **security:** Vaultwarden;
- **productivity:** BookStack, Mailcow, Monica CRM, Radicale, Vikunja;
- **media:** Plex, Radarr, SABnzbd, Sonarr;
- **gaming:** HyOS, Minecraft, TrinityCore 3.3.5a, Valheim;
- **dashboard/documents/system:** Heimdall, Paperless-ngx, Webmin.

Das sind Installations-/Integrations-Deskriptoren für Drittanbieter-Software. Sie sind nicht per Default installiert und nicht von HydraHive lizenziert. Extension-Actions können privilegierte Shell- oder Docker-Operationen aufrufen und benötigen daher Administrator-Vertrauen.

**Quellen:** `extensions/manifests/`, `extensions/install/`, `extensions/uninstall/`, `extensions/docker/`, `core/src/hydrahive/api/routes/extensions.py`.

---

## 13. Weitere Core- und Modul-Arbeitsbereiche

### Core-Arbeitsbereiche

- **Dashboard:** lokale Summary-Cards inklusive System/Agent/Projekt/Token-Infos.
- **Project Cockpit:** dichter Projekt-Chat, Agenten, Git, Dateien, Tasks und Management-Overlays.
- **Buddy Cockpit:** persönlicher Assistent und installierte Buddy-Widgets.
- **Media Cockpit:** Medien-Projekt-Vorbereitung und Post-Produktion.
- **Vault Cockpit:** Offline-first Launchpad für Patientenakte, Cryptoboard, Scratchpad, Credentials, Data Mining und Memory.
- **Admin Cockpit:** User, LLM, MCP, Credentials, Module, Themes, Plugins, Extensions, VMs, Container, Nodes/Jobs und System-Links.
- **Communication, Teamchat, Butler, Federation, Streaming, Data Mining, Memory, Zahnfee und Help** Seiten.

Der aktuelle Vault ist ein Launchpad/Soft-Guard. Das dort angezeigte künftige 15-Minuten-Hard-Lock, der konsolidierte Dokumenten-/OCR-Store und die automatische KI-Analyse sind noch nicht implementiert. Diese Punkte sind in `VaultCockpitPage.tsx` explizit als Roadmap markiert.

### Streaming-Downloader

**Status: Core, spezialisierte externe Abhängigkeit**

- verschlüsselte Per-User-Ghostflix-Credentials;
- Series-Scrape;
- ausgewählte Episoden-Download-Jobs;
- Ausgabe-Pfad in eine Plex-Library;
- Job-Liste, Abbruch und Löschung.

**Quellen:** `core/src/hydrahive/api/routes/streaming.py`, `core/src/hydrahive/streaming/`, `frontend/src/features/streaming/`.

### Zahnfee

**Status: Core, Administrator-Route**

Dental-Labor/Auftrags-Workflow, exponiert über eigenes Backend und Frontend-Feature.

**Quellen:** `core/src/hydrahive/zahnfee/`, `core/src/hydrahive/api/routes/zahnfee.py`, `frontend/src/features/zahnfee/`.

---

## 14. Administration, Settings und Lifecycle

**Status: Core; privilegierte Aktionen sind Administrator-only, wo API-seitig geschützt**

- User-Create/List/Update/Delete und API-Key-Management.
- Globale System-Overrides und Mail-Defaults.
- Provider-, Model-, OAuth-, MCP-, Credential- und Research-API-Konfiguration.
- Modul-, Theme-, Plugin- und Service-Extension-Management.
- System-Info, Application/Storage-Statistiken und Health-Checks.
- Update-Check, Update-Request, Restart-Request und Update-Logs.
- Voice-, Network-Bridge- und Samba-Setup-Requests/Logs.
- Backup und Restore.
- Server-zu-Server-Migration State/Start/Log.
- Dashboard und Analytics, inklusive pro Session Trace und Token/Cost-Daten.

**Quellen:** `core/src/hydrahive/api/routes/system*.py`, `users.py`, `backup.py`, `migration.py`, `analytics.py`, `dashboard.py`, `frontend/src/features/system/`, `frontend/src/features/cockpit/admin/`.

### API-Dokumentation

OpenAPI/Swagger ist per Default deaktiviert. Setzen:

```text
HH_ENABLE_DOCS=true
```

und Backend neu starten, um zu exponieren:

```text
/api/docs
/api/openapi.json
```

Die API ist absichtlich unter `/api` namespaced, inklusive Runtime-Modul-Routern unter `/api/modules/<module-id>`.

**Quelle:** `core/src/hydrahive/api/main.py`.

---

## 15. Installation und Deployment

**Status: Linux primär; macOS-Installer existiert mit reduzierter Host-Infrastruktur-Parität**

Der interaktive Linux-Installer kann provisionieren:

- Python 3.12, Node.js 20, ffmpeg, `uv/uvx`, GitHub-CLI und mmx-CLI;
- dedizierten Service-User und Filesystem-Permissions;
- Python-Umgebung und React-Build;
- `llmfit`;
- lokale ComfyUI-Media-Runtime auf kompatiblen NVIDIA-Systemen;
- WhatsApp-Bridge;
- Samba-Projekt-Shares;
- PostgreSQL-Data-Mining-Mirror;
- systemd-Application- und Helper-Timer;
- nginx-HTTPS-Kante;
- QEMU/KVM/libvirt-VM-Support;
- Incus-Container;
- Voice-Stack;
- HydraLink/AgentLink;
- Tailscale;
- initiale LLM-Provider-Einrichtung.

Alle Komponenten-Wahlen defaultieren im nicht-interaktiven Modus ohne gespeicherte Auswahl auf yes, außer wo explizit anders gesetzt. Vor der Installation auf einem Mehrzweck-Host [../installer/README.md](../installer/README.md) lesen.

**Quellen:** `installer/install.sh`, `installer/modules/`, `installer/install-mac.sh`, `installer/update.sh`, `installer/migrate.sh`.

---

## 16. Authentifizierung und Security-Kontrollen

Implementierte Kontrollen umfassen:

- bcrypt-Passwort-Hashing und Lazy-Migration von Legacy-SHA-256;
- ablaufende HS256-JWTs und explizite API-Keys;
- unveränderliche User-IDs im neueren Principal-basierten Autorisierungs-Pfad;
- Admin-Rollen-Checks und Last-Admin-Demotion-Schutz;
- Login-Lockout/Throttling-Support;
- AES-GCM-Verschlüsselung von Credential-Werten und restriktiver Credential-File-Mode;
- Projekt-Rollen und Projekt-Audit-Events;
- Tool-Allowlists und Confirmation-Gate;
- validierte Plugin-Manifeste, explizite Zuweisung und pro Plugin Load-Failure-Isolation (aber keine Plugin-Sandbox);
- nginx-TLS, Security-Header, Request-Limits und Compute-Node-mTLS im Standard-Linux-Deployment.

Wichtige Grenzen:

- mehrere Legacy-Route-Abhängigkeiten liefern weiterhin Username/Role statt unveränderliche Principals; jede Ressource-Route muss daher selbst auf ihren Ownership-Check geprüft werden;
- authentifizierter Data-Mining-Zugriff geht über Per-User-Isolation hinaus;
- Module laufen im Backend-Prozess und Plugins sind keine gehärtete Sandbox;
- Extension-Installation ist per Design privilegiert;
- das Default-Zertifikat ist selbstsigniert;
- Cloud-Provider und externe Integrationen erhalten die für die gewählte Operation benötigten Daten.

Siehe [../SECURITY.md](../SECURITY.md) und [SECURITY_THREAT_MODEL.md](SECURITY_THREAT_MODEL.md).

**Quellen:** `core/src/hydrahive/api/middleware/`, `core/src/hydrahive/credentials/`, `core/src/hydrahive/projects/`, `installer/modules/50-systemd.sh`, `60-nginx.sh`.

---

## 17. Bewusste Nicht-Aussagen

Dieses Inventar behauptet nicht:

- dass jedes Modul oder jede Extension per Default installiert ist;
- dass jedes in den Metadaten gelistete Provider-Modell aktuell für jeden Account verfügbar ist;
- dass Model/Provider-Preise oder Context-Metadaten den Live-Contract des Providers überschreiben;
- dass lokale Inferenz ohne kompatible Hardware und genug RAM/VRAM funktioniert;
- dass macOS Linux-Virtualisierungs-/Service-Parität bietet;
- dass der Vault bereits einen harten Timeout-Lock erzwingt;
- dass alle authentifizierten Analytics pro Nutzer isoliert sind;
- dass generierte Inhalte korrekt, sicher oder frei von Drittanbieter-Rechten sind;
- dass Medizin-, Finanz- oder Krypto-Module professionelle Beratung bieten;
- dass Modul/Plugin-Grenzen gegen bösartigen installierten Code schützen; beide laufen im Backend-Prozess;
- dass Beta-APIs und persistente Formate stabil sind.