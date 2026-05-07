#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }

info "Deinstalliere Ollama..."

systemctl stop ollama 2>/dev/null || true
systemctl disable ollama 2>/dev/null || true
rm -f /etc/systemd/system/ollama.service
systemctl daemon-reload

rm -f /usr/local/bin/ollama
userdel -r ollama 2>/dev/null || true

success "Ollama deinstalliert (Modelle unter /usr/share/ollama/.ollama bleiben erhalten)"
