# Team-Chat Schicht 1 — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (empfohlen) oder superpowers:executing-plans, um diesen Plan Task für Task umzusetzen. Steps nutzen Checkbox-Syntax (`- [ ]`).

**Goal:** Intra-Instanz-Team-Chat: die User *einer* HydraHive-Instanz chatten in freien Räumen miteinander, lokale Agenten sind zuschaltbar und antworten bei Anrede.

**Architecture:** Matrix als Backend-Substrat (Homeserver tuwunel via Extension, opt-out). Ein Core-Feature-Modul `core/src/hydrahive/teamchat/` spricht als einziges Matrix (matrix-nio), das Frontend redet nur mit der HH-API. Feature konditional — inaktiv ohne erreichbaren Homeserver. Föderation aus (Schicht 2).

**Tech Stack:** Python 3.12 / FastAPI / matrix-nio / SQLite · React+TS+Vite · tuwunel (conduit-Fork) · matrix-nio AsyncClient · SSE (wie Live-Sync).

**Design-Doc:** `docs/superpowers/specs/2026-06-03-teamchat-schicht1-design.md` (ab5528dd).

---

## Etappen (je „eines komplett fertig, dann das nächste", Regel #2)

| Etappe | Inhalt | Till testet |
|---|---|---|
| **1 — Fundament** | matrix-nio-Dep, Settings-Mixin, tuwunel-Extension, Migration 025 + `db/teamchat.py` | Extension installiert sich auf Testserver, Health-Check grün; Migration läuft; Settings lesbar |
| **2 — Bridge-Kern** | `client.py` (Login/Sync), `identity.py` (Provisioning + Token-Crypto), `loop_guard.py` + Tests | `pytest` grün; Backend loggt sich am lokalen tuwunel ein, provisioniert einen User |
| **3 — Räume/Nachrichten/Echtzeit** | `rooms.py`, `messages.py`, `broadcaster.py`, `routes/teamchat.py` (ohne Agent), Sync-Loop im lifespan, `main.py` | Zwei Browser → Mensch↔Mensch-Chat in Echtzeit + History, ohne Agent |
| **4 — Agent + Frontend** | `agent_bridge.py`, Agent-Endpoints, `features/teamchat/` + Verkabelung | Volles Feature: Agent antwortet bei Anrede, native UI, cross-device |

**Dieser Plan detailliert Etappe 1 voll.** Etappen 2–4 stehen als Task-Listen mit
Vorlagen-Pointern; jede wird vor Baubeginn voll als TDD-Tasks ausgeschrieben (verhindert
Drift durch Vorab-Erfindung von API-Shapes, die sich beim Bauen noch ändern).

---

## File-Structure (gesamt Schicht 1)

```
core/src/hydrahive/teamchat/
  __init__.py        # Public-API-Fassade
  client.py          # [E2] matrix-nio AsyncClient: Login, Sync-Loop
  identity.py        # [E2] HH-User ↔ Matrix-Account, Token verschlüsselt
  loop_guard.py      # [E2] Circuit-Breaker (Port aus HH1)
  rooms.py           # [E3] Raum anlegen/einladen/Mitglieder/Liste
  messages.py        # [E3] senden/empfangen/History
  broadcaster.py     # [E3] RoomBroadcaster (SSE-Fanout pro room_id)
  agent_bridge.py    # [E4] @mention erkennen, Runner triggern, Antwort posten
  sync_loop.py       # [E3] lifespan-Hintergrund-Task (sync → broadcast)
core/src/hydrahive/db/teamchat.py            # [E1] DB-Layer
core/src/hydrahive/db/migrations/025_teamchat.sql  # [E1]
core/src/hydrahive/settings/_teamchat.py     # [E1] Settings-Mixin
core/src/hydrahive/api/routes/teamchat.py    # [E3/E4] Endpoints
extensions/manifests/tuwunel.json            # [E1]
extensions/install/tuwunel.sh                # [E1]
extensions/uninstall/tuwunel.sh              # [E1]
frontend/src/features/teamchat/{api,types,useTeamchat,TeamchatPage,RoomList,ChatView,MemberPanel,AgentAttachButton}.{ts,tsx}  # [E4]
```

---

## Vorlagen-Katalog (verbindliche Muster, verifiziert)

**HH2 (`/home/till/claudeneu`):**
- DB-CRUD-Muster: `core/src/hydrahive/db/federation.py:11-110` (`with db() as conn`, `_row()`-Helper).
- Migration-Runner: `core/src/hydrahive/db/migrations.py` (alle `*.sql` automatisch, `schema_version`-Tabelle). Höchste = 024 → **unsere = 025**.
- Settings-Mixin + live-`@property`: `settings/_mail.py:24` (`env_or_override`), Komposition in `settings/settings.py:30-46`.
- Crypto: `credentials/_crypto.py:56-69` — `encrypt(plaintext, settings.data_dir)` / `decrypt(value, settings.data_dir)`, Prefix `"enc:v1:"`.
- API-Routen: `routes/federation.py:16,49-82` — `APIRouter(prefix=..., tags=[...])`, `require_auth`/`require_admin` aus `api/middleware/auth.py` → `tuple[str,str]`=(username,role). Registrierung `api/main.py` `include_router`.
- SSE-Broadcaster: `api/_session_broadcast.py:1-67` (`subscribe`/`broadcast`/`unsubscribe`, threading.Lock + `dict[id→set[Queue]]`). SSE-Endpoint: `routes/sessions_messages.py:59-93` (`StreamingResponse`, `text/event-stream`, keepalive 20s).
- Agent-Run aus Event: `communication/_agent_glue.py:119-178` — `_run_agent(agent_id, event, prefix=...)`, `_session_lookup.find_or_create(...)`, `runner_run(session.id, user_text, extra_system=...)`, `IncomingEvent`, Sender-Rahmung, `redaction.scrub`.
- Agent-Config: `agents.config.get(agent_id)` → dict (`tools`, `owner`, `status`, `tool_config`).
- lifespan-Task: `api/lifespan.py:177-233` (`asyncio.Event()` + `create_task`, shutdown `stop.set()`+`wait_for`). Loop-Vorlage: `communication/mail/watcher.py:64-90`.
- Extension: `extensions/manifests/headscale.json` (Schema), `extensions/install/ollama.sh` (Script-Stil, `[OK]`/`[INFO]`-Sentinels, `set -euo pipefail`).
- Frontend-Feature: `features/federation/{api,types}.ts`, `features/chat/useChat.ts`; `api`-Wrapper `shared/api-client.ts` (`request<T>`, Token aus `useAuthStore`). Verkabelung: `App.tsx`, `shared/nav-config.ts`, `shared/colors.ts`, `i18n/index.ts`. SSE-Konsum: `features/extensions/api.ts:16-59` (fetch+ReadableStream). Build-Check: `npm run build` (`tsc -b && vite build`) — **nicht** `tsc --noEmit`.

**HH1 (`/home/till/octopos`, Portierungs-Vorlage):**
- Client/Login/Sync/Token: `core/src/hydrahive_core/matrix_agent.py:78-122,219-246,366-387`.
- Eingehende Nachricht + Filter: `matrix_agent.py:327-359`.
- **Loop-Guard-Algorithmus**: `matrix_agent.py:49-74,153-206` (Detektor 1: ≥`bot_threshold` Bot-Msgs → `cooldown`; Detektor 2: PingPong `≥8` in `pingpong_seconds`).
- UIAA-Registrierung: `matrix_agent.py:248-313`.
- Raum-Erstellung: `provisioner.py:621-688` (`/createRoom`, `power_level_content_override`, `invite`).
- Installer: `installer/modules/04_tuwunel.sh` (Release-API → Binary, `conduwuit.toml`, systemd-Unit, Health-Retry). ⚠️ Beim Bau aktuelle **tuwunel**-Release-URL verifizieren (Regel: Pakete vor dem Bauen prüfen).

---

## ETAPPE 1 — Fundament

### Task 1.1: matrix-nio Dependency

**Files:** Modify: `core/pyproject.toml`

- [ ] **Step 1:** In `core/pyproject.toml` unter `dependencies` ergänzen: `"matrix-nio>=0.25,<0.26"`.
- [ ] **Step 2:** Install: `cd core && pip install -e .` — Erwartung: matrix-nio + Abhängigkeiten (aiohttp, h11) installiert, kein Konflikt.
- [ ] **Step 3:** Verifizieren: `python -c "import nio; print(nio.__version__)"` — Erwartung: `0.25.x`.
- [ ] **Step 4:** Commit: `git add core/pyproject.toml && git commit -m "chore(teamchat): matrix-nio dependency"`.

### Task 1.2: Settings-Mixin

**Files:** Create: `core/src/hydrahive/settings/_teamchat.py` · Modify: `core/src/hydrahive/settings/settings.py` (Mixin in Komposition) · Test: `core/tests/test_teamchat_settings.py`

- [ ] **Step 1: Failing test**

```python
# core/tests/test_teamchat_settings.py
def test_teamchat_disabled_by_default(monkeypatch):
    monkeypatch.delenv("HH_TEAMCHAT_ENABLED", raising=False)
    from hydrahive.settings import settings
    assert settings.teamchat_enabled is False

def test_teamchat_homeserver_default():
    from hydrahive.settings import settings
    assert settings.matrix_homeserver_url == "http://127.0.0.1:6167"
```

- [ ] **Step 2:** Run `pytest core/tests/test_teamchat_settings.py -v` → FAIL (`AttributeError: teamchat_enabled`).
- [ ] **Step 3: Implement** — `_teamchat.py` nach `_mail.py`-Muster (live-`@property`, `env_or_override`):

```python
from functools import cached_property
from hydrahive.settings._env import env_or_override

class _TeamchatMixin:
    @property
    def teamchat_enabled(self) -> bool:
        return env_or_override("teamchat_enabled", "HH_TEAMCHAT_ENABLED", "0").lower() in ("1", "true", "yes")

    @property
    def matrix_homeserver_url(self) -> str:
        return env_or_override("matrix_homeserver_url", "HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167").strip()

    @property
    def matrix_server_name(self) -> str:
        return env_or_override("matrix_server_name", "HH_MATRIX_SERVER_NAME", "").strip()

    @property
    def matrix_registration_token(self) -> str:
        return env_or_override("matrix_registration_token", "HH_MATRIX_REGISTRATION_TOKEN", "").strip()
```

Dann `_TeamchatMixin` in die `Settings`-Klassen-Komposition in `settings.py:30-46` aufnehmen (Import + Basis-Klasse). `env_or_override`-Importpfad an `_mail.py` angleichen.

- [ ] **Step 4:** Run `pytest core/tests/test_teamchat_settings.py -v` → PASS.
- [ ] **Step 5:** Commit: `git add -A && git commit -m "feat(teamchat): Settings-Mixin (enabled, homeserver, server_name, reg_token)"`.

### Task 1.3: Migration 025 + DB-Layer

**Files:** Create: `core/src/hydrahive/db/migrations/025_teamchat.sql`, `core/src/hydrahive/db/teamchat.py` · Test: `core/tests/test_db_teamchat.py`

- [ ] **Step 1: Migration schreiben**

```sql
-- core/src/hydrahive/db/migrations/025_teamchat.sql
CREATE TABLE IF NOT EXISTS teamchat_identities (
    user_id       TEXT PRIMARY KEY,
    mxid          TEXT NOT NULL,
    access_token  TEXT NOT NULL,            -- verschlüsselt (enc:v1:)
    device_id     TEXT,
    next_batch    TEXT,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS teamchat_rooms (
    room_id     TEXT PRIMARY KEY,           -- Matrix room_id
    name        TEXT NOT NULL,
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS teamchat_room_agents (
    room_id      TEXT NOT NULL,
    agent_id     TEXT NOT NULL,
    attached_by  TEXT NOT NULL,
    attached_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (room_id, agent_id)
);
CREATE INDEX IF NOT EXISTS idx_teamchat_room_agents_room ON teamchat_room_agents (room_id);
```

- [ ] **Step 2: Failing test**

```python
# core/tests/test_db_teamchat.py — hydrahive-Imports LAZY halten (settings.data_dir-Freeze-Falle)
def test_identity_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("HH_DATA_DIR", str(tmp_path))
    from hydrahive.db import teamchat as tc
    from hydrahive.db.connection import init_db
    init_db()
    tc.upsert_identity("till", "@till:node", "enc:v1:xxx", device_id="DEV", next_batch=None)
    got = tc.get_identity("till")
    assert got["mxid"] == "@till:node"
    assert got["access_token"] == "enc:v1:xxx"

def test_room_and_agent_attach(tmp_path, monkeypatch):
    monkeypatch.setenv("HH_DATA_DIR", str(tmp_path))
    from hydrahive.db import teamchat as tc
    from hydrahive.db.connection import init_db
    init_db()
    tc.create_room("!r1:node", "Familie", "till")
    tc.attach_agent("!r1:node", "buddy", "till")
    assert [a["agent_id"] for a in tc.list_room_agents("!r1:node")] == ["buddy"]
    tc.detach_agent("!r1:node", "buddy")
    assert tc.list_room_agents("!r1:node") == []
```

- [ ] **Step 3:** Run `pytest core/tests/test_db_teamchat.py -v` → FAIL (`ModuleNotFoundError`/`AttributeError`).
- [ ] **Step 4: Implement** `db/teamchat.py` exakt nach `db/federation.py:11-110`-Muster (`with db() as conn`, `_row`). Funktionen:
  `get_identity(user_id) -> dict|None`, `upsert_identity(user_id, mxid, access_token, device_id=None, next_batch=None) -> dict`, `update_next_batch(user_id, next_batch) -> None`, `create_room(room_id, name, created_by) -> dict`, `list_rooms_for_user(user_id) -> list[dict]` (Mitgliedschaft kommt aus Matrix; hier alle bekannten Räume), `get_room(room_id) -> dict|None`, `attach_agent(room_id, agent_id, attached_by) -> None`, `detach_agent(room_id, agent_id) -> None`, `list_room_agents(room_id) -> list[dict]`. `upsert_identity` per `INSERT ... ON CONFLICT(user_id) DO UPDATE`.
- [ ] **Step 5:** Run `pytest core/tests/test_db_teamchat.py -v` → PASS.
- [ ] **Step 6:** Commit: `git add -A && git commit -m "feat(teamchat): Migration 025 + db/teamchat.py (identities/rooms/agents)"`.

### Task 1.4: tuwunel-Extension

**Files:** Create: `extensions/manifests/tuwunel.json`, `extensions/install/tuwunel.sh`, `extensions/uninstall/tuwunel.sh`

- [ ] **Step 1: Release-URL verifizieren** (Regel „Pakete vor dem Bauen prüfen"): aktuelles tuwunel-Repo + Latest-Release-Asset-Pattern (x86_64-linux) per GitHub-API bestätigen, bevor das Script geschrieben wird. HH1-Vorlage nutzte `girlbossceo/conduwuit` — für tuwunel den aktuellen Pfad einsetzen.
- [ ] **Step 2: Manifest** nach `extensions/manifests/headscale.json`-Schema:

```json
{
  "id": "tuwunel",
  "name": "Tuwunel (Matrix-Homeserver für Team-Chat)",
  "description": "Selbst gehosteter Matrix-Homeserver (conduit-Fork). Basis für den HydraHive Team-Chat.",
  "icon": "MessagesSquare",
  "category": "network",
  "install_script": "install/tuwunel.sh",
  "uninstall_script": "uninstall/tuwunel.sh",
  "service": "hydrahive-tuwunel",
  "health_url": "http://127.0.0.1:6167/_matrix/client/versions",
  "open_url": null,
  "installed_check": "/usr/local/bin/tuwunel",
  "install_params": []
}
```

- [ ] **Step 3: Install-Script** — Port aus `04_tuwunel.sh` (`[INFO]`/`[OK]`-Sentinels, `set -euo pipefail`): Release-Binary holen → `/usr/local/bin/tuwunel`; `conduwuit.toml` mit `server_name=$(hostname -f)`, `port=6167`, `address=127.0.0.1`, `allow_registration=true`, `registration_token=$(openssl rand -hex 32)`, **`allow_federation = false`**; systemd-Unit `hydrahive-tuwunel.service`; Health-Retry gegen `/_matrix/client/versions`. **Zusätzlich (HH2-spezifisch):** `server_name` + `registration_token` nach `$HH_CONFIG_DIR/matrix/{server_name,registration_token}` schreiben (0600), damit das Backend sie liest (via Settings bzw. direktem Read im `identity.py`).
- [ ] **Step 4: Uninstall-Script** nach `extensions/uninstall/ollama.sh`-Muster: Service stoppen/disablen, Unit + Binary + `conduwuit.toml` + Datenverzeichnis entfernen (mit Bestätigung im UI), `[OK]`.
- [ ] **Step 5: Manuell testen (Till, Testserver):** Extension im Admin-UI installieren → Health-Check grün, `systemctl is-active hydrahive-tuwunel` = active, `curl http://127.0.0.1:6167/_matrix/client/versions` antwortet.
- [ ] **Step 6:** Commit: `git add extensions/ && git commit -m "feat(teamchat): tuwunel-Extension (Matrix-Homeserver, Federation aus)"`.

**→ Etappe-1-Akzeptanz:** Extension installiert sich, Health grün; Migration 025 läuft beim Backend-Start; `settings.teamchat_enabled`/`matrix_homeserver_url` lesbar. Till bestätigt auf Testserver.

---

## ETAPPE 2 — Bridge-Kern  *(vor Bau voll als TDD-Tasks ausschreiben)*

- **Task 2.1 `loop_guard.py` + Tests** — direkter Port von `matrix_agent.py:49-74,153-206`. Reine Unit-Tests (kein Matrix nötig): Detektor 1 (≥`bot_threshold` Bot-Msgs → Circuit `cooldown`s offen), Detektor 2 (PingPong ≥8 in `pingpong_seconds`), Mensch-Nachrichten nie geblockt, Circuit schließt nach Cooldown. Als zustandslose Klasse `LoopGuard` mit `check(room_id, is_bot) -> bool` + `monotonic`-Zeit injizierbar für Tests.
- **Task 2.2 `client.py`** — matrix-nio `AsyncClient`-Wrapper (Vorlage `matrix_agent.py:78-122,219-246`): Login (Token aus DB → Fallback UIAA-Register `matrix_agent.py:248-313`), Sync-Loop (`sync(timeout=30000)`, `next_batch` über `db.teamchat.update_next_batch` persistieren). Test gegen Mock (`nio`-Responses faken).
- **Task 2.3 `identity.py`** — `ensure_identity(user_id) -> dict`: lazy provisionieren (deterministisches PW `sha256(user_id+secret)`, UIAA-Register mit `settings.matrix_registration_token`), Access-Token via `credentials/_crypto.encrypt(token, settings.data_dir)` in `db.teamchat.upsert_identity`. Test: Provisioning-Lifecycle + Token-Crypto-Roundtrip (Mock-Homeserver).
- **Akzeptanz:** `pytest` grün; gegen lokalen tuwunel: Backend loggt einen User ein, MXID + verschlüsselter Token in DB.

## ETAPPE 3 — Räume / Nachrichten / Echtzeit  *(vor Bau voll ausschreiben)*

- **Task 3.1 `rooms.py`** — `create_room(creator_user_id, name, invite_user_ids) -> room_id` (Port `provisioner.py:621-688`, `preset="private_chat"`, kein Projekt-Alias — freie Räume), `invite`, `kick`, Member-Liste via Matrix-State; HH-Metadaten in `db.teamchat`.
- **Task 3.2 `messages.py`** — `send(room_id, sender_user_id, text)`, `history(room_id, limit, from_token)` (Matrix `/messages`-Pagination — schließt HH1-Lücke).
- **Task 3.3 `broadcaster.py`** — `RoomBroadcaster` (Kopie `_session_broadcast.py:1-67`, Schlüssel = `room_id`).
- **Task 3.4 `sync_loop.py` + lifespan** — Hintergrund-Task (Vorlage `lifespan.py:177-233` + `mail/watcher.py:64-90`): `client.sync` → eingehende Raum-Events → `RoomBroadcaster.broadcast(room_id, …)`. Start nur wenn `settings.teamchat_enabled` und Homeserver erreichbar.
- **Task 3.5 `routes/teamchat.py`** — `APIRouter(prefix="/api/teamchat")`, `require_auth`→user_id. `GET/POST /rooms`, `GET /rooms/{id}/messages`, `POST /rooms/{id}/messages`, `GET /rooms/{id}/stream` (SSE, Vorlage `sessions_messages.py:59-93`), Member-Endpoints. Konditional: bei nicht erreichbarem Homeserver `409 teamchat_not_configured`. Registrierung in `api/main.py`.
- **Akzeptanz:** zwei Browser/curl → Mensch↔Mensch-Chat in Echtzeit + History, ohne Agent.

## ETAPPE 4 — Agent-Zuschaltung + Frontend  *(vor Bau voll ausschreiben)*

- **Task 4.1 `agent_bridge.py`** — Agent-Bot pro zugeschaltetem Agent (eigene Matrix-Identität via `identity.py`). Eingehendes Raum-Event → @mention/Name-Erkennung (primär Matrix-`m.mentions`, zusätzlich Klartext-Name) → `LoopGuard.check` → Runner via `_agent_glue`-Muster (`_run_agent(agent_id, room_event, …)`, `channel="matrix"`, Sender-Rahmung) → Antwort als Bot posten, Typing-Indikator währenddessen. `redaction.scrub` auf die Antwort.
- **Task 4.2 Agent-Endpoints** — `POST/DELETE /api/teamchat/rooms/{id}/agents` (zu-/wegschalten, `db.teamchat.attach/detach_agent`, Bot joint/verlässt Raum).
- **Task 4.3 Frontend `features/teamchat/`** — `api.ts`/`types.ts`/`useTeamchat.ts`/`TeamchatPage.tsx`/`RoomList`/`ChatView`/`MemberPanel`/`AgentAttachButton` nach `features/federation`+`features/chat`-Muster; SSE-Konsum nach `features/extensions/api.ts:16-59`.
- **Task 4.4 Verkabelung** — `App.tsx` (Route), `nav-config.ts` (NavItem, konditional über Capabilities-Check), `colors.ts` (`/teamchat`), `i18n/index.ts` + `locales/{de,en}/teamchat.json`. Build-Check `npm run build`.
- **Akzeptanz:** volles Schicht-1-Feature — freie Räume, Mensch↔Mensch, Agent bei Anrede zuschaltbar+antwortend, native UI, cross-device. Till testet im Browser.

---

## Test-Strategie (Regel: 80 % Coverage, TDD)

Reine Units zuerst (`loop_guard`, `identity`-Crypto-Roundtrip, `agent_bridge`-Mention-Erkennung) — kein Homeserver nötig. Matrix-berührende Module (`client`, `rooms`, `messages`) gegen gemockte `nio`-Responses. API-Routen: Auth + konditionale Verfügbarkeit + Happy-Path. Integrationstest gegen lokalen tuwunel auf dem Testserver (Tills manuelle Bestätigung pro Etappe). **Test-Gotcha:** hydrahive-Imports in Tests lazy halten (settings.data_dir-Freeze).
