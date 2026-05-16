#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

SHADOWBROKER_DATA="/var/lib/hydrahive2/extensions/shadowbroker/data"
SERVER_IP=$(hostname -I | awk '{print $1}')

info "Installiere ShadowBroker (OSINT-Plattform)..."

# --- Docker prüfen ---
command -v docker &>/dev/null || die "Docker nicht gefunden — bitte zuerst Docker installieren"
docker compose version &>/dev/null || die "Docker Compose (Plugin) nicht gefunden"

# --- Datenpfad anlegen ---
mkdir -p "${SHADOWBROKER_DATA}"
success "Datenpfad ${SHADOWBROKER_DATA} bereit"

# --- Credentials speichern ---
mkdir -p /etc/hydrahive2/extensions
cat > /etc/hydrahive2/extensions/shadowbroker.credentials.json << CREDEOF
{
  "id": "shadowbroker",
  "name": "ShadowBroker (OSINT-Plattform)",
  "fields": [
    {"label": "Frontend", "value": "http://${SERVER_IP}:3007", "secret": false},
    {"label": "Backend API", "value": "http://${SERVER_IP}:8091", "secret": false}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/shadowbroker.credentials.json
chmod 640 /etc/hydrahive2/extensions/shadowbroker.credentials.json

success "ShadowBroker Installation vorbereitet"
info "  Frontend: http://${SERVER_IP}:3007"
info "  Backend:  http://${SERVER_IP}:8091"
info "  Docker Compose startet die Container im Anschluss..."
