#!/usr/bin/env bash
# Python-venv im Repo, Backend-Paket im editable mode installieren.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

INSTALLER_DIR="${INSTALLER_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
# shellcheck source=installer/lib/python-venv.sh
source "$INSTALLER_DIR/lib/python-venv.sh"

VENV="$HH_REPO_DIR/.venv"
hh_ensure_python_venv "$VENV" "$HH_USER" "" "$HH_REPO_DIR"

log "Aktualisiere pip"
hh_run_as_owner "$HH_USER" "$VENV/bin/python" -m pip install --upgrade pip

log "Installiere hydrahive-core (editable + Dependencies)"
hh_run_as_owner "$HH_USER" "$VENV/bin/python" -m pip install -e "$HH_REPO_DIR/core"

# Das Python-Paket allein enthält keinen Browser. Immer die exakt zur
# installierten Playwright-Version passende Chromium-Revision sicherstellen;
# der Befehl ist idempotent und lädt bei vorhandenem Match nichts erneut.
log "Installiere passende Playwright-Chromium-Version"
HH_HOME="/home/$HH_USER"
PW_CACHE_DIR="$HH_HOME/.cache/ms-playwright"
install -d -o "$HH_USER" -g "$(id -gn "$HH_USER")" "$HH_HOME/.cache" "$PW_CACHE_DIR"
hh_run_as_owner_home "$HH_USER" "$HH_HOME" "$VENV/bin/python" -m playwright install chromium \
  || log "Playwright-Chromium-Install fehlgeschlagen — Streaming-Scraper nicht verfügbar"

# Mac/uv installieren falls fehlt — manche MCP-Server brauchen uvx
if ! "$VENV/bin/python" -m pip show anthropic >/dev/null 2>&1; then
  log "anthropic-SDK fehlt — installiere"
  hh_run_as_owner "$HH_USER" "$VENV/bin/python" -m pip install anthropic mcp
fi

# Permissions: Repo und venv müssen vom Service-User lesbar sein
chown -R "$HH_USER:$HH_USER" "$HH_REPO_DIR"

# git safe.directory — sonst bricht `sudo git pull` und `sudo -u hydrahive git pull`
# mit "dubious ownership" ab, weil nach dem chown das Repo nicht mehr dem
# git-aufrufenden User gehört. Für beide Nutzer eintragen.
git config --global --add safe.directory "$HH_REPO_DIR" 2>/dev/null || true
sudo -u "$HH_USER" git config --global --add safe.directory "$HH_REPO_DIR" 2>/dev/null || true

log "Backend bereit"
