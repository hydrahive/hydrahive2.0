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
log "Backend bereit"
