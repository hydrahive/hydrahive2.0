#!/usr/bin/env bash
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

for d in "$HH_DATA_DIR" "$HH_CONFIG_DIR"; do
  if [ ! -d "$d" ]; then
    log "Erzeuge $d"
    sudo mkdir -p "$d"
  fi
  sudo chown -R "$HH_USER" "$d"
  sudo chmod 750 "$d"
done

for sub in agents projects workspaces workspaces/master workspaces/projects workspaces/specialists plugins; do
  sudo mkdir -p "$HH_DATA_DIR/$sub"
  sudo chown -R "$HH_USER" "$HH_DATA_DIR/$sub"
done

sudo chmod 770 "$HH_CONFIG_DIR"

# Log-Verzeichnis
sudo mkdir -p /usr/local/var/log
sudo chown -R "$HH_USER" /usr/local/var/log

log "Pfade bereit: $HH_DATA_DIR + $HH_CONFIG_DIR"
