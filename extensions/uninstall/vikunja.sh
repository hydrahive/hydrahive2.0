#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Vikunja..."

systemctl stop    vikunja 2>/dev/null || true
systemctl disable vikunja 2>/dev/null || true
rm -f /etc/systemd/system/vikunja.service
systemctl daemon-reload

warn "Installationsverzeichnis /opt/vikunja wird entfernt."
rm -rf /opt/vikunja
success "/opt/vikunja entfernt"

rm -rf /etc/vikunja

rm -f /etc/hydrahive2/extensions/vikunja.credentials.json

userdel vikunja 2>/dev/null || true
groupdel vikunja 2>/dev/null || true

warn "Aufgaben und Daten in /var/lib/vikunja wurden NICHT gelöscht."
warn "Manuell entfernen: sudo rm -rf /var/lib/vikunja"

success "Vikunja deinstalliert"
