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

# HydraHive-nginx zurück auf 0.0.0.0
NGINX_CONF="/etc/nginx/sites-available/hydrahive2"
if [ -f "${NGINX_CONF}" ]; then
    sed -i "s|listen [0-9.]*:80 default_server;|listen 80 default_server;|g" "${NGINX_CONF}"
    sed -i "s|    listen 127.0.0.1:80;||g" "${NGINX_CONF}"
    sed -i "s|# listen \[::\]:80.*|listen [::]:80 default_server;|g" "${NGINX_CONF}"
    sed -i "s|listen [0-9.]*:443 ssl default_server;|listen 443 ssl default_server;|g" "${NGINX_CONF}"
    sed -i "s|    listen 127.0.0.1:443 ssl;||g" "${NGINX_CONF}"
    sed -i "s|# listen \[::\]:443.*|listen [::]:443 ssl default_server;|g" "${NGINX_CONF}"
    nginx -t && systemctl reload nginx 2>/dev/null || true
fi

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
