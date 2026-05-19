#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

# Ziel-Major-Version — NodeSource LTS
NODE_MAJOR="22"

# Schon installiert?
if command -v node &>/dev/null; then
    INSTALLED="$(node --version 2>/dev/null || echo "")"
    INSTALLED_MAJOR="$(echo "${INSTALLED}" | grep -oP '\d+' | head -1 || echo "0")"
    if [ "${INSTALLED_MAJOR}" -ge "${NODE_MAJOR}" ]; then
        success "Node.js ${INSTALLED} bereits installiert"
        exit 0
    fi
    info "Update von ${INSTALLED} auf v${NODE_MAJOR} LTS..."
fi

info "Füge NodeSource-Repository für Node.js ${NODE_MAJOR} LTS hinzu..."
apt-get install -y curl gnupg 2>/dev/null || true

# NodeSource-Setup-Script (fügt apt-Repository hinzu und installiert)
curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash -

info "Installiere Node.js ${NODE_MAJOR}..."
apt-get install -y nodejs

# corepack und pnpm als Bonus
corepack enable 2>/dev/null || true

success "Node.js $(node --version) + npm $(npm --version) installiert"
