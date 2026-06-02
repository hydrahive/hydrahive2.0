# Projects

Das **Projects**-Subsystem ist die zweite Ebene der 3-Ebenen-Architektur (Masteragent → Projektagent → Spezialist). Ein Projekt = isolierter Workspace + automatisch gekoppelter Project-Agent + Members-Liste + optionale Infrastruktur (Git-Repos, Samba-Share, VM/Container-Assignments). Projekt-Configs leben als JSON auf der Platte (`config.json`), nicht in der DB; nur Audit-Log und Server-Assignments sind DB-gebunden.

---

## WAS

### Core-Modul (`core/src/hydrahive/projects/`)

- **`config.create(...)`** — Legt ein Projekt an: validiert Name + Members, generiert `uuid7()`-ID, erstellt `project_dir/config.json`, erstellt Workspace-Verzeichnis (setgid 02775), optional `git init`, erstellt automatisch einen gekoppelten **Project-Agent** (`agent_type="project"`, temperature 1.0, max_tokens 16000, thinking_budget 0), generiert ein `webhook_secret` (`secrets.token_urlsafe(32)`), und ruft `sync_links_for_project` (Master-Symlinks).
- **`config.update(project_id, **changes)`** — Patcht ein Projekt; schützt `id`, `agent_id`, `created_at`, `created_by` (werden aus changes gepoppt); validiert `name`/`status`/`members` falls geändert; setzt `updated_at`; re-synct Symlinks bei `members`/`name`-Änderung.
- **`config.delete(project_id)`** — Cascade-Delete: löscht Project-Agent, setzt VM/Container-`project_id` auf NULL (Server bleiben dem Owner), deaktiviert Samba-Share, `rmtree` Workspace + Project-Verzeichnis, re-synct Symlinks für alle betroffenen User.
- **`config.get(project_id)`** — Lädt + normalisiert eine Projekt-Config (oder `None`).
- **`config.list_all()`** — Alle Projekte (Admin), überspringt defekte JSON-Configs mit Warning.
- **`config.list_for_user(username)`** — Projekte wo User Member oder `created_by` ist.
- **`config._save_atomic(path, data)`** — Atomares Schreiben via `.json.tmp` + `replace`.
- **`config._normalize(cfg)`** — Füllt fehlende Felder mit Defaults (status, description, members, git_initialized, git_token, git_repos, samba_enabled, notes, tags, mcp_server_ids, allowed_plugins, allowed_specialists, llm_api_key, metadata, updated_at).
- **`members.add(project_id, username)`** — Fügt validierten User zur Members-Liste hinzu (idempotent), re-synct Symlinks für den User.
- **`members.remove(project_id, username)`** — Entfernt User aus Members-Liste (idempotent), re-synct Symlinks.
- **`audit.log(project_id, user_id, action, target, details)`** — Append-only Audit-Eintrag; schluckt alle Fehler (Audit darf Hauptoperation nie brechen).
- **`audit.list_for_project(project_id, action, user_id, limit)`** — Audit-Einträge neueste zuerst, optional gefiltert nach action/user.
- **`_validation.validate_name`** — Name nicht leer, max 200 Zeichen.
- **`_validation.validate_status`** — Status ∈ {active, paused, archived}.
- **`_validation.validate_member` / `validate_members`** — User muss in `users_module.list_users()` existieren.
- **`_paths.projects_root()`** — `data_dir/projects`.
- **`_paths.project_dir(id)`** — `data_dir/projects/<id>`.
- **`_paths.config_path(id)`** — `<project_dir>/config.json`.
- **`_paths.workspace_path(id)`** — `data_dir/workspaces/projects/<id>` (NICHT unter `projects/`!).
- **`_paths.ensure_workspace(id)`** — Erstellt Workspace mit Mode 02775 (setgid), chmod idempotent, weiches Fail bei OSError.
- **`_git.init_repo(path)`** — `git init -q`.
- **`_git.is_valid_name(name)`** — Repo-Name ∈ `_root` oder Regex `^[a-z0-9][a-z0-9_-]{0,49}$`.
- **`_git.repo_path_for(workspace, repo_name)`** — `_root` → Workspace selbst, sonst `workspace/<name>`.
- **`_git.repo_status(path)`** — Branch, remote_url, ahead/behind, letzte 5 Commits.
- **`_git.list_repos(workspace)`** — Alle Subdirs mit `.git/` + implizites `_root` falls `workspace/.git/` existiert.
- **`_git_ops.clone_into(workspace, repo_name, url, branch, token)`** — Klont in Subdir; injiziert Token in URL; setzt Remote nach Clone wieder auf saubere (token-freie) URL zurück.
- **`_git_ops.set_remote(repo_path, url)`** — `remote set-url`/`add origin`.
- **`_git_ops.commit_all(repo_path, message, author_name, author_email)`** — `add -A` + Commit mit Author-ENV; `no_changes` wenn Working Tree clean.
- **`_git_ops.push(repo_path, branch, token)`** — `push --set-upstream` mit Token-injizierter URL.
- **`_git_ops.pull(repo_path, branch, token)`** — `pull` mit Token-injizierter URL.

### API-Routen (alle Prefix `/api/projects`)

**`projects.py` — Projekt-CRUD + Members + Audit:**
- `GET  /api/projects` — Liste (Admin = alle, sonst eigene).
- `POST /api/projects` — Anlegen (**require_admin**), 201.
- `GET  /api/projects/{id}` — Details (access-checked).
- `PATCH /api/projects/{id}` — Update (**require_admin**), loggt `project_updated`.
- `DELETE /api/projects/{id}` — Löschen (**require_admin**), 204.
- `POST /api/projects/{id}/members/{username}` — Member hinzufügen (**require_admin**), loggt `member_added`.
- `DELETE /api/projects/{id}/members/{username}` — Member entfernen (**require_admin**), loggt `member_removed`.
- `GET  /api/projects/{id}/audit` — Audit-Spur (access-checked), Query `action`/`user`/`limit` (1–1000, default 200).

**`projects_info.py` — Read-Info:**
- `GET /api/projects/{id}/sessions` — Sessions des Projekts (User: eigene; Admin: alle des Project-Agents), gefiltert auf `project_id`.
- `GET /api/projects/{id}/stats` — Aggregat: total/active sessions, total messages, total tokens (nur role=assistant), last_activity.
- `GET /api/projects/{id}/agent` — Der gekoppelte Project-Agent.

**`projects_files.py` — Workspace-File-Browser (Read):**
- `GET /api/projects/{id}/files?path=` — Verzeichnislisting (name, type, size, modified), Dirs vor Files.
- `GET /api/projects/{id}/files/read?path=` — Datei-Inhalt als `PlainTextResponse`, max 100 KB, nur Text-Dateien (sonst 415), UTF-8 mit `errors="replace"`.

**`projects_files_write.py` — Workspace-File (Write/Upload/Delete):**
- `POST /api/projects/{id}/files/write` — Text schreiben (max 1 MB, nur Text-Dateien, erstellt Parent-Dirs).
- `POST /api/projects/{id}/files/upload?path=` — Multipart-Upload (max 10 MB, Filename ohne `/`/`\`).
- `DELETE /api/projects/{id}/files?path=` — Datei löschen (nicht Workspace-Root, keine Dirs).

**`projects_git_manage.py` — Git-Repo CRUD:**
- `GET /api/projects/{id}/git/repos` — Repo-Liste + `has_token`-Flag pro Repo.
- `POST /api/projects/{id}/git/repos/clone` — Klonen (Name muss valid + ≠ `_root` sein), speichert Token in `git_repos[name].git_token`, setzt `git_initialized=true`.
- `POST /api/projects/{id}/git/repos/init` — Leeres Repo anlegen (409 wenn Subdir existiert).
- `PUT /api/projects/{id}/git/repos/{repo}/config` — Remote-URL und/oder Token setzen.

**`projects_git_ops.py` — Git-Operationen:**
- `POST /api/projects/{id}/git/repos/{repo}/commit` — `commit_all`, Author = einloggter User (`{user}@hydrahive.local`).
- `POST /api/projects/{id}/git/repos/{repo}/push` — Push mit aufgelöstem Token.
- `POST /api/projects/{id}/git/repos/{repo}/pull` — Pull mit aufgelöstem Token.
- `DELETE /api/projects/{id}/git/repos/{repo}` — Repo löschen (`_root` verboten), 204, entfernt aus `git_repos`.

**`projects_git.py`** — Aggregator-Router (`include_router(manage)` + `include_router(ops)`).

**`projects_samba.py` — Samba-Toggle:**
- `GET /api/projects/{id}/samba` — enabled-Status, Share-Name, User, Klartext-Passwort.
- `PUT /api/projects/{id}/samba` — Share an/aus (Body `{enabled: bool}`).

**`projects_servers.py` — VM/Container-Assignments:**
- `GET /api/projects/{id}/servers` — Zugewiesene VMs + Container.
- `GET /api/projects/{id}/servers/available` — Eigene noch nicht zugewiesene VMs/Container.
- `POST /api/projects/{id}/servers/assign` — VM/Container zuweisen (409 wenn schon fremdem Projekt zugewiesen), loggt `server_assigned`.
- `DELETE /api/projects/{id}/servers/{kind}/{server_id}` — Assignment lösen, 204, loggt `server_unassigned`.

### Route-Helper

- **`_project_route_helpers.py`**: `ProjectCreate`/`ProjectUpdate` Pydantic-Models, `check_project_access`, `TEXT_FILE_EXTS`/`TEXT_FILE_NAMES`, `is_text_file`, `safe_workspace_path` (Path-Traversal-Guard).
- **`_git_helpers.py`**: `GitRepoConfig`/`GitRepoClone`/`GitRepoInit`/`GitCommit` Models, `project_or_404`, `repo_path_or_404`, `err_to_code` (Git-Fehler → HTTP-Code), `token_for` (Token-Auflösung: repo-spezifisch > `_root`-Fallback).
- **`_server_route_helpers.py`**: `ServerKind` Literal, `AssignRequest`, `project_or_404`, `vm_dict`/`container_dict` Serializer.

### Agent-facing Tools (Backend-LLM-Tools)

- **`tools/list_projects.py`** — Tool `list_projects`: listet Projekte des Owners mit Workspace-Pfad, Repos (name/remote_url/has_token), aufgelösten Specialists, Members, samba_enabled.
- **`tools/shell.py`** — Tool `shell_exec`: injiziert `GH_TOKEN` + `GITHUB_TOKEN` aus dem Projekt-Token (`_resolve_gh_token` → `_first_token_in`), filtert sensible ENV-Vars per Denylist.
- **`tools/ask_agent.py`** — Gating: Project-Agents dürfen nur in `allowed_specialists` freigegebene Spezialisten beauftragen.

### Cross-Subsystem-Verdrahtung

- **`agents/_workspace_links.py`** — `sync_links_for_user`/`sync_links_for_project`: setzt Symlinks `<master-workspace>/projects/<sanitized-name>` → `<project-workspace>`.
- **`samba/manager.py`** — `enable_share`/`disable_share`/`is_share_enabled`/`samba_status`/`share_name_for`/`render_share`/`_regenerate_index`/`_reload_smbd`.
- **`api/routes/system_samba.py`** — Globaler Samba-Status/Setup/Log (Admin-only): `GET/POST /api/system/samba/status|setup|log`.
- **`api/routes/butler.py`** — `POST /api/butler/webhooks/project/{id}`: Projekt-Webhook mit Secret-Auth (`webhook_secret`).
- **MCP** (`mcp-servers/hydrahive-api/`): `hh_list_projects`, `hh_list_files`, `hh_read_file` → REST-Proxy auf `/api/projects/*`.

### Frontend (`frontend/src/features/projects/`)

- **`ProjectsPage.tsx`** — Top-Level-Seite, Split-View (Form + `CollapsibleSidebar`-Liste + New-Dialog).
- **`ProjectList.tsx`** — Sidebar mit Suche (Name/Tags), Status-Pills, Member-Count, Git-Badge.
- **`NewProjectDialog.tsx`** — Anlege-Modal: Name, Beschreibung, Modell-Auswahl, Member-Toggles, init_git-Checkbox.
- **`ProjectForm.tsx`** — Detail-View mit 10 Tabs + dirty-aware Save (nur name/description/status).
- **`_OverviewTab.tsx`** — Beschreibung, Agent-Link, Workspace-Pfad, `TagEditor`, `MemberManager`, `WebhookQuickLink`, created_by.
- **`_NotesTab.tsx`** — Freitext-Notizen (`notes`).
- **`_FilesTab.tsx`** — File-Browser: Breadcrumbs, Up-Nav, Öffnen/Editieren (Textarea)/Speichern/Schließen, Upload, Delete.
- **`_SessionsTab.tsx`** — Projekt-Sessions, Klick → `/werkstatt/{sessionId}`.
- **`_GitTab.tsx`** — Repo-Liste + Add-Form.
- **`_GitRepoCard.tsx`** — Pro-Repo: Branch/ahead/behind-Pills, Commit-Input, Pull/Push, Commit-Historie, Settings-Toggle, Delete.
- **`_GitRepoSettings.tsx`** — Remote-URL + Token-Edit (Show/Hide), Delete (Danger Zone).
- **`_AddRepoForm.tsx`** — Clone (Name/URL/Branch/Token) oder Init-Empty; clientseitige Name-Validierung.
- **`_ServersTab.tsx`** — Assignment-Liste + Add-Form + Unassign.
- **`_ServerRow.tsx`** — VM/Container-Zeile, Status-Pill, Detail-Link (`/vms/{id}` / `/containers/{id}`), Unassign.
- **`_AddServerForm.tsx`** — Verfügbare Server zuweisen.
- **`_StatsTab.tsx`** — 4 Stat-Cards (Sessions, Messages, Tokens, Last Activity).
- **`_SettingsTab.tsx`** — Status-Select, `SambaSection`, `OverridesSection`, Delete-Project.
- **`_SettingsSamba.tsx`** — Share-Toggle, UNC-Pfad (`\\host\share`), User/Passwort mit Copy/Show.
- **`_SettingsOverrides.tsx`** — `mcp_server_ids`, `allowed_plugins`, `llm_api_key` (komma-getrennt).
- **`_SpecialistsTab.tsx`** — Specialist-Whitelist (`allowed_specialists`), AgentLink-Status-Warnung.
- **`_AuditTab.tsx`** — Audit-Log mit Action-/User-Filter.
- **`MemberManager.tsx`** — Member-Chips + Add-Select.
- **`api.ts`** — `projectsApi` (alle Endpoints) + `usersApi.list`.
- **`types.ts`** — `Project`, `ProjectCreate`, `ProjectSession`, `ProjectGitStatus`, `ProjectGitRepo`, `ServerKind`, `ProjectServer`, `ProjectStats`, `ProjectAuditEntry`, `ProjectAuditAction`.

### Config-Flags / Felder pro Projekt-Config

`id`, `name`, `description`, `members[]`, `agent_id`, `status`, `created_at`, `updated_at`, `created_by`, `git_initialized`, `git_token` (legacy `_root`), `git_repos{}`, `samba_enabled`, `notes`, `tags[]`, `mcp_server_ids[]`, `allowed_plugins[]`, `allowed_specialists[]`, `llm_api_key`, `metadata{}`, `webhook_secret`.

---

## WIE

### Projekt anlegen (Klick → DB/FS)
1. Frontend: `NewProjectDialog` lädt Modelle (`llmInfoApi.getModels`) + User (`usersApi.list`), Submit → `projectsApi.create`.
2. `POST /api/projects` (**require_admin**) → `ProjectCreate` → `project_config.create`.
3. `create`: `validate_name` + `validate_members` → `uuid7()` → Config-Dict (Status `active`, `webhook_secret`) → `project_dir().mkdir` → `ensure_workspace` (Mode 02775) → optional `init_repo` → `agent_config.create(agent_type="project", project_id=...)` → `agent_id` in Config → `_save_atomic` → `sync_links_for_project`.
4. **Invariante:** Project-Agent-Workspace (`agents/_paths.workspace_for` mit `type=="project"` → `data/workspaces/projects/<project_id>`) ist BYTE-IDENTISCH zum Projekt-Workspace (`projects/_paths.workspace_path` → `data/workspaces/projects/<project_id>`). Der Agent arbeitet direkt im Projekt-Workspace.
5. Frontend: `onCreated(id)` → `loadProjects(id)`.

### File lesen/schreiben (Path-Traversal-Guard)
1. `FilesTab` → `projectsApi.listFiles`/`readFile`/`writeFile`/`uploadFile`/`deleteFile`.
2. Route: `project_config.get` → `check_project_access` → `workspace_path(id)` → **`safe_workspace_path(workspace, rel)`**.
3. `safe_workspace_path`: `(workspace / rel).resolve()`, dann `resolved.relative_to(workspace.resolve())` — wirft `path_traversal` (400) wenn außerhalb. Workspace-Root selbst ist erlaubt.
4. Read: 100 KB Cap, `is_text_file`-Check (Extension oder Spezial-Name) sonst 415; Write: 1 MB; Upload: 10 MB.
5. `readFile` im Frontend nutzt rohes `fetch` (nicht `api.get`), weil die Antwort `text/plain` ist.

### Git-Clone mit Token-Injection
1. `AddRepoForm` → `cloneRepo(name, url, branch, token)`.
2. `clone_into`: `_inject_token(url, token)` → `https://x-access-token:<token>@github.com/...`; `git clone` mit `GIT_TERMINAL_PROMPT=0`; bei Fehler `rmtree`.
3. **Wichtig:** Nach erfolgreichem Clone wird der Remote per `remote set-url origin <url>` auf die **token-freie** URL zurückgesetzt — der Token landet NICHT in `.git/config`, sondern wird nur in der Projekt-Config (`git_repos[name].git_token`) persistiert und bei jedem Push/Pull frisch injiziert.
4. Config-Update: `git_repos[name] = {git_token}` + `git_initialized=true`.

### Token-Auflösung bei Push/Pull (`token_for`)
1. `git_repos[repo_name].git_token` (repo-spezifisch) hat Vorrang.
2. Falls `repo_name == "_root"` UND `project.git_token` (Top-Level legacy) gesetzt: dieser.
3. Sonst `None` (ungeauthter Push).

### Token-Auflösung im Shell-Tool (`_resolve_gh_token`)
1. Agent → `project_id` gesetzt (Project-Agent): direkt `_first_token_in(project)`.
2. Master-Agent (kein `project_id`): iteriert `list_for_user(owner)`, nimmt ersten Token. `_first_token_in` scannt erst alle `git_repos[*].git_token`, dann Top-Level `git_token`.
3. Token → `GH_TOKEN` + `GITHUB_TOKEN` im Shell-ENV (für `gh`/`git push` ohne extra Auth).

### Samba-Share an/aus
1. `PUT /api/projects/{id}/samba {enabled:true}` → `enable_share(id, name)`.
2. `enable_share`: prüft `samba_includes_dir.exists()` (sonst `samba_not_installed`/400), schreibt `<id>.conf` via `render_share`, `_regenerate_index` (schreibt `_index.conf` mit allen `include = <file>`-Zeilen — Samba kann keine Verzeichnis-Includes), `_reload_smbd` (`smbcontrol all reload-config`, leiser Fail).
3. Config: `samba_enabled=true`.
4. `GET /api/projects/{id}/samba`: `enabled` = `config.samba_enabled` AND `is_share_enabled` (Datei existiert) — beide müssen stimmen.
5. Globales Setup (`POST /api/system/samba/setup`) schreibt Trigger `data/.samba_setup_request`, den ein systemd-Service als root aufgreift (Bridge-Pattern); installiert Samba, legt User+Passwort an, patcht `smb.conf` mit `include = .../_index.conf`.

### Server-Assignment (Invariante: 1 Server = 0/1 Projekt)
1. `assign_server`: lädt VM/Container, Owner-Check (Nicht-Admin nur eigene), 409 wenn `project_id` bereits gesetzt (fremdes Projekt), `set_project(id, project_id)`.
2. `unassign`: `set_project(id, None)`, nur wenn `project_id == project_id`.
3. Beim Projekt-Delete: `clear_project_assignments` setzt `project_id=NULL` (Server bleiben dem Owner).

### Symlink-Sync (Master-Workspace ↔ Projekte)
1. `sync_links_for_user`: für jeden Master-Agent des Users werden in `<master-ws>/projects/` Symlinks gesetzt; erwartete = `{_safe_name(name,id): project_workspace(id)}` für alle Projekte des Users.
2. Tote/nicht-erwartete Symlinks werden entfernt; vorhandene Nicht-Symlinks (echte Dirs) werden mit Warning übersprungen.
3. `sync_links_for_project` (bei Create/Update/Delete): sammelt aktuelle Members + created_by + ALLE Master-Owner (für robustes Cleanup) und ruft `sync_links_for_user` je User.

### Projekt-Webhook (Butler)
1. `POST /api/butler/webhooks/project/{id}` mit Header `X-Webhook-Secret`.
2. Vergleich gegen `project.webhook_secret` via `secrets.compare_digest` (401 ohne Header wenn Secret gesetzt, 403 bei Mismatch).
3. `_project_flows`: nur Flows von autorisierten Ownern (created_by + members), `scope=="project"` UND `scope_id==project_id` UND enabled — Tenant-Isolation (Issue #178).

---

## WO

### Core-Modul
- `core/src/hydrahive/projects/__init__.py:7` — Re-Export `config`, `workspace_path`, `ProjectValidationError`.
- `core/src/hydrahive/projects/config.py:26` — `create(...)`.
- `core/src/hydrahive/projects/config.py:53` — `webhook_secret` Generierung.
- `core/src/hydrahive/projects/config.py:63` — Auto-Create Project-Agent (`agent_type="project"`, temperature 1.0, max_tokens 16000, thinking_budget 0).
- `core/src/hydrahive/projects/config.py:77` — `sync_links_for_project` nach Create.
- `core/src/hydrahive/projects/config.py:84` — `update(...)`, geschützte Felder Zeile 88.
- `core/src/hydrahive/projects/config.py:105` — `delete(...)`, Cascade Zeile 111–130.
- `core/src/hydrahive/projects/_config_io.py:13` — `_save_atomic`.
- `core/src/hydrahive/projects/_config_io.py:20` — `_normalize` (Default-Felder).
- `core/src/hydrahive/projects/_config_io.py:39` — `get`.
- `core/src/hydrahive/projects/_config_io.py:46` — `list_all`.
- `core/src/hydrahive/projects/_config_io.py:60` — `list_for_user`.
- `core/src/hydrahive/projects/members.py:10` — `add`.
- `core/src/hydrahive/projects/members.py:25` — `remove`.
- `core/src/hydrahive/projects/audit.py:18` — `log`.
- `core/src/hydrahive/projects/audit.py:43` — `list_for_project`.
- `core/src/hydrahive/projects/_validation.py:6` — `ProjectValidationError`.
- `core/src/hydrahive/projects/_validation.py:10` — `_VALID_STATUS`.
- `core/src/hydrahive/projects/_validation.py:13` — `validate_name`.
- `core/src/hydrahive/projects/_validation.py:27` — `validate_member`.
- `core/src/hydrahive/projects/_paths.py:16` — `WORKSPACE_DIR_MODE = 0o2775`.
- `core/src/hydrahive/projects/_paths.py:19` — `projects_root`.
- `core/src/hydrahive/projects/_paths.py:31` — `workspace_path` (`data/workspaces/projects/<id>`).
- `core/src/hydrahive/projects/_paths.py:35` — `ensure_workspace` (chmod).
- `core/src/hydrahive/projects/_git.py:13` — `ROOT_REPO = "_root"`.
- `core/src/hydrahive/projects/_git.py:14` — `NAME_RE`.
- `core/src/hydrahive/projects/_git.py:28` — `init_repo`.
- `core/src/hydrahive/projects/_git.py:40` — `is_valid_name`.
- `core/src/hydrahive/projects/_git.py:44` — `repo_path_for`.
- `core/src/hydrahive/projects/_git.py:52` — `repo_status`.
- `core/src/hydrahive/projects/_git.py:92` — `list_repos`.
- `core/src/hydrahive/projects/_git_ops.py:25` — `_inject_token` (Token-Injection in HTTPS-URL).
- `core/src/hydrahive/projects/_git_ops.py:31` — `_author_env`.
- `core/src/hydrahive/projects/_git_ops.py:43` — `clone_into`, Token-Reset Zeile 62–63.
- `core/src/hydrahive/projects/_git_ops.py:67` — `set_remote`.
- `core/src/hydrahive/projects/_git_ops.py:78` — `commit_all`.
- `core/src/hydrahive/projects/_git_ops.py:97` — `push`.
- `core/src/hydrahive/projects/_git_ops.py:109` — `pull`.

### API-Routen
- `core/src/hydrahive/api/routes/projects.py:20` — `list_projects`.
- `core/src/hydrahive/api/routes/projects.py:28` — `create_project` (require_admin).
- `core/src/hydrahive/api/routes/projects.py:47` — `get_project`.
- `core/src/hydrahive/api/routes/projects.py:59` — `update_project`.
- `core/src/hydrahive/api/routes/projects.py:76` — `delete_project`.
- `core/src/hydrahive/api/routes/projects.py:84` — `add_member`.
- `core/src/hydrahive/api/routes/projects.py:100` — `remove_member`.
- `core/src/hydrahive/api/routes/projects.py:114` — `get_project_audit`.
- `core/src/hydrahive/api/routes/projects_info.py:19` — `list_project_sessions`.
- `core/src/hydrahive/api/routes/projects_info.py:39` — `get_project_stats`.
- `core/src/hydrahive/api/routes/projects_info.py:74` — `get_project_agent`.
- `core/src/hydrahive/api/routes/projects_files.py:19` — `_MAX_READ = 100*1024`.
- `core/src/hydrahive/api/routes/projects_files.py:22` — `list_files`.
- `core/src/hydrahive/api/routes/projects_files.py:54` — `read_file`.
- `core/src/hydrahive/api/routes/projects_files_write.py:19` — `MAX_WRITE_BYTES`/`MAX_UPLOAD_BYTES`.
- `core/src/hydrahive/api/routes/projects_files_write.py:28` — `write_file`.
- `core/src/hydrahive/api/routes/projects_files_write.py:58` — `upload_file`.
- `core/src/hydrahive/api/routes/projects_files_write.py:88` — `delete_file`.
- `core/src/hydrahive/api/routes/projects_git.py:7` — Aggregator-Router.
- `core/src/hydrahive/api/routes/projects_git_manage.py:22` — `get_repos`.
- `core/src/hydrahive/api/routes/projects_git_manage.py:37` — `post_clone`.
- `core/src/hydrahive/api/routes/projects_git_manage.py:59` — `post_init`.
- `core/src/hydrahive/api/routes/projects_git_manage.py:79` — `put_repo_config`.
- `core/src/hydrahive/api/routes/projects_git_ops.py:21` — `post_commit`.
- `core/src/hydrahive/api/routes/projects_git_ops.py:39` — `post_push`.
- `core/src/hydrahive/api/routes/projects_git_ops.py:54` — `post_pull`.
- `core/src/hydrahive/api/routes/projects_git_ops.py:69` — `delete_repo`.
- `core/src/hydrahive/api/routes/projects_samba.py:19` — `SambaToggle`.
- `core/src/hydrahive/api/routes/projects_samba.py:32` — `get_samba`.
- `core/src/hydrahive/api/routes/projects_samba.py:53` — `put_samba`.
- `core/src/hydrahive/api/routes/projects_servers.py:25` — `list_assigned`.
- `core/src/hydrahive/api/routes/projects_servers.py:39` — `list_available`.
- `core/src/hydrahive/api/routes/projects_servers.py:58` — `assign_server`.
- `core/src/hydrahive/api/routes/projects_servers.py:89` — `unassign_server`.

### Route-Helper
- `core/src/hydrahive/api/routes/_project_route_helpers.py:11` — `ProjectCreate`.
- `core/src/hydrahive/api/routes/_project_route_helpers.py:19` — `ProjectUpdate`.
- `core/src/hydrahive/api/routes/_project_route_helpers.py:27` — `check_project_access`.
- `core/src/hydrahive/api/routes/_project_route_helpers.py:35` — `TEXT_FILE_EXTS`.
- `core/src/hydrahive/api/routes/_project_route_helpers.py:42` — `TEXT_FILE_NAMES`.
- `core/src/hydrahive/api/routes/_project_route_helpers.py:49` — `is_text_file`.
- `core/src/hydrahive/api/routes/_project_route_helpers.py:55` — `safe_workspace_path` (Path-Traversal-Guard).
- `core/src/hydrahive/api/routes/_git_helpers.py:33` — `project_or_404`.
- `core/src/hydrahive/api/routes/_git_helpers.py:42` — `repo_path_or_404`.
- `core/src/hydrahive/api/routes/_git_helpers.py:51` — `err_to_code`.
- `core/src/hydrahive/api/routes/_git_helpers.py:63` — `token_for`.
- `core/src/hydrahive/api/routes/_server_route_helpers.py:12` — `ServerKind`.
- `core/src/hydrahive/api/routes/_server_route_helpers.py:20` — `project_or_404`.
- `core/src/hydrahive/api/routes/_server_route_helpers.py:29` — `vm_dict`.
- `core/src/hydrahive/api/routes/_server_route_helpers.py:38` — `container_dict`.

### Router-Registrierung
- `core/src/hydrahive/api/main.py:42–48` — Imports der 7 Projekt-Router.
- `core/src/hydrahive/api/main.py:117–122` — `include_router` (info, files, files_write, git, samba, servers). (Haupt-`projects_router` separat eingebunden.)
- `core/src/hydrahive/api/main.py:146` — `system_samba_router`.

### Cross-Subsystem
- `core/src/hydrahive/agents/_workspace_links.py:24` — `_safe_name`.
- `core/src/hydrahive/agents/_workspace_links.py:45` — `sync_links_for_user`.
- `core/src/hydrahive/agents/_workspace_links.py:82` — `sync_links_for_project`.
- `core/src/hydrahive/agents/_paths.py:8` — `workspace_for`.
- `core/src/hydrahive/agents/_paths.py:20–22` — Project-Agent-Workspace = `data/workspaces/projects/<project_id>` (= Projekt-Workspace!).
- `core/src/hydrahive/agents/config.py:35` — `create(..., project_id=None)`.
- `core/src/hydrahive/agents/config.py:61` — `cfg["project_id"] = project_id`.
- `core/src/hydrahive/samba/manager.py:24` — `_safe_share_name`.
- `core/src/hydrahive/samba/manager.py:36` — `_regenerate_index`.
- `core/src/hydrahive/samba/manager.py:48` — `render_share` (Share-Block).
- `core/src/hydrahive/samba/manager.py:66` — `_reload_smbd`.
- `core/src/hydrahive/samba/manager.py:84` — `enable_share`.
- `core/src/hydrahive/samba/manager.py:98` — `disable_share`.
- `core/src/hydrahive/samba/manager.py:110` — `is_share_enabled`.
- `core/src/hydrahive/samba/manager.py:130` — `samba_status`.
- `core/src/hydrahive/api/routes/system_samba.py:27` — `GET /api/system/samba/status`.
- `core/src/hydrahive/api/routes/system_samba.py:39` — `POST /api/system/samba/setup`.
- `core/src/hydrahive/api/routes/system_samba.py:50` — `GET /api/system/samba/log`.
- `core/src/hydrahive/api/routes/butler.py:111` — `project_webhook`.
- `core/src/hydrahive/api/routes/butler.py:128–133` — Secret-Validierung.
- `core/src/hydrahive/api/routes/butler.py:151` — `_project_flows` (Tenant-Isolation).
- `core/src/hydrahive/tools/shell.py:42` — `_first_token_in`.
- `core/src/hydrahive/tools/shell.py:50` — `_resolve_gh_token`.
- `core/src/hydrahive/tools/shell.py:107` — `_build_env` (GH_TOKEN/GITHUB_TOKEN).
- `core/src/hydrahive/tools/list_projects.py:21` — Tool-Execute.
- `core/src/hydrahive/tools/ask_agent.py:121–133` — Specialist-Gating für Project-Agents.

### DB / Migrations
- `core/src/hydrahive/db/migrations/024_project_audit_log.sql:4` — `project_audit_log` Tabelle.
- `core/src/hydrahive/db/migrations/024_project_audit_log.sql:13` — Index `idx_project_audit_project`.
- `core/src/hydrahive/db/migrations/005_project_assignments.sql:7–8` — `vms.project_id`, `containers.project_id`.
- `core/src/hydrahive/db/migrations/005_project_assignments.sql:10–11` — Indizes.
- `core/src/hydrahive/vms/db.py:84` — `set_project`.
- `core/src/hydrahive/vms/db.py:92` — `list_for_project`.
- `core/src/hydrahive/vms/db.py:101` — `clear_project_assignments`.
- `core/src/hydrahive/containers/db.py:122` — `set_project`.
- `core/src/hydrahive/containers/db.py:130` — `list_for_project`.
- `core/src/hydrahive/containers/db.py:139` — `clear_project_assignments`.

### Settings / Env
- `core/src/hydrahive/settings/_paths.py:32` — `projects_dir`.
- `core/src/hydrahive/settings/_infra.py:11` — `samba_includes_dir` (`HH_SAMBA_INCLUDES_DIR`, default `/etc/samba/hh-projects.d`).
- `core/src/hydrahive/settings/_infra.py:17` — `samba_user` (`HH_SAMBA_USER`, default `hh`).
- `core/src/hydrahive/settings/_infra.py:23` — `samba_password_file` (`HH_SAMBA_PASSWORD_FILE`).
- `core/src/hydrahive/settings/_paths.py:121` — `samba_log_path` (`HH_SAMBA_LOG`).

### Installer
- `installer/modules/47-samba.sh` — Samba-Setup (User, smb.conf-Patch, Workspace-Permissions 2775/664).

### Frontend
- `frontend/src/features/projects/ProjectsPage.tsx:10` — `ProjectsPage`.
- `frontend/src/features/projects/ProjectForm.tsx:23` — `Tab`-Union (10 Tabs).
- `frontend/src/features/projects/ProjectForm.tsx:40` — `dirty`-Logik (nur name/description/status).
- `frontend/src/features/projects/api.ts:4` — `projectsApi`.
- `frontend/src/features/projects/api.ts:12` — `readFile` (rohes fetch wegen text/plain).
- `frontend/src/features/projects/types.ts:1` — `Project`-Interface.
- `frontend/src/features/projects/_OverviewTab.tsx:118` — `WebhookQuickLink` (`/api/butler/webhooks/project/{id}`).
- `frontend/src/features/projects/_AddRepoForm.tsx:15` — `NAME_RE` (Mirror der Backend-Regex).
- `frontend/src/i18n/locales/{de,en}/projects.json` — i18n-Namespace `projects`.

### MCP
- `mcp-servers/hydrahive-api/server.py:105` — `hh_list_projects`.
- `mcp-servers/hydrahive-api/server.py:111` — `hh_list_files`.
- `mcp-servers/hydrahive-api/server.py:117` — `hh_read_file`.
- `mcp-servers/hydrahive-api/tools/workspace.py:6` — `list_projects` REST-Proxy.

### Tests
- `core/tests/test_project_audit.py` — 9 Tests für Audit-Log.

---

## WARUM

### Invarianten / nicht-offensichtliche Verdrahtung

- **Project-Workspace == Project-Agent-Workspace.** `projects/_paths.workspace_path(id)` und `agents/_paths.workspace_for(agent)` (für `type=="project"`) erzeugen denselben Pfad `data/workspaces/projects/<project_id>`. Wer einen dieser beiden Pfad-Builder ändert, muss beide ändern, sonst arbeitet der Project-Agent in einem leeren/falschen Verzeichnis. Beim Agent ist der Fallback `agent.get("project_id") or agent_id` — wenn `project_id` fehlt, würde der Agent in `projects/<agent_id>` landen (kein Match mit dem Projekt).

- **Config-as-JSON, nicht DB.** Projekte sind reine FS-Configs (`config.json`). Nur `project_audit_log` und die `project_id`-Spalten auf `vms`/`containers` sind DB-gebunden. Kein referenzielles Constraint zwischen Config und DB — ein gelöschtes Projekt mit verwaisten Audit-Zeilen oder Server-Assignments ist möglich, wenn `delete()` halb durchläuft. `delete()` ist NICHT transaktional über FS+DB.

- **Token wird NIE in `.git/config` persistiert.** `clone_into` resettet den Remote nach dem Klonen auf die token-freie URL (`_git_ops.py:62`). Der Token lebt nur in der Projekt-Config und wird bei jedem Push/Pull frisch injiziert (`_inject_token`). Das verhindert Token-Leak über `cat .git/config` im Workspace (den Agents lesen können). **Falle:** `_inject_token` greift nur bei `https://`-URLs — SSH-Remotes (`git@…`) werden nie geauthet, Push/Pull schlägt dann still fehl.

- **`_root` ist ein virtuelles Legacy-Repo.** Vor der Multi-Repo-Umstellung lag `.git/` direkt im Workspace-Root. `list_repos` exposed das als `_root`. `_root` kann nicht gelöscht (`git_cannot_delete_root`) oder neu angelegt/geklont werden. Sein Token sitzt top-level in `config.git_token` statt in `git_repos`. `token_for` und `_first_token_in` haben beide diesen Doppel-Pfad einprogrammiert — wer das Token-Schema vereinheitlicht, muss beide anfassen.

- **Samba braucht `_index.conf`-Aggregator.** Samba kann keine Verzeichnis-Includes. Daher schreibt jedes enable/disable `_regenerate_index()` neu, das alle `*.conf` (außer `_index.conf` selbst) per `include = <abspfad>` listet. `smb.conf` inkludiert nur `_index.conf`. Wer eine `<id>.conf` von Hand löscht ohne `_regenerate_index`, hinterlässt eine tote `include`-Zeile → Samba-Reload-Fehler.

- **Samba-`enabled` ist doppelt verifiziert.** `get_samba` liefert `enabled = config.samba_enabled AND is_share_enabled(id)` (Config-Flag UND tatsächlich existierende `.conf`-Datei). So driftet die UI nicht, wenn die Datei extern verschwindet, aber das Config-Flag noch `true` ist.

- **Setgid 02775 auf Workspaces ist die Samba-Schreibvoraussetzung.** Der gemeinsame Samba-User ist per `usermod -aG hydrahive` Mitglied der hydrahive-Gruppe. Ohne setgid würden tief geschachtelte Sub-Dirs die Default-Gruppe des Erzeugers erben statt hydrahive → Samba-Schreibzugriff bricht mit ACCESS_DENIED. `ensure_workspace` chmod't idempotent, der Installer zieht bestehende Workspaces per `find -exec chmod` nach.

- **Webhook-Secret-Backward-Compat.** `project_webhook` erzwingt das Secret nur, wenn `webhook_secret` in der Config gesetzt ist. Alt-Projekte ohne Secret laufen im unsicheren Modus (Deprecation-Phase). `create()` setzt das Secret seit der Webhook-Härtung immer — nur via `_normalize` geladene Alt-Configs ohne Secret nutzen den Legacy-Pfad. `_normalize` setzt KEIN `webhook_secret`-Default (anders als die übrigen Felder), d.h. Alt-Configs behalten ihren secret-losen Zustand.

- **Member-Permissions kommen über Symlinks, nicht ACLs.** SPEC.md:150–151: keine Linux-Gruppe pro Projekt, keine FS-ACLs. Isolation läuft über DB + Workspace-Pfade. Member-Zugriff auf den Workspace im Master-Agent ist NUR der Symlink `<master-ws>/projects/<name>`. `sync_links_*` ist die einzige Stelle die diese Sichtbarkeit herstellt — bricht das, sehen Master-Agents fremde/keine Projekte.

- **Audit ist fire-and-forget.** `audit.log` schluckt JEDE Exception (auch DB-Fehler). Ein fehlendes Audit bricht nie eine Projekt-Operation. Kehrseite: stilles Audit-Loch wenn die DB klemmt. Außerdem werden NUR die Route-Handler in `projects.py`/`projects_servers.py` geloggt — Git-/File-/Samba-Operationen tauchen NICHT im Audit auf (siehe Offene Enden).

- **`require_admin` für Projekt-CRUD, `require_auth` für den Rest.** Create/Update/Delete/Member-Management sind admin-only. Files/Git/Samba/Servers/Sessions/Stats/Audit sind für jeden Member offen (`check_project_access`/`project_or_404`). D.h. ein normaler Member kann Git pushen, Files schreiben und Server zuweisen, aber das Projekt selbst nicht umbenennen oder Members ändern.

- **Drei parallele `project_or_404`-Implementierungen.** `_git_helpers`, `_server_route_helpers` und `projects_samba._project_or_404` haben jeweils eigene (identische) Access-Check-Kopien, plus `_project_route_helpers.check_project_access`. DRY-Bruch — eine Permission-Änderung müsste an 4 Stellen erfolgen (verstößt gegen CLAUDE.md „Permissions: EIN zentrales Modul").

### Was bricht wenn man X anfasst

- **`workspace_path`-Schema ändern** → Project-Agents verlieren ihren Workspace + alle Master-Symlinks zeigen ins Leere. Beide Pfad-Builder synchron halten.
- **`is_valid_name`/`NAME_RE` ändern** → Frontend `_AddRepoForm.NAME_RE` ist eine separate Kopie, driftet sonst.
- **`_inject_token` für SSH erweitern** → aktuell stiller No-Op bei SSH-URLs; Push/Pull über SSH schlägt ohne Hinweis fehl.
- **`agent_config.delete`-Signatur/Verhalten** → `config.delete` ruft es im Cascade; bricht es, bleibt ein verwaister Project-Agent.
- **Samba `samba_includes_dir` umbenennen** → der Installer-Patch in `smb.conf` (`include = .../_index.conf`) und `_regenerate_index` müssen mitziehen.

---

## Datenmodell

### Projekt-Config (`data/projects/<id>/config.json`, JSON-on-disk)
| Feld | Typ | Quelle/Default |
|------|-----|----------------|
| `id` | str | `uuid7()` |
| `name` | str | validiert ≤200 |
| `description` | str | `""` |
| `members` | list[str] | validierte Usernames |
| `agent_id` | str | Auto-Project-Agent |
| `status` | str | `active`\|`paused`\|`archived` |
| `created_at` / `updated_at` | ISO str | `now_iso()` |
| `created_by` | str | Ersteller (admin) |
| `git_initialized` | bool | `False`, true nach init/clone |
| `git_token` | str | Legacy `_root`-Token (top-level) |
| `git_repos` | dict | `{repo_name: {git_token?, remote_url?}}` |
| `samba_enabled` | bool | `False` |
| `notes` | str | `""` |
| `tags` | list[str] | `[]` |
| `mcp_server_ids` | list[str] | `[]` |
| `allowed_plugins` | list[str] | `[]` |
| `allowed_specialists` | list[str] | Agent-IDs |
| `llm_api_key` | str | `""` (Override) |
| `metadata` | dict | `{}` |
| `webhook_secret` | str | `token_urlsafe(32)` (nur via `create`, kein `_normalize`-Default) |

### Tabelle `project_audit_log` (Migration 024)
`id` PK TEXT, `project_id` TEXT NOT NULL, `user_id` TEXT NOT NULL, `action` TEXT NOT NULL, `target` TEXT, `details_json` TEXT, `created_at` TEXT NOT NULL. Index `idx_project_audit_project(project_id, created_at)`.

**Geloggte Actions:** `project_updated`, `member_added`, `member_removed`, `server_assigned`, `server_unassigned`.

### Server-Assignment (Migration 005)
`vms.project_id` TEXT (nullable), `containers.project_id` TEXT (nullable). Indizes `idx_vms_project`, `idx_containers_project`. 1 Server = 0/1 Projekt; Delete → NULL.

### Env-Vars
| Var | Default | Zweck |
|-----|---------|-------|
| `HH_DATA_DIR` | `/var/lib/hydrahive2` | Basis für `projects/` + `workspaces/` |
| `HH_SAMBA_INCLUDES_DIR` | `/etc/samba/hh-projects.d` | Per-Projekt-Share-Configs |
| `HH_SAMBA_USER` | `hh` | gemeinsamer Samba-User |
| `HH_SAMBA_PASSWORD_FILE` | `<config_dir>/samba.password` | Klartext-Passwort |
| `HH_SAMBA_LOG` | `/var/log/hydrahive2-samba.log` | Samba-Setup-Log |
| `HH_SKIP_SAMBA` / `HH_INSTALL_SAMBA` | — | Installer-Skip-Flags |

### Konstanten
- `WORKSPACE_DIR_MODE = 0o2775` (setgid).
- `ROOT_REPO = "_root"`, `NAME_RE = ^[a-z0-9][a-z0-9_-]{0,49}$`.
- `_MAX_READ = 100 KB`, `MAX_WRITE_BYTES = 1 MB`, `MAX_UPLOAD_BYTES = 10 MB`.
- `_VALID_STATUS = {active, paused, archived}`.

### Events
- `TriggerEvent(event_type="webhook", channel=f"project:{id}", payload=body)` → Butler-Flows mit `scope="project"` + `scope_id==id`.

---

## Offene Enden

- **DRY-Bruch: vierfach kopierter Access-Check.** `_git_helpers.project_or_404`, `_server_route_helpers.project_or_404`, `projects_samba._project_or_404` und `_project_route_helpers.check_project_access` sind alle dieselbe Logik (`role != "admin" and username not in members and created_by != username`). Verstößt gegen CLAUDE.md („Permissions: EIN zentrales Modul"). Sollte zu einem geteilten Helper konsolidiert werden.

- **Audit deckt nur Teilmenge ab.** Geloggt werden `project_updated`/`member_*`/`server_*`. NICHT geloggt: Git-Clone/Init/Commit/Push/Pull/Delete, File-Write/Upload/Delete, Samba-Toggle, Override-Änderungen (mcp/plugins/api_key). Der Audit-Tab suggeriert eine vollständige „wer-hat-was"-Spur, die es nicht ist. `details_json` wird nur bei `project_updated` befüllt; `member_*`/`server_*` nutzen nur `target`.

- **`webhook_secret` ohne `_normalize`-Default.** Alle anderen Felder bekommen in `_normalize` einen Default, `webhook_secret` nicht. Alt-Projekte (vor der Webhook-Härtung) bleiben dadurch dauerhaft im unsicheren Webhook-Modus, bis sie einmal mit Secret neu gespeichert werden. Es gibt keinen Backfill/Migrationspfad.

- **SSH-Remotes werden nie geauthet.** `_inject_token` greift nur bei `https://`. Ein `git@github.com:…`-Remote bekommt nie einen Token → Push/Pull schlägt still mit Auth-Fehler fehl. Kein UI-Hinweis darauf, dass nur HTTPS-Token-Auth unterstützt wird.

- **`_normalize` mutiert das übergebene Dict.** `cfg.setdefault(...)` schreibt in den geladenen JSON-Dict in-place (statt Copy). Verstößt gegen die Immutability-Regel; bei wiederverwendeten Dicts (z.B. in Tests) Quelle subtiler Bugs.

- **`config._normalize` und `_config_io._normalize` doppelt importiert.** `config.py:11` importiert `_normalize` aus `_config_io`, nutzt es aber nicht (toter Import — `create`/`update` bauen Dicts selbst). `__all__` in `_config_io` fehlt; `members.py` greift auf `config._save_atomic`/`config.get` zu (Re-Export-Kette config→_config_io), was die Modul-Grenzen verwischt.

- **Master-Agent Multi-Account-Token-Lookup ist TODO.** `_resolve_gh_token` (shell.py:55) kommentiert: Master-Agent nimmt „den ersten Token" aus allen Owner-Projekten. Bei einem User mit mehreren GitHub-Accounts greift potenziell der falsche Token. Geplanter cwd-basierter Lookup ist nicht implementiert.

- **`delete()` nicht transaktional.** Cascade über FS (`rmtree` ×2) + DB (`clear_project_assignments` ×2) + Agent-Delete + Samba. Bricht es mittendrin (z.B. `rmtree`-Permission-Fehler), bleibt ein inkonsistenter Zwischenzustand: Agent gelöscht aber Workspace da, oder Audit-Zeilen verwaist (Audit wird beim Delete gar nicht abgeräumt — `project_audit_log`-Zeilen überleben das Projekt). Kein Audit-Eintrag für `project_deleted`.

- **`projects_git.py`-Aggregator verliert Tags doppelt.** `projects_git_manage` und `_ops` haben beide `tags=["projects"]` + `prefix=/api/projects`; der Aggregator-Router inkludiert sie ohne weiteren Prefix — funktioniert, ist aber eine redundante Router-Schachtelung.

- **Migration-Nummer 024 ist die höchste.** Laut Memory (Issue-Board 2026-06-02) gibt es eine geplante Migration-Kollision: ein offenes Feature (#170) muss von 024 auf 025 umnummeriert werden. Aktuell ist 024 (`project_audit_log`) die letzte vorhandene — neue Projekt-Migrationen müssen bei 025 beginnen.

- **`git_token` (top-level) vs `git_repos[*].git_token`.** Zwei parallele Token-Schemata (Legacy-`_root` top-level, Multi-Repo per-repo) leben nebeneinander in jeder Config. Konsolidierung würde `token_for`, `_first_token_in`, `get_repos` (has_token) und das Frontend `has_token`-Flag betreffen.

- **`workspace.py` Git-Routen ≠ Projekt-Git.** `/api/workspace/git/*` (agent_id-basiert) ist ein SEPARATES Git-Subsystem für Agent-Workspaces (nutzt `gs.resolve_repo`/`gs.list_repos`), nicht das Projekt-Git hier. Beide haben ein `_root`-Konzept und überlappende Begriffe — Verwechslungsgefahr beim Refactoring.

- **`_config_io.py:6` importiert `now_iso`/`uuid7` nicht, aber `members.py`/`audit.py` schon** — keine Inkonsistenz, nur Hinweis dass die Schreibhelfer über mehrere Module verstreut sind (`_save_atomic` in `_config_io`, aber `config`, `members`, `git_manage`-Routen rufen alle `project_config.update`/`_save_atomic`).
