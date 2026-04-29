#!/usr/bin/env bash
# Installiert hydrahive2.service als systemd-Unit + startet ihn.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

SERVICE_FILE=/etc/systemd/system/hydrahive2.service
UPDATE_SERVICE=/etc/systemd/system/hydrahive2-update.service
UPDATE_PATH=/etc/systemd/system/hydrahive2-update.path
RESTART_SERVICE=/etc/systemd/system/hydrahive2-restart.service
RESTART_PATH=/etc/systemd/system/hydrahive2-restart.path

# JWT-Secret generieren falls nicht da
SECRET_FILE="$HH_CONFIG_DIR/secret_key"
if [ ! -f "$SECRET_FILE" ]; then
  log "Generiere JWT-Secret"
  python3 -c "import secrets; print(secrets.token_urlsafe(48))" > "$SECRET_FILE"
  chmod 600 "$SECRET_FILE"
  chown "$HH_USER:$HH_USER" "$SECRET_FILE"
fi
SECRET_KEY="$(cat "$SECRET_FILE")"

log "Schreibe $SERVICE_FILE"
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=HydraHive2 Backend
After=network.target

[Service]
Type=exec
User=$HH_USER
Group=$HH_USER
WorkingDirectory=$HH_REPO_DIR
Environment=HH_DATA_DIR=$HH_DATA_DIR
Environment=HH_CONFIG_DIR=$HH_CONFIG_DIR
Environment=HH_HOST=$HH_HOST
Environment=HH_PORT=$HH_PORT
Environment=HH_SECRET_KEY=$SECRET_KEY
Environment=PATH=$HH_REPO_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$HH_REPO_DIR/.venv/bin/uvicorn hydrahive.api.main:app --host $HH_HOST --port $HH_PORT
Restart=on-failure
RestartSec=5

# Sicherheit
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$HH_DATA_DIR $HH_CONFIG_DIR

[Install]
WantedBy=multi-user.target
EOF

log "Schreibe $UPDATE_SERVICE (Self-Update Runner)"
cat > "$UPDATE_SERVICE" <<EOF
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

log "Schreibe $UPDATE_PATH (Trigger-Watcher)"
cat > "$UPDATE_PATH" <<EOF
[Unit]
Description=HydraHive2 Update-Trigger Watcher

[Path]
PathExists=$HH_DATA_DIR/.update_request
Unit=hydrahive2-update.service

[Install]
WantedBy=multi-user.target
EOF

log "Schreibe $RESTART_SERVICE (Restart-Runner)"
cat > "$RESTART_SERVICE" <<EOF
[Unit]
Description=HydraHive2 Restart Runner
ConditionPathExists=$HH_DATA_DIR/.restart_request

[Service]
Type=oneshot
ExecStartPre=/bin/rm -f $HH_DATA_DIR/.restart_request
ExecStart=/bin/systemctl restart hydrahive2.service
EOF

log "Schreibe $RESTART_PATH (Trigger-Watcher)"
cat > "$RESTART_PATH" <<EOF
[Unit]
Description=HydraHive2 Restart-Trigger Watcher

[Path]
PathExists=$HH_DATA_DIR/.restart_request
Unit=hydrahive2-restart.service

[Install]
WantedBy=multi-user.target
EOF

# Log-File mit korrekten Permissions vorbereiten
touch /var/log/hydrahive2-update.log
chmod 644 /var/log/hydrahive2-update.log

log "systemd reload + enable"
systemctl daemon-reload
systemctl enable hydrahive2.service >/dev/null 2>&1
systemctl enable hydrahive2-update.path >/dev/null 2>&1
systemctl enable hydrahive2-restart.path >/dev/null 2>&1

log "Starte Service + Update-Watcher + Restart-Watcher"
systemctl restart hydrahive2.service
systemctl restart hydrahive2-update.path
systemctl restart hydrahive2-restart.path

sleep 2
if systemctl is-active --quiet hydrahive2.service; then
  log "Service läuft."
else
  log "Service-Start fehlgeschlagen — siehe: journalctl -u hydrahive2 -n 50"
  exit 1
fi
