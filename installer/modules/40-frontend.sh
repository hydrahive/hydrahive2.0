#!/usr/bin/env bash
# Frontend bauen — produziert frontend/dist/.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

cd "$HH_REPO_DIR/frontend"

log "npm install (kann ein paar Minuten dauern)"
npm install --silent

log "npm run build → dist/"
npm run build --silent

log "Frontend gebaut: $HH_REPO_DIR/frontend/dist/"

# Vite produziert dist/ — wird später vom nginx oder vom Backend ausgeliefert
chown -R "$HH_USER:$HH_USER" "$HH_REPO_DIR/frontend/dist"
