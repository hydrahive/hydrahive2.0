#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

SHADOWBROKER_DATA="/var/lib/hydrahive2/extensions/shadowbroker"

info "Deinstalliere ShadowBroker..."

# --- Credentials entfernen ---
rm -f /etc/hydrahive2/extensions/shadowbroker.credentials.json
success "Credentials entfernt"

# --- Datenpfad entfernen ---
if [ -d "${SHADOWBROKER_DATA}" ]; then
    rm -rf "${SHADOWBROKER_DATA}"
    success "Datenpfad ${SHADOWBROKER_DATA} entfernt"
else
    warn "Datenpfad nicht gefunden — überspringe"
fi

success "ShadowBroker deinstalliert"
