#!/usr/bin/env bash
set -euo pipefail
log() { printf "  · %s\n" "$*"; }
# shellcheck source=../lib/mac-roles.sh
source "$(dirname "$0")/../lib/mac-roles.sh"

# npm als Dienst-Konto (gehört dem Repo); beim alten Weg (Dienst-Nutzer = Mac-Besitzer) direkt.
cd "$HH_REPO_DIR/frontend"
log "npm install"
as_svc npm install --silent
log "npm run build"
as_svc npm run build --silent
priv chown -R "$HH_USER" "$HH_REPO_DIR/frontend/dist"
log "Frontend gebaut."
