# HydraHive2 Installer

Setup-Skripte für Ubuntu 22.04 / 24.04 und Debian 12+.

## Schnellstart

Auf einem frischen Server (root oder sudo):

```bash
# 1. Repo klonen
git clone https://github.com/hydrahive/hydrahive2.0.git /opt/hydrahive2

# 2. Installer starten
cd /opt/hydrahive2/installer
sudo ./install.sh
```

Der Installer:

1. Installiert apt-Dependencies (`python3.12`, `nodejs`, `npm`, `git`, optional `nginx`)
2. Legt System-User `hydrahive` an (kein Login)
3. Erstellt `/var/lib/hydrahive2` und `/etc/hydrahive2`
4. Baut Python-venv unter `/opt/hydrahive2/.venv`, installiert `hydrahive-core`
5. Baut das Frontend (`npm run build` → `frontend/dist/`)
6. Installiert `hydrahive2.service` als systemd-Unit, startet ihn

## Konfiguration

Defaults können per Umgebungsvariablen überschrieben werden:

```bash
sudo HH_HOST=0.0.0.0 HH_PORT=8001 HH_INSTALL_NGINX=yes ./install.sh
```

| Variable | Default | Bedeutung |
|---|---|---|
| `HH_REPO_DIR` | `/opt/hydrahive2` | Wo das Repo liegt |
| `HH_USER` | `hydrahive` | Service-User |
| `HH_DATA_DIR` | `/var/lib/hydrahive2` | Sessions-DB, Workspaces, Agents-Configs |
| `HH_CONFIG_DIR` | `/etc/hydrahive2` | LLM-Config, User-DB, MCP-Config |
| `HH_HOST` | `127.0.0.1` | Bind-Adresse — `0.0.0.0` für extern erreichbar |
| `HH_PORT` | `8001` | Backend-Port |
| `HH_INSTALL_NGINX` | `no` | `yes` = nginx-Reverse-Proxy auf Port 80 dazu |
| `HH_INITIAL_ADMIN_PASSWORD` | (random) | Initial-Passwort für `admin`. Ohne: random + Log |

## Erste Anmeldung

Nach dem Installer steht das Admin-Passwort im journal:

```bash
sudo journalctl -u hydrahive2 | grep -A 3 "Admin-User angelegt"
```

Dort findet sich:

```
Username: admin
Passwort: <random-token>
```

Login dann auf http://<server>/  (mit nginx) oder http://<server>:8001/  (ohne).

## Update

Auf neueste main-Branch updaten:

```bash
cd /opt/hydrahive2/installer
sudo ./update.sh
```

Macht: `git pull`, Backend-Deps refresh, Frontend neu bauen, Service-Restart.

## Service-Verwaltung

```bash
sudo systemctl status hydrahive2     # Status
sudo systemctl restart hydrahive2    # Neu starten
sudo journalctl -u hydrahive2 -f     # Live-Log
sudo systemctl stop hydrahive2       # Stoppen
```

## Sicherheits-Härtung

Der systemd-Service nutzt:

- Eigener Service-User `hydrahive`, kein Login-Shell
- `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ProtectHome=true`
- `ReadWritePaths` nur auf `HH_DATA_DIR` und `HH_CONFIG_DIR`

## Problembehebung

**Service startet nicht:**
```bash
sudo journalctl -u hydrahive2 -n 100
```

**Frontend zeigt 502 / API nicht erreichbar:**
- Backend läuft? `systemctl status hydrahive2`
- Bei nginx: `nginx -t` und `journalctl -u nginx`
- CORS-Origins korrekt? `HH_CORS_ORIGINS` setzen wenn anderer Hostname

**`uvx` fehlt für Python-MCP-Server:**
```bash
sudo curl -LsSf https://astral.sh/uv/install.sh | sudo sh
sudo cp /root/.local/bin/uvx /usr/local/bin/
```
