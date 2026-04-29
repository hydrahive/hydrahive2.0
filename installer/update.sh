#!/usr/bin/env bash
# HydraHive2 — Update auf den neuesten Stand der main-Branch.
set -euo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"

log() { printf "\033[1;36m[hh2-update]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[hh2-update]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Bitte mit sudo / als root ausführen."
[ -d "$HH_REPO_DIR/.git" ] || err "$HH_REPO_DIR ist kein Git-Repo."

cd "$HH_REPO_DIR"

log "git pull"
sudo -u hydrahive git pull --ff-only

log "Backend-Dependencies aktualisieren"
"$HH_REPO_DIR/.venv/bin/pip" install --quiet -e "$HH_REPO_DIR/core"

log "Frontend neu bauen"
cd "$HH_REPO_DIR/frontend"
sudo -u hydrahive npm install --silent
sudo -u hydrahive npm run build --silent

log "Systemd-Units prüfen"
HH_DATA_DIR="${HH_DATA_DIR:-/var/lib/hydrahive2}"
if [ ! -f /etc/systemd/system/hydrahive2-update.path ] || [ ! -f /etc/systemd/system/hydrahive2-update.service ]; then
  log "Self-Update-Units fehlen — werden angelegt"
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
  cat > /etc/systemd/system/hydrahive2-update.path <<EOF
[Unit]
Description=HydraHive2 Update-Trigger Watcher

[Path]
PathExists=$HH_DATA_DIR/.update_request
Unit=hydrahive2-update.service

[Install]
WantedBy=multi-user.target
EOF
  touch /var/log/hydrahive2-update.log
  chmod 644 /var/log/hydrahive2-update.log
  systemctl daemon-reload
  systemctl enable hydrahive2-update.path >/dev/null 2>&1
  systemctl restart hydrahive2-update.path
fi

if [ ! -f /etc/systemd/system/hydrahive2-restart.path ] || [ ! -f /etc/systemd/system/hydrahive2-restart.service ]; then
  log "Restart-Trigger-Units fehlen — werden angelegt"
  cat > /etc/systemd/system/hydrahive2-restart.service <<EOF
[Unit]
Description=HydraHive2 Restart Runner
ConditionPathExists=$HH_DATA_DIR/.restart_request

[Service]
Type=oneshot
ExecStartPre=/bin/rm -f $HH_DATA_DIR/.restart_request
ExecStart=/bin/systemctl restart hydrahive2.service
EOF
  cat > /etc/systemd/system/hydrahive2-restart.path <<EOF
[Unit]
Description=HydraHive2 Restart-Trigger Watcher

[Path]
PathExists=$HH_DATA_DIR/.restart_request
Unit=hydrahive2-restart.service

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable hydrahive2-restart.path >/dev/null 2>&1
  systemctl restart hydrahive2-restart.path
fi

log "nginx Security-Headers prüfen"
NGINX_CONF=/etc/nginx/sites-available/hydrahive2
if [ -f "$NGINX_CONF" ] && ! grep -q "X-Frame-Options" "$NGINX_CONF"; then
  log "Security-Headers fehlen — nginx-Config neu schreiben"
  HH_HOST="${HH_HOST:-127.0.0.1}"
  HH_PORT="${HH_PORT:-8001}"
  HH_REPO_DIR="$HH_REPO_DIR" HH_HOST="$HH_HOST" HH_PORT="$HH_PORT" \
    bash "$HH_REPO_DIR/installer/modules/60-nginx.sh"
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
