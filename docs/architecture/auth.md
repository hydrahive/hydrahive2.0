# Auth + OAuth

> Wer darf was, wie kommen Credentials in den LLM-Call.

## Zwei Auth-Wege ins Backend

```
Frontend (Browser)                       Externe Tools / CI / CLI
       │                                          │
       ▼ Login                                    ▼
   POST /api/auth/login                  hhk_<44-char-token>
   (username + password)                 (API-Key, vom User generiert
       │                                  unter Profile-Settings)
       ▼                                          │
   Bearer <JWT>                                   │
   {sub: username, role, exp: 60min}              │
       │                                          │
       └────────────────┬─────────────────────────┘
                        ▼
              HTTPBearer dependency
              (api/middleware/auth.py)
                        │
                        ▼
              require_auth → tuple(username, role)
              require_admin → tuple, raises 403 if role != 'admin'
              get_current_user_optional → tuple | None (kein 401-Throw)
```

JWT lebt 60min (`settings.jwt_expire_minutes`). API-Keys haben kein Ablauf —
werden bei `verify(plain)` per `bcrypt.checkpw` gegen alle gespeicherten Hashes
geprüft.

## Roles

```
admin   — kann alles (alle Agents PATCH/DELETE, alle Sessions, alle Configs)
user    — nur eigene Ressourcen (siehe check_agent_access /
          check_session_access)
```

Es gibt **keine** weiter granulierten Rollen (keine "owner" / "viewer" /
"editor" Differenzierung). Bewusste Vereinfachung — siehe SPEC.md "Nicht-Ziele".

`check_agent_access(agent, username, role)` und `check_session_access(...)`:
return None wenn admin ODER owner == username, sonst raise 403.

## Login-Lockout

Defense gegen Brute-Force in `auth/login_lockout.py`:

| Trigger | Threshold | Lockout-Dauer |
|---|---|---|
| Pro User (failed logins) | 5 | 15min |
| Pro IP (failed logins) | 20 | 1h |

Lockout-Records in `lockout.json` mit Atomic-Write. Erfolgreicher Login
resettet den User-Counter (IP-Counter bleibt bis Expiry).

Tests: `test_lockout.py` (8) — User-Threshold, IP-Threshold, Reset, Expiry.

## API-Key-Format

```
hhk_<44-char-base64url-secrets-token>
```

Beispiel: `hhk_aB3xZ_kQs9pYzL2mN-rTvW4-fGhJk_LpQrStUvWxYz`

- Erzeugung: `secrets.token_urlsafe(32)` (256 bit Entropy)
- Storage: nur `bcrypt.hashpw(plain)` in `api_keys.json`
- Klartext sieht der User **einmal** beim Erzeugen — danach nie wieder
- Permissions wie der User der den Key erzeugt hat

Aktuell linearer bcrypt-Loop in `verify()` (Issue #118 für key_id-Lookup).

## OAuth — Anthropic + ChatGPT Plus/Pro

Beide Provider bieten OAuth-Token-basierten Zugriff zusätzlich zum API-Key.
Für ChatGPT Plus/Pro ist das die **einzige** Option (Codex-Endpoint braucht
OAuth, kein API-Key-Pendant).

### Flow

```
Frontend "Mit Anthropic verbinden"-Button
   │
   ▼ POST /api/llm/oauth/start?provider=anthropic
   ← {auth_url, state}                         (PKCE: code_verifier serverseitig)
   │
   ▼ User browst auth_url → Anthropic-Login
   │   Anthropic redirected to https://localhost:8123/callback?code=...&state=...
   │
   ▼ POST /api/llm/oauth/exchange
   {provider, code, state}
   │
   ▼ exchange_code (oauth/anthropic.py)
   ├── PKCE-Verifier holen
   └── POST <provider-token-url>
       ← {access_token, refresh_token, expires_in}
   │
   ▼ update_provider_oauth(llm.json, "anthropic", new_block)   ← atomic mit flock
   │
   ▼ Frontend zeigt "Verbunden ✓"
```

Tests: `test_llm_config_rmw.py` (6, inkl. multiprocessing-Concurrent-Test).

### Refresh

Bei jedem `resolve_anthropic_token()` / `resolve_openai_codex_token()`-Call:

```
if (expires_at - now()) > _REFRESH_THRESHOLD_S (300s):
    return current access
else:
    refresh via refresh_token-Grant
    update_provider_oauth(...)   ← atomic
    return new access
```

Threshold 5min: refresht eher zu früh als dass ein gerade abgelaufener
Token in einen Stream-Call geht.

### Atomic Refresh (#S3-Fix, Commit `b62108a`)

`oauth/_llm_config_rmw.py:update_provider_oauth` schützt vor Race wenn
mehrere Prozesse gleichzeitig refreshen (API-Server + Web-UI + CLI):

```python
with lock_path.open("w") as fd:
    fcntl.flock(fd, fcntl.LOCK_EX)        # blockierend
    data = json.loads(path.read_text())   # frischer Read unter Lock
    update provider...
    atomic write (temp + rename)
    flock release
```

Vorher: `read_text()` → mutate → `write_text()` ohne Lock → letzter Writer
gewinnt → einer der parallelen Refreshes verloren → Logout-Effekt für
betroffenen Provider.

## OAuth-spezifische Details

### Anthropic OAuth

- Token-Endpoint: `auth.anthropic.com/oauth/token`
- Identity-Header: spezielle System-Prompt-Block in jedem Call (siehe
  `llm/_anthropic.py:_ANTHROPIC_OAUTH_IDENTITY`)
- Modelle: alle die Anthropic anbietet, inkl. opus-4-x

### ChatGPT Plus/Pro (OpenAI Codex)

- Token-Endpoint: `auth.openai.com/oauth/token`
- Account-ID muss zusätzlich mitgesendet werden (`oauth.account_id`)
- Endpoint: `chatgpt.com/backend-api/codex/responses` (kein `api.openai.com`)
- Modell-Support eingeschränkt — nur gpt-5.5 / gpt-5.4 / gpt-5.3-codex /
  gpt-5.2 verifiziert (siehe `_codex_provider.py:CodexModelNotAllowed`)

## Permissions im Frontend

Single-Source: `frontend/src/features/auth/permissions.ts`. Sonst niemand
schreibt Permission-Logic. Alle anderen Features importieren `canX(...)` /
`isAdmin()` von dort.

## Wichtige Dateien

| Datei | Verantwortung |
|---|---|
| `api/middleware/auth.py` | `require_auth`, `require_admin`, `get_current_user_optional` |
| `api/middleware/api_keys.py` | `create`, `verify`, `list_keys`, `delete` |
| `auth/login_lockout.py` | User + IP Counter, Threshold-Check |
| `auth/users.py` | bcrypt User-Store |
| `oauth/anthropic.py` | OAuth-Flow + `resolve_anthropic_token` |
| `oauth/openai_codex.py` | ChatGPT Plus/Pro OAuth |
| `oauth/_llm_config_rmw.py` | Atomic Provider-Update mit fcntl.flock |
| `api/routes/auth.py` | Login/Logout/me-Endpoints |
| `api/routes/api_keys.py` | API-Key-Management-Endpoints |
| `api/routes/llm_oauth.py` | OAuth-Start/Exchange-Endpoints |
| `frontend/src/features/auth/permissions.ts` | Single-Source-Permissions |

## Tests

- `test_auth.py` (10) — JWT Encode/Decode, require_auth/admin, optional
- `test_lockout.py` (8) — Lockout-Logic
- `test_session_ownership.py` (6) — User vs Admin vs Fremde
- `test_llm_config_rmw.py` (6) — OAuth atomic refresh + Concurrency
- `test_api_integration.py` (11) — Login/me/Sessions-CRUD via TestClient
