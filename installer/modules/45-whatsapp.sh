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
npm install --cache /tmp/npm-cache-hh --no-audit --no-fund --silent
chown -R "$HH_USER:$HH_USER" node_modules

log "WhatsApp-Bridge bereit ($BRIDGE_DIR)"
