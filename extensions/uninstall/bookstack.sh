#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere BookStack..."

systemctl stop    bookstack bookstack-queue 2>/dev/null || true
systemctl disable bookstack bookstack-queue 2>/dev/null || true
rm -f /etc/systemd/system/bookstack.service
rm -f /etc/systemd/system/bookstack-queue.service
systemctl daemon-reload

# Legacy PHP-FPM Pool entfernen
for phpv in 8.3 8.2 8.1 8.0; do
    POOL="/etc/php/${phpv}/fpm/pool.d/bookstack.conf"
    if [ -f "${POOL}" ]; then
        rm -f "${POOL}"
        systemctl restart "php${phpv}-fpm" 2>/dev/null || true
        break
    fi
done

warn "App-Verzeichnis /opt/bookstack wird entfernt (enthält Code, Uploads, Konfiguration)."
warn "Datenbank-Backup vorher empfohlen: mysqldump bookstack > ~/bookstack-backup.sql"
rm -rf /opt/bookstack
success "/opt/bookstack entfernt"

warn "BookStack-Datenbank 'bookstack' wird entfernt..."
mysql -e "DROP DATABASE IF EXISTS bookstack;" 2>/dev/null || true
mysql -e "DROP USER IF EXISTS 'bookstack'@'localhost';" 2>/dev/null || true
mysql -e "FLUSH PRIVILEGES;" 2>/dev/null || true
success "Datenbank entfernt"

rm -f /etc/hydrahive2/extensions/bookstack.credentials.json

userdel bookstack 2>/dev/null || true
groupdel bookstack 2>/dev/null || true

success "BookStack deinstalliert"
