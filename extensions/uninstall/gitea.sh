#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }

info "Deinstalliere Gitea..."

systemctl stop gitea 2>/dev/null || true
systemctl disable gitea 2>/dev/null || true
rm -f /etc/systemd/system/gitea.service
systemctl daemon-reload

rm -f /usr/local/bin/gitea
rm -rf /opt/gitea /etc/gitea /etc/hydrahive2/gitea_config.json
userdel -r git 2>/dev/null || true

rm -f /etc/nginx/sites-enabled/gitea /etc/nginx/sites-available/gitea
command -v nginx &>/dev/null && nginx -t && systemctl reload nginx || true

success "Gitea deinstalliert"
