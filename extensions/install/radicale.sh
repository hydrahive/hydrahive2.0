#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

RADICALE_USER="radicale"
RADICALE_DATA="/var/lib/radicale/collections"
RADICALE_CONF_DIR="/etc/radicale"
RADICALE_CONF="${RADICALE_CONF_DIR}/config"
RADICALE_LOG_DIR="/var/log/radicale"
RADICALE_PORT="5232"
RADICALE_VENV="/opt/radicale"

info "Installiere Radicale (CalDAV/CardDAV)..."

_SERVER_IP="$(hostname -I | awk '{print $1}')"

# --- Abhängigkeiten ---
info "Installiere Abhängigkeiten..."
apt-get update -qq
apt-get install -y --quiet \
    python3 python3-pip python3-venv python3-dev libssl-dev \
    2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true

# Radicale via apt versuchen, sonst venv
RADICALE_BIN=""
if apt-get install -y --quiet radicale 2>/dev/null; then
    RADICALE_BIN="$(command -v radicale 2>/dev/null || true)"
    [ -n "${RADICALE_BIN}" ] && success "Radicale via apt installiert"
fi

if [ -z "${RADICALE_BIN}" ] || [ ! -x "${RADICALE_BIN}" ]; then
    info "Installiere Radicale in virtualenv ${RADICALE_VENV}..."
    python3 -m venv "${RADICALE_VENV}"
    "${RADICALE_VENV}/bin/pip" install --quiet --upgrade pip
    "${RADICALE_VENV}/bin/pip" install --quiet radicale bcrypt passlib
    RADICALE_BIN="${RADICALE_VENV}/bin/radicale"
    # Symlink für installed_check
    ln -sf "${RADICALE_BIN}" /usr/bin/radicale 2>/dev/null || true
    success "Radicale via pip in ${RADICALE_VENV} installiert"
fi

RADICALE_VERSION="$("${RADICALE_BIN}" --version 2>/dev/null | head -1 || echo 'unbekannt')"
success "Radicale ${RADICALE_VERSION}: ${RADICALE_BIN}"

# --- System-User ---
if ! id "${RADICALE_USER}" &>/dev/null; then
    if getent group "${RADICALE_USER}" &>/dev/null; then
        useradd -r -s /bin/false -d /var/lib/radicale -g "${RADICALE_USER}" "${RADICALE_USER}"
    else
        useradd -r -s /bin/false -d /var/lib/radicale "${RADICALE_USER}"
    fi
    success "System-User '${RADICALE_USER}' angelegt"
fi

# --- Verzeichnisse ---
mkdir -p "${RADICALE_DATA}" "${RADICALE_CONF_DIR}" "${RADICALE_LOG_DIR}"
chown -R "${RADICALE_USER}:${RADICALE_USER}" /var/lib/radicale "${RADICALE_LOG_DIR}"
chmod 750 /var/lib/radicale "${RADICALE_DATA}"

# --- Konfiguration ---
if [ ! -f "${RADICALE_CONF}" ]; then
    info "Erstelle ${RADICALE_CONF}..."
    RADICALE_HTPASSWD="${RADICALE_CONF_DIR}/users"
    touch "${RADICALE_HTPASSWD}"
    chown "${RADICALE_USER}:${RADICALE_USER}" "${RADICALE_HTPASSWD}"
    chmod 640 "${RADICALE_HTPASSWD}"

    cat > "${RADICALE_CONF}" << CFGEOF
[server]
hosts = 0.0.0.0:${RADICALE_PORT}
max_connections = 20
max_content_length = 100000000
timeout = 30

[auth]
type = htpasswd
htpasswd_filename = ${RADICALE_HTPASSWD}
htpasswd_encryption = bcrypt
delay = 1

[storage]
filesystem_folder = ${RADICALE_DATA}

[logging]
level = warning
CFGEOF
    chown root:"${RADICALE_USER}" "${RADICALE_CONF}"
    chmod 640 "${RADICALE_CONF}"
    success "Konfiguration erstellt"

    if [ -x "${RADICALE_VENV}/bin/pip" ]; then
        "${RADICALE_VENV}/bin/pip" install --quiet bcrypt passlib 2>/dev/null || true
    else
        apt-get install -y --quiet python3-bcrypt python3-passlib 2>/dev/null || true
    fi
else
    info "${RADICALE_CONF} bereits vorhanden"
    sed -i "s|^hosts = .*|hosts = 0.0.0.0:${RADICALE_PORT}|" "${RADICALE_CONF}"
fi

# --- systemd Service ---
cat > /etc/systemd/system/radicale.service << SVCEOF
[Unit]
Description=Radicale CalDAV/CardDAV Server
After=network.target

[Service]
Type=simple
User=${RADICALE_USER}
Group=${RADICALE_USER}
ExecStart=${RADICALE_BIN} --config ${RADICALE_CONF}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable radicale
systemctl restart radicale
success "Service 'radicale' gestartet auf Port ${RADICALE_PORT}"

# --- Warten ---
info "Warte auf Radicale (bis 20 s)..."
for i in $(seq 1 10); do
    sleep 2
    curl -sf "http://127.0.0.1:${RADICALE_PORT}/" &>/dev/null && break || true
done
curl -sf "http://127.0.0.1:${RADICALE_PORT}/" &>/dev/null \
    && success "Radicale erreichbar" \
    || warn "Radicale noch nicht erreichbar — prüfe: journalctl -u radicale"

# --- Credentials ---
mkdir -p /etc/hydrahive2/extensions
cat > /etc/hydrahive2/extensions/radicale.credentials.json << CREDEOF
{
  "id": "radicale",
  "name": "Radicale (CalDAV/CardDAV)",
  "fields": [
    {"label": "URL",          "value": "http://${_SERVER_IP}:${RADICALE_PORT}", "secret": false},
    {"label": "Benutzer anlegen", "value": "python3 -c 'import bcrypt; print(\"USER:\"+bcrypt.hashpw(b\"PASS\",bcrypt.gensalt()).decode())' >> /etc/radicale/users", "secret": false},
    {"label": "Htpasswd-Datei", "value": "/etc/radicale/users", "secret": false}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/radicale.credentials.json
chmod 640 /etc/hydrahive2/extensions/radicale.credentials.json

success "Radicale installiert"
info "  URL:       http://${_SERVER_IP}:${RADICALE_PORT}"
info "  CalDAV:    http://${_SERVER_IP}:${RADICALE_PORT}/USER/COLLECTION/"
warn "  Benutzer anlegen: sudo python3 -c 'import bcrypt; print(\"USER:\"+bcrypt.hashpw(b\"PASS\",bcrypt.gensalt()).decode())' >> /etc/radicale/users"
