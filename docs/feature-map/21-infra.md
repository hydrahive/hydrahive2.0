# Infra (Backup/Tailscale/Samba/Net)

Dieses Subsystem bündelt vier voneinander unabhängige Infrastruktur-Bausteine von HydraHive2:

1. **Backup/Restore** — System-Backup (Admin, ganzer Server) + User-Backup (DSGVO Art. 20 Datenportabilität pro User). Tar.gz mit Manifest, Versionierung, Pre-Validate, Auto-Rollback, Größen-Caps gegen Dekompressionsbomben.
2. **Tailscale** — VPN-Mesh: Binary nachinstallieren, Host verbinden/trennen, Status/Peers anzeigen, Admin-API-Key verwalten + 24h-Single-Use-Pre-Auth-Keys ("Invites") erzeugen.
3. **Samba** — Per-Projekt SMB-Share auf den Projekt-Workspace, ein gemeinsamer Samba-User (MVP Option A). System-Setup-Trigger + Status + Log.
4. **Net (SSRF-Guard)** — zentraler Egress-Schutz für ausgehende HTTP-Requests (DNS-Rebinding-sicher, IP-Pinning). Genutzt von `fetch_url`-Tool und Butler `http_post`-Action.

---

## WAS

### Backup — System-Archiv (Admin)
- **`create_system_archive(target_dir)`** — erzeugt vollständiges System-Backup als `.tar.gz` (`core/src/hydrahive/backup/archive.py:72`). Packt: SQLite-DB (Snapshot), `data/agents`, `data/projects`, `data/plugins`, `data/whatsapp`, `config/`. Schreibt Manifest + optional `skipped.json`.
- **`_checkpoint_db_to_tempfile(target)`** — SQLite via `sqlite3.backup()`-API in Temp-File kopieren (WAL-Mode-safe, atomic) (`archive.py:29`).
- **`_add_dir(tar, arcname, source, skipped)`** — Verzeichnis rekursiv ins Tar mit Exclude-Filter; unlesbare Dateien (I/O-Fehler) werden übersprungen statt abzubrechen (`archive.py:42`).
- **`_add_bytes(tar, arcname, data)`** — In-Memory-Bytes (Manifest/skipped.json) als Tar-Member schreiben (`archive.py:141`).
- **`_read_hostname()`** — liest `/etc/hostname` fürs Manifest, Fallback `"unknown"` (`archive.py:149`).
- **Config-Flag `ARCHIVE_VERSION = "1"`** — Manifest-Versionierung (`archive.py:25`).
- **Manifest-Felder**: `version`, `kind="system"`, `created_at` (Timestamp `%Y%m%d-%H%M%S`), `hostname` (`archive.py:92`).
- **Archiv-Name**: `hydrahive2-system-<timestamp>.tar.gz` (`archive.py:79`).

### Backup — System-Restore (Admin)
- **`restore_system_archive(archive_path)`** — Validate → Auto-Rollback → Extract → atomic Replace → DB-Replace → Restart-Trigger (`core/src/hydrahive/backup/restore.py:31`).
- **`_create_rollback_backup()`** — sichert aktuellen Stand als `.backup-rollback-<epoch>.tar.gz` BEVOR überschrieben wird (`restore.py:65`).
- **`_atomic_replace_dir(src, dst)`** — alten Pfad → `.old-restore`, neuen rein, alten löschen; bei Fehler Rollback des Rename (`restore.py:75`).
- **`_trigger_restart()`** — schreibt `<data_dir>/.restart_request`, systemd-path-Watcher übernimmt (`restore.py:97`).

### Backup — Tarball-Validation (vor Restore)
- **`validate_archive(archive_path)`** — liest Manifest, prüft mitgelieferte SQLite-DB auf Integrität, bevor irgendetwas live ausgetauscht wird (`core/src/hydrahive/backup/validate.py:27`).
- **`_read_manifest(tar)`** — Manifest lesen + prüfen: `version == "1"` und `kind == "system"`, sonst `RestoreError` (`validate.py:47`).
- **`_check_sqlite_in_tar(tar, db_arc)`** — DB in Temp-File extrahieren, `PRAGMA integrity_check` laufen lassen, bei `!= "ok"` → `RestoreError("backup_db_corrupt")` (`validate.py:68`).
- **`RestoreError(code, **params)`** — Exception mit Fehler-Code für Error-Envelope (`validate.py:20`).
- **Fehler-Codes**: `backup_archive_missing`, `backup_tar_corrupt`, `backup_manifest_missing`, `backup_manifest_unreadable`, `backup_manifest_invalid`, `backup_version_unsupported`, `backup_kind_mismatch`, `backup_db_unreadable`, `backup_db_corrupt`.

### Backup — Pfad-Definitionen (was rein, was raus)
- **`data_subdirs()`** — Liste der `(arcname, source)`-Paare: `data/agents`, `data/projects`, `data/plugins`, `data/whatsapp` (`core/src/hydrahive/backup/_paths.py:16`).
- **`config_dir_arcname()`** — `("config", settings.config_dir)` (`_paths.py:26`).
- **`db_arcname()`** — `("db/sessions.db", settings.sessions_db)` (`_paths.py:30`).
- **`is_excluded(path)`** — Pattern-/Dir-Match auf jedem Path-Teil (`_paths.py:57`).
- **`EXCLUDE_PATTERNS`** — `.plugin-cache`, `.update_request`, `.restart_request`, `.voice_install_request`, `.backup-rollback-` (`_paths.py:41`).
- **`EXCLUDE_DIRS`** — `tls` (Private-Key root-only, Cert Server-spezifisch → beim Migrate neu generieren) (`_paths.py:52`).

### Backup — Größen-Caps / Bomben-Schutz (#189)
- **`stream_upload_capped(upload, dest_path, max_bytes=None)`** — async chunked Upload auf Platte, bricht bei Überschreitung von `MAX_UPLOAD_BYTES` ab (`core/src/hydrahive/backup/_limits.py:26`).
- **`enforce_archive_limits(tar, max_bytes=None, max_members=None)`** — prüft kumulierte entpackte Größe + Member-Anzahl VOR `extractall` (`_limits.py:41`).
- **`RestoreTooLarge(code, **params)`** — Exception (`_limits.py:19`).
- **Konstanten**: `MAX_UPLOAD_BYTES = 2 GiB`, `MAX_EXTRACTED_BYTES = 8 GiB`, `MAX_MEMBERS = 100_000`, `_CHUNK = 1 MiB` (`_limits.py:12-16`).
- **Fehler-Codes**: `backup_upload_too_large`, `backup_too_many_members`, `backup_extracted_too_large`.

### Backup — User-Archiv (DSGVO Art. 20, pro User)
- **`create_user_archive(username, target_dir)`** — User-Backup `.tar.gz` mit allen Daten des Users (`core/src/hydrahive/backup/user_archive.py:30`).
- **`_export_sessions(tar, username)`** — alle Sessions + Messages des Users als `sessions.json` (limit 10000) (`user_archive.py:56`).
- **`_export_agents(tar, username)`** — pro Agent: `agents/<id>/` (Config) + Workspace nach `workspaces/master/<id>` bzw. `workspaces/specialists/<id>` je nach Typ (`user_archive.py:68`).
- **`_export_projects(tar, username)`** — pro Projekt: `projects/<id>/` + `workspaces/projects/<id>` (`user_archive.py:83`).
- **`_export_whatsapp(tar, username)`** — WhatsApp-Config-File des Users als `whatsapp.json` (`user_archive.py:90`).
- **`_export_butler(tar, username)`** — alle Butler-Flows des Owners als `butler/<flow_id>.json` (`user_archive.py:96`).
- **Manifest**: `version="1"`, `kind="user"`, `username`, `created_at` (`user_archive.py:37`).
- **Archiv-Name**: `hydrahive2-user-<username>-<timestamp>.tar.gz` (`user_archive.py:34`).

### Backup — User-Restore (DSGVO Art. 20)
- **`restore_user_archive(archive_path, username)`** — Restore mit Owner-Check; wirft `UserRestoreError` (`core/src/hydrahive/backup/user_restore.py:31`).
- **`_read_manifest(tar)`** — Manifest aus Tar lesen (`user_restore.py:67`).
- **`_restore_sessions(file, username)`** — Sessions/Messages via `INSERT OR IGNORE` (kein Überschreiben), nur Rows mit passendem `user_id` (`user_restore.py:76`).
- **`_restore_agents(src, username)`** — pro Agent-ID Owner-Gate (`#183`): existiert er → muss dem User gehören; existiert er nicht → Archiv-`config.json.owner` muss == username (`user_restore.py:127`).
- **`_restore_projects(src, username)`** — analog für Projekte, Owner-Feld `created_by` (`user_restore.py:148`).
- **`_restore_owned_workspaces(src, dst, username, is_project)`** — Workspace nur einspielen wenn zugehörige Agent-/Projekt-ID dem User gehört; läuft NACH Agent-/Projekt-Restore (`user_restore.py:168`).
- **`_restore_whatsapp(wa_file, username)`** — WhatsApp-Config zurückspielen (`user_restore.py:193`).
- **`_restore_butler(src, username)`** — Butler-Flows zurückspielen, Owner auf username erzwingen (`user_restore.py:202`).
- **`_copy_tree(src, dst)`** — File-Copy mit `shutil.copy2` (existierende Files bleiben? → siehe Gotcha, wird überschrieben) (`user_restore.py:108`).
- **`_json_field(path, field)`** — robustes JSON-Feld-Lesen, Fallback `None` (`user_restore.py:120`).
- **`UserRestoreError(code, **params)`** (`user_restore.py:24`).
- **Fehler-Codes**: `backup_wrong_kind`, `backup_wrong_owner`, `backup_no_manifest`.

### Backup — API-Endpoints
- **`POST /api/admin/backup`** (require_admin) — erstellt Archiv in Temp-Dir, liefert als `FileResponse` (Content-Length für Browser-Progress), Temp-Cleanup via BackgroundTask (`core/src/hydrahive/api/routes/backup.py:31`).
- **`POST /api/admin/restore`** (require_admin) — Multipart-Upload, capped-Stream, Pre-Validate, Auto-Rollback, Replace, Restart-Trigger. Antwort kommt VOR dem Service-Restart (`backup.py:54`).
- **`POST /api/users/me/backup`** (require_auth) — eigenes User-Backup als Download (`core/src/hydrahive/api/routes/users.py:95`).
- **`POST /api/users/me/restore`** (require_auth) — eigener User-Restore aus Upload (`users.py:112`).

### Tailscale — Status
- **`get_status()`** — `tailscale status --json` parsen → `{installed, connected, backend_state, ip, hostname, dns_name, tailnet, version, magic_dns, auth_url, peers[], exit_node_active}` (`core/src/hydrahive/tailscale/status.py:40`).
- **`_peer_dict(p)`** — Peer-Mapping: `hostname, dns_name, ip(v4), online, os, exit_node, exit_node_option, last_seen` (`status.py:25`).
- **`_tailscale_bin()`** — `shutil.which("tailscale")` Fallback `/usr/bin/tailscale` (`status.py:11`).
- **`connected` = `BackendState == "Running"`** (`status.py:57`); Peers sortiert online-first dann hostname; aktiver Exit-Node ermittelt (`status.py:54-55`).
- Bei `FileNotFoundError` → `{installed: False, connected: False}` (`status.py:70`).

### Tailscale — Control (up/logout)
- **`up(authkey, accept_routes=False)`** — `tailscale up --authkey=...`; `--accept-routes` ist **opt-in** (sonst LAN-Default-Interface weg) (`core/src/hydrahive/tailscale/control.py:23`).
- **`logout()`** — `tailscale logout` (timeout 10s) (`control.py:33`).
- **`_run(*args, timeout=30)`** — subprocess-Wrapper, wirft `RuntimeError` bei rc != 0 (`control.py:11`).

### Tailscale — Install (Binary nachinstallieren)
- **`install_tailscale()`** — ruft `sudo -n bash <repo>/installer/modules/80-tailscale.sh` mit `HH_INSTALL_TAILSCALE=yes`; idempotent; returnt `{ok, rc, output}` (letzte ~30 Log-Zeilen). Wirft KEIN RuntimeError, Fehler kommen als rc != 0 (`core/src/hydrahive/tailscale/install.py:24`).
- **Konstante `INSTALL_TIMEOUT = 120.0`** (`install.py:21`).

### Tailscale — Admin (API-Key + Invites)
- **`load_admin_config()`** → `{api_key, tailnet}` oder `{}` (`core/src/hydrahive/tailscale/admin.py:31`).
- **`save_admin_config(api_key, tailnet)`** — atomar schreiben mit chmod 0600 (`admin.py:39`).
- **`is_configured()`** → bool (`admin.py:49`).
- **`public_config()`** → Frontend-safe `{configured, tailnet}` — **niemals** api_key (`admin.py:54`).
- **`validate_api_key(api_key, tailnet)`** — probt `GET /tailnet/<tn>/devices?fields=id`, True bei 200 (`admin.py:81`).
- **`create_invite()`** — POST `/tailnet/<tn>/keys` mit `reusable=False, ephemeral=False, preauthorized=True, expirySeconds=86400` → 24h-Single-Use-Pre-Auth-Key, returnt `{auth_key, expires, id}` (`admin.py:94`).
- **`_ts_api_sync(path, api_key, method, body, timeout)`** — sync urllib-Call an Tailscale-API (`admin.py:63`).
- **Konstanten**: `TS_API_BASE = "https://api.tailscale.com/api/v2"`, `INVITE_EXPIRY_S = 24*3600` (`admin.py:23-24`).
- **Storage**: `<config_dir>/tailscale-admin.json` chmod 0600 (`admin.py:27`).

### Tailscale — API-Endpoints
- **`GET /api/tailscale/status`** (require_admin) → `get_status()` (`core/src/hydrahive/api/routes/tailscale.py:26`).
- **`POST /api/tailscale/up`** (require_admin) — body `{authkey}`, ruft `up()` dann `get_status()` (`tailscale.py:31`).
- **`POST /api/tailscale/logout`** (require_admin) (`tailscale.py:40`).
- **`POST /api/tailscale/install`** (require_admin) → `{ok, rc, output, status}` (`tailscale.py:49`).
- **`GET /api/tailscale/admin-config`** (require_admin) → `public_config()` — niemals api_key (`tailscale.py:60`).
- **`PUT /api/tailscale/admin-config`** (require_admin) — body `{api_key, tailnet="-"}`, validiert gegen TS-API dann speichert, 400 bei invalid (`tailscale.py:66`).
- **`POST /api/tailscale/invite`** (require_admin) → `create_invite()`; 400 wenn nicht konfiguriert, 502 bei API-Fehler (`tailscale.py:79`).
- **Pydantic-Models**: `UpRequest{authkey}`, `AdminConfigRequest{api_key, tailnet="-"}` (`tailscale.py:17,21`).

### Samba — Manager (Share-Verwaltung)
- **`enable_share(project_id, project_name)`** → `(ok, err)` — schreibt Per-Projekt-Config, regeneriert Index, reload smbd (`core/src/hydrahive/samba/manager.py:84`).
- **`disable_share(project_id)`** → `(ok, err)` — löscht Config, regeneriert Index, reload (`manager.py:98`).
- **`is_share_enabled(project_id)`** → bool (Config-File existiert) (`manager.py:110`).
- **`samba_status()`** → `{installed, running, user, password_set, includes_dir, includes_dir_exists}` (`manager.py:130`).
- **`render_share(project_id, project_name)`** — rendert smb.conf-Block: `[name]`, path=Workspace, `valid users`/`force user` = samba_user, masks 0664/0775 (`manager.py:48`).
- **`_safe_share_name(project_name, project_id)`** — sanitisiert auf alnum/`_`/`-`, Fallback `hh_<id[:8]>` bei leer oder >50 Zeichen (`manager.py:24`).
- **`share_name_for(project_id, project_name)`** — Public-Alias von `_safe_share_name` (`manager.py:114`).
- **`_config_path(project_id)`** → `<samba_includes_dir>/<project_id>.conf` (`manager.py:32`).
- **`_regenerate_index()`** — schreibt `_index.conf` das alle Per-Projekt-`*.conf` per `include = ` aggregiert (Samba kann keine Verzeichnis-Includes) (`manager.py:36`).
- **`_reload_smbd()`** — `smbcontrol all reload-config`, failt leise wenn smbd fehlt (`manager.py:66`).
- **`_find_smbd()`** — Binary-Suche inkl. `/usr/sbin` (Service-PATH hat das oft nicht) (`manager.py:118`).
- **Re-Exports im `__init__.py`**: `disable_share, enable_share, is_share_enabled, samba_status` (`core/src/hydrahive/samba/__init__.py:10`).
- **Fehler-Codes**: `samba_not_installed`, `samba_no_write_access`.

### Samba — Per-Projekt API-Endpoints
- **`GET /api/projects/{id}/samba`** (require_auth) → `{enabled, share_name, user, password}` (`core/src/hydrahive/api/routes/projects_samba.py:32`). Enabled = `samba_enabled`-Flag UND Config-File existiert.
- **`PUT /api/projects/{id}/samba`** (require_auth) — body `{enabled}`, ruft enable/disable + persistiert `samba_enabled` in Projekt-Config (`projects_samba.py:53`).
- **`_project_or_404(project_id, username, role)`** — 404 wenn nicht existent, 403 wenn nicht Member/Owner/Admin (`projects_samba.py:23`).
- **Pydantic-Model**: `SambaToggle{enabled}` (`projects_samba.py:19`).

### Samba — System API-Endpoints (Setup/Status/Log)
- **`GET /api/system/samba/status`** (require_admin) → `samba_status()` + `password` (aus password-File gelesen) (`core/src/hydrahive/api/routes/system_samba.py:27`).
- **`POST /api/system/samba/setup`** (require_admin) — generiert Passwort-File (token_urlsafe(18), chmod 0600) wenn fehlend, schreibt Trigger `.samba_setup_request` (`system_samba.py:39`).
- **`GET /api/system/samba/log?tail=200`** (require_admin) — letzte N Zeilen aus Setup-Log (`system_samba.py:50`).
- **Trigger-Pfad**: `settings.data_dir / ".samba_setup_request"` (`system_samba.py:23`).

### Net — SSRF-Guard
- **`validate_outbound_url(url)`** → `None` (ok) oder Begründungs-String (`core/src/hydrahive/net/ssrf.py:84`). Prüft Scheme-Allowlist + interne Hosts.
- **`is_blocked_host(hostname)`** → bool — 3 Stufen: Denylist → IP-Parse → DNS-Auflösung (`ssrf.py:55`).
- **`resolve_validated_ip(hostname)`** → validierte IP (EINE Auflösung, alle A-Records geprüft); wirft `SsrfBlocked` (`ssrf.py:99`).
- **`pin_request(request, host_to_ip)`** — schreibt `url.host` auf IP um, behält SNI + Host-Header (TLS bleibt korrekt) (`ssrf.py:138`).
- **`safe_async_client(url, timeout)`** → DNS-Rebinding-sicherer `httpx.AsyncClient` mit gepinntem Transport, `follow_redirects=False` (`ssrf.py:167`).
- **`_PinnedTransport`** — AsyncHTTPTransport der Requests an validierte IPs pinnt (`ssrf.py:155`).
- **`_ip_is_internal(ip)`** — normalisiert IPv4-mapped-IPv6, blockt alles Nicht-Globale (`ssrf.py:43`).
- **`SsrfBlocked`** — Exception, `args[0]` = Begründung (`ssrf.py:19`).
- **`ALLOWED_SCHEMES = {http, https}`** (`ssrf.py:16`).
- **`BLOCKED_RANGES`** — 127.0.0.0/8, 10/8, 172.16/12, 192.168/16, 169.254/16, ::1/128, fc00::/7, fe80::/10 (`ssrf.py:23`).
- **`BLOCKED_HOSTNAMES`** — localhost, metadata.google.internal, metadata.internal, 169.254.169.254 (`ssrf.py:35`).
- **Begründungs-Codes**: `scheme_not_allowed`, `host_missing`, `host_blocked`, `dns_failed`, `dns_empty`.

### Frontend — UI-Komponenten
- **`BackupCard`** (Admin, SystemPage) — Download/Restore-Buttons, Restore über Modal mit Confirm + Health-Poll bis Backend wieder antwortet (`frontend/src/features/system/BackupCard.tsx:9`).
- **`BackupRestoreModal`** — Zustandsmaschine `idle|confirm|uploading|waiting|done|failed` (`frontend/src/features/system/BackupRestoreModal.tsx:6`).
- **`BackupRestoreCard`** (Profile, jeder User) — DSGVO User-Backup/-Restore mit `window.confirm` (`frontend/src/features/profile/BackupRestoreCard.tsx:8`).
- **`TailscaleCard`** (Admin, SystemPage + DashboardPage) — Install/Connect/Logout, Status-Polling alle 15s (`frontend/src/features/system/TailscaleCard.tsx:21`).
- **`TailscaleConnectedView`** — IP/Hostname/DNS/Tailnet/Version/Exit-Node + Peer-Liste + Copy-IP/Admin-Console/Logout (`frontend/src/features/system/_TailscaleConnectedView.tsx:14`).
- **`TailscaleInviteSection`** — Admin-API-Key-Settings + Invite-Generator (`frontend/src/features/system/_TailscaleInviteSection.tsx:17`).
- **`TailscaleLoginForm`** — Auth-Key-Eingabe (`frontend/src/features/system/_TailscaleLoginForm.tsx:13`).
- **`TailscaleStatus`/`TailscalePeer`** — TS-Typen (`frontend/src/features/system/_tailscaleTypes.ts:12`).
- **`SambaCard`** (Admin, SystemPage) — System-Setup-Trigger + Log-Polling (1.5s) + User/Passwort-Anzeige (`frontend/src/features/system/SambaCard.tsx:10`).
- **`SambaSection`** (Projekt-Settings-Tab) — Per-Projekt-Toggle + SMB-URL/User/Passwort mit Copy (`frontend/src/features/projects/_SettingsSamba.tsx:21`).
- **`systemApi`** — Frontend-API-Client für system/backup/samba/tailscale-Endpoints (`frontend/src/features/system/api.ts`).

---

## WIE

### Datenfluss System-Backup (Download)
1. Admin klickt "Download" in `BackupCard` → `systemApi.downloadBackup()` POST `/api/admin/backup` mit Bearer-Token (`BackupCard.tsx:17`, `api.ts` `downloadBackup`).
2. `create_backup()` legt Temp-Dir an (`backup.py:37`), ruft `create_system_archive(tmp_dir)`.
3. `create_system_archive`: Temp-Dir anlegen, Timestamp, DB-Snapshot via `_checkpoint_db_to_tempfile` (sqlite3.backup-API — WAL-safe), Manifest bauen, Tar `w:gz` öffnen: Manifest ZUERST (Validator liest ohne Auspacken), dann DB-Member, dann `data_subdirs()` rekursiv, dann `config/`, dann optional `skipped.json` (`archive.py:99-124`).
4. FileResponse mit `media_type=application/gzip`, Temp-Cleanup via BackgroundTask nach Send (`backup.py:46`).
5. Frontend baut Blob → `<a download>` mit Filename aus `Content-Disposition` (`api.ts` downloadBackup).

### Datenfluss System-Restore (Upload)
1. Admin wählt File → `BackupCard` setzt State `confirm`, zeigt `BackupRestoreModal` (`BackupCard.tsx:28`).
2. Bei Confirm: State `uploading`, `systemApi.restoreBackup(file)` POST `/api/admin/restore` (multipart) (`BackupCard.tsx:37`).
3. Backend `restore_backup`: Temp-Dir, `stream_upload_capped` (Disk-Fill-Schutz, 2 GiB Cap), dann `restore_system_archive`.
4. `restore_system_archive` (`restore.py:31`):
   a. `validate_archive` — Manifest + SQLite-`integrity_check` (jeder Fehler → Live-Stand bleibt unverändert).
   b. `_create_rollback_backup` — aktueller Stand als `.backup-rollback-<epoch>.tar.gz`.
   c. Tarball in Temp-Dir mit `enforce_archive_limits` (8 GiB / 100k Member Cap) + `extractall(filter="data")` (lehnt eskapierende Symlinks/Hardlinks/Device-Nodes/setuid ab).
   d. Pro `data_subdirs()` + `config/`: `_atomic_replace_dir` (alt → `.old-restore`, neu rein, alt löschen).
   e. DB-File: `db_src.replace(db_dst)` (atomic auf gleichem FS).
   f. `_trigger_restart` schreibt `.restart_request`.
5. Response `{restored, manifest, rollback_path}` kommt zurück, DANN systemd-path-Watcher startet Service neu.
6. Frontend State `waiting`, pollt `/api/health` (no-store) alle 2s bis zu 120s → `done` (`BackupCard.tsx:45`).

### Datenfluss Restart-Trigger (systemd)
- `.restart_request` in `$HH_DATA_DIR` → `hydrahive2-restart.service` mit `ConditionPathExists=$HH_DATA_DIR/.restart_request`, `ExecStartPre=/bin/rm -f .restart_request`, `ExecStart=/bin/systemctl restart hydrahive2.service` (`installer/modules/50-systemd.sh:135`). `hydrahive2-restart.timer` pollt alle 5s (`OnUnitActiveSec=5s`).
- Mac-Pendant: launchd WatchPaths (`installer/modules-mac/55-launchd-triggers.sh:59`).

### Datenfluss User-Backup/Restore (DSGVO)
- Download: `POST /api/users/me/backup` → `create_user_archive(username, tmp)` → FileResponse. Im Gegensatz zum System-Backup wird DB nicht als File mitgepackt, sondern Sessions+Messages als `sessions.json` serialisiert.
- Restore: `POST /api/users/me/restore` → `stream_upload_capped` → `restore_user_archive`:
  1. Manifest prüfen: `kind == "user"` UND `username` == auth-username, sonst `UserRestoreError`.
  2. `enforce_archive_limits`, `extractall(filter="data")`.
  3. **Reihenfolge bewusst**: Sessions → Agents → Master/Specialist-Workspaces → Projects → Project-Workspaces → WhatsApp → Butler. Workspaces werden NACH Agent/Projekt eingespielt, weil deren Owner-Gate sich nach der (ggf. frisch wiederhergestellten) DB-/Config-Ownership richtet.
  4. Pro Entität Owner-Gate (`_owned`): überspringt fremde IDs mit Warning statt zu überschreiben (#182/#183).

### Datenfluss Tailscale-Install → Connect → Invite
1. `TailscaleCard` lädt `GET /api/tailscale/status` (15s-Poll). `!installed` → Install-Button.
2. Install: `POST /api/tailscale/install` → `install_tailscale()` ruft `sudo -n bash 80-tailscale.sh` (kein durchgereichter Authkey). Modul: `command -v tailscale`-Check → curl|sh, `systemctl enable/start tailscaled`, `tailscale set --operator=$HH_USER`, alte sudoers-Regel aufräumen.
3. Connect: User holt Auth-Key von login.tailscale.com → `TailscaleLoginForm` → `POST /api/tailscale/up {authkey}` → `up()` (`tailscale up --authkey=...`, ohne `--accept-routes`).
4. Connected: `TailscaleConnectedView` zeigt Status + Peers. `TailscaleInviteSection`: Admin speichert API-Key via `PUT /admin-config` (validiert gegen TS-API), dann `POST /invite` → `create_invite()` erzeugt 24h-Single-Use-Key, den der Empfänger-Server als `tailscale up --authkey=...` nutzt.

### Datenfluss Samba — System-Setup
1. Admin klickt Setup in `SambaCard` → `POST /api/system/samba/setup`.
2. `setup()`: legt Passwort-File an (token_urlsafe(18), chmod 0600), schreibt `.samba_setup_request`.
3. systemd `hydrahive2-samba.service` (ConditionPathExists, ExecStartPre rm, Env HH_USER/HH_DATA_DIR/HH_CONFIG_DIR) ruft `47-samba.sh`, Log nach `/var/log/hydrahive2-samba.log` (`installer/modules/50-systemd.sh:209`).
4. `47-samba.sh`: apt install samba, includes-dir 2775 chgrp $HH_USER, smb.conf patchen (`include = .../​_index.conf`), Samba-System-User `hh` anlegen (`useradd -r -M -s nologin`), gegenseitige Gruppen-Membership (hh↔hydrahive für Path-Traversal + Backend-Write), `smbpasswd -a/-e`, Workspaces-Permissions nachziehen (2775 dirs / 664 files, setgid), `systemctl enable/restart smbd`.
5. `SambaCard` pollt `GET /api/system/samba/log` (1.5s) + `GET /api/system/samba/status` bis `installed && running` (max 300s).

### Datenfluss Samba — Per-Projekt-Toggle
1. Projekt-Settings-Tab lädt `GET /api/projects/{id}/samba` (`_SettingsTab.tsx:24`).
2. Toggle → `PUT /api/projects/{id}/samba {enabled}`.
3. `enable_share`: schreibt `<id>.conf` mit `render_share`, `_regenerate_index` (aggregiert alle `*.conf` in `_index.conf`), `_reload_smbd` (`smbcontrol all reload-config`), persistiert `samba_enabled=True` in Projekt-Config.
4. `disable_share`: löscht `<id>.conf`, regeneriert Index, reload, persistiert `False`.
5. Cascade: bei `project_config.delete` wird `samba_disable` mitgerufen (`core/src/hydrahive/projects/config.py:115`).

### Datenfluss SSRF-Guard (fetch_url / http_post)
1. `fetch_url`-Tool: `safe_async_client(url, timeout)` → `resolve_validated_ip` löst Host EINMAL auf, prüft alle A-Records, gibt validierte IP. `_PinnedTransport` pinnt Connect an diese IP (kein 2. DNS-Lookup → TOCTOU/DNS-Rebinding ausgeschlossen, #206), `follow_redirects=False`. `SsrfBlocked` → ToolResult.fail (`core/src/hydrahive/tools/fetch_url.py:121`).
2. Butler `http_post`-Action: zusätzlich `validate_outbound_url` als Vorab-Check, dann `safe_async_client` (`core/src/hydrahive/butler/registry/actions/http_post.py:20,35`).

---

## WO

### Backup
- `core/src/hydrahive/backup/__init__.py` — leer (1 Zeile, kein Re-Export)
- `core/src/hydrahive/backup/archive.py:25` `ARCHIVE_VERSION`, `:29` `_checkpoint_db_to_tempfile`, `:42` `_add_dir`, `:72` `create_system_archive`, `:141` `_add_bytes`, `:149` `_read_hostname`
- `core/src/hydrahive/backup/restore.py:31` `restore_system_archive`, `:65` `_create_rollback_backup`, `:75` `_atomic_replace_dir`, `:97` `_trigger_restart`
- `core/src/hydrahive/backup/validate.py:20` `RestoreError`, `:27` `validate_archive`, `:47` `_read_manifest`, `:68` `_check_sqlite_in_tar`
- `core/src/hydrahive/backup/_paths.py:16` `data_subdirs`, `:26` `config_dir_arcname`, `:30` `db_arcname`, `:41` `EXCLUDE_PATTERNS`, `:52` `EXCLUDE_DIRS`, `:57` `is_excluded`
- `core/src/hydrahive/backup/_limits.py:12-16` Caps-Konstanten, `:19` `RestoreTooLarge`, `:26` `stream_upload_capped`, `:41` `enforce_archive_limits`
- `core/src/hydrahive/backup/user_archive.py:30` `create_user_archive`, `:56` `_export_sessions`, `:68` `_export_agents`, `:83` `_export_projects`, `:90` `_export_whatsapp`, `:96` `_export_butler`
- `core/src/hydrahive/backup/user_restore.py:24` `UserRestoreError`, `:31` `restore_user_archive`, `:76` `_restore_sessions`, `:108` `_copy_tree`, `:120` `_json_field`, `:127` `_restore_agents`, `:148` `_restore_projects`, `:168` `_restore_owned_workspaces`, `:193` `_restore_whatsapp`, `:202` `_restore_butler`
- `core/src/hydrahive/api/routes/backup.py:31` `create_backup`, `:54` `restore_backup`
- `core/src/hydrahive/api/routes/users.py:95` `backup_own_data`, `:112` `restore_own_data`

### Tailscale
- `core/src/hydrahive/tailscale/__init__.py` — leer (1 Zeile)
- `core/src/hydrahive/tailscale/status.py:11` `_tailscale_bin`, `:15` `_run`, `:25` `_peer_dict`, `:40` `get_status`
- `core/src/hydrahive/tailscale/control.py:7` `_tailscale_bin`, `:11` `_run`, `:23` `up`, `:33` `logout`
- `core/src/hydrahive/tailscale/install.py:21` `INSTALL_TIMEOUT`, `:24` `install_tailscale`
- `core/src/hydrahive/tailscale/admin.py:23-24` Konstanten, `:27` `_config_path`, `:31` `load_admin_config`, `:39` `save_admin_config`, `:49` `is_configured`, `:54` `public_config`, `:63` `_ts_api_sync`, `:81` `validate_api_key`, `:94` `create_invite`
- `core/src/hydrahive/api/routes/tailscale.py:14` Router, `:17/:21` Models, `:26-90` Endpoints
- `installer/modules/80-tailscale.sh` — Install-Modul

### Samba
- `core/src/hydrahive/samba/__init__.py:10` Re-Exports
- `core/src/hydrahive/samba/manager.py:21` `_NAME_RE`, `:24` `_safe_share_name`, `:32` `_config_path`, `:36` `_regenerate_index`, `:48` `render_share`, `:66` `_reload_smbd`, `:84` `enable_share`, `:98` `disable_share`, `:110` `is_share_enabled`, `:114` `share_name_for`, `:118` `_find_smbd`, `:130` `samba_status`
- `core/src/hydrahive/api/routes/projects_samba.py:16` Router, `:19` `SambaToggle`, `:23` `_project_or_404`, `:32` `get_samba`, `:53` `put_samba`
- `core/src/hydrahive/api/routes/system_samba.py:21` Router, `:23` `TRIGGER`, `:27` `status`, `:39` `setup`, `:50` `log_`
- `core/src/hydrahive/projects/config.py:115` `samba_disable` im Delete-Cascade
- `installer/modules/47-samba.sh` — Setup-Modul

### Net
- `core/src/hydrahive/net/__init__.py` — leer (1 Zeile)
- `core/src/hydrahive/net/ssrf.py:16` `ALLOWED_SCHEMES`, `:19` `SsrfBlocked`, `:23` `BLOCKED_RANGES`, `:35` `BLOCKED_HOSTNAMES`, `:43` `_ip_is_internal`, `:55` `is_blocked_host`, `:84` `validate_outbound_url`, `:99` `resolve_validated_ip`, `:138` `pin_request`, `:155` `_PinnedTransport`, `:167` `safe_async_client`
- Konsumenten: `core/src/hydrahive/tools/fetch_url.py:13,121`, `core/src/hydrahive/butler/registry/actions/http_post.py:10,20,35`

### Settings-Keys
- `core/src/hydrahive/settings/_paths.py:16` `base_dir`, `:20` `data_dir`, `:24` `config_dir`, `:28` `agents_dir`, `:32` `projects_dir`, `:36` `plugins_dir`, `:79` `sessions_db`, `:121` `samba_log_path`, `:125` `bridge_log_path`
- `core/src/hydrahive/settings/_infra.py:11` `samba_includes_dir`, `:17` `samba_user`, `:23` `samba_password_file`
- `whatsapp_data_dir`, `config_dir` (in `_paths`/`_services`/Communication-Mixin)

### Frontend
- `frontend/src/features/system/BackupCard.tsx`, `BackupRestoreModal.tsx`, `TailscaleCard.tsx`, `_TailscaleConnectedView.tsx`, `_TailscaleInviteSection.tsx`, `_TailscaleLoginForm.tsx`, `_tailscaleTypes.ts`, `SambaCard.tsx`, `api.ts`, `SystemPage.tsx:139-142`
- `frontend/src/features/profile/BackupRestoreCard.tsx`, `frontend/src/features/profile/api.ts`
- `frontend/src/features/projects/_SettingsSamba.tsx`, `_SettingsTab.tsx:6,63`, `api.ts:62,64`
- `frontend/src/features/dashboard/DashboardPage.tsx:59` (TailscaleCard)

### Router-Mounts
- `core/src/hydrahive/api/main.py:101` backup, `:121` projects_samba, `:146` system_samba, `:147` tailscale

### Tests
- `core/tests/test_backup_auth.py`, `test_user_restore_ownership.py`, `test_tailscale_invite.py`, `test_tailscale_install.py`, `test_restore_limits.py`, `test_backup_restore_symlink.py`, `test_ssrf_pinning.py`, `test_ssrf_guard.py`, `test_fetch_url_ssrf.py`

### systemd / installer
- `installer/modules/50-systemd.sh:135` Restart-Service, `:155` Restart-Timer, `:209` Samba-Service, `:220+` Samba-Timer
- `installer/update.sh:171` Restart-Watcher, `:201` Samba-Watcher
- `installer/modules-mac/55-launchd-triggers.sh:59` Mac-Restart-Watcher

---

## WARUM

### Backup — nicht-offensichtliche Verdrahtung & Invarianten
- **Manifest zuerst im Tar**: Der Validator (`validate_archive`) liest Manifest + macht `getmember(db_arc)` ohne komplettes Auspacken. Die Reihenfolge im Tar (Manifest → DB → data → config) ist absichtlich, damit der schnelle Pre-Check (`integrity_check`) läuft, bevor irgendetwas live ersetzt wird. **Bricht** man die Reihenfolge nicht — `tarfile` indexiert sowieso, aber das Pattern dokumentiert die Intention.
- **WAL-Mode-Safety**: Die DB darf NICHT per `shutil.copy` gesichert werden (WAL → inkonsistenter Snapshot). `sqlite3.backup()` ist Pflicht. Wer das ändert, riskiert korrupte Backups bei laufendem Schreibverkehr.
- **VMs/Container sind bewusst ausgeschlossen** — qcow2-Files sind mehrere GB, separater Operator-Backup-Pfad. Deshalb sind die Caps (2/8 GiB) großzügig aber endlich. **Annahme**: `data/agents/projects/plugins/whatsapp` + `config/` bleiben unter 8 GiB entpackt.
- **`tls/` ausgeschlossen** (`EXCLUDE_DIRS`): Private-Key ist root-only lesbar (würde beim Backup als skipped landen oder fehlschlagen), und das Cert ist Server-spezifisch (IP/Hostname) — beim Migrate ist Neu-Generieren sinnvoller. Wer `tls/` reinnimmt, schleppt fremde Zertifikate auf den Ziel-Server.
- **`.backup-rollback-` ausgeschlossen**: sonst rekursive Aufblähung (Backup-im-Backup-im-Backup). Das Auto-Rollback landet IN `data_dir` (`restore.py:67`), also würde ein folgendes Backup es mitpacken — der Exclude verhindert das.
- **`is_excluded` matcht auf JEDEM Path-Teil**: fängt sowohl Top-Level `.update_request` als auch `.plugin-cache/<subfile>`. Ein Pattern-Match ist `pat in part` (Substring!) — deshalb fängt `.backup-rollback-` auch `.backup-rollback-123.tar.gz`. **Falle**: ein Projekt namens `update_request_demo` würde NICHT geblockt (Pattern ist `.update_request` mit Punkt), aber ein Pattern wie `tls` als EXCLUDE_DIR matcht exakte Path-Parts, kein Substring.
- **Atomic-Replace ist NICHT strikt atomic** (`_atomic_replace_dir`): Bei Abbruch zwischen Rename und Löschen bleibt `.old-restore` stehen — manuell wiederherstellbar. Der DB-Replace dagegen IST atomic (`Path.replace` auf gleichem FS). **Falle**: liegt `data_dir` auf anderem FS als die Workspaces, schlägt `replace` mit `EXDEL` fehl — `shutil.move` fängt das ab, aber DB-`replace` nicht.
- **Restart kommt NACH der HTTP-Response**: Der Endpoint schreibt den Trigger und returnt; der systemd-path-Watcher startet erst beim nächsten Poll (≤5s) neu. Das Frontend pollt deshalb `/api/health`. Wer den Trigger durch direkten `systemctl restart` ersetzt, killt die noch laufende Response.
- **Rollback-Backup wird IMMER erstellt** (auch wenn der Restore später scheitert) — der Auto-Rollback ist die letzte Rettung. Die Erstellung passiert NACH `validate_archive`, damit nicht für ein kaputtes Upload-Archiv unnötig gesichert wird.

### User-Restore — Owner-Gates (#182/#183)
- **Doppeltes Gate pro Entität**: existiert die ID schon → DB-Owner muss == username; existiert sie nicht → Archiv-`config.json`-Owner muss == username. Das verhindert (a) Überschreiben fremder Agents/Projekte und (b) "Claiming" fremder IDs durch ein präpariertes Archiv. **Bricht** man die Reihenfolge (Workspaces vor Agents), greift das Gate ins Leere, weil die DB-Ownership noch nicht aktualisiert ist — daher die feste Reihenfolge in `restore_user_archive`.
- **`extractall(filter="data")`** ist Pflicht bei Restore aus fremder Quelle — lehnt absolute/eskapierende Symlinks, Hardlinks, Device-Nodes, setuid ab (Tarball-Path-Traversal). System-Restore und User-Restore nutzen beide diesen Filter.
- **`INSERT OR IGNORE`** für Sessions/Messages: kein Überschreiben existierender Daten. Restore ist additiv, nicht destruktiv (anders als System-Restore, der ersetzt).

### Tailscale — Verdrahtung & Gotchas
- **`--accept-routes` default OFF** (sowohl in `control.up` als auch im Install-Modul): Mit accept-routes pushen Tailnet-Subnet/Exit-Routes auf den Host, das LAN-Default-Interface verschwindet aus `ip route get` → der Server ist LAN-seitig unerreichbar. Das ist die kritischste Falle hier. Opt-in nur via `HH_TAILSCALE_ACCEPT_ROUTES=yes` (Install) — die UI-`up()` bietet es gar nicht erst an.
- **Operator statt sudoers**: `tailscale set --operator=$HH_USER` erlaubt dem Service `up/logout/status` direkt über `/run/tailscale/tailscaled.sock` ohne sudo — funktioniert sogar mit `NoNewPrivileges=true`. Die alte sudoers-Regel wird aktiv gelöscht. Wer auf sudo zurückbaut, bricht den NoNewPrivileges-Service.
- **api_key NIE ans Frontend**: `public_config()` gibt nur `{configured, tailnet}`. Es gibt bewusst keinen GET der den Key (auch maskiert) zurückgibt — Test `test_admin_config_get_never_returns_key` zementiert das. Speicherung chmod 0600, atomar (tmp + replace).
- **Invite-Mechanik**: `reusable=False, ephemeral=False, preauthorized=True, expirySeconds=86400` — Single-Use, 24h, vorautorisiert (kein Admin-Approval nötig beim Beitritt). Der `key` aus der Response wird 1:1 durchgereicht; der Empfänger nutzt ihn als `tailscale up --authkey`.
- **Install wirft kein RuntimeError**: Fehler kommen als `rc != 0` + `output`-Tail zurück, damit das Frontend differenziert melden kann (nicht nur 500). `INSTALL_TIMEOUT=120s` weil `apt + curl|sh` auf langsamem Link dauert.
- **`install.py` ruft `sudo -n bash` ohne neuen sudoers-Eintrag**: nutzt die NOPASSWD-Regel für `/bin/bash`, die schon aus `50-systemd.sh` (Extensions-Manager) existiert. Wer die entfernt, bricht den Install-Button.

### Samba — Verdrahtung & Gotchas
- **`_index.conf`-Umweg**: Samba kann KEINE Verzeichnis-Includes. Deshalb schreibt jedes enable/disable ein Aggregator-`_index.conf` mit `include = <jede-conf>`, und `smb.conf` inkludiert nur `_index.conf`. Wer direkt ein Verzeichnis-Include in `smb.conf` setzt, bricht Samba (das alte Verhalten wird im Modul aktiv per `sed` bereinigt).
- **Gegenseitige Gruppen-Membership** (kritisch): Samba-User `hh` muss in Gruppe `hydrahive` sein, sonst ACCESS_DENIED beim Path-Traversal durch `/var/lib/hydrahive2` (750 hydrahive:hydrahive). UND `hydrahive` muss in Gruppe `hh` sein für Backend-Write auf `/etc/samba/hh-projects.d`. Plus setgid-Bit (2775) auf alle Workspace-Dirs, damit neue Sub-Dirs die Gruppe erben + 664/2775 Masks. Ohne das funktioniert der Share nicht oder ist read-only. **Das ist der häufigste Samba-Bruch.**
- **`render_share` ist der einzige Per-User-Refactor-Punkt**: MVP nutzt einen gemeinsamen `samba_user` für alle Projekte (`valid users`/`force user` = samba_user). Beim späteren Per-User-Auth-Refactor wird NUR `render_share` umgebaut (dynamische `valid users` je nach Projekt-Members). Dieser Single-Point ist Absicht (Co-location).
- **`_safe_share_name` Fallback** `hh_<id[:8]>`: bei leerem/zu-langem Namen — verhindert kaputte smb.conf durch Sonderzeichen oder zu lange Section-Header.
- **Setup via Trigger-File, nicht direkt**: Der Backend-Service hat nicht die Rechte für `apt install` / `useradd` / `smbpasswd`. Der Trigger `.samba_setup_request` wird vom root-laufenden systemd-Service aufgegriffen (Bridge/Voice-Pattern). Wer Setup synchron im Backend macht, scheitert an Permissions.
- **Passwort im Klartext im Status**: `GET /system/samba/status` und `GET /projects/{id}/samba` geben das Samba-Passwort im Klartext zurück (nötig zum Anzeigen/Kopieren in der UI). Das ist bewusst, aber beide Endpoints sind gegated (require_admin bzw. Member/Owner/Admin). Wer den Gate lockert, leakt das Passwort.
- **Per-Projekt-Enabled doppelt geprüft**: `samba_enabled`-Flag in Projekt-Config UND Config-File-Existenz müssen beide stimmen (`projects_samba.py:38`). Verhindert Drift wenn das File manuell gelöscht wurde aber das Flag noch steht.

### Net (SSRF) — Verdrahtung & Invarianten
- **DNS-Rebinding-Schutz durch IP-Pinning** (#206): `resolve_validated_ip` löst EINMAL auf, `_PinnedTransport` connectet zur GEPRÜFTEN IP — kein 2. DNS-Lookup zwischen Check und Connect (TOCTOU geschlossen). Wer `safe_async_client` durch einen normalen `httpx.AsyncClient` ersetzt, öffnet DNS-Rebinding wieder.
- **`pin_request` behält SNI + Host-Header**: URL.host wird auf die IP umgeschrieben (TCP geht dorthin), aber `sni_hostname`-Extension + `Host`-Header bleiben auf dem Original-Namen — sonst bricht TLS-Cert-Validierung und Server-Routing (vhosts).
- **`follow_redirects=False` ist Pflicht**: ein 30x auf eine interne URL würde den Vorab-Check umgehen. Wer Redirects aktiviert, hat ein SSRF-Loch.
- **ALLE A-Records geprüft**: `resolve_validated_ip` blockt wenn IRGENDEINE aufgelöste IP intern ist (Multi-A-Record-Bypass). Es reicht nicht, nur die erste IP zu prüfen.
- **IPv4-mapped-IPv6-Normalisierung**: `::ffff:127.0.0.1` wird auf `127.0.0.1` normalisiert, sonst Bypass über mapped-Adressen (Test `test_resolve_blocks_ipv4_mapped_ipv6_*`).
- **Zwei Validierungs-Pfade**: `validate_outbound_url`/`is_blocked_host` (schneller Vorab-Check, KEIN Pinning — TOCTOU-anfällig wenn allein genutzt) vs. `resolve_validated_ip`/`safe_async_client` (Pinning, rebinding-sicher). http_post nutzt beide (Vorab-Check als schnelles Fail), fetch_url nur den sicheren Client. **Falle**: `is_blocked_host` allein ist NICHT rebinding-sicher — nur als Vorfilter verwenden.

### Allgemein
- Alle Infra-Endpoints sind admin-gegated außer User-Backup (require_auth) und Per-Projekt-Samba (Member/Owner/Admin). System-Cards im Frontend werden nur bei `role === "admin"` gerendert (`SystemPage.tsx:139-142`).
- Error-Envelope durchgängig über `coded(status, code, **params)` → `{detail: {code, params}}` (`errors.py:21`). Backup/User-Restore werfen typisierte Exceptions (`RestoreError`/`RestoreTooLarge`/`UserRestoreError`) die in den Routes auf HTTP-Codes gemappt werden.

---

## Datenmodell

### Manifest (System-Backup) — `manifest.json` im Tar
| Feld | Wert |
|------|------|
| `version` | `"1"` (`ARCHIVE_VERSION`) |
| `kind` | `"system"` |
| `created_at` | Timestamp `%Y%m%d-%H%M%S` |
| `hostname` | aus `/etc/hostname`, Fallback `"unknown"` |

### Manifest (User-Backup) — `manifest.json` im Tar
| Feld | Wert |
|------|------|
| `version` | `"1"` |
| `kind` | `"user"` |
| `username` | Owner |
| `created_at` | Timestamp |

### Tar-Layout System-Backup
```
manifest.json
db/sessions.db          (sqlite3.backup-Snapshot, optional)
data/agents/...
data/projects/...
data/plugins/...
data/whatsapp/...
config/...
skipped.json            (nur wenn Dateien übersprungen wurden)
```

### Tar-Layout User-Backup
```
manifest.json
sessions.json           (Sessions + Messages serialisiert)
agents/<id>/...
projects/<id>/...
workspaces/master/<id>/...
workspaces/specialists/<id>/...
workspaces/projects/<id>/...
whatsapp.json
butler/<flow_id>.json
```

### Auto-Rollback-Artefakt
- `<data_dir>/.backup-rollback-<epoch>.tar.gz` (vom Exclude-Filter erfasst, nicht in Folge-Backups)

### Trigger-Files (in `$HH_DATA_DIR`)
| File | Konsument | Zweck |
|------|-----------|-------|
| `.restart_request` | `hydrahive2-restart.service` | Service-Neustart nach Restore |
| `.samba_setup_request` | `hydrahive2-samba.service` | Samba-Setup als root |

### Tailscale-Config — `<config_dir>/tailscale-admin.json` (chmod 0600)
| Feld | Wert |
|------|------|
| `api_key` | Tailscale Admin-API-Key (nie ans Frontend) |
| `tailnet` | Tailnet-Name, default `"-"` |

### Tailscale-Status (Response-Shape)
`installed, connected, backend_state, ip, hostname, dns_name, tailnet, version, magic_dns, auth_url, peers[], exit_node_active, error`
Peer: `hostname, dns_name, ip, online, os, exit_node, exit_node_option, last_seen`

### Tailscale-Invite (Response)
`auth_key, expires, id` (24h, single-use, preauthorized)

### Samba — Per-Projekt-Config `<samba_includes_dir>/<project_id>.conf`
smb.conf-Block: `[<safe_name>]`, `comment`, `path=<workspace>`, `browseable=yes`, `read only=no`, `valid users=<samba_user>`, `force user=<samba_user>`, `create mask=0664`, `directory mask=0775`

### Samba — Aggregator `<samba_includes_dir>/_index.conf`
Zeilen `include = <pfad>` für jede Per-Projekt-`*.conf`

### Samba — Status (Response)
`installed, running, user, password_set, includes_dir, includes_dir_exists` (+ `password` nur über System-/Projekt-Endpoint)

### Projekt-Config — relevantes Feld
- `samba_enabled: bool` (in `projects/<id>/config.json`, gesetzt durch `project_config.update`)

### Config-Keys / Env-Vars
| Env-Var | Default | Settings-Property |
|---------|---------|-------------------|
| `HH_BASE_DIR` | `/opt/hydrahive2` | `base_dir` |
| `HH_DATA_DIR` | `/var/lib/hydrahive2` | `data_dir` |
| `HH_CONFIG_DIR` | `/etc/hydrahive2` | `config_dir` |
| `HH_LOG_DIR` | `/var/log` | `log_dir` |
| `HH_SAMBA_INCLUDES_DIR` | `/etc/samba/hh-projects.d` | `samba_includes_dir` |
| `HH_SAMBA_USER` | `hh` | `samba_user` |
| `HH_SAMBA_PASSWORD_FILE` | `<config_dir>/samba.password` | `samba_password_file` |
| `HH_SAMBA_LOG` | `/var/log/hydrahive2-samba.log` | `samba_log_path` |
| `HH_INSTALL_TAILSCALE` | `yes` | (Install-Modul-Env) |
| `HH_TAILSCALE_AUTHKEY` | leer | (Install-Modul) |
| `HH_TAILSCALE_ACCEPT_ROUTES` | `no` | (Install-Modul) |
| `HH_USER` | `hydrahive` | (Install-Module, Operator) |
| `HH_INSTALL_SAMBA` / `HH_SKIP_SAMBA` | `yes` / `no` | (Samba-Modul) |
| (abgeleitet) | `<data_dir>/sessions.db` | `sessions_db` |
| (abgeleitet) | `<data_dir>/agents|projects|plugins` | `agents_dir`/`projects_dir`/`plugins_dir` |

### Backup-Caps (Konstanten)
`MAX_UPLOAD_BYTES = 2 GiB`, `MAX_EXTRACTED_BYTES = 8 GiB`, `MAX_MEMBERS = 100_000`, `_CHUNK = 1 MiB`

### Tailscale-Konstanten
`TS_API_BASE = https://api.tailscale.com/api/v2`, `INVITE_EXPIRY_S = 86400`, `INSTALL_TIMEOUT = 120.0`

### SSRF-Konstanten
`ALLOWED_SCHEMES = {http, https}`; `BLOCKED_RANGES` (8 Netze); `BLOCKED_HOSTNAMES` (4 Einträge)

---

## Offene Enden

- **Samba Per-User-Auth ungelöst** (mehrfach als "Issue: TBD" / "spätere Refactor" markiert): `samba/__init__.py:7`, `_infra.py:18`, `manager.py:49`. MVP nutzt EINEN gemeinsamen `samba_user` für alle Projekte — kein echtes Mapping HH-User → Samba-User. Single-Refactor-Point ist `render_share`, aber das Issue hat noch keine Nummer.
- **Samba-Passwort im Klartext** über zwei Endpoints (`system_samba.py:33`, `projects_samba.py:42`) — funktional nötig fürs UI-Copy, aber sensibel. Liegt zudem als Klartext-File `samba.password` (chmod 0600). Kein Rotations-Mechanismus.
- **`db_arcname()` Inkonsistenz**: `restore.py:55-59` baut `db_src = extract_root / db_arc` (= `extract_root/db/sessions.db`), während `data_subdirs` über `arcname.split("/",1)[1]` aus `extract_root/data/...` liest. Funktioniert, aber zwei verschiedene Pfad-Auflösungs-Stile nebeneinander.
- **`_check_sqlite_in_tar` Temp-File-Leak-Risiko**: `NamedTemporaryFile(delete=False)` (`validate.py:74`) — wird im `finally` mit `unlink(missing_ok=True)` gelöscht, aber bei einem Crash zwischen `tmp.name`-Zuweisung und try-Block bliebe es liegen. Praktisch unkritisch.
- **User-Restore `_copy_tree` überschreibt** existierende Files (`shutil.copy2`), obwohl der Docstring von `user_restore.py:5` sagt "existierende Dateien bleiben erhalten". Drift zwischen Doc und Code: Sessions/Messages sind additiv (`INSERT OR IGNORE`), aber Workspace-/Config-Files werden überschrieben. Das Owner-Gate verhindert nur FREMDE Überschreibung, nicht die eigene.
- **`validate.py` re-deklariert `ARCHIVE_VERSION`/`MANIFEST_NAME`** lokal (`validate.py:16-17`) statt aus `archive.py` zu importieren — DRY-Bruch, drei Stellen halten `"1"` (`archive.py:25`, `validate.py:16`, `user_archive.py:27`). Bei Version-Bump müssen alle drei angefasst werden.
- **`RestoreError` in `backup.py:25` importiert aber `restore.py:25` re-importiert dasselbe** — und `restore.py` importiert `RestoreError` ohne es zu verwenden (Validation wirft es, Restore fängt es nicht selbst; es propagiert zur Route). Toter Import in `restore.py`.
- **Tailscale `magic_dns`** wird aus `MagicDNSSuffix` abgeleitet (`status.py:65`) und im Frontend-Typ deklariert (`_tailscaleTypes.ts:20`), aber nirgends im UI angezeigt — totes Feld.
- **Tailscale `auth_url`** (`status.py:67`) wird zurückgegeben und im Typ deklariert, aber das UI nutzt es nicht (interaktiver Login-Flow ist nicht verdrahtet — nur Auth-Key-Flow). Halbfertiger interaktiver Login.
- **`net/__init__.py`, `backup/__init__.py`, `tailscale/__init__.py` sind leer** — kein Package-Level-Re-Export (anders als `samba/__init__.py`). Konsumenten importieren direkt aus Submodulen. Inkonsistente Konvention.
- **`_reload_smbd` failt leise** (`manager.py:79`) — enable/disable_share returnen `(True, "")` auch wenn der Reload fehlschlug. Der Share ist dann in der Config aber smbd hat ihn noch nicht geladen, bis zum nächsten Reload/Restart. Kein Feedback ans UI.
- **Doppelte `BackupCard`-Logik**: System-`BackupCard` (Admin) und Profile-`BackupRestoreCard` (User) implementieren Download-Blob-Logik fast identisch, plus `systemApi.downloadBackup` vs. `profileApi.downloadBackup` — leichte Drift (Filename-Regex unterschiedlich). Kandidat für gemeinsamen Helper.
- **`samba_status` ruft `systemctl is-active smbd`** ohne sudo (`manager.py:136`) — funktioniert nur wenn der Service-User das darf; bei Fehler still `running=False`. Kein Unterschied zwischen "nicht laufend" und "darf nicht prüfen".
- **`is_blocked_host` als öffentliche API** (in `fetch_url` als `_is_blocked` importiert, `test_ssrf_guard.py` prüft Importierbarkeit) ist NICHT rebinding-sicher, lebt aber neben dem sicheren `safe_async_client`. Wer es als alleinige Schutzschicht nutzt, hat ein TOCTOU-Loch — die Doku in `ssrf.py:6` warnt davor ("unmittelbar vor dem Connect aufrufen"), aber die Funktion erzwingt es nicht.
