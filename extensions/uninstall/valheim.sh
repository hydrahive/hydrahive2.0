#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Valheim Server..."

systemctl stop    valheim 2>/dev/null || true
systemctl disable valheim 2>/dev/null || true
rm -f /etc/systemd/system/valheim.service
systemctl daemon-reload
success "systemd Service entfernt"

warn "Valheim-Verzeichnis /opt/valheim wird entfernt (inkl. Spielwelt-Daten)."
warn "Backup vorher: sudo cp -r /opt/valheim/.config ~/valheim-backup"
rm -rf /opt/valheim
success "/opt/valheim entfernt"

userdel -r valheim 2>/dev/null || true
success "User valheim entfernt"

rm -f /etc/hydrahive2/extensions/valheim.credentials.json

if command -v ufw &>/dev/null; then
    ufw delete allow 2456:2458/udp 2>/dev/null || true
fi

success "Valheim Server deinstalliert"
