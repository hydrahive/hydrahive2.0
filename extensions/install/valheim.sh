#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

VH_DIR="/opt/valheim"
VH_USER="valheim"
VH_PORT="2456"
WORLD_NAME="${WORLD_NAME:-HydraHiveWorld}"
SERVER_NAME="${SERVER_NAME:-HydraHive Valheim}"
SERVER_PASS="${SERVER_PASS:-valheim_$(hostname | md5sum | head -c8)}"
STEAMCMD_DIR="/opt/steamcmd"

info "Installiere Valheim Dedicated Server..."

# --- Dependencies ---
info "Installiere Dependencies..."
dpkg --add-architecture i386 2>/dev/null || true
apt-get update -qq 2>&1 | tail -1
apt-get install -y -qq lib32gcc-s1 curl tar 2>&1 | tail -3
success "Dependencies installiert"

# --- SteamCMD ---
if [ ! -f "${STEAMCMD_DIR}/steamcmd.sh" ]; then
    info "Installiere SteamCMD..."
    mkdir -p "${STEAMCMD_DIR}"
    curl -s -o /tmp/steamcmd.tar.gz "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
    tar -xzf /tmp/steamcmd.tar.gz -C "${STEAMCMD_DIR}"
    rm /tmp/steamcmd.tar.gz
    success "SteamCMD installiert"
else
    success "SteamCMD bereits vorhanden"
fi

# --- System-User ---
if ! id "${VH_USER}" &>/dev/null; then
    useradd -r -m -d "${VH_DIR}" -s /bin/bash "${VH_USER}"
    success "User '${VH_USER}' erstellt"
fi
mkdir -p "${VH_DIR}"

# --- Valheim installieren/updaten ---
info "Installiere/Aktualisiere Valheim Server via SteamCMD (App ID 896660)..."
"${STEAMCMD_DIR}/steamcmd.sh" \
    +force_install_dir "${VH_DIR}" \
    +login anonymous \
    +app_update 896660 validate \
    +quit 2>&1 | tail -10
success "Valheim Server installiert/aktualisiert"

mkdir -p "${VH_DIR}/.config/unity3d/IronGate/Valheim"
chown -R "${VH_USER}:${VH_USER}" "${VH_DIR}"

# --- Firewall ---
if command -v ufw &>/dev/null; then
    ufw allow ${VH_PORT}:$((VH_PORT+2))/udp comment "Valheim Server" 2>/dev/null || true
    success "Firewall: Port ${VH_PORT}-$((VH_PORT+2))/udp geöffnet"
fi

# --- systemd Service ---
cat > /etc/systemd/system/valheim.service << SVCEOF
[Unit]
Description=Valheim Dedicated Server
After=network.target

[Service]
Type=simple
User=${VH_USER}
WorkingDirectory=${VH_DIR}
ExecStart=${VH_DIR}/valheim_server.x86_64 \
    -name "${SERVER_NAME}" \
    -port ${VH_PORT} \
    -world "${WORLD_NAME}" \
    -password "${SERVER_PASS}" \
    -public 0
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal
Environment=SteamAppId=892970

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable valheim 2>/dev/null || true
systemctl start valheim 2>/dev/null \
    || warn "Server Start fehlgeschlagen — prüfe: journalctl -u valheim"
success "systemd Service 'valheim' gestartet"

# --- Credentials ---
mkdir -p /etc/hydrahive2/extensions
cat > /etc/hydrahive2/extensions/valheim.credentials.json << CREDEOF
{
  "id": "valheim",
  "name": "Valheim Dedicated Server",
  "fields": [
    {"label": "Server-Name",  "value": "${SERVER_NAME}",         "secret": false},
    {"label": "Welt-Name",    "value": "${WORLD_NAME}",          "secret": false},
    {"label": "Port",         "value": "${VH_PORT}-$((VH_PORT+2))/udp", "secret": false},
    {"label": "Passwort",     "value": "${SERVER_PASS}",         "secret": true}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/valheim.credentials.json
chmod 640 /etc/hydrahive2/extensions/valheim.credentials.json

success "Valheim Server installiert"
info "  Server: ${SERVER_NAME}"
info "  Welt:   ${WORLD_NAME}"
info "  Port:   ${VH_PORT}-$((VH_PORT+2))/udp"
info "  Passwort: ${SERVER_PASS}"
info "  Logs:   journalctl -u valheim -f"
