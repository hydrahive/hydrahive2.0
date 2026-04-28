#!/usr/bin/env bash
# Installiert hydrahive2.service als systemd-Unit + startet ihn.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

SERVICE_FILE=/etc/systemd/system/hydrahive2.service

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

log "systemd reload + enable"
systemctl daemon-reload
systemctl enable hydrahive2.service >/dev/null 2>&1

log "Starte Service"
systemctl restart hydrahive2.service

sleep 2
if systemctl is-active --quiet hydrahive2.service; then
  log "Service läuft."
else
  log "Service-Start fehlgeschlagen — siehe: journalctl -u hydrahive2 -n 50"
  exit 1
fi
