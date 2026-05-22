#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

MCP_CONFIG="/etc/hydrahive2/mcp_servers.json"
ENV_FILE="/etc/hydrahive2/extensions/composio.env"

info "Installiere Composio MCP-Integration..."

# --- API-Key prüfen ---
if [ -z "${COMPOSIO_API_KEY:-}" ]; then
    echo "[ERROR] COMPOSIO_API_KEY fehlt — bitte API-Key unter app.composio.dev → Settings → API Keys erstellen" >&2
    exit 1
fi

# --- Alten lokalen Service aufräumen falls noch vorhanden ---
if systemctl is-active --quiet hydrahive-composio 2>/dev/null; then
    info "Stoppe alten lokalen Composio-Service..."
    systemctl stop hydrahive-composio 2>/dev/null || true
    systemctl disable hydrahive-composio 2>/dev/null || true
fi
rm -f /etc/systemd/system/hydrahive-composio.service
systemctl daemon-reload 2>/dev/null || true

# --- API-Key speichern ---
mkdir -p /etc/hydrahive2/extensions
cat > "${ENV_FILE}" <<EOF
COMPOSIO_API_KEY=${COMPOSIO_API_KEY}
EOF
chmod 600 "${ENV_FILE}"
success "API-Key gespeichert"

# --- In HydraHive MCP-Registry eintragen ---
MCP_URL="https://mcp.composio.dev/composio?api_key=${COMPOSIO_API_KEY}"

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

# Bereits vorhanden → aktualisieren (API-Key kann sich ändern)
now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
existing = next((s for s in data.get("servers", []) if s.get("id") == "composio"), None)
if existing:
    existing["url"] = "${MCP_URL}"
    existing["updated_at"] = now
    print("[INFO] Composio MCP-Eintrag aktualisiert")
else:
    data.setdefault("servers", []).append({
        "id": "composio",
        "name": "Composio (SaaS-Integrationen)",
        "transport": "sse",
        "url": "${MCP_URL}",
        "headers": {},
        "description": "500+ SaaS-Integrationen: Gmail, Slack, GitHub, Notion, Jira u.v.m. — Cloud-hosted MCP",
        "enabled": True,
        "created_at": now,
        "updated_at": now,
    })
    print("[OK] Composio in HydraHive MCP-Registry eingetragen")

tmp = cfg_path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
tmp.replace(cfg_path)
PYEOF

# --- Credentials-Datei für Extension-UI ---
cat > /etc/hydrahive2/extensions/composio.credentials.json <<CREDEOF
{
  "id": "composio",
  "name": "Composio (SaaS-Integrationen)",
  "fields": [
    {"label": "MCP-Endpoint", "value": "https://mcp.composio.dev/composio", "secret": false},
    {"label": "Dashboard", "value": "https://app.composio.dev", "secret": false}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/composio.credentials.json 2>/dev/null || true
chmod 640 /etc/hydrahive2/extensions/composio.credentials.json

success "Composio MCP-Integration bereit"
info "  Endpoint: https://mcp.composio.dev/composio"
info "  Alle Agenten können jetzt 500+ Composio-Tools nutzen"
