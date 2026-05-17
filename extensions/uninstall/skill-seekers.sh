#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

STORAGE="/var/lib/hydrahive2/extensions/skill-seekers"

info "Deinstalliere Skill Seekers..."

rm -f /etc/hydrahive2/extensions/skill-seekers.credentials.json
rm -f /etc/hydrahive2/extensions/skill-seekers.env
success "Credentials und Konfiguration entfernt"

if [ -d "${STORAGE}" ]; then
    rm -rf "${STORAGE}"
    success "Storage ${STORAGE} entfernt"
else
    warn "Storage nicht gefunden — überspringe"
fi

success "Skill Seekers deinstalliert"
