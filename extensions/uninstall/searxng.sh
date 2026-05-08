#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }

info "Deinstalliere SearXNG..."

systemctl stop searxng 2>/dev/null || true
systemctl disable searxng 2>/dev/null || true
rm -f /etc/systemd/system/searxng.service
systemctl daemon-reload

rm -rf /opt/searxng
userdel searxng 2>/dev/null || true
groupdel searxng 2>/dev/null || true

rm -f /etc/hydrahive2/extensions/searxng.credentials.json

success "SearXNG deinstalliert"
