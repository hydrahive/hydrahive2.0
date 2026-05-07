#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

RADARR_DIR="/opt/radarr"
RADARR_DATA="/var/lib/radarr"
RADARR_USER="radarr"
RADARR_PORT="7878"
RADARR_DL_URL="https://radarr.servarr.com/v1/update/master/updatefile?os=linux&runtime=netcore&arch=x64"

info "Installiere Radarr..."

# --- Abhängigkeiten ---
apt-get update -qq
apt-get install -y --quiet curl wget sqlite3 \
    2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true

# --- System-User ---
if ! id "${RADARR_USER}" &>/dev/null; then
    if getent group "${RADARR_USER}" &>/dev/null; then
        useradd -r -s /bin/false -d "${RADARR_DATA}" -g "${RADARR_USER}" "${RADARR_USER}"
    else
        useradd -r -s /bin/false -d "${RADARR_DATA}" "${RADARR_USER}"
    fi
    success "System-User '${RADARR_USER}' angelegt"
fi

mkdir -p "${RADARR_DIR}" "${RADARR_DATA}"
chown "${RADARR_USER}:${RADARR_USER}" "${RADARR_DATA}"

systemctl stop radarr 2>/dev/null || true

# --- Download ---
info "Lade Radarr herunter..."
TMP_TAR="/tmp/radarr_linux.tar.gz"
curl -fSL "${RADARR_DL_URL}" -o "${TMP_TAR}" \
    || die "Radarr-Download fehlgeschlagen"

info "Entpacke nach ${RADARR_DIR}..."
tar -xzf "${TMP_TAR}" -C /opt --overwrite \
    || die "Entpacken fehlgeschlagen"
rm -f "${TMP_TAR}"

# Archiv entpackt nach /opt/Radarr (Großbuchstabe) — umbenennen
if [ -d "/opt/Radarr" ] && [ ! -L "/opt/Radarr" ]; then
    rm -rf "${RADARR_DIR}"
    mv /opt/Radarr "${RADARR_DIR}"
fi
chown -R "${RADARR_USER}:${RADARR_USER}" "${RADARR_DIR}"
success "Radarr entpackt nach ${RADARR_DIR}"

# --- systemd Service ---
cat > /etc/systemd/system/radarr.service << SVCEOF
[Unit]
Description=Radarr - Movie Collection Manager
After=network.target

[Service]
Type=simple
User=${RADARR_USER}
Group=${RADARR_USER}
WorkingDirectory=${RADARR_DIR}
ExecStart=${RADARR_DIR}/Radarr -nobrowser -data=${RADARR_DATA}
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
systemctl enable radarr
systemctl start radarr
success "Service 'radarr' gestartet auf Port ${RADARR_PORT}"

# --- Warten ---
info "Warte auf Radarr (bis 30 s)..."
for i in $(seq 1 15); do
    sleep 2
    curl -sf "http://127.0.0.1:${RADARR_PORT}/" &>/dev/null && break || true
done
curl -sf "http://127.0.0.1:${RADARR_PORT}/" &>/dev/null \
    && success "Radarr erreichbar" \
    || warn "Radarr noch nicht erreichbar — prüfe: journalctl -u radarr"

SERVER_IP=$(hostname -I | awk '{print $1}')
success "Radarr installiert"
info "  URL:    http://${SERVER_IP}:${RADARR_PORT}"
info "  API-Key: Settings → General"
