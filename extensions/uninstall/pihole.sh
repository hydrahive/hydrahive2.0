#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Pi-hole..."

if [ -f /usr/local/bin/pihole ]; then
    pihole uninstall --yes 2>/dev/null || true
    success "Pi-hole deinstalliert"
fi

systemctl stop pihole-FTL lighttpd 2>/dev/null || true
systemctl disable pihole-FTL lighttpd 2>/dev/null || true

# systemd-resolved wiederherstellen
if ! systemctl is-enabled systemd-resolved &>/dev/null; then
    systemctl enable --now systemd-resolved 2>/dev/null || true
    ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf 2>/dev/null || true
    success "systemd-resolved wiederhergestellt"
fi

rm -f /etc/hydrahive2/extensions/pihole.credentials.json

warn "Pi-hole Daten unter /etc/pihole wurden NICHT gelöscht."
warn "Manuell entfernen: sudo rm -rf /etc/pihole"

success "Pi-hole deinstalliert"
