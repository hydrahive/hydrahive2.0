#!/usr/bin/env bash
# WhatsApp-Bridge: npm-Module installieren falls package.json vorhanden.
# Idempotent. Wenn die Bridge nicht existiert wird übersprungen.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

BRIDGE_DIR="$HH_REPO_DIR/core/src/hydrahive/communication/whatsapp/bridge"

if [ ! -f "$BRIDGE_DIR/package.json" ]; then
  log "Keine WhatsApp-Bridge im Repo (übersprungen)"
  exit 0
fi

cd "$BRIDGE_DIR"

log "WhatsApp-Bridge: npm install"
sudo -u "$HH_USER" npm install --silent --no-audit --no-fund

log "WhatsApp-Bridge bereit ($BRIDGE_DIR)"
