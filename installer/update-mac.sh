#!/usr/bin/env bash
# HydraHive2 — Self-Update für macOS (launchd-Variante).
# Wird von io.hydrahive.update LaunchDaemon aufgerufen wenn
# $HH_DATA_DIR/.update_request erscheint.
set -euo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
# Dienstnutzer = Besitzer des Repos (der Installer legt es als dieser Nutzer an).
# Früher fest „admin“ – beim Update von Hand liefen git/pip dann unter dem falschen Nutzer.
HH_USER="${HH_USER:-$(ls -ld "$HH_REPO_DIR" 2>/dev/null | awk '{print $3}')}"
HH_USER="${HH_USER:-admin}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
BACKEND_PLIST="${HH_BACKEND_PLIST:-/Library/LaunchDaemons/io.hydrahive.backend.plist}"
LOG="${HH_UPDATE_LOG:-/usr/local/var/log/hydrahive2-update.log}"

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

# PostgreSQL lief früher als brew-services-LaunchAgent (startet erst nach der Anmeldung).
# Einmalig auf den LaunchDaemon umstellen – nur wenn HydraHive die Datenbank nutzt.
PG_PLIST="${HH_PG_PLIST:-/Library/LaunchDaemons/io.hydrahive.postgres.plist}"
if [ -s "$HH_CONFIG_DIR/pg_mirror.dsn" ] && [ ! -f "$PG_PLIST" ]; then
  log "PostgreSQL auf LaunchDaemon umstellen (Start ohne Anmeldung)"
  HH_USER="$HH_USER" HH_PG_PLIST="$PG_PLIST" bash "$HH_REPO_DIR/installer/lib/mac-postgres-daemon.sh" 2>&1 | tee -a "$LOG" \
    || log "PostgreSQL-Umstellung fehlgeschlagen – Datamining evtl. erst nach Anmeldung (Log oben)"
fi

# Alte plists enthalten HH_SECRET_KEY + PG-DSN im Klartext (0644, für alle
# lesbar). Dann neu schreiben lassen: 50-launchd.sh übernimmt den BESTEHENDEN
# Schlüssel aus secret_key, startet über mac-backend-start.sh und lädt neu.
# Das Skript kommt frisch aus dem git pull oben.
# Ohne Zeitlimit beim Herunterfahren hängt uvicorn an offenen SSE-Verbindungen (Task 06d38ae9).
if grep -q "HH_SECRET_KEY\|HH_PG_MIRROR_DSN" "$BACKEND_PLIST" 2>/dev/null \
   || ! grep -q "mac-backend-start.sh" "$BACKEND_PLIST" 2>/dev/null \
   || ! grep -q -- "--timeout-graceful-shutdown" "$BACKEND_PLIST" 2>/dev/null; then
  log "launchd-plist enthält Secrets, keinen Start-Wrapper oder kein Zeitlimit — neu schreiben"
  HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" HH_CONFIG_DIR="$HH_CONFIG_DIR" \
    HH_REPO_DIR="$HH_REPO_DIR" HH_HOST="${HH_HOST:-127.0.0.1}" HH_PORT="${HH_PORT:-8001}" \
    HH_BACKEND_PLIST="$BACKEND_PLIST" \
    bash "$HH_REPO_DIR/installer/modules-mac/50-launchd.sh" 2>&1 | tee -a "$LOG" \
    || { log "plist-Umbau fehlgeschlagen — Fehler im Log"; exit 1; }
  log "Update abgeschlossen"
  exit 0
fi

log "Service neu starten"
launchctl unload "$BACKEND_PLIST" 2>/dev/null || true
sleep 1
launchctl load "$BACKEND_PLIST"

log "Update abgeschlossen"
