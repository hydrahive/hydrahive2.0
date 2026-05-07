#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

MAILCOW_DIR="/opt/mailcow-dockerized"

if [ ! -d "${MAILCOW_DIR}" ]; then
    info "Mailcow-Verzeichnis nicht gefunden — nichts zu tun"
    exit 0
fi

warn "Fahre Mailcow-Stack herunter..."
cd "${MAILCOW_DIR}"
docker compose down --volumes 2>/dev/null || true

# nginx-Proxy-Config entfernen
rm -f /etc/nginx/sites-enabled/mailcow
rm -f /etc/nginx/sites-available/mailcow
nginx -t && systemctl reload nginx 2>/dev/null || true

# IP-Alias-Service entfernen
if systemctl is-enabled mailcow-ip.service &>/dev/null 2>&1; then
    systemctl stop mailcow-ip.service 2>/dev/null || true
    systemctl disable mailcow-ip.service 2>/dev/null || true
fi
rm -f /etc/systemd/system/mailcow-ip.service
systemctl daemon-reload 2>/dev/null || true

info "Lösche Mailcow-Verzeichnis..."
rm -rf "${MAILCOW_DIR}"

rm -f /etc/hydrahive2/extensions/mailcow.credentials.json
rm -f /etc/hydrahive2/extensions/mailcow.url

success "Mailcow deinstalliert"
warn "Hinweis: Mail-Daten (Postfächer) wurden mit entfernt."
