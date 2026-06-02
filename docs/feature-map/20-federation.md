# Federation & Streaming

> Feature-Landkarte für zwei lose gekoppelte Subsysteme, die im Frontend beide in der Nav-Gruppe `infrastructure` liegen:
> 1. **Federation** — Registry für entfernte „Workstations" (ProjektX-Peers), A2A-Card-Fetch, Remote-Chat-Bridge (`persona@workstation`), TLS-Verify-Toggle pro Peer, Client-Config-Generator (API-Key + Tailscale-Authkey + AgentLink-Koordinaten als JSON) **und** „Datamining-Instanzen" (externe Claude-Code-Instanzen = User + external-Agent + API-Key).
> 2. **Streaming** — Ghostflix-Scraper (Playwright-Login) + yt-dlp-Download-Runner für Bunny-CDN-Videos in eine Plex-Struktur.
>
> ⚠️ Begriffsklärung „Streaming": Dieses Subsystem hat **nichts** mit SSE/LLM-Token-Streaming zu tun. Die `A2ACapabilities.streaming`-Flag in der Federation-Card und das echte LLM-Token-Streaming (`runner/llm_bridge_stream.py`) sind **getrennte** Konzepte und gehören NICHT hierher. „Streaming" im Datei-/Routen-Namen meint ausschließlich den Video-Download (Ghostflix→Bunny→Plex).

---

## WAS

### Federation — Backend (Registry-Layer)

- `fetch_card(ws_id, force=False)` — holt die A2A-Card einer Workstation von `{url}/.well-known/agent.json`, cached 60 s in-memory, persistiert `card_json` + `last_seen` in DB. — `core/src/hydrahive/federation/registry.py:31`
- `remote_chat(ws_id, input_text, persona_id="", system="")` — POST `{url}/remote/chat` mit `Bearer`-Token + `X-Caller: hydrahive2`, gibt `data["text"]` zurück. — `registry.py:61`
- `refresh_all_cards()` — refresht im Hintergrund alle `enabled`-Workstations parallel via `asyncio.gather`. **TOT — nirgends aufgerufen** (siehe Offene Enden). — `registry.py:93`
- `_verify_for(ws)` — entscheidet, ob httpx die TLS-Kette prüft (`verify_tls`-Spalte, Default 1=prüfen). — `registry.py:20`
- `_card_cache` — in-memory dict `ws_id → (card_dict, fetched_at)`, TTL `_CACHE_TTL = 60.0`. — `registry.py:16`
- Package-Re-Export: `from hydrahive.federation import fetch_card, remote_chat`. `refresh_all_cards` ist **nicht** in `__all__`. — `core/src/hydrahive/federation/__init__.py:2`

### Federation — Backend (DB-Layer)

- `list_workstations()` — alle Workstations, sortiert nach `name`. — `core/src/hydrahive/db/federation.py:27`
- `get_workstation(ws_id)` — eine Workstation per ID. — `db/federation.py:35`
- `get_by_name(name)` — case-insensitive Lookup per Name (`LOWER(name)=LOWER(?)`). Wird vom `ask_agent`-Federation-Routing genutzt. — `db/federation.py:43`
- `create_workstation(name, url, token="", enabled=True, verify_tls=True)` — legt Row an, generiert `uuid4`, strippt trailing `/` von der URL, coerced bool→int. — `db/federation.py:52`
- `update_workstation(ws_id, **fields)` — Allow-List `{name,url,token,enabled,verify_tls}`, strippt URL-Slash, coerced enabled/verify_tls bool→int. — `db/federation.py:75`
- `update_card(ws_id, card_json)` — schreibt `card_json` + setzt `last_seen` per `strftime`. — `db/federation.py:96`
- `delete_workstation(ws_id)` — DELETE, gibt `rowcount > 0` zurück. — `db/federation.py:105`
- `_row(r)` — Row→dict, parsed `card_json`→`card`, normalisiert fehlendes `verify_tls`→1. — `db/federation.py:11`

### Federation — API-Endpoints (`/api/federation`, Prefix in `routes/federation.py:16`)

- `GET /api/federation/workstations` — Liste (Token gestrippt via `_strip_token`), Auth: `require_auth`. — `routes/federation.py:49`
- `POST /api/federation/workstations` — anlegen, 201, Auth: `require_admin`. Body `WorkstationCreate`. — `routes/federation.py:56`
- `PUT /api/federation/workstations/{ws_id}` — update (`exclude_none=True`), 404 wenn unbekannt, Auth: `require_admin`. Body `WorkstationUpdate`. — `routes/federation.py:71`
- `DELETE /api/federation/workstations/{ws_id}` — löschen, 204, Auth: `require_admin`. — `routes/federation.py:85`
- `POST /api/federation/workstations/{ws_id}/refresh` — forciert Card-Fetch (`fetch_card(force=True)`), 502 wenn Peer nicht erreichbar, Auth: `require_auth`. — `routes/federation.py:94`
- `GET /api/federation/workstations/{ws_id}/audit` — holt Remote-Audit-Log von `{url}/remote/audit` (Bearer + X-Caller), 400 wenn kein Token, 502 bei Fehler, Auth: `require_auth`. — `routes/federation.py:111`
- `GET /api/federation/clients` — listet API-Keys mit `role == "projektx"`, Auth: `require_admin`. — `routes/federation.py:149`
- `POST /api/federation/clients` — Client-Config-Generator: legt `projektx`-API-Key an, generiert Tailscale-Authkey (best effort), baut `hh2_client_v1`-JSON, Auth: `require_admin`. — `routes/federation.py:156`
- `DELETE /api/federation/clients/{key_id}` — löscht Client-Key, 204/404, Auth: `require_admin`. — `routes/federation.py:209`
- Pydantic-Modelle: `WorkstationCreate` (`routes/federation.py:22`), `WorkstationUpdate` (`:32`), `ClientCreate` (`:145`).
- Helper `_strip_token(ws)` — entfernt `token` + `card_json`, fügt `has_token: bool` + normalisiertes `verify_tls: bool` hinzu. — `routes/federation.py:40`

### Federation — Externe Instanzen / „Datamining-Instanzen" (`/api/external-instances`)

- `GET /api/external-instances` — Liste, Auth: `require_admin`. — `core/src/hydrahive/api/routes/external_instances.py:18`
- `POST /api/external-instances` — anlegen (User + external-Agent + API-Key als Einheit), 201; 400 `validation_error`, 409 `username_exists`. — `external_instances.py:23`
- `DELETE /api/external-instances/{agent_id}` — löschen, 204/404 `instance_not_found`. — `external_instances.py:33`
- `POST /api/external-instances/{agent_id}/rotate-key` — rotiert API-Key, gibt neuen Key einmalig zurück, 404 `instance_not_found`. — `external_instances.py:40`
- Pydantic `InstanceCreate(name 1–64, llm_model)`. — `external_instances.py:13`
- Orchestrierungs-Logik (keine eigene Tabelle, external-Marker am Agent IST die Einheit):
  - `create_instance(name, llm_model)` — `users.create` → `agent_config.create(external=True, type=master, temp=0.7, max_tokens=DEFAULT_MAX_TOKENS=16384, thinking_budget=0)` → `api_keys.create(name=f"{name}-hook")`. Rollt bei Teilfehler zurück. — `core/src/hydrahive/agents/external_instances.py:14`
  - `list_instances()` — leitet aus allen Agenten mit `external=True` ab: key_count, session_count (token_stats), last_activity (letzte Session). — `agents/external_instances.py:35`
  - `delete_instance(agent_id)` — löscht Agent, löscht Owner-User + dessen Keys nur wenn `_owner_is_dedicated`. — `agents/external_instances.py:66`
  - `rotate_key(agent_id)` — erst neuen Key, dann alte löschen (kein Aussperren). — `agents/external_instances.py:79`
  - `_owner_is_dedicated(owner)` — True nur wenn Rolle `user` UND keine weiteren Agenten (schützt admin/shared User). — `agents/external_instances.py:55`

### Federation — `ask_agent`-Tool (Federation-Routing)

- `ask_agent`-Tool mit `agent_id` im Format `persona@workstation` → Federation-Branch. — `core/src/hydrahive/tools/ask_agent.py:90`
- `_execute_federated(target, task, args)` — splittet `persona@ws`, Lookup per `get_by_name` ODER `get_workstation`, prüft `enabled`, ruft `remote_chat(ws_id, task, persona_id=persona)`, formatiert `[persona@ws]: <text>`. — `ask_agent.py:217`
- Tool-Schema erwähnt Federation-Adressierung explizit im `agent_id`-Description-Feld. — `ask_agent.py:42`

### Federation — Frontend (`features/federation/`)

- `FederationPage` — Hauptseite: Workstation-Liste + Info-Box + `ClientConnectionsSection` + `DataminingInstancesSection`. — `frontend/src/features/federation/FederationPage.tsx:13`
- `WorkstationCard` — Karte je Workstation: Status-Dot (last_seen), Protocol-Badge, Token-Shield, TLS-Lock/Unlock-Icon, Refresh-Button, Enable/Disable-Toggle, Delete, Expand (Card-Description, Capabilities-Badges, Personas-Liste `persona@ws`, last_seen, TLS-Toggle-Zeile, Audit-Log-Loader). — `frontend/src/features/federation/_WorkstationCard.tsx:16`
- `AddWorkstationDialog` — Dialog: name/url/token/verify_tls; Self-Signed-Heuristik (CGNAT-IP/.local/.tailnet) zeigt Warn-Hinweis. — `frontend/src/features/federation/_AddDialog.tsx:12`
- `ClientConnectionsSection` — Liste der ProjektX-Clients + „neu". — `frontend/src/features/federation/_ClientConnectionsSection.tsx:16`
- `NewClientDialog` — generiert Client-Config, zeigt URL/Tailscale/Authkey/AgentLink-Zusammenfassung, Download als `hh2-client-<slug>.json`. — `frontend/src/features/federation/_NewClientDialog.tsx:25`
- `DataminingInstancesSection` — Liste externer Instanzen mit session_count/last_activity, Copy-`HH_AGENT_ID`, Rotate-Key (zeigt neuen Key per `window.prompt`), Delete. — `frontend/src/features/federation/_DataminingInstancesSection.tsx:17`
- `NewInstanceDialog` — Name + Modell (Default `claude-opus-4-8`), zeigt nach Erstellung `HH_BASE_URL`/`HH_API_KEY`/`HH_AGENT_ID`-Block (+ auskommentiertes `HH_VERIFY_SSL=0`) zum Kopieren. — `frontend/src/features/federation/_NewInstanceDialog.tsx:24`
- API-Clients: `federationApi` (list/create/update/delete/refresh/audit), `clientsApi` (list/create/delete), `externalInstancesApi` (list/create/delete/rotateKey). — `frontend/src/features/federation/api.ts:22`
- Types: `A2ACard`, `A2ACapabilities`, `A2AAgent`, `Workstation`, `ClientConnection`, `ClientConfig`, `CreateClientResult`, `ExternalInstance`, `CreateInstanceResult`. — `frontend/src/features/federation/types.ts`
- `WorkstationFields`-Interface (geteilte create/update-Shape inkl. `verify_tls`). — `frontend/src/features/federation/api.ts:9`

### Streaming — Backend (Scraper)

- `scrape_series(url, username, password)` — Playwright-Login bei Ghostflix → Serien-URL laden → `window.episodes_data` aus JS-Kontext ODER Regex-Fallback aus HTML → Titel/Staffel/Episoden. — `core/src/hydrahive/streaming/scraper.py:21`
- `_login(page, username, password)` — POST `wp-login.php` (`#user_login`/`#user_pass`/`#wp-submit`), wartet auf Redirect, erkennt Fehler-Keywords. — `scraper.py:99`
- `_parse_title`, `_parse_season`, `_parse_episodes`, `_episodes_from_dict`, `_extract_ep_number` — HTML/JSON-Parsing-Helfer. — `scraper.py:127–196`
- Regexe: `_EPISODES_RE`, `_ASSIGN_RE`, `_LIBRARY_RE`, `_TITLE_RE`, `_SEASON_RE`. — `scraper.py:10–18`

### Streaming — Backend (Downloader)

- `run_job(job_id)` — Download-Runner: prüft Status/Existenz, baut Bunny-Embed-URL, hält `_download_lock` (max 1 gleichzeitig), ruft `_ytdlp` mit 2h-Timeout, setzt Status done/error/skipped. — `core/src/hydrahive/streaming/downloader.py:37`
- `_ytdlp(job_id, url, output)` — `asyncio.create_subprocess_exec` (keine Shell), liest stdout zeilenweise, parsed `%`-Fortschritt, schreibt progress (gecappt auf 99 während Lauf). — `downloader.py:85`
- `cancel_job(job_id)` — cancelt laufenden/wartenden Task, setzt Status `error="Abgebrochen"`. — `downloader.py:28`
- `build_output_path(plex_path, series_title, season, episode)` — baut `{plex}/{safe_title}/Staffel {N}/{safe_title} - S{NN}E{NN}.mkv`, säubert Sonderzeichen. — `downloader.py:124`
- Konstanten: `_DOWNLOAD_TIMEOUT = 7200` (2h), `_EMBED_BASE = iframe.mediadelivery.net/embed`, `_YTDLP_BIN` (venv-bin neben Python). — `downloader.py:11,19,21`
- State: `_download_lock` (process-wide), `_running_tasks: dict[job_id → Task]`, `_PROGRESS_RE`. — `downloader.py:18,24,25`

### Streaming — DB-Layer

- `get_credentials(user_id, provider="ghostflix")` — `db/streaming.py:16`
- `upsert_credentials(...)` — UPSERT auf `(user_id, provider)`. — `db/streaming.py:25`
- `create_job(...)` — `db/streaming.py:46`
- `list_jobs(user_id, limit=50)` — neueste zuerst. — `db/streaming.py:74`
- `get_job(job_id)` — `db/streaming.py:84`
- `update_job_status(job_id, status, progress=0, error=None)` — setzt `updated_at`. — `db/streaming.py:92`
- `delete_job(job_id, user_id)` — nur eigene Jobs. — `db/streaming.py:106`
- `count_active_jobs(user_id)` — **TOT — nirgends aufgerufen** (siehe Offene Enden). — `db/streaming.py:115`

### Streaming — API-Endpoints (`/api/streaming`)

- `GET /api/streaming/credentials` — eigene Credentials (ohne Klartext-PW, nur `has_password`), Auth: `require_auth`. — `core/src/hydrahive/api/routes/streaming.py:36`
- `PUT /api/streaming/credentials` — speichern (PW wird via `encrypt` verschlüsselt; leeres PW behält altes), 204. — `streaming.py:49`
- `POST /api/streaming/scrape` — Scrape mit gespeicherten Credentials (PW per `decrypt`), 400 wenn keine Creds, 422 bei `ValueError`. — `streaming.py:66`
- `POST /api/streaming/download/start` — erzeugt Jobs, startet sie sequenziell via `BackgroundTasks`, 202, gibt `job_ids` zurück, 400 wenn keine Episoden. — `streaming.py:98`
- `GET /api/streaming/jobs` — eigene Jobs. — `streaming.py:137`
- `DELETE /api/streaming/jobs/{job_id}` — löschen, 204/404. — `streaming.py:143`
- `POST /api/streaming/jobs/{job_id}/cancel` — abbrechen (Owner-Check), 204/404. — `streaming.py:150`
- Pydantic: `CredentialsIn`/`CredentialsOut` (`:24`/`:30`), `ScrapeIn` (`:62`), `JobIn` (`:83`), `StartDownloadIn` (`:90`).

### Streaming — Frontend (`features/streaming/`)

- `StreamingPage` — Credentials-Form + Scrape-Form + EpisodeList + JobList; pollt Jobs alle 2 s. — `frontend/src/features/streaming/StreamingPage.tsx:10`
- `CredentialsForm` — username/password/plex_path (collapsible, auto-open wenn keine Creds). — `frontend/src/features/streaming/_CredentialsForm.tsx:16`
- `EpisodeList` — Checkbox-Liste, Select-/Deselect-All, Download-Button (zeigt count). — `frontend/src/features/streaming/_EpisodeList.tsx:17`
- `JobList` — Job-Zeilen mit Status-Icon, Progress-Bar (nur `downloading`), Cancel/Delete, „Fertige löschen". — `frontend/src/features/streaming/_JobList.tsx:24`
- API-Client `streamingApi` (getCredentials/saveCredentials/scrape/startDownload/listJobs/deleteJob/cancelJob). — `frontend/src/features/streaming/api.ts:4`
- Types: `StreamingCredentials`, `Episode`, `ScrapeResult`, `StreamingJob`. — `frontend/src/features/streaming/types.ts`
- `STATUS_ICON`-Map, `DELETABLE`/`CANCELLABLE`-Sets. — `_JobList.tsx:13,21,22`

### Nav / Routing / i18n

- Nav-Einträge: `/federation` (Globe-Icon) + `/streaming` (Film-Icon), beide Gruppe `infrastructure`. — `frontend/src/shared/nav-config.ts:47,48`
- Routen registriert in `App.tsx:79` (`federation`) + `App.tsx:80` (`streaming`); Imports `App.tsx:33,34`.
- i18n-Namespaces `federation` + `streaming` registriert (de+en). — `frontend/src/i18n/index.ts:80,81,91,92,108`
- Backend-Router-Registrierung: `external_instances_router` (`api/main.py:105`), `federation_router` (`:149`), `streaming_router` (`:150`).

---

## WIE

### Federation: A2A-Card-Fetch (Klick „Refresh" → DB)

1. User klickt Refresh-Icon in `WorkstationCard` → `federationApi.refresh(ws.id)` → `POST /api/federation/workstations/{ws_id}/refresh`. — `_WorkstationCard.tsx:26`
2. Route lädt Workstation, ruft `fetch_card(ws_id, force=True)`. — `routes/federation.py:102`
3. `fetch_card`: bei `force=True` Cache-Skip; baut `{url}/.well-known/agent.json`; `httpx.AsyncClient(timeout=10, verify=_verify_for(ws))`; GET + `raise_for_status` + `.json()`. — `registry.py:42`
4. Bei Erfolg: `json.dumps(card)` → `update_card` (schreibt `card_json` + `last_seen`) → Cache-Eintrag mit `time.monotonic()`. — `registry.py:55`
5. Bei Exception: Warnung loggen, `None` zurück → Route antwortet **502** „A2A-Card nicht erreichbar". — `registry.py:51`, `routes/federation.py:103`
6. Frontend lädt Liste neu (`onRefresh()` → `load()`); `last_seen` ⇒ grüner Status-Dot. — `FederationPage.tsx:88`, `_WorkstationCard.tsx:41`

### Federation: Remote-Chat über `ask_agent` (`persona@workstation`)

1. Ein Agent ruft `ask_agent(agent_id="geralt@projektx-till", task=...)`. — `ask_agent.py:81`
2. `@` im Target → `_execute_federated`. Split in `persona_id`/`ws_name`. — `ask_agent.py:90,219`
3. Workstation-Lookup `get_by_name(ws_name)` **oder** `get_workstation(ws_name)` (Name- ODER ID-Treffer). Nicht gefunden → fail; deaktiviert → fail. — `ask_agent.py:228`
4. `remote_chat(ws["id"], task, persona_id=persona)`: prüft Token (sonst `ValueError`), baut Payload `{input, persona_id?, system?}`, Header `Authorization: Bearer <token>` + `X-Caller: hydrahive2`; `httpx.AsyncClient(timeout=120, verify=_verify_for)`; POST `{url}/remote/chat`; gibt `data["text"]` zurück. — `registry.py:61`
5. Tool-Output `[geralt@projektx-till]: <antwort>`. — `ask_agent.py:241`

> Hinweis: Der **interne** AgentLink-Pfad (kein `@`) ist ein völlig anderer Mechanismus (WebSocket + Redis-Pub/Sub + Future, `post_state`/`register_pending`) und gehört zu AgentLink, nicht zu Federation. Federation = HTTP-`/remote/chat`; AgentLink = WS-State-Transfer. Beide hängen am selben Tool `ask_agent`, sind aber strikt getrennt (`@` vs. kein `@`).

### Federation: Client-Config-Generator (Klick „Erstellen" → JSON-Download)

1. User gibt Namen in `NewClientDialog` ein → `clientsApi.create(name)` → `POST /api/federation/clients`. — `_NewClientDialog.tsx:37`
2. Route: `api_keys.create(name, username="admin", role="projektx")` → Plaintext-Key. `key_id` = erste 16 Hex-Zeichen nach `hhk_`. — `routes/federation.py:165`
3. Tailscale-Status `get_status()`; wenn `connected`: `create_invite()` (best effort, Fehler ignoriert) → `auth_key`. — `routes/federation.py:169`
4. Config `hh2_client_v1` zusammenbauen: `hh2.api_url` (`http://{ts_ip}:{port}`), `api_url_dns` (`https://{ts_dns}:{port}`), `api_key` (Klartext), optional `agentlink`-Block (nur wenn `settings.agentlink_url`), optional `tailscale`-Block. — `routes/federation.py:189`
5. Response `{key_id, name, config}`. Frontend zeigt Zusammenfassung, Download als `hh2-client-<slug>.json` (`Blob` + `URL.createObjectURL`). — `_NewClientDialog.tsx:14`

### Federation: TLS-Verify-Toggle

- Default `verify_tls=1` (prüfen, sicher). `_verify_for(ws)` liest die Spalte → `bool(ws.get("verify_tls", 1))`. Greift in `fetch_card` **und** `remote_chat` (`verify=` von httpx). Der Audit-Endpoint liest `verify_tls` direkt (`bool(ws.get("verify_tls", 1))`, nicht über `_verify_for`). — `registry.py:20,46,84`; `routes/federation.py:126`
- Toggle im Frontend: Expand-Zeile in `WorkstationCard` → `federationApi.update(ws.id, { verify_tls: !ws.verify_tls })`. — `_WorkstationCard.tsx:156`
- Add-Dialog-Heuristik: URL matcht CGNAT (`100.64.0.0/10`), `.local`, `.tailnet` → bei `verify_tls=true` Amber-Warnung „self-signed wahrscheinlich". Reine UX, ändert nichts am Verhalten. — `_AddDialog.tsx:46`

### Externe Instanzen: Anlegen (transaktionsartig mit Rollback)

1. `NewInstanceDialog` → `externalInstancesApi.create(name, model)` → `POST /api/external-instances`. — `_NewInstanceDialog.tsx:37`
2. `create_instance`: `users.create(name, random_pw, role="user")` → bei Erfolg `agent_config.create(external=True, ...)` (bei Fehler User löschen) → `api_keys.create(name=f"{name}-hook")` (bei Fehler Agent + User löschen). — `agents/external_instances.py:14`
3. Response `{username, agent_id, api_key}` → Dialog zeigt kopierbaren `HH_*`-Env-Block.
4. **Liste** wird **abgeleitet**, nicht gespeichert: jeder Agent mit `external=True` → key_count/session_count/last_activity zusammengerechnet. — `agents/external_instances.py:35`

### Streaming: Scrape → Auswahl → Download (Klick → Plex-Datei)

1. Credentials speichern: `CredentialsForm` → `PUT /api/streaming/credentials`; PW via `encrypt(password, settings.data_dir)`. Leeres PW behält altes (`existing["password_enc"]`). — `streaming.py:49`
2. Scrape: `StreamingPage.handleScrape` → `POST /api/streaming/scrape`; PW `decrypt`; `scraper.scrape_series`. — `streaming.py:66`
3. `scrape_series`: Playwright-Chromium (headless, Desktop-UA) → `_login` (WP-Login) → Serien-URL mit `wait_until="load"` → Zugriffs-Check (`kein-zugriff`/`restricted` in URL → `ValueError`) → `page.evaluate(window.episodes_data)` **oder** Regex-Fallback aus HTML → Titel/Staffel/Episoden. Keine Episoden → `ValueError` → Route 422. — `scraper.py:21`
4. Frontend wählt initial alle Episoden vor; `EpisodeList`-Checkboxen toggeln `selected`-Set.
5. Download: `handleDownload` baut `jobs[]` aus `selected` → `POST /api/streaming/download/start`. — `StreamingPage.tsx:60`
6. Route: pro Episode `build_output_path` + `db.create_job` → sammelt `created_ids` → `bg.add_task(_run_all, ids)` (sequenziell). 202 + `job_ids`. — `streaming.py:98`
7. `run_job` (pro Job): Status/Existenz-Check (existiert → `skipped`) → `out.parent.mkdir` → Embed-URL `{_EMBED_BASE}/{lib}/{vid}` → `async with _download_lock` (max 1 gleichzeitig) → erneuter Abbruch-Check → `update_job_status("downloading", 0)` → `asyncio.wait_for(_ytdlp(...), 7200)` → done/error/timeout. — `downloader.py:37`
8. `_ytdlp`: subprocess `yt-dlp --format bestvideo+bestaudio/best --merge-output-format mkv ...`; liest stdout zeilenweise, `_PROGRESS_RE` parsed `%` (gecappt auf 99) → `update_job_status("downloading", pct)`. Exit≠0 → `RuntimeError`. — `downloader.py:85`
9. Frontend pollt `GET /api/streaming/jobs` alle 2 s → Progress-Bar + Status-Icon. — `StreamingPage.tsx:33`
10. Cancel: `POST .../cancel` → `cancel_job` → Task `.cancel()` + Status `error="Abgebrochen"`. — `downloader.py:28`

### Zustandsmaschine Streaming-Job

`pending` → `downloading` → `done` | `error` | `skipped`
- `pending`: nach `create_job` (DB-Default). — `019_streaming.sql:24`
- `downloading`: in `run_job` (nach Lock). progress 0→99 live, 100 bei done.
- `done`: Erfolg. `skipped`: Output existierte bereits. `error`: Exception/Timeout/Abbruch (`out.unlink` bei Timeout/Error).
- `CANCELLABLE = {pending, downloading}`, `DELETABLE = {done, error, skipped}` (Frontend-UI-Gating). — `_JobList.tsx:21,22`

---

## WO

### Backend Federation
- Registry: `core/src/hydrahive/federation/registry.py`
  - `_verify_for` `:20`, `fetch_card` `:31`, `remote_chat` `:61`, `refresh_all_cards` `:93` (tot), `_card_cache` `:16`, `_CACHE_TTL` `:17`
- Package-Init: `core/src/hydrahive/federation/__init__.py:2`
- DB: `core/src/hydrahive/db/federation.py`
  - `_row` `:11`, `list_workstations` `:27`, `get_workstation` `:35`, `get_by_name` `:43`, `create_workstation` `:52`, `update_workstation` `:75`, `update_card` `:96`, `delete_workstation` `:105`
- Route: `core/src/hydrahive/api/routes/federation.py`
  - `router` `:16`, `WorkstationCreate` `:22`, `WorkstationUpdate` `:32`, `_strip_token` `:40`, `list_workstations` `:49`, `create_workstation` `:56`, `update_workstation` `:71`, `delete_workstation` `:85`, `refresh_card` `:94`, `get_audit` `:111`, `ClientCreate` `:145`, `list_clients` `:149`, `create_client` `:156`, `delete_client` `:209`
- Tool-Routing: `core/src/hydrahive/tools/ask_agent.py` — `_execute` `:81`, Federation-Branch `:90`, `_execute_federated` `:217`

### Backend Externe Instanzen
- Orchestrierung: `core/src/hydrahive/agents/external_instances.py`
  - `create_instance` `:14`, `list_instances` `:35`, `_owner_is_dedicated` `:55`, `delete_instance` `:66`, `rotate_key` `:79`
- Route: `core/src/hydrahive/api/routes/external_instances.py`
  - `router` `:10`, `InstanceCreate` `:13`, `list` `:18`, `create` `:23`, `delete` `:33`, `rotate-key` `:40`
- Abhängigkeiten: `agents/_config_utils.py` (`list_all` `:57`, `list_by_owner` `:71`), `agents/_defaults.py` (`DEFAULT_MAX_TOKENS=16384` `:65`), `agents/config.py` (`create(external=...)` `:21/:38/:59`)

### Backend Streaming
- Scraper: `core/src/hydrahive/streaming/scraper.py`
  - `scrape_series` `:21`, `_login` `:99`, `_parse_title` `:127`, `_parse_season` `:135`, `_parse_episodes` `:143`, `_episodes_from_dict` `:174`, `_extract_ep_number` `:191`, Regexe `:10–18`
- Downloader: `core/src/hydrahive/streaming/downloader.py`
  - `cancel_job` `:28`, `run_job` `:37`, `_ytdlp` `:85`, `build_output_path` `:124`, Konstanten `:11/:19/:21`, State `:18/:24/:25`
- DB: `core/src/hydrahive/db/streaming.py`
  - `get_credentials` `:16`, `upsert_credentials` `:25`, `create_job` `:46`, `list_jobs` `:74`, `get_job` `:84`, `update_job_status` `:92`, `delete_job` `:106`, `count_active_jobs` `:115` (tot)
- Route: `core/src/hydrahive/api/routes/streaming.py`
  - `router` `:17`, `CredentialsIn/Out` `:24/:30`, `get_credentials` `:36`, `save_credentials` `:49`, `ScrapeIn` `:62`, `scrape` `:66`, `JobIn` `:83`, `StartDownloadIn` `:90`, `start_download` `:98`, `list_jobs` `:137`, `delete_job` `:143`, `cancel_job` `:150`
- Crypto: `core/src/hydrahive/credentials/_crypto.py` — `encrypt(plaintext, data_dir)` `:56`, `decrypt(value, data_dir)` `:63`, `_key_path` `:26`, `_load_key` `:30`

### Migrationen
- `core/src/hydrahive/db/migrations/017_federation.sql` — `federation_workstations` + Index `idx_federation_ws_enabled`
- `core/src/hydrahive/db/migrations/018_federation_verify_tls.sql` — `ALTER ... ADD COLUMN verify_tls INTEGER NOT NULL DEFAULT 1`
- `core/src/hydrahive/db/migrations/019_streaming.sql` — `streaming_credentials` + `streaming_jobs`

### Auth / Tailscale / Settings (Abhängigkeiten)
- `core/src/hydrahive/api/middleware/auth.py` — `require_auth` `:36`, `require_admin` `:53`, API-Key-Pfad (`hhk_`) `:46`
- `core/src/hydrahive/api/middleware/api_keys.py` — `PREFIX="hhk_"` `:23`, `_KEY_ID_HEX_LEN=16` `:25`, `create` `:59`, `verify` `:79`, `list_keys` `:111`, `delete` `:121`
- `core/src/hydrahive/tailscale/status.py` — `get_status` `:40` (`connected`/`ip`/`hostname`/`dns_name`)
- `core/src/hydrahive/tailscale/admin.py` — `create_invite` `:94` (`auth_key` `:128`)
- `core/src/hydrahive/settings/_services.py` — `agentlink_url` `:47`, `agentlink_ws_url` `:53`, `agentlink_agent_id` `:66`, `agentlink_handoff_timeout` `:81`
- Router-Registrierung: `core/src/hydrahive/api/main.py:105,149,150`

### Frontend
- Federation: `frontend/src/features/federation/` — `FederationPage.tsx`, `_WorkstationCard.tsx`, `_AddDialog.tsx`, `_ClientConnectionsSection.tsx`, `_NewClientDialog.tsx`, `_DataminingInstancesSection.tsx`, `_NewInstanceDialog.tsx`, `api.ts`, `types.ts`
- Streaming: `frontend/src/features/streaming/` — `StreamingPage.tsx`, `_CredentialsForm.tsx`, `_EpisodeList.tsx`, `_JobList.tsx`, `api.ts`, `types.ts`
- Routing/Nav: `frontend/src/App.tsx:33,34,79,80`, `frontend/src/shared/nav-config.ts:47,48`
- Farben: `frontend/src/shared/colors.ts` (DOMAIN_COLORS `:15`, `colorFor` `:37`, `rgbFor` `:55`) — **kein** Eintrag für `/federation`/`/streaming`
- i18n: `frontend/src/i18n/index.ts:80,81,91,92,108`; Locales `locales/{de,en}/federation.json`, `locales/{de,en}/streaming.json`

### Tests
- `core/tests/test_federation_verify_tls.py` — Default-True, Toggle, Allow-List-Ignore, API-Roundtrip
- `core/tests/test_external_instances.py` + `core/tests/test_external_instances_api.py`
- **Kein** Test für `streaming` (Scraper/Downloader/Route ungetestet)

---

## WARUM

### Federation TLS-Verify pro Peer (zentrale Design-Entscheidung)
- Problem: Frisch `--tls-auto`'te ProjektX-Peers servieren ein self-signed Cert für `CN=localhost`. Über die Tailscale-IP (`100.x.y.z`) lehnt httpx' Default-Cert-Verify die Kette ab. Lösung: **pro-Row**-Flag `verify_tls`, sicherer Default `1` (prüfen). LAN/Tailnet-Peer → auf 0; Public-CA-Peer → 1. — Begründung steht in `018_federation_verify_tls.sql:1–8`.
- Invariante: `verify_tls=1` heißt „**do** verify". Der DB-Wert ist int, das API/Frontend bool. `_strip_token` + `_row` normalisieren **immer** auf bool/int, damit kein None durchrutscht. Wer das anfasst, muss bool↔int-Coercion in **allen drei** Schichten (DB `update_workstation:84`, Route `_strip_token:45`, Registry `_verify_for:28`) konsistent halten.
- Gotcha: `get_audit` nutzt **nicht** `_verify_for`, sondern inline `bool(ws.get("verify_tls", 1))` (`routes/federation.py:126`). Verhalten ist identisch, aber wenn jemand `_verify_for` ändert (z.B. globale Override-Logik), bleibt der Audit-Pfad zurück → Drift-Falle.

### Federation ist Client-only — HH2 ist **kein** A2A-Server
- ⚠️ Wichtigste nicht-offensichtliche Invariante: HH2 **konsumiert** `/.well-known/agent.json`, `/remote/chat` und `/remote/audit` von **entfernten** ProjektX-Peers. HH2 selbst **serviert keine** dieser Endpoints (Grep im Core findet sie nur als httpx-Targets in `registry.py`, nicht als FastAPI-Route). Die A2A-Server-Seite lebt in ProjektX (separates Repo). Wer „warum antwortet meine Workstation nicht" debuggt, muss auf der **Gegenseite** suchen, nicht in HH2.
- Der Token (`PROJEKTX_REMOTE_TOKEN` peer-seitig) wird als `Bearer` mitgeschickt; `X-Caller: hydrahive2` identifiziert den Anrufer im Remote-Audit-Log.

### Token-Hygiene
- `_strip_token` entfernt `token` **und** `card_json` aus jeder API-Antwort und ersetzt durch `has_token: bool`. Invariante: das Frontend sieht **nie** den Workstation-Token. Test `test_api_create_workstation_with_verify_tls` prüft explizit `"token" not in data`.

### Externe Instanzen: keine Tabelle, abgeleiteter Zustand
- Design: „external-Marker am Agent IST die Einheit" (`agents/external_instances.py:1`). Keine eigene Tabelle — `list_instances` rechnet alles aus `external=True`-Agenten zusammen. Vorteil: keine Schema-Drift, kein Sync-Problem. Preis: jeder List-Call macht N×token_stats + N×session-Lookup (N+1, bei vielen Instanzen teuer).
- Rollback-Reihenfolge bei `create_instance`: User → Agent → Key, mit umgekehrtem Cleanup. Wer die Reihenfolge ändert, riskiert verwaiste User/Agenten.
- `_owner_is_dedicated` schützt davor, beim Löschen einer Instanz den **admin** oder einen **geteilten** User mitzulöschen. Muss **nach** `agent_config.delete` aufgerufen werden, damit der gelöschte Agent nicht mehr zählt (`agents/external_instances.py:59`). Reihenfolge ist load-bearing.
- `rotate_key`: erst neuen Key, dann alte löschen — sonst stünde die Instanz bei einem Fehler ohne Key da (ausgesperrt). — `agents/external_instances.py:86`
- Verbindung zur Memory-Notiz: `agent_id == server-uuid` beim joshua/datamining-Setup; der hier generierte `HH_AGENT_ID` (Copy-Button) ist genau diese UUID.

### Streaming: Subprocess-Sicherheit + Concurrency
- `_ytdlp` nutzt `create_subprocess_exec` (kein Shell) — explizit kommentiert „keine Shell, kein Injection-Risiko". URL/Output kommen aus DB (UUID-Werte + sanitized Path). Wer auf `shell=True` umstellt, öffnet Injection.
- `_download_lock` (process-wide `asyncio.Lock`) ⇒ **max 1 Download gleichzeitig**. Jobs queuen natürlich über die sequenzielle `_run_all`-Schleife (`bg.add_task`). Wer parallel will, muss Lock-Strategie + Output-Pfad-Kollisionen überdenken.
- Progress wird auf 99 gecappt während des Laufs (`min(99, ...)`), 100 erst bei `done` — damit die UI nicht vorzeitig „fertig" zeigt.
- 2h-Timeout (`_DOWNLOAD_TIMEOUT`) + `out.unlink()` bei Timeout/Error verhindert Teil-Dateien in Plex.
- `_YTDLP_BIN` = yt-dlp im **selben venv-bin** wie der laufende Python (`Path(sys.executable).parent`). Annahme: `pip install yt-dlp` lief im HH2-venv. Bricht, wenn yt-dlp global statt im venv installiert ist.

### Streaming: Credential-Verschlüsselung
- PW wird per Fernet-artigem `encrypt(password, settings.data_dir)` gespeichert (Master-Key in `data_dir/credentials/.master_key`, 0600). Leeres PW im PUT behält das alte — verhindert versehentliches Löschen beim Bearbeiten anderer Felder. `get_credentials` gibt **nie** Klartext zurück, nur `has_password`.

### Verlorene Card-Refresh-Automatik
- `refresh_all_cards()` ist die offensichtlich gedachte Hintergrund-Refresh-Funktion (alle enabled Workstations parallel). Sie wird **nirgends** aufgerufen (kein Scheduler, kein lifespan-Hook, kein Cron). Cards werden nur **on demand** beim manuellen Refresh-Klick oder beim ersten `fetch_card` (Cache-Miss) aktualisiert. ⇒ `last_seen`/grüner Dot „rosten" ein, bis jemand klickt.

---

## Datenmodell

### Tabelle `federation_workstations` (017 + 018)
| Spalte | Typ | Default | Notiz |
|---|---|---|---|
| `id` | TEXT PK | — | uuid4 |
| `name` | TEXT NOT NULL | — | @-Adress-Suffix (`persona@name`) |
| `url` | TEXT NOT NULL | — | trailing `/` gestrippt |
| `token` | TEXT NOT NULL | `''` | Bearer für `/remote/*`, nie ans Frontend |
| `enabled` | INTEGER NOT NULL | `1` | |
| `last_seen` | TEXT | NULL | von `update_card` (`strftime`) |
| `card_json` | TEXT | NULL | gecachte A2A-Card |
| `created_at` | TEXT NOT NULL | `strftime(...'now')` | |
| `verify_tls` | INTEGER NOT NULL | `1` | 1=prüfen (sicher); 0 für self-signed |
- Index `idx_federation_ws_enabled` auf `(enabled)`.

### Tabelle `streaming_credentials` (019)
| Spalte | Typ | Default | Notiz |
|---|---|---|---|
| `id` | TEXT PK | `lower(hex(randomblob(8)))` | |
| `user_id` | TEXT NOT NULL | — | |
| `provider` | TEXT NOT NULL | `'ghostflix'` | UNIQUE(user_id, provider) |
| `username` | TEXT NOT NULL | — | Ghostflix-Login (E-Mail) |
| `password_enc` | TEXT NOT NULL | — | Fernet-verschlüsselt |
| `plex_path` | TEXT NOT NULL | `'/media/plex'` | |
| `created_at` | TEXT NOT NULL | `datetime('now')` | |

### Tabelle `streaming_jobs` (019)
| Spalte | Typ | Default | Notiz |
|---|---|---|---|
| `id` | TEXT PK | `lower(hex(randomblob(8)))` | (aber Code setzt `uuid4` in `create_job`) |
| `user_id` | TEXT NOT NULL | — | |
| `provider` | TEXT NOT NULL | `'ghostflix'` | |
| `series_title` | TEXT NOT NULL | — | |
| `series_url` | TEXT NOT NULL | — | |
| `season` | INTEGER NOT NULL | `1` | |
| `episode` | INTEGER NOT NULL | — | |
| `episode_key` | TEXT NOT NULL | — | Scraper-Key |
| `bunny_video_id` | TEXT NOT NULL | — | |
| `bunny_library_id` | TEXT NOT NULL | — | |
| `output_path` | TEXT NOT NULL | — | Plex-Zielpfad (.mkv) |
| `status` | TEXT NOT NULL | `'pending'` | pending/downloading/done/error/skipped |
| `progress` | INTEGER NOT NULL | `0` | 0–99 live, 100 done |
| `error` | TEXT | NULL | |
| `created_at` | TEXT NOT NULL | `datetime('now')` | |
| `updated_at` | TEXT NOT NULL | `datetime('now')` | von `update_job_status` |

### „Pseudo-Entität" externe Instanz (keine Tabelle)
Abgeleitet aus `agents`-Row mit `external=true`: `{agent_id, name, username(=owner), key_count, session_count, last_activity}`. Zugehörig: ein dedizierter `users`-Row (Rolle `user`) + ein `api_keys`-Row (`{name}-hook`).

### A2A-Card-Schema (vom Peer geliefert, im Frontend typisiert)
`A2ACard{ name, description, url, version, commit?, protocol, capabilities{a2a,streaming,tools,chat,shell}, agents[{id,name,description?,type}], endpoints? }` — `frontend/src/features/federation/types.ts:16`

### Client-Config-Schema `hh2_client_v1`
`{ schema, name, generated_at, hh2{api_url, api_url_dns, api_key}, agentlink{url, ws_url, agent_id}|null, tailscale{ip, hostname, dns_name, authkey}|null }` — generiert `routes/federation.py:189`, typisiert `types.ts:36`

### Env-Vars / Config-Keys
- `HH_AGENTLINK_URL` → `settings.agentlink_url` (leer ⇒ kein AgentLink-Block in Client-Config; `ask_agent`-WS-Pfad disabled). — `_services.py:47`
- `HH_AGENTLINK_WS_URL` → `agentlink_ws_url` (auto-derived wenn leer). — `_services.py:53`
- `HH_AGENTLINK_AGENT_ID` → `agentlink_agent_id` (Default `hydrahive`). — `_services.py:66`
- `HH_AGENTLINK_HANDOFF_TIMEOUT` → `agentlink_handoff_timeout` (Default 600). — `_services.py:81`
- `HH_HOST`/`HH_PORT` → `settings.host`/`settings.port` (Client-Config-URLs).
- `HH_BASE_URL`/`HH_API_KEY`/`HH_AGENT_ID`/`HH_VERIFY_SSL` — vom `NewInstanceDialog` als Client-Env-Block ausgegeben (peer-seitig konsumiert, nicht in HH2 gelesen).
- Streaming: keine eigenen Env-Vars; nur `settings.data_dir` (für Crypto-Master-Key) + Credentials-Tabelle.
- Peer-seitig (NICHT in HH2): `PROJEKTX_REMOTE_TOKEN` (Bearer für `/remote/*`).
- Konstanten: `_CACHE_TTL=60.0`, `_DOWNLOAD_TIMEOUT=7200`, `DEFAULT_MAX_TOKENS=16384`, `_EMBED_BASE=https://iframe.mediadelivery.net/embed`, `PREFIX="hhk_"`, `_KEY_ID_HEX_LEN=16`.

---

## Offene Enden

### Tote / unverdrahtete Funktionen
- `refresh_all_cards()` (`registry.py:93`) — **nirgends aufgerufen**, kein Scheduler/lifespan/Cron. Cards rosten ein, `last_seen` aktualisiert nur bei manuellem Refresh. Entweder verdrahten (Background-Task im lifespan) oder löschen.
- `count_active_jobs(user_id)` (`db/streaming.py:115`) — **nirgends aufgerufen**. Wirkt wie geplantes Concurrency-/Rate-Limit, das nie gebaut wurde. Tot.

### Fehlende Tests
- **Kein** Test für `streaming` (Scraper, Downloader, Route). Scraper ist fragil (Playwright + Ghostflix-DOM + Regex-Fallbacks) und völlig ungetestet. Downloader-Statusmaschine + Timeout/Cancel ungetestet.

### Drift / Inkonsistenzen
- `get_audit` (`routes/federation.py:126`) dupliziert die Verify-Logik inline statt `_verify_for` zu nutzen → Drift-Risiko, wenn `_verify_for` je erweitert wird.
- `streaming_jobs.id` hat DB-Default `lower(hex(randomblob(8)))` (`019:13`), aber `create_job` setzt explizit `uuid4` (`db/streaming.py:58`). Inkonsistente ID-Formate je nach Insert-Pfad (aktuell immer Code-Pfad, also uuid4 — der DB-Default ist totes Fallback).
- `update_job_status(progress=0)`-Default: ein Statuswechsel ohne explizites `progress` setzt es auf 0 zurück. `cancel_job` und die done/error-Pfade rufen es jeweils mit passendem progress; aber jeder neue Caller, der `progress` vergisst, nullt die Anzeige.
- `DOMAIN_COLORS` (`colors.ts:15`) hat **keinen** Eintrag für `/federation` oder `/streaming` → `colorFor` fällt auf Default `"violet"` zurück. Funktioniert (violet ist das durchgängig genutzte Akzent), ist aber implizit. Die Federation-Komponenten setzen `--c` hart auf `rgbFor("/federation")` (=violet via Fallback), Streaming-Komponenten nutzen `rgbFor("/llm")` (=emerald) — also Streaming-Karten sind grün, obwohl die Nav unter „infrastructure" liegt. Optisch inkonsistent / wirkt nach Copy-Paste vom LLM-Feature.

### Halbfertiges / Fragiles
- Scraper-Zugriffs-Check (`scraper.py:59`) prüft nur URL-Substrings `kein-zugriff`/`restricted`. Andere Sperr-Varianten (HTTP-Status, anderes Redirect) fallen durch → endet in „Keine Episoden gefunden".
- `_login` schluckt Redirect-Timeout still (`except Exception: pass`, `scraper.py:115`) — Login-Fehler werden erst über DOM-Keyword-Heuristik (`incorrect/error/falsch/ungültig`) erkannt, sprachabhängig und brüchig.
- `create_client`/`create_invite` ist best-effort: Tailscale-Authkey-Fehler werden still verschluckt (`except Exception: pass`, `routes/federation.py:176`). Client-Config kommt dann ohne Authkey — Frontend zeigt „Tailscale Admin nicht konfiguriert", was den eigentlichen Fehler (z.B. abgelaufenes Admin-Token) verschleiert.
- `WorkstationCard`-Audit-Rendering castet die Remote-Antwort ungetypt (`as any[]`, `_WorkstationCard.tsx:188`) und greift auf `r.timestamp/r.status/r.path/r.caller/r.error` zu — implizites Schema-Coupling zur ProjektX-Audit-Antwort, kein Typ, kein Validierung.
- Federation-Routing in `ask_agent`: `get_by_name` **oder** `get_workstation` — kein URL-Prefix-Match trotz Kommentar „Workstation by name, ID, or URL-prefix" (`ask_agent.py:227`). Der Kommentar verspricht mehr als der Code liefert.
- `NewInstanceDialog` hat `claude-opus-4-8` als hartkodierten Default-Modellnamen (`_NewInstanceDialog.tsx:27`) — driftet, wenn sich Modell-IDs ändern (vgl. Live-Modelle-SSOT).
