#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Monica CRM..."

systemctl stop    monica 2>/dev/null || true
systemctl disable monica 2>/dev/null || true
rm -f /etc/systemd/system/monica.service
systemctl daemon-reload

CRED="/etc/hydrahive2/extensions/monica-crm.credentials.json"
if [ -f "${CRED}" ]; then
    DB_NAME=$(python3 -c "import json; d=json.load(open('${CRED}')); print('monica')" 2>/dev/null || echo "monica")
    mysql -e "DROP DATABASE IF EXISTS ${DB_NAME};" 2>/dev/null || true
    mysql -e "DROP USER IF EXISTS 'monica'@'localhost';" 2>/dev/null || true
    success "Datenbank 'monica' gelöscht"
fi

rm -rf /opt/monica
rm -f "${CRED}"

userdel -r monica 2>/dev/null || true

success "Monica CRM deinstalliert"
