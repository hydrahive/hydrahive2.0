#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Sonarr..."

systemctl stop    sonarr 2>/dev/null || true
systemctl disable sonarr 2>/dev/null || true
rm -f /etc/systemd/system/sonarr.service
systemctl daemon-reload

warn "Installationsverzeichnis /opt/sonarr wird entfernt."
rm -rf /opt/sonarr
success "/opt/sonarr entfernt"

warn "Sonarr-Daten unter /var/lib/sonarr wurden NICHT gelöscht."
warn "Manuell entfernen: sudo rm -rf /var/lib/sonarr"

userdel sonarr 2>/dev/null || true
groupdel sonarr 2>/dev/null || true

success "Sonarr deinstalliert"
