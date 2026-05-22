#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

PORT=9200
SERVICE="hydrahive-composio"
ENV_FILE="/etc/hydrahive2/extensions/composio.env"
MCP_CONFIG="/etc/hydrahive2/mcp_servers.json"

info "Installiere Composio MCP-Server (Port ${PORT})..."

# --- Node.js prüfen ---
if ! command -v node &>/dev/null; then
    info "Node.js nicht gefunden — installiere via NodeSource LTS..."
    apt-get install -y curl gnupg 2>/dev/null || true
    curl -fsSL -o /tmp/nodesource_setup.sh "https://deb.nodesource.com/setup_22.x"
    bash /tmp/nodesource_setup.sh
    rm -f /tmp/nodesource_setup.sh
    apt-get install -y nodejs
    success "Node.js $(node --version) installiert"
else
    success "Node.js $(node --version) vorhanden"
fi

# --- API-Key speichern ---
mkdir -p /etc/hydrahive2/extensions
cat > "${ENV_FILE}" <<EOF
COMPOSIO_API_KEY=${COMPOSIO_API_KEY:-}
EOF
chmod 600 "${ENV_FILE}"
success "Konfiguration gespeichert"

# --- systemd-Unit anlegen ---
cat > "/etc/systemd/system/${SERVICE}.service" <<UNIT
[Unit]
Description=Composio MCP-Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=${ENV_FILE}
ExecStart=npx --yes @composio-dev/mcp@latest --transport streamable-http --port ${PORT} --host 0.0.0.0
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE}

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable "${SERVICE}" &>/dev/null
if ! systemctl is-active --quiet "${SERVICE}"; then
    systemctl start "${SERVICE}"
    # kurz warten bis npx den Download abgeschlossen hat
    for i in $(seq 1 12); do
        sleep 5
        if systemctl is-active --quiet "${SERVICE}"; then
            break
        fi
        info "Warte auf Start... (${i}/12)"
    done
fi

if systemctl is-active --quiet "${SERVICE}"; then
    success "Composio MCP-Service aktiv"
else
    warn "Service noch nicht aktiv — er startet beim ersten Run (npx-Download)"
fi

# --- In HydraHive MCP-Registry eintragen ---
SERVER_IP=$(hostname -I | awk '{print $1}')
MCP_URL="http://${SERVER_IP}:${PORT}/mcp"

# Python-Snippet schreibt direkt in die mcp_servers.json
python3 - <<PYEOF
import json, pathlib, datetime

cfg_path = pathlib.Path("${MCP_CONFIG}")
cfg_path.parent.mkdir(parents=True, exist_ok=True)

data = {"servers": []}
if cfg_path.exists():
    try:
        data = json.loads(cfg_path.read_text())
    except json.JSONDecodeError:
        pass

# Nicht doppelt eintragen
if any(s.get("id") == "composio" for s in data.get("servers", [])):
    print("[INFO] Composio bereits in MCP-Registry — übersprungen")
else:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    data.setdefault("servers", []).append({
        "id": "composio",
        "name": "Composio (SaaS-Integrationen)",
        "transport": "http",
        "url": "${MCP_URL}",
        "headers": {},
        "description": "1000+ SaaS-Integrationen: Gmail, Slack, GitHub, Notion, Jira u.v.m.",
        "enabled": True,
        "created_at": now,
        "updated_at": now,
    })
    tmp = cfg_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(cfg_path)
    print("[OK] Composio in HydraHive MCP-Registry eingetragen")
PYEOF

# --- Credentials-Datei für Extension-UI ---
cat > /etc/hydrahive2/extensions/composio.credentials.json <<CREDEOF
{
  "id": "composio",
  "name": "Composio (SaaS-Integrationen)",
  "fields": [
    {"label": "MCP-Endpoint", "value": "http://${SERVER_IP}:${PORT}/mcp", "secret": false},
    {"label": "Health", "value": "http://${SERVER_IP}:${PORT}/health", "secret": false},
    {"label": "Dashboard", "value": "https://app.composio.dev", "secret": false}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/composio.credentials.json 2>/dev/null || true
chmod 640 /etc/hydrahive2/extensions/composio.credentials.json

success "Composio MCP-Server bereit"
info "  Endpoint: http://${SERVER_IP}:${PORT}/mcp"
info "  API-Key:  https://app.composio.dev → Settings → API Keys"
info "  Alle Agenten können jetzt Composio-Tools nutzen"
