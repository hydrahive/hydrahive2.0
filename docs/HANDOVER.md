# HydraHive2 — Übergabe (Stand 2026-04-29 Spätabend)

Konsolidierter Snapshot nach intensivem Build-Tag. Beim Wieder-Aufnehmen
diese Datei zuerst lesen, dann SPEC.md, dann konkret nach offenen Tasks fragen.

## TL;DR

Das System läuft End-to-End, ist live auf einem Test-Server, und Frauchen
kann es jetzt selbst testen. Heute kamen dazu: i18n vollständig migriert,
komplette Userverwaltung mit bcrypt + Admin-UI + Profile-Page,
Sicherheits-Härtung (Failed-Login-Lockout, nginx-Headers, Swagger UI gehärtet),
Self-Update aus der UI mit Live-Log-Modal, Backend-Error-Codes statt
deutscher Strings, Memory-Suche, README. **Spätabend: Plugin-System-MVP** —
externer Hub-Repo, Loader mit Crash-Isolation, hello-world-Demo per Chat
verifiziert.

## Was steht (alles getestet + auf 216 deployed)

| Bereich | Stand |
|---|---|
| Backend Runner | Tool-Loop, Streaming, Loop-Detection, Heal-Helper für orphan tool_uses |
| DB-Layer | sessions/messages/tool_calls/state, append-only Compaction mit firstKeptEntryId |
| 14 Core-Tools | shell, file_*, dir_list, web_search, http_request, read/write/**search**_memory, todo, ask_agent (Stub), send_mail |
| Agents | 3 Typen (master/project/specialist), CRUD, system_prompt-Datei, Pro-User-Isolation |
| Projekte | mit Members, gekoppeltem Project-Agent, Workspace, optional `git init` |
| Compaction | OpenClaw-Style append-only, Token-Budget-Walk, Plugin-Hooks, **Skip-Reasons als Codes** |
| Chat | SSE-Streaming, Markdown + GFM + Highlighter, Cancel via AbortController, Token-Anzeige |
| LLM-Provider | Anthropic (OAuth + Bearer), MiniMax, OpenAI/OpenRouter/Groq/Mistral/Gemini/**NVIDIA NIM** |
| MCP | 3 Transports (stdio/http/sse), 8 Quick-Add-Templates, Pool mit Health-Check |
| System-Page | HealthBar (jetzt voll lokalisiert via name_code/detail_code), Stats, Pfade |
| **Userverwaltung** | JWT + bcrypt mit Lazy-Migration, Failed-Login-Lockout, Admin-UI `/users`, Profile-Page `/profile` |
| **Self-Update** | Versions-Footer mit `↑`-Tag, Modal mit Live-Log, systemd-Path-Watcher, sudoless Trigger-File |
| **i18n** | DE/EN, 14 Namespaces, alle Feature-Folder migriert, **Backend-Errors als Codes statt deutsche Strings** |
| Help-Drawer | pro Seite ?-Button, 7 Topics × 2 Sprachen |
| Installer | 6-Phasen-Setup + systemd + nginx mit Security-Headers (CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy) |
| **Plugin-System** | MVP + **Hub-UI**: Loader/Manifest/Registry/Context/Tool-Bridge + Hub-Client (git clone/pull) + Installer (cp aus Cache). Frontend `/plugins`-Page (AdminGuard) mit Tabs Hub/Installiert, Install/Update/Uninstall, Restart-Hint. Hub-Repo `github.com/hydrahive/hydrahive2-plugins` (privat) gepusht. **Self-Bootstrap verifiziert**: lokaler Agent hat eigenständig `git-stats`-, `code-metrics`- und `file-search`-Plugins gebaut, in den Hub gepusht und über die UI installiert. |
| **Service-Restart-Knopf** | `POST /api/system/restart` mit Trigger-File-Pattern (analog Self-Update). Production-Units `hydrahive2-restart.{path,service}` im Installer + update.sh-Self-Heal. Dev: Watch-Loop in dev-start.sh. Frontend `RestartModal` + `useRestart`-Hook mit /health-Polling. Knöpfe auf Plugins- und System-Page. |
| **Communication-Foundation** | Neuer Core-Layer `core/src/hydrahive/communication/` für Messenger/Mail/etc. (fest im Core, nicht als Plugin — Messenger sind in SPEC verankert). Channel-Protocol + Registry + Session-Lookup pro `(agent, channel, external_id)` + Agent-Glue der eingehende Events durch den Master-Agent jagt + Router. DB-Migration 002 erweitert sessions um `channel` + `external_user_id`. Noch kein konkreter Channel — WhatsApp folgt mit Baileys. |

## Was offen ist

### Größere Initiativen (jeweils ein halber bis ganzer Build-Tag)

1. **WhatsApp als erster Channel** im Communication-Layer. Architektur entschieden: fest im Core unter `communication/whatsapp/` (NICHT als Plugin — Messenger sind Core-Layer in SPEC). Baileys (`@whiskeysockets/baileys`) als Node-Bridge auf 127.0.0.1:8767, Python-Wrapper. Eingehende Webhook → `communication.handle_incoming()` (Foundation steht). Frontend `/communication` mit WhatsApp-Karte (Connect/QR/Status). Loop-Schutz: unsichtbarer `​`-Marker aus altem HydraHive übernehmen.
2. **AgentLink** als externer Service — `ask_agent` ist Stub. Multi-Agent-Workflows fehlen, Redis Pub/Sub.
3. **MMX-CLI / MiniMax Multimodal**: Audio/Video/Bild-Generierung als Plugin.
4. **`PluginContext.register_compaction_hook()`** — Mechanismus ist schon da (`compaction/hooks.py`), Plugin-API-Erweiterung fehlt damit Plugins eigene Compaction-Hooks anmelden können.
5. **Production-Hub-Auth** — auf 216 läuft der Service als `hydrahive`-User ohne GitHub-SSH-Key. Optionen: Public-Hub-Repo, Deploy-Key, oder Token-basierter HTTPS-Clone.

### Kleinere Themen

- **i18n Phase 4** — zentrale `/help`-Handbuch-Seite mit Sub-Sidebar, FAQ, Glossar.
- **MCP Phase 4** (optional) — Resources + Prompts.
- **HTTPS** — verschoben auf Tailscale-Integration (LAN-only Test-Server, kein realistisches Risiko).
- **Backup/Restore** — kein Mechanismus für DB + Configs.

### Aufräumen (5-15 Min)

- `.gitkeep`-Dateien (5+) entfernen
- `console/`-Ordner ist leer — vermutlich Skelett-Rest, kann gelöscht werden (`git rm -r console/`)
- Bestehende Agents haben das neue `search_memory`-Tool nicht in ihrer `tools`-Liste — manuell in der UI zuschalten oder via API.

### Wunsch-Features (Plugin-Material)

- `project_stats`-Tool für Projekt-Metriken
- Auto-Doku aus OpenAPI als statisch gerenderte HTML im Repo

## Bekannte Schwächen / Tech-Debt

- Token-Schätzung char-basiert (~3.5 chars/token) — Anthropic `count_tokens`-API wäre genauer
- MCP-Pool ohne Timeout-basierte Eviction nach Inaktivität
- Frontend-Bundle 1.2 MB (gzip 400 KB) — Vite warnt vor 500 KB-Schwelle
- Keine Index auf `messages(session_id, role)` — relevant ab ~10k Messages
- CORS-Default nur localhost — auf Produktiv via `HH_CORS_ORIGINS`

## Test-Server-Deployment

- **Host**: `192.168.178.216` (Hostname `Hydrahive20-dev`, Ubuntu 24.04)
- **SSH-Alias**: `hh2-216`
- **Setup-User**: `chucky` mit Passwort, sudo-fähig
- **Service-User**: `hydrahive` (no-login)
- **Repo**: `/opt/hydrahive2/`, **Daten**: `/var/lib/hydrahive2/`, **Config**: `/etc/hydrahive2/`
- **Frontend**: http://192.168.178.216/
- **Service-Units**: `hydrahive2.service` (API), `hydrahive2-update.path` (Watcher), `hydrahive2-update.service` (Self-Update-Runner)
- **Update**: aus der UI klicken (Admin) ODER `cd /opt/hydrahive2/installer && sudo ./update.sh`

Initial-Admin-Passwort steht im Service-Log:
```bash
sudo journalctl -u hydrahive2 | grep -A 3 'Admin-User angelegt'
```

## Lokale Dev-Umgebung

- **Repo**: `/home/till/claudeneu/`
- **Daten**: `~/.hh2-dev/data/`, **Config**: `~/.hh2-dev/config/`
- **Start**: `./dev-start.sh` (Backend `:8001`, Frontend `:5173`)
- **Login**: `admin` / `admin123` (Default für lokale Dev-Daten)
- **Swagger UI** lokal aktiv (HH_ENABLE_DOCS=1 wird vom dev-start.sh gesetzt)

## Architektur-Highlights / Erkenntnisse

1. **Anthropic-OAuth-Tokens** (`sk-ant-oat01-…`) gehen NUR direkt über das Anthropic-SDK mit `auth_token=` + Identity-System-Block. LiteLLM bricht das (sendet Bearer). Same für MiniMax über deren Anthropic-Endpoint.
2. **Compaction-Modell**: append-only mit Pointer (OpenClaw-Style) statt destruktivem Replace. Robuster bei Bugs.
3. **Heal-Helper für orphan tool_uses** ist essentiell — `max_tokens`-Aborts hinterlassen sonst kaputte Histories die Anthropic mit 400 ablehnt.
4. **Loop-Detection (3× identisches Tool)** verhindert Token-Massaker bei Bug-Edge-Cases.
5. **Self-Update-Architektur**: API-Prozess hat NoNewPrivileges=true, kann kein sudo. Statt sudo-Eintrag → Trigger-File-Pattern: API schreibt nur eine Datei in $HH_DATA_DIR, ein systemd-Path-Watcher (root) triggert update.sh. Sauberere Sicherheits-Trennung.
6. **Backend-Error-Codes statt Strings**: alle 64 HTTPException-Stellen liefern `{detail: {code, params}}`. Frontend übersetzt via `t('errors:<code>', params)`. API-Konsumenten (Bots aus SPEC) können den Code direkt parsen.
7. **bcrypt mit Lazy-Migration**: alte SHA256-Hashes werden beim nächsten erfolgreichen Login transparent rehashed. Kein Forced-Reset, kein Schmerz für bestehende User.
8. **HealthCheck-Lokalisierung**: Backend liefert `name_code`/`detail_code` statt deutscher Strings. Locale-Keys waren bereits in `system.json` vorhanden — Frontend hat HealthBar nur auf das Mapping-Pattern umgestellt.

## Empfohlene Reihenfolge nächster Build-Tag

1. **WhatsApp-Bridge** als erstes echtes Nutz-Plugin im Hub-Repo, dann MMX/Multimodal.
2. **Aufräumen** (`.gitkeep`, leerer `console/`-Ordner) — 5 Min.
3. **Production-Hub-Auth** für 216 (Public-Repo oder Deploy-Key) bevor das auch dort nutzbar ist.
4. **AgentLink** als externer Service damit Multi-Agent-Workflows real werden.

## Git-Stand

Branch `main` ist auf `origin/main`. Heute hinzugekommen (`19ef47a` → aktueller HEAD):

```
3794297 feat(tools): search_memory — Volltextsuche über eigene Memory-Notizen
77f2629 docs: README.md — Setup, Architektur, Konfig, Sicherheit
23a4298 chore: .claude/ ignorieren (Claude-Code-Harness-Tempfiles)
9580f6d feat(errors): Backend liefert Codes statt deutscher Strings
14400b6 fix(update): ls-remote statt fetch — funktioniert mit ProtectSystem=strict
112be41 fix(llm): MiniMax-ThinkingBlock-Crash + NVIDIA-Provider + Swagger-UI gehärtet
a549685 feat(security): Failed-Login-Lockout + nginx Security-Headers
77552e5 fix(installer): update.sh richtet Self-Update-Units idempotent ein
4c298ff feat(system): Self-Update via Knopf in der Sidebar
f64a5ca feat(update): Modal mit Live-Log statt confirm()-Dialog
3152fa9 fix(system): _GIT_COMMIT periodisch aktualisieren
8c89f5b feat(users): Admin-UI + Profile-Page + Auth-Härtung + Versions-Footer
c1b559b fix(i18n): ungenutztes i18n-Destructuring in SessionList entfernen
2b91897 feat(i18n): Phase 2 — alle Feature-Komponenten auf t() migriert
```

Working-Tree wird nach Commit dieser HANDOVER.md clean.
