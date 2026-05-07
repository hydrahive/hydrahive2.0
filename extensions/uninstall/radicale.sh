#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Radicale..."

systemctl stop    radicale 2>/dev/null || true
systemctl disable radicale 2>/dev/null || true
rm -f /etc/systemd/system/radicale.service
systemctl daemon-reload

rm -rf /etc/radicale
rm -rf /var/log/radicale
rm -f /usr/bin/radicale

if [ -d /opt/radicale ]; then
    warn "virtualenv /opt/radicale wird entfernt."
    rm -rf /opt/radicale
    success "virtualenv entfernt"
fi

if dpkg -l radicale &>/dev/null 2>&1; then
    apt-get remove -y --quiet radicale 2>/dev/null || true
    success "radicale apt-Paket entfernt"
fi

rm -f /etc/hydrahive2/extensions/radicale.credentials.json

userdel radicale 2>/dev/null || true
groupdel radicale 2>/dev/null || true

warn "Kalender- und Kontaktdaten in /var/lib/radicale wurden NICHT gelöscht."
warn "Manuell entfernen: sudo rm -rf /var/lib/radicale"

success "Radicale deinstalliert"
