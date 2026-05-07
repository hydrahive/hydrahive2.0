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

# macvlan-Netzwerk entfernen (nur wenn keine anderen Container es nutzen)
if docker network inspect mailcow-macvlan &>/dev/null 2>&1; then
    docker network rm mailcow-macvlan 2>/dev/null || \
        warn "macvlan-Netzwerk konnte nicht entfernt werden (noch in Verwendung?)"
fi

info "Lösche Mailcow-Verzeichnis..."
rm -rf "${MAILCOW_DIR}"

rm -f /etc/hydrahive2/extensions/mailcow.credentials.json
rm -f /etc/hydrahive2/extensions/mailcow.url

success "Mailcow deinstalliert"
warn "Hinweis: Mail-Daten (Postfächer) wurden mit entfernt."
