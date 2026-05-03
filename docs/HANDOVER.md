# HydraHive2 — Übergabe (Stand 2026-05-03 abend)

Konsolidierter Snapshot. Beim Wieder-Aufnehmen diese Datei zuerst,
dann SPEC.md, dann konkret nach offenen Tasks fragen.

---

## Was heute erledigt wurde

### Discord-Adapter (Issue #35) — fertig
- `core/src/hydrahive/communication/discord/` — adapter.py, config.py, filter.py
- `api/routes/communication_discord.py` + `communication_discord_routes.py`
- Frontend: `DiscordCard.tsx`, `DiscordFilterPanel.tsx`, `CommunicationPage.tsx` +discord
- discord.py direkt im asyncio-Loop, kein Subprocess

### PostgreSQL Datamining-Mirror — fertig + deployed
- `core/src/hydrahive/db/mirror.py` — fire-and-forget Mirror aller Chat-Events nach PostgreSQL
- Schema: `sessions` + `events` Tabellen, blockweise Zerlegung mit Chunk-IDs
- `installer/modules/48-postgres.sh` — PostgreSQL + pgvector Installer (idempotent)
- `installer/update.sh` — Self-Heal für Postgres-Setup; **Bug gefixt**: `tr | head` Broken-Pipe
  unter `set -euo pipefail` → jetzt `openssl rand -hex 16`. Alle Sub-Skripte mit `|| log` abgesichert.
- `api/routes/datamining.py` — `GET /api/datamining/events?limit=N`
- `frontend/src/features/datamining/DataminingPage.tsx` — Live-Feed (Zeit | User | Agent | Typ | Tool | Snippet)
- `mcp-servers/datamining/server.py` — FastMCP, 3 Tools: search / get_session / list_sessions
- **218 läuft**, DSN gesetzt, Events loggen, Agent-Name sichtbar

### Embedding-Modell-Auswahl — fertig
- `core/src/hydrahive/llm/embed.py` — Lookup-Table bekannter Modelle (OpenAI/nvidia/mistral/gemini/cohere)
  mit Dimension + LiteLLM-Modell-String; nur Provider mit API-Key werden angezeigt
- `GET /api/llm/embed-models` — gibt verfügbare Modelle zurück
- `embed_model` Feld in `LlmConfig` gespeichert
- `mirror.py` überarbeitet: DDL ohne hardcoded `vector(4096)`, `_ensure_embed_col()` legt
  Spalte dynamisch an und passt sie bei Modellwechsel an (DROP + ADD)
- Nach jedem Event-Write: fire-and-forget `_embed_event()`-Task
- LLM-Seite: Dropdown "Embedding-Modell" zeigt nur passende Modelle mit Dimension `(Nd)`

---

## Aktuell offen / nächste Schritte

### Datamining — Semantic Search (nächste Phase)
- Embedding läuft, Vektoren werden geschrieben
- **Fehlt noch**: Such-UI auf der Datamining-Seite (Suchfeld + Ergebnisse)
- MCP-Server (`mcp-servers/datamining/server.py`) hat noch kein semantisches Search-Tool —
  nur ILIKE. Wenn Embeddings befüllt: `search` Tool um `query_vector` erweitern

### Backlog (keine Reihenfolge)
- Discord / Telegram / Matrix-Adapter Telegram+Matrix noch offen
- Branching/Tree-View in Chat
- Bundle-Splitting (#95) — chunks > 500 KB Warnung bleibt
- DB-Indizes (#96)
- AgentLink HTTPS Mixed-Content (#90)
- Buddy-Spielereien (Tamagotchi-Animation, Online-Radio, Achievements)
- MCP-Datamining-Server deployen + als Tool einbinden

---

## Installer / Server

### 218 (chucky@hh2-218 / 192.168.178.218, Passwort lummerland123)
- LXC-Container auf TrueNAS, kein /dev/kvm
- Repo: `/opt/hydrahive2`, Service-User: `hydrahive`
- **Stand**: aktuell (2026-05-03 abend)
- Update-Trigger: `sudo touch /var/lib/hydrahive2/.update_request`
- PostgreSQL läuft, DSN in `/etc/hydrahive2/pg_mirror.dsn` + systemd Drop-in

### Installer-Reihenfolge (module/)
```
00-deps  10-user  20-paths  30-python  40-frontend
47-samba  48-postgres  50-systemd  55-voice
60-nginx  65-vms  70-containers  75-agentlink  80-tailscale
```

---

## Wichtige Lektionen aus dieser Session

- **`tr | head -c 32` unter `set -euo pipefail`** = Broken Pipe → Script-Abbruch.
  Immer `openssl rand -hex 16` für Passwort-Generierung.
- **Sub-Skripte in update.sh** brauchen `|| log "... failed — weiter"` sonst bricht
  `set -euo pipefail` das gesamte Script ab bevor spätere Self-Heal-Blöcke greifen.
- **Embedding-Dimension nicht hardcoden** — verschiedene Modelle haben verschiedene Dims.
  Lookup-Table im Code, Spalte dynamisch per ALTER TABLE anlegen.
- **layer violation db→llm**: `mirror.py` importiert `llm.embed` und `llm._config`.
  Das ist bewusst akzeptiert — Embedding ist DB-nahe Post-Processing.

---

## Code-Änderungen seit letzter Übergabe (neue/geänderte Dateien)

```
core/src/hydrahive/communication/discord/__init__.py   NEU
core/src/hydrahive/communication/discord/adapter.py    NEU
core/src/hydrahive/communication/discord/config.py     NEU
core/src/hydrahive/communication/discord/filter.py     NEU
core/src/hydrahive/api/routes/communication_discord.py NEU
core/src/hydrahive/api/routes/communication_discord_routes.py NEU
core/src/hydrahive/api/lifespan.py                     +Discord-Startup
core/src/hydrahive/api/main.py                         +discord_router
core/src/hydrahive/db/mirror.py                        NEU (komplett)
core/src/hydrahive/db/messages.py                      +mirror.schedule_message
core/src/hydrahive/db/sessions.py                      +mirror.schedule_session
core/src/hydrahive/api/routes/datamining.py            NEU
core/src/hydrahive/api/main.py                         +datamining_router
core/src/hydrahive/settings/settings.py                +pg_mirror_dsn, +discord_*
core/src/hydrahive/llm/embed.py                        NEU
core/src/hydrahive/api/routes/llm.py                   +embed_model, +embed-models endpoint
core/pyproject.toml                                    +asyncpg>=0.29
installer/modules/48-postgres.sh                       NEU
installer/install.sh                                   +Phase 7b postgres
installer/update.sh                                    +postgres self-heal, alle || log fixes
mcp-servers/datamining/server.py                       NEU
mcp-servers/datamining/pyproject.toml                  NEU
frontend/src/features/communication/DiscordCard.tsx    NEU
frontend/src/features/communication/DiscordFilterPanel.tsx NEU
frontend/src/features/communication/CommunicationPage.tsx  +DiscordCard
frontend/src/features/datamining/DataminingPage.tsx    NEU
frontend/src/features/llm/LlmPage.tsx                  +embed_model Dropdown
frontend/src/features/llm/api.ts                       +EmbedModel, embed_model
frontend/src/i18n/index.ts                             +datamining namespace
frontend/src/i18n/locales/{de,en}/communication.json   +discord.*
frontend/src/i18n/locales/{de,en}/datamining.json      NEU
frontend/src/i18n/locales/{de,en}/llm.json             +embed_model*
```
