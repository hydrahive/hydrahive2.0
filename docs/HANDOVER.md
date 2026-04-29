# HydraHive2 — Übergabe (Stand 2026-04-29 Nacht)

Konsolidierter Snapshot nach langem Build-Tag. Beim Wieder-Aufnehmen
diese Datei zuerst lesen, dann SPEC.md, dann konkret nach offenen Tasks fragen.

## TL;DR

Das System läuft End-to-End, ist auf einem Test-Server live (Frauchen-tauglich).
Heute konsolidiert: **Plugin-System komplett (MVP + Hub-UI)** mit privatem
Hub-Repo, **Self-Bootstrap-Loop verifiziert** (lokaler Agent baut eigene
Plugins, pusht sie und installiert sie selbst), **Service-Restart-Knopf**
in der UI, **Communication-Foundation** für Messenger/Mail (Channel-
Protocol, Session-Lookup, Master-Agent-Glue) — nächster Schritt:
WhatsApp als erster konkreter Channel auf dieser Foundation.

Vorher heute schon: i18n vollständig, komplette Userverwaltung mit
bcrypt + Admin-UI + Profile-Page, Sicherheits-Härtung (Failed-Login-
Lockout, nginx-Headers, Swagger UI gehärtet), Self-Update aus der UI
mit Live-Log-Modal, Backend-Error-Codes statt Strings, Memory-Suche.

## Was steht (alles getestet)

| Bereich | Stand |
|---|---|
| Backend Runner | Tool-Loop, Streaming, Loop-Detection, Heal-Helper für orphan tool_uses |
| DB-Layer | sessions/messages/tool_calls/state, append-only Compaction mit firstKeptEntryId; **Migration 002**: sessions.channel + external_user_id |
| 14 Core-Tools | shell, file_*, dir_list, web_search, http_request, read/write/search_memory, todo, ask_agent (Stub), send_mail |
| Agents | 3 Typen (master/project/specialist), CRUD, system_prompt-Datei, Pro-User-Isolation |
| Projekte | mit Members, gekoppeltem Project-Agent, Workspace, optional `git init` |
| Compaction | OpenClaw-Style append-only, Token-Budget-Walk, Plugin-Hooks, Skip-Reasons als Codes |
| Chat | SSE-Streaming, Markdown + GFM + Highlighter, Cancel via AbortController, Token-Anzeige |
| LLM-Provider | Anthropic (OAuth + Bearer), MiniMax, OpenAI/OpenRouter/Groq/Mistral/Gemini/NVIDIA NIM |
| MCP | 3 Transports (stdio/http/sse), 8 Quick-Add-Templates, Pool mit Health-Check |
| System-Page | HealthBar lokalisiert via name_code/detail_code, Stats, Pfade, Restart-Knopf |
| Userverwaltung | JWT + bcrypt mit Lazy-Migration, Failed-Login-Lockout, Admin-UI `/users`, Profile-Page `/profile` |
| Self-Update | Versions-Footer mit `↑`-Tag, Modal mit Live-Log, systemd-Path-Watcher, sudoless Trigger-File |
| **Service-Restart-Knopf** | `POST /api/system/restart` mit Trigger-File-Pattern (analog Self-Update). Production-Units `hydrahive2-restart.{path,service}` im Installer + update.sh-Self-Heal. Dev: Watch-Loop in dev-start.sh. Frontend `RestartModal` + `useRestart`-Hook mit /health-Polling. Knöpfe auf Plugins- und System-Page. |
| i18n | DE/EN, 14 Namespaces, alle Feature-Folder migriert, **Backend-Errors als Codes** statt deutsche Strings |
| Help-Drawer | pro Seite ?-Button, 7 Topics × 2 Sprachen |
| Installer | 6-Phasen-Setup + systemd + nginx mit Security-Headers (CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy). Update.sh macht Self-Heal für Update- *und* Restart-Units. |
| **Plugin-System** | MVP + **Hub-UI**: Loader/Manifest/Registry/Context/Tool-Bridge + Hub-Client (git clone/pull) + Installer (cp aus Cache). Frontend `/plugins`-Page (AdminGuard) mit Tabs Hub/Installiert, Install/Update/Uninstall, Restart-Hint. Hub-Repo `github.com/hydrahive/hydrahive2-plugins` (privat) gepusht. **Self-Bootstrap verifiziert**: lokaler Agent hat eigenständig `git-stats`-, `code-metrics`- und `file-search`-Plugins gebaut, gepusht, über die UI installiert und selbst genutzt. |
| **Communication-Foundation** | Neuer Core-Layer `core/src/hydrahive/communication/` für Messenger/Mail/etc. (fest im Core, nicht als Plugin — Messenger sind in SPEC verankert). Channel-Protocol + Registry + Session-Lookup pro `(agent, channel, external_id)` + Agent-Glue der eingehende Events durch den Master-Agent jagt + Router. Noch kein konkreter Channel — WhatsApp folgt mit Baileys. |

## Was offen ist

### Größere Initiativen (jeweils ein halber bis ganzer Build-Tag)

1. **WhatsApp als erster Channel** im Communication-Layer. Architektur entschieden: fest im Core unter `communication/whatsapp/` (NICHT als Plugin — Messenger sind Core-Layer in SPEC). Baileys (`@whiskeysockets/baileys` 7.x, von OpenClaw-Inspiration) als Node-Bridge auf 127.0.0.1:8767, Python-Wrapper. Eingehende Webhook → `communication.handle_incoming()` (Foundation steht). Frontend `/communication`-Page (oder Tab im Profile) mit WhatsApp-Karte (Connect-Button, QR-Anzeige beim Login, Status, Phone-Display nach Verbindung). Loop-Schutz: unsichtbarer `​`-Marker aus altem HydraHive übernehmen. Plus Bridge-Subprocess-Lifecycle (start/stop, systemd-Unit oder Plugin-Process-Management).
2. **AgentLink** als externer Service — `ask_agent` ist Stub. Multi-Agent-Workflows fehlen, Redis Pub/Sub.
3. **MMX-CLI / MiniMax Multimodal**: Audio/Video/Bild-Generierung als Plugin.
4. **`PluginContext.register_compaction_hook()`** — Mechanismus ist schon da (`compaction/hooks.py`), Plugin-API-Erweiterung fehlt damit Plugins eigene Compaction-Hooks anmelden können.
5. **Production-Hub-Auth** — auf 216 läuft der Service als `hydrahive`-User ohne GitHub-SSH-Key, Hub-Plugin-Install scheitert dort. Optionen: Public-Hub-Repo, Deploy-Key, oder Token-basierter HTTPS-Clone via Settings.

### Kleinere Themen

- **i18n Phase 4** — zentrale `/help`-Handbuch-Seite mit Sub-Sidebar, FAQ, Glossar.
- **MCP Phase 4** (optional) — Resources + Prompts.
- **HTTPS** — verschoben auf Tailscale-Integration (LAN-only Test-Server, kein realistisches Risiko).
- **Backup/Restore** — kein Mechanismus für DB + Configs.

### Aufräumen (5-15 Min)

- `.gitkeep`-Dateien (5+) entfernen
- `console/`-Ordner ist leer — vermutlich Skelett-Rest (`git rm -r console/`)
- Bestehende Agents haben das `search_memory`-Tool nicht in ihrer `tools`-Liste — manuell in der UI zuschalten oder via API.

### Wunsch-Features (Plugin-Material)

- `project_stats`-Tool für Projekt-Metriken
- Auto-Doku aus OpenAPI als statisch gerenderte HTML im Repo

### Chat-UI-Erweiterungen (Notizen, später)

- **Bild-Upload im Chat** — Drag&Drop oder Paperclip-Button. Anthropic + LiteLLM unterstützen Image-Content-Blocks (`{type: "image", source: {…}}`). Backend muss Multipart-Endpoint + base64-Encoding zum LLM-Call durchschleusen.
- **Datei-Upload im Chat** — Text-Files direkt als Inline-Content, Binär als Workspace-Datei mit auto-`file_read`-Hint. Größenlimit nötig.
- **Voice-Eingabe** — Browser-Mic-Aufnahme → Whisper/lokale STT → Text in Chat-Input. Lokale STT-Optionen: `whisper.cpp`, `faster-whisper`. Vorbild: alter HydraHive `whatsapp_transcribe.py`.
- **Voice-Ausgabe (TTS)** — Antwort des Agents als Audio. ElevenLabs (gut, externe API) oder Coqui/Piper (lokal). Pro-User-Config (Stimme, Sprache).
- Hängt mit der Communication-Architektur zusammen: WhatsApp-Sprachnachrichten brauchen STT, eine WhatsApp-Voice-Antwort braucht TTS — gleicher Code-Pfad wie für Chat-Voice.

## Bekannte Schwächen / Tech-Debt

- Token-Schätzung char-basiert (~3.5 chars/token) — Anthropic `count_tokens`-API wäre genauer
- MCP-Pool ohne Timeout-basierte Eviction nach Inaktivität
- Frontend-Bundle 1.2 MB (gzip 400 KB) — Vite warnt vor 500 KB-Schwelle
- Keine Index auf `messages(session_id, role)` — relevant ab ~10k Messages
- CORS-Default nur localhost — auf Produktiv via `HH_CORS_ORIGINS`
- Plugin-Code läuft im Backend-Prozess ohne OS-Sandbox — kommt mit Agent-OS-Isolation-Refactor (in SPEC)

## Test-Server-Deployment

- **Host**: `192.168.178.216` (Hostname `Hydrahive20-dev`, Ubuntu 24.04)
- **SSH-Alias**: `hh2-216`
- **Setup-User**: `chucky` mit Passwort, sudo-fähig
- **Service-User**: `hydrahive` (no-login)
- **Repo**: `/opt/hydrahive2/`, **Daten**: `/var/lib/hydrahive2/`, **Config**: `/etc/hydrahive2/`
- **Frontend**: http://192.168.178.216/
- **Service-Units**: `hydrahive2.service` (API) + `hydrahive2-update.path/.service` (Self-Update) + `hydrahive2-restart.path/.service` (Restart-Trigger, neu — kommt beim nächsten update.sh durch Self-Heal)
- **Update**: aus der UI klicken (Admin) ODER `cd /opt/hydrahive2/installer && sudo ./update.sh`

Initial-Admin-Passwort steht im Service-Log:
```bash
sudo journalctl -u hydrahive2 | grep -A 3 'Admin-User angelegt'
```

## Lokale Dev-Umgebung

- **Repo**: `/home/till/claudeneu/`
- **Hub-Repo (separat)**: `/home/till/hydrahive2-plugins/` → `github.com/hydrahive/hydrahive2-plugins` (privat)
- **Daten**: `~/.hh2-dev/data/`, **Config**: `~/.hh2-dev/config/`
- **Plugin-Cache**: `~/.hh2-dev/data/.plugin-cache/hub/`, **Installierte Plugins**: `~/.hh2-dev/data/plugins/<name>/`
- **Start**: `systemctl --user start hydrahive2-dev` (Autostart eingerichtet, ohne `linger`) ODER manuell `./dev-start.sh`
- **Backend**: `:8001`, **Frontend**: `:5173`
- **Login**: `admin` / `admin123` (Default für lokale Dev-Daten)
- **Swagger UI** lokal aktiv (HH_ENABLE_DOCS=1 wird vom dev-start.sh gesetzt)
- **Aktuell installierte Plugins (Dev)**: hello-world, git-stats, code-metrics, file-search — vom lokalen Agent gebaut

## Architektur-Highlights / Erkenntnisse

1. **Anthropic-OAuth-Tokens** (`sk-ant-oat01-…`) gehen NUR direkt über das Anthropic-SDK mit `auth_token=` + Identity-System-Block. LiteLLM bricht das (sendet Bearer). Same für MiniMax über deren Anthropic-Endpoint.
2. **Compaction-Modell**: append-only mit Pointer (OpenClaw-Style) statt destruktivem Replace. Robuster bei Bugs.
3. **Heal-Helper für orphan tool_uses** ist essentiell — `max_tokens`-Aborts hinterlassen sonst kaputte Histories die Anthropic mit 400 ablehnt.
4. **Loop-Detection (3× identisches Tool)** verhindert Token-Massaker bei Bug-Edge-Cases.
5. **Trigger-File-Pattern**: API-Prozess hat NoNewPrivileges=true, kann kein sudo. Statt sudo-Eintrag → API schreibt eine Datei in $HH_DATA_DIR, ein systemd-Path-Watcher (root) führt das Script aus. Wir nutzen das jetzt für **Self-Update** und **Service-Restart**. Saubere Sicherheits-Trennung.
6. **Backend-Error-Codes statt Strings**: alle HTTPException-Stellen liefern `{detail: {code, params}}`. Frontend übersetzt via `t('errors:<code>', params)`. API-Konsumenten (Bots aus SPEC) können den Code direkt parsen.
7. **bcrypt mit Lazy-Migration**: alte SHA256-Hashes werden beim nächsten erfolgreichen Login transparent rehashed.
8. **Plugin-System Self-Bootstrap-Loop**: der lokale Master-Agent kann via shell_exec Plugins schreiben → in den Hub-Repo committen + pushen → über die UI installieren → selbst die neuen Tools nutzen. Verifiziert mit 4 Plugins. Genau der autonome Workflow den die SPEC anvisiert.
9. **Communication-Architektur-Entscheidung**: Messenger sind **kein Plugin**, sondern Core-Layer. Begründung: in SPEC explizit als Komponente genannt, enge Kopplung zum Master-Agent (programmatischer Session-Trigger ohne UI-Klick), würde sonst eine generische Plugin-API für genau einen Use-Case erzwingen. Foundation steht in `core/src/hydrahive/communication/`, jeder konkrete Channel kommt als Submodul.
10. **WhatsApp-Tech-Wahl: Baileys statt whatsapp-web.js**. Alter HydraHive (octopos) nutzte Puppeteer + Chromium → 500 MB Disk, Browser-Crashes. OpenClaw nutzt Baileys (`@whiskeysockets/baileys`) → direktes WebSocket-Protokoll, ~50 MB, stabil. Wir übernehmen den Baileys-Weg.

## Empfohlene Reihenfolge nächster Build-Tag

1. **WhatsApp** als erster Channel im Communication-Layer (siehe Plan in „Was offen / Größere Initiativen #1"). Halber bis ganzer Tag.
2. **Aufräumen** (`.gitkeep`, leerer `console/`-Ordner) — 5 Min.
3. **Production-Hub-Auth** für 216 (Public-Repo oder Deploy-Key) bevor Plugin-Install dort geht.
4. **AgentLink** als externer Service damit Multi-Agent-Workflows real werden.

## Git-Stand

Branch `main` ist auf `origin/main`. Heute hinzugekommen seit Tagesbeginn (`5f4fbde` → aktueller HEAD `06ce477`):

```
06ce477 feat(communication): Foundation — Channel-Protocol, Session-Lookup, Agent-Glue
8e80fc8 feat(system): Service-Restart-Knopf — Trigger-File + Modal mit /health-Polling
c3f72df feat(plugins): Hub-UI Phase 2 — Marketplace mit Install/Update/Uninstall
b8a18a5 feat(plugins): Plugin-System MVP — Loader, Tool-Bridge, hello-world
5f4fbde docs: HANDOVER.md konsolidiert — Endstand 2026-04-29 Abend
```

Plus Hub-Repo `github.com/hydrahive/hydrahive2-plugins` (privat) hat 3 Commits — initial + git-stats + code-metrics + file-search (Letzteres vom lokalen Agent, nicht von uns).

Working-Tree wird nach Commit dieser HANDOVER.md clean.
