#!/usr/bin/env bash
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

eval "$(/usr/local/bin/brew shellenv zsh 2>/dev/null || /opt/homebrew/bin/brew shellenv zsh 2>/dev/null || true)"

PYTHON="$(brew --prefix python@3.12)/bin/python3.12"
VENV="$HH_REPO_DIR/.venv"

if [ ! -d "$VENV" ]; then
  log "Erstelle venv"
  "$PYTHON" -m venv "$VENV"
fi

log "Aktualisiere pip"
"$VENV/bin/pip" install --quiet --upgrade pip

log "Installiere hydrahive-core"
"$VENV/bin/pip" install --quiet -e "$HH_REPO_DIR/core"

chown -R "$HH_USER" "$HH_REPO_DIR"
log "Backend bereit"
