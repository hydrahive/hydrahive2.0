#!/usr/bin/env bash
# HydraHive2 — Self-Update für macOS (launchd-Variante).
# Wird von io.hydrahive.update LaunchDaemon aufgerufen wenn
# $HH_DATA_DIR/.update_request erscheint.
set -euo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
HH_USER="${HH_USER:-admin}"
BACKEND_PLIST="/Library/LaunchDaemons/io.hydrahive.backend.plist"
LOG="/usr/local/var/log/hydrahive2-update.log"

log() { printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG"; }

rm -f "$HH_DATA_DIR/.update_request"
log "Update gestartet"

eval "$(/usr/local/bin/brew shellenv zsh 2>/dev/null || /opt/homebrew/bin/brew shellenv zsh 2>/dev/null || true)"

cd "$HH_REPO_DIR"
sudo -u "$HH_USER" git pull --ff-only 2>&1 | tee -a "$LOG" || { log "git pull fehlgeschlagen"; exit 1; }

# Python-Dependencies aktualisieren
sudo -u "$HH_USER" "$HH_REPO_DIR/.venv/bin/pip" install --quiet -e "$HH_REPO_DIR/core"

# Frontend neu bauen falls sich was geändert hat
if git diff --name-only HEAD@{1} HEAD 2>/dev/null | grep -q "^frontend/"; then
  log "Frontend-Änderungen erkannt — rebuild"
  cd "$HH_REPO_DIR/frontend"
  sudo -u "$HH_USER" npm install --silent
  sudo -u "$HH_USER" npm run build --silent
fi

log "Service neu starten"
launchctl unload "$BACKEND_PLIST" 2>/dev/null || true
sleep 1
launchctl load "$BACKEND_PLIST"

log "Update abgeschlossen"
