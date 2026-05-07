#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere SABnzbd..."

for svc in sabnzbd sabnzbdplus; do
    systemctl stop    "${svc}" 2>/dev/null || true
    systemctl disable "${svc}" 2>/dev/null || true
done
rm -f /etc/systemd/system/sabnzbd.service
systemctl daemon-reload

if dpkg -l sabnzbdplus &>/dev/null 2>&1; then
    apt-get remove -y --purge sabnzbdplus 2>/dev/null || true
    success "Paket 'sabnzbdplus' entfernt"
fi

rm -f /etc/default/sabnzbdplus

warn "SABnzbd-Daten unter /var/lib/sabnzbd wurden NICHT gelöscht."
warn "Manuell entfernen: sudo rm -rf /var/lib/sabnzbd"

userdel sabnzbd 2>/dev/null || true
groupdel sabnzbd 2>/dev/null || true

success "SABnzbd deinstalliert"
