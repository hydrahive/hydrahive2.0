#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

info "Deinstalliere Node.js..."

apt-get remove -y --purge nodejs 2>/dev/null || true
apt-get autoremove -y 2>/dev/null || true
rm -f /etc/apt/sources.list.d/nodesource.list
rm -f /etc/apt/keyrings/nodesource.gpg

warn "Globale npm-Packages und node_modules-Ordner wurden nicht gelöscht."
success "Node.js deinstalliert"
