# HydraHive2 — Übergabe zum 2026-04-29

Snapshot des Standes nach 2 intensiven Build-Tagen. Beim nächsten Wieder-Aufnehmen
diese Datei zuerst lesen, dann SPEC.md.

## TL;DR

Das System läuft Ende-zu-Ende:
- Backend (FastAPI + SQLite) mit Tool-Loop, Streaming, Compaction, MCP-Integration
- Frontend (React + Vite) mit Chat, Agents, Projekte, MCP-Server-Verwaltung,
  System-Page, mehrsprachige Hilfe
- Installer für Ubuntu/Debian mit systemd-Service + nginx
- Live-Test auf 192.168.178.216 erfolgreich (`http://192.168.178.216/`)

## Was steht (13 Tasks fertig)

| # | Feature | Stand |
|---|---|---|
| Runner | Tool-Loop, Streaming, Loop-Detection, Heal-Helper | ✅ getestet |
| DB-Layer | sessions/messages/tools/state mit append-only | ✅ getestet |
| 13 Core-Tools | shell/file_*/dir/web/http/memory/todo/ask/mail | ✅ getestet |
| Agents | CRUD, system_prompt-Datei, Workspaces auto | ✅ Frontend + Backend |
| Projekte | mit Members, Project-Agent, Workspace, optional git init | ✅ Frontend + Backend |
| Compaction | OpenClaw-Style append-only mit firstKeptEntryId | ✅ getestet |
| Chat-API + Frontend | SSE-Streaming, Cancel, Token, Modell, Markdown | ✅ getestet |
| LLM-Provider | Anthropic-OAuth + MiniMax via Anthropic-SDK | ✅ getestet |
| MCP | 3 Transports (stdio/http/sse) + 8 Quick-Add-Templates | ✅ getestet |
| System-Page | Health-Bar, Stats, Auto-Refresh | ✅ getestet |
| i18n Foundation | react-i18next, DE/EN, Sprach-Switcher | ✅ Sidebar |
| Help-Drawer | pro Seite ?-Button mit Markdown-Hilfe | ✅ 7 Topics × 2 Sprachen |
| Installer | 6-Phasen-Setup + nginx + systemd | ✅ live getestet |

## Was offen ist

### High Priority
- **i18n Phase 2** — alle UI-Strings auf `t('key')` migrieren. Locale-Files sind da,
  Komponenten noch hardcoded außer Layout. ~3-4h Fließarbeit.
- **i18n Phase 4** — zentrale `/help`-Handbuch-Seite mit Sub-Sidebar
  (Konzepte / Bedienung / FAQ / Glossar)

### Medium Priority
- **AgentLink** — externer Service für `ask_agent`. Aktuell Stub. Multi-Agent-
  Workflows aus SPEC fehlen.
- **MMX-CLI / MiniMax Multimodal** — Audio/Video/Bild-Generierung. Notiz im
  Memory dazu existiert.
- **Plugin-System** — Hooks sind in Compaction vorbereitet, Loader fehlt.
  README/Doku im Repo (`docs/` ist leer).

### Low Priority
- **MCP Phase 4** — Resources + Prompts (optional, kein konkreter Bedarf)
- **`console/` Verzeichnis im Repo** — leeres Skelett, vermutlich für
  Backup/Admin-Tools laut SPEC. Kein Code.
- **Frontend-Bundle 1.2 MB** — Vite-Warning, Code-Splitting wäre nice
- **MCP-Pool ohne Timeout-Eviction** — Health-Check greift nur beim nächsten
  Use, nicht periodisch

## Bekannte Schwächen / Tech-Debt

- Token-Schätzung char-basiert (~3.5 chars/token), könnte `count_tokens`-API nutzen
- `messages.list_for_llm()` ist SQL-optimiert, aber kein Index auf
  `(session_id, role)` — bei 10k+ Messages später interessant
- CORS-Default nur lokal — auf Produktiv-Server muss `HH_CORS_ORIGINS` gesetzt
- Keine Backup/Restore-Funktionen

## Test-Server-Deployment

- **Host**: `192.168.178.216` (Hostname `Hydrahive20-dev`, Ubuntu 24.04)
- **SSH-Alias**: `hh2-216` (in `~/.ssh/config`)
- **Setup-User**: `chucky` mit Passwort, sudo-fähig
- **Service-User**: `hydrahive` (no-login)
- **Repo**: `/opt/hydrahive2/`
- **Daten**: `/var/lib/hydrahive2/`
- **Config**: `/etc/hydrahive2/`
- **Frontend**: http://192.168.178.216/
- **Update**: `cd /opt/hydrahive2/installer && sudo ./update.sh`

Admin-Initial-Passwort steht im journal:
```bash
sudo journalctl -u hydrahive2 | grep -A 3 'Admin-User angelegt'
```

## Lokale Dev-Umgebung

- **Repo**: `/home/till/claudeneu/`
- **Daten**: `~/.hh2-dev/data/` (überlebt Reboot, anders als initial `/tmp/`)
- **Config**: `~/.hh2-dev/config/`
- **Start**: `./dev-start.sh` (Backend auf :8001, Frontend auf :5173)
- **Login**: `admin` / `admin123` (für lokale Dev-Daten)

## Wichtige Erkenntnisse aus den letzten 2 Tagen

1. **Anthropic-OAuth-Tokens** (`sk-ant-oat01-…`) gehen NUR direkt über das
   Anthropic-SDK mit `auth_token=` und Identity-System-Block. LiteLLM
   konvertiert fälschlich zu Bearer und Anthropic gibt 429 ohne
   sinnvolle Meldung. Same für MiniMax über deren Anthropic-Endpoint.
2. **Compaction-Modell**: append-only mit Pointer (OpenClaw-Style) ist
   deutlich robuster als destruktives Replace (altes HydraHive-Style).
3. **Heal-Helper für orphan tool_uses** ist essentiell — `max_tokens`-Aborts
   hinterlassen sonst kaputte Histories die Anthropic mit 400 ablehnt.
4. **Loop-Detection (3× identisches Tool)** verhindert Token-Massaker bei
   Bug-Edge-Cases (z.B. wenn `max_tokens` zu klein für Code-Gen ist).
5. **Tetris-Test** hat die Token/Tool-Limits eindrucksvoll demonstriert —
   Default `max_tokens=8192` reicht für längere Code-Generation, 4096 nicht.

## Nächster Build-Tag — empfohlene Reihenfolge

1. **Lokal verifizieren** dass alles noch läuft (`./dev-start.sh`)
2. **i18n Phase 2** angreifen (UI-Migration komplett, eine Page nach der anderen)
3. **i18n Phase 4** (Handbuch-Seite) gleich danach — passt thematisch
4. Erst danach an AgentLink oder Plugin-System

## Git-Stand

Branch `main` ist auf `origin/main`. Letzte Commits (von neu nach alt):

```
fix(installer): npm-Konflikt + i18n-locales + State-Init
feat(installer): vollständiger Setup für Ubuntu/Debian
feat(i18n): react-i18next + Help-Drawer mit Markdown
chore: Quick-Wins aus Self-Review
feat(mcp+llm): MCP 3 Transports + Quick-Add + MiniMax + Modell-Dropdown
feat(runner+compaction+chat+system): Herzstück
feat(agents+projects): 3-Ebenen-Architektur
feat(tools): 13 Core-Tools mit Path-Schutz
feat(db): Session-DB mit append-only Storage
chore: Dev-Setup
```

Working-Tree clean nach Commit dieser HANDOVER.md.
