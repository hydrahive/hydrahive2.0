#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Heimdall..."

systemctl stop    heimdall 2>/dev/null || true
systemctl disable heimdall 2>/dev/null || true
rm -f /etc/systemd/system/heimdall.service
systemctl daemon-reload

rm -f /etc/nginx/sites-enabled/heimdall
rm -f /etc/nginx/sites-available/heimdall
nginx -t &>/dev/null && systemctl reload nginx 2>/dev/null || true

for phpv in 8.3 8.2 8.1 8.0; do
    POOL="/etc/php/${phpv}/fpm/pool.d/heimdall.conf"
    if [ -f "${POOL}" ]; then
        rm -f "${POOL}"
        systemctl restart "php${phpv}-fpm" 2>/dev/null || true
        break
    fi
done

warn "App-Verzeichnis /opt/heimdall wird entfernt (inkl. SQLite-Datenbank mit Dashboard-Konfiguration)."
warn "Backup vorher: sudo cp /opt/heimdall/database/app.sqlite ~/heimdall-backup.sqlite"
rm -rf /opt/heimdall

userdel heimdall 2>/dev/null || true
groupdel heimdall 2>/dev/null || true

success "Heimdall deinstalliert"
