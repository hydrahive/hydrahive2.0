#!/usr/bin/env bash
# HydraHive2 — Update auf den neuesten Stand der main-Branch.
set -euo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_USER="${HH_USER:-hydrahive}"
HH_DATA_DIR="${HH_DATA_DIR:-/var/lib/hydrahive2}"

log() { printf "\033[1;36m[hh2-update]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[hh2-update]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Bitte mit sudo / als root ausführen."
[ -d "$HH_REPO_DIR/.git" ] || err "$HH_REPO_DIR ist kein Git-Repo."

cd "$HH_REPO_DIR"

log "SSH-Verzeichnis für $HH_USER prüfen"
HH_HOME="/home/$HH_USER"
SSH_DIR="$HH_HOME/.ssh"
mkdir -p "$SSH_DIR"
chown -R "$HH_USER:$HH_USER" "$HH_HOME"
chmod 700 "$SSH_DIR"
touch "$SSH_DIR/known_hosts"
chown "$HH_USER:$HH_USER" "$SSH_DIR/known_hosts"
chmod 600 "$SSH_DIR/known_hosts"
if ! grep -q "github.com" "$SSH_DIR/known_hosts" 2>/dev/null; then
  ssh-keyscan -t ed25519,rsa github.com 2>/dev/null >> "$SSH_DIR/known_hosts" || true
  chown "$HH_USER:$HH_USER" "$SSH_DIR/known_hosts"
fi

log "git pull"
sudo -u hydrahive git pull --ff-only

log "Node.js prüfen"
if ! command -v node >/dev/null 2>&1 || [ "$(node -v 2>/dev/null | cut -d. -f1 | tr -d v)" -lt 20 ]; then
  log "Node.js 20 fehlt — installiere via NodeSource"
  export DEBIAN_FRONTEND=noninteractive
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null
  apt-get install -y nodejs >/dev/null
fi

log "Backend-Dependencies aktualisieren"
"$HH_REPO_DIR/.venv/bin/pip" install --quiet -e "$HH_REPO_DIR/core"

log "Frontend neu bauen"
cd "$HH_REPO_DIR/frontend"
sudo -u hydrahive npm install --silent
sudo -u hydrahive npm run build --silent

WA_BRIDGE_DIR="$HH_REPO_DIR/core/src/hydrahive/communication/whatsapp/bridge"
if [ -f "$WA_BRIDGE_DIR/package.json" ]; then
  log "WhatsApp-Bridge: npm install"
  cd "$WA_BRIDGE_DIR"
  npm install --cache /tmp/npm-cache-hh --no-audit --no-fund --silent
  chown -R hydrahive:hydrahive "$WA_BRIDGE_DIR/node_modules"
fi

log "Systemd-Timer-Units prüfen und migrieren"
HH_DATA_DIR="${HH_DATA_DIR:-/var/lib/hydrahive2}"

# Alte Path-Units deaktivieren falls noch vorhanden (Migration inotify → Timer)
for old in hydrahive2-update.path hydrahive2-restart.path; do
  if [ -f "/etc/systemd/system/$old" ]; then
    systemctl stop "$old" >/dev/null 2>&1 || true
    systemctl disable "$old" >/dev/null 2>&1 || true
    rm -f "/etc/systemd/system/$old"
  fi
done

if [ ! -f /etc/systemd/system/hydrahive2-update.timer ] || [ ! -f /etc/systemd/system/hydrahive2-update.service ]; then
  log "Self-Update-Units anlegen"
  cat > /etc/systemd/system/hydrahive2-update.service <<EOF
[Unit]
Description=HydraHive2 Self-Update Runner
ConditionPathExists=$HH_DATA_DIR/.update_request

[Service]
Type=oneshot
ExecStartPre=/bin/rm -f $HH_DATA_DIR/.update_request
ExecStart=$HH_REPO_DIR/installer/update.sh
StandardOutput=append:/var/log/hydrahive2-update.log
StandardError=append:/var/log/hydrahive2-update.log
EOF
  cat > /etc/systemd/system/hydrahive2-update.timer <<EOF
[Unit]
Description=HydraHive2 Update-Trigger Poller

[Timer]
OnBootSec=30s
OnUnitActiveSec=5s
AccuracySec=1s
Unit=hydrahive2-update.service

[Install]
WantedBy=timers.target
EOF
  touch /var/log/hydrahive2-update.log
  chmod 644 /var/log/hydrahive2-update.log
  systemctl daemon-reload
  systemctl enable hydrahive2-update.timer >/dev/null 2>&1
  systemctl restart hydrahive2-update.timer
fi

if [ ! -f /etc/systemd/system/hydrahive2-restart.timer ] || [ ! -f /etc/systemd/system/hydrahive2-restart.service ]; then
  log "Restart-Trigger-Units anlegen"
  cat > /etc/systemd/system/hydrahive2-restart.service <<EOF
[Unit]
Description=HydraHive2 Restart Runner
ConditionPathExists=$HH_DATA_DIR/.restart_request

[Service]
Type=oneshot
ExecStartPre=/bin/rm -f $HH_DATA_DIR/.restart_request
ExecStart=/bin/systemctl restart hydrahive2.service
EOF
  cat > /etc/systemd/system/hydrahive2-restart.timer <<EOF
[Unit]
Description=HydraHive2 Restart-Trigger Poller

[Timer]
OnBootSec=10s
OnUnitActiveSec=5s
AccuracySec=1s
Unit=hydrahive2-restart.service

[Install]
WantedBy=timers.target
EOF
  systemctl daemon-reload
  systemctl enable hydrahive2-restart.timer >/dev/null 2>&1
  systemctl restart hydrahive2-restart.timer
fi

if [ ! -f /etc/systemd/system/hydrahive2-voice.timer ] || [ ! -f /etc/systemd/system/hydrahive2-voice.service ]; then
  log "Voice-Install-Units anlegen"
  cat > /etc/systemd/system/hydrahive2-voice.service <<EOF
[Unit]
Description=HydraHive2 Voice-Install Runner
ConditionPathExists=$HH_DATA_DIR/.voice_install_request

[Service]
Type=oneshot
ExecStartPre=/bin/rm -f $HH_DATA_DIR/.voice_install_request
ExecStart=$HH_REPO_DIR/installer/modules/55-voice.sh
StandardOutput=append:/var/log/hydrahive2-voice.log
StandardError=append:/var/log/hydrahive2-voice.log
EOF
  cat > /etc/systemd/system/hydrahive2-voice.timer <<EOF
[Unit]
Description=HydraHive2 Voice-Install Trigger Poller

[Timer]
OnBootSec=60s
OnUnitActiveSec=5s
AccuracySec=1s
Unit=hydrahive2-voice.service

[Install]
WantedBy=timers.target
EOF
  touch /var/log/hydrahive2-voice.log
  chmod 644 /var/log/hydrahive2-voice.log
  systemctl daemon-reload
  systemctl enable hydrahive2-voice.timer >/dev/null 2>&1
  systemctl restart hydrahive2-voice.timer
fi

if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "hydrahive2-stt"; then
  log "Voice-Container fehlen — starte 55-voice.sh"
  bash "$HH_REPO_DIR/installer/modules/55-voice.sh"
fi

if ! command -v qemu-system-x86_64 >/dev/null 2>&1 \
   || ! systemctl is-active --quiet hydrahive2-websockify.service; then
  log "VM-Manager-Setup fehlt oder unvollständig — starte 65-vms.sh"
  HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" \
    INSTALLER_DIR="$HH_REPO_DIR/installer" \
    bash "$HH_REPO_DIR/installer/modules/65-vms.sh"
fi

log "nginx-Config prüfen"
NGINX_CONF=/etc/nginx/sites-available/hydrahive2
if [ -f "$NGINX_CONF" ]; then
  NEEDS_REWRITE=0
  grep -q "ssl_certificate"      "$NGINX_CONF" || NEEDS_REWRITE=1
  grep -q "/vnc-ws/"             "$NGINX_CONF" || NEEDS_REWRITE=1
  grep -q "client_max_body_size 8G" "$NGINX_CONF" || NEEDS_REWRITE=1
  if [ "$NEEDS_REWRITE" = "1" ]; then
    log "nginx: Config braucht Update (HTTPS / VNC-Proxy / ISO-Upload-Limit) — neu schreiben"
    HH_HOST="${HH_HOST:-127.0.0.1}"
    HH_PORT="${HH_PORT:-8001}"
    HH_REPO_DIR="$HH_REPO_DIR" HH_HOST="$HH_HOST" HH_PORT="$HH_PORT" \
      bash "$HH_REPO_DIR/installer/modules/60-nginx.sh"
  fi
fi

log "Service neu starten"
systemctl restart hydrahive2.service

sleep 2
if systemctl is-active --quiet hydrahive2.service; then
  log "Update erfolgreich, Service läuft."
else
  log "Service-Neustart fehlgeschlagen — siehe: journalctl -u hydrahive2 -n 50"
  exit 1
fi
