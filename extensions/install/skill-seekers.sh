#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

STORAGE_BASE="/var/lib/hydrahive2/extensions/skill-seekers"
ENV_FILE="/etc/hydrahive2/extensions/skill-seekers.env"

info "Installiere Skill Seekers MCP-Server..."

command -v docker &>/dev/null || die "Docker nicht gefunden — bitte zuerst Docker installieren"
docker compose version &>/dev/null || die "Docker Compose (Plugin) nicht gefunden"

# --- Verzeichnisse anlegen ---
mkdir -p "${STORAGE_BASE}/data" "${STORAGE_BASE}/output"
chown -R 1000:1000 "${STORAGE_BASE}"
success "Storage ${STORAGE_BASE} bereit"

# --- Env-Datei schreiben (aus install_params) ---
mkdir -p /etc/hydrahive2/extensions
cat > "${ENV_FILE}" <<EOF
SKILL_SEEKERS_ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
SKILL_SEEKERS_GITHUB_TOKEN=${GITHUB_TOKEN:-}
SKILL_SEEKERS_OPENAI_API_KEY=${OPENAI_API_KEY:-}
EOF
chmod 600 "${ENV_FILE}"
success "Konfiguration gespeichert"

# --- Credentials speichern ---
SERVER_IP=$(hostname -I | awk '{print $1}')
cat > /etc/hydrahive2/extensions/skill-seekers.credentials.json <<CREDEOF
{
  "id": "skill-seekers",
  "name": "Skill Seekers (MCP-Server)",
  "fields": [
    {"label": "MCP-Endpoint", "value": "http://${SERVER_IP}:8765", "secret": false},
    {"label": "Health", "value": "http://${SERVER_IP}:8765/health", "secret": false}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/skill-seekers.credentials.json
chmod 640 /etc/hydrahive2/extensions/skill-seekers.credentials.json

success "Skill Seekers Installation vorbereitet"
info "  MCP-Endpoint: http://${SERVER_IP}:8765"
info "  Hinweis: Erster Start dauert ~2 Min (pip install beim ersten Hochfahren)"
info "  Docker Compose startet den Container im Anschluss..."
