#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }

MCP_CONFIG="/etc/hydrahive2/mcp_servers.json"
ENV_FILE="/etc/hydrahive2/extensions/composio.env"
API_BASE="https://backend.composio.dev/api/v3.1"

info "Installiere Composio MCP-Integration..."

if [ -z "${COMPOSIO_API_KEY:-}" ]; then
    echo "[ERROR] COMPOSIO_API_KEY fehlt" >&2
    exit 1
fi

# --- Alten lokalen Service aufräumen falls noch vorhanden ---
systemctl stop hydrahive-composio 2>/dev/null || true
systemctl disable hydrahive-composio 2>/dev/null || true
rm -f /etc/systemd/system/hydrahive-composio.service
systemctl daemon-reload 2>/dev/null || true

# --- API-Key speichern ---
mkdir -p /etc/hydrahive2/extensions
printf 'COMPOSIO_API_KEY=%s\n' "${COMPOSIO_API_KEY}" > "${ENV_FILE}"
chmod 600 "${ENV_FILE}"
success "API-Key gespeichert"

# --- MCP-Server anlegen + URL abrufen ---
info "Rufe Composio MCP-Server an..."

python3 - <<PYEOF
import json, sys, urllib.request, urllib.error, pathlib, datetime

API_KEY = "${COMPOSIO_API_KEY}"
API_BASE = "${API_BASE}"
MCP_CONFIG = "${MCP_CONFIG}"

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def api(method, path, body=None):
    url = API_BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        print(f"[ERROR] {method} {path} → HTTP {e.code}: {msg}", file=sys.stderr)
        sys.exit(1)

# Bestehende Server abrufen
servers = api("GET", "/mcp/servers").get("items", [])

if servers:
    server_id = servers[0]["id"]
    print(f"[INFO] Existierender Composio MCP-Server gefunden: {server_id}")
else:
    # Neuen Server anlegen
    result = api("POST", "/mcp/servers", {
        "name": "HydraHive",
        "auth_config_ids": [],
        "no_auth_apps": [],
    })
    server_id = result["id"]
    print(f"[OK] Composio MCP-Server angelegt: {server_id}")

# URL generieren
gen = api("POST", "/mcp/servers/generate", {"mcp_server_id": server_id})
mcp_url = gen.get("mcp_url", "")
if not mcp_url:
    print("[ERROR] Keine MCP-URL in der Antwort", file=sys.stderr)
    print(json.dumps(gen, indent=2), file=sys.stderr)
    sys.exit(1)

print(f"[OK] MCP-URL: {mcp_url}")

# In HydraHive MCP-Registry eintragen
cfg_path = pathlib.Path(MCP_CONFIG)
cfg_path.parent.mkdir(parents=True, exist_ok=True)

data = {"servers": []}
if cfg_path.exists():
    try:
        data = json.loads(cfg_path.read_text())
    except json.JSONDecodeError:
        pass

now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
existing = next((s for s in data.get("servers", []) if s.get("id") == "composio"), None)
if existing:
    existing["url"] = mcp_url
    existing["headers"] = {"x-api-key": API_KEY}
    existing["updated_at"] = now
    print("[INFO] Composio MCP-Eintrag aktualisiert")
else:
    data.setdefault("servers", []).append({
        "id": "composio",
        "name": "Composio (SaaS-Integrationen)",
        "transport": "sse",
        "url": mcp_url,
        "headers": {"x-api-key": API_KEY},
        "description": "500+ SaaS-Integrationen via Composio — Gmail, Slack, GitHub, Notion u.v.m.",
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
    {"label": "Dashboard", "value": "https://dashboard.composio.dev", "secret": false}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/composio.credentials.json 2>/dev/null || true
chmod 640 /etc/hydrahive2/extensions/composio.credentials.json

success "Composio MCP-Integration bereit"
info "  Apps verbinden: https://dashboard.composio.dev"
