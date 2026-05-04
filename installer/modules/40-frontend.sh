#!/usr/bin/env bash
# Frontend bauen — produziert frontend/dist/.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

cd "$HH_REPO_DIR/frontend"

log "npm install (kann ein paar Minuten dauern)"
npm install --no-fund --no-audit

log "npm run build → dist/"
npm run build

log "Frontend gebaut: $HH_REPO_DIR/frontend/dist/"

# Vite produziert dist/ — wird später vom nginx oder vom Backend ausgeliefert
# Komplett chownen: node_modules + dist + Source-Files. Sonst bleibt
# node_modules root-owned und ein späteres `sudo -u hydrahive npm install`
# (Update-Flow) scheitert mit EACCES.
chown -R "$HH_USER:$HH_USER" "$HH_REPO_DIR/frontend"
