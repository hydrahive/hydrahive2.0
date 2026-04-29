#!/usr/bin/env bash
# System-User für den Backend-Service. Kein Login, kein Home-Dir-Spam.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

if id "$HH_USER" &>/dev/null; then
  log "User '$HH_USER' existiert bereits"
else
  log "Lege User '$HH_USER' an"
  useradd --system --create-home --home-dir "/home/$HH_USER" --shell /usr/sbin/nologin "$HH_USER"
fi

# SSH-Verzeichnis mit korrekten Permissions — git braucht lesbare known_hosts
HH_HOME="/home/$HH_USER"
SSH_DIR="$HH_HOME/.ssh"
if [ ! -d "$SSH_DIR" ]; then
  mkdir -p "$SSH_DIR"
fi
chown -R "$HH_USER:$HH_USER" "$HH_HOME"
chmod 700 "$SSH_DIR"
touch "$SSH_DIR/known_hosts"
chown "$HH_USER:$HH_USER" "$SSH_DIR/known_hosts"
chmod 600 "$SSH_DIR/known_hosts"

# GitHub Host-Key eintragen falls noch nicht da
if ! grep -q "github.com" "$SSH_DIR/known_hosts" 2>/dev/null; then
  log "GitHub Host-Key in known_hosts eintragen"
  ssh-keyscan -t ed25519,rsa github.com 2>/dev/null >> "$SSH_DIR/known_hosts" || true
  chown "$HH_USER:$HH_USER" "$SSH_DIR/known_hosts"
fi
