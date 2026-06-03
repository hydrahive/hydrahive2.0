# Team-Chat (Matrix / tuwunel)

> Subsystem: **Gemeinsamer Mehr-Parteien-Chat** von HydraHive2 — die Lücke neben
> Buddy-Chat (1:1 Mensch↔eigener Agent), AgentLink (Agent↔Agent, unsichtbar) und
> Channels (extern→Agent). Mehrere Menschen *einer* Instanz chatten in freien Räumen
> miteinander; lokale Agenten sind pro Raum zuschaltbar und antworten **bei Anrede**.
>
> **Substrat = Matrix**, Homeserver **tuwunel** (conduit-Fork) als opt-out-Extension.
> Grund: der harte Teil ist Föderation/State-Resolution — den hat Matrix gelöst, also
> nicht selbst stricken (HH1-Trauma). **Backend-Bridge + native UI**: das Frontend redet
> nur die HH-API, Matrix bleibt Backend (kein Element, kein matrix-js-sdk).
>
> Design-Dok: `docs/superpowers/specs/2026-06-03-teamchat-schicht1-design.md` ·
> Plan: `docs/superpowers/plans/2026-06-03-teamchat-schicht1.md`.
> Status (2026-06-03): **Schicht 1 komplett** (Etappe 1–3 Fundament/Bridge/Räume+API+SSE,
> 4a Agent-Bridge, 4b Frontend) **+ Etappe 5a Mitglieder-Verwaltung** — alles auf `main`,
> live verifiziert auf Testserver `192.168.3.23`. Offen: 5b Raum umbenennen/löschen,
> 5c privat/offen pro Raum, 5d Presence.
>
> **3 Schichten** (Regel #2): 1 = Intra-Instanz (eigene User + lokaler Agent) ← *hier*,
> 2 = Föderation Cross-Node/Tailscale, 3 = fremde Agenten cross-node.

---

## WAS  (jede Fähigkeit / Modul / Endpoint / UI-Komponente einzeln)

### Architektur-Garantie / Kern-Entscheidungen (Schicht 1)
- Freie Räume (Slack-artig, nicht projektgebunden; 1:1 = 2-Personen-Raum), `preset=private_chat` + invite.
- Echte Matrix-Accounts pro User, **lazy** provisioniert, Access-Token **verschlüsselt** in HH-DB.
- **Kein Matrix-sync-loop** — jede Nachricht läuft durch die HH-API (`POST .../messages`) → Matrix-send →
  direkter SSE-Broadcast. Das ist der einzige Andockpunkt für den Agent-Trigger.
- Agent antwortet **nur bei Anrede** (Text: `@name` / Vokativ), ein **Bot-Account pro Agent**, Agent-Run
  über **denselben Runner** wie Buddy-Chat (`run_agent_for_event`, `channel="matrix"`).

### Settings (`settings/_teamchat.py`, Mixin `_TeamchatMixin`)
- **`teamchat_enabled`** — aktiv wenn explizites Flag (`HH_TEAMCHAT_ENABLED`) gesetzt, **sonst automatisch
  sobald der Homeserver konfiguriert ist** (server_name + registration_token vorhanden → tuwunel-Extension
  installiert). „Konditional wie Mail/WhatsApp". (`settings/_teamchat.py:35-44`)
- **`matrix_homeserver_url`** (Default `http://127.0.0.1:6167`), **`matrix_server_name`**, **`matrix_registration_token`**
  — env/GUI-Override gewinnt, sonst die vom tuwunel-Installer geschriebene Datei `<config_dir>/matrix/<name>`.
  (`settings/_teamchat.py:46-72`, File-Fallback via `_matrix_file` :22-31, `_config_dir` :18-19)

### DB (`db/teamchat.py`, Migration `db/migrations/025_teamchat.sql`)
- Tabellen `teamchat_identities` (user_id PK, mxid, **access_token verschlüsselt**, device_id, next_batch),
  `teamchat_rooms` (room_id PK, name, created_by), `teamchat_room_agents` (room_id+agent_id PK, attached_by).
- `get_identity`/`upsert_identity` (INSERT…ON CONFLICT) /`update_next_batch` (`db/teamchat.py:22-65`),
  `get_room`/`create_room`/`list_rooms_for_user` (:72-100), `attach_agent`/`detach_agent`/`list_room_agents` (:107-136).

### tuwunel-Extension (`extensions/{manifests,install,uninstall}/tuwunel.sh`)
- Installiert den Matrix-Homeserver als systemd-Dienst `hydrahive-tuwunel` (Port 6167, `allow_federation=false`),
  schreibt `server_name` + `registration_token` nach `${HH_CONFIG_DIR}/matrix/` (das Backend liest sie).
  Health `…/_matrix/client/versions`. server_name ist nach Account-Erstellung quasi unveränderlich (Reuse-Logik).

### Matrix-Client (`teamchat/client.py`)
- `register_account` (UIAA-2-Schritt via httpx, `M_USER_IN_USE`→`AccountExistsError`), `login_password`
  (matrix-nio), `build_client` (authentifizierter AsyncClient, kein I/O), `_tokens_from_dict`.
  `AccountTokens`-Dataclass (mxid/access_token/device_id). (`teamchat/client.py:44,57,133,163`)

### Identität / Provisioning (`teamchat/identity.py`)
- **`ensure_identity(user_id)`** (Mensch) und **`ensure_bot_identity(agent_id)`** (Agent-Bot) — beide auf dem
  geteilten **`_ensure_account(db_key, localpart)`**-Kern (:57). Idempotent (DB-Treffer → entschlüsselter Token,
  kein Netz; sonst register→AccountExists→login-Fallback). (`identity.py:47-55`)
- Deterministisches Passwort `sha256(localpart:secret_key)[:32]` (`_derive_password` :36). Bot-localpart
  `agent-<sanitisiert>` (`_bot_localpart` :41, Matrix-Zeichensatz). **Bot-Namensraum getrennt**: DB-Key
  `agent:{id}` vs Mensch `user_id` → Mensch „buddy" und Agent „buddy" kollidieren nicht.
- Token-Crypto via `credentials._crypto.encrypt/decrypt(…, settings.data_dir)` (Prefix `enc:v1:`).

### LoopGuard (`teamchat/loop_guard.py`, Klasse `LoopGuard`)
- Sliding-Window-Circuit-Breaker (Default 5 Bot-Nachrichten / 30 s → 300 s Cooldown), pro `room_id`,
  Menschen nie geblockt. `check(room_id, is_bot, now=…)` (`now` injizierbar für Tests). Modul-Singleton
  `_loop_guard` in `agent_bridge.py:35`.

### Räume (`teamchat/rooms.py`)
- `create_room(creator, name, invite_user_ids)` (private_chat, invite + **auto-join** jedes Invitees mit dessen
  eigenem Token — invite ≠ member) (:28), `invite_member(room, inviter, invitee)` (invite + join) (:101),
  **`kick_member(room, kicker, target)`** (Ziel-MXID aus `server_name` gebaut → kein Geister-Account) (:150),
  `list_members` (joined MXIDs) (:179), `list_joined_rooms` (Matrix `joined_rooms` ∩ DB) (:200),
  `is_member` (:230). Alle werfen `RoomError`.

### Nachrichten (`teamchat/messages.py`)
- `send_message(room, sender, text)` → `{event_id, sender, text}` (:24), `history(room, requester, limit)` →
  `[{event_id, sender, text, ts}]` chronologisch, Nicht-Text gefiltert (:56). Schicht-1: nur `m.text`.

### Echtzeit (`teamchat/broadcaster.py`, `RoomBroadcaster` → Singleton `room_broadcaster`)
- Kopie des Session-Broadcaster-Musters, Schlüssel = `room_id`: `subscribe`/`broadcast`/`unsubscribe`,
  `threading.Lock` + `dict[room_id → set[Queue]]`. Gespeist von der POST-Message-Route + Bot-Post.

### Agent-Bridge (`teamchat/agent_bridge.py`) — „wann + wie antwortet ein Agent"
- **`is_addressed(text, agent_name, mention_mxids=, bot_mxid=)`** (:42) — reine Funktion, kein I/O. „mittel"-
  Heuristik: Matrix-`m.mentions` (stärkstes), `@name`, Vokativ (Name als ganzes Wort am Anfang oder an Komma/
  Doppelpunkt). Beiläufig im Fließtext → **nicht** adressiert.
- **`schedule_response(room, sender, text, mention_mxids=)`** (:84) — fire-and-forget `asyncio.create_task`
  (+ `_background_tasks`-Referenz gegen GC).
- **`respond_if_addressed(...)`** (:104) — pro angehängtem Agent: cfg holen (skip wenn disabled) → `ensure_bot_identity`
  → `is_addressed` → `_loop_guard.check` → `_run_and_post`. Jeder Agent in eigenem `try/except` (Background-Task
  darf nicht hochreißen).
- **`_run_and_post(...)`** (:141) — Owner-Guard (kein Owner → skip), Typing an, `run_agent_for_event` (Antwort
  ist bereits egress-`redaction.scrub`t), Typing **im finally** wieder aus (sonst hängt der Indikator 30 s),
  Bot postet `m.text` + Broadcast. Leere Antwort → kein Post.

### Agent-Membership (`teamchat/agent_membership.py`)
- `attach_agent(room, inviter, agent_id)` (:26) — `ensure_bot_identity` → invite (Fehler toleriert, evtl. schon
  Mitglied) → Bot `join` (Pflicht) → `db.attach_agent` (DB **nach** erfolgreichem Join, keine Geister-Zuordnung).
- `detach_agent(room, agent_id)` (:69) — DB zuerst (Quelle der Wahrheit fürs Antwortverhalten), dann Bot best-effort
  `room_leave`. `AgentMembershipError`.

### HTTP-API (`api/routes/teamchat.py`, Prefix `/api/teamchat`)
- Verfügbarkeits-Gate `_require_teamchat` → **409 `teamchat_not_configured`** wenn aus. (:37) Als Dep `_TC` an allen Routen.
- Authz-Helfer: `_require_member` (403 `not_a_member`, :77), `_require_agent_owner` (404/403, Admin-Bypass, :87),
  `_require_room_manager` (Ersteller/Admin, 404 `room_not_found`/403 `not_room_manager`, :97),
  `_require_known_user` (404 `user_not_found` — Einladen nur echter HH-User, :111).
- `GET/POST /rooms` (:123/:134), `GET/POST /rooms/{id}/messages` (:147/:160 — POST broadcastet + triggert via
  `schedule_response`), `GET /rooms/{id}/members` (:182), `POST /rooms/{id}/members` (einladen, manager-gated, läuft
  als Ersteller :198), **`DELETE /rooms/{id}/members/{user}`** (kicken, manager-gated, Ersteller nicht kickbar→422
  :219), `GET /rooms/{id}/stream` (SSE, Membership-403 :237), `GET/POST/DELETE /rooms/{id}/agents` (:285/:305/:325).

### Frontend (`frontend/src/features/teamchat/`)
- `types.ts` (TeamRoom/TeamMessage/RoomAgent), `_format.ts` (`mxidToName` :7 — `@agent-<id>`→Bot-Erkennung),
  `api.ts` (`teamchatApi` :15 REST + `streamRoom` :43 SSE-Reader), `useTeamchat.ts` (:7 Hook: Räume/Messages/
  Members/Agents, SSE-Subscription mit event_id-Dedupe + alive/active-Guards gegen Wrong-Room-Race).
- `TeamchatPage.tsx` (:12, 3-Spalten-Layout + 409-/Loading-/Error-Zustände), `_RoomList.tsx` (:21, links: Räume +
  Mitglieder, Raum-anlegen, **„+ Mitglied"/Entfernen** nur für Manager), `_ChatView.tsx` (:21, Buddy-Style-Karte:
  Bubbles via EmoteText/Markdown, **@-Ansprech-Pills**, Bot-Name statt UUID), `_AgentPanel.tsx` (:15, rechts:
  zugeschaltete Agenten + Picker).
- Verkabelung: Route `/teamchat` (`App.tsx`), NavItem Gruppe „working" + Icon `MessagesSquare` (`nav-config.ts`),
  Farbe `cyan` (`colors.ts`), i18n-Namespace `teamchat` de+en (`i18n/index.ts` + `locales/{de,en}/teamchat.json`).

### Tests + Smoke
- `core/tests/test_teamchat_{settings,db,client,identity,loop_guard,rooms,messages,broadcaster,routes,agent_bridge,agent_membership}.py`
  (~170 teamchat-Tests, TDD, Netzwerk gemockt). `scripts/smoke_teamchat.py` — E2E gegen echten tuwunel
  (Schritte 1–7 Mensch-Kette + 8–10 Bot join/leave).

---

## WIE  (Datenflüsse)

### Mensch schreibt Nachricht (Web → Matrix → alle)
`ChatView` POST `/rooms/{id}/messages` → `messages.send_message` (ensure_identity → build_client → room_send) →
`room_broadcaster.broadcast(room_id, json)` an **alle** SSE-Abonnenten (inkl. Absender!) → `useTeamchat`-SSE
dedupet über `event_id`. Danach `agent_bridge.schedule_response(...)` als fire-and-forget.

### Agent antwortet (Anrede → Runner → Bot-Post)
`schedule_response` → `respond_if_addressed`: für jeden angehängten Agent `is_addressed?` → `LoopGuard` →
`_run_and_post`: Typing an → `run_agent_for_event(agent_id, IncomingEvent(channel="matrix", is_owner=True,
is_group=True))` → Runner (Agent-eigenes `llm_model`) → egress-`scrub` → Bot-`room_send` → Broadcast.

### Agent zuschalten / Mitglied verwalten
`AgentPanel` POST `/rooms/{id}/agents` → `_require_member`+`_require_agent_owner` → `agent_membership.attach_agent`
(Bot joint). `RoomList` POST/DELETE `/rooms/{id}/members[/{user}]` → `_require_room_manager`(+`_require_known_user`)
→ `rooms.invite_member`/`kick_member` als Ersteller.

---

## WO  (Datei:Zeile)
- Settings: `core/src/hydrahive/settings/_teamchat.py:34-72`
- DB: `core/src/hydrahive/db/teamchat.py:22-136` · Migration `db/migrations/025_teamchat.sql`
- Client: `teamchat/client.py:44,57,133,163,188`
- Identity: `teamchat/identity.py:36,41,47,52,57`
- LoopGuard: `teamchat/loop_guard.py:16` · Singleton `teamchat/agent_bridge.py:35`
- Räume: `teamchat/rooms.py:28,101,150,179,200,230`
- Nachrichten: `teamchat/messages.py:24,56`
- Broadcaster: `teamchat/broadcaster.py:24`
- Agent-Bridge: `teamchat/agent_bridge.py:42,84,104,141`
- Agent-Membership: `teamchat/agent_membership.py:26,69`
- API: `api/routes/teamchat.py:30,37,77,87,97,111,123,134,147,160,182,198,219,237,285,305,325`
- Extension: `extensions/manifests/tuwunel.json`, `extensions/install/tuwunel.sh`, `extensions/uninstall/tuwunel.sh`
- Frontend: `frontend/src/features/teamchat/{types,_format,api,useTeamchat,TeamchatPage,_RoomList,_ChatView,_AgentPanel}.{ts,tsx}`
- Verkabelung: `frontend/src/App.tsx` (Route), `shared/nav-config.ts`, `shared/colors.ts` (`/teamchat`→cyan),
  `i18n/index.ts` (+`locales/{de,en}/teamchat.json`)
- Smoke: `scripts/smoke_teamchat.py`

---

## WARUM  (nicht-offensichtliche Verdrahtung, Gotchas)
- **Kein Sync-Loop** (bewusst): jede Nachricht durch die HH-API → POST-Route broadcastet selbst. Folge: ein Agent
  „hört" nur, was durch die API kommt; Bot-Posts re-triggern keine Agenten (kein Echo-Loop in Schicht 1).
- **Auto-Aktivierung**: `teamchat_enabled` leitet sich aus der Homeserver-Config ab — tuwunel-Extension installieren
  reicht, kein manuelles Flag pro Instanz. (Frühere Falle: nur Env-Flag → „läuft auf einer Kiste, Rest nicht".)
- **Bot-Namensraum** getrennt (`agent:{id}`-DB-Key, `agent-{id}`-localpart) — sonst kollidiert Mensch „buddy" mit
  Agent „buddy". Bot wird im Frontend über `roomAgents` zum Agent-Namen aufgelöst (sonst stünde die UUID da).
- **Anrede via Text** (`@name`/Vokativ), KEIN formales `m.mentions` — in Schicht 1 fließt alles als `m.text` durch
  die API, ein Metadaten-Kanal wäre redundant. Die @-Pills erzeugen den exakten `@Name`-Text.
- **`_run_and_post` Typing-off im finally** — sonst spinnt der Indikator 30 s wenn der Run wirft. Leere Antwort →
  kein Post (silent — siehe Offene Enden). nio-Response-`repr` nie loggen (Header/Token-Hygiene).
- **Kick baut Ziel-MXID aus `server_name`** statt `ensure_identity(target)` — sonst legt ein Tippfehler einen
  Geister-Account an. Add/Kick laufen **als Raum-Ersteller** (hat Matrix-Power-Level) — so funktioniert auch der
  Admin-Fall. Ersteller nicht kickbar (würde den Raum unbedienbar machen).
- **config_dir-Falle**: tuwunel-Extension schreibt nach `${HH_CONFIG_DIR}/matrix`. Läuft die Extension mit einem
  anderen `HH_CONFIG_DIR` als der Dienst, findet das Backend server_name/token nicht (auf HydrahiveHome beobachtet:
  `/etc/hydrahive` vs `/etc/hydrahive2`; auf `.23` konsistent).
- **Modell-Falle**: Coder/Billig-Modelle (qwen3-coder, jamba) liefern auf „sag hallo" oft **leere** Antworten →
  kein Post (kein Bug). Sonnet-Agenten antworten zuverlässig.

---

## Datenmodell
- **Tabellen** (Migration 025): `teamchat_identities`, `teamchat_rooms`, `teamchat_room_agents` (s.o.).
- **API-Fehler-Codes**: `teamchat_not_configured` (409), `not_a_member`/`not_room_manager`/`not_your_agent` (403),
  `room_not_found`/`agent_not_found`/`user_not_found` (404), `cannot_remove_room_owner` (422).
- **Env/Settings-Keys**: `HH_TEAMCHAT_ENABLED`, `HH_MATRIX_HOMESERVER_URL`, `HH_MATRIX_SERVER_NAME`,
  `HH_MATRIX_REGISTRATION_TOKEN` · Config-Dateien `<config_dir>/matrix/{server_name,registration_token}`.
- **i18n**: Namespace `teamchat` (de+en), Nav-Label `nav.teamchat`. **Farbe** `/teamchat`→cyan.
- **Routing**: `/teamchat` (Frontend), `/api/teamchat/*` (Backend), tuwunel `127.0.0.1:6167`.

---

## Offene Enden
- **Etappe 5b** Raum umbenennen/löschen, **5c** privat/offen pro Raum (Migration `visibility` + browse/join),
  **5d** Presence (geplant HH-native: online = aktive SSE-Verbindung) — noch nicht gebaut.
- **Leere/fehlgeschlagene Agent-Antwort ist still** — kein sichtbarer Hinweis im Raum (UX-Politur offen).
- **Kein Emote-Picker** im teamchat-Eingabefeld (Rendering geht, Einfügen nur per Tippen `:hydra-name:`).
- **Formales `m.mentions`** (primäres Anrede-Signal laut Design) wird vom Frontend (noch) nicht produziert;
  `is_addressed` kann es, Route hat den Durchreich-Marker.
- **Schicht 2/3** (Föderation cross-node, fremde Agenten) — `allow_federation=false`, komplett offen.
- **config_dir-Mismatch** auf manchen Installs (s. WARUM) — Install-Hygiene, kein Code-Bug.
