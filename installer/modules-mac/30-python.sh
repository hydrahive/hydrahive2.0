#!/usr/bin/env bash
set -euo pipefail
log() { printf "  · %s\n" "$*"; }
# shellcheck source=../lib/mac-roles.sh
source "$(dirname "$0")/../lib/mac-roles.sh"

eval "$(/usr/local/bin/brew shellenv zsh 2>/dev/null || /opt/homebrew/bin/brew shellenv zsh 2>/dev/null || true)"

PYTHON="$(as_brew --prefix python@3.12)/bin/python3.12"
VENV="$HH_REPO_DIR/.venv"

# Repo gehört dem Dienst-Konto, venv/pip laufen als Dienst-Konto (pip-Cache in dessen Home).
priv chown -R "$HH_USER" "$HH_REPO_DIR"
cd "$HH_REPO_DIR"   # sudo -u aus einem Ordner, den das Konto nicht lesen darf → getcwd-Fehler

if [ ! -d "$VENV" ]; then
  log "Erstelle venv"
  as_svc "$PYTHON" -m venv "$VENV"
fi

log "Aktualisiere pip"
as_svc "$VENV/bin/pip" install --quiet --upgrade pip

log "Installiere hydrahive-core"
as_svc "$VENV/bin/pip" install --quiet -e "$HH_REPO_DIR/core"

log "Backend bereit"
