#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

CS_PORT="8484"
CS_USER="hydrahive"
CS_PASS="$(head -c 16 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 20)"

info "Installiere Code-Server..."

# --- Neueste Version ermitteln ---
CS_VERSION="$(curl -sf "https://api.github.com/repos/coder/code-server/releases/latest" \
    | python3 -c "import sys,json; v=json.load(sys.stdin).get('tag_name','v4.96.2'); print(v.lstrip('v'))" 2>/dev/null \
    || echo "4.96.2")"
info "Version: ${CS_VERSION}"

# --- Schon installiert? ---
if command -v code-server &>/dev/null; then
    INSTALLED="$(code-server --version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "")"
    if [ "${INSTALLED}" = "${CS_VERSION}" ]; then
        success "Code-Server ${INSTALLED} bereits aktuell"
        systemctl start code-server 2>/dev/null || true
        exit 0
    fi
    info "Update von ${INSTALLED} auf ${CS_VERSION}..."
    systemctl stop code-server 2>/dev/null || true
fi

# --- Download + Install ---
ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64)  DL_ARCH="amd64" ;;
    aarch64) DL_ARCH="arm64" ;;
    *)        die "Nicht unterstützte Architektur: ${ARCH}" ;;
esac

DL_URL="https://github.com/coder/code-server/releases/download/v${CS_VERSION}/code-server_${CS_VERSION}_${DL_ARCH}.deb"
info "Lade Code-Server ${CS_VERSION}..."
curl -fSL "${DL_URL}" -o /tmp/code-server.deb \
    || die "Download fehlgeschlagen"

dpkg -i /tmp/code-server.deb 2>/dev/null \
    || { apt-get install -f -y --quiet; dpkg -i /tmp/code-server.deb; }
rm -f /tmp/code-server.deb
success "Code-Server ${CS_VERSION} installiert"

# --- Konfiguration ---
CS_CONFIG_DIR="/home/${CS_USER}/.config/code-server"
mkdir -p "${CS_CONFIG_DIR}"

# Passwort nur beim ersten Mal setzen
if [ ! -f "${CS_CONFIG_DIR}/config.yaml" ]; then
    cat > "${CS_CONFIG_DIR}/config.yaml" << CONFEOF
bind-addr: 0.0.0.0:${CS_PORT}
auth: password
password: ${CS_PASS}
cert: false
CONFEOF
else
    CS_PASS="$(grep '^password:' "${CS_CONFIG_DIR}/config.yaml" | awk '{print $2}')"
    sed -i "s|^bind-addr:.*|bind-addr: 0.0.0.0:${CS_PORT}|" "${CS_CONFIG_DIR}/config.yaml"
fi
chown -R "${CS_USER}:${CS_USER}" "${CS_CONFIG_DIR}" 2>/dev/null || true
success "Konfiguration erstellt (Port ${CS_PORT})"

# --- systemd Service ---
cat > /etc/systemd/system/code-server.service << SVCEOF
[Unit]
Description=Code-Server (VS Code im Browser)
After=network.target

[Service]
Type=simple
User=${CS_USER}
Group=${CS_USER}
WorkingDirectory=/home/${CS_USER}
ExecStart=/usr/bin/code-server --config ${CS_CONFIG_DIR}/config.yaml
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable code-server

# Port-Konflikt prüfen
if ss -tlnp 2>/dev/null | grep -q ":${CS_PORT} "; then
    PORTOWNER="$(ss -tlnp | grep ":${CS_PORT} " | grep -oP '(?<=users:\(\(")[^"]+' | head -1 || echo "unbekannt")"
    warn "Port ${CS_PORT} bereits belegt von: ${PORTOWNER}"
    warn "Code-Server kann nicht starten — anderen Port wählen oder Konflikt lösen"
    exit 1
fi

systemctl start code-server
sleep 1
if ! systemctl is-active --quiet code-server; then
    warn "Service-Start fehlgeschlagen — letzte Logs:"
    journalctl -u code-server -n 20 --no-pager 2>/dev/null || true
    exit 1
fi
success "Service 'code-server' gestartet auf Port ${CS_PORT}"

# --- Warten ---
info "Warte auf Code-Server (bis 20 s)..."
for i in $(seq 1 10); do
    sleep 2
    curl -sf "http://127.0.0.1:${CS_PORT}/" &>/dev/null && break || true
done
if ! curl -sf "http://127.0.0.1:${CS_PORT}/" &>/dev/null; then
    warn "Code-Server antwortet nicht — Logs:"
    journalctl -u code-server -n 30 --no-pager 2>/dev/null || true
fi

# --- Credentials ---
SERVER_IP=$(hostname -I | awk '{print $1}')
mkdir -p /etc/hydrahive2/extensions
cat > /etc/hydrahive2/extensions/codeserver.credentials.json << CREDEOF
{
  "id": "codeserver",
  "name": "Code-Server (VS Code im Browser)",
  "fields": [
    {"label": "URL",      "value": "http://${SERVER_IP}:${CS_PORT}", "secret": false},
    {"label": "Passwort", "value": "${CS_PASS}",                     "secret": true}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/codeserver.credentials.json
chmod 640 /etc/hydrahive2/extensions/codeserver.credentials.json

success "Code-Server installiert"
info "  URL:      http://${SERVER_IP}:${CS_PORT}"
info "  Passwort: ${CS_PASS}"
