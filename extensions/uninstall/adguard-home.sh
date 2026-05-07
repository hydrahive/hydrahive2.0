#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere AdGuard Home..."

systemctl stop    adguardhome 2>/dev/null || true
systemctl disable adguardhome 2>/dev/null || true
rm -f /etc/systemd/system/adguardhome.service

# IP-Alias Service entfernen falls vorhanden
if systemctl is-enabled adguard-dns-alias.service &>/dev/null 2>&1; then
    systemctl stop    adguard-dns-alias.service 2>/dev/null || true
    systemctl disable adguard-dns-alias.service 2>/dev/null || true
fi
rm -f /etc/systemd/system/adguard-dns-alias.service

systemctl daemon-reload

rm -rf /opt/adguard-home

rm -f /etc/hydrahive2/extensions/adguard-home.credentials.json

userdel adguardhome 2>/dev/null || true

warn "Daten in /var/lib/adguard-home wurden NICHT gelöscht (Query-Logs, Blocklists, Statistiken)."
warn "Manuell löschen: sudo rm -rf /var/lib/adguard-home"

success "AdGuard Home deinstalliert"
