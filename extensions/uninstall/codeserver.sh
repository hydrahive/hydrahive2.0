#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Code-Server..."

systemctl stop code-server 2>/dev/null || true
systemctl disable code-server 2>/dev/null || true
rm -f /etc/systemd/system/code-server.service
systemctl daemon-reload

if dpkg -l code-server &>/dev/null 2>&1; then
    apt-get remove -y --purge code-server 2>/dev/null || true
    success "Paket 'code-server' entfernt"
fi

rm -f /etc/hydrahive2/extensions/codeserver.credentials.json

warn "Konfiguration unter /home/hydrahive/.config/code-server wurde NICHT gelöscht."
warn "Manuell entfernen: sudo rm -rf /home/hydrahive/.config/code-server"

success "Code-Server deinstalliert"
