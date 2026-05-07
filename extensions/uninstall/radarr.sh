#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Radarr..."

systemctl stop    radarr 2>/dev/null || true
systemctl disable radarr 2>/dev/null || true
rm -f /etc/systemd/system/radarr.service
systemctl daemon-reload

warn "Installationsverzeichnis /opt/radarr wird entfernt."
rm -rf /opt/radarr
success "/opt/radarr entfernt"

warn "Radarr-Daten unter /var/lib/radarr wurden NICHT gelöscht."
warn "Manuell entfernen: sudo rm -rf /var/lib/radarr"

userdel radarr 2>/dev/null || true
groupdel radarr 2>/dev/null || true

success "Radarr deinstalliert"
