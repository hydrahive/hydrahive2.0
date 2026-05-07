#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

SONARR_DIR="/opt/sonarr"
SONARR_DATA="/var/lib/sonarr"
SONARR_USER="sonarr"
SONARR_PORT="8989"
SONARR_DL_URL="https://services.sonarr.tv/v1/download/main/latest?version=4&os=linux&arch=x64"

info "Installiere Sonarr..."

# --- Abhängigkeiten ---
apt-get update -qq
apt-get install -y --quiet curl wget sqlite3 \
    2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true

# --- System-User ---
if ! id "${SONARR_USER}" &>/dev/null; then
    if getent group "${SONARR_USER}" &>/dev/null; then
        useradd -r -s /bin/false -d "${SONARR_DATA}" -g "${SONARR_USER}" "${SONARR_USER}"
    else
        useradd -r -s /bin/false -d "${SONARR_DATA}" "${SONARR_USER}"
    fi
    success "System-User '${SONARR_USER}' angelegt"
fi

mkdir -p "${SONARR_DIR}" "${SONARR_DATA}"
chown "${SONARR_USER}:${SONARR_USER}" "${SONARR_DATA}"

systemctl stop sonarr 2>/dev/null || true

# --- Download ---
info "Lade Sonarr v4 herunter..."
TMP_TAR="/tmp/sonarr_linux.tar.gz"
curl -fSL "${SONARR_DL_URL}" -o "${TMP_TAR}" \
    || die "Sonarr-Download fehlgeschlagen"

info "Entpacke nach ${SONARR_DIR}..."
tar -xzf "${TMP_TAR}" -C /opt --overwrite \
    || die "Entpacken fehlgeschlagen"
rm -f "${TMP_TAR}"

# Archiv entpackt nach /opt/Sonarr (Großbuchstabe) — umbenennen
if [ -d "/opt/Sonarr" ] && [ ! -L "/opt/Sonarr" ]; then
    rm -rf "${SONARR_DIR}"
    mv /opt/Sonarr "${SONARR_DIR}"
fi
chown -R "${SONARR_USER}:${SONARR_USER}" "${SONARR_DIR}"
success "Sonarr entpackt nach ${SONARR_DIR}"

# --- systemd Service ---
cat > /etc/systemd/system/sonarr.service << SVCEOF
[Unit]
Description=Sonarr - TV Series Collection Manager
After=network.target

[Service]
Type=simple
User=${SONARR_USER}
Group=${SONARR_USER}
WorkingDirectory=${SONARR_DIR}
ExecStart=${SONARR_DIR}/Sonarr -nobrowser -data=${SONARR_DATA}
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
StandardOutput=journal
StandardError=journal
Environment=TMPDIR=/tmp

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable sonarr
systemctl start sonarr
success "Service 'sonarr' gestartet auf Port ${SONARR_PORT}"

# --- Warten ---
info "Warte auf Sonarr (bis 30 s)..."
for i in $(seq 1 15); do
    sleep 2
    curl -sf "http://127.0.0.1:${SONARR_PORT}/" &>/dev/null && break || true
done
curl -sf "http://127.0.0.1:${SONARR_PORT}/" &>/dev/null \
    && success "Sonarr erreichbar" \
    || warn "Sonarr noch nicht erreichbar — prüfe: journalctl -u sonarr"

SERVER_IP=$(hostname -I | awk '{print $1}')
success "Sonarr installiert"
info "  URL:     http://${SERVER_IP}:${SONARR_PORT}"
info "  API-Key: Settings → General"
