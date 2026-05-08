#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

VW_DIR="/opt/vaultwarden"
VW_DATA="/var/lib/vaultwarden"
VW_USER="vaultwarden"
VW_PORT="8222"

info "Installiere Vaultwarden..."

# --- Abhängigkeiten ---
apt-get update -qq
apt-get install -y --quiet curl sqlite3 openssl python3 \
    2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true

# --- System-User ---
if ! id "${VW_USER}" &>/dev/null; then
    useradd -r -s /bin/false -d "${VW_DATA}" -m "${VW_USER}"
    success "System-User '${VW_USER}' angelegt"
fi

mkdir -p "${VW_DIR}" "${VW_DATA}"

# --- Neueste Version ermitteln ---
VW_VERSION="$(curl -sf "https://api.github.com/repos/dani-garcia/vaultwarden/releases/latest" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('tag_name','1.31.0'))" 2>/dev/null \
    || echo "1.31.0")"
info "Version: ${VW_VERSION}"

# --- Schon installiert und aktuell? ---
if [ -x "${VW_DIR}/vaultwarden" ]; then
    INSTALLED="$("${VW_DIR}/vaultwarden" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "")"
    if [ "${INSTALLED}" = "${VW_VERSION}" ]; then
        success "Vaultwarden ${INSTALLED} bereits aktuell"
        systemctl start vaultwarden 2>/dev/null || true
        exit 0
    fi
    info "Update von ${INSTALLED} auf ${VW_VERSION}..."
    systemctl stop vaultwarden 2>/dev/null || true
fi

# --- Download ---
ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64)  DL_ARCH="amd64" ;;
    aarch64) DL_ARCH="arm64" ;;
    *)        die "Nicht unterstützte Architektur: ${ARCH}" ;;
esac

DL_URL="https://github.com/dani-garcia/vaultwarden/releases/download/${VW_VERSION}/vaultwarden-${VW_VERSION}-linux-${DL_ARCH}.tar.gz"
info "Lade Vaultwarden ${VW_VERSION}..."
curl -fSL "${DL_URL}" -o /tmp/vaultwarden.tar.gz \
    || die "Download fehlgeschlagen — URL: ${DL_URL}"

tar -xzf /tmp/vaultwarden.tar.gz -C "${VW_DIR}" 2>/dev/null \
    || { rm -f /tmp/vaultwarden.tar.gz; die "Entpacken fehlgeschlagen"; }
rm -f /tmp/vaultwarden.tar.gz

chmod 755 "${VW_DIR}"/vaultwarden* 2>/dev/null || true

# --- Web-Vault ---
WEB_VAULT_VERSION="$(curl -sf "https://api.github.com/repos/dani-garcia/bw_web_builds/releases/latest" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('tag_name','v2024.6.2c'))" 2>/dev/null \
    || echo "v2024.6.2c")"
info "Lade Web-Vault ${WEB_VAULT_VERSION}..."
curl -fSL "https://github.com/dani-garcia/bw_web_builds/releases/download/${WEB_VAULT_VERSION}/bw_web_${WEB_VAULT_VERSION}.tar.gz" \
    -o /tmp/web_vault.tar.gz 2>/dev/null \
    && tar -xzf /tmp/web_vault.tar.gz -C "${VW_DIR}" 2>/dev/null \
    && rm -f /tmp/web_vault.tar.gz \
    || warn "Web-Vault konnte nicht geladen werden — nur API-Modus"

chown -R "${VW_USER}:${VW_USER}" "${VW_DIR}" "${VW_DATA}"
success "Vaultwarden ${VW_VERSION} nach ${VW_DIR}"

# --- Admin-Token ---
ADMIN_TOKEN="$(head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)"

# --- Konfiguration ---
cat > "${VW_DIR}/.env" << ENVEOF
DATA_FOLDER=${VW_DATA}
WEB_VAULT_FOLDER=${VW_DIR}/web-vault
WEB_VAULT_ENABLED=true
ROCKET_ADDRESS=0.0.0.0
ROCKET_PORT=${VW_PORT}
ADMIN_TOKEN=${ADMIN_TOKEN}
LOG_FILE=${VW_DATA}/vaultwarden.log
LOG_LEVEL=warn
SIGNUPS_ALLOWED=true
SHOW_PASSWORD_HINT=false
DOMAIN=http://127.0.0.1:${VW_PORT}
ENVEOF
chown "${VW_USER}:${VW_USER}" "${VW_DIR}/.env"
chmod 640 "${VW_DIR}/.env"
success ".env konfiguriert"

# --- systemd Service ---
cat > /etc/systemd/system/vaultwarden.service << SVCEOF
[Unit]
Description=Vaultwarden - Bitwarden-kompatibler Passwort-Manager
After=network.target

[Service]
Type=simple
User=${VW_USER}
Group=${VW_USER}
WorkingDirectory=${VW_DIR}
EnvironmentFile=${VW_DIR}/.env
ExecStart=${VW_DIR}/vaultwarden
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable --now vaultwarden
success "Service 'vaultwarden' gestartet auf Port ${VW_PORT}"

# --- Warten ---
info "Warte auf Vaultwarden (bis 20 s)..."
for i in $(seq 1 10); do
    sleep 2
    curl -sf "http://127.0.0.1:${VW_PORT}/" &>/dev/null && break || true
done
curl -sf "http://127.0.0.1:${VW_PORT}/" &>/dev/null \
    && success "Vaultwarden erreichbar" \
    || warn "Vaultwarden noch nicht erreichbar — prüfe: journalctl -u vaultwarden"

# --- Credentials ---
SERVER_IP=$(hostname -I | awk '{print $1}')
mkdir -p /etc/hydrahive2/extensions
cat > /etc/hydrahive2/extensions/vaultwarden.credentials.json << CREDEOF
{
  "id": "vaultwarden",
  "name": "Vaultwarden (Passwort-Manager)",
  "fields": [
    {"label": "URL",         "value": "http://${SERVER_IP}:${VW_PORT}",       "secret": false},
    {"label": "Admin-Panel", "value": "http://${SERVER_IP}:${VW_PORT}/admin", "secret": false},
    {"label": "Admin-Token", "value": "${ADMIN_TOKEN}",                        "secret": true}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/vaultwarden.credentials.json
chmod 640 /etc/hydrahive2/extensions/vaultwarden.credentials.json

success "Vaultwarden installiert"
info "  URL:         http://${SERVER_IP}:${VW_PORT}"
info "  Admin-Panel: http://${SERVER_IP}:${VW_PORT}/admin  (Token oben)"
warn "  Signups nach erstem Account deaktivieren"
