#!/usr/bin/env bash
# Erstellt Daten- und Config-Verzeichnisse mit korrekten Permissions.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

for d in "$HH_DATA_DIR" "$HH_CONFIG_DIR"; do
  if [ ! -d "$d" ]; then
    log "Erzeuge $d"
    mkdir -p "$d"
  fi
  chown -R "$HH_USER:$HH_USER" "$d"
  chmod 750 "$d"
done

# Workspace-Unterverzeichnisse vorab anlegen
for sub in agents projects workspaces workspaces/master workspaces/projects workspaces/specialists plugins; do
  mkdir -p "$HH_DATA_DIR/$sub"
  chown -R "$HH_USER:$HH_USER" "$HH_DATA_DIR/$sub"
done

# Config-Verzeichnis muss von $HH_USER schreibbar sein (für users.json, llm.json)
chmod 770 "$HH_CONFIG_DIR"
log "Pfade bereit: $HH_DATA_DIR + $HH_CONFIG_DIR"
