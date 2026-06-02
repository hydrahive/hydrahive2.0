# Feature Map: Credentials — Secrets Vault

> **Modul:** `core/src/hydrahive/credentials/`  
> **Frontend:** `frontend/src/features/credentials/`  
> **Was:** Zentraler Secret-Speicher. API-Keys, Passwörter, SSH-Keys, Tokens.  
> **Warum:** Secrets nie im Klartext in Configs oder Agent-Prompts — immer aus dem Vault.

---

## Konzept

```
Agent ruft fetch_url auf:
  {url: "https://api.openai.com/...", auth: "openai"}

fetch_url.py:
  → credentials/store.py.get("openai")
  → {Authorization: "Bearer sk-..."}  ← aus Vault
  → Request geht raus
  → Tool-Result: nur Response-Body, KEIN Token sichtbar
```

Secrets werden **niemals** in Tool-Results, Logs oder Datamining gespeichert.
`credentials/redaction.py` filtert bekannte Secrets aus allem raus.

---

## Credential-Typen

| Typ | Format | Verwendung |
|---|---|---|
| `api_key` | `{"key": "sk-..."}` | API-Schlüssel für Web-Services |
| `basic_auth` | `{"user": "...", "password": "..."}` | HTTP Basic Auth |
| `bearer_token` | `{"token": "..."}` | Bearer-Token |
| `ssh_key` | `{"private_key": "...", "public_key": "..."}` | SSH-Zugriff |
| `smtp` | `{"host": "...", "port": 587, "user": "...", "pass": "..."}` | E-Mail |
| `webhook_secret` | `{"secret": "..."}` | HMAC-Verifikation |
| `custom` | `{...}` | Beliebige JSON-Struktur |

---

## Speicherung

```
/var/lib/hydrahive2/credentials.enc
```

- AES-256-GCM verschlüsselt
- Key kommt aus `settings.credentials_key` (aus Umgebungsvariable)
- Backup: ebenfalls verschlüsselt

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `credentials/store.py` | **CRUD**: get, set, delete. Verschlüsselung/Entschlüsselung. |
| `credentials/encryption.py` | AES-256-GCM-Wrapper |
| `credentials/redaction.py` | Secrets aus Strings rausfiltern (für Logs/Tool-Results) |
| `credentials/profiles.py` | Credential-Profile verwalten (Name → Secret) |
| `api/routes/credentials.py` | REST-Endpoints (ohne echte Secret-Werte zu leaken) |
| `frontend/features/credentials/` | UI: Credential anlegen, bearbeiten, löschen |

---

## API-Endpoints

| Endpoint | Beschreibung |
|---|---|
| `GET /api/credentials` | Credential-Namen-Liste (OHNE Werte) |
| `POST /api/credentials` | Credential anlegen |
| `PUT /api/credentials/{name}` | Credential bearbeiten |
| `DELETE /api/credentials/{name}` | Credential löschen |
| `POST /api/credentials/{name}/test` | Verbindung testen |

**Wichtig:** `GET /api/credentials` gibt KEINE Secret-Werte zurück. Nur Namen + Typ.

---

## Nutzung in Tools

```python
# fetch_url automatisch:
fetch_url(url="https://...", auth="credential-name")

# Manuell in Custom-Tools:
from hydrahive.credentials.store import get_credential
secret = get_credential("my-api-key")  # → {"key": "sk-..."}
```

---

## Vordefinierte Credential-Typen für Tools

| Credential-Name | Genutzt von | Zweck |
|---|---|---|
| `openrouter` | LLM-Client | OpenRouter API-Key |
| `smtp` | send_mail | E-Mail-Server |
| `webmin` | webmin_* Tools | Webmin RPC-Auth |
| `openai-tts` | generate_speech | OpenAI TTS |
| `anthropic` | LLM-Client | Direkter Anthropic-Key (optional) |
| `federation-*` | Federation | Inter-Server-Auth |

---

## Verwandte Subsysteme

- **→ Tools** (`02-tools.md`): `fetch_url` nutzt Credential-Injection
- **→ Auth** (`21-auth-security.md`): Credentials-Verschlüsselungskey in Settings
- **→ Federation** (`26-federation.md`): Federation-Secrets
