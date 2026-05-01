#!/usr/bin/env bash
# Installiert hydrahive2.service als systemd-Unit + startet ihn.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

SERVICE_FILE=/etc/systemd/system/hydrahive2.service
UPDATE_SERVICE=/etc/systemd/system/hydrahive2-update.service
UPDATE_TIMER=/etc/systemd/system/hydrahive2-update.timer
RESTART_SERVICE=/etc/systemd/system/hydrahive2-restart.service
RESTART_TIMER=/etc/systemd/system/hydrahive2-restart.timer
VOICE_SERVICE=/etc/systemd/system/hydrahive2-voice.service
VOICE_TIMER=/etc/systemd/system/hydrahive2-voice.timer
BRIDGE_SERVICE=/etc/systemd/system/hydrahive2-bridge.service
BRIDGE_TIMER=/etc/systemd/system/hydrahive2-bridge.timer
SAMBA_SERVICE=/etc/systemd/system/hydrahive2-samba.service
SAMBA_TIMER=/etc/systemd/system/hydrahive2-samba.timer

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
Environment=HOME=/home/$HH_USER
Environment=PATH=$HH_REPO_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$HH_REPO_DIR/.venv/bin/uvicorn hydrahive.api.main:app --host $HH_HOST --port $HH_PORT
Restart=on-failure
RestartSec=5

# Sicherheit — HOME-Dir braucht Read-Access (incus config.yml), Write nur via ReadWritePaths
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$HH_DATA_DIR $HH_CONFIG_DIR /home/$HH_USER/.config /home/$HH_USER/.mmx

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

log "Schreibe $UPDATE_TIMER (Trigger-Poller)"
cat > "$UPDATE_TIMER" <<EOF
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

log "Schreibe $RESTART_TIMER (Trigger-Poller)"
cat > "$RESTART_TIMER" <<EOF
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

log "Schreibe $VOICE_SERVICE (Voice-Install Runner)"
cat > "$VOICE_SERVICE" <<EOF
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

log "Schreibe $VOICE_TIMER (Voice-Install Trigger-Poller)"
cat > "$VOICE_TIMER" <<EOF
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

log "Schreibe $BRIDGE_SERVICE (Bridge-Setup Runner)"
cat > "$BRIDGE_SERVICE" <<EOF
[Unit]
Description=HydraHive2 Bridge-Setup Runner
ConditionPathExists=$HH_DATA_DIR/.bridge_setup_request

[Service]
Type=oneshot
ExecStartPre=/bin/rm -f $HH_DATA_DIR/.bridge_setup_request
ExecStart=$HH_REPO_DIR/installer/setup-bridge.sh
StandardOutput=append:/var/log/hydrahive2-bridge.log
StandardError=append:/var/log/hydrahive2-bridge.log
EOF

log "Schreibe $SAMBA_SERVICE (Samba-Setup Runner)"
cat > "$SAMBA_SERVICE" <<EOF
[Unit]
Description=HydraHive2 Samba-Setup Runner
ConditionPathExists=$HH_DATA_DIR/.samba_setup_request

[Service]
Type=oneshot
ExecStartPre=/bin/rm -f $HH_DATA_DIR/.samba_setup_request
Environment=HH_USER=$HH_USER
Environment=HH_DATA_DIR=$HH_DATA_DIR
Environment=HH_CONFIG_DIR=$HH_CONFIG_DIR
ExecStart=$HH_REPO_DIR/installer/modules/47-samba.sh
StandardOutput=append:/var/log/hydrahive2-samba.log
StandardError=append:/var/log/hydrahive2-samba.log
EOF

log "Schreibe $SAMBA_TIMER (Samba-Setup Trigger-Poller)"
cat > "$SAMBA_TIMER" <<EOF
[Unit]
Description=HydraHive2 Samba-Setup Trigger Poller

[Timer]
OnBootSec=60s
OnUnitActiveSec=5s
AccuracySec=1s
Unit=hydrahive2-samba.service

[Install]
WantedBy=timers.target
EOF

log "Schreibe $BRIDGE_TIMER (Bridge-Setup Trigger-Poller)"
cat > "$BRIDGE_TIMER" <<EOF
[Unit]
Description=HydraHive2 Bridge-Setup Trigger Poller

[Timer]
OnBootSec=60s
OnUnitActiveSec=5s
AccuracySec=1s
Unit=hydrahive2-bridge.service

[Install]
WantedBy=timers.target
EOF

# Alte Path-Units entfernen falls vorhanden
rm -f /etc/systemd/system/hydrahive2-update.path
rm -f /etc/systemd/system/hydrahive2-restart.path

# Log-Files mit korrekten Permissions vorbereiten
touch /var/log/hydrahive2-update.log
chmod 644 /var/log/hydrahive2-update.log
touch /var/log/hydrahive2-voice.log
chmod 644 /var/log/hydrahive2-voice.log
touch /var/log/hydrahive2-bridge.log
chmod 644 /var/log/hydrahive2-bridge.log
touch /var/log/hydrahive2-samba.log
chmod 644 /var/log/hydrahive2-samba.log

log "systemd reload + enable"
systemctl daemon-reload
systemctl enable hydrahive2.service >/dev/null 2>&1
systemctl enable hydrahive2-update.timer >/dev/null 2>&1
systemctl enable hydrahive2-restart.timer >/dev/null 2>&1
systemctl enable hydrahive2-voice.timer >/dev/null 2>&1
systemctl enable hydrahive2-bridge.timer >/dev/null 2>&1
systemctl enable hydrahive2-samba.timer >/dev/null 2>&1

log "Starte Service + Update-/Restart-/Voice-/Bridge-/Samba-Timer"
systemctl restart hydrahive2.service
systemctl restart hydrahive2-update.timer
systemctl restart hydrahive2-restart.timer
systemctl restart hydrahive2-voice.timer
systemctl restart hydrahive2-bridge.timer
systemctl restart hydrahive2-samba.timer

sleep 2
if systemctl is-active --quiet hydrahive2.service; then
  log "Service läuft."
else
  log "Service-Start fehlgeschlagen — siehe: journalctl -u hydrahive2 -n 50"
  exit 1
fi
