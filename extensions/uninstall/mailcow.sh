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

info "Lösche Mailcow-Verzeichnis..."
rm -rf "${MAILCOW_DIR}"

rm -f /etc/hydrahive2/extensions/mailcow.credentials.json

success "Mailcow deinstalliert"
warn "Hinweis: Mail-Daten (Postfächer) wurden mit entfernt."
