# HydraHive

> 🇬🇧 [English version](README.md)

**Self-hosted AI-Orchestrierung, Projekt-Workspaces, dauerhaftes Gedächtnis, Automatisierung und Medienproduktion — in einem erweiterbaren Web-Cockpit.**

<p align="center">
  <a href="https://github.com/hydrahive/hydrahive2.0/actions/workflows/pytest.yml"><img src="https://img.shields.io/github/actions/workflow/status/hydrahive/hydrahive2.0/pytest.yml?branch=main&label=CI" alt="CI"></a>
  <a href="https://github.com/hydrahive/hydrahive2.0/releases"><img src="https://img.shields.io/github/v/release/hydrahive/hydrahive2.0?include_prereleases&label=release" alt="Release"></a>
  <img src="https://img.shields.io/badge/status-beta-orange" alt="Beta">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/FastAPI-0.111%E2%80%930.136-009688" alt="FastAPI 0.111–0.136">
  <img src="https://img.shields.io/badge/React-19-61dafb" alt="React 19">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"></a>
</p>

> [!IMPORTANT]
> HydraHive befindet sich in **Beta**. APIs und persistente Konfigurationsformate können sich noch ändern. Vor Upgrades Daten- und Konfigurationsverzeichnisse sichern.

Diese README ist ein kompakter Produkt-Überblick. Die code-gestützte Feature-Liste, Abhängigkeiten, Grenzen und Quellenverweise stehen in **[docs/FEATURES.md](docs/FEATURES.md)** (englisch) bzw. **[docs/FEATURES.de.md](docs/FEATURES.de.md)**.

---

## Was HydraHive ist

HydraHive ist eine selbstgehostete Steuerebene für KI-Agenten. Sie kombiniert:

- ein Python/FastAPI-Orchestrierungs-Backend;
- eine React-Webanwendung für Chat, Konfiguration und Betrieb;
- persönliche, Projekt- und Spezialisten-Agenten;
- isolierte Agent-/Projekt-Workspaces mit Dateien und Git;
- Skills, native Tools, MCP-Server und lokale Tool-Plugins;
- dauerhaftes Gedächtnis, Context-Compaction und optionale sessionsübergreifende Data-Mining-Suche;
- Medien-Generierung und projektbezogene Post-Produktion;
- optionale Komponenten für Kommunikation, Automatisierung, Virtualisierung und Compute-Nodes;
- einen offiziellen Hub installierbarer Endnutzer-Module.

„Self-hosted" gilt für die HydraHive-Steuerebene und ihre gespeicherten Daten. Anfragen an konfigurierte Cloud-Modelle, Suchdienste, MCP-Server, Messenger oder andere Integrationen verlassen den Host gemäß den Bedingungen des jeweiligen Dienstes.

---

## Highlights

### Agenten und belastbares Chat

- Ein persönlicher **Buddy**, eigenständige Agenten, Projekt-Agenten und Projekt-Spezialisten.
- Streaming-Chat mit Anhängen, Tool-Karten, Bestätigungs-Gates, Abbruch und Reconnect zu serverseitigen Runs.
- Primär- und Fallback-Modelle, pro Session Override für Modell/Reasoning sowie Token-/Cache-/Kosten-Telemetrie.
- Iterations- und Tool-Loop-Limits, kontextbewusste Compaction und fortsetzbare pausierte Runs.
- Wiederverwendbare globale, Projekt- und Spezialisten-**Skills**.
- Agent-zu-Agent-Delegation über **HydraLink/AgentLink**.

### Tools, Gedächtnis und Recherche

- Native Tools für Dateien, Shell, Web-Suche/Browser, authentifiziertes HTTP, Mail, Medien, Projekte, Code-Graph und mehr.
- Weitere Tools aus konfigurierten MCP-Servern, installierten Plugins und Modulen.
- Persistente Memory-Notizen, Beobachtungen, Hintergrund-Konsolidierung und proaktiver Recall.
- Optionaler PostgreSQL-Mirror für Data Mining mit semantischer/Full-Text-Suche, Timeline, Event-Graph und Importen.
- Deep-Research-Modul für mehrstufige, quellenbasierte Berichte.

### Projekte und Engineering-Workflows

- Projekt-Owner/Member mit projektspezifischen Rollen, Audit-Events und isolierten Workspaces.
- Datei-Browser/Editor, Uploads, SMB-Mounts, Samba-Shares und Git-/Gitea-Operationen.
- Projekt-Chat, -Agenten, -Spezialisten und persistentes Tasks-Board (Modul).
- Lokal gebauter Code-Graph mit Query, Explanation, Shortest-Path, Impact und Refresh.
- VM-/Container-Zuweisung plus Session-/Statistik-Ansichten im Project Cockpit.

### Modelle und Medien

- Provider-Konfiguration für Anthropic, OpenAI, OpenAI Codex OAuth, OpenRouter, Groq, Mistral, Gemini, NVIDIA NIM, MiniMax und Ollama.
- Live-/statische Modell-Kataloge, Capability-/Kontext-Metadaten, Purpose-Klassifikation und Preis-Schätzungen.
- Ollama-Modell-Lifecycle plus optionale `llmfit`-Hardware-Empfehlungen.
- Bild-Analyse/-Generierung, Musik, Sprache, Transkription und asynchrone Video-Generierung.
- Optionale lokale ComfyUI-Workflows für SDXL und Wan auf NVIDIA/CUDA + Docker-Hosts.
- Media Cockpit, Prompt-Archiv, Timeline-/Schnitt-Workflow und installierbare Atelier-/Video-Editor-Module.

### Automatisierung, Kommunikation und Infrastruktur

- Butler-Trigger/Condition/Action-Flows, Trockenläufe und Projekt-Webhooks.
- Optional WhatsApp, Discord, Matrix-Teamchat, IMAP/SMTP-Mail und Voice-Komponenten.
- Compute-Node-Enrollment, mTLS-Kanal, Health/Resources und Remote-Jobs.
- QEMU/libvirt-VMs, Incus-Container, Browser-VNC und Container-Terminal.
- Federation/Workstation-Registry und optionaler Tailscale-Client-Bootstrap.
- Backup/Restore, Self-Update/Restart-Helfer und Server-zu-Server-Migration.

### Erweiterbarkeit

- Runtime-**Module** für UI, API-Routen, DB-Migrationen, Tools, Butler-Typen und Hintergrund-Jobs.
- Reine UI-**Themes** mit generierter Registry und Layout/CSS-Beiträgen.
- Agent-Tool-**Plugins**, die aus validierten Manifesten geladen und über die normale Tool-Schnittstelle exponiert werden.
- Privilegierte Service-**Extensions** für Drittanbieter-Software wie Gitea, Ollama, SearXNG, Plex oder Vaultwarden.

Der offizielle Modul-Hub enthält aktuell **18 Manifeste: 17 Endnutzer-Module plus ein Entwickler-Beispiel**. Der Service-Extension-Katalog umfasst **32 Manifeste**. Berechnung und vollständige Listen sind in [docs/FEATURES.md](docs/FEATURES.md) (bzw. [docs/FEATURES.de.md](docs/FEATURES.de.md)) dokumentiert.

---

## Hauptarbeitsbereiche

| Cockpit | Zweck |
|---|---|
| **Project Cockpit** | Projekt-Chat, Agenten, Git, Dateien, Tasks, Mitglieder, Mounts, Server und Code-Graph |
| **Buddy Cockpit** | persönlicher Assistent und von Modulen beigetragene Widgets |
| **Media Cockpit** | Idee, Prompts, Drehbuch, Charaktere/Stil/Assets und Timeline/Export |
| **Vault Cockpit** | Offline-first Launchpad für sensible Datensätze, Krypto, Notizen, Credentials, Gedächtnis und Data Mining |
| **Admin Cockpit** | User, Provider, MCP, Credentials, Module, Themes, Plugins, Extensions, VMs, Container, Nodes/Jobs und Systemaktionen |

Der aktuelle Vault ist ein Launchpad mit weicher Schutzwirkung; seine UI markiert hartes Timeout-Locking und konsolidiertes Dokumenten-/OCR-Handling explizit als künftige Arbeit. Er startet beim Öffnen keine KI-Analysen im Hintergrund.

---

## Module versus Extensions

| Konzept | Zweck | Pfad/Vertrag |
|---|---|---|
| **Module** | Endnutzer-Feature mit optionalem Backend, Migrationen, Tools, Jobs und Frontend | installiert unter `HH_DATA_DIR/modules/<id>` aus [`hydrahive2-modules`](https://github.com/hydrahive/hydrahive2-modules) |
| **Theme** | Frontend-Layout, CSS und visuelle Variablen | kopiert nach `frontend/src/themes` und beim Build eingebunden |
| **Plugin** | Agent-Tool-Paket | installiert unter `HH_DATA_DIR/plugins/<name>` mit Plugin-Manifest |
| **Extension** | Drittanbieter-Service/System-Paket | `extensions/manifests/*.json` plus Install/Uninstall/Compose-Assets |

Installation/Update eines Moduls kopiert Backend-/Runtime-Dateien, kopiert das Frontend in den Core-Source-Tree, baut das Frontend neu und fordert einen Backend-Restart an. Deinstallation entfernt Modul-Dateien, lässt Modul-Datenbank-Daten aber bewusst stehen.

Extensions sind anders: ihre Installer können privilegierte Shell- oder Docker-Operationen ausführen. Jede Extension ist als reviewed administrator-trusted code zu behandeln.

---

## Schnellstart

### Linux

Der primäre Installer zielt auf einen dedizierten apt-basierten Ubuntu/Debian-Host. Das Repository hat explizites Upgrade-Handling für Ubuntu 24.04 und 26.04. Auf anderen Releases zuerst Python 3.12 und Host-Komponenten-Kompatibilität prüfen.

```bash
git clone https://github.com/hydrahive/hydrahive2.0.git
cd hydrahive2.0
sudo bash installer/install.sh
```

Der interaktive Wizard kann installieren:

- das FastAPI-Backend, den React-Build, den Service-Account und die systemd-Unit;
- nginx mit selbstsigniertem HTTPS-Zertifikat;
- HydraLink/AgentLink;
- PostgreSQL-Data-Mining;
- WhatsApp, Samba, Voice und Tailscale;
- QEMU/libvirt-VMs und Incus-Container;
- die NVIDIA-Local-Media-Runtime, wenn kompatible Hardware erkannt wird.

Die meisten optionalen Komponenten defaultieren auf **yes**, solange keine Auswahl gespeichert ist. Vor nicht-interaktivem Lauf auf einem Mehrzweckserver [installer/README.md](installer/README.md) lesen.

Bei Abschluss gibt der Installer aus:

```text
URL:       https://<server-ip>
Benutzer:  admin
Passwort:  <generierter Wert>
```

Die Zertifikats-Warnung ist erwartet, bis das generierte Zertifikat vertraut oder ersetzt ist. Das Backend selbst bindet per Default auf Loopback.

### macOS

Es existiert ein experimenteller nativer Installer:

```bash
bash installer/install-mac.sh
```

Linux-only systemd, libvirt, Incus und nginx-Provisioning haben auf macOS keine automatische Parität.

---

## Entwicklung

### Voraussetzungen

- Python 3.12+
- Node.js 20+
- Git

```bash
git clone https://github.com/hydrahive/hydrahive2.0.git
cd hydrahive2.0

python3.12 -m venv .venv
source .venv/bin/activate
pip install -e core

cd frontend
npm ci
cd ..

./dev-start.sh
```

`dev-start.sh` liefert Entwicklungs-Secrets, startet das Backend auf `127.0.0.1:8001` und startet Vite.

### Verifikation

```bash
cd core
python -m pytest
python -m ruff check src tests

cd ../frontend
npx tsc --noEmit
npm run lint
npm run build
```

CI führt Backend-pytest + Ruff, ein nicht-blockierendes Dependency-Audit, Frontend-TypeScript und ESLint aus. Siehe [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Konfiguration

Runtime-Settings verwenden das Präfix `HH_`. Der Linux-Installer schreibt optionale Environment-Overrides nach `/etc/hydrahive2/env` und legt Secrets/PKI unter `/etc/hydrahive2` an.

| Variable | Code-Default | Zweck |
|---|---:|---|
| `HH_BASE_DIR` | `/opt/hydrahive2` | Quell-/Build-Pfad der Anwendung |
| `HH_DATA_DIR` | `/var/lib/hydrahive2` | Sessions-Datenbank, Agenten, Workspaces, Module, Plugins und Mediendaten |
| `HH_CONFIG_DIR` | `/etc/hydrahive2` | User, Provider-/MCP-Konfiguration, Secrets und Compute-PKI |
| `HH_SECRET_KEY` | **erforderlich** | JWT-Signatur und Credential-Encryption-Wurzel-Secret; Installer generiert es |
| `HH_JWT_EXPIRE_MINUTES` | `1440` | JWT-Lebensdauer |
| `HH_HOST` | `127.0.0.1` | Backend-Bind-Adresse |
| `HH_PORT` | `8765` | Code-Default; Linux-Installer konfiguriert `8001` hinter nginx |
| `HH_CORS_ORIGINS` | localhost-Vite-Origins | kommaseparierte Browser-Origins |
| `HH_AGENTLINK_URL` | `http://127.0.0.1:9000` | lokaler/remote AgentLink-REST-Endpoint; explizit leer deaktiviert ihn |
| `HH_AGENTLINK_TOKEN` | leer | optionaler AgentLink-Bearer-Token |
| `HH_PG_MIRROR_DSN` | leer | optionaler PostgreSQL-Data-Mining-Mirror |
| `HH_MODULE_HUB_GIT_URL` | offizieller Modul-Hub | primäre Modul-Quelle |
| `HH_MODULE_HUB_GIT_URLS` | leer | zusätzliche kommaseparierte Modul-Hubs |
| `HH_ENABLE_DOCS` | false | exponiert Swagger unter `/api/docs` und OpenAPI unter `/api/openapi.json` |
| `HH_UPDATE_CHECK_ENABLED` | true | fragt das Git-Remote nach Update-Status |

Provider, Mail, Matrix, Webmin, Samba, VM- und Compute-Features haben weitere Settings. Secrets lieber über die UI-Credential-/Provider-Screens oder `/etc/hydrahive2/env` pflegen, statt sie zu committen.

---

## Sicherheitsmodell

Verifizierte Implementierungs-Eigenschaften:

- neue Passwörter nutzen bcrypt; Legacy-SHA-256-Hashes werden nach erfolgreichem Login migriert;
- API-Zugriff erfolgt über ablaufende JWTs oder explizite API-Keys;
- neuere Principal-basierte Ressourcen lösen unveränderliche User-IDs und aktuelle Rollen auf;
- Projekt-Routen erzwingen Projekt-Mitgliedschaft/Rollen und protokollieren ausgewählte Audit-Events;
- Credential-Werte sind at rest mit AES-GCM verschlüsselt und mit restriktiven Datei-Modi gespeichert;
- Agenten erhalten explizite Tool-/MCP-/Plugin-Selektionen und können Bestätigung verlangen;
- die Standard-Linux-Kante nutzt HTTPS, Security-Header, Request-Limits und Compute-Node-mTLS;
- Plugin-Manifeste werden validiert und Plugins werden Agenten explizit zugewiesen; Plugin-Python-Code läuft im Backend-Prozess und muss vertrauenswürdig sein.

Wichtige Grenzen:

- einige Legacy-APIs nutzen weiterhin Username/Role-Abhängigkeiten und müssen Ownership selbst durchsetzen;
- authentifizierte Data-Mining-Queries gehen über strenge Per-User-Isolation hinaus;
- Module und Plugins sind vertrauenswürdiger ausführbarer Code, keine Security-Sandboxen;
- Extension-Installation ist per Design privilegiert;
- das Standard-TLS-Zertifikat ist selbstsigniert;
- Cloud-Provider und externe Integrationen erhalten die für eine gewählte Operation nötigen Daten.

Lies [SECURITY.md](SECURITY.md) und [docs/SECURITY_THREAT_MODEL.md](docs/SECURITY_THREAT_MODEL.md). Den Entwicklungsserver nicht direkt öffentlich ans Internet hängen.

---

## Repository-Layout

```text
hydrahive2.0/
├── core/                    # FastAPI-Backend, Runner, Tools und Persistenz
├── frontend/                # React + TypeScript + Vite-Anwendung
├── modules/                 # gebündelte Tasks/Patientenakte-Quellen und Beispiel-Template
├── extensions/              # Service-Manifeste und Install-/Compose-Assets
├── node-agent/              # Remote-Compute-Node-Service
├── installer/               # Install-, Update- und Migrations-Skripte
├── mcp-servers/             # gebündelte MCP-Server-Helfer/Beispiele
├── docs/                    # Produkt-, Architektur-, Sicherheits- und Runbook-Doku
├── SPEC.md                  # bindende Produkt-Baseline
└── CONTRIBUTING.md          # Repository-Regeln und Checks
```

---

## Dokumentation

- [Feature-Inventar](docs/FEATURES.md) | [deutsch](docs/FEATURES.de.md) — implementierte Fähigkeiten, Modul-/Extension-Kataloge und Grenzen
- [Release Notes](docs/RELEASE_NOTES.md) — aktuelle unveröffentlichte Änderungen und Verweis auf veröffentlichte Releases
- [Benutzerhandbuch](docs/USER_GUIDE.md) — tägliche Workflows
- [Architektur](docs/ARCHITECTURE.md) — Komponenten, Datenfluss und Vertrauensgrenzen
- [Cockpits](docs/COCKPITS.md) — aktuelle Navigation und Cockpit-Modell
- [Doku-Index](docs/README.md)
- [Installer-Anleitung](installer/README.md)
- [Frontend-Contributor-Guide](frontend/README.md)
- [Node-Agent-Referenz](node-agent/README.md)
- [Modul-Hub](https://github.com/hydrahive/hydrahive2-modules)
- [Beitragen](CONTRIBUTING.md)
- [Internationalisierung der Doku](docs/I18N.md) | [deutsch](docs/I18N.de.md) — wie Spiegel-Dateien gepflegt werden

---

## Lizenz und Beitrag

HydraHive steht unter der [MIT-Lizenz](LICENSE).

Bug-Reports und Pull-Requests sind willkommen. Änderungen fokussiert halten, [CONTRIBUTING.md](CONTRIBUTING.md) folgen und vor dem PR die passenden Verifikations-Befehle ausführen.
