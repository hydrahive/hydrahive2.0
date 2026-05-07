#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Plex Media Server..."

systemctl stop    plexmediaserver 2>/dev/null || true
systemctl disable plexmediaserver 2>/dev/null || true

if dpkg -l plexmediaserver &>/dev/null 2>&1; then
    apt-get remove -y --purge plexmediaserver 2>/dev/null || true
    success "Paket 'plexmediaserver' entfernt"
fi

rm -f /etc/apt/sources.list.d/plexmediaserver.list
rm -f /etc/apt/trusted.gpg.d/plexmediaserver.asc
apt-get update -qq 2>/dev/null || true
success "Plex apt-Repository entfernt"

warn "Plex-Daten unter /var/lib/plexmediaserver wurden NICHT gelöscht."
warn "Manuell entfernen: sudo rm -rf /var/lib/plexmediaserver"

userdel plex 2>/dev/null || true
groupdel plex 2>/dev/null || true

success "Plex Media Server deinstalliert"
