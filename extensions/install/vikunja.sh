#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

VIKUNJA_DIR="/opt/vikunja"
VIKUNJA_BINARY="${VIKUNJA_DIR}/vikunja"
VIKUNJA_DATA="/var/lib/vikunja"
VIKUNJA_CONF_DIR="/etc/vikunja"
VIKUNJA_CONF="${VIKUNJA_CONF_DIR}/config.yaml"
VIKUNJA_USER="vikunja"
VIKUNJA_PORT="3456"

info "Installiere Vikunja (Task Management)..."

_SERVER_IP="$(hostname -I | awk '{print $1}')"

# --- Abhängigkeiten ---
apt-get update -qq
apt-get install -y --quiet curl wget sqlite3 python3 unzip \
    2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true

# --- Neueste Version ermitteln ---
info "Ermittle neueste Vikunja-Version..."
LATEST_VERSION="$(curl -sf 'https://api.github.com/repos/go-vikunja/vikunja/releases/latest' \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('tag_name','v2.2.2'))" 2>/dev/null \
    || echo 'v2.2.2')"
info "Neueste Version: ${LATEST_VERSION}"

# --- Schon installiert und aktuell? ---
if [ -x "${VIKUNJA_BINARY}" ]; then
    INSTALLED_VERSION="$("${VIKUNJA_BINARY}" version 2>/dev/null | grep -oP 'v[\d.]+' | head -1 || echo "")"
    if [ "${INSTALLED_VERSION}" = "${LATEST_VERSION}" ]; then
        success "Vikunja ${INSTALLED_VERSION} bereits aktuell"
        systemctl start vikunja 2>/dev/null || true
        exit 0
    fi
    info "Update von ${INSTALLED_VERSION} auf ${LATEST_VERSION}..."
    systemctl stop vikunja 2>/dev/null || true
fi

# --- Binary herunterladen ---
mkdir -p "${VIKUNJA_DIR}"
DL_URL="https://github.com/go-vikunja/vikunja/releases/download/${LATEST_VERSION}/vikunja-${LATEST_VERSION}-linux-amd64-full.zip"

info "Lade vikunja-${LATEST_VERSION}-linux-amd64-full.zip..."
curl -fSL "${DL_URL}" -o "/tmp/vikunja.zip" \
    || die "Download fehlgeschlagen: ${DL_URL}"

# SHA256-Verifizierung
CHECKSUM_URL="https://github.com/go-vikunja/vikunja/releases/download/${LATEST_VERSION}/vikunja-${LATEST_VERSION}-linux-amd64-full.zip.sha256"
if curl -fsSL "${CHECKSUM_URL}" -o "/tmp/vikunja.zip.sha256" 2>/dev/null; then
    EXPECTED_HASH="$(awk '{print $1}' /tmp/vikunja.zip.sha256)"
    ACTUAL_HASH="$(sha256sum /tmp/vikunja.zip | awk '{print $1}')"
    if [ -n "${EXPECTED_HASH}" ] && [ "${EXPECTED_HASH}" != "${ACTUAL_HASH}" ]; then
        rm -f /tmp/vikunja.zip /tmp/vikunja.zip.sha256
        die "SHA256-Prüfsumme stimmt nicht überein"
    fi
    success "SHA256 korrekt: ${ACTUAL_HASH:0:16}..."
    rm -f /tmp/vikunja.zip.sha256
else
    warn "Checksum-Datei nicht verfügbar — überspringe Verifikation"
fi

info "Entpacke ZIP..."
VIKUNJA_EXTRACT=/tmp/vikunja-extract
rm -rf "${VIKUNJA_EXTRACT}"
mkdir -p "${VIKUNJA_EXTRACT}"
unzip -o -q /tmp/vikunja.zip -d "${VIKUNJA_EXTRACT}"
rm -f /tmp/vikunja.zip

# Binary finden
FOUND_BIN="$(find /tmp/vikunja-extract -name 'vikunja*linux*amd64' -type f ! -name '*.sha256' | head -1)"
if [ -z "${FOUND_BIN}" ]; then
    FOUND_BIN="$(find /tmp/vikunja-extract -type f -printf '%s %p\n' | sort -rn | head -1 | awk '{print $2}')"
fi
[ -n "${FOUND_BIN}" ] || die "Binary nicht im ZIP gefunden"
file "${FOUND_BIN}" | grep -q "ELF" || die "Gefundene Datei ist keine Binary"
mv "${FOUND_BIN}" "${VIKUNJA_BINARY}"
chmod 755 "${VIKUNJA_BINARY}"
rm -rf "${VIKUNJA_EXTRACT}"
success "Vikunja ${LATEST_VERSION} installiert"

# --- System-User ---
if ! id "${VIKUNJA_USER}" &>/dev/null; then
    if getent group "${VIKUNJA_USER}" &>/dev/null; then
        useradd -r -s /bin/false -d "${VIKUNJA_DATA}" -m -g "${VIKUNJA_USER}" "${VIKUNJA_USER}"
    else
        useradd -r -s /bin/false -d "${VIKUNJA_DATA}" -m "${VIKUNJA_USER}"
    fi
    success "System-User '${VIKUNJA_USER}' angelegt"
fi

mkdir -p "${VIKUNJA_DATA}" "${VIKUNJA_CONF_DIR}"
chown -R "${VIKUNJA_USER}:${VIKUNJA_USER}" "${VIKUNJA_DIR}" "${VIKUNJA_DATA}"

# --- Zufälliges JWT-Secret ---
JWT_SECRET="$(head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 48)"

# --- Konfiguration ---
if [ ! -f "${VIKUNJA_CONF}" ]; then
    info "Erstelle ${VIKUNJA_CONF}..."
    cat > "${VIKUNJA_CONF}" << YAMLEOF
service:
  JWTSecret: "${JWT_SECRET}"
  interface: "0.0.0.0:${VIKUNJA_PORT}"
  frontendurl: "http://${_SERVER_IP}:${VIKUNJA_PORT}/"
  enableregistration: true
  enablelinksharing: true
  enablepublicteams: true

database:
  type: "sqlite"
  path: "${VIKUNJA_DATA}/vikunja.db"

files:
  basepath: "${VIKUNJA_DATA}/files"
  maxsize: "20MB"

mailer:
  enabled: false

log:
  level: "WARNING"
  standardout: true
YAMLEOF
    chown root:"${VIKUNJA_USER}" "${VIKUNJA_CONF}"
    chmod 640 "${VIKUNJA_CONF}"
    success "Konfiguration erstellt"
else
    info "${VIKUNJA_CONF} bereits vorhanden"
    sed -i "s|interface:.*|interface: \"0.0.0.0:${VIKUNJA_PORT}\"|" "${VIKUNJA_CONF}"
fi

mkdir -p "${VIKUNJA_DATA}/files"
chown -R "${VIKUNJA_USER}:${VIKUNJA_USER}" "${VIKUNJA_DATA}"

# --- systemd Service ---
cat > /etc/systemd/system/vikunja.service << SVCEOF
[Unit]
Description=Vikunja Task Management
After=network.target

[Service]
Type=simple
User=${VIKUNJA_USER}
Group=${VIKUNJA_USER}
WorkingDirectory=${VIKUNJA_DATA}
ExecStart=${VIKUNJA_BINARY} --config ${VIKUNJA_CONF}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=VIKUNJA_SERVICE_ROOTPATH=${VIKUNJA_DATA}

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable vikunja
systemctl restart vikunja
success "Service 'vikunja' gestartet auf Port ${VIKUNJA_PORT}"

# --- Warten ---
info "Warte auf Vikunja (bis 30 s)..."
for i in $(seq 1 15); do
    sleep 2
    curl -sf "http://127.0.0.1:${VIKUNJA_PORT}/api/v1/info" &>/dev/null && break || true
done
curl -sf "http://127.0.0.1:${VIKUNJA_PORT}/api/v1/info" &>/dev/null \
    && success "Vikunja erreichbar" \
    || warn "Vikunja noch nicht erreichbar — prüfe: journalctl -u vikunja"

# --- Credentials ---
mkdir -p /etc/hydrahive2/extensions
cat > /etc/hydrahive2/extensions/vikunja.credentials.json << CREDEOF
{
  "id": "vikunja",
  "name": "Vikunja (Task Management)",
  "fields": [
    {"label": "URL",     "value": "http://${_SERVER_IP}:${VIKUNJA_PORT}", "secret": false},
    {"label": "Version", "value": "${LATEST_VERSION}",                    "secret": false}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/vikunja.credentials.json
chmod 640 /etc/hydrahive2/extensions/vikunja.credentials.json

success "Vikunja installiert"
info "  URL:     http://${_SERVER_IP}:${VIKUNJA_PORT}"
info "  Ersten Account im Browser anlegen (Registrierung aktiviert)"
