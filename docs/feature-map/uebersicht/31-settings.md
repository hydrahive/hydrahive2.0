# Feature Map: Settings — Systemkonfiguration

> **Modul:** `core/src/hydrahive/config/settings.py`  
> **Frontend:** `frontend/src/features/system/`  
> **Was:** Zentrale Systemeinstellungen. Umgebungsvariablen, DB-Werte, Runtime-Config.  
> **Warum:** Ein Ort für alle konfigurierbaren Parameter — kein Magic-String-Chaos.

---

## Settings-Hierarchie

```
1. Defaults (in settings.py)
2. Umgebungsvariablen (Systemstart)
3. DB-Overrides (Runtime — via UI veränderbar)
4. Per-Request-Overrides (Session-Level, nur wenige)
```

---

## Settings-Datei

```python
# config/settings.py — Pydantic BaseSettings

class Settings(BaseSettings):
    # Core
    secret_key: str           # JWT-Signatur-Key
    db_url: str               # SQLite-Pfad oder PostgreSQL-URL
    data_dir: Path            # /var/lib/hydrahive2/

    # LLM
    default_model: str = "anthropic/claude-opus-4-5"
    default_max_tokens: int = 8192
    
    # Auth
    jwt_secret: str
    jwt_expiry_hours: int = 1
    jwt_refresh_days: int = 30
    
    # Rate-Limiting
    ratelimit_requests_per_minute: int = 60
    lockout_max_attempts: int = 10
    lockout_duration_minutes: int = 15
    
    # Credentials
    credentials_key: str       # Verschlüsselungs-Key für Vault
    
    # Samba
    samba_enabled: bool = True
    samba_config_dir: Path = Path("/etc/samba/hh-projects.d")
    
    # Mirror/Datamining
    mirror_enabled: bool = False
    mirror_db_url: str = ""   # PostgreSQL-URL für Mirror
    
    # Media
    openrouter_api_key: str = ""  # Oder aus Credential-Store
    
    class Config:
        env_file = "/etc/hydrahive2/env"
        env_prefix = "HH2_"
```

---

## DB-Overrides

Manche Settings sind über die UI editierbar (kein Neustart nötig):

| Setting | Beschreibung |
|---|---|
| `default_model` | Standard-LLM für neue Sessions |
| `default_max_tokens` | Standard-Token-Limit |
| `ratelimit_requests_per_minute` | API-Rate-Limit |
| `lockout_max_attempts` | Brute-Force-Schutz |
| `maintenance_mode` | Read-Only-Modus |
| `registration_open` | Neue User erlaubt? |

---

## Frontend-Settings-Seiten

| Route | Beschreibung |
|---|---|
| `/system` | System-Status, Versioninfo, Dienst-Kontrolle |
| `/system/settings` | Alle DB-Overrides editieren |
| `/system/backup` | Backup/Restore |
| `/system/logs` | System-Logs |
| `/users` | User-Verwaltung |
| `/profile` | Eigenes Profil, Passwort, Avatar |

---

## Umgebungsvariablen (wichtigste)

```bash
HH2_SECRET_KEY=...           # REQUIRED: JWT-Schlüssel
HH2_DB_URL=sqlite:///...     # DB-Pfad
HH2_DATA_DIR=/var/lib/hydrahive2
HH2_CREDENTIALS_KEY=...      # REQUIRED: Vault-Schlüssel
HH2_OPENROUTER_API_KEY=...   # Für Media-Tools
HH2_MIRROR_DB_URL=...        # PostgreSQL für Datamining
```

Alle in `/etc/hydrahive2/env` (700 permissions, nur root lesbar).

---

## Verwandte Subsysteme

- **→ Auth** (`21-auth-security.md`): JWT-Secrets aus Settings
- **→ DB** (`03-db.md`): DB-URL aus Settings
- **→ Credentials** (`30-credentials.md`): Credentials-Key aus Settings
- **→ LLM** (`12-llm.md`): Default-Modell aus Settings
