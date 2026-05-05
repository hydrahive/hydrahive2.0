#!/usr/bin/env bash
# Python-venv im Repo, Backend-Paket im editable mode installieren.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

VENV="$HH_REPO_DIR/.venv"

if [ ! -d "$VENV" ]; then
  log "Erstelle venv unter $VENV"
  python3.12 -m venv "$VENV"
fi

log "Aktualisiere pip"
"$VENV/bin/pip" install --upgrade pip

log "Installiere hydrahive-core (editable + Dependencies)"
"$VENV/bin/pip" install -e "$HH_REPO_DIR/core"

# Mac/uv installieren falls fehlt — manche MCP-Server brauchen uvx
if ! "$VENV/bin/pip" show anthropic >/dev/null 2>&1; then
  log "anthropic-SDK fehlt — installiere"
  "$VENV/bin/pip" install anthropic mcp
fi

# Permissions: venv muss vom Service-User lesbar sein
chown -R "$HH_USER:$HH_USER" "$HH_REPO_DIR"

# git safe.directory — sonst bricht `sudo git pull` und `sudo -u hydrahive git pull`
# mit "dubious ownership" ab, weil nach dem chown das Repo nicht mehr dem
# git-aufrufenden User gehört. Für beide Nutzer eintragen.
git config --global --add safe.directory "$HH_REPO_DIR" 2>/dev/null || true
sudo -u "$HH_USER" git config --global --add safe.directory "$HH_REPO_DIR" 2>/dev/null || true

log "Backend bereit"
