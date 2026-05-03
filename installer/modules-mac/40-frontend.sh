#!/usr/bin/env bash
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

cd "$HH_REPO_DIR/frontend"
log "npm install"
npm install --silent
log "npm run build"
npm run build --silent
chown -R "$HH_USER" "$HH_REPO_DIR/frontend/dist"
log "Frontend gebaut."
