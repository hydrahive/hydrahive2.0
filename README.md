# HydraHive2

Selbst gehostetes KI-Agenten-System: ein Backend (FastAPI + SQLite) mit
Tool-Loop, Streaming-Chat, Compaction und MCP-Integration, plus eine
React-Web-Konsole zum Verwalten von Agenten, Projekten und Sessions.

Status: **Alpha** — läuft Ende-zu-Ende auf einem Test-Server, aber noch
nicht für mehrere Produktiv-User getestet. Alleinstellungsmerkmale:

- **Drei Agent-Typen** (Master / Project / Specialist) mit isolierten
  Workspaces und eigenen Memory-Notizen.
- **MCP-Server** über alle drei Transports (stdio, HTTP-Streamable, SSE),
  Tools werden per Agent zugewiesen.
- **Append-only Compaction** mit `firstKeptEntryId`-Pointer — lange
  Konversationen schrumpfen kontrolliert, ohne Geschichte zu verlieren.
- **Mehrere LLM-Provider** parallel (Anthropic, OpenAI, OpenRouter, Groq,
  Mistral, Gemini, MiniMax, NVIDIA NIM) — Modell pro Agent wählbar.
- **Self-Update aus der UI** (Admin klickt einen Knopf, systemd zieht
  per `git pull` + Rebuild + Service-Restart neue Version).
- **Mehrsprachig** (Deutsch / Englisch).

## Quick-Start

### Production (Ubuntu 24.04)

```bash
# Idempotenter Installer — legt User, Pfade, Service, nginx und
# Systemd-Units an. Setzt nichts kaputt wenn nochmal ausgeführt.
git clone https://github.com/hydrahive/hydrahive2.0.git /opt/hydrahive2
cd /opt/hydrahive2/installer
sudo ./install.sh
```

Nach Installation: Browser → `http://<server-ip>/`. Initiales Admin-Passwort
steht im Service-Log:

```bash
sudo journalctl -u hydrahive2 -n 50 | grep "Erster Start"
```

Updates später per Klick im UI (für Admins) oder `sudo ./update.sh`.

### Lokal entwickeln

```bash
git clone https://github.com/hydrahive/hydrahive2.0.git
cd hydrahive2
python3.12 -m venv .venv
.venv/bin/pip install -e core
cd frontend && npm install && cd ..
./dev-start.sh   # Backend auf :8001, Vite auf :5173
```

Default-Admin lokal: `admin / admin123`.

## Architektur in einem Absatz

Backend ist ein einzelner FastAPI-Prozess (`hydrahive`-User, NoNewPrivileges,
ProtectSystem=strict), der die Web-Konsole bedient und Agent-Tool-Loops
ausführt. Agent-Konfigurationen, MCP-Server, LLM-Provider und Projekte
liegen als JSON unter `/var/lib/hydrahive2`. Sessions, Messages und Tool-Calls
in einer SQLite-Datenbank ebendort. nginx terminiert HTTP und proxied
`/api/*` ans Backend. Self-Updates laufen über ein Trigger-File +
systemd-Path-Watcher, der `update.sh` als root startet — der API-Prozess
selbst braucht kein sudo.

Volltext-Spec: [SPEC.md](SPEC.md). Detail-Übergabe für nächsten Build-Tag:
[docs/HANDOVER.md](docs/HANDOVER.md). Arbeitsregeln für Beiträge:
[CLAUDE.md](CLAUDE.md).

## Konfiguration

| Env-Variable | Default | Bedeutung |
|---|---|---|
| `HH_DATA_DIR` | `/var/lib/hydrahive2` | DB, Workspaces, Konfigs |
| `HH_CONFIG_DIR` | `/etc/hydrahive2` | Secret-Key, users.json |
| `HH_HOST` | `127.0.0.1` | Backend-Bind |
| `HH_PORT` | `8765` | Backend-Port |
| `HH_SECRET_KEY` | (gen. beim Install) | JWT-Signing-Key |
| `HH_INITIAL_ADMIN_PASSWORD` | (random beim ersten Start) | Setzt Admin-Passwort beim allerersten Backend-Start |
| `HH_CORS_ORIGINS` | `localhost:5173/4` | Komma-Liste erlaubter CORS-Origins |
| `HH_ENABLE_DOCS` | `0` | `1` aktiviert `/api/docs` (Swagger UI) |

Production stellt diese via systemd-Service-Unit. Im Dev liest
`dev-start.sh` aus `~/.hh2-dev/`.

## Sicherheit

- **JWT-Auth** auf allen API-Endpoints außer `/api/auth/login` und
  `/api/health` (Liveness).
- **Pro-User-Isolation** — non-Admin sehen nur eigene Agents, Projekte,
  Sessions.
- **bcrypt-Hashing** (Cost 12) mit Lazy-Migration alter SHA256-Hashes
  beim nächsten Login.
- **Failed-Login-Lockout**: 5 Versuche pro Username / 20 pro IP innerhalb
  15 Min → 429.
- **systemd-Sandbox**: `NoNewPrivileges=true`, `ProtectSystem=strict`,
  `ReadWritePaths` nur auf Daten- und Konfig-Verzeichnis.
- **nginx-Security-Headers** (CSP, X-Frame-Options, Referrer-Policy,
  Permissions-Policy). HSTS-Eintrag liegt auskommentiert vor — sobald
  HTTPS aktiv ist, eine Zeile uncomment.

Was noch fehlt: HTTPS (geplant über Tailscale-Integration mit Auto-Certs).

## Lizenz

Noch nicht festgelegt — Repo ist privat. Bei Veröffentlichung wird die
Lizenz hier ergänzt.
