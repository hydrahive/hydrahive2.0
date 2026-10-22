#!/usr/bin/env bash
set -euo pipefail
log() { printf "  · %s\n" "$*"; }
# shellcheck source=../lib/mac-roles.sh
source "$(dirname "$0")/../lib/mac-roles.sh"
HH_LOG_DIR="${HH_LOG_DIR:-/usr/local/var/log}"

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
sudo mkdir -p "$HH_LOG_DIR"
if hh_service_account; then
  # Eigenes Dienst-Konto: den Ordner NICHT übernehmen – auf Intel-Macs gehört /usr/local/var/log Homebrew (Mac-Besitzer).
  # Stattdessen darf das Konto dort Dateien anlegen (launchd legt die Log-Dateien der Dienste als Dienst-Konto an).
  # Erst entfernen, dann setzen – sonst stünde der Eintrag nach jeder Installation einmal mehr da.
  ACE="user:$HH_USER allow list,search,add_file,readattr,readextattr,readsecurity"
  sudo chmod -a "$ACE" "$HH_LOG_DIR" 2>/dev/null || true
  sudo chmod +a "$ACE" "$HH_LOG_DIR"
  for f in hydrahive2.log hydrahive2-error.log; do
    sudo touch "$HH_LOG_DIR/$f"
    sudo chown "$HH_USER" "$HH_LOG_DIR/$f"
  done
else
  sudo chown -R "$HH_USER" "$HH_LOG_DIR"
fi

log "Pfade bereit: $HH_DATA_DIR + $HH_CONFIG_DIR"
