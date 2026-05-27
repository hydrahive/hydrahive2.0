#!/usr/bin/env bash
# HydraHive2 — Einmalige Recovery nach History-Rewrite auf GitHub.
# Ausführen mit: sudo bash /opt/hydrahive2/installer/recover.sh
set -euo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"

log() { printf "\033[1;36m[hh2-recover]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[hh2-recover]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Bitte mit sudo / als root ausführen."
[ -d "$HH_REPO_DIR/.git" ] || err "$HH_REPO_DIR ist kein Git-Repo."

cd "$HH_REPO_DIR"

log "Fetch von GitHub..."
sudo -u hydrahive git -c safe.directory="$HH_REPO_DIR" fetch origin

log "Reset auf origin/main (History-Rewrite-Recovery)..."
sudo -u hydrahive git -c safe.directory="$HH_REPO_DIR" reset --hard origin/main

log "Recovery abgeschlossen — starte Update..."
exec bash "$HH_REPO_DIR/installer/update.sh" "$@"
