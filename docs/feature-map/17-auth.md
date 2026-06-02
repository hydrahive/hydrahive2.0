# Auth, Permissions & Users

> Subsystem-Landkarte für **Auth, Permissions & Users** in HydraHive2.
> Stand: 2026-06-02. Quellen: `core/src/hydrahive/api/middleware/`, `core/src/hydrahive/credentials/`,
> `core/src/hydrahive/api/routes/{auth,users,credentials}.py`, `frontend/src/features/{auth,users,credentials,profile}/`.
>
> **Wichtigste Erkenntnis vorab:** Das Verzeichnis `core/src/hydrahive/auth/` ist **LEER** (nur `__init__.py`-loser Ordner).
> Die gesamte Auth-/Permissions-Logik lebt **NICHT** in `auth/`, sondern in `core/src/hydrahive/api/middleware/`.
> Das ist die zentrale Drift-Falle dieses Subsystems (siehe Offene Enden).

---

## WAS

### Backend — Middleware-Module (`core/src/hydrahive/api/middleware/`)

**`auth.py` — JWT + Permission-Gates (das De-facto-Permissions-SSOT-Modul):**
- `create_token(username, role)` — erzeugt JWT (HS256), Claims `sub`/`role`/`exp`.
- `_decode(token)` — dekodiert JWT, wirft `coded(401,"token_expired")` bei `ExpiredSignatureError`, `coded(401,"invalid_token")` bei `InvalidTokenError`.
- `require_auth(creds)` — FastAPI-Dependency. Gibt `(username, role)` zurück. Wirft `coded(401,"not_authenticated")` ohne Credentials. Unterstützt **zwei Token-Arten**: JWT und API-Key (Prefix `hhk_`).
- `require_admin(auth)` — Dependency auf `require_auth`; wirft `coded(403,"admin_only")` wenn `role != "admin"`.
- `get_current_user_optional(creds)` — wie `require_auth`, aber gibt `None` statt 401 zurück (für Endpoints, die anonym UND authentifiziert bedienbar sind).
- `_bearer = HTTPBearer(auto_error=False)` — FastAPI-Security-Scheme, gibt `None` statt auto-401 zurück (damit die Funktionen `coded()`-Errors werfen können).

**`users.py` — User-Store (JSON-Datei, bcrypt):**
- `verify(username, password)` — prüft Passwort, gibt `{username, role}` oder `None`. **Migriert Legacy-SHA256-Hashes lazy auf bcrypt** bei erfolgreichem Login.
- `create(username, password, role="user")` — legt User an, `ValueError` wenn existiert.
- `update_password(username, new_password)` — setzt neuen bcrypt-Hash.
- `update_role(username, role)` — ändert Rolle; **schützt letzten Admin** (`ValueError("last_admin")`); validiert Rolle (`admin`/`user`).
- `delete(username)` — löscht User (idempotent, `pop(..., None)`).
- `list_users()` — `[{username, role}]` ohne Hashes.
- `ensure_admin(username, password)` — legt Admin an **wenn KEIN User existiert**; gibt `True` bei Neuanlage. (Beim ersten Start in `lifespan`.)
- `_hash(password)` — `bcrypt.hashpw(..., gensalt())`.
- `_is_bcrypt(stored)` — erkennt `$2a$`/`$2b$`/`$2y$`.
- `_verify_hash(password, stored)` — bcrypt-checkpw oder Legacy-SHA256-Vergleich.
- `_load()`/`_save()` — JSON I/O, `_save` ist **atomic** (temp+rename, gegen Race bei Login+Migration).

**`api_keys.py` — persistente API-Keys (kein Ablauf):**
- `create(name, username, role)` — neuer Key Format `hhk_<key_id_16hex>_<random_43>`, bcrypt-gehasht, gibt Klartext **einmalig** zurück.
- `verify(plain)` — prüft Key. **Neues Format = O(1)** (Key-ID direkt aus Plain-Key, ein bcrypt-Call). **Altformat = lineare Schleife** mit `key_prefix`-Filter (Fallback).
- `list_keys(username=None)` — Keys ohne Hash. `None` = alle (Admin).
- `delete(key_id, username=None)` — löscht Key; `None` = Admin darf alle.
- `_is_new_format(plain)` — Format-Detektion (16 Hex + `_`).
- `PREFIX = "hhk_"`, `_KEY_ID_HEX_LEN = 16`, `_PREFIX_LEN = 12`.

**`lockout.py` — Brute-Force-Schutz für Login (In-Memory):**
- `is_locked(username, ip)` — `(locked, retry_after_seconds)`. Sliding-Window pro **Username UND IP**.
- `record_failure(username, ip)` — zählt Fehlversuch.
- `reset(username, ip)` — leert Counter nach erfolgreichem Login.
- `_prune(entries, now)` — entfernt Einträge älter als Window.
- Konstanten: `WINDOW_SECONDS = 15*60`, `USERNAME_THRESHOLD = 5`, `IP_THRESHOLD = 20`.

**`inbound_ratelimit.py` — Rate-Limit für UNauthentifizierte Inbound-Endpoints (In-Memory, Issue #180):**
- `check_rate(key, limit=120, window=60)` — `(allowed, retry_after)`. Zählt Treffer nur wenn erlaubt.
- `reset(key=None)` — leert Counter (`None` = alle).
- Konstanten: `WINDOW_SECONDS = 60`, `DEFAULT_LIMIT = 120`.
- **Konsumenten:** `health_data.py` (`health-ingest:<ip>`), `communication_whatsapp_incoming.py` (`wa-incoming:<ip>`).

**`secret_compare.py` — konstant-zeitiger Vergleich (Issue #180):**
- `verify_secret(provided, expected)` — `hmac.compare_digest`; **fail-closed** (leeres expected → immer False).
- **Konsumenten:** WhatsApp-Bridge-Secret, Health-Ingest-Key.

**`client_ip.py` — Client-IP hinter Reverse-Proxy:**
- `client_ip(request)` — `X-Forwarded-For` nur wenn direkter Peer in `TRUSTED_PROXIES = {"127.0.0.1", "::1"}`, sonst Spoofing-Schutz.

**`errors.py` — strukturierte Code-Errors:**
- `coded(status_code, code, **params)` — baut `HTTPException` mit `detail={"code": ..., "params": ...}`. Frontend mappt Code via i18next.

### Backend — Routes

**`api/routes/auth.py` (prefix `/api/auth`, tag `auth`):**
- `POST /api/auth/login` — Login. Body `{username, password}`. Lockout-Check → `verify` → `record_failure`/`reset` → `create_token`. Response `{access_token, username, role}`. `429` bei Lockout (mit `Retry-After`-Header), `401` bei falschen Daten.
- `GET /api/auth/me` — gibt `{username, role}` des aktuellen Tokens (`require_auth`).
- `GET /api/auth/apikeys` — listet eigene Keys (Admin: alle).
- `POST /api/auth/apikeys` — erzeugt Key (`201`), Body `{name}`, validiert `name.strip()`. Response `{key, name, username}`.
- `DELETE /api/auth/apikeys/{key_id}` — löscht Key (`204`); `404` `key_not_found`.

**`api/routes/users.py` (prefix `/api/users`, tag `users`):**
- `GET /api/users` — alle User (`require_admin`).
- `POST /api/users` — User anlegen (`201`, `require_admin`). `409` `username_exists`. **Bootstrappt zugleich Master-Agent** (`agent_bootstrap.ensure_master`).
- `DELETE /api/users/{username}` — löscht User (`204`, `require_admin`). **Löscht zuvor alle Agenten dieses Owners** (`agent_config.list_by_owner` → `delete`).
- `PATCH /api/users/{username}` — Rolle ändern (`require_admin`). Mapped `last_admin`→`400 last_admin_cannot_demote`, `Ungültige Rolle`→`400 invalid_role`, sonst `404 user_not_found`.
- `PATCH /api/users/me/password` — eigenes Passwort (`require_auth`, kein Admin nötig).
- `POST /api/users/me/backup` — eigenes Daten-Archiv erzeugen + downloaden (`require_auth`). FileResponse `.tar.gz`.
- `POST /api/users/me/restore` — eigenes Archiv hochladen + restoren (`require_auth`). Cap via `stream_upload_capped`, `413` bei zu groß.
- `PATCH /api/users/{username}/password` — fremdes Passwort setzen (`require_admin`).

**`api/routes/credentials.py` (prefix `/api/credentials`, tag `credentials`):**
- `GET /api/credentials` — eigene Credentials, **value maskiert** (`require_auth`).
- `GET /api/credentials/{name}?reveal=bool` — eine Credential, value nur bei `reveal=true` (`require_auth`). `404` `credential_not_found`.
- `POST /api/credentials` — Create/Update (`201`, `require_auth`). Validiert `is_valid_name`, `type in ALL_TYPES`. `400` bei Fehler.
- `DELETE /api/credentials/{name}` — löschen (`204`). `404` `credential_not_found`.
- `CredentialBody` Pydantic: `name(1-50)`, `type(Literal)`, `value`, `url_pattern="*"`, `description`, `header_name`, `query_param`.
- `_serialize(c, mask)` — maskiert `value`, exponiert `value_set: bool`.

### Backend — Credential-Vault (`core/src/hydrahive/credentials/`)

**`models.py`:**
- `Credential` (dataclass): `name, type, value, url_pattern="*", description, header_name, query_param`.
- `CredentialType = Literal["bearer","basic","cookie","header","query"]`, `ALL_TYPES`.
- `is_valid_name(name)` — `NAME_RE = ^[a-z0-9][a-z0-9_-]{0,49}$`.
- `matches_url(pattern, url)` — Glob (`*`→`.*`, Rest escaped), `"*"`/leer matcht alles.

**`store.py` — File-Storage pro User:**
- `list_credentials(username)`, `get_credential(username, name)`, `save_credential(username, cred)→(ok,err)`, `delete_credential(username, name)→bool`.
- `match_credential(username, url, prefer_name=None)` — findet passendste Credential per URL-Pattern; `prefer_name` erzwingt Profil.
- `save_credential` validiert: `is_valid_name`, `type in ALL_TYPES`, `header`→`header_name` Pflicht, `query`→`query_param` Pflicht.
- `_file_for(username)` = `data_dir/credentials/<username>.json`.
- `_load_raw`/`_save_raw` — **value-Felder werden AES-GCM-verschlüsselt** (`encrypt`/`decrypt`), atomic write, `chmod 600`.
- `_row_to_credential(name, row)` — Default-fallback `type="bearer"`.

**`_crypto.py` — AES-GCM für Credential-Values:**
- `encrypt(plaintext, data_dir)` → `enc:v1:<b64(nonce+ct)>`.
- `decrypt(value, data_dir)` → Klartext; **Plaintext-Legacy** (ohne Prefix) bleibt unverändert (wird beim nächsten Write verschlüsselt).
- `is_encrypted(value)` → bool.
- `_load_key(data_dir)` — Master-Key-Quellen: (1) `HH_MASTER_KEY` env (64-hex = 32 byte), (2) auto-generierte `data_dir/credentials/.master_key` (chmod 600).
- `_PREFIX = "enc:v1:"`, `_NONCE_BYTES = 12`.

**`redaction.py` — wert-basierte Egress-Redaction:**
- `secret_values()` — aktuelle Secret-Werte aus (1) shell-Denylist-SSOT `tools.shell._env_denylist`, (2) Provider-Keys aus LLM-Config. **Keine dritte hartcodierte Liste.**
- `scrub(value, secrets=None)` — rekursiv über dict/list/tuple; ersetzt bekannte Secret-Werte durch `[REDACTED]`. Immutable (neue Strukturen).
- `scrub_result(result, secrets=None)` — neues `ToolResult` mit geschwärztem output/error/metadata.
- `detect_secrets(text)` — findet **secret-FÖRMIGE** Substrings via `SECRET_PATTERNS` (für historische Audit, auch rotierte Keys).
- `redact_detected(text)` — ersetzt secret-förmige Substrings durch Placeholder.
- `register_pattern(pattern)` — Plugins können Zusatz-Patterns registrieren (`_EXTRA_PATTERNS`).
- `mask(secret)` — `<prefix9>…(N chars)` für Reports.
- `MIN_SECRET_LEN = 12`, `PLACEHOLDER = "[REDACTED]"`.
- `SECRET_PATTERNS` — OpenRouter, Anthropic, OpenAI, Groq, Google, NVIDIA, GitHub PAT (classic+fine), HuggingFace, Bearer-Header, PEM-Privatekey, generisches `sk-`.

**`__init__.py`** — re-exportiert `Credential, CredentialType, delete_credential, get_credential, list_credentials, match_credential, save_credential`.

### Frontend — Auth (`frontend/src/features/auth/`)
- `useAuthStore.ts` — Zustand-Store mit `persist` auf **sessionStorage** (Key `hh-auth`). State: `token, username, role`. Actions: `setAuth`, `logout`.
- `LoginPage.tsx` — Login-Form, POST `/auth/login` → `setAuth` → `navigate("/")`. Fehleranzeige via i18n.

### Frontend — Users (`frontend/src/features/users/`)
- `UsersPage.tsx` — Admin-Seite: Liste + New/Edit/ChangePassword-Dialoge + ApiKeysSection. Self-Delete-Guard (`alert errors.self_delete`).
- `UserList.tsx` — Liste mit Rollen-Icon (Crown/User), Edit/Pw/Delete-Buttons, Self-Delete disabled.
- `NewUserDialog.tsx` — Create-Form (`pattern=[a-zA-Z0-9_\-]+`, `minLength=8`, Rolle-Select).
- `EditUserDialog.tsx` — nur Rolle änderbar (`dirty`-Tracking).
- `ChangePasswordDialog.tsx` — fremdes Passwort (Admin), `minLength=8`.
- `ApiKeysSection.tsx` — API-Key CRUD: Create (Name) → einmalige Klartext-Anzeige + Copy, Liste, Delete.
- `api.ts` — `usersApi` (list/create/update/delete/changePassword), `apiKeysApi` (list/create/delete).
- `types.ts` — `UserRole = "admin"|"user"`, `User`, `ApiKey`.

### Frontend — Credentials (`frontend/src/features/credentials/`)
- `CredentialsPage.tsx` — Tabs **HTTP-Credentials** (alle User) / **Extensions** (nur `role==="admin"`). Grid der Credentials, Security-Note.
- `CredentialEditor.tsx` — Create/Edit-Modal. `NAME_RE` clientseitig. Header/Query-Felder bedingt. Reveal via separaten GET.
- `_credentialHelpers.tsx` — `Field`-Wrapper + `CredentialValueInput` (Eye/EyeOff, lazy reveal via `credentialsApi.get(name, true)`).
- `ExtensionCredentials.tsx` — Admin-View: GET `/admin/extensions/credentials`, Felder mit `secret`-Maskierung.
- `api.ts` — `credentialsApi` (list/get/save/remove).
- `types.ts` — `CredentialType`, `Credential` (mit `value_set`), `CredentialSavePayload`.

### Frontend — Profile (`frontend/src/features/profile/`)
- `ProfilePage.tsx` — Profil-Header (Avatar, Rolle) + ChangeOwnPassword + Language + Theme + Landing + TTS + Backup/Restore.
- `ChangeOwnPasswordCard.tsx` — eigenes Passwort (PATCH `/users/me/password`).
- `BackupRestoreCard.tsx` — Download (POST `/users/me/backup`) + Restore (POST `/users/me/restore`), Confirm-Dialog.
- `api.ts` — `profileApi.changeOwnPassword`, `downloadBackup`, `restoreBackup` (eigene `fetch`-Calls mit Token-Header, nicht über `api`-Client).
- (Weitere Profile-Dateien `TTSSettings`, `LandingSwitcher`, `ThemeSwitcher` gehören zu anderen Subsystemen.)

### Frontend — Routing/Gating (`frontend/src/`)
- `App.tsx` — `Guard` (Token-Pflicht → `/login`), `AdminGuard` (`role==="admin"` → sonst `/`). Admin-Routen: `/users`, `/plugins`, `/extensions`, `/zahnfee`.
- `shared/api-client.ts` — `request<T>` hängt `Authorization: Bearer <token>` an; bei `401` → `logout()` + Redirect-Effekt; `coded`-Detail-Mapping via i18next (`errors:<code>`).
- `shared/nav-config.ts` — `roles?: ("admin"|"user")[]` pro NavItem; `visibleItems(role)` filtert. Admin-only: zahnfee/plugins/extensions/users.
- `shared/AvatarMenu.tsx` — zeigt `username`/`role`, Logout-Button.
- `shared/Layout.tsx` — `visibleItems(role)`, `isAdmin = role==="admin"`.

---

## WIE

### Login-Flow (Klick → Token)
1. `LoginPage.handleSubmit` → `api.post("/auth/login", {username, password})`.
2. `routes/auth.login`: `client_ip(request)` ermitteln → `lockout.is_locked(username, ip)`.
   - Wenn locked: `429 too_many_login_attempts` + `Retry-After`-Header. **Ende.**
3. `users.verify(username, password)`:
   - `_load()` JSON → User-Dict → `_verify_hash(password, stored)`.
   - Hash falsch → `lockout.record_failure(username, ip)` → `401 invalid_credentials`.
   - Hash richtig **aber Legacy-SHA256** → re-hash auf bcrypt + atomic `_save`.
4. `lockout.reset(username, ip)` → `create_token(username, role)` → JWT signiert mit `secret_key`.
5. Response `{access_token, username, role}` → `setAuth` schreibt in **sessionStorage** (`hh-auth`).
6. `navigate("/")` → `Guard` lässt durch (Token vorhanden).

### Request-Auth-Flow (jeder API-Call)
1. `api-client.request` liest `useAuthStore.getState().token`, hängt `Authorization: Bearer <token>` an.
2. Backend-Endpoint hat `Depends(require_auth)` oder `Depends(require_admin)`.
3. `require_auth`: `HTTPBearer` extrahiert Credentials.
   - Token startet mit `hhk_` → `api_keys.verify(token)` (API-Key-Pfad).
   - Sonst → `_decode(token)` (JWT-Pfad) → `payload["sub"]`, `payload["role"]`.
4. `require_admin` ruft `require_auth` und prüft `role == "admin"`.
5. Bei `401` im Frontend: `api-client` ruft `logout()` → Store geleert → nächster Render redirected zu `/login`.

### API-Key-Verifikation (zwei Formate)
- **Neu (`hhk_<16hex>_<rest>`):** `_is_new_format` true → Key-ID = erste 16 Hex → `data.get(key_id)` → **ein** `bcrypt.checkpw`. O(1).
- **Alt (`hhk_<44 base64url>`):** lineare Schleife über alle Entries mit `key_prefix`-Vorfilter, bcrypt pro Match-Kandidat. Bleibt bis alle alten Keys rotiert sind (Migration #118).

### Credential-Injection (Tokens NIE im LLM-Kontext)
1. Agent ruft `fetch_url`-Tool mit `url` (+ optional `auth=<profile_name>`).
2. `fetch_url._select_cred(ctx.user_id, url, auth_name)`:
   - `match_credential(user_id, url, prefer_name=auth_name)` (per-User-Vault hat Vorrang).
   - Wenn kein Match UND kein erzwungenes Profil → `match_research_api(url)` (system-weite Registry, AES-verschlüsselt, Admin-gepflegt).
3. `fetch_url._apply_auth(cred, headers, params)` injiziert je nach Typ:
   - `bearer` → `Authorization: Bearer <value>`
   - `basic` → `Authorization: Basic <b64(value)>`
   - `cookie` → `Cookie:` angehängt
   - `header` → `<header_name>: <value>`
   - `query` → `params[<query_param>] = value`
4. Der Tool-Output enthält nur `auth_used = "<Typ> via Profil <name>"` — **nie den Token-Wert**.

### Redaction-Pipeline (Egress-Schutz)
- **Tool-Ebene (Engstelle):** `runner/dispatcher.py:96` ruft `redaction.scrub_result(result)` **nach** Tool-Execution, **bevor** das Result in die `tool_calls`-DB / ins Transcript / in den SSE-Stream geht. Schwärzt bekannte Secret-Werte egal wie sie reinkamen (`env`, `echo $KEY`, `cat config`).
- **Channel-Ebene (Draht-Grenze):** `communication/_agent_glue.py:178`, `discord/adapter.py:160`, `whatsapp/adapter.py:58` rufen `redaction.scrub(text)` bevor eine Agent-Antwort nach extern geht.
- **Compaction-Ebene:** `compaction/redact.py` nutzt `redaction.redact_detected` (FORM-basiert) für historische Transcripts.
- **SSOT:** Secret-Werte stammen aus `tools.shell._env_denylist()` (= `_STATIC_ENV_DENYLIST` ∪ `provider_env_vars()`) + LLM-Config-Provider-Keys. Neuer Provider → automatisch abgedeckt.

### Lockout-Zustandsmaschine
- Zwei unabhängige Sliding-Windows (Username, IP), Thread-safe (`Lock`).
- Jeder `record_failure` appended `now`. `is_locked` prunt erst (Cutoff `now-900s`), dann Schwellenvergleich (`>=5` User / `>=20` IP).
- Erfolgreicher Login → `reset` löscht beide Counter.
- **Reset bei Backend-Restart** ist gewollt akzeptabel (Angreifer-IPs wechseln eh).

### User-Bootstrapping (erster Start)
1. `lifespan` → `ensure_admin("admin", initial_pw)`.
2. `initial_pw` = `HH_INITIAL_ADMIN_PASSWORD` env ODER `secrets.token_urlsafe(16)`.
3. Wenn User neu angelegt: Passwort wird **einmal** geloggt UND in `config_dir/.admin_initial_password` (chmod 600) geschrieben (vom Installer gelesen+gelöscht).
4. `agent_bootstrap.ensure_master("admin")` legt Master-Agent für Admin an.

### User-Create/Delete-Seiteneffekte
- **Create** (`POST /api/users`): nach `users.create` → `agent_bootstrap.ensure_master(username)`. Jeder User bekommt einen Master-Agent.
- **Delete** (`DELETE /api/users/{username}`): zuerst alle Agenten des Owners löschen (`agent_config.list_by_owner` → `delete`), dann `users.delete`.

---

## WO

### Backend-Middleware
- `core/src/hydrahive/api/middleware/auth.py:18` — `create_token`
- `core/src/hydrahive/api/middleware/auth.py:27` — `_decode`
- `core/src/hydrahive/api/middleware/auth.py:36` — `require_auth`
- `core/src/hydrahive/api/middleware/auth.py:43-48` — API-Key-Branch (`hhk_`)
- `core/src/hydrahive/api/middleware/auth.py:53` — `require_admin`
- `core/src/hydrahive/api/middleware/auth.py:63` — `get_current_user_optional`
- `core/src/hydrahive/api/middleware/auth.py:15` — `_bearer = HTTPBearer(auto_error=False)`
- `core/src/hydrahive/api/middleware/users.py:21` — `_load`
- `core/src/hydrahive/api/middleware/users.py:28` — `_save` (atomic)
- `core/src/hydrahive/api/middleware/users.py:37` — `_hash`
- `core/src/hydrahive/api/middleware/users.py:41` — `_is_bcrypt`
- `core/src/hydrahive/api/middleware/users.py:45` — `_verify_hash`
- `core/src/hydrahive/api/middleware/users.py:54` — `verify` (+ lazy bcrypt-Migration `:66-69`)
- `core/src/hydrahive/api/middleware/users.py:73` — `create`
- `core/src/hydrahive/api/middleware/users.py:83` — `update_password`
- `core/src/hydrahive/api/middleware/users.py:91` — `update_role` (last-admin-Schutz `:97-100`)
- `core/src/hydrahive/api/middleware/users.py:106` — `delete`
- `core/src/hydrahive/api/middleware/users.py:112` — `list_users`
- `core/src/hydrahive/api/middleware/users.py:119` — `ensure_admin`
- `core/src/hydrahive/api/middleware/api_keys.py:48` — `_is_new_format`
- `core/src/hydrahive/api/middleware/api_keys.py:59` — `create`
- `core/src/hydrahive/api/middleware/api_keys.py:78` — `verify` (O(1)-Pfad `:85-96`, Altformat `:98-108`)
- `core/src/hydrahive/api/middleware/api_keys.py:111` — `list_keys`
- `core/src/hydrahive/api/middleware/api_keys.py:121` — `delete`
- `core/src/hydrahive/api/middleware/api_keys.py:23-26` — `PREFIX`, `_KEY_ID_HEX_LEN`, `_PREFIX_LEN`
- `core/src/hydrahive/api/middleware/lockout.py:17-19` — Konstanten
- `core/src/hydrahive/api/middleware/lockout.py:31` — `is_locked`
- `core/src/hydrahive/api/middleware/lockout.py:46` — `record_failure`
- `core/src/hydrahive/api/middleware/lockout.py:53` — `reset`
- `core/src/hydrahive/api/middleware/inbound_ratelimit.py:21` — `check_rate`
- `core/src/hydrahive/api/middleware/inbound_ratelimit.py:34` — `reset`
- `core/src/hydrahive/api/middleware/secret_compare.py:13` — `verify_secret`
- `core/src/hydrahive/api/middleware/client_ip.py:11` — `TRUSTED_PROXIES`
- `core/src/hydrahive/api/middleware/client_ip.py:14` — `client_ip`
- `core/src/hydrahive/api/middleware/errors.py:21` — `coded`

### Backend-Routes
- `core/src/hydrahive/api/routes/auth.py:31` — `POST /api/auth/login`
- `core/src/hydrahive/api/routes/auth.py:48` — `GET /api/auth/me`
- `core/src/hydrahive/api/routes/auth.py:58` — `GET /api/auth/apikeys`
- `core/src/hydrahive/api/routes/auth.py:64` — `POST /api/auth/apikeys`
- `core/src/hydrahive/api/routes/auth.py:76` — `DELETE /api/auth/apikeys/{key_id}`
- `core/src/hydrahive/api/routes/auth.py:20` — `LoginRequest`, `:25` `LoginResponse`, `:54` `CreateKeyRequest`
- `core/src/hydrahive/api/routes/users.py:44` — `GET /api/users` (admin)
- `core/src/hydrahive/api/routes/users.py:49` — `POST /api/users` (admin + ensure_master)
- `core/src/hydrahive/api/routes/users.py:59` — `DELETE /api/users/{username}` (admin + agent-cleanup)
- `core/src/hydrahive/api/routes/users.py:67` — `PATCH /api/users/{username}` (admin)
- `core/src/hydrahive/api/routes/users.py:82` — `PATCH /api/users/me/password`
- `core/src/hydrahive/api/routes/users.py:95` — `POST /api/users/me/backup`
- `core/src/hydrahive/api/routes/users.py:112` — `POST /api/users/me/restore`
- `core/src/hydrahive/api/routes/users.py:140` — `PATCH /api/users/{username}/password` (admin)
- `core/src/hydrahive/api/routes/users.py:30/36/40` — `CreateUserRequest`/`ChangePasswordRequest`/`UpdateUserRequest`
- `core/src/hydrahive/api/routes/credentials.py:43` — `GET /api/credentials`
- `core/src/hydrahive/api/routes/credentials.py:49` — `GET /api/credentials/{name}` (reveal)
- `core/src/hydrahive/api/routes/credentials.py:62` — `POST /api/credentials`
- `core/src/hydrahive/api/routes/credentials.py:85` — `DELETE /api/credentials/{name}`
- `core/src/hydrahive/api/routes/credentials.py:20` — `CredentialBody`, `:30` `_serialize`
- `core/src/hydrahive/api/routes/extensions.py:30` — router prefix `/api/admin/extensions`
- `core/src/hydrahive/api/routes/extensions.py:48` — `GET /api/admin/extensions/credentials` (admin)
- `core/src/hydrahive/api/routes/research_apis.py:24/29/40` — research-API-Registry (alle `require_admin`)

### Credential-Vault
- `core/src/hydrahive/credentials/models.py:13` — `Credential`
- `core/src/hydrahive/credentials/models.py:7-8` — `CredentialType`, `ALL_TYPES`
- `core/src/hydrahive/credentials/models.py:10` — `NAME_RE`
- `core/src/hydrahive/credentials/models.py:24` — `is_valid_name`
- `core/src/hydrahive/credentials/models.py:28` — `matches_url`
- `core/src/hydrahive/credentials/store.py:22` — `_file_for`
- `core/src/hydrahive/credentials/store.py:26` — `_load_raw` (decrypt)
- `core/src/hydrahive/credentials/store.py:41` — `_save_raw` (encrypt + chmod 600)
- `core/src/hydrahive/credentials/store.py:58` — `_row_to_credential`
- `core/src/hydrahive/credentials/store.py:73` — `list_credentials`
- `core/src/hydrahive/credentials/store.py:78` — `get_credential`
- `core/src/hydrahive/credentials/store.py:85` — `save_credential`
- `core/src/hydrahive/credentials/store.py:104` — `delete_credential`
- `core/src/hydrahive/credentials/store.py:113` — `match_credential`
- `core/src/hydrahive/credentials/_crypto.py:26` — `_key_path`
- `core/src/hydrahive/credentials/_crypto.py:30` — `_load_key`
- `core/src/hydrahive/credentials/_crypto.py:56` — `encrypt`
- `core/src/hydrahive/credentials/_crypto.py:63` — `decrypt`
- `core/src/hydrahive/credentials/_crypto.py:72` — `is_encrypted`
- `core/src/hydrahive/credentials/_crypto.py:22-23` — `_PREFIX`, `_NONCE_BYTES`
- `core/src/hydrahive/credentials/redaction.py:30` — `secret_values` (SSOT-Quelle)
- `core/src/hydrahive/credentials/redaction.py:58` — `_scrub_str`
- `core/src/hydrahive/credentials/redaction.py:65` — `scrub`
- `core/src/hydrahive/credentials/redaction.py:79` — `_scrub_value`
- `core/src/hydrahive/credentials/redaction.py:94` — `SECRET_PATTERNS`
- `core/src/hydrahive/credentials/redaction.py:115` — `register_pattern`
- `core/src/hydrahive/credentials/redaction.py:120` — `detect_secrets`
- `core/src/hydrahive/credentials/redaction.py:132` — `mask`
- `core/src/hydrahive/credentials/redaction.py:139` — `redact_detected`
- `core/src/hydrahive/credentials/redaction.py:146` — `scrub_result`
- `core/src/hydrahive/credentials/redaction.py:25/27` — `MIN_SECRET_LEN`, `PLACEHOLDER`
- `core/src/hydrahive/credentials/__init__.py:10-23` — Re-Exports

### Konsumenten / Verdrahtung
- `core/src/hydrahive/api/lifespan.py:18` — Import `ensure_admin`
- `core/src/hydrahive/api/lifespan.py:94-117` — Admin-Bootstrap, `.admin_initial_password`, `ensure_master`
- `core/src/hydrahive/tools/fetch_url.py:40-66` — `_apply_auth`
- `core/src/hydrahive/tools/fetch_url.py:69-78` — `_select_cred`
- `core/src/hydrahive/tools/fetch_url.py:113-115` — Credential-Anwendung
- `core/src/hydrahive/runner/dispatcher.py:7` — Import `redaction`
- `core/src/hydrahive/runner/dispatcher.py:96` — `scrub_result` (Tool-Engstelle)
- `core/src/hydrahive/communication/_agent_glue.py:178` — `redaction.scrub`
- `core/src/hydrahive/communication/discord/adapter.py:160` — `redaction.scrub`
- `core/src/hydrahive/communication/whatsapp/adapter.py:58` — `redaction.scrub`
- `core/src/hydrahive/compaction/redact.py:15/21` — `redact_detected`/`register_pattern`
- `core/src/hydrahive/tools/shell.py:90-104` — `_STATIC_ENV_DENYLIST` + `_env_denylist` (Redaction-SSOT)
- `core/src/hydrahive/tools/_webmin.py:11/22` — `get_credential` (Webmin-Tools)
- `core/src/hydrahive/api/routes/health_data.py:31-33,50` — `verify_secret`/`check_rate`
- `core/src/hydrahive/api/routes/communication_whatsapp_incoming.py:46-51` — `check_rate`/`verify_secret`
- `core/src/hydrahive/api/main.py:100/102/130` — Router-Registrierung (auth/users/credentials)

### Settings / Config-Keys
- `core/src/hydrahive/settings/_services.py:19` — `secret_key` (env `HH_SECRET_KEY`, **raises wenn fehlt**)
- `core/src/hydrahive/settings/_services.py:26` — `jwt_algorithm` (`"HS256"`, fix)
- `core/src/hydrahive/settings/_services.py:30` — `jwt_expire_minutes` (env `HH_JWT_EXPIRE_MINUTES`, default 1440 = 24h)
- `core/src/hydrahive/settings/_paths.py:91` — `users_config` = `config_dir/users.json`
- `core/src/hydrahive/settings/_paths.py:95` — `api_keys_config` = `config_dir/api_keys.json`
- `core/src/hydrahive/settings/_paths.py:24` — `config_dir` (env `HH_CONFIG_DIR`, default `/etc/hydrahive2`)
- `core/src/hydrahive/settings/_paths.py:20` — `data_dir` (env `HH_DATA_DIR`, default `/var/lib/hydrahive2`)

### Frontend
- `frontend/src/features/auth/useAuthStore.ts:12` — Store (`name: "hh-auth"`, sessionStorage `:21`)
- `frontend/src/features/auth/LoginPage.tsx:22-35` — `handleSubmit`
- `frontend/src/shared/api-client.ts:24` — `request<T>` (Token-Header `:31`, 401-Logout `:36-39`)
- `frontend/src/shared/api-client.ts:13-22` — `buildErrorMessage` (coded-Mapping)
- `frontend/src/App.tsx:38` — `Guard`, `:44` `AdminGuard`, `:89-94` Admin-Routen
- `frontend/src/shared/nav-config.ts:62` — `visibleItems(role)`, `:40/43/54/55` admin-roles
- `frontend/src/shared/AvatarMenu.tsx:9/54` — Logout
- `frontend/src/features/users/UsersPage.tsx:27-39` — Self-Delete-Guard
- `frontend/src/features/users/api.ts:8/19` — `usersApi`/`apiKeysApi`
- `frontend/src/features/users/types.ts:1` — `UserRole`
- `frontend/src/features/credentials/CredentialsPage.tsx:16/53` — Admin-Tab-Gate
- `frontend/src/features/credentials/CredentialEditor.tsx:17` — `NAME_RE` (Client)
- `frontend/src/features/credentials/_credentialHelpers.tsx:24-33` — lazy reveal
- `frontend/src/features/profile/api.ts:5-25` — changeOwnPassword/backup/restore
- `frontend/src/features/profile/ChangeOwnPasswordCard.tsx:16-27` — submit

### i18n (Error-Codes)
- `frontend/src/i18n/locales/en/errors.json:17-22` — invalid_credentials, too_many_login_attempts, not_authenticated, token_expired, invalid_token, admin_only
- `frontend/src/i18n/locales/en/errors.json:50-53` — username_exists, user_not_found, last_admin_cannot_demote, invalid_role
- `frontend/src/i18n/locales/en/errors.json:4-15` — backup_* Codes
- `frontend/src/i18n/locales/{en,de}/auth.json`, `users.json`, `credentials.json` — UI-Strings

### Tests
- `core/tests/test_auth.py` — create_token/_decode/require_auth/require_admin/get_current_user_optional (401/403-Pfade)
- `core/tests/test_api_keys_verify.py` — API-Key-Verifikation (neu/alt)
- `core/tests/test_lockout.py` — Brute-Force-Windows
- `core/tests/test_redaction.py` — Egress-Redaction
- `core/tests/test_research_apis.py` — system-weite Credential-Registry
- `core/tests/test_api_integration.py`, `core/tests/conftest.py` — Integration + Fixtures

---

## WARUM

**Permissions-SSOT lebt in `api/middleware/auth.py`, nicht in `auth/`.**
`require_auth`/`require_admin` sind die EINZIGEN Permission-Gates. Alle Routes importieren sie und schreiben **nie** eigene Rollen-Checks. Das entspricht der CLAUDE.md-Regel „EIN zentrales Permissions-Modul". Falle: Das physische Verzeichnis `core/src/hydrahive/auth/` ist leer und ein Honeypot — wer dort Permission-Logik sucht, findet nichts. **Nicht** dorthin neuen Code legen.

**Rollenmodell ist binär (`admin`/`user`), keine Granularität.**
Es gibt keine Fine-grained-Permissions, keine Gruppen, keine Scopes. Alles ist „ist Admin?" oder „ist authentifiziert?". Owner-basierte Isolation läuft NICHT über Rollen, sondern über `username` als Datenraum-Schlüssel: Credentials liegen in `<username>.json`, Agenten haben `owner`, Backup ist `me`-scoped. Ein `user` kann nur seine eigenen Credentials/Keys/Daten sehen — durchgesetzt dadurch, dass jeder `require_auth`-Endpoint `username` aus dem Token nimmt und damit die Store-Funktionen parametrisiert (`list_credentials(username)`, `list_keys(username=...)`).

**Zwei Token-Arten teilen sich `require_auth`.**
JWT (Browser-Session, läuft ab) und API-Key (`hhk_`, kein Ablauf, für Bots/Skripte). `require_auth` unterscheidet am Prefix. Beide liefern identisches `(username, role)`-Tupel → Routes müssen nicht wissen, womit authentifiziert wurde. Gotcha: API-Keys erben die Rolle des Erstellers zum **Erstellungszeitpunkt** (gespeichert im Key-Entry). Wird die Rolle des Users später geändert, ändert sich die Key-Rolle NICHT — der Key behält die alte Rolle bis zur Rotation.

**JWT enthält `role` direkt — keine DB-Lookup bei jedem Request.**
Performance-Entscheidung: `_decode` liest `role` aus dem Token-Claim, statt `users.json` zu lesen. Gotcha: **Rollenänderung wirkt erst nach Re-Login** (neues Token). Ein zum `user` degradierter Admin behält bis zum Token-Ablauf (default 24h) Admin-Rechte. Es gibt keine Token-Revocation-Liste.

**`HH_SECRET_KEY` ist hart erforderlich (raises beim Zugriff).**
`secret_key` wirft `RuntimeError` wenn die env-Var fehlt — fail-fast. Ohne diesen Key kann kein Token erzeugt/validiert werden → der ganze Login bricht. Wird der Key rotiert, sind **alle** existierenden JWTs sofort ungültig (gewollt). API-Keys sind davon NICHT betroffen (separater bcrypt-Hash, nicht mit `secret_key` signiert).

**bcrypt mit lazy Legacy-Migration.**
Alte Installationen hatten SHA256-Hashes. `verify` re-hasht transparent beim nächsten erfolgreichen Login. Deshalb ist `_save` **atomic** (temp+rename): paralleler Login + Migration hatte vorher eine beobachtbare Race, die `users.json` truncaten konnte. Wer `_save` anfasst, muss die Atomicity bewahren, sonst kommt die Race zurück.

**Last-Admin-Schutz nur in `update_role`, NICHT in `delete`.**
`update_role` verhindert das Degradieren des letzten Admins (`ValueError("last_admin")`). Aber `users.delete` hat **keinen** solchen Schutz — ein Admin kann sich theoretisch selbst löschen, wenn er der letzte ist (das Frontend blockt nur Self-Delete per disabled-Button + `alert`, aber das ist Client-Side und umgehbar via direktem API-Call). Mögliche Lücke: alle Admins per DELETE entfernen → System ohne Admin (heilbar nur über `ensure_admin`-Bootstrap, der aber nur greift wenn `users.json` LEER ist, nicht wenn nur die Admins fehlen).

**Lockout + Inbound-Ratelimit sind In-Memory, NICHT geteilt.**
Beide nutzen Modul-globale Dicts mit `Lock`. In einem Multi-Worker-Deployment (uvicorn `--workers > 1`) hat jeder Worker eigene Counter → effektives Limit = N × Threshold. Aktuell läuft HH2 single-process (uvicorn ohne workers, siehe `main.run`), daher kein Problem — aber Skalierung würde die Limits aufweichen. Reset bei Restart ist bewusst akzeptiert.

**X-Forwarded-For wird nur von Loopback vertraut.**
`client_ip` akzeptiert den Header NUR wenn der direkte Peer `127.0.0.1`/`::1` ist. Sonst könnte ein Client seine IP spoofen und IP-basierte Lockouts/Ratelimits umgehen. Gotcha: Steht ein nicht-Loopback-Reverse-Proxy davor (z.B. nginx auf anderer Maschine), kommt die echte Client-IP NICHT durch → alle Requests teilen sich die Proxy-IP im Lockout-Counter (zu aggressiv). `TRUSTED_PROXIES` müsste dann erweitert werden.

**Redaction hat EINE Secret-Quelle (SSOT), aber zwei Match-Strategien.**
`secret_values()` (wert-basiert) findet aktuelle Keys aus `_env_denylist` + LLM-Config — schwärzt sie überall im Output. `detect_secrets()` (form-basiert via Regex) findet auch **bereits rotierte** Keys (deren Wert nicht mehr im Env steht) für die historische Audit. Wichtig: wert-basiert ist die Laufzeit-Engstelle (`scrub_result` im Dispatcher), form-basiert ist nur für `audit_leaked_secrets.py` + Compaction. `MIN_SECRET_LEN=12` verhindert, dass kurze/leere Werte als Substring den ganzen Output zerstören. Neuer LLM-Provider → automatisch in `provider_env_vars()` → automatisch redacted. Wer einen Secret-tragenden env-Key hinzufügt, muss ihn in `_STATIC_ENV_DENYLIST` (shell.py) eintragen, sonst leckt er.

**Credential-Values sind AES-GCM-verschlüsselt at-rest, Tokens NIE im LLM-Kontext.**
Der Vault verschlüsselt `value` mit `enc:v1:`-Prefix (AES-GCM, 12-byte Nonce). Master-Key aus `HH_MASTER_KEY` oder auto-generierter `.master_key` (chmod 600). Plaintext-Legacy-Werte werden beim nächsten Write migriert. Der eigentliche Token-Wert verlässt den Server nur als HTTP-Header im `fetch_url`-Tool — er taucht **nie** im Prompt, im `tool_result` oder im Transcript auf (nur `"via Profil <name>"`). Wer `_save_raw`/`_load_raw` anfasst, muss encrypt/decrypt-Roundtrip + chmod 600 erhalten. Geht der Master-Key verloren, sind alle Credentials unwiederbringlich (GCM, kein Recovery).

**Frontend-Token in sessionStorage (nicht localStorage).**
`useAuthStore` persistiert auf `sessionStorage` → Token überlebt Reload, aber NICHT Tab-Schließen. Bewusste Härtung gegenüber dem alten HH1-Befund „JWT in localStorage" (siehe Memory `project_hydrahive_review_2026_05_15`). Gotcha: XSS kann sessionStorage trotzdem lesen — es ist kein httpOnly-Cookie. Die `AdminGuard`/`Guard` im Frontend sind **reine UX** (Redirect), keine Sicherheit — die echte Durchsetzung ist serverseitig (`require_admin`). Wer eine Admin-Route nur im Frontend gated und serverseitig `require_admin` vergisst, hat ein Loch.

**`401` → globaler Logout im api-client.**
Jeder `401` (egal welcher Endpoint) löst `useAuthStore.logout()` aus → Store leer → Re-Render redirected zu `/login`. Das ist die Token-Expiry-UX: läuft der JWT nach 24h ab, fliegt der User beim nächsten Call automatisch raus. Gotcha: ein einzelner fehlerhafter 401 (z.B. ein Endpoint, der fälschlich 401 statt 403/404 wirft) loggt den User komplett aus.

**Profile-Backup/Restore umgeht den `api`-Client.**
`profileApi.downloadBackup`/`restoreBackup` nutzen rohes `fetch` mit manuellem Token-Header (statt `api.post`), weil Binärdaten (FileResponse/FormData) den JSON-Client sprengen würden. Konsequenz: Diese Calls haben **kein** automatisches 401-Logout. Restore ist `me`-scoped (nur eigene Daten).

---

## Datenmodell

### Config-Dateien (JSON, in `config_dir` = `/etc/hydrahive2`)
| Datei | Schema | Erzeuger |
|-------|--------|----------|
| `users.json` | `{"<username>": {"password_hash": "<bcrypt|sha256>", "role": "admin"\|"user"}}` | `users._save` |
| `api_keys.json` | `{"<key_id>": {"name", "key_hash": "<bcrypt>", "username", "role", "created_at": ISO}}` (neu) / Altformat zusätzlich `key_prefix` | `api_keys._save` |
| `.admin_initial_password` | Klartext-Passwort + `\n`, chmod 600 | `lifespan` (einmalig, Installer löscht) |
| `research_apis.json` | `{"<rid>": {"key": "enc:v1:...", "enabled": bool}}` (Admin-Overrides) | `research/store._save_overrides` |
| `extensions/*.credentials.json` | von Extension-Installer generiert (Felder mit `secret`-Flag) | Extension-Install |

### Credential-Vault (in `data_dir` = `/var/lib/hydrahive2`)
| Pfad | Schema |
|------|--------|
| `credentials/<username>.json` | `{"<name>": {"type", "value": "enc:v1:...", "url_pattern", "description", "header_name", "query_param"}}`, chmod 600 |
| `credentials/.master_key` | 64-hex (32 byte) AES-Key, chmod 600 |

### `Credential` (dataclass)
`name: str`, `type: bearer|basic|cookie|header|query`, `value: str`, `url_pattern: str="*"`, `description: str=""`, `header_name: str=""`, `query_param: str=""`.

### JWT-Payload (HS256)
`{"sub": username, "role": role, "exp": now+jwt_expire_minutes}`.

### API-Response-Shapes
- Login: `{access_token, username, role}`
- `/me`: `{username, role}`
- User-Liste: `[{username, role}]`
- API-Key-Liste: `[{id, name, username, role, created_at}]`
- API-Key-Create: `{key, name, username}` (key nur EINMAL)
- Credential (serialisiert): `{name, type, value, value_set, url_pattern, description, header_name, query_param}` (value leer wenn maskiert)
- Error: `{"detail": {"code": "<code>", "params": {...}}}`

### Env-Vars
| Var | Default | Zweck |
|-----|---------|-------|
| `HH_SECRET_KEY` | — (raises) | JWT-Signing-Key |
| `HH_JWT_EXPIRE_MINUTES` | `1440` | Token-Lebensdauer (Minuten) |
| `HH_MASTER_KEY` | auto-gen | AES-Key für Credential-Values (64-hex) |
| `HH_INITIAL_ADMIN_PASSWORD` | `token_urlsafe(16)` | Admin-Passwort beim ersten Start |
| `HH_CONFIG_DIR` | `/etc/hydrahive2` | Ort von users.json/api_keys.json |
| `HH_DATA_DIR` | `/var/lib/hydrahive2` | Ort des Credential-Vaults |
| `HH_CORS_ORIGINS` | localhost:5173/5174 | erlaubte CORS-Origins |

### Konstanten (hartcodiert)
- JWT-Algorithmus: `HS256` (`_services.py:27`)
- Lockout: 5/User, 20/IP, 15-min-Window (`lockout.py:17-19`)
- Inbound-Ratelimit: 120/60s (`inbound_ratelimit.py:14-15`)
- `MIN_SECRET_LEN = 12`, `PLACEHOLDER = "[REDACTED]"` (`redaction.py:25,27`)
- `NAME_RE = ^[a-z0-9][a-z0-9_-]{0,49}$` (Credential-Name)
- Trusted Proxies: `127.0.0.1`, `::1`
- API-Key-Prefix `hhk_`, Key-ID 16 hex

### Error-Codes (gesendet via `coded()`)
`token_expired`, `invalid_token`, `not_authenticated`, `admin_only`, `invalid_credentials`, `too_many_login_attempts`, `name_required`, `key_not_found`, `username_exists`, `user_not_found`, `last_admin_cannot_demote`, `invalid_role`, `credential_not_found`, `credential_name_invalid`, `credential_type_invalid`, `credential_header_name_required`, `credential_query_param_required`, `credential_save_failed`, `backup_*`.

---

## Offene Enden

**1. Leeres `auth/`-Verzeichnis.**
`core/src/hydrahive/auth/` enthält keinen `.py`-Code (nicht mal `__init__.py`). Reiner Namensgeber-Honeypot. Entweder löschen oder ein README mit Verweis auf `api/middleware/` hinterlegen — sonst sucht jeder neue Contributor dort vergeblich nach der Auth-Logik. **Architektur-Drift gegenüber der erwarteten Co-location** (CLAUDE.md: „Permissions: EIN zentrales Modul `auth/permissions.py`" — existiert NICHT, die Logik liegt in `api/middleware/auth.py`).

**2. API-Key-Altformat-Fallback ist toter Code-Pfad in Wartemodus.**
`api_keys.verify` hat eine lineare Schleife für `hhk_<44 base64url>`-Keys (Migration #118). Bleibt „bis alle alten Keys rotiert sind" — kein Mechanismus erzwingt die Rotation, kein Telemetrie-Zähler, der meldet ob noch alte Keys existieren. Potenziell ewig mitgeschleppt. `_PREFIX_LEN = 12` und der `key_prefix`-Pfad sind nur dafür da.

**3. Legacy-SHA256-Hash-Pfad in `users._verify_hash`.**
Wie #2 — wird lazy migriert, aber ein User, der sich nie einloggt, behält ewig den SHA256-Hash. Kein Batch-Migrations-Tool.

**4. Plaintext-Credential-Legacy in `_crypto.decrypt`.**
`decrypt` gibt Werte ohne `enc:v1:`-Prefix unverändert zurück („wird beim nächsten Write verschlüsselt"). Eine Credential, die nur gelesen aber nie wieder gespeichert wird, bleibt für immer Klartext auf der Platte. Kein Migrations-Sweep.

**5. Last-Admin-Schutz fehlt bei `users.delete`.**
`update_role` schützt den letzten Admin, `delete` NICHT. Server-seitig kann der letzte Admin gelöscht werden → System ohne Admin. `ensure_admin` heilt das NICHT (greift nur wenn `users.json` komplett leer). Frontend-Self-Delete-Guard ist Client-Side (`disabled` + `alert`) und per direktem API-Call umgehbar.

**6. Keine Token-Revocation.**
Logout leert nur den Client-Store; das JWT bleibt bis `exp` gültig. Rollenänderung/Degradierung wirkt erst nach Re-Login. Kein Blacklist-/Revocation-Mechanismus. Bei kompromittiertem Token hilft nur `HH_SECRET_KEY`-Rotation (invalidiert ALLE Tokens).

**7. API-Key-Rolle friert beim Erstellen ein.**
Der Key speichert `role` zum Erstellungszeitpunkt. Spätere Rollenänderung des Users propagiert NICHT auf seine Keys. Ein Key, der als Admin erstellt wurde, bleibt Admin auch nachdem der User zum `user` degradiert wurde — bis der Key gelöscht wird.

**8. In-Memory-Lockout/Ratelimit skaliert nicht über Worker.**
Bei `uvicorn --workers > 1` hätte jeder Worker eigene Counter (effektives Limit × N). Aktuell single-process, aber undokumentierte Skalierungs-Falle.

**9. Kein expliziter Passwort-Komplexitäts-Check serverseitig.**
`minLength=8` ist nur Frontend (`NewUserDialog`, `ChangePasswordDialog`, `ChangeOwnPasswordCard`). Der Server (`users.create`/`update_password`) akzeptiert beliebig kurze/leere Passwörter via direktem API-Call.

**10. `me/backup` und `me/restore` umgehen den 401-Logout-Pfad.**
Da sie rohes `fetch` statt `api`-Client nutzen, lösen sie bei abgelaufenem Token kein automatisches Logout aus — der User sieht nur einen generischen Fehler.

**11. CORS-Default erlaubt `allow_methods=["*"]` + `allow_credentials=True`.**
`main.py:91-97`. In Kombination mit konkreten Origins ok, aber der Default-Origin-Satz (`localhost:5173/5174`) ist Dev-orientiert; produktiv muss `HH_CORS_ORIGINS` gesetzt sein, sonst funktioniert das Frontend hinter einer echten Domain nicht (und der Default-Satz ist dann nutzlos statt sicher).

**12. `extensions/*.credentials.json` werden ungefiltert ausgeliefert.**
`GET /api/admin/extensions/credentials` liest alle `*.credentials.json` und gibt sie zurück (inkl. als `secret` markierter Felder — die das Frontend nur visuell maskiert). Admin-only, aber die Secrets gehen im Klartext über die API an den Browser. Kein Reveal-on-demand wie beim HTTP-Credential-Vault.

**13. Doppelte Name-Validierung (Drift-Risiko).**
`NAME_RE` existiert in `credentials/models.py:10` (Backend) UND `CredentialEditor.tsx:17` (Frontend) als getrennte Literale. Ändert sich eine, driftet die andere. Gleiches Muster bei `minLength=8` (Frontend) ohne Backend-Pendant.
