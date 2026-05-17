#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

ANYTHINGLLM_STORAGE="/var/lib/hydrahive2/extensions/anythingllm/storage"
SERVER_IP=$(hostname -I | awk '{print $1}')

info "Installiere AnythingLLM..."

# --- Docker prüfen ---
command -v docker &>/dev/null || die "Docker nicht gefunden — bitte zuerst Docker installieren"
docker compose version &>/dev/null || die "Docker Compose (Plugin) nicht gefunden"

# --- Storage anlegen (UID 1000 = Container-User) ---
mkdir -p "${ANYTHINGLLM_STORAGE}"
chown -R 1000:1000 "${ANYTHINGLLM_STORAGE}"
success "Storage ${ANYTHINGLLM_STORAGE} bereit"

# --- Secrets generieren (einmalig, idempotent) ---
ENV_FILE="/etc/hydrahive2/extensions/anythingllm.env"
mkdir -p /etc/hydrahive2/extensions

if [ ! -f "${ENV_FILE}" ]; then
    SIG_KEY=$(openssl rand -hex 32)
    SIG_SALT=$(openssl rand -hex 32)
    JWT_SECRET=$(openssl rand -hex 24)
    cat > "${ENV_FILE}" <<EOF
ANYTHINGLLM_SIG_KEY=${SIG_KEY}
ANYTHINGLLM_SIG_SALT=${SIG_SALT}
ANYTHINGLLM_JWT_SECRET=${JWT_SECRET}
EOF
    chmod 600 "${ENV_FILE}"
    success "Secrets generiert"
else
    info "Secrets bereits vorhanden — überspringe"
fi

# --- Credentials speichern ---
cat > /etc/hydrahive2/extensions/anythingllm.credentials.json <<CREDEOF
{
  "id": "anythingllm",
  "name": "AnythingLLM (RAG & Agents)",
  "fields": [
    {"label": "Web-UI", "value": "http://${SERVER_IP}:3001", "secret": false},
    {"label": "API", "value": "http://${SERVER_IP}:3001/api", "secret": false}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/anythingllm.credentials.json
chmod 640 /etc/hydrahive2/extensions/anythingllm.credentials.json

success "AnythingLLM Installation vorbereitet"
info "  Web-UI: http://${SERVER_IP}:3001"
info "  API:    http://${SERVER_IP}:3001/api"
info "  Docker Compose startet den Container im Anschluss..."
