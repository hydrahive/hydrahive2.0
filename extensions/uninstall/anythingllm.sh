#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

ANYTHINGLLM_DATA="/var/lib/hydrahive2/extensions/anythingllm"

info "Deinstalliere AnythingLLM..."

# --- Credentials + Secrets entfernen ---
rm -f /etc/hydrahive2/extensions/anythingllm.credentials.json
rm -f /etc/hydrahive2/extensions/anythingllm.env
success "Credentials und Secrets entfernt"

# --- Storage entfernen ---
if [ -d "${ANYTHINGLLM_DATA}" ]; then
    rm -rf "${ANYTHINGLLM_DATA}"
    success "Storage ${ANYTHINGLLM_DATA} entfernt"
else
    warn "Storage nicht gefunden — überspringe"
fi

success "AnythingLLM deinstalliert"
