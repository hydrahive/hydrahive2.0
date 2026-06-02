# Butler (Automation)

> Visueller Flow-Builder im Stil "Trigger → Condition → Action". Pro User/Projekt
> werden Regeln (Flows) als gerichteter Graph gespeichert; eingehende Events
> (Channel-Nachrichten, Webhooks, …) laufen durch alle aktiven Flows und können
> das Default-Verhalten (Master-Agent) überstimmen, eine feste Antwort senden oder
> an einen bestimmten Agenten weiterleiten.
>
> Codebase-Stand zum Zeitpunkt der Doku: Backend `core/src/hydrahive/butler/`,
> Route `api/routes/butler.py`, Frontend `frontend/src/features/butler/`.

---

## WAS

Einzelauflistung aller Fähigkeiten, Endpoints, Bausteine, Flags, UI-Komponenten.

### Backend-Kernmodule

- **`butler/__init__.py`** — Paket-Docstring/Public-API-Beschreibung (models / persistence / registry). Enthält keinen ausführbaren Code außer `from __future__ import annotations`. (`core/src/hydrahive/butler/__init__.py:1`)
- **`butler/models.py`** — Pydantic-Models: `NodePosition`, `Node`, `Edge`, `Flow`, `TriggerEvent`; Graph-Validierung in `Flow.validate_graph`. (`core/src/hydrahive/butler/models.py`)
- **`butler/persistence.py`** — Load/Save/Delete/List für Flows als JSON-Dateien pro Owner. (`core/src/hydrahive/butler/persistence.py`)
- **`butler/executor.py`** — DFS-Traversal eines Flows gegen ein Event, Trace-Sammlung, Action-Ausführung, `dry_run`-Modus, `dispatch_event` über alle Flows eines Owners. (`core/src/hydrahive/butler/executor.py`)
- **`butler/dispatch.py`** — Public-API `dispatch_for_channel` für Channel-Adapter; baut `Decision`-Objekt für den Channel-Router. (`core/src/hydrahive/butler/dispatch.py`)
- **`butler/template.py`** — Jinja2-`SandboxedEnvironment`-Rendering für Action-Params (`render(template, event)`). (`core/src/hydrahive/butler/template.py`)
- **`butler/registry/__init__.py`** — Registry-Pattern: `ParamSchema`, `TriggerSpec`, `ConditionSpec`, `ActionSpec`, `ActionResult`; die drei globalen Dicts `TRIGGERS`/`CONDITIONS`/`ACTIONS`; `register_*`-Funktionen; `all_specs()` Meta-API; `load_builtins()`. (`core/src/hydrahive/butler/registry/__init__.py`)

### Registry — Trigger (Backend, real registriert)

Jeder Trigger ist eine `TriggerSpec` mit `matches(params, event) -> bool`. Registriert über die Imports in `butler/registry/triggers/__init__.py:4`.

- **`message_received`** — "Nachricht eingegangen". Matcht `event_type=="message"`; Param `channel` (`all`/`whatsapp`/`telegram`/`discord`/`matrix`, default `all`); `all` matcht jeden Channel, sonst case-insensitiver Vergleich `event.channel`. (`core/src/hydrahive/butler/registry/triggers/message_received.py:7`)
- **`webhook_received`** — "Webhook eingegangen". Matcht `event_type=="webhook"`; Param `hook_id` (required im Schema); leeres `hook_id` matcht jeden Webhook, sonst exakter Vergleich mit `event.channel` (das beim Projekt-Webhook auf `project:<id>` gesetzt wird). (`core/src/hydrahive/butler/registry/triggers/webhook_received.py:7`)
- **`email_received`** — "Email eingegangen". Matcht `event_type=="email"`; Param `folder` (default `INBOX`); wenn gesetzt, case-insensitiver Vergleich gegen `event.payload["folder"]` (default `INBOX`). (`core/src/hydrahive/butler/registry/triggers/email_received.py:7`)
- **`git_event_received`** — "Git-Event". Matcht `event_type=="git"`; Params `provider` (`any`/`github`/`gitea`), `git_event` (`push`/`pull_request`/`issues`/`issue_comment`), `repo` (`owner/name`). Filtert über `event.payload["git_event"]`, `["provider"]`, `["repo"]`. (`core/src/hydrahive/butler/registry/triggers/git_event_received.py:7`)
- **`cron_fired`** — "Zeitplan". Matcht `event_type=="cron"`; Params `schedule_id` (optional; wenn gesetzt Vergleich gegen `event.payload["schedule_id"]`), `cron` (Cron-Expression, reines UI-Feld, wird in `matches` NICHT ausgewertet). (`core/src/hydrahive/butler/registry/triggers/cron_fired.py:7`)

### Registry — Conditions (Backend, real registriert)

Jede Condition ist eine `ConditionSpec` mit `evaluate(params, event) -> bool`. Registriert über `butler/registry/conditions/__init__.py:4`.

- **`time_window`** — "Zeitfenster". Params `from`/`to` (`HH:MM`, default `09:00`/`17:00`). Vergleicht lokale Systemzeit (`datetime.now()`); unterstützt Mitternacht-Crossing (z.B. 22:00–06:00). Ungültige/leere Zeiten → `False`. (`core/src/hydrahive/butler/registry/conditions/time_window.py:17`)
- **`day_of_week`** — "Wochentag". Param `days` (Liste aus `mo,di,mi,do,fr,sa,so`). Mappt `datetime.now().weekday()` auf das Kürzel und prüft Mitgliedschaft. Nicht-Liste → `False`. (`core/src/hydrahive/butler/registry/conditions/day_of_week.py:11`)
- **`contact_in_list`** — "Kontakt in Liste". Param `contacts` (komma-separierter String ODER Liste). Vergleicht `event.contact_id` (case-insensitiv) gegen die Liste. Leere Liste oder fehlende `contact_id` → `False`. (`core/src/hydrahive/butler/registry/conditions/contact_in_list.py:7`)
- **`message_contains`** — "Nachricht enthält". Param `keyword`. Case-insensitiver Substring-Check in `event.message_text`. (`core/src/hydrahive/butler/registry/conditions/message_contains.py:7`)
- **`payload_field_equals`** — "Payload-Feld =". Params `field` (Punkt-Notation JSON-Pfad), `value`. `str(actual)==str(expected)`. (`core/src/hydrahive/butler/registry/conditions/payload_field.py:46`)
- **`payload_field_contains`** — "Payload-Feld enthält". Params `field`, `value`. Case-insensitiver Substring im aufgelösten Feld. (`core/src/hydrahive/butler/registry/conditions/payload_field.py:53`)
- **`regex_match`** — "Regex-Treffer". Params `pattern`, `target` (default `message_text`; sonst Payload-Feldname). `re.search`; ungültige Regex → `False`. (`core/src/hydrahive/butler/registry/conditions/regex_match.py:9`)
  - Hilfsfunktion `_walk(obj, path)` navigiert per Punkt-Notation durch verschachtelte Dicts (`payload_field.py:10`).

### Registry — Actions (Backend, real registriert)

Jede Action ist eine `ActionSpec` mit `async execute(params, event) -> ActionResult`. Registriert über `butler/registry/actions/__init__.py:4`.

- **`agent_reply`** — "Agent antworten lassen". Param `agent_id` (required). Ruft den Agenten NICHT selbst, sondern liefert `reply_via_agent=agent_id`, `stop_default=True`. Leeres `agent_id` → `ok=False`, `stop_default=False` (Master bleibt zuständig statt stiller Failure). (`core/src/hydrahive/butler/registry/actions/agent_reply.py:18`)
- **`agent_reply_with_prefix`** — "Agent mit Vorgabe antworten lassen". Params `agent_id`, `instruction`. Rendert `instruction` per Jinja2, liefert `reply_via_agent` + `reply_prefix`. (`core/src/hydrahive/butler/registry/actions/agent_reply.py:30`, `:61`)
- **`agent_reply_guided`** — Alias auf `_exec_prefix` (= `agent_reply_with_prefix`), für alten octopos-Frontend-Code. (`core/src/hydrahive/butler/registry/actions/agent_reply.py:69`)
- **`forward`** — "An Agent weiterleiten". Alias auf `_exec_plain` (= `agent_reply`), für altes UI. (`core/src/hydrahive/butler/registry/actions/agent_reply.py:79`, `:83`)
- **`reply_fixed`** — "Feste Antwort senden". Param `text` (required, Jinja2). Liefert `reply_text` (gerendert) + `stop_default=True`. Sendet NICHT selbst — Channel-Router sendet. (`core/src/hydrahive/butler/registry/actions/reply_fixed.py:13`)
- **`http_post`** — "HTTP-POST". Params `url` (required, Jinja2), `body` (Jinja2), `headers` (JSON-String). Echter POST via `safe_async_client` mit SSRF-Schutz; default `Content-Type: application/json`; Timeout 15s. (`core/src/hydrahive/butler/registry/actions/http_post.py:15`)
- **`send_email`** — "Email senden". Params `to`/`subject`/`body` (Jinja2). **STUB** — rendert nur und loggt via `stub_result`, sendet keine Mail. (`core/src/hydrahive/butler/registry/actions/send_email.py:10`)
- **`discord_post`** — "Discord-Nachricht". Params `channel_id`, `message` (Jinja2). **STUB**. (`core/src/hydrahive/butler/registry/actions/discord_post.py:10`)
- **`git_create_issue`** — "Git-Issue erstellen". Params `provider`/`repo`/`title`/`body`. **STUB**. (`core/src/hydrahive/butler/registry/actions/git.py:11`)
- **`git_add_comment`** — "Git-Kommentar hinzufügen". Params `provider`/`repo`/`issue_number`/`body`. **STUB**. (`core/src/hydrahive/butler/registry/actions/git.py:21`)
- **`ignore`** — "Ignorieren". Keine Params. Liefert `stop_default=True` ohne Side-Effects. (`core/src/hydrahive/butler/registry/actions/ignore.py:17`)
- **`queue`** — "In Queue legen". Keine Params. Aktuell identisch zu `ignore` (`stop_default=True`); Queue-Anbindung geplant. (`core/src/hydrahive/butler/registry/actions/ignore.py:24`)
- **`_stub.stub_result(label, params)`** — gemeinsamer Helper für die Stub-Actions: loggt `[butler-stub] <label> params=...` und liefert `ActionResult(ok=True, detail="stub:<label>")`. (`core/src/hydrahive/butler/registry/actions/_stub.py:12`)

### REST-Endpoints (`prefix=/api/butler`, `api/routes/butler.py`)

- **`GET /api/butler/flows`** — Liste aller Flows; Admin sieht alle (`list_flows(owner=None)`), sonst nur eigene. (`api/routes/butler.py:24`)
- **`GET /api/butler/flows/{flow_id}`** — Einzelner Flow; `flow_or_404` prüft Existenz + Ownership/Admin. (`api/routes/butler.py:34`)
- **`POST /api/butler/flows`** — Flow anlegen (`201`); prüft `flow_id`-Format (`_ID_RE`), Kollision (`409 butler_flow_id_taken`), validiert Graph. (`api/routes/butler.py:43`)
- **`PUT /api/butler/flows/{flow_id}`** — Flow aktualisieren; `body.flow_id` muss zum Pfad passen (`butler_flow_id_mismatch`); `owner` + `created_at` werden aus dem existierenden Flow übernommen. (`api/routes/butler.py:66`)
- **`POST /api/butler/flows/{flow_id}/dry_run`** — Dry-Run: lädt Flow, ruft `bex.dispatch(flow, body.event, dry_run=True)`; Actions werden NICHT ausgeführt. (`api/routes/butler.py:90`)
- **`DELETE /api/butler/flows/{flow_id}`** — Flow löschen (`204`). (`api/routes/butler.py:101`)
- **`POST /api/butler/webhooks/project/{project_id}`** — Projekt-Webhook (`202`); Secret-Auth via `X-Webhook-Secret`; baut `TriggerEvent(event_type="webhook", channel="project:<id>")`; feuert nur tenant-isolierte Flows. (`api/routes/butler.py:111`)
- **Helper `_project_flows(project, project_id)`** — Tenant-isolierte Flow-Auswahl (created_by + members, scope=project, scope_id-Match, enabled). (`api/routes/butler.py:151`)

> **Kein** `GET /api/butler/registry`-Endpoint existiert, obwohl `all_specs()` (registry/__init__.py:85) genau dafür gebaut ist und Frontend-Kommentare darauf verweisen (`palette-data.ts:5`). Die Meta-API ist tot/unverdrahtet — das Frontend definiert die Palette komplett client-seitig.

### Route-Helper (`api/routes/_butler_route_helpers.py`)

- **`FlowInput`** — Request-Body-Model (flow_id, name, enabled, nodes, edges, scope, scope_id). (`_butler_route_helpers.py:15`)
- **`DryRunInput`** — `{event: TriggerEvent}`. (`_butler_route_helpers.py:25`)
- **`is_admin(role)`** — `role == "admin"`. (`_butler_route_helpers.py:29`)
- **`flow_or_404(owner_query, flow_id, user, role)`** — `_ID_RE`-Check, Existenz, Ownership/Admin. (`_butler_route_helpers.py:33`)
- **`_ID_RE = ^[A-Za-z0-9_\-]+$`** (`_butler_route_helpers.py:12`).

### Integrationspunkte (außerhalb des butler-Pakets)

- **App-Lifespan** ruft `load_butler_builtins()` (= `registry.load_builtins`) beim Start — registriert alle builtin Subtypes. (`api/lifespan.py:21`, `:120`)
- **Router-Registrierung**: `app.include_router(butler_router)` in `api/main.py:140` (Import `:19`).
- **Channel-Router** `handle_incoming` ruft `dispatch_for_channel` als ersten Pass vor dem Master-Agent. (`communication/router.py:13`, `:38`)
- **Mail-Watcher** schickt eingehende Mails ebenfalls durch `handle_incoming` (channel=`email`). (`communication/mail/watcher.py:51`)
- **Backup/Restore**: `user_archive._export_butler` exportiert `butler/<flow_id>.json`; `user_restore._restore_butler` lädt sie wieder ein. (`backup/user_archive.py:96`, `backup/user_restore.py:202`)
- **Settings**: `settings.butler_dir` = `config_dir / "butler"`. (`settings/_infra.py:80`)
- **SSRF-Guard** `net/ssrf.py` wird von `http_post` genutzt (`validate_outbound_url`, `safe_async_client`, `SsrfBlocked`). (`net/ssrf.py:1`)

### Frontend — Komponenten (`frontend/src/features/butler/`)

- **`ButlerPage.tsx`** — Top-Level-Page, wrappt alles in `<ReactFlowProvider>`; `ButlerPageInner` verbindet `useButlerFlow()` mit TopBar/Palette/Canvas/PropertiesPanel; Dark-Mode-Detection via `document.documentElement.classList`. (`ButlerPage.tsx:9`, `:17`)
- **`useButlerFlow.ts`** — zentraler Hook: State für flows/activeFlowId/name/enabled/saving/toast, ReactFlow-Nodes/Edges, ausgewählte Node, Agentenliste; Aktionen `loadFlow/newFlow/saveFlow/deleteFlow/toggleFlow/dryRunFlow`, Drag&Drop, Connect, Param-Update, Delete. (`useButlerFlow.ts:12`)
- **`_ButlerTopBar.tsx`** — Toolbar: Flow-Dropdown (gefiltert nach projectId), Name-Input, Enable-Toggle, Neu/Speichern/Dry-Run/Löschen-Buttons, Projekt-Badge. (`_ButlerTopBar.tsx:22`)
- **`_ButlerCanvas.tsx`** — ReactFlow-Canvas mit Background-Dots, Controls, MiniMap (Farbe nach Node-Typ), Empty-State-Panel, snapToGrid `[15,15]`. (`_ButlerCanvas.tsx:23`)
- **`NodePalette.tsx`** — linke Sidebar, drei collapsible Gruppen (Trigger/Condition/Action), Drag-Source mit MIME `application/butler-node`; "bald"-Badge + Drag-Sperre für `UNWIRED_TRIGGERS`. (`NodePalette.tsx:26`)
- **`nodes.tsx`** — drei Custom-Node-Komponenten `TriggerNodeComp`/`ConditionNodeComp`/`ActionNodeComp` + `NODE_TYPES`-Map; Handles (Trigger: nur output; Condition: input + true/false; Action: input + output); Farbcodierung grün/blau/orange. (`nodes.tsx:19`, `:92`)
- **`PropertiesPanel.tsx`** — rechte Sidebar; rendert subtype-spezifische Form via `FORMS[subtype]` + optionalem `EXTRA_FORMS[subtype]`; Delete-Button. (`PropertiesPanel.tsx:19`)
- **`paramSummary.ts`** — `paramSummary(subtype, params, t)` liefert die Kurzvorschau-Zeile pro Node auf dem Canvas. (`paramSummary.ts:5`)
- **`palette-data.ts`** — statische Palette: `defaultParams(subtype)`, `PALETTE_LABEL_KEY`, `UNWIRED_TRIGGERS`, `PALETTE_STRUCTURE`. (`palette-data.ts:15`)
- **`adapter.ts`** — `backendToFrontend`/`frontendToBackend`-Konvertierung + `butlerLegacyApi` (list/create/update/remove/toggle/dryRun) + `slugify`. (`adapter.ts:9`)
- **`types.ts`** — Frontend- (`ButlerNodeData`, `ButlerFlow`, `BNode`) und Backend-Shapes (`BackendNode`, `BackendEdge`, `BackendFlow`). (`types.ts`)

### Frontend — Property-Forms

- **`properties/registry.tsx`** — `FORMS`-Map (subtype → Form) + `EXTRA_FORMS` (nur `agent_reply_guided`). (`properties/registry.tsx:28`, `:66`)
- **`properties/_helpers.tsx`** — `FormProps`, `Field`, `TextInput`, `TextArea`, `Select`, `AgentSelect`, `Info`. (`properties/_helpers.tsx`)
- **`properties/_triggers.tsx`** — `GitEventForm`, `HeartbeatForm`, `MessageReceivedForm`, `DiscordEventReceivedForm`, `EmailReceivedForm`; export `DISCORD_EVENT_OPTS`. (`properties/_triggers.tsx`)
- **`properties/_conditions.tsx`** — `TimeWindowForm`, `DayOfWeekForm`, `MessageContainsForm`, `PayloadFieldContainsForm`, `GitBranchIsForm`, `GitAuthorIsForm`, `GitActionIsForm`, `EmailContainsForm`, `DiscordEventIsForm`, `DiscordEmojiIsForm`. (`properties/_conditions.tsx`)
- **`properties/_actions.tsx`** — `AgentReplyForm`, `AgentReplyGuidedExtra`, `ReplyFixedForm`, `HttpPostForm`, `SendEmailForm`, `GitCreateIssueForm`, `GitAddCommentForm`, `DiscordPostForm`, `ContactKnownInfo`, `IgnoreInfo`, `QueueInfo`. (`properties/_actions.tsx`)
- **`properties/_webhook.tsx`** — `WebhookTriggerForm` mit Hook-ID-Sanitizing + Copy-to-Clipboard für die Webhook-URL. (`properties/_webhook.tsx:7`)

### Frontend — Routing & i18n

- **Route** `path="butler"` → `<ButlerPage />` in `frontend/src/App.tsx:78` (Import `:24`).
- **i18n-Namespace** `butler` registriert in `frontend/src/i18n/index.ts:77/:88/:108`; Locale-Dateien `frontend/src/i18n/locales/{de,en}/butler.json` (de: 147 Keys).

---

## WIE

### Datenfluss 1 — Flow im Editor bauen & speichern

1. User öffnet `/butler` → `ButlerPage` → `useButlerFlow()` lädt beim Mount alle Flows (`butlerLegacyApi.list()` → `GET /butler/flows` → `backendToFrontend`) und die Agentenliste (`GET /agents`). (`useButlerFlow.ts:35`)
2. Drag aus `NodePalette`: `onDragStart` schreibt `{type, subtype, label}` als `application/butler-node` ins `dataTransfer`. (`NodePalette.tsx:32`)
3. Drop auf Canvas: `onDrop` liest den MIME-Payload, berechnet die Flow-Position (`rf.screenToFlowPosition`), erzeugt eine neue Node mit `genId(type)` und `defaultParams(subtype)`. (`useButlerFlow.ts:119`)
4. Verbinden: `onConnect` → `addEdge` mit Style; Condition-Handles `true`/`false` erzeugen rote/indigo Edges. (`useButlerFlow.ts:115`, `adapter.ts:27`)
5. Node auswählen → `PropertiesPanel`; `updateParams` ersetzt `node.data.params` immutabel. (`useButlerFlow.ts:134`)
6. Speichern (`saveFlow`):
   - **Guard**: enthält der Flow einen Trigger aus `UNWIRED_TRIGGERS`, bricht der Save mit Toast ab (kein Backend-Event-Sender). (`useButlerFlow.ts:58`)
   - scope/scope_id: nur beim **Neu-Anlegen mit `?project=<id>`** in der URL wird `scope="project"` + `scope_id=projectId` gesetzt, sonst `user`/`null`. (`useButlerFlow.ts:67`)
   - `frontendToBackend` mappt ReactFlow-Shape → Backend-Shape; `create` generiert `flow_id = slugify(name)-<rand4>`; `update` nutzt die bestehende ID. (`adapter.ts:71`, `:56`)
7. Backend `create_flow`/`update_flow`: baut `Flow(...)` → `model_validator validate_graph` läuft → `bp.save_flow` schreibt atomar (`.tmp` → `replace`). (`api/routes/butler.py:43`, `persistence.py:80`)

### Datenfluss 2 — Eingehende Channel-Nachricht (Live-Pfad)

1. Channel-Adapter (WhatsApp/Telegram/Mail/…) ruft `handle_incoming(event)` (`IncomingEvent`). (`communication/router.py:24`)
2. **Butler-Pass**: `dispatch_for_channel(target_username, channel, text, contact_id, contact_label)` baut einen `TriggerEvent(event_type="message", …)` und ruft `bex.dispatch_event(event, owner=target_username, dry_run=False)`. (`dispatch.py:34`)
3. `dispatch_event` lädt alle Flows des Owners (`bp.list_flows(owner=...)`), überspringt `enabled=False`, ruft pro Flow `dispatch(flow, event)`; nur matchende Flows landen im Ergebnis. Exceptions je Flow werden geloggt und geschluckt (ein kaputter Flow bricht nicht alles). (`executor.py:117`)
4. `dispatch(flow, event)`:
   - Findet den (einzigen) Trigger-Node, sucht `TRIGGERS[subtype]`; unbekannter Trigger → `matched=False`.
   - Ruft `tspec.matches(params, event)`; bei `False` → Abbruch, `matched=False`.
   - Sonst `_traverse` ab Trigger-`output`. (`executor.py:29`)
5. `_traverse(node_id, handle, …)`: iteriert Edges mit passender `source` + `source_handle`; für Ziel-Conditions → `_run_condition`, für Ziel-Actions → `_run_action`. Tiefe ist auf `_MAX_DEPTH=30` begrenzt. (`executor.py:53`, `:21`)
6. `_run_condition`: `CONDITIONS[subtype].evaluate(...)`; Exception → Trace `error`, Abbruch dieses Zweigs; sonst Trace `true`/`false` und Traverse über das passende Handle (`true`/`false`), Tiefe +1. (`executor.py:72`)
7. `_run_action`: bei `dry_run` nur Trace `would_execute`; sonst `await spec.execute(...)`, sammelt `ActionResult`-Felder in `actions_executed`, Trace `executed`; Exception → Trace `error`. Danach **Traverse über `output` weiter — AUSSER bei `ignore`/`queue`** (die terminieren den Zweig). (`executor.py:89`, `:112`)
8. Rückgabe `dispatch_for_channel`: iteriert alle Results und deren `actions_executed`; die **erste Action mit `stop_default=True` gewinnt** und füllt das `Decision`-Objekt (`reply_text` ODER `reply_via_agent`+`reply_prefix`), dann sofortiger Return. (`dispatch.py:52`)
9. Zurück im Router: bei `decision.stop_default`:
   - `reply_text` gesetzt → diesen Text direkt zurückgeben (Channel sendet). (`router.py:51`)
   - `reply_via_agent` gesetzt → `run_agent_for_event(agent_id, event, prefix=reply_prefix, voice_reply=…)`. (`router.py:53`)
   - sonst (`ignore`/`queue`) → `None` (schweigen). (`router.py:67`)
   - Kein `stop_default` / kein Match → **Default**: `run_master_for_event`. (`router.py:70`)
10. Agent-Run-Schicht `_build_agent_input`: baut User-Turn (Sender-Rahmung + Original-Nachricht, bei Fremden ohne Vorgabe ein Datenschutz-Block) und `extra_system` (Butler-Vorgabe als **vertrauenswürdiger Betreiber-Block** + ggf. Voice-Hint). Die Vorgabe (`reply_prefix`) landet **bewusst in der System-Schicht, nie im User-Turn** (sonst lehnt ein injection-resistenter Agent sie als eingeschleust ab). (`communication/_agent_glue.py:67`, `:45`)

### Datenfluss 3 — Projekt-Webhook

1. Externer POST auf `/api/butler/webhooks/project/{project_id}` mit `X-Webhook-Secret`. (`api/routes/butler.py:111`)
2. Projekt wird via `projects.config.get(project_id)` geladen (`404` wenn fehlt). (`api/routes/butler.py:122`)
3. Wenn das Projekt ein `webhook_secret` hat: Header-Pflicht (`401`) + `secrets.compare_digest` (`403` bei Mismatch). Ohne gesetztes Secret → "alter (insecure) Modus" ohne Auth (Deprecation). (`api/routes/butler.py:128`)
4. `TriggerEvent(event_type="webhook", channel=f"project:{project_id}", payload=request_body)`. (`api/routes/butler.py:135`)
5. `_project_flows` wählt nur tenant-autorisierte, projekt-gescopte, enabled Flows; jeder wird via `bex.dispatch(flow, event)` ausgeführt; Antwort zählt `flows_fired`. (`api/routes/butler.py:141`, `:151`)

### Schlüssel-Algorithmen / Zustandsmaschinen

- **Graph-Validierung** (`Flow.validate_graph`, `models.py:66`): eindeutige Node-IDs; max. 1 Trigger; jede Edge-Endpoint existiert; Condition-Edges nutzen nur `true`/`false`, alle anderen nur `output`; kein Zyklus (3-Farben-DFS `_check_no_cycles`, `models.py:92`); kein orphan Action-Node (Erreichbarkeit ab Trigger via DFS-Stack `_check_actions_reachable`, `models.py:112`).
- **Condition-Verzweigung**: `evaluate` liefert bool → Traverse über `true`- oder `false`-Handle. Das ist die einzige Verzweigungslogik; mehrere `true`-Edges fächern parallel auf.
- **`stop_default`-Wettlauf**: Über mehrere Flows hinweg gewinnt die erste `stop_default`-Action (Reihenfolge = Flow-Lade-Reihenfolge aus `list_flows`, also Dateisystem-`glob`-Reihenfolge — nicht deterministisch sortiert).
- **Template-Rendering**: `SandboxedEnvironment(autoescape=False)`, einzige Variable `event` (= `TriggerEvent.model_dump()`); Render-Fehler → Original-String zurück (Butler bricht nicht wegen Tippfehlern). (`template.py:16`, `:19`)

---

## WO

Datei:Zeile-Index für alle wichtigen Symbole.

### Backend butler/

- `core/src/hydrahive/butler/__init__.py:1` — Paket-Docstring
- `core/src/hydrahive/butler/models.py:18` — `NodeType`, `Scope`, `NAME_RE`
- `core/src/hydrahive/butler/models.py:23` — `NodePosition`
- `core/src/hydrahive/butler/models.py:28` — `Node`
- `core/src/hydrahive/butler/models.py:39` — `Edge`
- `core/src/hydrahive/butler/models.py:46` — `Flow`
- `core/src/hydrahive/butler/models.py:59` — `Flow._name_format` (Validator)
- `core/src/hydrahive/butler/models.py:66` — `Flow.validate_graph` (model_validator)
- `core/src/hydrahive/butler/models.py:92` — `_check_no_cycles`
- `core/src/hydrahive/butler/models.py:112` — `_check_actions_reachable`
- `core/src/hydrahive/butler/models.py:129` — `TriggerEvent`
- `core/src/hydrahive/butler/persistence.py:20` — `_FLOW_ID_RE`, `:21` `_OWNER_RE`
- `core/src/hydrahive/butler/persistence.py:24` — `_safe_owner`
- `core/src/hydrahive/butler/persistence.py:30` — `_flow_dir`, `:37` `_flow_path`, `:43` `_now`
- `core/src/hydrahive/butler/persistence.py:47` — `list_flows`
- `core/src/hydrahive/butler/persistence.py:69` — `get_flow`
- `core/src/hydrahive/butler/persistence.py:80` — `save_flow` (atomar via `.tmp`+`replace`)
- `core/src/hydrahive/butler/persistence.py:93` — `delete_flow`
- `core/src/hydrahive/butler/executor.py:21` — `_MAX_DEPTH=30`
- `core/src/hydrahive/butler/executor.py:24` — `_trace_node`
- `core/src/hydrahive/butler/executor.py:29` — `dispatch`
- `core/src/hydrahive/butler/executor.py:53` — `_traverse`
- `core/src/hydrahive/butler/executor.py:72` — `_run_condition`
- `core/src/hydrahive/butler/executor.py:89` — `_run_action` (`:112` ignore/queue-Terminierung)
- `core/src/hydrahive/butler/executor.py:117` — `dispatch_event`
- `core/src/hydrahive/butler/dispatch.py:25` — `Decision` (dataclass)
- `core/src/hydrahive/butler/dispatch.py:34` — `dispatch_for_channel`
- `core/src/hydrahive/butler/template.py:16` — `_ENV` (Sandbox), `:19` `render`

### Backend registry/

- `core/src/hydrahive/butler/registry/__init__.py:17` — `ParamSchema`
- `core/src/hydrahive/butler/registry/__init__.py:29` — `TriggerSpec`, `:38` `ConditionSpec`, `:47` `ActionSpec`
- `core/src/hydrahive/butler/registry/__init__.py:56` — `ActionResult`
- `core/src/hydrahive/butler/registry/__init__.py:68` — `TRIGGERS`/`CONDITIONS`/`ACTIONS` Dicts
- `core/src/hydrahive/butler/registry/__init__.py:73` — `register_trigger`/`register_condition`/`register_action`
- `core/src/hydrahive/butler/registry/__init__.py:85` — `all_specs` (Meta-API, unverdrahtet)
- `core/src/hydrahive/butler/registry/__init__.py:113` — `load_builtins`
- Triggers: `triggers/__init__.py:4`, `message_received.py:7/:16`, `webhook_received.py:7/:16`, `email_received.py:7/:17`, `git_event_received.py:7/:25`, `cron_fired.py:7/:16`
- Conditions: `conditions/__init__.py:4`, `time_window.py:9/:17/:32`, `day_of_week.py:8/:11/:19`, `contact_in_list.py:7/:21`, `message_contains.py:7/:14`, `payload_field.py:10/:22/:31/:46/:53`, `regex_match.py:9/:24`
- Actions: `actions/__init__.py:4`, `agent_reply.py:18/:30/:52/:61/:69/:79/:83`, `reply_fixed.py:13/:21`, `http_post.py:15/:46`, `send_email.py:10/:19`, `discord_post.py:10/:18`, `git.py:11/:21/:40/:52`, `ignore.py:13/:17/:24`, `_stub.py:12`

### Backend API & Integration

- `core/src/hydrahive/api/routes/butler.py:21` — `router` (prefix `/api/butler`)
- `core/src/hydrahive/api/routes/butler.py:24/:34/:43/:66/:90/:101/:111` — Endpoints (siehe WAS)
- `core/src/hydrahive/api/routes/butler.py:151` — `_project_flows`
- `core/src/hydrahive/api/routes/_butler_route_helpers.py:12` — `_ID_RE`, `:15` `FlowInput`, `:25` `DryRunInput`, `:29` `is_admin`, `:33` `flow_or_404`
- `core/src/hydrahive/api/main.py:19/:140` — Router-Import + include
- `core/src/hydrahive/api/lifespan.py:21/:120` — `load_butler_builtins`
- `core/src/hydrahive/communication/router.py:13/:24/:38/:49/:70` — `handle_incoming` + Butler-Pass
- `core/src/hydrahive/communication/_agent_glue.py:45/:67/:130` — Operator-Vorgabe-Block, `_build_agent_input`, `run_agent_for_event`
- `core/src/hydrahive/communication/mail/watcher.py:43/:51` — Mail → `handle_incoming`
- `core/src/hydrahive/backup/user_archive.py:96` / `user_restore.py:202` — Butler-Backup/Restore
- `core/src/hydrahive/settings/_infra.py:80` — `butler_dir`
- `core/src/hydrahive/net/ssrf.py:16/:19/:23/:35` — `ALLOWED_SCHEMES`, `SsrfBlocked`, `BLOCKED_RANGES`, `BLOCKED_HOSTNAMES`

### Frontend

- `frontend/src/features/butler/ButlerPage.tsx:9/:17`
- `frontend/src/features/butler/useButlerFlow.ts:10` `genId`, `:12` `useButlerFlow`, `:57` `saveFlow`, `:83` `deleteFlow`, `:91` `toggleFlow`, `:102` `dryRunFlow`, `:119` `onDrop`
- `frontend/src/features/butler/adapter.ts:9/:32/:56/:66` — Konverter + `butlerLegacyApi`
- `frontend/src/features/butler/types.ts:5/:12/:24/:33/:40` — Shapes
- `frontend/src/features/butler/_ButlerTopBar.tsx:22`
- `frontend/src/features/butler/_ButlerCanvas.tsx:23`
- `frontend/src/features/butler/NodePalette.tsx:26/:32/:40`
- `frontend/src/features/butler/nodes.tsx:19/:40/:68/:92`
- `frontend/src/features/butler/paramSummary.ts:5`
- `frontend/src/features/butler/palette-data.ts:15` `defaultParams`, `:51` `PALETTE_LABEL_KEY`, `:86` `UNWIRED_TRIGGERS`, `:93` `PALETTE_STRUCTURE`
- `frontend/src/features/butler/PropertiesPanel.tsx:19`
- `frontend/src/features/butler/properties/registry.tsx:28/:66` — `FORMS`/`EXTRA_FORMS`
- `frontend/src/features/butler/properties/_helpers.tsx:21/:31/:45/:59/:73/:89`
- `frontend/src/features/butler/properties/_triggers.tsx:5/:42/:58/:83/:99`
- `frontend/src/features/butler/properties/_conditions.tsx:10/:25/:54/:64/:80/:90/:100/:118/:131/:141`
- `frontend/src/features/butler/properties/_actions.tsx:5/:15/:25/:35/:55/:76/:95/:114/:130/:135/:140`
- `frontend/src/features/butler/properties/_webhook.tsx:7`
- `frontend/src/App.tsx:24/:78` — Route
- `frontend/src/i18n/index.ts:77/:88/:108` — Namespace `butler`

### Tests

- `core/tests/test_butler_smoke.py` — Graph-Validierung + Executor-Dispatch
- `core/tests/test_butler_webhook_tenant.py` — Tenant-Isolation `_project_flows` (Issue #178)
- `core/tests/test_butler_no_webhook_secret.py` — totes Pro-Flow-Secret entfernt (Issue #188)
- `core/tests/test_butler_prefix_system.py` — Butler-Vorgabe in System-Schicht statt User-Turn

---

## WARUM

Die nicht-offensichtliche Verdrahtung, Annahmen, Invarianten, Fallen.

### Actions senden NICHT — sie geben Routing-Hinweise zurück

Die Kern-Invariante des Designs: Der **Action-Executor sendet selbst keine Channel-Replies und ruft keine Agenten**. `reply_fixed`/`agent_reply`/`agent_reply_with_prefix` füllen nur die Felder `reply_text`/`reply_via_agent`/`reply_prefix`/`stop_default` im `ActionResult` (`registry/__init__.py:56`). Erst der **Channel-Router** (`handle_incoming`) wertet das aus und sendet bzw. startet den Agent-Run. Grund: Nur der Router hat den vollen `IncomingEvent`-Kontext (Session, Channel, Owner, Voice-Mode) korrekt verdrahtet — würde die Action selbst den Agenten rufen, ginge dieser Kontext verloren. Wer eine neue "sendende" Action baut, MUSS diesem Muster folgen, sonst fehlt der Kontext.

### `stop_default` ist der einzige Hebel auf das Default-Verhalten

Ob der Master-Agent übersprungen wird, hängt allein an `stop_default=True`. `agent_reply` mit leerem `agent_id` setzt bewusst `stop_default=False` (`agent_reply.py:23`) — sonst hätte ein halbkonfigurierter Flow den User stillgelegt (stille Failure). `ignore`/`queue` setzen `stop_default=True` ohne Reply → der Router schweigt aktiv.

### "Erste stop_default-Action gewinnt" ist reihenfolgenabhängig — und die Reihenfolge ist undefiniert

`dispatch_for_channel` bricht bei der ersten `stop_default`-Action ab (`dispatch.py:62`). Die Flow-Reihenfolge kommt aus `list_flows` → `d.glob("*.json")` (`persistence.py:61`) — also Dateisystem-Reihenfolge, **nicht sortiert/deterministisch**. Bei mehreren konkurrierenden Flows ist nicht garantiert, welcher "gewinnt". Falle für Multi-Flow-Setups.

### `ignore`/`queue` terminieren den Zweig, alle anderen Actions traversieren weiter

`_run_action` ruft nach Ausführung `_traverse(... "output" ...)` weiter — **außer** für `ignore`/`queue` (`executor.py:112`). Das ist hardcoded auf die Subtype-Strings. Eine neue terminierende Action müsste hier ergänzt werden, sonst läuft der Flow nach ihr weiter. Gleichzeitig haben `ignore`/`queue` in der Default-`PALETTE_STRUCTURE`/`nodes.tsx` einen `output`-Handle — man kann im UI also Edges hinter sie ziehen, die nie ausgeführt werden.

### Trigger sind Filter, kein Event-Bus

Ein Trigger `matches()` nur — er **erzeugt keine Events**. Ob ein Trigger jemals feuert, hängt davon ab, ob irgendwo ein `TriggerEvent` mit dem passenden `event_type` in `dispatch_event`/`dispatch` gespeist wird. Aktuell gibt es nur zwei reale Event-Quellen: (a) Channel-Nachrichten via `dispatch_for_channel` (immer `event_type="message"`) und (b) der Projekt-Webhook (`event_type="webhook"`). **`cron`, `git`, `email` werden nirgends gespeist** → diese Trigger sind tot (siehe Offene Enden). Das Frontend kennzeichnet einen Teil davon via `UNWIRED_TRIGGERS`, aber inkonsistent.

### Validierung doppelt: bei Save UND bei Load

`Flow` ist ein Pydantic-Model mit `model_validator` — Garbage wird beim `save_flow` und beim `get_flow`/`list_flows` (jeweils `model_validate_json`) abgelehnt. Manuell editierte/korrupte JSON-Dateien werden beim Laden geloggt und **übersprungen**, nicht geworfen (`persistence.py:64`). Vorteil: ein kaputtes File legt nicht die ganze Flow-Liste lahm. Falle: ein Tippfehler im JSON lässt den Flow stillschweigend verschwinden.

### Owner-Pfad-Sicherheit

`_safe_owner` erlaubt nur `[A-Za-z0-9_\-]` bzw. `project:<id>` und ersetzt `:` durch `_` (`persistence.py:24`) — Schutz gegen Path-Traversal beim Verzeichnisnamen. `_flow_path` validiert die `flow_id` separat (`persistence.py:37`). Wer den Owner-Regex ändert, öffnet potenziell Path-Traversal.

### Tenant-Isolation am Projekt-Webhook (Issue #178)

`_project_flows` lädt Flows **nur** für autorisierte Owner (`created_by` + `members`) und filtert auf `scope=="project"` + `scope_id==project_id` + `enabled` (`api/routes/butler.py:151`). Damit kann ein Außenstehender weder fremde Flows triggern noch über ein **gefälschtes `scope_id`** auf ein fremdes Projekt feuern (Test `test_forged_scope_id_by_outsider_does_not_fire`). Wer die Auswahl-Logik auf "alle Flows mit passendem scope_id" vereinfacht, reißt diesen Cross-Tenant-Bypass wieder auf.

### Webhook-Secret: gestaffelte Deprecation

Projekte **ohne** `webhook_secret` laufen im "alten (insecure) Modus" ohne Auth (`api/routes/butler.py:128`). `secrets.compare_digest` schützt vor Timing-Angriffen. Das **frühere Pro-Flow** `webhook_secret`-Feld wurde entfernt (Issue #188), weil es nie verifiziert, aber an alle Lese-User geleakt wurde — Alt-Flows mit dem Feld laden weiter (Pydantic ignoriert Extra-Keys).

### Butler-Vorgabe gehört in die System-Schicht (WhatsApp-Bug-Fix)

`reply_prefix` (aus `agent_reply_with_prefix`) wird in `_build_agent_input` als **Betreiber-Block in `extra_system`** gehängt, **nie in den User-Turn** (`_agent_glue.py:100`, `:45`). Grund (Tills realer WhatsApp-Test): Ein injection-resistenter Agent (Opus 4.8) hält eine Persona-Anweisung im User-Turn für eine eingeschleuste Nachricht und lehnt sie ab. In der System-Schicht ist sie echte Konfiguration und hat Vorrang vor der Persona. Bei Fremden + Vorgabe ersetzt der Block zusätzlich den generischen Datenschutz-Text durch einen harten "Sicherheits-Boden". Wer die Vorgabe wieder in den User-Turn zieht, bricht den Fix.

### SSRF-Schutz bei http_post

`http_post` validiert die URL vor dem Connect (`validate_outbound_url`) und nutzt `safe_async_client`, der die IP pinnt (DNS-Rebinding-sicher, #206) und `follow_redirects=False` hält (ein 30x auf eine interne URL würde den Check sonst umgehen) (`http_post.py:19`, `:35`). Wer auf einen rohen `httpx`-Client umstellt, öffnet SSRF.

### Template-Sandbox

`SandboxedEnvironment` verhindert `__import__`/Magie-Attributzugriff. Einzige Variable ist `event` (das ganze `TriggerEvent` als dict). `autoescape=False`, weil die Outputs Plaintext/JSON sind, kein HTML. Render-Fehler degradieren still zum Original-String — gut für UX, aber ein fehlerhaftes Template fällt nicht auf.

---

## Datenmodell

### Persistenz (Dateisystem, kein SQL)

- **Speicherort**: `settings.butler_dir` = `<HH_CONFIG_DIR>/butler/` (`settings/_infra.py:82`).
- **Layout**: `butler/<owner>/<flow_id>.json` — ein Verzeichnis pro Owner, eine JSON-Datei pro Flow.
- **Owner-Wert**: Username (`[A-Za-z0-9_\-]`) oder `project:<id>` (gespeichert mit `:`→`_` ersetzt). (`persistence.py:21/:24`)
- **Atomares Schreiben**: `.tmp`-Datei → `Path.replace`. (`persistence.py:87`)

### `Flow` (Pydantic, `models.py:46`)

| Feld | Typ | Default | Notiz |
|------|-----|---------|-------|
| `flow_id` | str (1–80) | — | nur `[A-Za-z0-9_\-]` (Route-Check) |
| `name` | str (1–80) | — | Regex `^[A-Za-z0-9_\- ]{1,80}$` |
| `owner` | str (1–80) | — | Username oder `project:<id>` |
| `enabled` | bool | `False` | nur enabled Flows feuern |
| `scope` | `"user"`/`"project"` | `"user"` | |
| `scope_id` | str\|None | `None` | bei project = Projekt-ID |
| `nodes` | list[Node] | `[]` | |
| `edges` | list[Edge] | `[]` | |
| `created_at` | str\|None | `None` | ISO-8601, beim ersten Save gesetzt |
| `modified_at` | str\|None | `None` | ISO-8601, bei jedem Save |
| `modified_by` | str\|None | `None` | Username |

### `Node` (`models.py:28`)

`id` (1–80), `type` (`trigger`/`condition`/`action`), `subtype` (1–80), `position` (`{x,y}` float), `params` (dict, default `{}`), `label` (str\|None, ≤120).

### `Edge` (`models.py:39`)

`id` (1–120), `source`, `target`, `source_handle` (`output`/`true`/`false`, default `output`).

### `TriggerEvent` (`models.py:129`)

`event_type` (str, Pflicht — Diskriminator: `message`/`webhook`/`email`/`git`/`cron`), `channel`, `contact_id`, `contact_label`, `is_known` (bool, default `False`), `message_text`, `payload` (dict, default `{}`), `timestamp`, `owner`.

### `ActionResult` (`registry/__init__.py:56`)

`ok` (bool), `detail` (str\|None), `reply_text`, `reply_via_agent`, `reply_prefix`, `stop_default` (bool, default `False`).

### `Decision` (Channel-Router-Vertrag, `dispatch.py:25`)

`matched` (bool), `reply_text`, `reply_via_agent`, `reply_prefix`, `stop_default` (bool).

### `ParamSchema` (UI-Meta, `registry/__init__.py:17`)

`key`, `label`, `kind` (`text`/`textarea`/`select`/`time`/`number`/`checkbox`/`list_text`), `required` (bool), `options` (list), `placeholder`, `default`.

### Events / Trace-Dicts

- `dispatch`-Rückgabe: `{matched, trace[], actions_executed[]}`.
- `trace`-Eintrag: `{node_id, type, subtype, label, decision, …}` mit `decision` ∈ `match`/`no_match`/`unknown_trigger`/`unknown_condition`/`unknown_action`/`true`/`false`/`error`/`executed`/`would_execute`/`max_depth_reached`.
- `dispatch_event`-Rückgabe: Liste von `{flow_id, owner, matched, trace, actions_executed}`.

### Config / Env / Konstanten

- `HH_CONFIG_DIR` (indirekt über `settings.config_dir`) → bestimmt `butler_dir`.
- `_MAX_DEPTH = 30` (Traversal-Tiefe, `executor.py:21`).
- `NAME_RE`, `_FLOW_ID_RE`, `_OWNER_RE`, `_ID_RE` — Validierungs-Regexes.
- Projekt-`webhook_secret` (aus `projects.config`, nicht butler-eigen) für den Projekt-Webhook.
- Frontend-Konstanten: `UNWIRED_TRIGGERS`, `PALETTE_STRUCTURE`, MIME-Type `application/butler-node`, snapGrid `[15,15]`.
- i18n-Namespace `butler` (de: 147 Keys).

---

## Offene Enden

### Tote / unverdrahtete Trigger (keine Event-Quelle)

- **`cron_fired`** — kein Sender speist jemals `event_type="cron"`. Der `cron`-Param wird in `matches` nicht ausgewertet (reines UI-Feld). Der Zahnfee-Scheduler (`zahnfee_scheduler`, lifespan.py:129) ist NICHT mit Butler verdrahtet. Tot. (`cron_fired.py`)
- **`git_event_received`** — kein Sender speist `event_type="git"`. Frontend kennzeichnet ihn als `UNWIRED_TRIGGERS` (palette-data.ts:88) und blockt das Speichern; aber der Backend-Trigger ist registriert und im Frontend-Properties-Form (`GitEventForm`) voll ausgebaut inkl. erfundener Webhook-URLs `/webhooks/github` + `/webhooks/gitea-butler`, die im Backend **nicht existieren** (_triggers.tsx:33). Drift/Falle.
- **`email_received`** — als `UNWIRED_TRIGGERS` markiert und Save-blockiert, ABER der Mail-Watcher existiert und ist live (`mail/watcher.py`). Er schickt Mails jedoch über `handle_incoming` → `dispatch_for_channel`, das **immer `event_type="message"`** baut (`dispatch.py:42`). Der `email_received`-Trigger braucht `event_type="email"` (`email_received.py:9`) → **er feuert nie, obwohl eine echte Mail-Quelle existiert**. Eine E-Mail triggert stattdessen nur `message_received`-Flows mit `channel=="email"`. Klarer Drift zwischen Mail-Schicht und Butler-Trigger-Modell.

### Stub-Actions (registriert, tun aber nichts Echtes)

- `send_email`, `discord_post`, `git_create_issue`, `git_add_comment` sind **Phase-2-Stubs**: sie rendern Params, loggen `[butler-stub] …` und liefern `ok=True, detail="stub:<label>"` — **ohne tatsächlichen Versand/API-Call** (`_stub.py`, `send_email.py`, `discord_post.py`, `git.py`). Im UI sehen sie wie funktionierende Actions aus → User erwartet Wirkung, bekommt keine. `send_email` ist besonders heikel, weil der Mail-Watcher (echtes SMTP) existiert und das Tool `send_mail` laut Docstring (`send_email.py:1`) "Phase 4" anbinden sollte — passiert nicht.

### Meta-API tot

- `all_specs()` (`registry/__init__.py:85`) ist als JSON-Meta-API für die Inspector-UI gebaut, aber **es gibt keinen Endpoint**, der sie ausliefert. `palette-data.ts:5` verweist explizit auf "siehe `/api/butler/registry`", die Route existiert nicht. Das Frontend definiert die Palette komplett client-seitig → doppelte Quelle der Wahrheit.

### Frontend ⇄ Backend Subtype-Drift (groß)

Das Frontend (`palette-data.ts`, `properties/registry.tsx`) kennt etliche Subtypes, die im **Backend gar nicht registriert** sind:
- Trigger: `heartbeat_fired`, `discord_event_received` (Backend hat dafür keine `TriggerSpec`).
- Conditions: `contact_known` (Backend hat `contact_in_list`, nicht `contact_known`), `git_branch_is`, `git_author_is`, `git_action_is`, `email_from_contains`, `email_subject_contains`, `email_body_contains`, `discord_event_is`, `discord_emoji_is` — **keine** dieser Conditions existiert im Backend-Registry. Ein gespeicherter Flow mit z.B. `git_branch_is` würde im Executor als `unknown_condition` enden.
- Umgekehrt kennt das Backend `payload_field_equals`, `cron_fired`, `contact_in_list`, `regex_match`, die im Frontend-Palette **fehlen** (kein UI-Eintrag).
- Param-Name-Drift: Frontend `http_post` nutzt `body_template` (palette-data.ts:35, _actions.tsx:44), Backend `http_post` liest `body` (`http_post.py:24`) → der im UI eingegebene Body kommt im Backend nie an. `git_event_received` Frontend nutzt `channel` für den Provider (_triggers.tsx:10), Backend liest `provider` (`git_event_received.py:13`). `email_received` Frontend hat `from_filter` (palette-data.ts:41), Backend wertet nur `folder` aus.

### Webhook-URL-Drift

- `_webhook.tsx:12` baut die Trigger-URL als `${origin}/webhooks/butler/${hookId}` — dieser Endpoint **existiert nicht** im Backend (nur `/api/butler/webhooks/project/{project_id}`). Der `webhook_received`-Trigger matcht zudem über `event.channel == hook_id`, aber der Projekt-Webhook setzt `channel="project:<id>"` — `hook_id` müsste also `project:<id>` lauten, was die UI nirgends nahelegt. Webhook-Trigger ist faktisch nur über den Projekt-Webhook + passend gesetztes `hook_id` nutzbar, die UI führt in die Irre.

### Inkonsistenzen / Aufräum-Kandidaten

- **`UNWIRED_TRIGGERS` unvollständig**: `cron_fired` ist im Backend registriert und fehlt im Frontend-Palette ganz; `heartbeat_fired`/`discord_event_received` sind im Frontend, aber im Backend gar nicht registriert (also nicht nur "unwired", sondern "nicht existent"). Die Liste schützt nur teilweise.
- **`webhook_received` Save nicht blockiert**, obwohl der einzige reale Webhook-Pfad der Projekt-Webhook ist und `hook_id`-Semantik unklar.
- **`queue` == `ignore`**: identisches Verhalten, eigener Subtype nur als Platzhalter (`ignore.py:24`). Bis zur echten Queue-Anbindung redundant.
- **`agent_reply_guided` + `forward`**: Aliase für Legacy-octopos-Frontend; `agent_reply_guided` ist im aktuellen Frontend-Palette vorhanden, `forward` ebenfalls — drei verschiedene Subtypes (`agent_reply_with_prefix`/`agent_reply_guided`) machen exakt dasselbe.
- **Dry-Run-Event hartcodiert**: `dryRunFlow` sendet immer `{event_type:"message", channel:"all", message_text:"test"}` (`useButlerFlow.ts:106`) — Flows mit Webhook/Email/Git/Cron-Trigger matchen im Dry-Run nie, der UI-Test ist für sie wertlos.
- **`is_known` in `TriggerEvent`** wird gesetzt aber nirgends ausgewertet; `dispatch_for_channel` setzt es immer auf `False` (`dispatch.py:48`). Die `contact_in_list`-Condition wertet stattdessen `contact_id` aus — `is_known` ist totes Feld.
- **`contact_id`-Quelle**: `dispatch_for_channel` mappt `event.external_user_id` → `contact_id`, aber `contact_label` (`sender_name`) wird nie in Conditions genutzt.
- **Phase-Kommentare** ("Phase 2: Stub", "Phase 4 verkabelt …") in mehreren Action-Files deuten auf einen nie abgeschlossenen Ausbauplan (`send_email.py:1`, `git.py:1`, `discord_post.py:1`).
- **`from_filter`/`folder` Email-UI** existiert, obwohl der Email-Trigger nie feuert — toter UI-Pfad.
