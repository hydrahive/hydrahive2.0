# HydraHive2 — Übergabe (Stand 2026-04-29 Nacht, WhatsApp + Filter)

Konsolidierter Snapshot. Beim Wieder-Aufnehmen diese Datei zuerst,
dann SPEC.md, dann konkret nach offenen Tasks fragen.

## TL;DR

Heute durchgezogen: **WhatsApp-Channel ist E2E live** — Baileys-Bridge
als Node-Subprocess, Python-Adapter, Frontend `/communication`-Page mit
Connect/QR-Scan/Status/Filter-Panel, **Pro-User-Filter-Config** (Owner,
Whitelist, Blacklist, Keyword, Private/Group-Toggles) inklusive
LID→Telefonnummer-Resolve. Eingehende Nachrichten landen automatisch
als Sessions in der Chat-History (Foundation arbeitet sauber). Nächster
großer Build-Tag ist der **Butler** als kanal-übergreifender Flow-
Builder (im alten HydraHive ein 2200-Zeilen Feature mit ReactFlow).

**Korrektur an alter Roadmap**: AgentLink existiert bereits extern als
Service — es geht nur noch um den Hookup unseres `ask_agent`-Stubs an
die existierende API.

## Was steht (alles getestet)

| Bereich | Stand |
|---|---|
| Backend Runner | Tool-Loop, Streaming, Loop-Detection, Heal-Helper für orphan tool_uses |
| DB-Layer | sessions/messages/tool_calls/state, append-only Compaction; Migration 002 für Channel-Sessions |
| 14 Core-Tools | shell, file_*, dir_list, web_search, http_request, read/write/search_memory, todo, ask_agent (Stub), send_mail |
| Agents | 3 Typen (master/project/specialist), CRUD, system_prompt-Datei, Pro-User-Isolation |
| Projekte | mit Members, gekoppeltem Project-Agent, Workspace, optional `git init` |
| Compaction | append-only, Token-Budget-Walk, Plugin-Hooks, Skip-Reasons als Codes |
| Chat | SSE-Streaming, Markdown + GFM + Highlighter, Cancel via AbortController, Token-Anzeige |
| LLM-Provider | Anthropic (OAuth + Bearer), MiniMax, OpenAI/OpenRouter/Groq/Mistral/Gemini/NVIDIA NIM |
| MCP | 3 Transports (stdio/http/sse), 8 Quick-Add-Templates, Pool mit Health-Check |
| System-Page | HealthBar lokalisiert via name_code/detail_code, Stats, Pfade, Restart-Knopf |
| Userverwaltung | JWT + bcrypt mit Lazy-Migration, Failed-Login-Lockout, Admin-UI `/users`, Profile `/profile` |
| Self-Update | Versions-Footer mit `↑`-Tag, Modal mit Live-Log, systemd-Path-Watcher, Trigger-File |
| Service-Restart-Knopf | Trigger-File-Pattern + Modal mit /health-Polling |
| i18n | DE/EN, **15 Namespaces** (mit `communication`), alle Feature-Folder migriert, Backend-Errors als Codes |
| Help-Drawer | pro Seite ?-Button, 7 Topics × 2 Sprachen |
| Installer | 6-Phasen-Setup + systemd + nginx mit Security-Headers |
| Plugin-System | MVP + Hub-UI, Self-Bootstrap-Loop verifiziert, Hub-Repo `github.com/hydrahive/hydrahive2-plugins` |
| Communication-Foundation | Channel-Protocol + Registry + Session-Lookup + Master-Agent-Glue + Router |
| **WhatsApp-Channel (NEU)** | Baileys-Node-Bridge (HTTP loopback 8767, multi-file Auth in `$HH_DATA_DIR/whatsapp/<user>/auth/`, Stream-515-Auto-Reconnect, Loop-Marker, LID-Resolve via `senderPn`/`participantPn`). Python-Adapter implementiert Channel-Protocol. Frontend `/communication` mit `WhatsAppCard` (Status, QR, Connect/Disconnect) und `WhatsAppFilterPanel` (Owner/Whitelist/Blacklist/Keyword/Private+Group, sichtbar wenn connected). Filter-Reihenfolge im Backend: Owner → Blacklist → Group/Private → Whitelist → Keyword. Eingehende Nachrichten persistieren als Sessions pro `(master, channel, external_user_id)`. |

## Was offen ist

### Größere Initiativen (jeweils ein halber bis ganzer Build-Tag)

1. **Butler** als kanal-übergreifender Flow-Builder. Im alten HydraHive
   (`/home/till/octopos/`) war das ein 2200-Zeilen Feature mit ReactFlow:
   `ButlerPage.tsx` (1402 Z., Trigger/Condition/Action-Palette, Drag&Drop,
   Node-Inspector), `butler_executor.py` (496 Z., Backend-Engine die Flows
   ausführt), `router_butler.py` (197 Z., CRUD-API), `butler_rule.py`
   (143 Z., nodes/edges-Datenmodell). Pro-User-Flows in
   `$HH_CONFIG_DIR/butler/<owner>/<flow_id>.json`. Trigger u.a.
   `message_received`, `webhook_received`, `email_received`,
   `git_event_received`, `heartbeat_fired`, `discord_event_received`.
   Conditions: `time_window`, `day_of_week`, `contact_known`,
   `message_contains`, `keyword`, `git_branch_is`/`author_is`.
   Actions: `agent_reply`, `agent_reply_guided`, `reply_fixed`, `queue`,
   `ignore`, `forward`, `http_post`, `send_email`, `git_create_issue`,
   `discord_post`. **Nicht in SPEC.md** — braucht SPEC-Erweiterung.
   Vom User explizit als „wichtig" priorisiert.
2. **AgentLink-Hookup** (extern bereits verfügbar als Service, User-Korrektur 2026-04-29).
   Bei uns: `ask_agent`-Tool ist Stub, anbinden an existierende API. Dann
   funktionieren Multi-Agent-Workflows, Redis Pub/Sub-Konsum.
3. **WhatsApp Production-Deployment** (216): Installer-Module für Node 20 +
   `npm install` im Bridge-Verzeichnis. Bridge startet sonst nicht
   (Adapter logged Warning, Channel registriert sich nicht — Frontend zeigt
   „Bridge nicht verfügbar").
4. **MMX-CLI / MiniMax Multimodal**: Audio/Video/Bild-Generierung als Plugin.
5. **`PluginContext.register_compaction_hook()`** — Mechanismus ist da
   (`compaction/hooks.py`), Plugin-API-Erweiterung fehlt damit Plugins
   eigene Compaction-Hooks anmelden können.
6. **Production-Hub-Auth** — auf 216 hat User `hydrahive` keinen
   GitHub-SSH-Key, Hub-Plugin-Install scheitert. Optionen: Public-Hub-Repo,
   Deploy-Key, oder Token-basierter HTTPS-Clone via Settings.
7. **Web → WhatsApp-Send**: Eingehende WhatsApp-Sessions tauchen als
   Chat-Sessions auf (cool!), aber Web-Antworten gehen NICHT zurück über
   WhatsApp. Wäre ein Channel-Send-Hook im normalen Chat-Flow.

### Kleinere Themen

- **i18n Phase 4** — zentrale `/help`-Handbuch-Seite mit Sub-Sidebar, FAQ, Glossar.
- **MCP Phase 4** (optional) — Resources + Prompts.
- **HTTPS** — verschoben auf Tailscale-Integration (LAN-only Test-Server).
- **Backup/Restore** — kein Mechanismus für DB + Configs.

### Aufräumen (5-15 Min)

- `.gitkeep`-Dateien (5+) entfernen
- `console/`-Ordner ist leer — vermutlich Skelett-Rest (`git rm -r console/`)
- Bestehende Agents haben das `search_memory`-Tool nicht in ihrer `tools`-Liste

### Wunsch-Features (Plugin-Material)

- `project_stats`-Tool für Projekt-Metriken
- Auto-Doku aus OpenAPI als statisch gerenderte HTML im Repo

### Chat-UI-Erweiterungen (Notizen, später)

- **Bild-Upload im Chat** — Drag&Drop oder Paperclip-Button. Anthropic + LiteLLM unterstützen Image-Content-Blocks. Backend muss Multipart-Endpoint + base64-Encoding zum LLM-Call durchschleusen.
- **Datei-Upload im Chat** — Text-Files direkt als Inline-Content, Binär als Workspace-Datei mit auto-`file_read`-Hint. Größenlimit nötig.
- **Voice-Eingabe** — Browser-Mic-Aufnahme → Whisper/lokale STT → Text in Chat-Input.
- **Voice-Ausgabe (TTS)** — Antwort des Agents als Audio. Bevorzugt MiniMax TTS (haben wir eh als LLM-Provider, mmx-CLI kann Audio).
- Hängt mit der Communication-Architektur zusammen: WhatsApp-Sprachnachrichten brauchen STT, eine WhatsApp-Voice-Antwort braucht TTS — gleicher Code-Pfad wie für Chat-Voice.

## Bekannte Schwächen / Tech-Debt

- Token-Schätzung char-basiert (~3.5 chars/token) — Anthropic `count_tokens`-API wäre genauer
- MCP-Pool ohne Timeout-basierte Eviction nach Inaktivität
- Frontend-Bundle 1.2 MB (gzip 400 KB) — Vite warnt vor 500 KB-Schwelle
- CORS-Default nur localhost — auf Produktiv via `HH_CORS_ORIGINS`
- Plugin-Code läuft im Backend-Prozess ohne OS-Sandbox — kommt mit Agent-OS-Isolation-Refactor
- WhatsApp-Bridge: kein Auto-Reconnect bei Netzwerk-Hickups (nur bei Stream-515 nach Pairing). User klickt Connect erneut, Auth bleibt erhalten.
- WhatsApp-Filter ohne `/me/chats`-API: Owner-Bypass-Test braucht zweites Telefon (oder WhatsApp Web mit zweitem Account)

## Test-Server-Deployment

- **Host**: `192.168.178.216` (Hostname `Hydrahive20-dev`, Ubuntu 24.04)
- **SSH-Alias**: `hh2-216`
- **Setup-User**: `chucky` mit Passwort, sudo-fähig
- **Service-User**: `hydrahive` (no-login)
- **Repo**: `/opt/hydrahive2/`, **Daten**: `/var/lib/hydrahive2/`, **Config**: `/etc/hydrahive2/`
- **Frontend**: http://192.168.178.216/
- **Service-Units**: `hydrahive2.service` + `hydrahive2-update.path/.service` + `hydrahive2-restart.path/.service`
- **Update**: aus der UI klicken (Admin) ODER `cd /opt/hydrahive2/installer && sudo ./update.sh`
- **WhatsApp auf 216 noch nicht funktionsfähig**: Node + `npm install` im Bridge-Verzeichnis fehlen → Installer-Erweiterung nötig (siehe Roadmap #3)

## Lokale Dev-Umgebung

- **Repo**: `/home/till/claudeneu/`
- **Hub-Repo (separat)**: `/home/till/hydrahive2-plugins/` → `github.com/hydrahive/hydrahive2-plugins` (privat)
- **Daten**: `~/.hh2-dev/data/`, **Config**: `~/.hh2-dev/config/`
- **Plugin-Cache**: `~/.hh2-dev/data/.plugin-cache/hub/`, **Plugins**: `~/.hh2-dev/data/plugins/<name>/`
- **WhatsApp-Auth**: `~/.hh2-dev/data/whatsapp/<user>/auth/` (multi-file)
- **WhatsApp-Filter-Config**: `~/.hh2-dev/config/whatsapp/<username>.json`
- **WhatsApp-Bridge-Secret**: `~/.hh2-dev/config/whatsapp_bridge.secret`
- **Start**: `systemctl --user start hydrahive2-dev` (Autostart eingerichtet) ODER `./dev-start.sh`
- **Backend**: `:8001`, **Frontend**: `:5173`, **WhatsApp-Bridge**: `:8767` (loopback)
- **Login**: `admin` / `admin123` (Default)
- **Aktuell installierte Plugins (Dev)**: hello-world, git-stats, code-metrics, file-search

## Architektur-Highlights / Erkenntnisse

1. **Anthropic-OAuth-Tokens** gehen NUR direkt über das Anthropic-SDK mit `auth_token=` + Identity-System-Block.
2. **Compaction-Modell**: append-only mit Pointer (OpenClaw-Style) statt destruktivem Replace.
3. **Heal-Helper für orphan tool_uses** ist essentiell — `max_tokens`-Aborts hinterlassen sonst kaputte Histories die Anthropic mit 400 ablehnt.
4. **Loop-Detection (3× identisches Tool)** verhindert Token-Massaker.
5. **Trigger-File-Pattern**: API-Prozess hat `NoNewPrivileges=true`, kann kein sudo. API schreibt Datei in `$HH_DATA_DIR`, ein systemd-Path-Watcher (root) führt das Script aus. Genutzt für **Self-Update** und **Service-Restart**.
6. **Backend-Error-Codes statt Strings**: alle HTTPException-Stellen liefern `{detail: {code, params}}`. Frontend übersetzt, API-Konsumenten parsen direkt.
7. **bcrypt mit Lazy-Migration**: alte SHA256-Hashes werden beim nächsten erfolgreichen Login transparent rehashed.
8. **Plugin-System Self-Bootstrap-Loop**: lokaler Master-Agent kann via shell_exec Plugins schreiben → in Hub committen+pushen → über UI installieren → selbst nutzen. Verifiziert mit 4 Plugins.
9. **Communication-Architektur**: Messenger sind **kein Plugin**, sondern Core-Layer. Begründung: in SPEC explizit als Komponente genannt, enge Kopplung zum Master-Agent (programmatischer Session-Trigger ohne UI-Klick).
10. **WhatsApp-Tech-Wahl: Baileys statt whatsapp-web.js**. Alter HydraHive (octopos) nutzte Puppeteer + Chromium → 500 MB Disk, Browser-Crashes. Wir nutzen Baileys (`@whiskeysockets/baileys` 6.7) → direktes WebSocket-Protokoll, ~50 MB, stabil. Hinweis im alten HANDOVER „OpenClaw nutzt Baileys" stimmt nicht — `.openclaw` enthält keinen WhatsApp-Code; wir sind die ersten Baileys-Konsumenten.
11. **WhatsApp LID-Resolve**: Baileys liefert manche Sender als `xxx@lid` (interne ID statt Nummer). Wir mappen via `m.key.senderPn` (1:1) bzw. `participantPn` (Group) zur echten Telefonnummer — sonst matchen Owner-/Whitelist-Filter nicht und Sessions hätten LID-Titel.
12. **WhatsApp Stream-515 nach Pairing**: Baileys-Standard-Verhalten — nach erstem QR-Scan kommt sofort `stream:error code 515` als „restart required". Die Bridge reconnected automatisch mit den frischen Creds (kein neuer QR), Auto-Reconnect-Logik in `sock.js`.
13. **Filter-Reihenfolge** im WhatsApp-Filter ist bewusst: Owner schlägt vor allem (auch Blacklist), dann Blacklist, dann Group/Private-Toggles, dann Whitelist, dann Keyword. Owner-Bypass garantiert dass der Besitzer nie ausgesperrt werden kann.

## Empfohlene Reihenfolge nächster Build-Tag

1. **WhatsApp-Production-Deployment auf 216** (Installer Node + npm install) — kurz, sonst läuft das Feature dort nicht.
2. **Butler** als kanal-übergreifender Flow-Builder — großes Feature, vom User priorisiert. SPEC-Erweiterung zuerst.
3. **AgentLink-Hookup** — kleiner als gedacht, weil AgentLink schon existiert.
4. **Aufräumen** (`.gitkeep`, leerer `console/`-Ordner) — 5 Min.

## Git-Stand

Branch `main` ist auf `origin/main`. Heute hinzugekommen seit Tagesbeginn:

```
06ce477 feat(communication): Foundation — Channel-Protocol, Session-Lookup, Agent-Glue
8e80fc8 feat(system): Service-Restart-Knopf — Trigger-File + Modal mit /health-Polling
c3f72df feat(plugins): Hub-UI Phase 2 — Marketplace mit Install/Update/Uninstall
b8a18a5 feat(plugins): Plugin-System MVP — Loader, Tool-Bridge, hello-world
```

Heute Nacht (zum Commit anstehend): WhatsApp-Bridge + Adapter, WhatsApp-Frontend, Filter-Config, kleine Fixes (TextDelta, LID-Resolve, Stream-515-Auto-Reconnect, dev-start.sh HH_PORT/HH_INTERNAL_URL).
