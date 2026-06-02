# System, Dashboard & Admin

Dieses Subsystem deckt vier zusammenhängende, aber getrennte Frontend-Surfaces ab — **Dashboard** (Übersichts-Aggregat), **System-Seite** (Admin-Status & -Aktionen), **Analytics/Token-Audit** (Telemetrie-Drilldown) — plus die zentrale **Settings-Singleton-Schicht** (SSOT für Pfade/Config/Env). Es ist überwiegend ein Read-Aggregator über andere Subsysteme (Sessions, VMs, Container, Agents, LLM-Telemetrie) mit einer kleinen Menge an echten Schreib-/Wirk-Endpunkten (Update, Restart, Voice-Install, Bridge/Samba-Setup, Backup/Restore).

---

## WAS

### Settings-Singleton (`core/src/hydrahive/settings/`)
Ein einziges Singleton `settings` (aggregiert über Mixins). Alle Werte sind `cached_property` und kommen aus `HH_*`-Env-Vars mit Defaults. Einzelne Properties:

**Pfade (`_PathsMixin`)**
- `base_dir` — `HH_BASE_DIR`, default `/opt/hydrahive2`
- `data_dir` — `HH_DATA_DIR`, default `/var/lib/hydrahive2`
- `config_dir` — `HH_CONFIG_DIR`, default `/etc/hydrahive2`
- `agents_dir` — `data_dir/agents`
- `projects_dir` — `data_dir/projects`
- `plugins_dir` — `data_dir/plugins`
- `plugin_hub_cache` — `data_dir/.plugin-cache/hub`
- `plugin_hub_git_url` — `HH_PLUGIN_HUB_GIT_URL`, default GitHub-Plugins-Repo
- `tmp_dir` — `HH_TMP_DIR`, default System-tempdir
- `media_dirs` — `HH_MEDIA_DIRS` (`:`-getrennte absolute Pfade) für `/api/files`
- `oauth_pending_path` — `data_dir/oauth_pending.json`
- `numba_cache_dir` — `HH_NUMBA_CACHE`
- `servable_prefixes` — Tupel `(tmp_dir/, data_dir/)` für File-Serving-Whitelist
- `sessions_db` — `data_dir/sessions.db` (zentrale SQLite-DB)
- `mcp_config` — `config_dir/mcp_servers.json`
- `llm_config` — `config_dir/llm.json`
- `users_config` — `config_dir/users.json`
- `api_keys_config` — `config_dir/api_keys.json`
- `research_apis_config` — `config_dir/research_apis.json`
- `voice_conversations_path` — `data_dir/voice_conversations.json`
- `log_dir` — `HH_LOG_DIR`, default `/var/log`
- `update_log` — `log_dir/hydrahive2-update.log`
- `voice_log` — `log_dir/hydrahive2-voice.log`
- `samba_log_path` — `HH_SAMBA_LOG`
- `bridge_log_path` — `HH_BRIDGE_LOG`
- `ensure_dirs()` — legt data/agents/projects/plugins/config-Verzeichnisse an

**Server/JWT (`_ServerMixin`)**
- `host` — `HH_HOST`, default `127.0.0.1`
- `port` — `HH_PORT`, default `8765`
- `secret_key` — `HH_SECRET_KEY` (raises RuntimeError wenn nicht gesetzt!)
- `jwt_algorithm` — fix `HS256`
- `jwt_expire_minutes` — `HH_JWT_EXPIRE_MINUTES`, default 1440 (24h)
- `update_check_enabled` — `HH_UPDATE_CHECK_ENABLED`, default ON (steuert Background-Update-Check + `update_behind`-Feld)

**AgentLink (`_AgentLinkMixin`)**: `agentlink_url`, `agentlink_ws_url` (abgeleitet aus REST), `agentlink_agent_id` (default `hydrahive`), `agentlink_token`, `agentlink_handoff_timeout` (600s), `agentlink_dashboard_url`

**Communication (`_CommunicationMixin`)**: `pg_mirror_dsn`, `backend_internal_url`, `discord_enabled`, `discord_config_dir`, `whatsapp_enabled`, `whatsapp_data_dir`, `whatsapp_bridge_port` (8767), `whatsapp_bridge_url`, `whatsapp_bridge_secret_file`, `health_api_key`, `health_ingest_user` (default `till`)

**Mail (`_MailMixin`)**: `mail_enabled` (default OFF), `mail_owner_username` (default `admin`), `mail_poll_interval` (60s), `mail_seen_ids`, IMAP-Quartett (`mail_imap_host/port/user/password/folder`), SMTP-Quartett (`mail_smtp_host/port/user/password/use_tls`), `mail_from`

**Infra (`_SambaMixin/_VmsMixin/_ExtensionsMixin/_WebminMixin/_ButlerMixin`)**: `samba_includes_dir`, `samba_user` (default `hh`), `samba_password_file`; `vms_dir` + Sub-Dirs (isos/disks/pids/logs/vnc-tokens), `vms_bridge` (default `br0`); `extensions_manifests_dir`, `extensions_install_dir`; `webmin_url`, `webmin_credential`; `butler_dir`

### Dashboard-Backend (`api/routes/dashboard.py`)
- `GET /api/dashboard` — **Ein-Call-Aggregat**: liefert `health`, `stats` (active_sessions, tokens_today, tool_calls_today, servers_running, servers_total), `recent_sessions` (max 10), `servers` (VMs+Container), `agents`, `version` (commit + update_behind). Role-aware: admin sieht alles, sonst eigene Agents/Sessions.

### Dashboard-Helpers (`api/routes/_dashboard_helpers.py`)
- `today_start_iso()` — UTC-Mitternacht als ISO-String (auch von analytics genutzt)
- `health_check()` — prüft backend (immer ok), agentlink (connected + configured), bridge (`ip -br link show br0`), tailscale (`tailscale status --json` + BackendState-Check)
- `query_user_stats(conn, role, session_ids, today)` — tokens_today (SUM messages.token_count assistant) + tool_calls_today; admin-weit oder per-Session-IN-Filter

### Analytics-Backend (`api/routes/analytics.py`)
- `GET /api/analytics/overview` — today + last_7d Aggregate (input/output/cache_read/cache_creation tokens, cost_micros, llm_calls, tool_calls, tool_errors, compactions, errors, sessions), `top_cost_sessions` (5 teuerste 7d), `by_model` (aus llm_calls 7d). Role-aware via user_id-Filter.
- `GET /api/analytics/session/{session_id}` — Voll-Drilldown: session-Meta, metrics (aus session_metrics-VIEW), llm_calls, tool_calls (args/result auf 500 Zeichen Preview gekürzt), compactions, errors. 404 wenn nicht da, 403 wenn fremde Session und nicht admin.

### System-Backend (`api/routes/system.py`)
- `GET /api/system/info` — version (`2.0.0`), started_at, uptime_seconds, python-Version, platform, data_dir, config_dir, db_path, db_size_bytes
- `GET /api/system/stats` — agents (total + by_type), projects (total + active), sessions (total + active), messages (total + compactions), tool_calls (total/success/error/success_rate)
- `GET /api/system/health` — Liste der 4 Health-Checks (db, llm, workspaces, disk)
- `set_start_time()` — setzt Modul-Globale `_start_time` (von lifespan aufgerufen)

### System-Checks (`api/routes/_system_checks.py`)
- `count_agents()` — iteriert `agents_dir`, liest `config.json`, gruppiert nach `type`
- `count_projects()` — iteriert `data_dir/projects`, zählt total + active
- `check_db_writable()` — `SELECT 1`
- `check_llm_configured()` — prüft llm.json: default_model + providers
- `check_workspace_dir()` — `data_dir/workspaces` existiert + W_OK
- `check_disk()` — `shutil.disk_usage`, ok wenn free_pct > 5%

### System-Admin-Backend (`api/routes/system_admin.py`) — alle `require_admin`
- `GET /api/system/check-update` — On-Demand-Refresh von commit + update_behind
- `POST /api/system/update` — schreibt `.update_request`-Trigger (Cooldown 300s)
- `POST /api/system/restart` — schreibt `.restart_request`-Trigger (Cooldown 60s)
- `POST /api/system/install-voice` — schreibt `.voice_install_request`-Trigger
- `GET /api/system/install-voice/log?tail=N` — liest voice_log (tail cap 1000)
- `GET /api/system/update/log?tail=N` — liest update_log (tail cap 1000)

### System-Bridge-Backend (`api/routes/system_bridge.py`)
- `GET /api/system/bridge/status` — `ip -br link show br0` → installed/state/ip (require_auth)
- `POST /api/system/bridge/setup` — schreibt `.bridge_setup_request` (require_admin)
- `GET /api/system/bridge/log?tail=N` — liest bridge_log (require_admin)

### System-Samba-Backend (`api/routes/system_samba.py`) — alle `require_admin`
- `GET /api/system/samba/status` — `samba_status()` + Passwort (aus samba_password_file, nur wenn password_set)
- `POST /api/system/samba/setup` — generiert Passwort (`secrets.token_urlsafe(18)`, chmod 600) + schreibt `.samba_setup_request`
- `GET /api/system/samba/log?tail=N`

### Backup-Backend (`api/routes/backup.py`) — alle `require_admin`
- `POST /api/admin/backup` — erzeugt .tar.gz in temp-Dir, liefert als FileResponse, löscht temp via BackgroundTask
- `POST /api/admin/restore` — Multipart-Upload (cap 2 GiB), Pre-Validate, Auto-Rollback, atomic Replace, Restart-Trigger

### Version-Modul (`api/version.py`)
- `_detect_git_commit()` — `git rev-parse HEAD`, fix auf 8 Stellen gekürzt
- `_remote_url_https()` — origin-URL, SSH→HTTPS umgebogen
- `_check_update_behind()` — `git ls-remote` vs lokaler HEAD → 0/1/None
- `update_check_loop()` — Background-Task, alle 1800s (30min) refresh
- `refresh_update_status()` — On-Demand
- `current_status()` — gibt gecachte (commit, behind) zurück
- `GET /api/health` (in main.py) — status/version/commit/update_behind (unauthenticated)

### MiniMax-Usage (`llm/_minimax_usage.py` + `api/routes/llm.py`)
- `GET /api/llm/minimax/usage` — pro-Modell Quota (require_auth, auch non-admin)
- `fetch_usage()` — 30s-In-Module-Cache, ruft `api.minimax.io/v1/token_plan/remains`
- `_classify()` — Modell→Kategorie (m2→text/5h, hailuo→video/daily, speech→tts, music, image)
- `_normalize_model()` — interval/weekly total/used/pct + reset_in_s

### Frontend — Dashboard (`features/dashboard/`)
- `DashboardPage.tsx` — Hauptseite, Auto-Refresh 30s, rendert: UpdateBanner (conditional), HealthStrip, StatsRow, TokenAuditCard, TailscaleCard + AgentLinkCard, MinimaxUsageCard, RecentSessions + AgentsList, ServersOverview; EmptyState beim Laden
- `_StatsRow.tsx` — 4 Kacheln (active_sessions, tokens_today, tool_calls_today, servers_running)
- `_HealthStrip.tsx` — 4 Pills (Backend/AgentLink/Bridge/Tailscale), state ok/warn/off, verlinkt nach `/system`
- `_TokenAuditCard.tsx` — eigener 30s-Poll von `/analytics/overview`; 4 Tiles (Heute Tokens, Heute Kosten, Cache-Hit 7d, Heute Fehler) + Teuerste Sessions + Nach Modell
- `_UpdateBanner.tsx` — Amber-Banner bei update_behind>0, Admin-Link nach `/system`
- `_RecentSessions.tsx` — letzte Sessions mit Relativzeit, verlinkt `/chat?session=`
- `_AgentsList.tsx` — Agents gruppiert nach master/project/specialist
- `_ServersOverview.tsx` — VM/Container-Grid mit State-Dot, verlinkt `/vms/:id` bzw `/containers/:id`
- `api.ts` — `dashboardApi.summary()`, `analyticsApi.overview()`, alle Interfaces

### Frontend — System (`features/system/`)
- `SystemPage.tsx` — Auto-Refresh 10s, Voice-/Restart-Buttons (admin), HealthBar, 8 StatCards, Pfad-Box, AgentLink/Tailscale/Bridge/Samba/Backup-Cards (Infra-Cards admin-only)
- `HealthBar.tsx` — rendert die 4 checks aus `/system/health` mit i18n via name_code/detail_code
- `StatCard.tsx` — generische Kachel mit Glow
- `_systemHelpers.tsx` — PathRow, formatBytes, formatUptime
- `BridgeCard.tsx` — Status + Setup-Flow (confirm→running→done/failed), Log-Poll 1.5s, 180s-Timeout-Loop
- `SambaCard.tsx` — Status + Setup, Passwort-Anzeige (show/copy), 300s-Timeout
- `BackupCard.tsx` — Download + Restore (file picker → BackupRestoreModal)
- `BackupRestoreModal.tsx` — Restore-States idle/confirm/uploading/waiting/done/failed
- `VoiceInstallModal.tsx` + `useVoiceInstall.ts` — Install-Flow, pollt voice_log auf "Voice Interface bereit"
- `MinimaxUsageCard.tsx` — Quota-Bars pro Modell, 30s-Poll, return null bei no_api_key
- `api.ts` — `systemApi` (info/stats/health/installVoice/voiceLog/bridge*/samba*/downloadBackup/restoreBackup)
- (weitere: AgentLinkCard, TailscaleCard + Tailscale-Subkomponenten — gehören primär ins AgentLink/Netz-Subsystem, hier nur eingebunden)

### Frontend — Analytics (`features/analytics/`)
- `SessionDetailPage.tsx` — Route `/analytics/session/:sid`, MetricsRow (12 Kacheln) + Tabellen (LlmCalls/ToolCalls/Compactions/Errors)
- `api.ts` — `analyticsApi.sessionDetail()` + LlmCallRow/ToolCallRow/CompactionRow/ErrorRow/SessionDetail-Typen

### Frontend — Shared (System-relevant)
- `shared/useRestart.ts` — Restart-State-Maschine, pollt `/api/health` (down→up-Erkennung, 60s-Timeout)
- `shared/RestartModal.tsx` — confirm/starting/running/done/failed

---

## WIE

### Dashboard-Page-Load (Klick → Antwort)
1. `DashboardPage` mountet → `dashboardApi.summary()` → `GET /api/dashboard`.
2. `summary()` (dashboard.py:22) liest auth (username, role). Bei admin `agent_config.list_all()`, sonst `list_by_owner(username)`.
3. Sessions via `sessions_db.list_for_user(username, limit=200)`; active = Count status=="active".
4. **Eine** DB-Connection `with db()`: `query_user_stats()` rechnet tokens_today (SUM `messages.token_count` WHERE role='assistant' + created_at>=heute) und tool_calls_today. Admin = global, sonst per `session_id IN (...)`.
5. VMs (`vms_db.list_vms`) + Container (`containers_db.list_`), owner-gefiltert außer admin. servers_running = Summe actual_state=="running".
6. recent_sessions: erste 10 Sessions, je Agent-Name/Type nachgeschlagen.
7. `current_status()` (version.py) liefert gecachten commit + update_behind.
8. Antwort als ein JSON-Blob → Frontend setzt `data`, rendert Sektionen, Auto-Reload alle 30s.
9. Frontend zeigt UpdateBanner nur wenn `version.update_behind > 0`.

### TokenAuditCard (separater Datenpfad!)
- Lädt **nicht** aus dem Dashboard-Summary, sondern eigenständig `GET /api/analytics/overview` (eigener 30s-Poll).
- `overview()` (analytics.py:26) baut role-abhängige WHERE-Klauseln (qualifiziert `m.user_id` für JOIN, unqualifiziert sonst), führt 4 Queries aus: today-Aggregat, 7d-Aggregat, Top-5-Cost-Sessions (JOIN sessions), by_model (direkt aus `llm_calls` GROUP BY model).
- Cache-Hit-Ratio wird im Frontend berechnet: `cache_read / (input + cache_read + cache_creation)` — Output zählt nicht.

### Session-Detail-Drilldown
1. Klick auf teuerste Session in TokenAuditCard → `Link to /analytics/session/${session_id}`.
2. `SessionDetailPage` liest `:sid` → `analyticsApi.sessionDetail(sid)` → `GET /api/analytics/session/{session_id}`.
3. Backend (analytics.py:135) lädt Session, prüft Ownership (403 bei fremd + non-admin), liest `session_metrics.for_session()` (VIEW), Agent-Name, dann je-Tabelle `for_session()`-Reader: llm_calls, tool_calls (args/result gekürzt auf 500 Zeichen Preview), compaction_events, errors_log.
4. Frontend rendert MetricsRow + vier Tabellen. Zurück-Link → `/dashboard`, Open-in-Chat → `/werkstatt?session=`.

### System-Page-Load
- `SystemPage` lädt parallel `systemApi.info()/stats()/health()` (`Promise.all`), Auto-Refresh 10s.
- `/system/info` rechnet uptime = `time.time() - _start_time` (Globale, gesetzt von lifespan `set_start_time()` beim Boot).
- `/system/stats` zählt Sessions/Messages/ToolCalls per Direct-SQL + Agent/Project-Counts via Filesystem-Walk.
- `/system/health` ruft die 4 Check-Funktionen, jede gibt name_code/ok/detail(_code)/params zurück → Frontend i18n.

### Trigger-File-Pattern (Update/Restart/Voice/Bridge/Samba)
**Kern-Mechanismus**: Der API-Prozess läuft *nicht* als root und kann nicht selbst updaten/restarten. Stattdessen:
1. Endpoint schreibt eine Trigger-Datei in `data_dir` (z.B. `.update_request` mit Unix-Timestamp).
2. Ein **systemd-Path-Watcher** (außerhalb dieses Codes, im Installer) erkennt den Write und startet einen root-Service, der das jeweilige Script (`installer/update.sh`, `setup-bridge.sh`, `55-voice.sh`, …) ausführt.
3. Endpoint antwortet sofort `{"started": True}`.
4. Frontend pollt einen Status-/Log-Endpoint (1.5–3s) bis Fertig-Marker oder Timeout.

**Cooldowns**: Update 300s, Restart 60s — Modul-Globale `_last_*_trigger` verhindern Click-Spam → parallele Script-Runs (jeder Write triggert den Path-Watcher).

### Backup-Erzeugung
1. `POST /api/admin/backup` → `create_system_archive(temp_dir)`.
2. SQLite via `sqlite3.connect().backup()` in temp-File (WAL-safe, atomic).
3. tar.gz: Manifest zuerst, dann DB (`db/sessions.db`), data-Subdirs (agents/projects/plugins/whatsapp), config-Dir. Exclude-Filter überspringt VMs/Cache/Trigger/tls/Rollback-Backups. Unlesbare Dateien → `skipped.json` statt Abbruch.
4. FileResponse mit Content-Length → Browser-Progress. Temp via BackgroundTask gelöscht.

### Backup-Restore (atomic + Rollback)
1. `POST /api/admin/restore` → `stream_upload_capped` (chunked, 2 GiB cap) → `restore_system_archive`.
2. `validate_archive`: Manifest lesen (version==1, kind==system), DB-Integrität via `PRAGMA integrity_check` *vor* jedem Live-Eingriff.
3. **Auto-Rollback**: aktueller Stand wird als `.backup-rollback-<ts>.tar.gz` gesichert.
4. Extract in temp mit `filter="data"` (lehnt eskapierende Symlinks/Hardlinks/Device-Nodes/setuid ab — #182).
5. `enforce_archive_limits`: Bomben-Schutz (8 GiB entpackt, 100k Member) *vor* extractall.
6. Verzeichnis-für-Verzeichnis `_atomic_replace_dir` (alt→.old-restore, neu→live, alt löschen), dann DB atomic `replace`.
7. Restart-Trigger geschrieben → systemd-Watcher. Antwort kommt *vor* dem Restart; Frontend pollt `/api/health` bis Backend wieder antwortet.

### Update-Check-Zustandsmaschine
- Boot: `update_check_loop()` als asyncio-Task gestartet (nur wenn `update_check_enabled`).
- Loop: alle 30min `_detect_git_commit()` + `_check_update_behind()` (`git ls-remote` gegen origin-HTTPS).
- `current_status()` liefert gecachten Stand für `/api/health` und `/api/dashboard`.
- On-Demand: `GET /api/system/check-update` → `refresh_update_status()` (sofortiger frischer Stand).

---

## WO

**Settings**
- `core/src/hydrahive/settings/settings.py:30` — `Settings`-Aggregat-Klasse, `settings`-Singleton (`:46`)
- `core/src/hydrahive/settings/_paths.py:14` — `_PathsMixin`; `ensure_dirs` `:130`; `sessions_db` `:79`; `servable_prefixes` `:73`
- `core/src/hydrahive/settings/_services.py:9` — `_ServerMixin`; `secret_key` `:19` (raises!); `update_check_enabled` `:34`; `_AgentLinkMixin` `:45`; `_CommunicationMixin` `:91`
- `core/src/hydrahive/settings/_infra.py:9` — Samba/VMs/Extensions/Webmin/Butler-Mixins
- `core/src/hydrahive/settings/_mail.py:18` — `_MailMixin`
- `core/src/hydrahive/settings/__init__.py:1` — re-export `settings`

**Dashboard**
- `core/src/hydrahive/api/routes/dashboard.py:22` — `summary()`
- `core/src/hydrahive/api/routes/_dashboard_helpers.py:12` — `today_start_iso`; `health_check` `:18`; `query_user_stats` `:52`

**Analytics**
- `core/src/hydrahive/api/routes/analytics.py:26` — `overview()`; `session_detail()` `:135`; `_seven_days_ago_iso` `:21`
- `core/src/hydrahive/db/session_metrics.py:11` — `for_session`; `for_agent` `:21`; `for_user` `:34`; `top_cost` `:47`; `daily_rollup` `:69`; `totals_for_agent` `:101`

**System**
- `core/src/hydrahive/api/routes/system.py:35` — `info`; `stats` `:52`; `health` `:88`; `set_start_time` `:30`; `_start_time` `:27`
- `core/src/hydrahive/api/routes/_system_checks.py:12` — `count_agents`; `count_projects` `:31`; `check_db_writable` `:50`; `check_llm_configured` `:59`; `check_workspace_dir` `:79`; `check_disk` `:86`

**System-Admin / Bridge / Samba**
- `core/src/hydrahive/api/routes/system_admin.py:46` — `trigger_update` (Cooldown `:42`); `trigger_restart` `:76`; `trigger_voice_install` `:100`; `voice_log` `:113`; `update_log` `:126`; `check_update` `:35`; Trigger-Pfade `:26-32`; `_installer_path` `:19`
- `core/src/hydrahive/api/routes/system_bridge.py:27` — `bridge_status`; `bridge_setup` `:50`; `bridge_log` `:57`; TRIGGER `:23`
- `core/src/hydrahive/api/routes/system_samba.py:27` — `status`; `setup` `:39`; `log_` `:50`; TRIGGER `:23`

**Backup**
- `core/src/hydrahive/api/routes/backup.py:31` — `create_backup`; `restore_backup` `:54`
- `core/src/hydrahive/backup/archive.py:72` — `create_system_archive`; `_checkpoint_db_to_tempfile` `:29`; `_add_dir` `:42`
- `core/src/hydrahive/backup/restore.py:31` — `restore_system_archive`; `_create_rollback_backup` `:65`; `_atomic_replace_dir` `:75`; `_trigger_restart` `:97`
- `core/src/hydrahive/backup/validate.py:27` — `validate_archive`; `_check_sqlite_in_tar` `:68`
- `core/src/hydrahive/backup/_limits.py:26` — `stream_upload_capped`; `enforce_archive_limits` `:41`; Caps `:12-14`
- `core/src/hydrahive/backup/_paths.py:16` — `data_subdirs`; `EXCLUDE_PATTERNS` `:41`; `EXCLUDE_DIRS` `:52`; `is_excluded` `:57`

**Version / Health / Routing**
- `core/src/hydrahive/api/version.py:23` — `_detect_git_commit`; `_check_update_behind` `:58`; `update_check_loop` `:88`; `refresh_update_status` `:100`; `current_status` `:108`; `_COMMIT_LEN=8` `:20`
- `core/src/hydrahive/api/main.py:165` — `GET /api/health`; Router-Includes `:99-153`; CORS `:91`; `_DOCS_ENABLED` `:74`; `run()` `:176`
- `core/src/hydrahive/api/lifespan.py:121` — `set_start_time()`; `update_check_loop`-Task `:124`
- `core/src/hydrahive/api/middleware/auth.py:36` — `require_auth`; `require_admin` `:53`; `create_token` `:18`

**MiniMax**
- `core/src/hydrahive/llm/_minimax_usage.py:79` — `fetch_usage`; `_classify` `:35`; `_normalize_model` `:48`; `_MODEL_CATEGORIES` `:26`; Cache `:20`
- `core/src/hydrahive/api/routes/llm.py:113` — `minimax_usage` Route

**DB-Schema (Migrations)**
- `core/src/hydrahive/db/migrations/010_llm_calls.sql` — `llm_calls`-Tabelle
- `core/src/hydrahive/db/migrations/011_compaction_events.sql` — `compaction_events`
- `core/src/hydrahive/db/migrations/012_tool_calls_telemetry.sql` — `tool_calls`-ALTERs
- `core/src/hydrahive/db/migrations/013_errors_log.sql` — `errors_log`
- `core/src/hydrahive/db/migrations/014_session_metrics.sql:6` — `session_metrics`-VIEW
- `core/src/hydrahive/db/migrations/001_initial.sql:18` — `messages` (token_count); `tool_calls` `:30`

**Frontend**
- `frontend/src/features/dashboard/DashboardPage.tsx:19`; REFRESH_MS `:17`
- `frontend/src/features/dashboard/_StatsRow.tsx:11`; `_HealthStrip.tsx:16`; `_TokenAuditCard.tsx:10`; `_UpdateBanner.tsx:10`; `_RecentSessions.tsx:14`; `_AgentsList.tsx:19`; `_ServersOverview.tsx:12`
- `frontend/src/features/dashboard/api.ts:55` — `dashboardApi`; `analyticsApi` `:105`
- `frontend/src/features/system/SystemPage.tsx:26`; REFRESH_MS `:24`
- `frontend/src/features/system/api.ts:38` — `systemApi`; downloadBackup `:56`; restoreBackup `:74`
- `frontend/src/features/system/HealthBar.tsx:5`; `StatCard.tsx:13`; `_systemHelpers.tsx:3`
- `frontend/src/features/system/BridgeCard.tsx:10`; `SambaCard.tsx:10`; `BackupCard.tsx:9`; `BackupRestoreModal.tsx:8`; `VoiceInstallModal.tsx:17`; `useVoiceInstall.ts:5`; `MinimaxUsageCard.tsx:47`
- `frontend/src/features/analytics/SessionDetailPage.tsx:8`; `api.ts:100`
- `frontend/src/shared/useRestart.ts:5`; `shared/RestartModal.tsx`
- `frontend/src/App.tsx:65` — `/dashboard`; `/analytics/session/:sid` `:67`; `/system` `:88`

---

## WARUM

**Dashboard ist ein Aggregator, kein Owner.** Der ganze Sinn von `GET /api/dashboard` ist, 5+ Round-Trips beim Page-Load zu vermeiden (Stats/Health/Sessions/Servers/Version in einem Call). Er besitzt keinerlei eigene Daten — er liest aus sessions_db, vms_db, containers_db, agent_config, version-Cache. Wer den Endpoint anfasst, fasst implizit fünf andere Subsysteme an.

**TokenAuditCard pollt getrennt — bewusst.** Die Token-Audit-Daten kommen *nicht* aus dem Dashboard-Summary, sondern aus einem eigenen `/analytics/overview`-Poll (eigener 30s-Timer). Grund: Telemetrie-Aggregate (4 Queries inkl. JOIN) sind teurer und sollen den schlanken Summary-Call nicht ausbremsen. Folge: zwei unabhängige 30s-Timer auf dem Dashboard.

**`session_metrics` ist eine VIEW, kein Cache.** Migration 014 baut `session_metrics` als always-recompute-VIEW über llm_calls/tool_calls/compaction_events/errors_log mit LEFT JOINs + COALESCE. Vorteil: drift-frei, kein Sync-Code. Gotcha: `tool_calls`/`errors_log` werden nur gezählt wenn `session_id IS NOT NULL` — alte PR2-Zeilen ohne session_id fallen aus dem Aggregat (NULL ≠ 0, "wussten wir damals nicht"). Wenn das langsam wird, ist der dokumentierte Plan: *erst messen, dann* auf inkrementelle Aggregate in `sessions` umstellen — nicht vorzeitig optimieren.

**cost_micros sind Integer.** Kosten in Mikro-Cents (1 Cent = 1000 Micros) als INTEGER, damit `SUM()`-Queries drift-stabil sind (keine Float-Rundungsfehler). Das Frontend formatiert: `micros/100_000 = €`. Wer die Einheit ändert, bricht alle Cost-Anzeigen und alle Aggregate gleichzeitig.

**Trigger-File-Pattern statt direkter Privileg-Eskalation.** Der API-Prozess läuft unprivilegiert (kein root). Update/Restart/Voice/Bridge/Samba können nicht direkt ausgeführt werden — also schreibt der Endpoint nur eine Marker-Datei, und ein root-systemd-Path-Watcher (im Installer, *nicht* in diesem Code) führt das eigentliche Script aus. **Invariante**: die Trigger-Dateien dürfen *nie* ins Backup (sie würden beim Restore einen Phantom-Update/-Restart auslösen) — deshalb stehen sie in `EXCLUDE_PATTERNS`. Wer das Backup-Exclude anfasst, riskiert Restart-Loops nach Restore.

**Cooldowns sind kein Komfort, sondern Schutz.** Jeder Write von `.update_request` triggert den Path-Watcher. Ohne Cooldown (Update 300s, Restart 60s) löst Doppelklick mehrere parallele `update.sh`-Runs aus → Korruption. Die Cooldowns sind Modul-Globale (`_last_*_trigger`) — d.h. prozess-lokal, nicht persistent: nach einem Restart ist der Cooldown vergessen (akzeptiert, weil der Restart selbst die Serialisierung ist).

**`_start_time` ist eine Modul-Globale, gesetzt vom lifespan.** `set_start_time()` wird genau einmal beim Boot aufgerufen (lifespan.py:121). uptime = `time.time() - _start_time`. Bei `0.0` (nie gesetzt) gibt info `max(0.0, ...)` zurück — defensiv gegen Import-Zeit-Reads.

**Commit-Hash fix auf 8 Stellen.** `git rev-parse --short` lässt git die Länge selbst wählen (7 auf dem Server, 8 anderswo) → sah wie eine "fehlende Stelle" aus. Deshalb voller Hash + fix `_COMMIT_LEN=8`. Reiner Anzeige-Fix.

**Update-Check ist die einzige Outbound-Verbindung im Default-Betrieb.** `_check_update_behind` macht `git ls-remote` gegen origin (HTTPS, weil hydrahive-User keine SSH-Keys hat). Für strikt-offline: `HH_UPDATE_CHECK_ENABLED=false` — dann kein Background-Task, kein `update_behind`-Feld mehr (Banner verschwindet).

**Restore-Sicherheit ist mehrstufig.** `filter="data"` beim extractall lehnt eskapierende Symlinks/Device-Nodes/setuid ab (#182, kritisch bei Fremd-Backups). `enforce_archive_limits` schützt vor Dekompressionsbomben *vor* dem Entpacken. `validate_archive` prüft DB-Integrität *vor* jedem Live-Eingriff. Auto-Rollback sichert den alten Stand. Reihenfolge ist Pflicht: validate → rollback → extract → replace → restart.

**Role-Awareness ist überall dupliziert.** dashboard.summary, analytics.overview und analytics.session_detail bauen jeweils eigene `role == "admin"`-Verzweigungen mit eigenen WHERE-Klauseln. analytics.overview hat sogar *zwei* WHERE-Varianten (`where_user` qualifiziert für JOIN, `where_user_unqualified` für Single-Table) weil `user_id` in session_metrics *und* sessions vorkommt — sonst „ambiguous column". Wer Cost-Queries umbaut, muss beide Varianten anfassen.

**MiniMax-Usage hat eigenen Cache (30s).** Verhindert API-Spam beim Dashboard-Polling. Frontend rendert die Card *nur* wenn ein Key da ist (`return null` bei `reason === "no_api_key"`). Auch für non-admin sichtbar (nur Quota-Info).

---

## Datenmodell

### Tabellen / Views (SQLite, sessions.db)
| Objekt | Migration | Zweck |
|---|---|---|
| `messages` (token_count, role, created_at) | 001 | Quelle für dashboard tokens_today |
| `tool_calls` (+ session_id/agent_id/iteration/sizes/error_* ab 012) | 001 + 012 | Tool-Telemetrie |
| `llm_calls` | 010 | Pro-LLM-Call: provider/model/temperature/max_tokens/reasoning_effort, prompt/completion/cache_read/cache_creation_tokens, stop_reason, ttft_ms/total_ms, cost_micros, turn_in_session |
| `compaction_events` | 011 | Pro-Compaction: triggered_by, threshold_pct, skipped/skip_reason, messages_*, tokens_before/after, cut_*, summary_*, duration_ms, error |
| `errors_log` | 013 | Zentrale Fehler: source, severity, error_type/message, traceback, context(JSON) |
| `session_metrics` (VIEW) | 014 | Aggregat über die 4 obigen Tabellen je Session |

### `session_metrics`-VIEW-Spalten (analytics-relevant)
session_id, agent_id, user_id, project_id, created_at, updated_at, status; llm_calls, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, cost_micros, total_llm_ms; tool_calls, tool_successes, tool_errors, tool_truncates, tool_total_ms; compactions, compactions_skipped; errors.

### Config-Dateien (config_dir)
`mcp_servers.json`, `llm.json` (default_model + providers — von check_llm_configured geprüft), `users.json`, `api_keys.json`, `research_apis.json`, `samba.password`, `whatsapp_bridge.secret`, `butler/`, `discord/`.

### Trigger-/State-Dateien (data_dir)
`.update_request`, `.restart_request`, `.voice_install_request`, `.bridge_setup_request`, `.samba_setup_request`, `.backup-rollback-<ts>.tar.gz`, `oauth_pending.json`, `voice_conversations.json`. (Trigger + Rollback sind alle vom Backup ausgeschlossen.)

### Backup-Inhalt
**Inkludiert**: `db/sessions.db`, `data/agents`, `data/projects`, `data/plugins`, `data/whatsapp`, `config/*` + Manifest (version="1", kind="system", created_at, hostname). **Exkludiert**: VMs/Container, `.plugin-cache`, Trigger-Files, `.backup-rollback-*`, `tls/`.

### Env-Vars (Auswahl, system-relevant)
`HH_BASE_DIR`, `HH_DATA_DIR`, `HH_CONFIG_DIR`, `HH_LOG_DIR`, `HH_TMP_DIR`, `HH_MEDIA_DIRS`, `HH_NUMBA_CACHE`, `HH_PLUGIN_HUB_GIT_URL`; `HH_HOST`, `HH_PORT`, `HH_SECRET_KEY` (pflicht!), `HH_JWT_EXPIRE_MINUTES`, `HH_UPDATE_CHECK_ENABLED`, `HH_CORS_ORIGINS`, `HH_ENABLE_DOCS`, `HH_INTERNAL_URL`; `HH_SAMBA_*`, `HH_VMS_BRIDGE`, `HH_WEBMIN_*`, `HH_BRIDGE_LOG`, `HH_SAMBA_LOG`; `HH_INITIAL_ADMIN_PASSWORD`.

### REST-Endpunkte dieses Subsystems
- `GET /api/dashboard` (auth)
- `GET /api/analytics/overview` (auth), `GET /api/analytics/session/{id}` (auth, ownership-gated)
- `GET /api/system/info|stats|health` (auth)
- `GET /api/system/check-update`, `POST /api/system/update`, `POST /api/system/restart`, `POST /api/system/install-voice`, `GET /api/system/install-voice/log`, `GET /api/system/update/log` (admin)
- `GET /api/system/bridge/status` (auth), `POST /api/system/bridge/setup`, `GET /api/system/bridge/log` (admin)
- `GET|POST /api/system/samba/status|setup|log` (admin)
- `POST /api/admin/backup`, `POST /api/admin/restore` (admin)
- `GET /api/llm/minimax/usage` (auth)
- `GET /api/health` (unauthenticated)

---

## Offene Enden

- **Doppelter 30s-Timer auf dem Dashboard.** DashboardPage pollt `/api/dashboard` und TokenAuditCard pollt `/analytics/overview` unabhängig — zwei separate Intervalle, leicht versetzt. Funktioniert, aber redundante Render-Zyklen. (Bewusst getrennt wegen Query-Kosten, siehe WARUM.)

- **`count_projects()` hardcodet den Pfad.** `_system_checks.py:32` baut `settings.data_dir / "projects"` direkt statt `settings.projects_dir` zu nutzen (das exakt dasselbe ist). Minimaler DRY-Bruch / Drift-Risiko, falls projects_dir je umgezogen wird. `count_agents()` nutzt korrekt `settings.agents_dir`.

- **`check_workspace_dir` prüft `data_dir/workspaces`** — ein Verzeichnis, das in `_paths.py` keine eigene Property hat (anders als agents/projects/plugins). Hardcoded String, kein Settings-Eintrag, kein Backup-Pfad. Entweder toter Check oder undokumentierte Workspace-Konvention.

- **`backup/_paths.py` sichert `data/whatsapp`, aber kein `health`, `mail`, `vms-Metadaten`, `scratchpad`, Voice-Conversations.** Die data_subdirs-Liste ist statisch (agents/projects/plugins/whatsapp). Neue data_dir-Inhalte (z.B. `mail/seen_ids.json`, `voice_conversations.json`, `oauth_pending.json`) landen *nicht* im Backup, ohne dass das irgendwo geflaggt wird. Stiller Drift bei jedem neuen data_dir-Feature.

- **`tool_calls.created_at` wird in zwei Bedeutungen genutzt.** `query_user_stats` joint `tool_calls.created_at` (Original-Spalte aus 001) — aber die Telemetrie-Spalten kamen erst mit 012. Für historische Zeilen ohne session_id liefert das Dashboard-Tool-Count andere Zahlen als der analytics-VIEW (der `session_id IS NOT NULL` filtert). Zwei Zählungen, zwei Wahrheiten.

- **MiniMax-Klassifikation ist fragil.** `_classify` matcht Modellnamen-Fragmente (`m2`, `hailuo`, `speech`, `music`, `image`) gegen lowercase. Neue MiniMax-Modelle ohne passendes Fragment fallen in `misc/daily/Einheiten`. Hardcoded Liste, kein Test-Pin gegen die echte API-Antwort.

- **`_start_time`-Globale überlebt keinen Reload.** Bei Hot-Reload (uvicorn `--reload`) wird das Modul neu importiert, `_start_time` ist `0.0` bis lifespan wieder läuft → uptime kurzzeitig 0. Nur Dev-relevant.

- **Cooldown-Globale prozess-lokal.** `_last_update_trigger`/`_last_restart_trigger` gehen bei Restart verloren — kein Persistenz-Schutz gegen „Restart, dann sofort wieder Update". In der Praxis serialisiert der Restart selbst, aber es ist keine harte Garantie.

- **Drei separate Cards für AgentLink/Tailscale tauchen sowohl auf Dashboard als auch SystemPage auf** (DashboardPage importiert `TailscaleCard`/`AgentLinkCard` aus `features/system/`). Gehören eigentlich ins Netz-/AgentLink-Subsystem; hier nur eingebunden — Doppel-Rendering je nach Seite.

- **`/api/health` ist unauthenticated und leakt commit + update_behind.** Bewusst (Frontend-Restart-Poll braucht keinen Token), aber exponiert Versions-/Update-Stand ohne Auth. Bei Public-Exposure ein minimaler Info-Leak.

- **Tests vorhanden, aber dünn**: `core/tests/test_analytics_api.py`, `test_update_cooldown.py`, `test_no_telemetry.py`. Keine erkennbaren Tests für Dashboard-Summary, System-Stats/Health, Backup-Restore-Roundtrip oder die Trigger-File-Endpoints.
