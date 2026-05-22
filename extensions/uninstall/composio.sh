#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }

SERVICE="hydrahive-composio"
MCP_CONFIG="/etc/hydrahive2/mcp_servers.json"

info "Deinstalliere Composio MCP-Server..."

systemctl stop "${SERVICE}" 2>/dev/null || true
systemctl disable "${SERVICE}" 2>/dev/null || true
rm -f "/etc/systemd/system/${SERVICE}.service"
systemctl daemon-reload

rm -f /etc/hydrahive2/extensions/composio.env
rm -f /etc/hydrahive2/extensions/composio.credentials.json

# Aus HydraHive MCP-Registry entfernen
python3 - <<PYEOF
import json, pathlib

cfg_path = pathlib.Path("${MCP_CONFIG}")
if not cfg_path.exists():
    print("[INFO] MCP-Config nicht gefunden — übersprungen")
else:
    try:
        data = json.loads(cfg_path.read_text())
    except json.JSONDecodeError:
        print("[INFO] MCP-Config defekt — übersprungen")
    else:
        before = len(data.get("servers", []))
        data["servers"] = [s for s in data.get("servers", []) if s.get("id") != "composio"]
        if len(data["servers"]) < before:
            tmp = cfg_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            tmp.replace(cfg_path)
            print("[OK] Composio aus MCP-Registry entfernt")
        else:
            print("[INFO] Composio war nicht in MCP-Registry")
PYEOF

success "Composio deinstalliert"
