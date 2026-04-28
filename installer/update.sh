#!/usr/bin/env bash
# HydraHive2 — Update auf den neuesten Stand der main-Branch.
set -euo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"

log() { printf "\033[1;36m[hh2-update]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[hh2-update]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Bitte mit sudo / als root ausführen."
[ -d "$HH_REPO_DIR/.git" ] || err "$HH_REPO_DIR ist kein Git-Repo."

cd "$HH_REPO_DIR"

log "git pull"
sudo -u hydrahive git pull --ff-only

log "Backend-Dependencies aktualisieren"
"$HH_REPO_DIR/.venv/bin/pip" install --quiet -e "$HH_REPO_DIR/core"

log "Frontend neu bauen"
cd "$HH_REPO_DIR/frontend"
sudo -u hydrahive npm install --silent
sudo -u hydrahive npm run build --silent

log "Service neu starten"
systemctl restart hydrahive2.service

sleep 2
if systemctl is-active --quiet hydrahive2.service; then
  log "Update erfolgreich, Service läuft."
else
  log "Service-Neustart fehlgeschlagen — siehe: journalctl -u hydrahive2 -n 50"
  exit 1
fi
