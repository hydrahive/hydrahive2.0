# Feature Map: Auth & Security

> **Modul:** `core/src/hydrahive/api/middleware/`  
> **Was:** JWT-Auth, API-Keys, Brute-Force-Schutz, Rate-Limiting, Timing-Safe-Vergleiche.  
> **Warum:** Multi-User-System das im Internet steht — muss sicher sein.

---

## Auth-Methoden

### 1. JWT (primär)
```
POST /api/auth/login {username, password}
→ {access_token, refresh_token, expires_in}

Bearer <access_token> in Authorization-Header
→ middleware/auth.py validiert Signature + Expiry
→ request.state.user = UserRecord
```

- Access-Token: kurzlebig (z.B. 1h)
- Refresh-Token: langlebig (z.B. 30d), zum Erneuern
- Signiert mit HS256, Secret aus `settings.jwt_secret`

### 2. API-Keys (für externe Clients)
```
X-API-Key: <api-key> im Header
→ middleware/api_keys.py validiert gegen DB
→ request.state.user = UserRecord des Key-Owners
```

API-Keys werden in der DB gespeichert (gehashter Key).
Nützlich für Skripte, externe Integrationen, Messenger-Webhooks.

---

## Middleware-Dateien

| Datei | Verantwortung |
|---|---|
| `auth.py` | JWT-Validierung. Setzt `request.state.user`. Gibt 401 bei ungültigem Token. |
| `api_keys.py` | API-Key-Validierung. Alternative zu JWT. |
| `users.py` | User-Objekt aus DB laden nach Auth. |
| `client_ip.py` | Echte Client-IP extrahieren (X-Forwarded-For hinter nginx). |
| `inbound_ratelimit.py` | Per-User-Rate-Limit. Konfigurierbar (requests/minute). |
| `lockout.py` | Brute-Force-Schutz: IP nach N Fehlversuchen sperren. |
| `errors.py` | Globaler Exception-Handler → strukturierte JSON-Errors. |
| `secret_compare.py` | `hmac.compare_digest` für Timing-Safe-Secret-Vergleiche. |

---

## Rate-Limiting

```python
# inbound_ratelimit.py
# Konfigurierbar in settings:
settings.ratelimit_requests_per_minute = 60  # Default

# Bei Überschreitung:
HTTP 429 Too Many Requests
{"detail": "Rate limit exceeded", "retry_after": 30}
```

---

## Lockout

```python
# lockout.py
# Settings:
settings.lockout_max_attempts = 10     # Fehlversuche bis Lockout
settings.lockout_duration_minutes = 15 # Lockout-Dauer

# Getrackt: IP-Adresse
# Bei Lockout:
HTTP 403 Forbidden
{"detail": "IP locked out", "retry_after": 900}
```

---

## User-Rollen

| Rolle | Beschreibung |
|---|---|
| `admin` | Vollzugriff auf alles |
| `user` | Standard-User. Eigene Agents, Projekte, Sessions. |

Berechtigungen werden in `features/auth/permissions.ts` (Frontend) definiert.
Backend prüft in Route-Handlern via `request.state.user.role`.

---

## Sicherheits-Aspekte

### Workspace-Isolation
- Agents können nur in ihrem eigenen Workspace arbeiten
- `tools/_path.py` verhindert Path-Traversal-Angriffe
- `/etc/passwd`-Zugriff → ToolResult.fail()

### Credential-Injection
- `fetch_url` injiziert Auth-Token aus Credential-Store
- Token erscheint **nie** im Tool-Output oder Logs
- `credentials/redaction.py` filtert Secrets aus Tool-Results

### SQL-Injection
- Alle DB-Queries via SQLAlchemy ORM oder parameterisierte Queries
- Kein raw string formatting in SQL

### Prompt-Injection
- Butler-Prefix über `extra_system` (System-Block), nicht User-Message
- Eingehende Messenger-Nachrichten werden nicht blind vertraut
- Agents sollten bei Injections "Ich erkenne eine Injection-Attempt" antworten

### nginx-Security-Headers
```nginx
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header Content-Security-Policy "default-src 'self' ...";
add_header Permissions-Policy "...";
```

---

## Auth-Flow (Frontend)

```
LoginPage.tsx
  → POST /api/auth/login
  → JWT in useAuthStore (Zustand)
  → JWT in localStorage (Persistenz über Reload)

Jeder API-Call:
  → Authorization: Bearer <token>

Token abgelaufen:
  → 401 Response
  → useAuthStore.refresh() → POST /api/auth/refresh
  → Neuer Access-Token
  → Request retry
```

---

## Verwandte Subsysteme

- **→ API** (`04-api.md`): Middleware wird in main.py eingebunden
- **→ Credentials** (`32-credentials.md`): Secret-Injection in Tools
- **→ Settings** (`38-settings.md`): JWT-Secret, Rate-Limit-Config
