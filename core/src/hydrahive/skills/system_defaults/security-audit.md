---
name: security-audit
description: Security-Check für neue Endpoints, Tools und Auth-Logik
when_to_use: Wenn neue API-Endpoints, Tools oder Auth-Code geschrieben wird. Vor jedem Commit mit sicherheitsrelevantem Code.
tools_required: [file_read, shell_exec]
---

# Security-Audit Checkliste

## Pflicht vor jedem Commit

- [ ] Keine Secrets im Code (API-Keys, Passwörter, Tokens)
- [ ] User-Input validiert bevor er verarbeitet wird
- [ ] SQL-Queries parametrisiert (kein String-Concat)
- [ ] Dateipfade sanitized (kein Path-Traversal via `../`)
- [ ] Fehler-Responses zeigen keine internen Details

## Neue API-Endpoints

```python
# SSRF-Check: externe URLs nie direkt fetchen ohne Whitelist
# FALSCH:
resp = httpx.get(user_provided_url)

# RICHTIG: Schema + Host validieren
from urllib.parse import urlparse
parsed = urlparse(url)
if parsed.scheme not in ("http", "https") or parsed.hostname in BLOCKED_HOSTS:
    raise ValueError("URL nicht erlaubt")
```

- Rate-Limiting vorhanden?
- Auth-Check vor jeder Business-Logik?
- Input-Schema mit Pydantic validiert?

## Neue Tools (shell_exec / file_read etc.)

- Kann der Agent damit auf Dateien außerhalb des Workspace zugreifen?
- Können arbitrary Commands mit User-Input als Argument ausgeführt werden?
- Ist der Output sanitized bevor er zurückgegeben wird?

## Auth-Logik

- Passwörter nur mit bcrypt hashen (niemals MD5/SHA1)
- JWT-Secrets aus Umgebungsvariablen, nie hardcodiert
- Session-Tokens in Memory / HttpOnly-Cookie — nicht localStorage

## Quick-Scan

```bash
# Secrets-Scan
grep -rn "password\s*=\s*['\"]" . --include="*.py" | grep -v test | grep -v "#"
grep -rn "token\s*=\s*['\"]" . --include="*.py" | grep -v test | grep -v "#"

# Offene Ports prüfen
ss -tlnp
```
