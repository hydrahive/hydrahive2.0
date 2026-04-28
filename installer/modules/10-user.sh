#!/usr/bin/env bash
# System-User für den Backend-Service. Kein Login, kein Home-Dir-Spam.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

if id "$HH_USER" &>/dev/null; then
  log "User '$HH_USER' existiert bereits"
else
  log "Lege User '$HH_USER' an"
  useradd --system --no-create-home --shell /usr/sbin/nologin "$HH_USER"
fi
