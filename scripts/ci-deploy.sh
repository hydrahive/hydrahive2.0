#!/usr/bin/env bash
# CI-Deploy: pull → test → build → restart (mit Rollback bei Test-Fehler)
# Wird vom GitHub Actions Runner als hydrahive-User aufgerufen.
set -euo pipefail

REPO=/opt/hydrahive2
VENV=$REPO/.venv
LOG_PREFIX="[ci-deploy]"

log() { echo "$LOG_PREFIX $*"; }

cd "$REPO"

# Aktuellen Stand für Rollback sichern
OLD_HEAD=$(git rev-parse HEAD)
log "Aktueller Stand: $OLD_HEAD"

# --- Pull ---
log "Pulling origin main..."
git pull origin main
NEW_HEAD=$(git rev-parse HEAD)
log "Neuer Stand: $NEW_HEAD"

if [ "$OLD_HEAD" = "$NEW_HEAD" ]; then
  log "Keine neuen Commits — abgebrochen."
  exit 0
fi

# --- Backend-Tests ---
log "Backend-Tests..."
if ! $VENV/bin/pytest core/tests/ -q --tb=short -x 2>&1; then
  log "FEHLER: Tests fehlgeschlagen — Rollback auf $OLD_HEAD"
  git reset --hard "$OLD_HEAD"
  exit 1
fi
log "Tests grün."

# --- Pip-Install wenn Abhängigkeiten geändert ---
if git diff --name-only "$OLD_HEAD" "$NEW_HEAD" | grep -q "pyproject.toml\|requirements"; then
  log "Abhängigkeiten geändert — pip install..."
  $VENV/bin/pip install -e "$REPO/core/" -q
fi

# --- Frontend-Build ---
log "Frontend-Build..."
if ! npm run build --prefix "$REPO/frontend" 2>&1; then
  log "FEHLER: Frontend-Build fehlgeschlagen — Rollback auf $OLD_HEAD"
  git reset --hard "$OLD_HEAD"
  exit 1
fi
log "Frontend-Build fertig."

# --- Restart ---
log "Service-Restart..."
sudo systemctl restart hydrahive2
sleep 2
if sudo systemctl is-active --quiet hydrahive2; then
  log "Deploy erfolgreich. $OLD_HEAD → $NEW_HEAD"
else
  log "FEHLER: Service nicht gestartet — Rollback auf $OLD_HEAD"
  git reset --hard "$OLD_HEAD"
  $VENV/bin/pip install -e "$REPO/core/" -q
  npm run build --prefix "$REPO/frontend" -q || true
  sudo systemctl restart hydrahive2
  exit 1
fi
